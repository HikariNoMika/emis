"""Tests for password-protected station data clearing."""

from datetime import datetime, timezone

from app.extensions import db
from app.models import ImportBatch, Measurement, MeasurementType, Station, User
from app.utils.security import hash_password


def _setup(app):
    station = Station(station_code="CLEAR-001", name="Clear Station", timezone="UTC")
    db.session.add(station)
    db.session.commit()
    mtype = MeasurementType.query.filter_by(code="air_temperature").first()
    if not mtype:
        mtype = MeasurementType(
            code="air_temperature", name="Air temperature", category="ATMOSPHERIC",
            unit="degC", expected_min=-60, expected_max=80, aggregation_method="AVG",
        )
        db.session.add(mtype)
        db.session.commit()
    batch = ImportBatch(
        batch_number="CLR-1", station_id=station.id, original_filename="x.xlsx",
        stored_path="/tmp/x.xlsx", file_checksum="x", status="COMPLETED",
    )
    db.session.add(batch)
    db.session.flush()
    from app.models import Measurement as M
    db.session.add(M(
        station_id=station.id, measurement_type_id=mtype.id,
        observation_time=datetime(2026, 1, 1, tzinfo=timezone.utc), normalized_value=20,
        unit="degC", quality_status="VALID", import_batch_id=batch.id,
    ))
    db.session.commit()
    return station


def test_clear_requires_correct_password(client, auth_headers, app):
    station = _setup(app)
    url = f"/api/v1/stations/{station.id}/data"

    # Wrong password -> 403, nothing deleted.
    r = client.request("DELETE", url, headers=auth_headers, json={"password": "wrong"})
    assert r.status_code == 403
    assert Measurement.query.filter_by(station_id=station.id).count() == 1

    # Correct password -> data cleared, station kept.
    r = client.request(
        "DELETE", url, headers=auth_headers,
        json={"password": "Secret123!"},
    )
    assert r.status_code == 200, r.text
    assert Measurement.query.filter_by(station_id=station.id).count() == 0
    assert ImportBatch.query.filter_by(station_id=station.id).count() == 0
    assert db.session.get(Station, station.id) is not None
