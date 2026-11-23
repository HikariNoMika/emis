"""Pydantic schemas for alerts."""

from typing import Optional

from pydantic import BaseModel, Field


class AlertQuerySchema(BaseModel):
    station_id: Optional[int] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)


class AlertActionSchema(BaseModel):
    remarks: Optional[str] = None
