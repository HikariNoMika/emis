"""Common interface and helpers for file connectors."""


class BaseConnector:
    """A connector inspects a file and returns a uniform snapshot dictionary.

    Snapshot shape:
        {
          "sheets": [
              {"name": str, "headers": [str], "rows": [dict], "row_count": int}
          ],
          "metadata": dict,
          "metadata_text": [str],
          "warnings": [str],
        }
    """

    def inspect(self, path):
        raise NotImplementedError

    def read_rows(self, path, sheet_name):
        raise NotImplementedError


def json_safe(value):
    """Convert pandas/numpy values into JSON-serializable Python values."""
    import pandas as pd

    if value is None or value is pd.NA:
        return None
    if isinstance(value, float):
        # NaN is a missing value, not a number.
        return None if pd.isna(value) else value
    if hasattr(value, "item") and not isinstance(value, str):
        # numpy scalar -> Python scalar
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    try:
        # Final NaN check for python floats that slipped through.
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value
