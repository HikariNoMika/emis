"""Tests for destination/source types on stations and imports."""

from app.extensions import db
from app.models import ImportBatch, Station
from app.services import import_service


def test_station_from_metadata_uses_destination_type(app):
    metadata = {
        "station": {"code": "TYPE-001", "name": "Water Site", "timezone": "Asia/Manila"},
        "sensors": [{"port": 1, "Name": "Level"}],
    }
    station = import_service.station_from_metadata(metadata, station_type="AWLS")
    assert station.station_type == "AWLS"
    assert len(station.sensors) == 1


def test_update_mapping_retags_station(app):
    station = Station(station_code="TYPE-002", name="Site", station_type="AWS")
    db.session.add(station)
    db.session.commit()
    batch = ImportBatch(
        batch_number="TYPE-B", station_id=station.id, original_filename="x.csv",
        stored_path="/tmp/x.csv", file_checksum="x", status="PREVIEWED",
    )
    db.session.add(batch)
    db.session.commit()

    import_service.update_mapping(
        batch,
        {"station_id": station.id, "station_type": "AWLS"},
        user_id=None,
    )
    assert db.session.get(Station, station.id).station_type == "AWLS"
    assert batch.column_mapping["station_type"] == "AWLS"


def test_invalid_station_type_rejected(app):
    station = Station(station_code="TYPE-003", name="Site", station_type="AWS")
    db.session.add(station)
    db.session.commit()
    batch = ImportBatch(
        batch_number="TYPE-C", station_id=station.id, original_filename="x.csv",
        stored_path="/tmp/y.csv", file_checksum="y", status="PREVIEWED",
    )
    db.session.add(batch)
    db.session.commit()
    import pytest
    from app.services.exceptions import ValidationAppError
    with pytest.raises(ValidationAppError):
        import_service.update_mapping(batch, {"station_type": "NOPE"}, user_id=None)
