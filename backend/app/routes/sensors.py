"""Sensor endpoints."""

from fastapi import APIRouter, Depends, Query

from app.repositories.sensor_repository import SensorRepository
from app.schemas import SensorMeasurementTypesSchema, SensorQuerySchema, SensorSchema
from app.services import sensor_service
from app.services.exceptions import NotFoundError, ValidationAppError
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import measurement_to_dict, sensor_to_dict

sensors_bp = APIRouter()


@sensors_bp.get("")
def list_sensors(filters: SensorQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = SensorRepository.list_sensors(data, data["page"], data["per_page"])
    return paginated(
        [sensor_to_dict(s) for s in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@sensors_bp.post("", status_code=201)
def create_sensor(payload: SensorSchema, user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not data.get("station_id") or not data.get("name"):
        raise ValidationAppError("station_id and name are required.")
    sensor = sensor_service.create_sensor(data, user.id)
    return ok(data=sensor_to_dict(sensor), message="Sensor created.")


@sensors_bp.get("/{sensor_id}")
def get_sensor(sensor_id: int, user=Depends(get_current_user)):
    sensor = SensorRepository.find_by_id(sensor_id)
    if sensor is None:
        raise NotFoundError("Sensor not found.")
    return ok(data=sensor_to_dict(sensor))


@sensors_bp.put("/{sensor_id}")
def update_sensor(sensor_id: int, payload: SensorSchema, user=Depends(get_current_user)):
    sensor = SensorRepository.find_by_id(sensor_id)
    if sensor is None:
        raise NotFoundError("Sensor not found.")
    sensor_service.update_sensor(sensor, payload.model_dump(exclude_unset=True), user.id)
    return ok(data=sensor_to_dict(sensor), message="Sensor updated.")


@sensors_bp.put("/{sensor_id}/measurement-types")
def set_measurement_types(
    sensor_id: int, payload: SensorMeasurementTypesSchema, user=Depends(get_current_user)
):
    sensor = sensor_service.set_measurement_types(
        sensor_id,
        payload.measurement_type_ids,
        payload.column_hints,
        user.id,
    )
    return ok(data=sensor_to_dict(sensor), message="Measurement types updated.")


@sensors_bp.get("/{sensor_id}/health")
def sensor_health(sensor_id: int, user=Depends(get_current_user)):
    sensor = SensorRepository.find_by_id(sensor_id)
    if sensor is None:
        raise NotFoundError("Sensor not found.")
    return ok(data=sensor_service.sensor_health(sensor))


@sensors_bp.get("/{sensor_id}/measurements")
def sensor_measurements(
    sensor_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    user=Depends(get_current_user),
):
    if SensorRepository.find_by_id(sensor_id) is None:
        raise NotFoundError("Sensor not found.")
    pagination = SensorRepository.measurements_for_sensor(sensor_id, page, per_page)
    return paginated(
        [measurement_to_dict(m) for m in pagination.items],
        page, per_page, pagination.total,
    )
