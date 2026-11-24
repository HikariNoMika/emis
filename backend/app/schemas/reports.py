"""Pydantic schema for report generation."""

from typing import List, Optional

from pydantic import BaseModel, field_validator

REPORT_TYPES = (
    "daily", "weekly", "monthly", "station_performance", "sensor_health",
    "data_quality", "rainfall", "environmental_trends",
    "multi_station_comparison", "import_summary", "maintenance_calibration",
    "station_full", "station_comparison",
    "accomplishment_quarterly", "accomplishment_annual",
    "accomplishment_activities", "accomplishment_deliverables",
    "accomplishment_data_completeness",
)


class ReportGenerateSchema(BaseModel):
    report_type: str
    title: Optional[str] = None
    station_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    measurement_type_ids: List[int] = []
    station_ids: List[int] = []
    file_format: str = "pdf"
    reporting_year: Optional[int] = None
    quarter: Optional[int] = None

    @field_validator("report_type")
    @classmethod
    def check_type(cls, value):
        if value not in REPORT_TYPES:
            raise ValueError("Unsupported report type.")
        return value

    @field_validator("file_format")
    @classmethod
    def check_format(cls, value):
        if value not in ("pdf", "xlsx"):
            raise ValueError("Format must be pdf or xlsx.")
        return value
