"""Analytics endpoints."""

from fastapi import APIRouter, Depends, Request

from app.schemas import ComparisonQuerySchema
from app.services import measurement_service
from app.utils.responses import ok
from app.utils.security import get_current_user
from app.utils.time import parse_iso

analytics_bp = APIRouter()


@analytics_bp.get("/comparison")
def comparison(request: Request, user=Depends(get_current_user)):
    params = dict(request.query_params)
    # Axios sends arrays as station_ids[]=1&station_ids[]=2.
    params["station_ids"] = (
        request.query_params.getlist("station_ids")
        or request.query_params.getlist("station_ids[]")
    )
    payload = ComparisonQuerySchema.model_validate(params)
    results = measurement_service.comparison(
        payload.model_dump(),
        parse_iso(payload.date_from),
        parse_iso(payload.date_to),
    )
    return ok(data={
        "measurement_type_id": payload.measurement_type_id,
        "stations": results,
    })
