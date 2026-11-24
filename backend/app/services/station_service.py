"""Station business logic: create, update, archive and detail assembly."""

from app.extensions import db
from app.models import Station
from app.repositories.station_repository import StationRepository
from app.utils.serializers import (
    import_batch_to_dict,
    maintenance_to_dict,
    measurement_to_dict,
    station_status_to_dict,
    station_to_dict,
)
from app.utils.time import to_iso

from .audit_service import log_action
from .exceptions import ConflictError, NotFoundError


def create_station(data, user_id):
    """Create a station after checking that its code is unique."""
    if StationRepository.find_by_code(data["station_code"]):
        raise ConflictError(
            f"Station code '{data['station_code']}' is already in use."
        )

    station = Station(**data)
    db.session.add(station)
    # Flush now so the station has an id for the audit snapshot.
    db.session.flush()
    log_action(
        "STATION_CREATED",
        "stations",
        record_identifier=data["station_code"],
        new_values=station_to_dict(station),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return station


def update_station(station, data, user_id):
    """Update a station, keeping a before/after audit snapshot."""
    previous = station_to_dict(station)

    new_code = data.get("station_code")
    if new_code and StationRepository.find_by_code(new_code, exclude_id=station.id):
        raise ConflictError(f"Station code '{new_code}' is already in use.")

    for field, value in data.items():
        setattr(station, field, value)

    log_action(
        "STATION_UPDATED",
        "stations",
        record_identifier=station.station_code,
        previous_values=previous,
        new_values=station_to_dict(station),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return station


def archive_station(station, user_id):
    """Archive (never delete) a station and its sensors.

    Historical measurements are preserved exactly as they are.
    """
    if station.is_archived:
        return station  # idempotent: nothing to change

    previous = station_to_dict(station)
    station.is_archived = True
    log_action(
        "STATION_ARCHIVED",
        "stations",
        record_identifier=station.station_code,
        previous_values=previous,
        new_values=station_to_dict(station),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return station


def clear_station_data(station, user_id):
    """Permanently delete all readings and imports for one station.

    The station itself, its sensors and its configuration are kept. This is a
    deliberate destructive action for fixing a station that received the wrong
    file (e.g. a water-level workbook imported into a weather station). It is
    only reachable through an explicit, confirmed administrator action.
    """
    from app.models import (
        Alert,
        DataQualityFlag,
        ImportBatch,
        MaintenanceRecord,
        Measurement,
        RawImportRecord,
        Report,
        StationStatus,
    )

    station_id = station.id

    # Count what will be removed for the confirmation/result message.
    measurement_count = Measurement.query.filter_by(station_id=station_id).count()
    batch_ids = [
        row[0] for row in db.session.query(ImportBatch.id)
        .filter(ImportBatch.station_id == station_id).all()
    ]

    # Delete in dependency order so no foreign key is left dangling.
    # Quality flags can reference a measurement OR an import batch directly.
    if batch_ids:
        DataQualityFlag.query.filter(
            DataQualityFlag.import_batch_id.in_(batch_ids)
        ).delete(synchronize_session=False)
    DataQualityFlag.query.filter_by(station_id=station_id).delete(
        synchronize_session=False
    )
    Measurement.query.filter_by(station_id=station_id).delete(
        synchronize_session=False
    )
    if batch_ids:
        RawImportRecord.query.filter(
            RawImportRecord.import_batch_id.in_(batch_ids)
        ).delete(synchronize_session=False)
        ImportBatch.query.filter(ImportBatch.id.in_(batch_ids)).delete(
            synchronize_session=False
        )

    StationStatus.query.filter_by(station_id=station_id).delete(
        synchronize_session=False
    )
    Alert.query.filter_by(station_id=station_id).delete(synchronize_session=False)
    MaintenanceRecord.query.filter_by(station_id=station_id).delete(
        synchronize_session=False
    )
    Report.query.filter_by(station_id=station_id).delete(synchronize_session=False)

    # Reset health so the station is not shown as OFFLINE from stale snapshots.
    station.operational_status = "UNKNOWN"

    log_action(
        "STATION_DATA_CLEARED",
        "stations",
        record_identifier=station.station_code,
        new_values={
            "measurements_deleted": measurement_count,
            "import_batches_deleted": len(batch_ids),
        },
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return {
        "station_id": station_id,
        "measurements_deleted": measurement_count,
        "import_batches_deleted": len(batch_ids),
    }


def station_detail(station):
    """Assemble the station detail page data from several tables."""
    from app.models import ImportBatch, Measurement, Sensor

    latest_status = StationRepository.status_history(station.id, limit=1)
    return {
        **station_to_dict(station),
        "sensor_count": Sensor.query.filter_by(station_id=station.id).count(),
        "measurement_count": Measurement.query.filter_by(station_id=station.id).count(),
        "import_count": ImportBatch.query.filter_by(station_id=station.id).count(),
        "latest_status": station_status_to_dict(latest_status[0]) if latest_status else None,
    }


def map_data():
    """All active stations with coordinates for the GIS map (unpaginated)."""
    return [station_to_dict(station) for station in StationRepository.list_all_active()]


def station_history(station_id, limit=50):
    """Audit entries that mention this station (used by 'View station history')."""
    from app.models import AuditLog

    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")

    # Audit records store the station code as identifier; also match numeric ids.
    rows = (
        AuditLog.query.filter_by(module="stations")
        .filter(
            AuditLog.record_identifier.in_(
                [station.station_code, str(station.id)]
            )
        )
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "action": row.action,
            "record_identifier": row.record_identifier,
            "previous_values": row.previous_values,
            "new_values": row.new_values,
            "occurred_at": to_iso(row.occurred_at),
        }
        for row in rows
    ]


def related_records(station_id, kind, page=1, per_page=25, measurement_type_id=None):
    """Return sensors / measurements / status / maintenance / imports."""
    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")

    if kind == "sensors":
        from app.utils.serializers import sensor_to_dict

        return [sensor_to_dict(s) for s in StationRepository.sensors_for_station(station_id, True)], None

    if kind == "measurements":
        pagination = StationRepository.measurements_for_station(
            station_id, page, per_page, measurement_type_id
        )
        return [measurement_to_dict(m) for m in pagination.items], pagination

    if kind == "status":
        return [station_status_to_dict(s) for s in StationRepository.status_history(station_id)], None

    if kind == "maintenance":
        return [maintenance_to_dict(m) for m in StationRepository.maintenance_for_station(station_id)], None

    if kind == "imports":
        return [import_batch_to_dict(b) for b in StationRepository.imports_for_station(station_id)], None

    raise NotFoundError(f"Unknown related-record type: {kind}")
