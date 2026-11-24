"""
Column-role detection and value normalization.

This module converts human spreadsheet headers ("Air Temp (degC)", "RH %") into
internal measurement codes ("air_temperature", "relative_humidity"). Because it
works on header text and a configurable alias table, it does not depend on
column positions and will work with future station workbooks after the admin
reviews the suggested mapping in the preview screen.
"""

import re

# Order does not matter here: we sort by length so the most specific alias wins.
MEASUREMENT_ALIASES = [
    ("electrical conductivity", "ec"),
    ("water temperature", "water_temperature"),
    ("water level", "water_level"),
    ("systembattery", "system_battery_voltage"),
    ("systembatteryvolts", "system_battery_voltage"),
    ("systembatteryvoltage", "system_battery_voltage"),
    ("system temperature", "system_temperature"),
    ("systemtemperature", "system_temperature"),
    ("waterlevel", "water_level"),
    ("ec", "ec"),
    ("max rainfall rate", "max_rainfall_rate"),
    ("max precip rate", "max_rainfall_rate"),
    ("max precipitation rate", "max_rainfall_rate"),
    ("maximum rainfall rate", "max_rainfall_rate"),
    ("rainfall rate", "max_rainfall_rate"),
    ("rainfall accumulation", "rainfall_accumulation"),
    ("rain accumulation", "rainfall_accumulation"),
    ("atmospheric pressure", "atmospheric_pressure"),
    ("barometric pressure", "atmospheric_pressure"),
    ("vapor pressure deficit", "vapor_pressure_deficit"),
    ("vapour pressure deficit", "vapor_pressure_deficit"),
    ("relative humidity", "relative_humidity"),
    ("soil water content", "soil_water_content"),
    ("water content", "soil_water_content"),
    ("soil moisture", "soil_water_content"),
    ("logger temperature", "logger_temperature"),
    ("air temperature", "air_temperature"),
    ("wind direction", "wind_direction"),
    ("battery voltage", "battery_voltage"),
    ("battery percent", "battery_percentage"),
    ("reference pressure", "atmospheric_pressure"),
    ("precipitation", "rainfall"),
    ("solar radiation", "solar_radiation"),
    ("wind speed", "wind_speed"),
    ("wind gust", "wind_gust"),
    ("gust speed", "wind_gust"),
    ("air temp", "air_temperature"),
    ("rainfall", "rainfall"),
    ("radiation", "solar_radiation"),
    ("humidity", "relative_humidity"),
    ("pressure", "atmospheric_pressure"),
    ("temperature", "air_temperature"),
    ("direction", "wind_direction"),
    ("battery", "battery_percentage"),
    ("solar", "solar_radiation"),
    ("gust", "wind_gust"),
    ("moisture", "soil_water_content"),
    ("volt", "battery_voltage"),
    ("rain", "rainfall"),
    ("temp", "air_temperature"),
    ("vpd", "vapor_pressure_deficit"),
    ("batt", "battery_percentage"),
    ("rh", "relative_humidity"),
]

TIMESTAMP_WORDS = ("timestamp", "date time", "datetime", "observation time", "time", "date")
PORT_WORDS = ("port", "channel")


def _normalize_header(header):
    text = str(header or "").lower()
    # The reference workbook uses ".NET"-generated placeholders in some header
    # cells. Treat them as empty so they cannot produce false mappings.
    if "system.xml.xmlelement" in text or text.startswith("unnamed") or text == "nan":
        return ""
    # Raw Config 1 prefixes names with "raw"; the processed sheet does not.
    text = re.sub(r"^raw\s+", "", text)
    text = text.replace("_", " ").replace("-", " ")
    # Remove a trailing unit such as "(degC)" so aliases match the label.
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def measurement_types_as_dicts(measurement_types):
    """Convert MeasurementType ORM objects into simple dicts for detection."""
    return [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "unit": item.unit,
            "expected_min": item.expected_min,
            "expected_max": item.expected_max,
        }
        for item in measurement_types
    ]


def guess_measurement_type(header, available_codes):
    """Return a measurement-type code for a header, or None if unknown."""
    text = _normalize_header(header)
    for alias, code in sorted(MEASUREMENT_ALIASES, key=lambda item: len(item[0]), reverse=True):
        if alias in text and code in available_codes:
            return code
    return None


def guess_column_roles(headers, measurement_types):
    """
    Build a suggested mapping from the headers of one sheet.

    Returns a dict with timestamp_column, port_column and measurement_columns.
    """
    available_codes = {item["code"] for item in measurement_types}
    lower_headers = {header: _normalize_header(header) for header in headers}

    # Prefer a dedicated Timestamps column over generic date/time columns.
    timestamp_column = next(
        (header for header, text in lower_headers.items()
         if text.replace(" ", "") in ("timestamp", "timestamps")),
        None,
    )
    if timestamp_column is None:
        timestamp_column = next(
            (header for header, text in lower_headers.items()
             if any(word in text for word in TIMESTAMP_WORDS) and "interval" not in text),
            None,
        )
    port_column = next(
        (header for header, text in lower_headers.items()
         if any(word in text for word in PORT_WORDS)),
        None,
    )

    measurement_columns = {}
    for header in headers:
        if header == timestamp_column or header == port_column:
            continue
        code = guess_measurement_type(header, available_codes)
        if code:
            measurement_columns[str(header)] = code

    return {
        "timestamp_column": timestamp_column,
        "port_column": port_column,
        "measurement_columns": measurement_columns,
    }


def detect_station_from_snapshot(snapshot, stations):
    """Try to identify the station from the Metadata sheet.

    We look for exact station codes and device serial numbers in the flattened
    metadata text. If nothing matches, the administrator selects the station in
    the preview screen — we never guess from coordinates alone.
    """
    searchable = [str(item).lower() for item in snapshot.get("metadata_text", [])]
    searchable.extend(str(value).lower() for value in snapshot.get("metadata", {}).values())

    for station in stations:
        for candidate in (station.station_code, station.device_serial_number):
            if not candidate:
                continue
            candidate_lower = str(candidate).lower()
            if any(candidate_lower in text for text in searchable):
                return station
    return None


def normalize_number(value):
    """Convert a spreadsheet cell into a float or None (never a silent zero)."""
    import math

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if math.isnan(float(value)) else float(value)
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in {"nan", "na", "n/a", "null", "none", "-"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return None if math.isnan(number) else number
