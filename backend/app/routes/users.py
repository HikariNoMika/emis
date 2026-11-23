"""User administration endpoints: /api/v1/users/*."""

from fastapi import APIRouter, Depends

from app.api.v1.deps import require_admin
from app.schemas import (
    ResetPasswordSchema,
    UserCreateSchema,
    UserQuerySchema,
    UserUpdateSchema,
)
from app.services import user_management_service as service
from app.utils.responses import ok, paginated
from app.utils.serializers import user_to_dict

users_bp = APIRouter()


@users_bp.get("")
def list_users(filters: UserQuerySchema = Depends(), admin=Depends(require_admin)):
    data = filters.model_dump()
    pagination = service.list_users(data, data["page"], data["per_page"])
    return paginated(
        [user_to_dict(user) for user in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@users_bp.post("", status_code=201)
def create_user(payload: UserCreateSchema, admin=Depends(require_admin)):
    data = payload.model_dump(exclude={"confirm_password"})
    user = service.create_user(data, admin.id)
    return ok(data=user_to_dict(user), message="User created.")


@users_bp.get("/{user_id}")
def get_user(user_id: int, admin=Depends(require_admin)):
    return ok(data=user_to_dict(service.get_user(user_id)))


@users_bp.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdateSchema, admin=Depends(require_admin)):
    user = service.update_user(
        service.get_user(user_id),
        payload.model_dump(exclude_unset=True),
        admin.id,
    )
    return ok(data=user_to_dict(user), message="User updated.")


@users_bp.post("/{user_id}/activate")
def activate_user(user_id: int, admin=Depends(require_admin)):
    return ok(data=user_to_dict(
        service.set_active(service.get_user(user_id), True, admin.id)
    ), message="User activated.")


@users_bp.post("/{user_id}/deactivate")
def deactivate_user(user_id: int, admin=Depends(require_admin)):
    return ok(data=user_to_dict(
        service.set_active(service.get_user(user_id), False, admin.id)
    ), message="User deactivated.")


@users_bp.post("/{user_id}/reset-password")
def reset_password(
    user_id: int, payload: ResetPasswordSchema, admin=Depends(require_admin)
):
    service.reset_password(
        service.get_user(user_id),
        payload.new_password,
        admin.id,
        payload.must_change_password,
    )
    return ok(message="Password reset. The user will be asked to change it at login.")
