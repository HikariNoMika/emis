"""Maintenance endpoints."""

from fastapi import APIRouter, Depends

from app.schemas import MaintenanceQuerySchema, MaintenanceSchema
from app.services import maintenance_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import maintenance_to_dict

maintenance_bp = APIRouter()


@maintenance_bp.get("")
def list_maintenance(filters: MaintenanceQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = maintenance_service.list_records(data, data["page"], data["per_page"])
    return paginated(
        [maintenance_to_dict(r) for r in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@maintenance_bp.get("/calendar")
def calendar(user=Depends(get_current_user)):
    return ok(data=maintenance_service.calendar())


@maintenance_bp.post("", status_code=201)
def create_maintenance(payload: MaintenanceSchema, user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    record = maintenance_service.create_record(data, user.id)
    return ok(data=maintenance_to_dict(record), message="Maintenance record created.")


@maintenance_bp.get("/{record_id}")
def get_maintenance(record_id: int, user=Depends(get_current_user)):
    return ok(data=maintenance_to_dict(maintenance_service.get_record(record_id)))


@maintenance_bp.put("/{record_id}")
def update_maintenance(
    record_id: int, payload: MaintenanceSchema, user=Depends(get_current_user)
):
    record = maintenance_service.get_record(record_id)
    maintenance_service.update_record(
        record, payload.model_dump(exclude_unset=True), user.id
    )
    return ok(data=maintenance_to_dict(record), message="Maintenance record updated.")


@maintenance_bp.delete("/{record_id}")
def delete_maintenance(record_id: int, user=Depends(get_current_user)):
    maintenance_service.delete_record(
        maintenance_service.get_record(record_id), user.id
    )
    return ok(message="Maintenance record deleted.")
