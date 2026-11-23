"""Pydantic schemas for user management."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

VALID_ROLES = ("admin", "viewer")


def valid_email(value: str) -> str:
    """Basic email check that still allows internal domains such as .local."""
    if "@" not in value or "." not in value.split("@", 1)[1]:
        raise ValueError("Enter a valid email address.")
    return value


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: str
    full_name: str = Field(min_length=1, max_length=150)

    @field_validator("email")
    @classmethod
    def check_email(cls, value):
        return valid_email(value)
    password: str = Field(min_length=8)
    confirm_password: str
    role: str = "admin"
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def clean_username(cls, value):
        return value.strip()

    @field_validator("role")
    @classmethod
    def check_role(cls, value):
        if value not in VALID_ROLES:
            raise ValueError(f"Role must be one of {VALID_ROLES}")
        return value

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value, info):
        if value != info.data.get("password"):
            raise ValueError("Passwords do not match.")
        return value


class UserUpdateSchema(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, max_length=150)

    @field_validator("email")
    @classmethod
    def check_email(cls, value):
        return valid_email(value) if value else value
    role: Optional[str] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def check_role(cls, value):
        if value is not None and value not in VALID_ROLES:
            raise ValueError(f"Role must be one of {VALID_ROLES}")
        return value


class UserProfileUpdateSchema(BaseModel):
    """Fields a user may edit on their own profile."""

    full_name: str = Field(min_length=1, max_length=150)
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value):
        return valid_email(value)


class ResetPasswordSchema(BaseModel):
    new_password: str = Field(min_length=8)
    confirm_password: str
    must_change_password: bool = True

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value, info):
        if value != info.data.get("new_password"):
            raise ValueError("Passwords do not match.")
        return value


class UserQuerySchema(BaseModel):
    search: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
