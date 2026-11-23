"""PDF and Excel generation for accomplishment reports."""

import os
import uuid

from app.config import get_settings
from app.services import accomplishment_calculator as calc

TITLES = {
    "quarterly": "Quarterly Accomplishment Report",
    "q1": "Q1 Accomplishment Report",
    "q2": "Q2 Accomplishment Report",
    "q3": "Q3 Accomplishment Report",
    "q4": "Q4 Accomplishment Report",
    "annual": "Annual Accomplishment Report",
    "activities": "Activities Accomplishment Report",
    "deliverables": "Deliverables Accomplishment Report",
    "data_completeness": "Environmental Data Completeness Report",
}


def _payload(report):
    snapshot = report.snapshots[-1] if report.snapshots else None
    data = snapshot.snapshot if snapshot else {}
    if report.quarter:
        computed = calc.quarterly_summary(report.reporting_year, report.quarter)
    else:
        computed = calc.annual_summary(report.reporting_year)
    return computed or data


def _build_pdf(path, report, data):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title = TITLES.get(report.report_type, "Accomplishment Report")
    document = SimpleDocTemplate(path, pagesize=A4, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 10)]

    story.append(Paragraph(f"<b>Reporting period:</b> {data.get('period_name')}", styles["Normal"]))
    story.append(Paragraph(
        f"<b>Period:</b> {data.get('period_start')} to {data.get('period_end')}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        f"<b>Report status:</b> {report.status} &nbsp; <b>Version:</b> {report.version}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        f"<b>Prepared by:</b> {report.prepared_by or '—'} &nbsp; "
        f"<b>Reviewed by:</b> {report.reviewed_by or '—'}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        f"<b>Generated:</b> {report.generated_at.isoformat() if report.generated_at else '—'}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Category scores", styles["Heading2"]))
    rows = [["Category", "Weight %", "Score %", "Complete"]]
    for code, category in data.get("categories", {}).items():
        rows.append([
            category.get("name", code),
            str(category.get("weight")),
            str(category.get("score")) if category.get("score") is not None else "N/A",
            "Yes" if category.get("is_complete") else "No",
        ])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"<b>Overall accomplishment:</b> "
        f"{data.get('overall') if data.get('overall') is not None else 'N/A'}%",
        styles["Normal"],
    ))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Indicator details", styles["Heading2"]))
    indicator_rows = [[
        "Indicator", "Category", "Planned", "Actual", "Unit", "%", "Weight", "Contribution", "Status",
    ]]
    for category in data.get("categories", {}).values():
        for item in category.get("indicators", []):
            indicator_rows.append([
                item["name"], item["category"],
                str(item["planned_target"]) if item["planned_target"] is not None else "N/A",
                str(item["actual_accomplishment"]) if item["actual_accomplishment"] is not None else "—",
                item["unit"],
                str(item["percentage"]) if item["percentage"] is not None else "N/A",
                str(item["weight"]),
                str(item["weighted_contribution"]) if item["weighted_contribution"] is not None else "N/A",
                item["status"],
            ])
    detail = Table(indicator_rows, repeatRows=1)
    detail.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174a7c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
    ]))
    story.append(detail)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Delays, issues and remarks", styles["Heading2"]))
    for remark in data.get("remarks", []) or ["No blocking issues recorded."]:
        story.append(Paragraph(f"• {remark}", styles["Normal"]))
    if report.remarks:
        story.append(Paragraph(f"• {report.remarks}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Environmental data completeness (separate technical KPI)", styles["Heading2"]))
    story.append(Paragraph(
        "Data completeness is reported separately and is never added to accomplishment "
        "scores when the same work is already represented by an indicator.",
        styles["Normal"],
    ))
    document.build(story)


def _build_xlsx(path, report, data):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    info = workbook.active
    info.title = "Report info"
    info_rows = [
        ["Report title", TITLES.get(report.report_type, "Accomplishment Report")],
        ["Report number", report.report_number],
        ["Reporting period", data.get("period_name")],
        ["From", data.get("period_start")],
        ["To", data.get("period_end")],
        ["Status", report.status],
        ["Version", report.version],
        ["Prepared by", report.prepared_by or ""],
        ["Reviewed by", report.reviewed_by or ""],
        ["Generated", report.generated_at.isoformat() if report.generated_at else ""],
        ["Overall accomplishment %", data.get("overall")],
    ]
    for row in info_rows:
        info.append(row)
    info["A1"].font = Font(bold=True)

    scores = workbook.create_sheet("Category scores")
    scores.append(["Category", "Weight %", "Score %", "Complete"])
    for code, category in data.get("categories", {}).items():
        scores.append([
            category.get("name", code), category.get("weight"),
            category.get("score"), category.get("is_complete"),
        ])

    indicators = workbook.create_sheet("Indicators")
    indicators.append([
        "Indicator", "Category", "Planned", "Actual", "Unit", "Percentage",
        "Weight", "Weighted contribution", "Status", "Remarks",
    ])
    for category in data.get("categories", {}).values():
        for item in category.get("indicators", []):
            indicators.append([
                item["name"], item["category"], item["planned_target"],
                item["actual_accomplishment"], item["unit"], item["percentage"],
                item["weight"], item["weighted_contribution"], item["status"],
                item.get("remarks"),
            ])

    notes = workbook.create_sheet("Remarks")
    notes.append(["Remarks / delays / issues"])
    for remark in data.get("remarks", []) or []:
        notes.append([remark])
    if report.remarks:
        notes.append([report.remarks])

    workbook.save(path)


def generate_file(report, file_format="pdf"):
    """Generate a file for an accomplishment report and register it on the report."""
    folder = get_settings().REPORT_FOLDER
    os.makedirs(folder, exist_ok=True)
    file_name = f"accomplishment_{report.report_number.lower()}.{file_format}"
    path = os.path.join(folder, file_name)
    data = _payload(report)

    if file_format == "xlsx":
        _build_xlsx(path, report, data)
    else:
        _build_pdf(path, report, data)

    report.file_name = file_name
    report.file_path = path
    return path, file_name
