"""Measurement-type catalogue endpoints."""

from fastapi import APIRouter, Depends

from app.extensions import db
from app.models import MeasurementType
from app.schemas import MeasurementTypeSchema
from app.services import measurement_type_service
from app.services.exceptions import NotFoundError, ValidationAppError
from app.utils.responses import ok
from app.utils.security import get_current_user
from app.utils.serializers import measurement_type_to_dict

measurement_types_bp = APIRouter()


@measurement_types_bp.get("")
def list_types(user=Depends(get_current_user)):
    return ok(data=measurement_type_service.list_types())


@measurement_types_bp.post("", status_code=201)
def create_type(payload: MeasurementTypeSchema, user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not all(data.get(key) for key in ("code", "name", "category", "unit")):
        raise ValidationAppError("code, name, category and unit are required.")
    item = measurement_type_service.create_type(data, user.id)
    return ok(data=measurement_type_to_dict(item), message="Measurement type created.")


@measurement_types_bp.put("/{type_id}")
def update_type(type_id: int, payload: MeasurementTypeSchema, user=Depends(get_current_user)):
    item = db.session.get(MeasurementType, type_id)
    if item is None:
        raise NotFoundError("Measurement type not found.")
    measurement_type_service.update_type(
        item, payload.model_dump(exclude_unset=True), user.id
    )
    return ok(data=measurement_type_to_dict(item), message="Measurement type updated.")
