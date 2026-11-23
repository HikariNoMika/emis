"""Data-quality endpoints."""

from fastapi import APIRouter, Depends

from app.schemas import QualityFlagQuerySchema, ResolveFlagSchema
from app.services import data_quality_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import quality_flag_to_dict

data_quality_bp = APIRouter()


@data_quality_bp.get("/summary")
def summary(user=Depends(get_current_user)):
    return ok(data=data_quality_service.summary())


@data_quality_bp.get("/flags")
def list_flags(filters: QualityFlagQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = data_quality_service.list_flags(data, data["page"], data["per_page"])
    return paginated(
        [quality_flag_to_dict(f) for f in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@data_quality_bp.get("/flags/{flag_id}")
def get_flag(flag_id: int, user=Depends(get_current_user)):
    return ok(data=quality_flag_to_dict(data_quality_service.get_flag(flag_id)))


@data_quality_bp.post("/flags/{flag_id}/resolve")
def resolve_flag(
    flag_id: int, payload: ResolveFlagSchema, user=Depends(get_current_user)
):
    flag = data_quality_service.resolve_flag(
        data_quality_service.get_flag(flag_id),
        payload.resolution_status,
        payload.admin_remarks,
        user.id,
    )
    return ok(data=quality_flag_to_dict(flag), message="Flag updated.")
