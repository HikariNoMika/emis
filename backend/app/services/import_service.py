"""Import workflow orchestration (upload -> inspect -> preview -> process)."""

import hashlib
import os
import uuid

from app.config import get_settings
from app.extensions import db
from app.models import ImportBatch, MeasurementType, Sensor, Station
from app.processors.import_processor import build_preview, create_raw_records, execute_import
from app.processors.workbook_inspector import get_connector, inspect_file, suggest_mapping
from app.utils.serializers import import_batch_to_dict

from .audit_service import log_action
from .exceptions import ConflictError, ValidationAppError

# Files larger than this are processed by a Celery worker instead of in the
# web request. The value is intentionally conservative.
BACKGROUND_THRESHOLD_BYTES = 2 * 1024 * 1024  # 2 MB


def _checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_float(value):
    """Best-effort numeric conversion for metadata coordinates/intervals."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def station_from_metadata(metadata, uploaded_by_id=None):
    """Create a station (and its sensors) from a workbook's Metadata sheet.

    Called when the file's station code does not match any existing station.
    Reuses an existing station with the same code (including archived ones) so
    re-uploading a file never creates duplicates. Only metadata actually present
    in the workbook is used — no values are invented.
    """
    meta = (metadata or {}).get("station") or {}
    code = str(meta.get("code") or "").strip()
    if not code:
        return None

    existing = Station.query.filter_by(station_code=code).first()
    if existing:
        return existing

    interval = _as_float(meta.get("interval_seconds"))
    station = Station(
        station_code=code[:50],
        name=str(meta.get("name") or meta.get("site") or code).strip()[:150],
        site_name=(str(meta.get("site")).strip()[:150] or None) if meta.get("site") else None,
        latitude=_as_float(meta.get("latitude")),
        longitude=_as_float(meta.get("longitude")),
        elevation=_as_float(meta.get("altitude")),
        timezone=str(meta.get("timezone") or "Asia/Manila")[:64],
        measurement_interval_seconds=int(interval) if interval and interval > 0 else 900,
        device_serial_number=(
            str(meta.get("device_serial")).strip()[:100] or None
        ) if meta.get("device_serial") else None,
        operational_status="UNKNOWN",
    )
    db.session.add(station)
    db.session.flush()

    for item in (metadata or {}).get("sensors") or []:
        port = item.get("port")
        if port is None:
            continue
        sensor = Sensor(
            station_id=station.id,
            port_number=str(port)[:20],
            name=str(item.get("Name") or item.get("name") or f"Port {port}")[:150],
            serial_number=(
                str(item.get("Serial Number")).strip()[:100] or None
            ) if item.get("Serial Number") else None,
        )
        db.session.add(sensor)

    db.session.flush()
    log_action(
        "STATION_AUTO_CREATED",
        "stations",
        record_identifier=station.station_code,
        new_values={"source": "workbook metadata", "station_code": station.station_code},
        user_id=uploaded_by_id,
        commit=False,
    )
    return station


def upload(file_storage, uploaded_by_id, station_id=None, sheet_name=None):
    """Steps 1-4: save, inspect, detect metadata and preserve raw rows."""
    original_filename = file_storage.filename or ""
    extension = os.path.splitext(original_filename)[1].lower()
    settings = get_settings()
    allowed = settings.ALLOWED_IMPORT_EXTENSIONS
    if extension not in allowed:
        raise ValidationAppError(
            f"Unsupported file type '{extension}'. Allowed: {', '.join(sorted(allowed))}."
        )

    upload_folder = settings.UPLOAD_FOLDER
    os.makedirs(upload_folder, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = os.path.join(upload_folder, stored_name)
    file_storage.save(stored_path)

    data_source_code = "csv" if extension == ".csv" else "excel"
    from app.models import DataSource

    source = DataSource.query.filter_by(code=data_source_code).first()

    batch = ImportBatch(
        batch_number=f"IMP-{uuid.uuid4().hex[:12].upper()}",
        data_source_id=source.id if source else None,
        station_id=station_id,
        original_filename=original_filename,
        stored_path=stored_path,
        file_checksum=_checksum(stored_path),
        file_size_bytes=os.path.getsize(stored_path),
        status="UPLOADING",
        uploaded_by_id=uploaded_by_id,
    )
    db.session.add(batch)
    db.session.flush()

    try:
        snapshot = inspect_file(stored_path, original_filename)
        measurement_types = MeasurementType.query.all()
        stations = Station.query.filter_by(is_archived=False).all()
        mapping, warnings, detected_station = suggest_mapping(
            snapshot, measurement_types, stations, explicit_sheet=sheet_name
        )

        # An explicit selection from the upload form wins over auto-detection.
        if station_id is not None:
            if db.session.get(Station, station_id) is None:
                raise ValidationAppError(f"Station {station_id} does not exist.")
            mapping["station_id"] = station_id
            selected = db.session.get(Station, station_id)
            if not mapping.get("timezone"):
                mapping["timezone"] = selected.timezone
        elif detected_station:
            batch.station_id = detected_station.id
        else:
            # No existing station matched. Create it from the workbook's own
            # Metadata sheet so the administrator does not have to type it in.
            auto_station = station_from_metadata(
                snapshot.get("metadata", {}), uploaded_by_id
            )
            if auto_station:
                mapping["station_id"] = auto_station.id
                batch.station_id = auto_station.id
                warnings.append(
                    f"Station {auto_station.station_code} was created automatically "
                    "from the workbook metadata."
                )

        # Reuse the station's existing sensors by port number. This is essential
        # for duplicate detection: the same file must resolve to the same
        # (sensor_id, type, timestamp) key on every upload.
        active_station_id = mapping.get("station_id") or batch.station_id
        if active_station_id and not mapping.get("sensor_mapping"):
            existing_sensors = Sensor.query.filter_by(
                station_id=active_station_id
            ).all()
            mapping["sensor_mapping"] = {
                str(sensor.port_number): sensor.id
                for sensor in existing_sensors
                if sensor.port_number
            }

        sheet = next(
            (item for item in snapshot["sheets"]
             if item["name"] == mapping.get("sheet_name")),
            None,
        )
        rows = sheet["preview_rows"] if sheet else []
        if sheet and sheet["row_count"] > len(sheet["preview_rows"]):
            # The preview only keeps 50 rows. Re-read the full sheet now so all
            # source rows are preserved before any processing happens.
            connector = get_connector(original_filename)
            _headers, rows = connector.read_rows(stored_path, sheet["name"])

        create_raw_records(batch, rows)
        batch.sheet_names = [item["name"] for item in snapshot["sheets"]]
        batch.detected_metadata = {
            "metadata": snapshot.get("metadata", {}),
            "metadata_text": snapshot.get("metadata_text", [])[:100],
        }
        batch.column_mapping = mapping
        batch.warnings = warnings
        batch.warning_count = len(warnings)
        batch.status = "INSPECTED"

        log_action(
            "IMPORT_UPLOADED",
            "imports",
            record_identifier=batch.batch_number,
            new_values=import_batch_to_dict(batch),
            user_id=uploaded_by_id,
            commit=False,
        )
        db.session.commit()
        return batch
    except Exception:
        # Keep the uploaded file and batch row for investigation, but mark it failed.
        batch.status = "FAILED"
        batch.notes = "Inspection failed. See error report."
        db.session.commit()
        raise


def list_batches(filters, page, per_page):
    """Import history with optional status filter."""
    query = ImportBatch.query
    if filters.get("status"):
        query = query.filter_by(status=filters["status"])
    if filters.get("station_id"):
        query = query.filter_by(station_id=filters["station_id"])
    return query.order_by(ImportBatch.file_imported_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_batch(batch_id):
    return db.session.get(ImportBatch, batch_id)


def update_mapping(batch, payload, user_id):
    """Validate and save administrator edits to the proposed mapping."""
    if batch.status in {"COMPLETED", "PROCESSING"}:
        raise ConflictError("This import has already been processed; mapping is locked.")

    mapping = dict(batch.column_mapping or {})
    original_sheet = mapping.get("sheet_name")

    for key in (
        "sheet_name", "timestamp_column", "port_column", "timezone",
    ):
        if key in payload:
            mapping[key] = payload[key]
    if "measurement_columns" in payload:
        mapping["measurement_columns"] = payload["measurement_columns"]
    if "sensor_mapping" in payload:
        mapping["sensor_mapping"] = payload["sensor_mapping"]
    if "station_id" in payload:
        station_id = payload["station_id"]
        if station_id is not None and db.session.get(Station, station_id) is None:
            raise ValidationAppError(f"Station {station_id} does not exist.")
        mapping["station_id"] = station_id
        batch.station_id = station_id

    # Validate references now so processing cannot fail halfway through.
    if mapping.get("station_id"):
        station = db.session.get(Station, mapping["station_id"])
        if station is None:
            raise ValidationAppError("Selected station no longer exists.")
    valid_codes = {item.code for item in MeasurementType.query.all()}
    for code in (mapping.get("measurement_columns") or {}).values():
        if code not in valid_codes:
            raise ValidationAppError(f"Unknown measurement type code '{code}'.")
    for sensor_id in (mapping.get("sensor_mapping") or {}).values():
        if sensor_id and db.session.get(Sensor, int(sensor_id)) is None:
            raise ValidationAppError(f"Sensor {sensor_id} does not exist.")

    # If the administrator switched worksheet, rebuild the preserved raw rows
    # from that sheet (not yet processed, so no historical data is lost).
    if mapping.get("sheet_name") != original_sheet:
        from app.models import RawImportRecord
        from app.processors.import_processor import create_raw_records

        connector = get_connector(batch.original_filename)
        _headers, rows = connector.read_rows(batch.stored_path, mapping["sheet_name"])
        RawImportRecord.query.filter_by(import_batch_id=batch.id).delete()
        batch.total_rows = 0
        create_raw_records(batch, rows)

    previous = dict(batch.column_mapping or {})
    batch.column_mapping = mapping
    batch.status = "PREVIEWED"
    log_action(
        "IMPORT_MAPPING_UPDATED",
        "imports",
        record_identifier=batch.batch_number,
        previous_values={"column_mapping": previous},
        new_values={"column_mapping": mapping},
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return batch


def preview(batch, limit=50):
    return build_preview(batch, limit)


def get_errors(batch, limit=200):
    """All raw rows with validation messages or invalid values."""
    preview_data = build_preview(batch, limit=limit)
    return [row for row in preview_data["rows"] if row["messages"]]


def process_batch(batch, user_id):
    """Steps 8-11. Large files are handed to Celery."""
    if batch.status == "COMPLETED":
        raise ConflictError("This import batch has already been processed.")
    if batch.status in {"PROCESSING", "QUEUED"}:
        raise ConflictError("This import batch is already being processed.")

    if batch.file_size_bytes and batch.file_size_bytes > BACKGROUND_THRESHOLD_BYTES:
        from app.tasks.import_tasks import process_import_task

        batch.status = "QUEUED"
        db.session.commit()
        task = process_import_task.delay(batch.id, user_id)
        return {"queued": True, "task_id": task.id, "batch": import_batch_to_dict(batch)}

    summary = execute_import(batch, user_id)
    log_action(
        "IMPORT_PROCESSED",
        "imports",
        record_identifier=batch.batch_number,
        new_values=summary,
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return {"queued": False, "summary": summary}
