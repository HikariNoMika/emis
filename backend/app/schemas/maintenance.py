"""Pydantic schemas for maintenance records."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

TYPES = ("ROUTINE", "CORRECTIVE", "CALIBRATION", "REPLACEMENT", "INSPECTION")


class MaintenanceSchema(BaseModel):
    station_id: Optional[int] = Field(default=None, ge=1)
    sensor_id: Optional[int] = None
    maintenance_type: Optional[str] = None
    maintenance_date: Optional[date] = None
    performed_by: Optional[str] = None
    description: Optional[str] = None
    findings: Optional[str] = None
    action_taken: Optional[str] = None
    calibration_details: Optional[str] = None
    next_maintenance_date: Optional[date] = None
    remarks: Optional[str] = None

    @field_validator("maintenance_type")
    @classmethod
    def check_type(cls, value):
        if value is not None and value not in TYPES:
            raise ValueError(f"Type must be one of {TYPES}")
        return value


class MaintenanceQuerySchema(BaseModel):
    station_id: Optional[int] = None
    sensor_id: Optional[int] = None
    maintenance_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
