"""System endpoints: health, settings and audit logs."""

from fastapi import APIRouter, Depends

from app.schemas import AuditLogFilterSchema, SystemSettingSchema
from app.services import system_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.time import parse_iso

system_bp = APIRouter()
audit_bp = APIRouter()


@system_bp.get("/health")
def health():
    payload = system_service.health_payload()
    if payload["status"] != "healthy":
        from app.utils.responses import error
        return error("Database unavailable.", 503, code="DB_UNAVAILABLE")
    return ok(data=payload)


@system_bp.get("/settings")
def get_settings(user=Depends(get_current_user)):
    return ok(data=system_service.list_settings())


@system_bp.put("/settings")
def put_setting(payload: SystemSettingSchema, user=Depends(get_current_user)):
    setting = system_service.update_setting(
        key=payload.key,
        value=payload.value,
        user_id=user.id,
        description=payload.description,
        category=payload.category,
    )
    return ok(data={"key": setting.key, "value": setting.value}, message="Setting saved.")


def _audit_response(filters: AuditLogFilterSchema):
    data = filters.model_dump()
    data["date_from"] = parse_iso(data.get("date_from"))
    data["date_to"] = parse_iso(data.get("date_to"))
    pagination = system_service.list_audit_logs(data, data["page"], data["per_page"])
    items = [
        {
            "id": row.id, "user_id": row.user_id, "action": row.action,
            "module": row.module, "record_identifier": row.record_identifier,
            "previous_values": row.previous_values, "new_values": row.new_values,
            "ip_address": row.ip_address,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        }
        for row in pagination.items
    ]
    return paginated(items, pagination.page, pagination.per_page, pagination.total)


@system_bp.get("/audit-logs")
def system_audit_logs(filters: AuditLogFilterSchema = Depends(), user=Depends(get_current_user)):
    return _audit_response(filters)


@audit_bp.get("/audit-logs")
def audit_logs(filters: AuditLogFilterSchema = Depends(), user=Depends(get_current_user)):
    return _audit_response(filters)
