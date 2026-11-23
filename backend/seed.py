"""
Seed initial reference data.

This script is SAFE TO RUN MORE THAN ONCE: it only inserts a row when it does not
already exist. Run it after `alembic upgrade head`.

It creates:
  1. the first administrator account,
  2. the standard measurement type catalogue,
  3. the two built-in data sources,
  4. the Salacafe reference station using the coordinates supplied in the brief,
  5. default system settings.

It deliberately does NOT invent sensors or spreadsheet columns for Salacafe —
those will come from inspecting the real workbook in Phase 3.
"""

import os

from app.config import get_settings
from app.extensions import db
from app.models import (
    DataSource,
    MeasurementType,
    Station,
    SystemSetting,
    User,
)
from app.utils.security import hash_password

# Measurement types shared by all stations. The units below are the internal
# (normalized) units. Importers convert source units into these where needed.
MEASUREMENT_TYPES = [
    # code, name, category, unit, min, max, circular, aggregation
    ("air_temperature", "Air temperature", "ATMOSPHERIC", "degC", -60, 80, False, "AVG"),
    ("relative_humidity", "Relative humidity", "ATMOSPHERIC", "%", 0, 100, False, "AVG"),
    ("atmospheric_pressure", "Atmospheric pressure", "ATMOSPHERIC", "hPa", 800, 1100, False, "AVG"),
    ("vapor_pressure_deficit", "Vapor Pressure Deficit", "ATMOSPHERIC", "kPa", 0, 20, False, "AVG"),
    ("wind_speed", "Wind speed", "WIND", "m/s", 0, 100, False, "AVG"),
    ("wind_gust", "Wind gust", "WIND", "m/s", 0, 100, False, "MAX"),
    ("wind_direction", "Wind direction", "WIND", "deg", 0, 360, True, "CIRCULAR_MEAN"),
    ("rainfall", "Rainfall", "PRECIPITATION", "mm", 0, 1000, False, "SUM"),
    ("max_rainfall_rate", "Maximum rainfall rate", "PRECIPITATION", "mm/h", 0, 1000, False, "MAX"),
    ("rainfall_accumulation", "Rainfall accumulation", "PRECIPITATION", "mm", 0, 10000, False, "SUM"),
    ("solar_radiation", "Solar radiation", "SOLAR", "W/m2", 0, 1500, False, "AVG"),
    ("soil_water_content", "Soil water content", "SOIL", "%", 0, 100, False, "AVG"),
    ("battery_percentage", "Battery percentage", "EQUIPMENT", "%", 0, 100, False, "AVG"),
    ("battery_voltage", "Battery voltage", "EQUIPMENT", "V", 0, 30, False, "AVG"),
    ("logger_temperature", "Logger temperature", "EQUIPMENT", "degC", -40, 85, False, "AVG"),
    ("water_level", "Water level", "HYDROLOGY", "mm", -10000, 10000, False, "AVG"),
    ("water_temperature", "Water temperature", "WATER", "degC", -10, 60, False, "AVG"),
    ("ec", "Electrical conductivity", "WATER", "mS/cm", 0, 200, False, "AVG"),
    ("system_temperature", "System temperature", "EQUIPMENT", "degC", -40, 85, False, "AVG"),
    ("system_battery_voltage", "System battery voltage", "EQUIPMENT", "V", 0, 30, False, "AVG"),
]

DEFAULT_SETTINGS = {
    "station_status_thresholds": {
        "delayed_minutes": 30,
        "offline_minutes": 120,
        "note": "Based on data freshness only. Excel upload delay is not proof of offline equipment.",
    },
    "data_quality_rules": {
        "relative_humidity_max": 100,
        "flag_repeated_identical_readings": 6,
        "flag_zero_soil_moisture": True,
    },
    "alert_thresholds": {
        "battery_warning_percent": 30,
        "battery_critical_percent": 15,
    },
    "import_settings": {
        "allowed_extensions": [".xlsx", ".csv"],
        "known_sheet_names": ["Config 1", "Raw Config 1", "Metadata"],
        "duplicate_policy": "skip_and_report",
    },
    "default_timezone": {"value": "Asia/Manila"},
    "report_settings": {
        "default_format": "pdf",
        "include_quality_notes": True,
    },
}


def seed_admin():
    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@emis.local")
    password = os.getenv("ADMIN_PASSWORD", "ChangeThisPassword123!")
    full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")

    user = User.query.filter_by(username=username).first()
    if user:
        print(f"[skip] admin '{username}' already exists")
        return user

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="admin",
        is_active=True,
        must_change_password=True,
    )
    db.session.add(user)
    print(f"[created] admin '{username}'")
    return user


def seed_measurement_types():
    for code, name, category, unit, low, high, circular, aggregation in MEASUREMENT_TYPES:
        if MeasurementType.query.filter_by(code=code).first():
            continue
        db.session.add(
            MeasurementType(
                code=code,
                name=name,
                category=category,
                unit=unit,
                expected_min=low,
                expected_max=high,
                is_circular=circular,
                aggregation_method=aggregation,
            )
        )
        print(f"[created] measurement type '{code}'")


def seed_data_sources():
    for code, name, source_type in [
        ("excel", "Excel workbook upload", "excel"),
        ("csv", "CSV file upload", "csv"),
        ("official_api", "Official monitoring API (future)", "official_api"),
    ]:
        if DataSource.query.filter_by(code=code).first():
            continue
        db.session.add(
            DataSource(code=code, name=name, source_type=source_type, is_active=(code != "official_api"))
        )
        print(f"[created] data source '{code}'")


def seed_reference_station():
    """Salacafe station — values taken directly from the project brief."""
    if Station.query.filter_by(station_code="06-02478").first():
        print("[skip] Salacafe station already exists")
        return
    db.session.add(
        Station(
            station_code="06-02478",
            name="Salacafe",
            site_name="DENRFMB-WATERSHED",
            description="Reference monitoring station used to develop and test the importer.",
            latitude=6.11582,
            longitude=124.846231,
            timezone="Asia/Manila",  # UTC+08:00
            measurement_interval_seconds=900,
            device_serial_number="929",
            operational_status="UNKNOWN",
        )
    )
    print("[created] station 06-02478 (Salacafe)")


def seed_settings(user):
    for key, value in DEFAULT_SETTINGS.items():
        if SystemSetting.query.filter_by(key=key).first():
            continue
        db.session.add(
            SystemSetting(
                key=key,
                value=value,
                category=key.split("_")[0],
                description=f"Default configuration for {key.replace('_', ' ')}.",
                updated_by_id=user.id if user else None,
            )
        )
        print(f"[created] setting '{key}'")


def ensure_core_data():
    """Insert the measurement-type catalogue and data sources if absent."""
    seed_measurement_types()
    seed_data_sources()
    db.session.commit()


def main():
    settings = get_settings(os.getenv("APP_ENV", "development"))
    db.init(settings)
    # create_all is only a convenience for a brand-new local database.
    # Production must use `alembic upgrade head` (real migrations).
    db.create_all()
    admin = seed_admin()
    seed_measurement_types()
    seed_data_sources()
    seed_reference_station()
    seed_settings(admin)
    db.session.commit()
    print("\nSeed complete.")
    print(f"Login with: {os.getenv('ADMIN_USERNAME', 'admin')} / "
          f"{os.getenv('ADMIN_PASSWORD', 'ChangeThisPassword123!')}")
    db.remove()


if __name__ == "__main__":
    main()
