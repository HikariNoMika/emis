"""Pydantic schemas for measurement, analytics and comparison queries."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MeasurementQuerySchema(BaseModel):
    station_id: Optional[int] = None
    sensor_id: Optional[int] = None
    measurement_type_id: Optional[int] = None
    quality_status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)


class FillGapsSchema(BaseModel):
    station_id: int
    measurement_type_id: int


class TrendsQuerySchema(BaseModel):
    station_id: int
    measurement_type_ids: List[int]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    interval_minutes: int = 15

    @field_validator("interval_minutes")
    @classmethod
    def check_interval(cls, value):
        if value not in (15, 30, 60, 180, 360, 1440):
            raise ValueError("Unsupported aggregation interval.")
        return value


class StatisticsQuerySchema(BaseModel):
    station_id: Optional[int] = None
    measurement_type_id: int
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ComparisonQuerySchema(BaseModel):
    station_ids: List[int]
    measurement_type_id: int
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    interval_minutes: int = 60


class FlexibleComparisonQuerySchema(BaseModel):
    station_id: int
    measurement_type_id: int
    date_from_a: str
    date_to_a: str
    date_from_b: str
    date_to_b: str
    interval_minutes: int = 60

    @field_validator("interval_minutes")
    @classmethod
    def check_interval(cls, value):
        if value not in (15, 30, 60, 180, 360, 1440):
            raise ValueError("Unsupported aggregation interval.")
        return value


class ExportQuerySchema(BaseModel):
    station_id: Optional[int] = None
    measurement_type_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    format: str = "csv"

    @field_validator("format")
    @classmethod
    def check_format(cls, value):
        if value not in ("csv", "xlsx"):
            raise ValueError("Format must be csv or xlsx.")
        return value
