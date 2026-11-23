"""
Value validation and data-quality rules applied during import.

These checks NEVER change the original value. They only decide the
`quality_status` written on the new measurement and create a separate
DataQualityFlag row when a value needs investigation.

The Salacafe reference workbook taught us that relative humidity can exceed
100% and that some zero readings may be real. Those are flagged as SUSPECT,
not silently replaced or deleted.
"""

# Hard physical rules that are always invalid regardless of configured ranges.
HARD_RULES = {
    "rainfall": (0, None),
    "rainfall_accumulation": (0, None),
    "max_rainfall_rate": (0, None),
    "wind_speed": (0, None),
    "wind_gust": (0, None),
    "wind_direction": (0, 360),
    "battery_percentage": (0, 100),
    "relative_humidity": (0, None),  # above 100 is SUSPECT, not INVALID
    "soil_water_content": (0, None),
}

# Values equal to zero that deserve an investigation note (not automatic error).
SUSPICIOUS_ZERO_TYPES = {"soil_water_content", "rainfall", "max_rainfall_rate"}


def validate_value(code, value, expected_min=None, expected_max=None):
    """
    Return (quality_status, severity, explanation).

    quality_status is one of VALID, SUSPECT, INVALID, MISSING, UNVERIFIED.
    """
    if value is None:
        return "MISSING", "INFO", "No value in the source cell."

    hard_min, hard_max = HARD_RULES.get(code, (None, None))

    if hard_min is not None and value < hard_min:
        return (
            "INVALID",
            "CRITICAL",
            f"Value {value} is below the physical minimum of {hard_min} for {code}.",
        )
    if hard_max is not None and value > hard_max:
        return (
            "INVALID",
            "CRITICAL",
            f"Value {value} is above the physical maximum of {hard_max} for {code}.",
        )

    # Values above the configured/expected range are suspicious, not proof of a
    # broken sensor. This covers the known RH > 100% case in the reference file.
    if expected_max is not None and value > float(expected_max):
        return (
            "SUSPECT",
            "WARNING",
            f"Value {value} exceeds the expected maximum of {expected_max} for {code}.",
        )
    if expected_min is not None and value < float(expected_min):
        return (
            "SUSPECT",
            "WARNING",
            f"Value {value} is below the expected minimum of {expected_min} for {code}.",
        )

    if code == "relative_humidity" and value > 100:
        return (
            "SUSPECT",
            "WARNING",
            "Relative humidity above 100% requires investigation; original value kept.",
        )

    if value == 0 and code in SUSPICIOUS_ZERO_TYPES:
        return (
            "SUSPECT",
            "INFO",
            f"Repeated or isolated zero reading for {code}; check channel placement.",
        )

    return "VALID", "INFO", "Value is within the expected range."
