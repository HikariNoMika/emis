"""Sensor business logic and health calculation."""

from app.extensions import db
from app.models import (
    MaintenanceRecord,
    Measurement,
    MeasurementType,
    Sensor,
    SensorMeasurementType,
)
from app.repositories.sensor_repository import SensorRepository
from app.utils.serializers import measurement_to_dict, sensor_to_dict
from app.utils.time import to_iso, utcnow

from .audit_service import log_action
from .exceptions import NotFoundError, ValidationAppError


def create_sensor(data, user_id):
    station_id = data.pop("station_id")
    if not SensorRepository.station_exists(station_id):
        raise ValidationAppError(f"Station {station_id} does not exist.")

    sensor = Sensor(station_id=station_id, **data)
    db.session.add(sensor)
    db.session.flush()
    log_action(
        "SENSOR_CREATED",
        "sensors",
        record_identifier=str(sensor.id),
        new_values=sensor_to_dict(sensor),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return sensor


def update_sensor(sensor, data, user_id):
    previous = sensor_to_dict(sensor)
    station_id = data.pop("station_id", None)
    if station_id is not None:
        if not SensorRepository.station_exists(station_id):
            raise ValidationAppError(f"Station {station_id} does not exist.")
        sensor.station_id = station_id

    for field, value in data.items():
        setattr(sensor, field, value)

    log_action(
        "SENSOR_UPDATED",
        "sensors",
        record_identifier=str(sensor.id),
        previous_values=previous,
        new_values=sensor_to_dict(sensor),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return sensor


def set_measurement_types(sensor_id, type_ids, column_hints, user_id):
    """Replace the list of measurement types produced by a sensor.

    `column_hints` is optional: it remembers the original spreadsheet column
    name for each type, which makes later imports much easier to map.
    """
    sensor = SensorRepository.find_by_id(sensor_id)
    if sensor is None:
        raise NotFoundError("Sensor not found.")

    previous = [link.measurement_type_id for link in sensor.measurement_type_links]

    # Validate every id before changing anything.
    for type_id in type_ids:
        if db.session.get(MeasurementType, type_id) is None:
            raise ValidationAppError(f"Measurement type {type_id} does not exist.")

    SensorMeasurementType.query.filter_by(sensor_id=sensor_id).delete()
    for type_id in type_ids:
        db.session.add(
            SensorMeasurementType(
                sensor_id=sensor_id,
                measurement_type_id=type_id,
                column_hint=(column_hints or {}).get(str(type_id)),
            )
        )

    log_action(
        "SENSOR_MEASUREMENT_TYPES_UPDATED",
        "sensors",
        record_identifier=str(sensor_id),
        previous_values={"measurement_type_ids": previous},
        new_values={"measurement_type_ids": type_ids},
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    # Refresh the relationship so the response includes the new links.
    db.session.expire(sensor, ["measurement_type_links"])
    return sensor


def sensor_health(sensor):
    """Latest observation, communication and calibration status for a sensor.

    `NOT_REPORTED` is used when no device communication data exists — a late
    Excel upload is not treated as broken equipment.
    """
    latest = SensorRepository.latest_measurement_for_sensor(sensor.id)
    now = utcnow()
    freshness_minutes = None
    if latest and latest.observation_time:
        freshness_minutes = int(
            (now - latest.observation_time).total_seconds() // 60
        )

    maintenance_count = MaintenanceRecord.query.filter_by(sensor_id=sensor.id).count()
    calibration_due = (
        sensor.next_calibration_date is not None
        and sensor.next_calibration_date < now.date()
    )

    return {
        **sensor_to_dict(sensor),
        "latest_observation_time": to_iso(latest.observation_time) if latest else None,
        "data_freshness_minutes": freshness_minutes,
        "connectivity_state": "NOT_REPORTED",
        "calibration_due": calibration_due,
        "maintenance_record_count": maintenance_count,
        "measurement_count": Measurement.query.filter_by(sensor_id=sensor.id).count(),
        "latest_measurement": measurement_to_dict(latest) if latest else None,
    }
