"""Maintenance and calibration record business logic."""

from datetime import date

from app.extensions import db
from app.models import MaintenanceRecord, Station
from app.utils.serializers import maintenance_to_dict
from app.utils.time import utcnow

from .audit_service import log_action
from .exceptions import NotFoundError, ValidationAppError


def list_records(filters, page, per_page):
    query = MaintenanceRecord.query
    for field in ("station_id", "sensor_id", "maintenance_type"):
        if filters.get(field):
            query = query.filter(getattr(MaintenanceRecord, field) == filters[field])
    return query.order_by(MaintenanceRecord.maintenance_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_record(record_id):
    record = db.session.get(MaintenanceRecord, record_id)
    if record is None:
        raise NotFoundError("Maintenance record not found.")
    return record


def _validate_references(data):
    if data.get("station_id") is None:
        return
    if db.session.get(Station, data["station_id"]) is None:
        raise ValidationAppError(f"Station {data['station_id']} does not exist.")
    if data.get("sensor_id"):
        from app.models import Sensor

        sensor = db.session.get(Sensor, data["sensor_id"])
        if sensor is None or sensor.station_id != data["station_id"]:
            raise ValidationAppError("Sensor does not belong to the selected station.")


def create_record(data, user_id):
    _validate_references(data)
    record = MaintenanceRecord(**data)
    db.session.add(record)
    db.session.flush()
    log_action(
        "MAINTENANCE_CREATED",
        "maintenance",
        record_identifier=record.id,
        new_values=maintenance_to_dict(record),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return record


def update_record(record, data, user_id):
    previous = maintenance_to_dict(record)
    merged = previous.copy()
    merged.update(data)
    _validate_references(
        {
            "station_id": merged.get("station_id"),
            "sensor_id": merged.get("sensor_id"),
        }
    )
    for field, value in data.items():
        setattr(record, field, value)
    log_action(
        "MAINTENANCE_UPDATED",
        "maintenance",
        record_identifier=record.id,
        previous_values=previous,
        new_values=maintenance_to_dict(record),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return record


def delete_record(record, user_id):
    """Maintenance records may be deleted; the action itself is audited."""
    snapshot = maintenance_to_dict(record)
    db.session.delete(record)
    log_action(
        "MAINTENANCE_DELETED",
        "maintenance",
        record_identifier=record.id,
        previous_values=snapshot,
        user_id=user_id,
        commit=False,
    )
    db.session.commit()


def calendar():
    """Upcoming and overdue maintenance grouped for the dashboard."""
    today = utcnow().date()
    upcoming = (
        MaintenanceRecord.query.filter(
            MaintenanceRecord.next_maintenance_date >= today
        )
        .order_by(MaintenanceRecord.next_maintenance_date)
        .limit(50)
        .all()
    )
    overdue = (
        MaintenanceRecord.query.filter(
            MaintenanceRecord.next_maintenance_date < today
        )
        .order_by(MaintenanceRecord.next_maintenance_date)
        .limit(50)
        .all()
    )
    return {
        "upcoming": [maintenance_to_dict(item) for item in upcoming],
        "overdue": [maintenance_to_dict(item) for item in overdue],
    }
