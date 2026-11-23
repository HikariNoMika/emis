"""Tests for station CRUD, archiving and related records (Phase 2)."""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Measurement, MeasurementType, Station
from tests.conftest import ensure_type


def _station_payload(code="STA-001"):
    return {
        "station_code": code,
        "name": "Test Station",
        "site_name": "Test Watershed",
        "latitude": 6.11582,
        "longitude": 124.846231,
        "timezone": "Asia/Manila",
        "measurement_interval_seconds": 900,
        "operational_status": "ONLINE",
    }


def test_create_and_list_station(client, auth_headers):
    response = client.post(
        "/api/v1/stations", json=_station_payload(), headers=auth_headers
    )
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["station_code"] == "STA-001"

    listing = client.get("/api/v1/stations", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 1


def test_duplicate_station_code_is_rejected(client, auth_headers):
    client.post("/api/v1/stations", json=_station_payload(), headers=auth_headers)
    duplicate = client.post(
        "/api/v1/stations", json=_station_payload(), headers=auth_headers
    )
    assert duplicate.status_code == 409


def test_get_update_and_archive_station(client, auth_headers):
    created = client.post(
        "/api/v1/stations", json=_station_payload(), headers=auth_headers
    )
    station_id = created.json()["data"]["id"]

    detail = client.get(f"/api/v1/stations/{station_id}", headers=auth_headers)
    assert detail.json()["data"]["sensor_count"] == 0

    updated = client.put(
        f"/api/v1/stations/{station_id}",
        json={"name": "Renamed Station"},
        headers=auth_headers,
    )
    assert updated.json()["data"]["name"] == "Renamed Station"

    archived = client.delete(
        f"/api/v1/stations/{station_id}", headers=auth_headers
    )
    assert archived.status_code == 200

    active = client.get("/api/v1/stations", headers=auth_headers)
    assert active.json()["meta"]["total"] == 0

    archived_list = client.get(
        "/api/v1/stations?is_archived=true", headers=auth_headers
    )
    assert archived_list.json()["meta"]["total"] == 1


def test_archiving_station_preserves_measurements(client, auth_headers, app):
    station = Station(station_code="KEEP-001", name="Keep Data", timezone="Asia/Manila")
    measurement_type = ensure_type(
        code="air_temperature", name="Air temperature",
        category="ATMOSPHERIC", unit="degC",
    )
    db.session.add_all([station, measurement_type])
    db.session.commit()

    db.session.add(
        Measurement(
            station_id=station.id,
            measurement_type_id=measurement_type.id,
            observation_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            normalized_value=25.5,
            unit="degC",
        )
    )
    db.session.commit()
    before = Measurement.query.count()

    response = client.delete(f"/api/v1/stations/{station.id}", headers=auth_headers)
    assert response.status_code == 200
    assert Measurement.query.count() == before

    # The endpoint ran in a worker thread; refresh this thread's identity map.
    db.session.expire_all()
    archived_station = db.session.get(Station, station.id)
    assert archived_station.is_archived is True


def test_station_validation_error(client, auth_headers):
    response = client.post(
        "/api/v1/stations",
        json={"name": "Missing code"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "errors" in response.json()


def test_map_data_returns_all_active_stations(client, auth_headers):
    client.post("/api/v1/stations", json=_station_payload("MAP-001"), headers=auth_headers)
    response = client.get("/api/v1/stations/map-data", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["station_code"] == "MAP-001"


def test_stations_require_authentication(client):
    response = client.get("/api/v1/stations")
    assert response.status_code == 401
