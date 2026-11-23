"""Timezone-aware time helpers.

All timestamps stored in the database are timezone-aware UTC values. Display
conversion to a station's local timezone happens at the API/response boundary.
"""

from datetime import datetime, timezone


def utcnow():
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def parse_iso(value):
    """
    Parse an ISO-8601 string into an aware datetime.
    Returns None for empty/invalid input instead of raising, which makes it
    convenient for optional API filters.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def to_iso(value):
    """Serialize a datetime to an ISO string, safely handling None."""
    return value.isoformat() if value else None
