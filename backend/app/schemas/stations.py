"""Pydantic schemas for stations."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

STATION_STATUSES = ("ONLINE", "DELAYED", "OFFLINE", "MAINTENANCE", "UNKNOWN")


class StationSchema(BaseModel):
    station_code: Optional[str] = Field(default=None, max_length=50)
    name: Optional[str] = Field(default=None, max_length=150)
    site_name: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    elevation: Optional[float] = None
    timezone: str = "Asia/Manila"
    measurement_interval_seconds: int = Field(default=900, ge=1, le=86400)
    installation_date: Optional[date] = None
    operational_status: str = "UNKNOWN"
    device_serial_number: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = None
    is_archived: bool = False

    @field_validator("operational_status")
    @classmethod
    def check_status(cls, value):
        if value not in STATION_STATUSES:
            raise ValueError(f"Status must be one of {STATION_STATUSES}")
        return value


class ClearDataSchema(BaseModel):
    password: str = Field(..., min_length=1)


class StationQuerySchema(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    is_archived: bool = False
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
