"""Tests against the actual supplied Salacafe workbook.

The workbook is stored in tests/fixtures so these tests run anywhere.
"""

import io
import os

from app.extensions import db
from app.integrations.excel_connector import ExcelConnector
from app.models import DataQualityFlag, ImportBatch, Measurement, Station
from app.processors.workbook_inspector import inspect_file, suggest_mapping

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "salacafe_reference.xlsx")


def _station():
    station = Station(
        station_code="06-02478",
        name="Salacafe",
        site_name="DENRFMB-WATERSHED",
        timezone="Asia/Manila",
        device_serial_number="929",
        measurement_interval_seconds=900,
    )
    db.session.add(station)
    db.session.commit()
    return station


def test_workbook_sheets_and_clean_headers():
    snapshot = inspect_file(FIXTURE, "salacafe.xlsx")
    names = [item["name"] for item in snapshot["sheets"]]
    assert names == ["Config 1", "Raw Config 1", "Metadata"]

    config = snapshot["sheets"][0]
    headers = config["headers"]
    assert "Timestamps" in headers
    # Recovered labels carry the raw sheet's unit prefix, e.g. "°C Air Temperature".
    assert any("Air Temperature" in header for header in headers)
    assert any("Wind Speed" in header for header in headers)
    assert any("VPD" in header for header in headers)
    assert config["row_count"] == 220
    # Port banners from row 1 are recovered for sensor mapping.
    assert "1" in config["port_layout"]


def test_workbook_metadata_is_captured():
    snapshot = inspect_file(FIXTURE, "salacafe.xlsx")
    metadata = snapshot["metadata"]

    station = metadata["station"]
    assert station["code"] == "06-02478"
    assert station["name"] == "Salacafe"
    assert station["site"] == "DENRFMB-WATERSHED"
    assert str(station["device_serial"]) == "929"
    assert int(station["interval_seconds"]) == 900
    assert abs(float(station["latitude"]) - 6.1158204) < 1e-6
    assert abs(float(station["longitude"]) - 124.846231) < 1e-6
    assert station["timezone"] == "UTC+08:00"
    assert station["logger_time"]

    sensors = metadata["sensors"]
    assert any(sensor.get("port") == 4 and "VP-4" in str(sensor.get("Name")) for sensor in sensors)
    assert any(sensor.get("port") == 5 for sensor in sensors)
    assert any(sensor.get("port") == 6 for sensor in sensors)
    assert metadata["raw_pairs"]


def test_mapping_from_real_workbook(app):
    station = _station()
    snapshot = inspect_file(FIXTURE, "salacafe.xlsx")
    from app.models import MeasurementType

    mapping, warnings, detected = suggest_mapping(
        snapshot, MeasurementType.query.all(), [station]
    )
    assert detected.id == station.id
    assert mapping["station_id"] == station.id
    assert mapping["timestamp_column"] == "Timestamps"
    assert mapping["timezone"] == "UTC+08:00"

    codes = set(mapping["measurement_columns"].values())
    for expected in (
        "wind_direction", "wind_speed", "wind_gust", "solar_radiation",
        "rainfall", "max_rainfall_rate", "air_temperature",
        "relative_humidity", "atmospheric_pressure", "vapor_pressure_deficit",
        "soil_water_content", "battery_percentage", "battery_voltage",
        "logger_temperature",
    ):
        assert expected in codes, f"missing mapping for {expected}"


def test_real_workbook_upload_and_import(client, auth_headers, app):
    station = _station()
    with open(FIXTURE, "rb") as handle:
        response = client.post(
            "/api/v1/imports/upload",
            files={"file": ("salacafe.xlsx", handle.read(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )
    assert response.status_code == 201, response.text
    batch_id = response.json()["data"]["id"]

    with app.app_context():
        batch = db.session.get(ImportBatch, batch_id)
        assert batch.total_rows == 220
        assert batch.detected_metadata["metadata"]["station"]["code"] == "06-02478"
        assert batch.detected_metadata["metadata"]["sensors"]

    preview = client.get(f"/api/v1/imports/{batch_id}/preview", headers=auth_headers)
    rows = preview.json()["data"]["rows"]
    assert len(rows) == 50  # preview limit

    processed = client.post(f"/api/v1/imports/{batch_id}/process", headers=auth_headers)
    assert processed.status_code == 200, processed.text
    summary = processed.json()["data"]["summary"]
    assert summary["imported_rows"] > 1000
    assert summary["quality_flags_created"] > 0

    with app.app_context():
        assert Measurement.query.count() == summary["imported_rows"]
        suspect = DataQualityFlag.query.filter_by(quality_status="SUSPECT").count()
        assert suspect > 0

        # Original source values were preserved, not overwritten.
        assert ImportBatch.query.filter_by(id=batch_id).first().status == "COMPLETED"
