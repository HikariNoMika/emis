"""Report generation (PDF via ReportLab, Excel via OpenPyXL).

All report content is derived from the database at generation time. Generated
files are stored under REPORT_FOLDER and registered in the `reports` table so
they can be listed and downloaded later.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.extensions import db
from app.models import (
    DataQualityFlag,
    Measurement,
    MeasurementType,
    Report,
    Station,
)
from app.repositories.measurement_repository import MeasurementRepository
from app.utils.serializers import report_to_dict
from app.utils.time import to_iso, utcnow

from . import measurement_service
from .audit_service import log_action
from .exceptions import NotFoundError

REPORT_TITLES = {
    "daily": "Daily Environmental Report",
    "weekly": "Weekly Environmental Report",
    "monthly": "Monthly Environmental Report",
    "station_performance": "Station Performance Report",
    "sensor_health": "Sensor Health Report",
    "data_quality": "Data Quality Report",
    "rainfall": "Rainfall Report",
    "environmental_trends": "Environmental Trend Report",
    "multi_station_comparison": "Multi-Station Comparison Report",
    "import_summary": "Data Import Summary",
    "maintenance_calibration": "Maintenance and Calibration Report",
    "station_full": "Station Comprehensive Report",
    "station_comparison": "Multi-Station Comparison Report",
}


def list_reports(page, per_page):
    return Report.query.order_by(Report.generated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


def _resolve_period(payload, date_from, date_to):
    """Use explicit dates when given, otherwise infer from the report type."""
    if date_from and date_to:
        return date_from, date_to
    now = utcnow()
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(payload["report_type"], 30)
    return now - timedelta(days=days), now


def _gather_data(payload, date_from, date_to):
    type_ids = payload.get("measurement_type_ids") or [
        item.id for item in MeasurementType.query.order_by(MeasurementType.id).all()
    ]
    station = None
    if payload.get("station_id"):
        station = db.session.get(Station, payload["station_id"])
        if station is None:
            raise NotFoundError("Station not found.")

    records_query = Measurement.query.filter(
        Measurement.measurement_type_id.in_(type_ids)
    )
    if station:
        records_query = records_query.filter_by(station_id=station.id)
    if date_from:
        records_query = records_query.filter(Measurement.observation_time >= date_from)
    if date_to:
        records_query = records_query.filter(Measurement.observation_time <= date_to)
    records = records_query.order_by(Measurement.observation_time.asc()).all()

    sections = []
    for type_id in type_ids:
        measurement_type = MeasurementRepository.get_type(type_id)
        if measurement_type is None:
            continue
        params = {"measurement_type_id": type_id}
        if station:
            params["station_id"] = station.id
        stats = measurement_service.statistics_for(params, date_from, date_to)
        series = measurement_service.trends(
            {
                "station_id": station.id if station else _first_station_id(records),
                "measurement_type_ids": [type_id],
                "interval_minutes": 60,
            },
            date_from,
            date_to,
        )
        sections.append(
            {
                "type": measurement_type,
                "statistics": stats,
                "points": series[0]["points"] if series else [],
            }
        )

    quality_query = DataQualityFlag.query
    if station:
        quality_query = quality_query.filter_by(station_id=station.id)
    if date_from:
        quality_query = quality_query.filter(DataQualityFlag.observation_time >= date_from)
    notes = quality_query.order_by(DataQualityFlag.created_at.desc()).limit(15).all()

    return {
        "station": station,
        "sections": sections,
        "records": records,
        "quality_notes": notes,
    }


def _first_station_id(records):
    return records[0].station_id if records else None


def _gather_station_report(payload, date_from, date_to):
    """Collect everything a station report needs for the given date range.

    Includes all readings, per-parameter statistics, data gaps, quality flags
    and plain-language explanations. Missing readings are reported as missing,
    never as zero.
    """
    from app.services import measurement_service as ms

    station = db.session.get(Station, payload.get("station_id"))
    if station is None:
        raise NotFoundError("Station not found.")

    allowed = payload.get("measurement_type_ids") or []
    if allowed:
        types = [t for t in MeasurementType.query.order_by(MeasurementType.id).all() if t.id in allowed]
    else:
        types = MeasurementType.query.order_by(MeasurementType.id).all()

    records_query = Measurement.query.filter_by(station_id=station.id)
    if date_from:
        records_query = records_query.filter(Measurement.observation_time >= date_from)
    if date_to:
        records_query = records_query.filter(Measurement.observation_time <= date_to)
    records = records_query.order_by(Measurement.observation_time.asc()).all()

    sections = []
    for measurement_type in types:
        params = {"station_id": station.id, "measurement_type_id": measurement_type.id}
        stats = ms.statistics_for(params, date_from, date_to)
        series = ms.trends(
            {
                "station_id": station.id,
                "measurement_type_ids": [measurement_type.id],
                "interval_minutes": 60,
            },
            date_from,
            date_to,
        )
        # Gaps only make sense for a type that actually has readings.
        gaps = ms.data_gaps(station.id, measurement_type.id, date_from, date_to, limit=50)
        sections.append({
            "type": measurement_type,
            "statistics": stats,
            "points": series[0]["points"] if series else [],
            "gaps": gaps,
        })

    quality_query = DataQualityFlag.query.filter_by(station_id=station.id)
    if date_from:
        quality_query = quality_query.filter(DataQualityFlag.observation_time >= date_from)
    if date_to:
        quality_query = quality_query.filter(DataQualityFlag.observation_time <= date_to)
    quality_notes = quality_query.order_by(DataQualityFlag.created_at.desc()).limit(50).all()

    return {
        "station": station,
        "sections": sections,
        "records": records,
        "quality_notes": quality_notes,
    }


def _build_station_pdf(path, title, date_from, date_to, data):
    """Station-focused PDF with all trends, statistics, readings, gaps and explanations."""
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        path, pagesize=A4, title=title,
        leftMargin=28, rightMargin=28, topMargin=32, bottomMargin=32,
    )
    story = [Paragraph(title, styles["Title"]), Spacer(1, 10)]
    station = data["station"]
    story.append(Paragraph(f"<b>Station:</b> {station.name} ({station.station_code})", styles["Normal"]))
    if station.site_name:
        story.append(Paragraph(f"<b>Site:</b> {station.site_name}", styles["Normal"]))
    story.append(Paragraph(f"<b>Reporting period:</b> {to_iso(date_from)} to {to_iso(date_to)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Data source:</b> uploaded monitoring files / stored measurements", styles["Normal"]))
    story.append(Paragraph(f"<b>Generated:</b> {to_iso(utcnow())}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Plain-language explanation of how to read the report.
    story.append(Paragraph("How to read this report", styles["Heading2"]))
    for line in [
        "Values are the original readings preserved from the source files; nothing is invented or overwritten.",
        "Missing readings are shown as missing (or as gaps) and are never counted as zero.",
        "Min / Max / Average / Median / Std dev describe only the readings stored in the selected period.",
        "Gaps list stretches where no reading exists at the station's expected interval.",
        "Quality notes explain why certain readings were flagged for investigation.",
    ]:
        story.append(Paragraph(f"• {line}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Every parameter's trend for the selected period, each with an explanation.
    story.append(Paragraph("Environmental trends", styles["Heading2"]))
    story.append(Paragraph(
        "Each chart plots the stored readings for one parameter across the "
        "selected period, aggregated hourly. Missing intervals are left blank "
        "and are never drawn as zero.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 6))
    for section in data["sections"]:
        points = section["points"]
        stats = section["statistics"]
        mtype = section["type"]
        if points:
            drawing = Drawing(460, 130)
            plot = LinePlot()
            plot.x, plot.y = 42, 22
            plot.height, plot.width = 95, 395
            plot.data = [[(index, point["value"]) for index, point in enumerate(points)]]
            plot.lines[0].strokeColor = colors.HexColor("#1d5b96")
            drawing.add(plot)
        else:
            drawing = Paragraph(
                "No readings for this parameter in the selected period.",
                styles["Normal"],
            )
        caption = (
            f"<b>{mtype.name}</b> ({mtype.unit or 'no unit'}) — "
            f"{stats.get('observations', 0):,} readings; "
            f"average {stats.get('average')}, min {stats.get('min')}, max {stats.get('max')}. "
            f"Aggregation: {mtype.aggregation_method or 'average'}."
        )
        story.append(KeepTogether([
            Paragraph(caption, styles["Normal"]),
            Spacer(1, 3),
            drawing,
            Spacer(1, 10),
        ]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Statistical summary", styles["Heading2"]))
    summary_rows = [["Parameter", "Unit", "Min", "Max", "Average", "Median", "Std dev", "Total", "N", "Missing"]]
    for section in data["sections"]:
        s = section["statistics"]
        summary_rows.append([
            s.get("name") or s.get("code", ""), s.get("unit") or "",
            str(s.get("min")), str(s.get("max")), str(s.get("average")),
            str(s.get("median")), str(s.get("std_dev")), str(s.get("total")),
            str(s.get("observations")), str(s.get("missing_records")),
        ])
    t = Table(summary_rows, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Data gaps", styles["Heading2"]))
    any_gap = False
    gap_rows = [["Parameter", "From", "To", "Missing readings", "Jump (min)"]]
    for section in data["sections"]:
        gaps = (section["gaps"] or {}).get("gaps") or []
        for gap in gaps:
            any_gap = True
            gap_rows.append([
                section["type"].name,
                str(gap.get("start", ""))[:19], str(gap.get("end", ""))[:19],
                str(gap.get("missing_readings", "")), str(gap.get("gap_minutes", "")),
            ])
    if any_gap:
        gt = Table(gap_rows, repeatRows=1)
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        story.append(gt)
    else:
        story.append(Paragraph("No data gaps detected in the selected period.", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(PageBreak())
    story.append(Paragraph("All measurements in period", styles["Heading2"]))
    story.append(Paragraph(
        f"{len(data['records']):,} readings. Columns show the stored value and its quality status.",
        styles["Normal"],
    ))
    header = ["Observed at (UTC)", "Parameter", "Value", "Unit", "Quality"]
    detail = [header]
    for record in data["records"]:
        mtype = MeasurementRepository.get_type(record.measurement_type_id)
        value = record.normalized_value if record.normalized_value is not None else record.original_value
        detail.append([
            to_iso(record.observation_time),
            mtype.name if mtype else str(record.measurement_type_id),
            "" if value is None else str(value),
            record.unit or "",
            record.quality_status,
        ])
    dt = Table(detail, repeatRows=1)
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 5.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(dt)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Quality notes", styles["Heading2"]))
    if data["quality_notes"]:
        for note in data["quality_notes"]:
            story.append(Paragraph(
                f"• {note.rule_code}: {note.explanation or 'See flag details.'}",
                styles["Normal"],
            ))
    else:
        story.append(Paragraph("No quality flags in this period.", styles["Normal"]))

    doc.build(story)


def _build_station_xlsx(path, title, date_from, date_to, data):
    """Station-focused Excel with info, summary, gaps and all readings."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    info = wb.active
    info.title = "Report info"
    station = data["station"]
    info.append(["Report title", title])
    info.append(["Station", station.name])
    info.append(["Station code", station.station_code])
    info.append(["Period from", to_iso(date_from)])
    info.append(["Period to", to_iso(date_to)])
    info.append(["Generated", to_iso(utcnow())])
    info.append(["Note", "Missing readings are reported as missing, never as zero."])
    for cell in info[1]:
        cell.font = Font(bold=True)

    summary = wb.create_sheet("Summary")
    summary.append(["Parameter", "Unit", "Min", "Max", "Average", "Median", "Std dev", "Total", "Observations", "Missing"])
    for section in data["sections"]:
        s = section["statistics"]
        summary.append([
            s.get("name"), s.get("unit"), s.get("min"), s.get("max"),
            s.get("average"), s.get("median"), s.get("std_dev"), s.get("total"),
            s.get("observations"), s.get("missing_records"),
        ])

    gaps = wb.create_sheet("Data gaps")
    gaps.append(["Parameter", "From", "To", "Missing readings", "Jump (min)"])
    for section in data["sections"]:
        for gap in (section["gaps"] or {}).get("gaps") or []:
            gaps.append([
                section["type"].name, gap.get("start"), gap.get("end"),
                gap.get("missing_readings"), gap.get("gap_minutes"),
            ])

    detail = wb.create_sheet("Measurements")
    detail.append(["Observation time (UTC)", "Parameter", "Value", "Unit", "Quality"])
    for record in data["records"]:
        mtype = MeasurementRepository.get_type(record.measurement_type_id)
        value = record.normalized_value if record.normalized_value is not None else record.original_value
        detail.append([
            to_iso(record.observation_time),
            mtype.name if mtype else str(record.measurement_type_id),
            float(value) if value is not None else None,
            record.unit,
            record.quality_status,
        ])

    quality = wb.create_sheet("Quality notes")
    quality.append(["Rule", "Status", "Severity", "Explanation"])
    for note in data["quality_notes"]:
        quality.append([note.rule_code, note.quality_status, note.severity, note.explanation])
    wb.save(path)


def _build_pdf(path, title, payload, date_from, date_to, data):
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(path, pagesize=A4, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    station = data["station"]
    story.append(
        Paragraph(
            f"<b>Station:</b> {station.name if station else 'All stations'} "
            f"({station.station_code if station else '—'})",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Reporting period:</b> {to_iso(date_from)} to {to_iso(date_to)}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Data source:</b> uploaded monitoring files / database measurements<br/>"
            f"<b>Generated:</b> {to_iso(utcnow())}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 14))

    story.append(Paragraph("Statistical summary", styles["Heading2"]))
    summary_rows = [
        ["Parameter", "Unit", "Min", "Max", "Average", "Median", "Std dev", "Total", "N", "Missing"]
    ]
    for section in data["sections"]:
        stats = section["statistics"]
        summary_rows.append(
            [
                stats["name"] or stats["code"], stats["unit"] or "",
                str(stats["min"]), str(stats["max"]), str(stats["average"]),
                str(stats["median"]), str(stats["std_dev"]), str(stats["total"]),
                str(stats["observations"]), str(stats["missing_records"]),
            ]
        )
    table = Table(summary_rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))

    # A simple line chart for the first parameter that has data.
    for section in data["sections"]:
        points = section["points"]
        if not points:
            continue
        story.append(
            Paragraph(f"Trend: {section['type'].name}", styles["Heading2"])
        )
        drawing = Drawing(460, 160)
        plot = LinePlot()
        plot.x, plot.y = 45, 25
        plot.height, plot.width = 125, 390
        plot.data = [[(index, point["value"]) for index, point in enumerate(points)]]
        plot.lines[0].strokeColor = colors.HexColor("#1d5b96")
        drawing.add(plot)
        story.append(drawing)
        story.append(Spacer(1, 12))
        break

    story.append(Paragraph("Recent measurements", styles["Heading2"]))
    data_rows = [["Observed at (UTC)", "Type", "Value", "Unit", "Quality"]]
    for record in data["records"][:80]:
        measurement_type = MeasurementRepository.get_type(record.measurement_type_id)
        data_rows.append(
            [
                to_iso(record.observation_time),
                measurement_type.code if measurement_type else str(record.measurement_type_id),
                str(record.normalized_value if record.normalized_value is not None else record.original_value),
                record.unit or "",
                record.quality_status,
            ]
        )
    detail_table = Table(data_rows, repeatRows=1)
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ]
        )
    )
    story.append(detail_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Data quality notes", styles["Heading2"]))
    if data["quality_notes"]:
        for note in data["quality_notes"]:
            story.append(
                Paragraph(
                    f"• {note.rule_code}: {note.explanation or 'See flag details.'}",
                    styles["Normal"],
                )
            )
    else:
        story.append(Paragraph("No quality flags in this period.", styles["Normal"]))

    document.build(story)


def _build_xlsx(path, title, payload, date_from, date_to, data):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    info = workbook.active
    info.title = "Report info"
    info.append(["Report title", title])
    info.append(["Station", data["station"].name if data["station"] else "All stations"])
    info.append(["Period from", to_iso(date_from)])
    info.append(["Period to", to_iso(date_to)])
    info.append(["Generated", to_iso(utcnow())])
    info.append(["Data source", "Uploaded monitoring files / database measurements"])
    for cell in info[1]:
        cell.font = Font(bold=True)

    summary = workbook.create_sheet("Summary")
    summary.append(
        ["Parameter", "Unit", "Min", "Max", "Average", "Median", "Std dev", "Total", "Observations", "Missing"]
    )
    for section in data["sections"]:
        stats = section["statistics"]
        summary.append(
            [
                stats["name"], stats["unit"], stats["min"], stats["max"],
                stats["average"], stats["median"], stats["std_dev"],
                stats["total"], stats["observations"], stats["missing_records"],
            ]
        )

    detail = workbook.create_sheet("Measurements")
    detail.append(["Observation time (UTC)", "Type id", "Value", "Unit", "Quality"])
    for record in data["records"]:
        detail.append(
            [
                to_iso(record.observation_time),
                record.measurement_type_id,
                float(record.normalized_value) if record.normalized_value is not None else None,
                record.unit,
                record.quality_status,
            ]
        )

    quality = workbook.create_sheet("Quality notes")
    quality.append(["Rule", "Status", "Severity", "Explanation"])
    for note in data["quality_notes"]:
        quality.append([note.rule_code, note.quality_status, note.severity, note.explanation])

    workbook.save(path)


def _gather_comparison_report(payload, date_from, date_to):
    """Compare up to 3 stations for each measurement type over a date span.

    For every parameter we collect each station's trend series and statistics,
    plus the exact lowest and highest reading (value, station and timestamp)
    across all compared stations.
    """
    from app.services import measurement_service as ms

    ids = (payload.get("station_ids") or [])[:3]
    if payload.get("station_id"):
        ids = [payload["station_id"]] + [i for i in ids if i != payload["station_id"]]
        ids = ids[:3]
    ids = [i for i in ids if db.session.get(Station, i) is not None]
    if not ids:
        raise NotFoundError("No valid stations selected for comparison.")

    stations = [db.session.get(Station, i) for i in ids]
    allowed = payload.get("measurement_type_ids") or []
    if allowed:
        types = [t for t in MeasurementType.query.order_by(MeasurementType.id).all() if t.id in allowed]
    else:
        # Only parameters that exist at the selected stations.
        present = {
            row[0] for row in db.session.query(Measurement.measurement_type_id)
            .filter(Measurement.station_id.in_(ids)).distinct().all()
        }
        types = [t for t in MeasurementType.query.order_by(MeasurementType.id).all() if t.id in present]

    blocks = []
    for mtype in types:
        series_by_station = []
        lows = []
        highs = []
        comparison_rows = []
        for station in stations:
            params = {"station_id": station.id, "measurement_type_id": mtype.id}
            stats = ms.statistics_for(params, date_from, date_to)
            series = ms.trends(
                {
                    "station_id": station.id,
                    "measurement_type_ids": [mtype.id],
                    "interval_minutes": 60,
                },
                date_from,
                date_to,
            )
            points = series[0]["points"] if series else []
            series_by_station.append({
                "station": station,
                "points": points,
                "statistics": stats,
            })
            comparison_rows.append({
                "station": station.name,
                "code": station.station_code,
                "observations": stats.get("observations", 0),
                "min": stats.get("min"),
                "max": stats.get("max"),
                "average": stats.get("average"),
                "median": stats.get("median"),
            })

            # Exact extremes with their timestamps for this station.
            query = Measurement.query.filter_by(
                station_id=station.id, measurement_type_id=mtype.id
            )
            if date_from:
                query = query.filter(Measurement.observation_time >= date_from)
            if date_to:
                query = query.filter(Measurement.observation_time <= date_to)
            low = query.order_by(Measurement.normalized_value.asc()).first()
            high = query.order_by(Measurement.normalized_value.desc()).first()
            if low and low.normalized_value is not None:
                lows.append((float(low.normalized_value), station.name, to_iso(low.observation_time)))
            if high and high.normalized_value is not None:
                highs.append((float(high.normalized_value), station.name, to_iso(high.observation_time)))

        overall_low = min(lows) if lows else None
        overall_high = max(highs) if highs else None
        blocks.append({
            "type": mtype,
            "series": series_by_station,
            "comparison": comparison_rows,
            "overall_low": overall_low,
            "overall_high": overall_high,
        })

    return {
        "stations": stations,
        "blocks": blocks,
    }


def _build_comparison_pdf(path, title, date_from, date_to, data):
    """PDF with overlaid trends, per-trend comparison table, and recorded extremes."""
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    palette = [colors.HexColor("#0f6fbf"), colors.HexColor("#e07a1f"), colors.HexColor("#2e8b57")]
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        path, pagesize=A4, title=title,
        leftMargin=28, rightMargin=28, topMargin=32, bottomMargin=32,
    )
    story = [Paragraph(title, styles["Title"]), Spacer(1, 8)]
    story.append(Paragraph(
        "<b>Stations:</b> " + ", ".join(
            f"{s.name} ({s.station_code})" for s in data["stations"]
        ),
        styles["Normal"],
    ))
    story.append(Paragraph(
        f"<b>Reporting period:</b> {to_iso(date_from)} to {to_iso(date_to)}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        "<b>Note:</b> only the same parameter is compared across stations. "
        "Missing readings are never counted as zero.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("How to read this report", styles["Heading2"]))
    for line in [
        "Each trend chart overlays the selected stations for one parameter over the same period.",
        "The comparison table lists each station's observation count, min, max, average and median.",
        "Recorded low / high shows the exact value, station and timestamp of the extremes in this period.",
        "Charts are aggregated hourly; blank intervals are missing data, not zero.",
    ]:
        story.append(Paragraph(f"• {line}", styles["Normal"]))
    story.append(Spacer(1, 8))

    for index, block in enumerate(data["blocks"]):
        mtype = block["type"]
        rows = [["Station", "Code", "N", "Min", "Max", "Average", "Median"]]
        for row in block["comparison"]:
            rows.append([
                row["station"], row["code"], str(row["observations"]),
                str(row["min"]), str(row["max"]), str(row["average"]), str(row["median"]),
            ])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ]))

        # Overlay each station's series on one chart.
        chart_data = []
        for si, s in enumerate(block["series"]):
            if s["points"]:
                chart_data.append([(i, p["value"]) for i, p in enumerate(s["points"])])
        if chart_data:
            drawing = Drawing(460, 140)
            plot = LinePlot()
            plot.x, plot.y = 42, 24
            plot.height, plot.width = 100, 395
            plot.data = chart_data
            for i in range(len(chart_data)):
                plot.lines[i].strokeColor = palette[i % len(palette)]
            drawing.add(plot)
        else:
            drawing = Paragraph("No readings for this parameter in the selected period.", styles["Normal"])

        low = block["overall_low"]
        high = block["overall_high"]
        extreme_text = (
            f"Recorded low: {low[0]} at {low[1]} on {low[2]}.<br/>"
            f"Recorded high: {high[0]} at {high[1]} on {high[2]}."
            if low and high else "No stored values for this parameter in the selected period."
        )

        block_story = [
            Paragraph(f"{mtype.name} ({mtype.unit or 'no unit'})", styles["Heading2"]),
            drawing,
            Spacer(1, 6),
            table,
            Spacer(1, 4),
            Paragraph(extreme_text, styles["Normal"]),
            Spacer(1, 12),
        ]
        story.append(KeepTogether(block_story))
        if index == 1:
            story.append(PageBreak())

    doc.build(story)


def _build_comparison_xlsx(path, title, date_from, date_to, data):
    """Excel with one comparison sheet per parameter plus an overview."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    overview = wb.active
    overview.title = "Overview"
    overview.append(["Report", title])
    overview.append(["Stations", ", ".join(s.name for s in data["stations"])])
    overview.append(["Period from", to_iso(date_from)])
    overview.append(["Period to", to_iso(date_to)])
    overview.append(["Generated", to_iso(utcnow())])
    for cell in overview[1]:
        cell.font = Font(bold=True)

    for block in data["blocks"]:
        name = block["type"].name[:31]
        ws = wb.create_sheet(name)
        ws.append(["Station", "Code", "Observations", "Min", "Max", "Average", "Median"])
        for row in block["comparison"]:
            ws.append([
                row["station"], row["code"], row["observations"],
                row["min"], row["max"], row["average"], row["median"],
            ])
        low, high = block["overall_low"], block["overall_high"]
        ws.append([])
        ws.append(["Recorded low", low[0] if low else None, low[1] if low else None, low[2] if low else None])
        ws.append(["Recorded high", high[0] if high else None, high[1] if high else None, high[2] if high else None])
        ws.append([])
        ws.append(["Time"] + [s.name for s in data["stations"]])
        max_len = max((len(s["points"]) for s in block["series"]), default=0)
        for i in range(max_len):
            row = []
            for s in block["series"]:
                row.append(s["points"][i]["value"] if i < len(s["points"]) else None)
            row_time = next(
                (s["points"][i]["time"] for s in block["series"] if i < len(s["points"])), ""
            )
            ws.append([row_time] + row)
    wb.save(path)


def _generate_accomplishment_report(payload, user_id):
    """Delegate to the accomplishment module, then register the file here."""
    from . import accomplishment_reporting_service as acc_reporting
    from . import accomplishment_service as acc_service

    year = payload.get("reporting_year")
    if year is None:
        year = datetime.now(timezone.utc).year
    quarter = payload.get("quarter")
    report_type = payload["report_type"].replace("accomplishment_", "", 1)
    if report_type == "quarterly" and not quarter:
        quarter = 1

    acc_report = acc_service.generate_report(
        {
            "reporting_year": year,
            "quarter": quarter,
            "report_type": report_type,
            "prepared_by": payload.get("title") or "EMIS Administrator",
            "reviewed_by": None,
            "remarks": None,
        },
        user_id,
    )
    path, file_name = acc_reporting.generate_file(
        acc_report, payload.get("file_format", "pdf")
    )

    report = Report(
        report_number=f"RPT-{uuid.uuid4().hex[:10].upper()}",
        report_type=payload["report_type"],
        title=acc_reporting.TITLES.get(report_type, "Accomplishment Report"),
        station_id=payload.get("station_id"),
        date_from=None,
        date_to=None,
        measurement_type_ids=[],
        parameters=payload,
        file_format=payload.get("file_format", "pdf"),
        file_name=file_name,
        file_path=path,
        generated_by_id=user_id,
        generated_at=utcnow(),
    )
    db.session.add(report)
    db.session.flush()
    log_action(
        "REPORT_GENERATED", "reports", record_identifier=report.report_number,
        new_values=report_to_dict(report), user_id=user_id, commit=False,
    )
    db.session.commit()
    return report


def generate(payload, user_id):
    """Generate, store and register a report. Returns the Report record."""
    # Accomplishment reports are produced by their own module and registered in
    # the shared report history so the Reports page can list/download them.
    if str(payload.get("report_type", "")).startswith("accomplishment_"):
        return _generate_accomplishment_report(payload, user_id)

    date_from, date_to = _resolve_period(payload, None, None)
    # Re-resolve using parsed dates when the caller supplied them as strings.
    if payload.get("date_from"):
        date_from = datetime.fromisoformat(
            str(payload["date_from"]).replace("Z", "+00:00")
        )
    if payload.get("date_to"):
        date_to = datetime.fromisoformat(
            str(payload["date_to"]).replace("Z", "+00:00")
        )
    if date_from and date_from.tzinfo is None:
        date_from = date_from.replace(tzinfo=timezone.utc)
    if date_to and date_to.tzinfo is None:
        date_to = date_to.replace(tzinfo=timezone.utc)

    title = payload.get("title") or REPORT_TITLES[payload["report_type"]]

    if payload["report_type"] == "station_full":
        data = _gather_station_report(payload, date_from, date_to)
    elif payload["report_type"] == "station_comparison":
        data = _gather_comparison_report(payload, date_from, date_to)
    else:
        data = _gather_data(payload, date_from, date_to)

    report_folder = get_settings().REPORT_FOLDER
    os.makedirs(report_folder, exist_ok=True)
    extension = payload["file_format"]
    file_name = f"report_{uuid.uuid4().hex[:12]}.{extension}"
    file_path = os.path.join(report_folder, file_name)

    if payload["report_type"] == "station_full":
        if extension == "pdf":
            _build_station_pdf(file_path, title, date_from, date_to, data)
        else:
            _build_station_xlsx(file_path, title, date_from, date_to, data)
    elif payload["report_type"] == "station_comparison":
        if extension == "pdf":
            _build_comparison_pdf(file_path, title, date_from, date_to, data)
        else:
            _build_comparison_xlsx(file_path, title, date_from, date_to, data)
    elif extension == "pdf":
        _build_pdf(file_path, title, payload, date_from, date_to, data)
    else:
        _build_xlsx(file_path, title, payload, date_from, date_to, data)

    report = Report(
        report_number=f"RPT-{uuid.uuid4().hex[:10].upper()}",
        report_type=payload["report_type"],
        title=title,
        station_id=payload.get("station_id"),
        date_from=date_from,
        date_to=date_to,
        measurement_type_ids=payload.get("measurement_type_ids") or [],
        parameters=payload,
        file_format=extension,
        file_name=file_name,
        file_path=file_path,
        generated_by_id=user_id,
        generated_at=utcnow(),
    )
    db.session.add(report)
    db.session.flush()
    log_action(
        "REPORT_GENERATED",
        "reports",
        record_identifier=report.report_number,
        new_values=report_to_dict(report),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return report
