"""Pydantic schemas for imports."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ImportMappingSchema(BaseModel):
    sheet_name: Optional[str] = None
    timestamp_column: Optional[str] = None
    port_column: Optional[str] = None
    measurement_columns: Optional[Dict[str, str]] = None
    sensor_mapping: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    station_id: Optional[int] = None
    station_type: Optional[str] = None


class ImportQuerySchema(BaseModel):
    status: Optional[str] = None
    station_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
