"""
Timestamp parsing and timezone handling.

Observation times from a station are LOCAL times. We convert them to aware UTC
datetimes before storing, because the database and all API responses use UTC.
The station's configured timezone (e.g. Asia/Manila or UTC+08:00) is supplied by
the import mapping.
"""

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


def build_timezone(name):
    """Return a tzinfo for 'Asia/Manila', 'UTC+08:00' or 'UTC'."""
    if not name:
        return timezone.utc
    text = str(name).strip()
    if text.upper() in {"UTC", "GMT"}:
        return timezone.utc

    match = re.fullmatch(r"(?:UTC|GMT)\s*([+-])(\d{1,2})(?::?(\d{2}))?", text, re.I)
    if match:
        sign = 1 if match.group(1) == "+" else -1
        hours = int(match.group(2))
        minutes = int(match.group(3) or 0)
        offset = timedelta(hours=hours, minutes=minutes) * sign
        return timezone(offset)

    try:
        return ZoneInfo(text)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def parse_timestamp(value, timezone_name="Asia/Manila"):
    """
    Parse one cell into a timezone-aware UTC datetime.

    Supports ISO strings, common spreadsheet date formats and Excel serial
    numbers. Returns None for missing/invalid values so the caller can flag
    them instead of crashing the import.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        return None

    parsed = None

    # Excel stores dates as days since 1899-12-30.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            parsed = pd.to_datetime(float(value), unit="D", origin="1899-12-30")
        except (ValueError, OverflowError):
            return None
    else:
        try:
            parsed = pd.to_datetime(str(value), errors="coerce", dayfirst=False)
        except (ValueError, TypeError):
            return None

    if parsed is None:
        return None
    if isinstance(parsed, pd.Series):
        return None
    if pd.isna(parsed):
        return None

    # pandas.Timestamp -> python datetime
    if isinstance(parsed, pd.Timestamp):
        naive = parsed.to_pydatetime().replace(tzinfo=None)
    elif isinstance(parsed, datetime):
        naive = parsed.replace(tzinfo=None)
    else:
        return None

    tzinfo = build_timezone(timezone_name)
    aware = naive.replace(tzinfo=tzinfo)
    return aware.astimezone(timezone.utc)
