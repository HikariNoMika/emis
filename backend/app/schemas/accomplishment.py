"""Pydantic schemas for the accomplishment reporting module."""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

CATEGORY_CODES = ("ACTIVITY", "DELIVERABLE")
REPORT_STATUSES = ("DRAFT", "IN_PROGRESS", "PRELIMINARY", "FINAL", "REVISED")
REPORT_TYPES = (
    "quarterly", "annual", "activities", "deliverables",
    "data_completeness", "q1", "q2", "q3", "q4",
)


def _non_negative(value):
    if value is not None and value < 0:
        raise ValueError("Value cannot be negative.")
    return value


class CategoryOut(BaseModel):
    id: int
    code: str
    name: str
    weight: float
    description: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class IndicatorCreate(BaseModel):
    category_code: str
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    reporting_year: int = Field(ge=2000, le=2100)
    unit: str = "Number of activities"
    annual_target: Optional[float] = None
    indicator_weight: float = Field(ge=0, le=100)
    station_id: Optional[int] = None
    responsible_person: Optional[str] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    status: str = "ACTIVE"
    remarks: Optional[str] = None

    @field_validator("category_code")
    @classmethod
    def check_category(cls, value):
        if value not in CATEGORY_CODES:
            raise ValueError(f"Category must be one of {CATEGORY_CODES}")
        return value

    @field_validator("annual_target")
    @classmethod
    def check_target(cls, value):
        return _non_negative(value)


class IndicatorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    category_code: Optional[str] = None
    unit: Optional[str] = None
    annual_target: Optional[float] = None
    indicator_weight: Optional[float] = Field(default=None, ge=0, le=100)
    station_id: Optional[int] = None
    responsible_person: Optional[str] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    status: Optional[str] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("annual_target")
    @classmethod
    def check_target(cls, value):
        return _non_negative(value)


class TargetCreate(BaseModel):
    indicator_id: int
    reporting_year: int = Field(ge=2000, le=2100)
    quarter: int = Field(ge=1, le=4)
    planned_target: float = Field(ge=0)
    is_approved: bool = False
    remarks: Optional[str] = None


class TargetUpdate(BaseModel):
    planned_target: Optional[float] = Field(default=None, ge=0)
    is_approved: Optional[bool] = None
    remarks: Optional[str] = None


class ActualCreate(BaseModel):
    indicator_id: int
    reporting_year: int = Field(ge=2000, le=2100)
    quarter: int = Field(ge=1, le=4)
    actual_quantity: float = Field(ge=0)
    unit: Optional[str] = None
    completion_date: Optional[date] = None
    reporting_date: Optional[date] = None
    evidence_reference: Optional[str] = None
    entry_reference: str = Field(min_length=1, max_length=150)
    is_cancelled: bool = False


class ActualUpdate(BaseModel):
    actual_quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    completion_date: Optional[date] = None
    reporting_date: Optional[date] = None
    evidence_reference: Optional[str] = None
    is_cancelled: Optional[bool] = None


class WeightSetItem(BaseModel):
    indicator_id: int
    weight: float = Field(ge=0, le=100)


class WeightsUpdate(BaseModel):
    reporting_year: int
    category_weights: Dict[str, float]
    indicator_weights: List[WeightSetItem] = []
    reason: Optional[str] = None

    @field_validator("category_weights")
    @classmethod
    def check_category_keys(cls, value):
        for key in value:
            if key not in CATEGORY_CODES:
                raise ValueError(f"Unknown category '{key}'.")
        return value


class SummaryQuery(BaseModel):
    year: int = Field(ge=2000, le=2100)
    quarter: int | None = Field(default=None, ge=1, le=4)


class DataCompletenessQuery(BaseModel):
    station_id: Optional[int] = None
    sensor_id: Optional[int] = None
    measurement_type_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ReportGenerate(BaseModel):
    reporting_year: int = Field(ge=2000, le=2100)
    quarter: int | None = Field(default=None, ge=1, le=4)
    report_type: str = "quarterly"
    file_format: str = "pdf"
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    remarks: Optional[str] = None

    @field_validator("report_type")
    @classmethod
    def check_type(cls, value):
        if value not in REPORT_TYPES:
            raise ValueError("Unsupported accomplishment report type.")
        return value

    @field_validator("file_format")
    @classmethod
    def check_format(cls, value):
        if value not in ("pdf", "xlsx"):
            raise ValueError("Format must be pdf or xlsx.")
        return value


class ReportRevise(BaseModel):
    remarks: Optional[str] = None


class AttachmentUpload(BaseModel):
    indicator_id: Optional[int] = None
    actual_id: Optional[int] = None
    evidence_reference: Optional[str] = None
