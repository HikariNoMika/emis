"""Pydantic schemas for system settings and audit filters."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SystemSettingSchema(BaseModel):
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None
    category: Optional[str] = None


class AuditLogFilterSchema(BaseModel):
    user_id: Optional[int] = None
    module: Optional[str] = None
    action: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
