"""Tests for the one-sheet source export with zero-filled gaps."""

import io

from openpyxl import load_workbook

from app.extensions import db
from app.models import ImportBatch, RawImportRecord, Station
from app.services.measurement_service import export_source_xlsx


def test_source_export_merges_batches_and_fills_gaps(app):
    station = Station(
        station_code="EXPORT-001", name="Export Station", timezone="UTC",
        measurement_interval_seconds=900,
    )
    db.session.add(station)
    db.session.commit()

    batch1 = ImportBatch(
        batch_number="EXP-1", station_id=station.id, original_filename="a.xlsx",
        stored_path="/tmp/a.xlsx", file_checksum="x", file_size_bytes=10, status="COMPLETED",
    )
    batch2 = ImportBatch(
        batch_number="EXP-2", station_id=station.id, original_filename="b.xlsx",
        stored_path="/tmp/b.xlsx", file_checksum="y", file_size_bytes=10, status="COMPLETED",
    )
    db.session.add_all([batch1, batch2])
    db.session.commit()

    def add_record(batch, row_number, payload):
        db.session.add(RawImportRecord(
            import_batch_id=batch.id, row_number=row_number,
            raw_payload=payload, is_processed=True,
        ))

    # Two batches with a 45-minute gap between 10:00 and 10:45 (15-min interval).
    add_record(batch1, 1, {"Timestamps": "2026-01-01T09:45:00", "°C Air Temperature": 20})
    add_record(batch1, 2, {"Timestamps": "2026-01-01T10:00:00", "°C Air Temperature": 21})
    add_record(batch2, 1, {"Timestamps": "2026-01-01T10:45:00", "°C Air Temperature": 22})
    db.session.commit()

    content = export_source_xlsx(station.id)
    workbook = load_workbook(io.BytesIO(content))

    # ONE sheet, not one per batch.
    assert workbook.sheetnames == ["source"]
    sheet = workbook["source"]
    rows = list(sheet.values)
    header = rows[0]
    assert header[0] == "Timestamps"
    assert "°C Air Temperature" in header

    timestamps = [row[0] for row in rows[1:]]
    # 3 real rows + 2 gap rows (10:15 and 10:30) = 5.
    assert len(timestamps) == 5
    assert timestamps == sorted(timestamps)
    assert "2026-01-01T10:15:00" in timestamps
    assert "2026-01-01T10:30:00" in timestamps

    temp_index = header.index("°C Air Temperature")
    gap_rows = [row for row in rows[1:] if row[0] in ("2026-01-01T10:15:00", "2026-01-01T10:30:00")]
    assert all(row[temp_index] == 0 for row in gap_rows)
    real_rows = [row for row in rows[1:] if row[0] not in ("2026-01-01T10:15:00", "2026-01-01T10:30:00")]
    assert sorted(row[temp_index] for row in real_rows) == [20, 21, 22]
