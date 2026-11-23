"""
Step 5-11 of the import workflow: preview, validate and process.

CRITICAL DATA SAFETY RULES IMPLEMENTED HERE:
  1. Every source row already exists in raw_import_records before processing.
  2. Processing only INSERTS new measurements. It never updates or deletes them.
  3. A duplicate row is skipped and counted, never used to overwrite a reading.
  4. Questionable values are flagged separately; the original value is kept.
  5. A completed batch cannot be processed a second time.
"""

from app.extensions import db
from app.integrations.normalizer import normalize_number
from app.services.exceptions import ConflictError, ValidationAppError
from app.integrations.timestamp_parser import parse_timestamp
from app.models import (
    DataQualityFlag,
    Measurement,
    MeasurementType,
    RawImportRecord,
    Sensor,
    Station,
)
from app.utils.time import utcnow

from .validation import validate_value


def create_raw_records(batch, rows):
    """Store every source row as untouched JSONB (no filtering at this stage)."""
    for index, row in enumerate(rows, start=1):
        db.session.add(
            RawImportRecord(
                import_batch_id=batch.id,
                sheet_name=batch.column_mapping.get("sheet_name"),
                row_number=index,
                source_record_identifier=str(row.get("record_id") or index),
                raw_payload=row,
                observation_time=None,
            )
        )
    batch.total_rows = len(rows)


def _type_lookup():
    return {item.code: item for item in MeasurementType.query.all()}


def _existing_keys(station_id):
    """Preload duplicate keys: (sensor_id, type_id, aware observation_time).

    SQLite strips timezone information on read, so normalize stored times back
    to aware UTC before comparing them with freshly parsed timestamps.
    """
    from datetime import timezone

    keys = set()
    for item in Measurement.query.filter_by(station_id=station_id).all():
        observed = item.observation_time
        if observed is not None and observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        keys.add((item.sensor_id, item.measurement_type_id, observed))
    return keys


def _sensor_id_for_port(mapping, port_value):
    sensor_mapping = mapping.get("sensor_mapping") or {}
    if port_value is None:
        return None
    key = str(port_value).strip()
    sensor_id = sensor_mapping.get(key) or sensor_mapping.get(str(port_value))
    return int(sensor_id) if sensor_id else None


def _sensor_id_for_measurement(mapping, header):
    """Resolve the sensor from the port assigned to this spreadsheet column."""
    port = (mapping.get("measurement_ports") or {}).get(header)
    if port is None:
        return None
    return _sensor_id_for_port(mapping, port)


def _parsed_rows(batch, limit=None):
    """Yield parsed/validated information for each raw record."""
    mapping = batch.column_mapping or {}
    types = _type_lookup()
    station_id = mapping.get("station_id")
    timezone_name = mapping.get("timezone") or "Asia/Manila"
    timestamp_column = mapping.get("timestamp_column")
    port_column = mapping.get("port_column")
    measurement_columns = mapping.get("measurement_columns") or {}
    existing_keys = _existing_keys(station_id) if station_id else set()

    query = RawImportRecord.query.filter_by(import_batch_id=batch.id).order_by(
        RawImportRecord.row_number
    )
    if limit:
        query = query.limit(limit)

    results = []
    for record in query:
        payload = record.raw_payload or {}
        raw_timestamp = payload.get(timestamp_column) if timestamp_column else None
        observation_time = parse_timestamp(raw_timestamp, timezone_name)
        port_value = payload.get(port_column) if port_column else None
        sensor_id = _sensor_id_for_port(mapping, port_value)

        messages = []
        if timestamp_column and observation_time is None:
            messages.append(
                f"Invalid or missing timestamp in column '{timestamp_column}': {raw_timestamp!r}"
            )
        if not measurement_columns:
            messages.append("No measurement columns are mapped for this batch.")

        values = []
        for header, code in measurement_columns.items():
            measurement_type = types.get(code)
            if measurement_type is None:
                messages.append(f"Unknown measurement type '{code}' for column '{header}'.")
                continue

            raw_value = payload.get(header)
            number = normalize_number(raw_value)
            status, severity, explanation = validate_value(
                code,
                number,
                measurement_type.expected_min,
                measurement_type.expected_max,
            )
            if number is None:
                explanation = f"No numeric value in '{header}'. Raw value: {raw_value!r}"

            # A physical port may host a sensor producing several types, and two
            # columns of the same type may belong to different ports.
            measurement_sensor_id = _sensor_id_for_measurement(mapping, header) or sensor_id
            is_duplicate = False
            if observation_time and station_id:
                key = (measurement_sensor_id, measurement_type.id, observation_time)
                is_duplicate = key in existing_keys

            values.append(
                {
                    "header": header,
                    "sensor_id": measurement_sensor_id,
                    "measurement_type_id": measurement_type.id,
                    "code": code,
                    "raw_value": raw_value,
                    "normalized_value": number,
                    "unit": measurement_type.unit,
                    "quality_status": status,
                    "severity": severity,
                    "explanation": explanation,
                    "is_duplicate": is_duplicate,
                }
            )
            if is_duplicate:
                messages.append(
                    f"Duplicate: {code} already exists for this sensor at {observation_time}."
                )

        results.append(
            {
                "raw_record_id": record.id,
                "row_number": record.row_number,
                "raw_payload": payload,
                "observation_time": observation_time.isoformat() if observation_time else None,
                "port_value": port_value,
                "sensor_id": sensor_id,
                "values": values,
                "messages": messages,
                "has_error": observation_time is None or any(
                    value["quality_status"] == "INVALID" for value in values
                ),
                "is_processed": record.is_processed,
            }
        )
    return results


def build_preview(batch, limit=50):
    """Return validation results without changing any data."""
    mapping = batch.column_mapping or {}
    station = db.session.get(Station, mapping.get("station_id")) if mapping.get("station_id") else None
    rows = _parsed_rows(batch, limit=limit)
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "mapping": mapping,
        "station": {
            "id": station.id,
            "name": station.name,
            "station_code": station.station_code,
        } if station else None,
        "rows": rows,
        "row_count": len(rows),
        "total_rows": batch.total_rows,
        "warning_count": sum(len(row["messages"]) for row in rows),
    }


def _create_pending_flags(pending_flags, batch_id, station_id):
    """Create quality flags whose measurements have just been flushed."""
    for (
        measurement,
        sensor_id,
        type_id,
        observation_time,
        number,
        status,
        severity,
        explanation,
        expected_range,
        unit,
    ) in pending_flags:
        db.session.add(
            DataQualityFlag(
                station_id=station_id,
                sensor_id=sensor_id,
                measurement_type_id=type_id,
                measurement_id=measurement.id,
                import_batch_id=batch_id,
                observation_time=observation_time,
                original_value=number,
                unit=unit,
                rule_code=f"IMPORT_{status}",
                quality_status=status,
                severity=severity,
                expected_range=expected_range,
                actual_condition=str(number),
                explanation=explanation,
            )
        )


def execute_import(batch, user_id):
    """Insert validated measurements and quality flags, then summarize."""
    if batch.status == "COMPLETED":
        raise ConflictError("This import batch has already been processed.")

    mapping = batch.column_mapping or {}
    station_id = mapping.get("station_id")
    station = db.session.get(Station, station_id) if station_id else None
    if station is None:
        raise ValidationAppError(
            "No station is selected. Open the import, set the station in the "
            "mapping step, save it, then process."
        )
    if not mapping.get("timestamp_column"):
        raise ValidationAppError("No timestamp column is mapped for this import batch.")
    if not mapping.get("measurement_columns"):
        raise ValidationAppError("No measurement columns are mapped for this import batch.")

    batch.status = "PROCESSING"
    batch.started_at = utcnow()
    db.session.commit()

    imported = duplicates = errors = warnings = 0
    # Flush in batches instead of once per reading. A flush is a database
    # round-trip; doing one per row made large workbooks extremely slow.
    FLUSH_EVERY = 1000
    pending_flags = []
    existing_keys = _existing_keys(station_id)
    types = _type_lookup()
    timezone_name = mapping.get("timezone") or station.timezone or "Asia/Manila"
    timestamp_column = mapping["timestamp_column"]
    port_column = mapping.get("port_column")
    measurement_columns = mapping["measurement_columns"]

    records = (
        RawImportRecord.query.filter_by(import_batch_id=batch.id)
        .order_by(RawImportRecord.row_number)
        .all()
    )

    for record in records:
        payload = record.raw_payload or {}
        observation_time = parse_timestamp(
            payload.get(timestamp_column), timezone_name
        )
        port_value = payload.get(port_column) if port_column else None
        sensor_id = _sensor_id_for_port(mapping, port_value)

        if observation_time is None:
            errors += 1
            record.is_processed = True
            record.processing_note = "Skipped: invalid or missing observation timestamp."
            continue

        row_notes = []
        for header, code in measurement_columns.items():
            measurement_type = types.get(code)
            if measurement_type is None:
                continue

            raw_value = payload.get(header)
            number = normalize_number(raw_value)
            status, severity, explanation = validate_value(
                code,
                number,
                measurement_type.expected_min,
                measurement_type.expected_max,
            )
            if number is None:
                explanation = f"No numeric value in '{header}'. Raw value: {raw_value!r}"

            measurement_sensor_id = _sensor_id_for_measurement(mapping, header) or sensor_id
            key = (measurement_sensor_id, measurement_type.id, observation_time)
            if key in existing_keys:
                duplicates += 1
                row_notes.append(f"duplicate {code}")
                continue  # NEVER overwrite an existing reading

            measurement = Measurement(
                station_id=station_id,
                sensor_id=measurement_sensor_id,
                measurement_type_id=measurement_type.id,
                import_batch_id=batch.id,
                raw_import_record_id=record.id,
                observation_time=observation_time,
                original_value=number,
                original_text=None if raw_value is None else str(raw_value),
                normalized_value=number,
                unit=measurement_type.unit,
                quality_status=status,
                source_record_identifier=str(payload.get("record_id") or record.row_number),
            )
            db.session.add(measurement)
            existing_keys.add(key)
            imported += 1

            if status in {"SUSPECT", "INVALID", "MISSING"}:
                warnings += 1
                # Defer the flag: measurement.id is only available after a
                # flush, so build flags once a batch of measurements is flushed.
                pending_flags.append(
                    (
                        measurement,
                        measurement_sensor_id,
                        measurement_type.id,
                        observation_time,
                        number,
                        status,
                        severity,
                        explanation,
                        (
                            f"{measurement_type.expected_min} - {measurement_type.expected_max}"
                            if measurement_type.expected_min is not None
                            else None
                        ),
                        measurement_type.unit,
                    )
                )

            if imported % FLUSH_EVERY == 0:
                db.session.flush()
                _create_pending_flags(pending_flags, batch.id, station_id)
                pending_flags = []

        record.is_processed = True
        record.processing_note = (
            "; ".join(row_notes) if row_notes else "Processed successfully."
        )

    # Flush any remaining measurements and their flags.
    db.session.flush()
    _create_pending_flags(pending_flags, batch.id, station_id)
    pending_flags = []

    batch.imported_rows = imported
    batch.duplicate_rows = duplicates
    batch.error_count = errors
    batch.warning_count = warnings
    batch.status = "COMPLETED"
    batch.completed_at = utcnow()
    db.session.commit()

    # Keep station health in sync with the freshly imported readings. A failure
    # here must not fail or roll back an otherwise successful import.
    try:
        from app.services.health_service import refresh_all
        refresh_all()
    except Exception:  # pragma: no cover - defensive
        db.session.rollback()

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "imported_rows": imported,
        "duplicate_rows": duplicates,
        "error_rows": errors,
        "quality_flags_created": warnings,
    }
