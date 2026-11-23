"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class LoginSchema(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        return self


class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
