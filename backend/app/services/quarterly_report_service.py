"""Build the quarterly watershed data analysis report as a Word document.

The structure follows the DENR memorandum used by the Watershed Monitoring Team:
memo header, instrument inventory, parameter summary, highest/lowest tables,
wind-direction distribution, AWLS section, correlations, summary and sign-off.
Every number is computed from stored measurements at generation time.
"""

from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from statistics import StatisticsError, correlation, fmean

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from app.extensions import db
from app.models import Measurement, MeasurementType, Station

# Parameters shown in the highest/lowest tables, in report order.
KEY_CODES = (
    "rainfall",
    "air_temperature",
    "relative_humidity",
    "wind_speed",
    "solar_radiation",
    "water_level",
    "water_temperature",
    "ec",
)

WIND_BINS = (
    ("N", 337.5, 22.5), ("NE", 22.5, 67.5), ("E", 67.5, 112.5),
    ("SE", 112.5, 157.5), ("S", 157.5, 202.5), ("SW", 202.5, 247.5),
    ("W", 247.5, 292.5), ("NW", 292.5, 337.5),
)


def quarter_bounds(year, quarter):
    """Return [start, end) datetimes for a quarter (UTC)."""
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    start = datetime(year, start_month, 1, tzinfo=timezone.utc)
    if end_month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, end_month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _fmt(value, digits=2):
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def _when(value):
    return value.strftime("%B %d, %Y %I:%M %p") if value else "-"


def _heading(doc, text, level=1):
    doc.add_heading(text, level=level)


def _table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, label in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = str(label)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = str(value)
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = width
    return table


def build_docx(year, quarter, title=None):
    """Return the report as .docx bytes for the given year and quarter."""
    start, end = quarter_bounds(year, quarter)
    all_types = MeasurementType.query.all()
    types = {item.code: item for item in all_types}
    types_by_id = {item.id: item for item in all_types}
    stations = Station.query.filter_by(is_archived=False).order_by(Station.id).all()
    type_ids = [item.id for item in types.values()]

    base_query = Measurement.query.filter(
        Measurement.observation_time >= start,
        Measurement.observation_time < end,
    )

    # ---- Summary statistics per measurement type ---------------------------
    stats_rows = db.session.query(
        Measurement.measurement_type_id,
        db.func.count(Measurement.id),
        db.func.count(db.func.distinct(Measurement.station_id)),
        db.func.avg(Measurement.normalized_value),
        db.func.max(Measurement.normalized_value),
        db.func.min(Measurement.normalized_value),
    ).filter(
        Measurement.observation_time >= start,
        Measurement.observation_time < end,
    ).group_by(Measurement.measurement_type_id).all()
    stats = {row[0]: row for row in stats_rows}

    # ---- Extremes with station and timestamp -------------------------------
    extremes = {}
    for code in KEY_CODES:
        item = types.get(code)
        if not item:
            continue
        for label, order in (("max", Measurement.normalized_value.desc()),
                             ("min", Measurement.normalized_value.asc())):
            record = (
                base_query.filter(Measurement.measurement_type_id == item.id,
                                  Measurement.normalized_value.isnot(None))
                .order_by(order).first()
            )
            extremes[(code, label)] = record

    # ---- Observations grouped by type, station and time -------------------
    series = defaultdict(lambda: defaultdict(list))
    wind = defaultdict(lambda: defaultdict(int))
    for type_id, station_id, value, observed in db.session.query(
        Measurement.measurement_type_id,
        Measurement.station_id,
        Measurement.normalized_value,
        Measurement.observation_time,
    ).filter(
        Measurement.observation_time >= start,
        Measurement.observation_time < end,
        Measurement.normalized_value.isnot(None),
    ).all():
        series[type_id][observed].append(float(value))
        if types.get("wind_direction") and type_id == types["wind_direction"].id:
            degrees = float(value) % 360
            for name, low, high in WIND_BINS:
                if low <= high:
                    hit = low <= degrees < high
                else:
                    hit = degrees >= low or degrees < high
                if hit:
                    wind[station_id][name] += 1
                    break

    daily = {
        type_id: {when: fmean(values) for when, values in by_time.items()}
        for type_id, by_time in series.items()
    }

    def corr(code_a, code_b):
        a, b = types.get(code_a), types.get(code_b)
        if not a or not b:
            return None
        shared = sorted(set(daily.get(a.id, {})) & set(daily.get(b.id, {})))
        if len(shared) < 3:
            return None
        xs = [daily[a.id][key] for key in shared]
        ys = [daily[b.id][key] for key in shared]
        try:
            return correlation(xs, ys)
        except StatisticsError:
            return None

    # ---- Compose the document ---------------------------------------------
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    for line in (
        "Republic of the Philippines",
        "Department of Environment and Natural Resources",
        "OFFICE OF THE REGIONAL EXECUTIVE DIRECTOR",
        "Region XII, Aurora Street, City of Koronadal, South Cotabato",
    ):
        p = doc.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    p = doc.add_paragraph("MEMORANDUM")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True
    doc.add_paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    doc.add_paragraph("FOR:    The Regional Executive Director, DENR Region XII")
    doc.add_paragraph("THRU:   Chief, Conservation and Development Division")
    doc.add_paragraph("FROM:   The Watershed Monitoring Team")
    doc.add_paragraph()
    subject = doc.add_paragraph()
    subject.add_run("SUBJECT: ").bold = True
    subject.add_run(title or f"Q{quarter} {year} Data Analysis Report")

    _heading(doc, "INTRODUCTION", 2)
    doc.add_paragraph(
        "This report presents the data generated by the science-based real-time "
        "watershed monitoring instruments within Region XII, specifically the "
        "Tamontaca River Watershed, from "
        f"{start.strftime('%B %d, %Y')} to {(end.replace(tzinfo=None)).strftime('%B %d, %Y')}. "
        "All values below were computed from measurements stored in the EMIS "
        "database at generation time; no value is estimated or filled in."
    )

    _heading(doc, "Table 1. Instruments installed within the watershed", 2)
    _table(doc,
           ["Station", "Code", "Type", "Coordinates", "Status", "Interval (s)"],
           [[s.name, s.station_code, s.station_type or "AWS",
             (f"{s.latitude}, {s.longitude}" if s.latitude is not None and s.longitude is not None else "Not surveyed"),
             s.operational_status or "UNKNOWN", s.measurement_interval_seconds]
            for s in stations])

    _heading(doc, "Table 2. Summary of recorded data", 2)
    _table(doc,
           ["Parameter", "Stations", "Observations", "Average", "Maximum", "Minimum"],
           [[types_by_id[type_id].name, row[2], row[1],
             _fmt(row[3]), _fmt(row[4]), _fmt(row[5])]
            for type_id, row in sorted(stats.items(), key=lambda pair: pair[1][0])
            if type_id in types_by_id])

    _heading(doc, "Highest and lowest recorded values", 2)
    for code in KEY_CODES:
        item = types.get(code)
        if not item:
            continue
        high, low = extremes.get((code, "max")), extremes.get((code, "min"))
        if high is None and low is None:
            continue
        _heading(doc, f"{item.name} ({item.unit})", 3)
        rows = []
        for label, record in (("Highest", high), ("Lowest", low)):
            if record is None:
                continue
            station = db.session.get(Station, record.station_id)
            rows.append([label, _fmt(record.normalized_value),
                         station.name if station else record.station_id,
                         _when(record.observation_time)])
        _table(doc, ["Category", "Value", "Station", "Observed at (UTC)"], rows)

    _heading(doc, "Table 3. Wind direction distribution", 2)
    direction_rows = []
    station_totals = [sum(wind.get(s.id, {}).values()) for s in stations]
    for name, _, _ in WIND_BINS:
        counts = [wind.get(s.id, {}).get(name, 0) for s in stations]
        total = sum(counts)
        if total == 0 and name != "N":
            continue
        direction_rows.append(
            [name]
            + [
                f"{(count * 100 / station_total):.0f}%" if station_total else "-"
                for count, station_total in zip(counts, station_totals)
            ]
            + [str(total)]
        )
    if direction_rows:
        _table(doc, ["Direction"] + [s.name for s in stations] + ["Readings"],
               direction_rows)

    _heading(doc, "Automated Water Level Station", 2)
    level = types.get("water_level")
    if level and level.id in stats:
        row = stats[level.id]
        doc.add_paragraph(
            f"Streamflow level averaged {_fmt(row[3])} m, with a maximum of "
            f"{_fmt(row[4])} m and a minimum of {_fmt(row[5])} m across "
            f"{row[1]:,} readings."
        )
    else:
        doc.add_paragraph("No water-level readings were stored for this period.")

    _heading(doc, "Correlation of parameters", 2)
    for label, a, b in (
        ("Rainfall and air temperature", "rainfall", "air_temperature"),
        ("Rainfall and water level", "rainfall", "water_level"),
        ("Air temperature and water temperature", "air_temperature", "water_temperature"),
        ("Wind speed and solar radiation", "wind_speed", "solar_radiation"),
    ):
        value = corr(a, b)
        text = (f"Pearson r = {value:.3f} over the aligned observations."
                if value is not None
                else "Insufficient aligned observations to compute a correlation.")
        doc.add_paragraph(f"{label}: {text}")

    _heading(doc, "SUMMARY", 2)
    doc.add_paragraph(
        f"The quarter covered {sum(row[1] for row in stats.values()):,} stored "
        f"readings across {len(types)} parameters and {len(stations)} active stations. "
        "Data-quality flags, gaps and anomalous readings remain in the source "
        "records and are reported without modification."
    )
    doc.add_paragraph("For information and record.")
    doc.add_paragraph()
    doc.add_paragraph("Prepared by: ____________________________")
    doc.add_paragraph("Reviewed by: ____________________________")
    doc.add_paragraph("Noted by:    ____________________________")

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output.getvalue()
