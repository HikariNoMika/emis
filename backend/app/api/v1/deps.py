"""Shared FastAPI dependencies for authorization."""

from fastapi import Depends

from app.services.exceptions import ValidationAppError
from app.utils.security import get_current_user


def require_admin(user=Depends(get_current_user)):
    """Allow only administrators."""
    if getattr(user, "role", "admin") != "admin":
        raise ValidationAppError("Administrator permission is required.")
    return user
