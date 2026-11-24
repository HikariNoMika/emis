"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class LoginSchema(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


def validate_password_policy(value):
    """Reject weak passwords: 12+ chars with upper, lower, digit and symbol."""
    if len(value) < 12:
        raise ValueError("Password must be at least 12 characters.")
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain an uppercase letter.")
    if not any(c.islower() for c in value):
        raise ValueError("Password must contain a lowercase letter.")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain a digit.")
    if not any(not c.isalnum() for c in value):
        raise ValueError("Password must contain a special character.")
    return value


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        validate_password_policy(self.new_password)
        return self


class MFACodeSchema(BaseModel):
    code: str = Field(min_length=6, max_length=255)


class MFAVerifySchema(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=255)


class MFADisableSchema(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6)


class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    mfa_enabled: bool = False
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
