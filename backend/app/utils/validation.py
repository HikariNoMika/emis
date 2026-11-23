"""Shared validation error formatting for FastAPI/Pydantic."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Return validation errors in the same envelope as the rest of the API."""
    errors = {}
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", [])[1:]) or "body"
        errors.setdefault(location, []).append(item.get("msg", "Invalid value"))
    return JSONResponse(
        {
            "success": False,
            "message": "Validation failed.",
            "errors": errors,
            "code": "VALIDATION_ERROR",
        },
        status_code=400,
    )
