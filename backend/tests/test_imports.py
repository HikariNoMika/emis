"""Tests for the Excel/CSV import workflow (Phase 3)."""

import io

from app.extensions import db
from app.integrations.normalizer import normalize_number
from app.integrations.timestamp_parser import parse_timestamp
from app.models import DataQualityFlag, ImportBatch, Measurement, RawImportRecord, Station
from create_sample_workbook import build_workbook


def _reference_station():
    station = Station(
        station_code="06-02478",
        name="Salacafe",
        site_name="DENRFMB-WATERSHED",
        timezone="Asia/Manila",
        device_serial_number="929",
    )
    db.session.add(station)
    db.session.commit()
    return station


def _upload(client, auth_headers, tmp_path, filename="sample.xlsx"):
    workbook_path = tmp_path / filename
    build_workbook(str(workbook_path))
    station = Station.query.first()
    form = {"station_id": str(station.id)} if station else {}
    with open(workbook_path, "rb") as handle:
        response = client.post(
            "/api/v1/imports/upload",
            files={"file": (filename, handle.read(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data=form,
            headers=auth_headers,
        )
    return response


def test_timestamp_and_number_helpers():
    parsed = parse_timestamp("2026-01-01 08:00:00", "Asia/Manila")
    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 0  # stored in UTC
    assert normalize_number("1,234.5") == 1234.5
    assert normalize_number("N/A") is None


def test_upload_inspects_and_preserves_raw_rows(client, auth_headers, tmp_path, app):
    _reference_station()
    response = _upload(client, auth_headers, tmp_path)
    assert response.status_code == 201, response.json()

    batch_id = response.json()["data"]["id"]
    with app.app_context():
        batch = db.session.get(ImportBatch, batch_id)
        assert batch.status == "INSPECTED"
        assert batch.total_rows == 12
        assert RawImportRecord.query.filter_by(import_batch_id=batch_id).count() == 12
        mapping = batch.column_mapping
        assert mapping["timestamp_column"] == "Timestamp"
        assert mapping["port_column"] == "Port"
        assert mapping["measurement_columns"]["Air Temperature (degC)"] == "air_temperature"
        assert mapping["measurement_columns"]["Relative Humidity (%)"] == "relative_humidity"
        assert mapping["station_id"] is not None


def test_preview_flags_suspicious_values(client, auth_headers, tmp_path):
    _reference_station()
    batch_id = _upload(client, auth_headers, tmp_path).json()["data"]["id"]

    response = client.get(f"/api/v1/imports/{batch_id}/preview", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()["data"]["rows"]
    assert len(rows) == 12

    all_values = [value for row in rows for value in row["values"]]
    humidity = [v for v in all_values if v["code"] == "relative_humidity"]
    assert any(v["quality_status"] == "SUSPECT" for v in humidity)

    soil = [v for v in all_values if v["code"] == "soil_water_content"]
    assert any(v["quality_status"] == "SUSPECT" for v in soil)


def test_process_import_creates_measurements_and_flags(client, auth_headers, tmp_path, app):
    _reference_station()
    batch_id = _upload(client, auth_headers, tmp_path).json()["data"]["id"]

    response = client.post(f"/api/v1/imports/{batch_id}/process", headers=auth_headers)
    assert response.status_code == 200, response.json()
    summary = response.json()["data"]["summary"]
    assert summary["imported_rows"] > 0

    with app.app_context():
        batch = db.session.get(ImportBatch, batch_id)
        assert batch.status == "COMPLETED"
        assert Measurement.query.count() == summary["imported_rows"]
        assert DataQualityFlag.query.count() > 0

        # Raw rows are still present and untouched.
        assert RawImportRecord.query.filter_by(import_batch_id=batch_id).count() == 12

    again = client.post(f"/api/v1/imports/{batch_id}/process", headers=auth_headers)
    assert again.status_code == 409


def test_duplicate_uploads_do_not_overwrite(client, auth_headers, tmp_path, app):
    _reference_station()
    first_id = _upload(client, auth_headers, tmp_path, "first.xlsx").json()["data"]["id"]
    client.post(f"/api/v1/imports/{first_id}/process", headers=auth_headers)

    with app.app_context():
        count_after_first = Measurement.query.count()

    second_id = _upload(client, auth_headers, tmp_path, "second.xlsx").json()["data"]["id"]
    preview = client.get(f"/api/v1/imports/{second_id}/preview", headers=auth_headers)
    assert any(
        value["is_duplicate"]
        for row in preview.json()["data"]["rows"]
        for value in row["values"]
    )

    client.post(f"/api/v1/imports/{second_id}/process", headers=auth_headers)
    with app.app_context():
        assert Measurement.query.count() == count_after_first


def test_unsupported_file_type_is_rejected(client, auth_headers, tmp_path):
    _reference_station()
    path = tmp_path / "notes.txt"
    path.write_text("not a monitoring file")
    with open(path, "rb") as handle:
        response = client.post(
            "/api/v1/imports/upload",
            files={"file": ("notes.txt", handle.read(), "text/plain")},
            headers=auth_headers,
        )
    assert response.status_code == 400
