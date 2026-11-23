"""Pydantic schemas for sensors."""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

SENSOR_STATUSES = ("ACTIVE", "INACTIVE", "FAULTY", "MAINTENANCE", "UNKNOWN")


class SensorSchema(BaseModel):
    station_id: Optional[int] = Field(default=None, ge=1)
    port_number: Optional[str] = Field(default=None, max_length=20)
    name: Optional[str] = Field(default=None, max_length=150)
    model: Optional[str] = Field(default=None, max_length=100)
    manufacturer: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    installation_date: Optional[date] = None
    calibration_date: Optional[date] = None
    next_calibration_date: Optional[date] = None
    operational_status: str = "ACTIVE"
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_archived: bool = False

    @field_validator("operational_status")
    @classmethod
    def check_status(cls, value):
        if value not in SENSOR_STATUSES:
            raise ValueError(f"Status must be one of {SENSOR_STATUSES}")
        return value


class SensorMeasurementTypesSchema(BaseModel):
    measurement_type_ids: List[int] = Field(default_factory=list)
    column_hints: Optional[Dict[str, str]] = None


class SensorQuerySchema(BaseModel):
    search: Optional[str] = None
    station_id: Optional[int] = None
    status: Optional[str] = None
    is_archived: bool = False
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
