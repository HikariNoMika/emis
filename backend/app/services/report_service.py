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
    data = _gather_data(payload, date_from, date_to)

    report_folder = get_settings().REPORT_FOLDER
    os.makedirs(report_folder, exist_ok=True)
    extension = payload["file_format"]
    file_name = f"report_{uuid.uuid4().hex[:12]}.{extension}"
    file_path = os.path.join(report_folder, file_name)

    if extension == "pdf":
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
