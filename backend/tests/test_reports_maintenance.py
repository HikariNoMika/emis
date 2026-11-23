"""Tests for reports, maintenance and settings (Phase 6)."""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Measurement, MeasurementType, Station
from tests.conftest import ensure_type


def _setup():
    station = Station(station_code="RPT-001", name="Report Station", timezone="Asia/Manila")
    temperature = ensure_type(
        code="air_temperature", name="Air temperature",
        category="ATMOSPHERIC", unit="degC",
    )
    db.session.add_all([station, temperature])
    db.session.commit()
    db.session.add(
        Measurement(
            station_id=station.id,
            measurement_type_id=temperature.id,
            observation_time=datetime.now(timezone.utc) - timedelta(hours=1),
            normalized_value=24.5,
            unit="degC",
            quality_status="VALID",
        )
    )
    db.session.commit()
    return station, temperature


def test_generate_pdf_report_and_download(client, auth_headers, app):
    station, temperature = _setup()
    response = client.post(
        "/api/v1/reports/generate",
        json={
            "report_type": "daily",
            "station_id": station.id,
            "measurement_type_ids": [temperature.id],
            "file_format": "pdf",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.json()
    report = response.json()["data"]

    listing = client.get("/api/v1/reports", headers=auth_headers)
    assert listing.json()["meta"]["total"] == 1

    download = client.get(f"/api/v1/reports/{report['id']}/download", headers=auth_headers)
    assert download.status_code == 200
    assert download.content[:4] == b"%PDF"


def test_generate_excel_report(client, auth_headers, app):
    station, temperature = _setup()
    response = client.post(
        "/api/v1/reports/generate",
        json={
            "report_type": "weekly",
            "station_id": station.id,
            "file_format": "xlsx",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    report = response.json()["data"]
    download = client.get(f"/api/v1/reports/{report['id']}/download", headers=auth_headers)
    assert download.content[:2] == b"PK"


def test_maintenance_crud(client, auth_headers, app):
    station = Station(station_code="MNT-001", name="Maintenance Station", timezone="Asia/Manila")
    db.session.add(station)
    db.session.commit()

    payload = {
        "station_id": station.id,
        "maintenance_type": "CALIBRATION",
        "maintenance_date": "2026-02-01",
        "performed_by": "Technician A",
        "description": "Annual calibration",
        "next_maintenance_date": "2027-02-01",
    }
    created = client.post("/api/v1/maintenance", json=payload, headers=auth_headers)
    assert created.status_code == 201, created.json()
    record_id = created.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/maintenance/{record_id}",
        json={"findings": "Sensor stable"},
        headers=auth_headers,
    )
    assert updated.json()["data"]["findings"] == "Sensor stable"

    calendar = client.get("/api/v1/maintenance/calendar", headers=auth_headers)
    assert calendar.status_code == 200
    assert len(calendar.json()["data"]["upcoming"]) == 1

    deleted = client.delete(f"/api/v1/maintenance/{record_id}", headers=auth_headers)
    assert deleted.status_code == 200
