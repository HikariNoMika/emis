"""Alert endpoints."""

from fastapi import APIRouter, Depends

from app.schemas import AlertActionSchema, AlertQuerySchema
from app.services import alert_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import alert_to_dict

alerts_bp = APIRouter()


@alerts_bp.get("")
def list_alerts(filters: AlertQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = alert_service.list_alerts(data, data["page"], data["per_page"])
    return paginated(
        [alert_to_dict(a) for a in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@alerts_bp.get("/{alert_id}")
def get_alert(alert_id: int, user=Depends(get_current_user)):
    return ok(data=alert_to_dict(alert_service.get_alert(alert_id)))


@alerts_bp.post("/{alert_id}/acknowledge")
def acknowledge(
    alert_id: int, payload: AlertActionSchema, user=Depends(get_current_user)
):
    alert = alert_service.acknowledge(
        alert_service.get_alert(alert_id), user.id, payload.remarks
    )
    return ok(data=alert_to_dict(alert), message="Alert acknowledged.")


@alerts_bp.post("/{alert_id}/resolve")
def resolve(alert_id: int, payload: AlertActionSchema, user=Depends(get_current_user)):
    alert = alert_service.resolve(
        alert_service.get_alert(alert_id), user.id, payload.remarks
    )
    return ok(data=alert_to_dict(alert), message="Alert resolved.")


@alerts_bp.get("/{alert_id}/history")
def alert_history(alert_id: int, user=Depends(get_current_user)):
    return ok(data=alert_service.history(alert_id))
