"""Tests for sensor CRUD, measurement-type links and health (Phase 2)."""

from app.extensions import db
from app.models import MeasurementType, Sensor, Station
from tests.conftest import ensure_type


def _setup_station():
    station = Station(station_code="SEN-001", name="Sensor Station", timezone="Asia/Manila")
    db.session.add(station)
    db.session.commit()
    return station


def _setup_types():
    types = [
        ensure_type(code="air_temperature", name="Air temperature",
                        category="ATMOSPHERIC", unit="degC"),
        ensure_type(code="relative_humidity", name="Relative humidity",
                        category="ATMOSPHERIC", unit="%"),
    ]
    db.session.add_all(types)
    db.session.commit()
    return types


def test_create_and_update_sensor(client, auth_headers, app):
    station = _setup_station()

    response = client.post(
        "/api/v1/sensors",
        json={
            "station_id": station.id,
            "port_number": "1",
            "name": "VP-4 Weather Sensor",
            "model": "VP-4",
            "manufacturer": "Test Maker",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.json()
    sensor_id = response.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/sensors/{sensor_id}",
        json={"operational_status": "MAINTENANCE"},
        headers=auth_headers,
    )
    assert updated.json()["data"]["operational_status"] == "MAINTENANCE"
    assert db.session.get(Sensor, sensor_id).station_id == station.id


def test_sensor_measurement_type_links(client, auth_headers, app):
    station = _setup_station()
    types = _setup_types()

    sensor_response = client.post(
        "/api/v1/sensors",
        json={"station_id": station.id, "name": "Multi-parameter sensor"},
        headers=auth_headers,
    )
    sensor_id = sensor_response.json()["data"]["id"]

    link_response = client.put(
        f"/api/v1/sensors/{sensor_id}/measurement-types",
        json={
            "measurement_type_ids": [types[0].id, types[1].id],
            "column_hints": {str(types[0].id): "Air Temp (degC)"},
        },
        headers=auth_headers,
    )
    assert link_response.status_code == 200
    data = link_response.json()["data"]
    assert len(data["measurement_types"]) == 2
    hints = {item["code"]: item["column_hint"] for item in data["measurement_types"]}
    assert hints["air_temperature"] == "Air Temp (degC)"


def test_sensor_health_without_measurements(client, auth_headers, app):
    station = _setup_station()
    sensor_response = client.post(
        "/api/v1/sensors",
        json={"station_id": station.id, "name": "Battery sensor"},
        headers=auth_headers,
    )
    sensor_id = sensor_response.json()["data"]["id"]

    health = client.get(f"/api/v1/sensors/{sensor_id}/health", headers=auth_headers)
    assert health.status_code == 200
    data = health.json()["data"]
    assert data["latest_observation_time"] is None
    assert data["connectivity_state"] == "NOT_REPORTED"
    assert data["measurement_count"] == 0


def test_sensor_requires_existing_station(client, auth_headers):
    response = client.post(
        "/api/v1/sensors",
        json={"station_id": 99999, "name": "Orphan sensor"},
        headers=auth_headers,
    )
    assert response.status_code == 400
