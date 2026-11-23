"""Tests for data quality, alerts and health monitoring (Phase 5)."""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (
    Alert,
    DataQualityFlag,
    Measurement,
    MeasurementType,
    Station,
)
from tests.conftest import ensure_type


def _setup_station():
    station = Station(station_code="HLTH-001", name="Health Station", timezone="Asia/Manila")
    temperature = ensure_type(
        code="air_temperature", name="Air temperature",
        category="ATMOSPHERIC", unit="degC",
    )
    battery = ensure_type(
        code="battery_percentage", name="Battery percentage",
        category="EQUIPMENT", unit="%",
    )
    db.session.add_all([station, temperature, battery])
    db.session.commit()
    return station, temperature, battery


def test_quality_summary_and_resolution(client, auth_headers, app):
    station, _temperature, _battery = _setup_station()
    flag = DataQualityFlag(
        station_id=station.id,
        rule_code="IMPORT_SUSPECT",
        quality_status="SUSPECT",
        severity="WARNING",
        original_value=105,
        explanation="Humidity above 100%.",
    )
    db.session.add(flag)
    db.session.commit()

    summary = client.get("/api/v1/data-quality/summary", headers=auth_headers)
    assert summary.json()["data"]["open_flags"] == 1

    response = client.post(
        f"/api/v1/data-quality/flags/{flag.id}/resolve",
        json={"resolution_status": "RESOLVED", "admin_remarks": "Verified by technician."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["resolution_status"] == "RESOLVED"

    summary_after = client.get("/api/v1/data-quality/summary", headers=auth_headers)
    assert summary_after.json()["data"]["open_flags"] == 0


def test_alert_deduplication_and_lifecycle(client, auth_headers, app):
    from app.services import alert_service

    alert_service.raise_alert("BATTERY", "WARNING", "Low battery", "Battery 25%",
                              "LOW_BATTERY:1", 1)
    alert_service.raise_alert("BATTERY", "WARNING", "Low battery", "Battery 24%",
                              "LOW_BATTERY:1", 1)
    assert Alert.query.filter_by(condition_key="LOW_BATTERY:1").count() == 1

    alert = Alert.query.first()
    acknowledged = client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge", json={"remarks": "Seen"},
        headers=auth_headers,
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["status"] == "ACKNOWLEDGED"

    resolved = client.post(
        f"/api/v1/alerts/{alert.id}/resolve", json={"remarks": "Battery replaced"},
        headers=auth_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "RESOLVED"

    history = client.get(f"/api/v1/alerts/{alert.id}/history", headers=auth_headers)
    assert len(history.json()["data"]) == 3


def test_health_refresh_creates_snapshot_and_alerts(client, auth_headers, app):
    station, temperature, battery = _setup_station()
    old_time = datetime.now(timezone.utc) - timedelta(hours=3)

    db.session.add(
        Measurement(
            station_id=station.id,
            measurement_type_id=temperature.id,
            observation_time=old_time,
            normalized_value=25,
            unit="degC",
        )
    )
    db.session.add(
        Measurement(
            station_id=station.id,
            measurement_type_id=battery.id,
            observation_time=old_time,
            normalized_value=10,
            unit="%",
        )
    )
    db.session.commit()

    response = client.post("/api/v1/health/refresh", headers=auth_headers)
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data[0]["status"] == "OFFLINE"  # stale data, not equipment state
    assert data[0]["connectivity_state"] == "NOT_REPORTED"
    assert data[0]["battery_percentage"] == 10

    alerts = client.get("/api/v1/alerts?status=ACTIVE", headers=auth_headers)
    condition_keys = {item["condition_key"] for item in alerts.json()["data"]}
    assert f"LOW_BATTERY:{station.id}" in condition_keys
    assert f"MISSING_DATA:{station.id}" in condition_keys
