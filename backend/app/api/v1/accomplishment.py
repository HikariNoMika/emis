"""Quarterly and annual accomplishment endpoints."""

from fastapi import APIRouter, Depends, Query

from app.schemas import (
    ActualCreate,
    ActualUpdate,
    DataCompletenessQuery,
    IndicatorCreate,
    IndicatorUpdate,
    SummaryQuery,
    TargetCreate,
    TargetUpdate,
    WeightsUpdate,
)
from app.services import (
    accomplishment_calculator as calculator,
    accomplishment_service as service,
)
from app.services.exceptions import NotFoundError
from app.utils.responses import ok
from app.utils.security import get_current_user
from app.utils.serializers import (
    accomplishment_actual_to_dict,
    accomplishment_indicator_to_dict,
    accomplishment_target_to_dict,
)

accomplishment_bp = APIRouter()


def _require_finalizer(user):
    """Only administrators can finalize/revise. Roles are extensible later."""
    if getattr(user, "role", "admin") != "admin":
        from app.services.exceptions import ValidationAppError
        raise ValidationAppError("Only administrators may finalize or revise reports.")
    return user


@accomplishment_bp.get("/summary")
def summary(year: int, quarter: int | None = None, user=Depends(get_current_user)):
    if quarter:
        return ok(data=calculator.quarterly_summary(year, quarter))
    return ok(data=calculator.dashboard_summary(year))


@accomplishment_bp.get("/quarterly")
def quarterly(year: int, quarter: int, user=Depends(get_current_user)):
    return ok(data=calculator.quarterly_summary(year, quarter))


@accomplishment_bp.get("/annual")
def annual(year: int, user=Depends(get_current_user)):
    return ok(data=calculator.annual_summary(year))


@accomplishment_bp.get("/data-completeness")
def data_completeness(filters: DataCompletenessQuery = Depends(), user=Depends(get_current_user)):
    return ok(data=calculator.data_completeness(filters.model_dump()))


@accomplishment_bp.get("/categories")
def categories(user=Depends(get_current_user)):
    return ok(data=service.categories())


# ---- Indicators -------------------------------------------------------------
@accomplishment_bp.get("/indicators")
def list_indicators(year: int | None = None, category_code: str | None = None,
                    user=Depends(get_current_user)):
    return ok(data=service.indicators(year, category_code))


@accomplishment_bp.post("/indicators", status_code=201)
def create_indicator(payload: IndicatorCreate, user=Depends(get_current_user)):
    item = service.create_indicator(payload.model_dump(), user.id)
    return ok(data=accomplishment_indicator_to_dict(item), message="Indicator created.")


@accomplishment_bp.get("/indicators/{indicator_id}")
def get_indicator(indicator_id: int, user=Depends(get_current_user)):
    return ok(data=accomplishment_indicator_to_dict(service.get_indicator(indicator_id)))


@accomplishment_bp.put("/indicators/{indicator_id}")
def update_indicator(indicator_id: int, payload: IndicatorUpdate, user=Depends(get_current_user)):
    item = service.update_indicator(
        service.get_indicator(indicator_id),
        payload.model_dump(exclude_unset=True),
        user.id,
    )
    return ok(data=accomplishment_indicator_to_dict(item), message="Indicator updated.")


@accomplishment_bp.delete("/indicators/{indicator_id}")
def delete_indicator(indicator_id: int, user=Depends(get_current_user)):
    service.delete_indicator(service.get_indicator(indicator_id), user.id)
    return ok(message="Indicator and its targets/actuals were removed.")


# ---- Targets ----------------------------------------------------------------
@accomplishment_bp.get("/targets")
def list_targets(year: int | None = None, quarter: int | None = None,
                 indicator_id: int | None = None, user=Depends(get_current_user)):
    return ok(data=service.targets(year, quarter, indicator_id))


@accomplishment_bp.post("/targets", status_code=201)
def create_target(payload: TargetCreate, user=Depends(get_current_user)):
    item = service.create_target(payload.model_dump(), user.id)
    return ok(data=accomplishment_target_to_dict(item), message="Target created.")


@accomplishment_bp.put("/targets/{target_id}")
def update_target(target_id: int, payload: TargetUpdate, user=Depends(get_current_user)):
    item = service.Repo.target_by_id(target_id)
    if item is None:
        from app.services.exceptions import NotFoundError
        raise NotFoundError("Target not found.")
    return ok(data=accomplishment_target_to_dict(
        service.update_target(item, payload.model_dump(exclude_unset=True), user.id)
    ), message="Target updated.")


@accomplishment_bp.delete("/targets/{target_id}")
def delete_target(target_id: int, user=Depends(get_current_user)):
    target = service.Repo.target_by_id(target_id)
    if target is None:
        raise NotFoundError("Target not found.")
    service.delete_target(target, user.id)
    return ok(message="Quarterly target removed.")


# ---- Actuals ----------------------------------------------------------------
@accomplishment_bp.get("/actuals")
def list_actuals(year: int | None = None, quarter: int | None = None,
                 indicator_id: int | None = None, user=Depends(get_current_user)):
    return ok(data=service.actuals(year, quarter, indicator_id))


@accomplishment_bp.post("/actuals", status_code=201)
def create_actual(payload: ActualCreate, user=Depends(get_current_user)):
    item = service.create_actual(payload.model_dump(), user.id)
    return ok(data=accomplishment_actual_to_dict(item), message="Accomplishment recorded.")


@accomplishment_bp.put("/actuals/{actual_id}")
def update_actual(actual_id: int, payload: ActualUpdate, user=Depends(get_current_user)):
    item = service.Repo.actual_by_id(actual_id)
    if item is None:
        from app.services.exceptions import NotFoundError
        raise NotFoundError("Accomplishment entry not found.")
    return ok(data=accomplishment_actual_to_dict(
        service.update_actual(item, payload.model_dump(exclude_unset=True), user.id)
    ), message="Accomplishment updated.")


@accomplishment_bp.delete("/actuals/{actual_id}")
def delete_actual(actual_id: int, user=Depends(get_current_user)):
    actual = service.Repo.actual_by_id(actual_id)
    if actual is None:
        raise NotFoundError("Accomplishment entry not found.")
    service.delete_actual(actual, user.id)
    return ok(message="Accomplishment entry removed.")


# ---- Weights ----------------------------------------------------------------
@accomplishment_bp.get("/weights")
def get_weights(year: int, user=Depends(get_current_user)):
    return ok(data={
        "categories": service.categories(),
        "indicators": [
            {
                "id": item["id"],
                "name": item["name"],
                "category": item["category_code"],
                "weight": item["indicator_weight"],
            }
            for item in service.indicators(year)
        ],
        "history": service.weight_history(),
    })


@accomplishment_bp.put("/weights")
def put_weights(payload: WeightsUpdate, user=Depends(get_current_user)):
    return ok(data=service.update_weights(payload.model_dump(), user.id),
              message="Weights saved and recorded in history.")
