"""Consistent JSON response helpers for FastAPI routes.

Every endpoint returns { success, message?, data?, meta? }. Routes return a
plain dict; `success_response` is used when a custom status code is needed.
"""

from fastapi.responses import JSONResponse


def success(data=None, message=None, status_code=200, meta=None):
    """Return a JSONResponse (used when a non-200 status is required)."""
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    return JSONResponse(payload, status_code=status_code)


def ok(data=None, message=None, meta=None):
    """Return a plain dict for a normal HTTP 200 response."""
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    return payload


def created(data=None, message="Created successfully."):
    return success(data=data, message=message, status_code=201)


def error(message, status_code=400, errors=None, code=None):
    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors
    if code:
        payload["code"] = code
    return JSONResponse(payload, status_code=status_code)


def paginated(items, page, per_page, total, message=None):
    meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        "has_next": page * per_page < total,
        "has_prev": page > 1,
    }
    return ok(data=items, message=message, meta=meta)
