"""Pydantic schemas for data quality."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class QualityFlagQuerySchema(BaseModel):
    station_id: Optional[int] = None
    measurement_type_id: Optional[int] = None
    quality_status: Optional[str] = None
    severity: Optional[str] = None
    resolution_status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)


class ResolveFlagSchema(BaseModel):
    resolution_status: str
    admin_remarks: Optional[str] = None

    @field_validator("resolution_status")
    @classmethod
    def check_status(cls, value):
        if value not in ("RESOLVED", "IGNORED", "OPEN"):
            raise ValueError("Invalid resolution status.")
        return value
