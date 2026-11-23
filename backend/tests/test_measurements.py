"""Tests for trends, statistics, comparison and export (Phase 4)."""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Measurement, MeasurementType, Station
from tests.conftest import ensure_type


def _setup(app, code="TREND-001"):
    station = Station(station_code=code, name="Trend Station", timezone="Asia/Manila",
                      measurement_interval_seconds=900)
    temperature = ensure_type(
        code="air_temperature", name="Air temperature", category="ATMOSPHERIC",
        unit="degC", expected_min=-60, expected_max=80, aggregation_method="AVG",
    )
    direction = ensure_type(
        code="wind_direction", name="Wind direction", category="WIND",
        unit="deg", expected_min=0, expected_max=360,
        is_circular=True, aggregation_method="CIRCULAR_MEAN",
    )
    db.session.add_all([station, temperature, direction])
    db.session.commit()

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(4):
        moment = start + timedelta(minutes=15 * index)
        db.session.add(
            Measurement(
                station_id=station.id,
                measurement_type_id=temperature.id,
                observation_time=moment,
                normalized_value=20 + index,
                unit="degC",
                quality_status="VALID",
            )
        )
    # Circular values 350 and 10 should average to 0, not 180.
    for index, angle in enumerate([350, 10]):
        db.session.add(
            Measurement(
                station_id=station.id,
                measurement_type_id=direction.id,
                observation_time=start + timedelta(minutes=15 * index),
                normalized_value=angle,
                unit="deg",
                quality_status="VALID",
            )
        )
    db.session.commit()
    return station, temperature, direction, start


def test_latest_measurements(client, auth_headers, app):
    _setup(app)
    response = client.get("/api/v1/measurements/latest", headers=auth_headers)
    assert response.status_code == 200
    codes = {item["measurement_type_id"] for item in response.json()["data"]}
    assert len(codes) == 2


def test_trends_group_by_bucket(client, auth_headers, app):
    station, temperature, _direction, start = _setup(app)
    end = start + timedelta(hours=2)
    response = client.get(
        "/api/v1/measurements/trends",
        params={
            "station_id": station.id,
            "measurement_type_ids": str(temperature.id),
            "interval_minutes": 60,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.json()
    series = response.json()["data"][0]
    assert series["code"] == "air_temperature"
    assert len(series["points"]) == 1  # four readings inside one hourly bucket
    assert series["points"][0]["value"] == 21.5  # average of 20,21,22,23


def test_statistics_and_circular_mean(client, auth_headers, app):
    station, temperature, direction, start = _setup(app)
    end = start + timedelta(hours=2)

    response = client.get(
        "/api/v1/measurements/statistics",
        params={
            "station_id": station.id,
            "measurement_type_id": temperature.id,
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
        },
        headers=auth_headers,
    )
    stats = response.json()["data"]
    assert stats["min"] == 20
    assert stats["max"] == 23
    assert stats["average"] == 21.5
    assert stats["observations"] == 4

    circular = client.get(
        "/api/v1/measurements/statistics",
        params={"measurement_type_id": direction.id, "station_id": station.id},
        headers=auth_headers,
    ).json()["data"]
    assert circular["circular_mean"] in (0, 360, 359.9999)


def test_comparison_uses_same_type(client, auth_headers, app):
    station_a, temperature, _d, _start = _setup(app, "CMP-A")
    _setup(app, "CMP-B")
    response = client.get(
        "/api/v1/analytics/comparison",
        params={
            "station_ids": [station_a.id, 999],
            "measurement_type_id": temperature.id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["stations"]) == 2


def test_flexible_two_period_comparison(client, auth_headers, app):
    station, temperature, _direction, start = _setup(app)
    # A second, later period with different values.
    later = start + timedelta(hours=3)
    for index in range(4):
        db.session.add(
            Measurement(
                station_id=station.id,
                measurement_type_id=temperature.id,
                observation_time=later + timedelta(minutes=15 * index),
                normalized_value=30 + index,
                unit="degC",
                quality_status="VALID",
            )
        )
    db.session.commit()

    response = client.get(
        "/api/v1/measurements/compare-flexible",
        params={
            "station_id": station.id,
            "measurement_type_id": temperature.id,
            "date_from_a": start.isoformat(),
            "date_to_a": (start + timedelta(hours=1)).isoformat(),
            "date_from_b": later.isoformat(),
            "date_to_b": (later + timedelta(hours=1)).isoformat(),
            "interval_minutes": 60,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["period_a"]["points"][0]["offset_hours"] == 0
    assert data["period_a"]["points"][0]["value"] == 21.5
    assert data["period_b"]["points"][0]["value"] == 31.5
    assert data["period_a"]["observations"] == 4
    assert data["period_b"]["observations"] == 4


def test_export_csv_and_xlsx(client, auth_headers, app):
    _setup(app)
    csv_response = client.get("/api/v1/measurements/export?format=csv", headers=auth_headers)
    assert csv_response.status_code == 200
    assert b"observation_time_utc" in csv_response.content

    xlsx_response = client.get("/api/v1/measurements/export?format=xlsx", headers=auth_headers)
    assert xlsx_response.status_code == 200
    assert xlsx_response.content[:2] == b"PK"  # zip signature of an .xlsx file
