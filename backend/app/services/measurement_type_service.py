"""Measurement-type catalogue business logic."""

from app.extensions import db
from app.models import MeasurementType
from app.utils.serializers import measurement_type_to_dict

from .audit_service import log_action
from .exceptions import ConflictError


def list_types():
    return [
        measurement_type_to_dict(item)
        for item in MeasurementType.query.order_by(
            MeasurementType.category, MeasurementType.name
        ).all()
    ]


def create_type(data, user_id):
    if MeasurementType.query.filter_by(code=data["code"]).first():
        raise ConflictError(f"Measurement type '{data['code']}' already exists.")
    item = MeasurementType(**data)
    db.session.add(item)
    db.session.flush()
    log_action(
        "MEASUREMENT_TYPE_CREATED",
        "measurement_types",
        record_identifier=item.code,
        new_values=measurement_type_to_dict(item),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return item


def update_type(item, data, user_id):
    previous = measurement_type_to_dict(item)
    new_code = data.get("code")
    if new_code and new_code != item.code:
        if MeasurementType.query.filter_by(code=new_code).first():
            raise ConflictError(f"Measurement type '{new_code}' already exists.")
    for field, value in data.items():
        setattr(item, field, value)
    log_action(
        "MEASUREMENT_TYPE_UPDATED",
        "measurement_types",
        record_identifier=item.code,
        previous_values=previous,
        new_values=measurement_type_to_dict(item),
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return item
