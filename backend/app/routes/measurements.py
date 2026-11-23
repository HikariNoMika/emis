"""Measurement, trend, statistics and export endpoints."""

from fastapi import APIRouter, Depends, Request

from app.schemas import FlexibleComparisonQuerySchema, MeasurementQuerySchema
from app.services import measurement_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.time import parse_iso

measurements_bp = APIRouter()


def _query_model(request, model):
    return model.model_validate(dict(request.query_params))


@measurements_bp.get("")
def list_measurements(request: Request, user=Depends(get_current_user)):
    payload = _query_model(request, MeasurementQuerySchema)
    date_from, date_to = parse_iso(payload.date_from), parse_iso(payload.date_to)
    items, pagination = measurement_service.list_measurements(
        payload.model_dump(), payload.page, payload.per_page, date_from, date_to
    )
    return paginated(items, pagination.page, pagination.per_page, pagination.total)


@measurements_bp.get("/latest")
def latest_measurements(request: Request, user=Depends(get_current_user)):
    payload = _query_model(request, MeasurementQuerySchema)
    return ok(data=measurement_service.latest(payload.model_dump()))


@measurements_bp.get("/trends")
def trends(request: Request, user=Depends(get_current_user)):
    params = dict(request.query_params)
    # Axios serializes arrays as measurement_type_ids[]=1, so accept both forms.
    params["measurement_type_ids"] = (
        request.query_params.getlist("measurement_type_ids")
        or request.query_params.getlist("measurement_type_ids[]")
    )
    if not params["measurement_type_ids"] and params.get("measurement_type_ids"):
        params["measurement_type_ids"] = [
            item for item in str(params["measurement_type_ids"]).split(",") if item
        ]
    from app.schemas import TrendsQuerySchema

    payload = TrendsQuerySchema.model_validate(params)
    date_from, date_to = parse_iso(payload.date_from), parse_iso(payload.date_to)
    return ok(data=measurement_service.trends(payload.model_dump(), date_from, date_to))


@measurements_bp.get("/statistics")
def statistics(request: Request, user=Depends(get_current_user)):
    from app.schemas import StatisticsQuerySchema

    payload = StatisticsQuerySchema.model_validate(dict(request.query_params))
    date_from, date_to = parse_iso(payload.date_from), parse_iso(payload.date_to)
    return ok(data=measurement_service.statistics_for(
        payload.model_dump(), date_from, date_to
    ))


@measurements_bp.get("/statistics/bulk")
def statistics_bulk(request: Request, user=Depends(get_current_user)):
    raw_station_id = request.query_params.get("station_id")
    try:
        station_id = int(raw_station_id) if raw_station_id else None
    except ValueError:
        station_id = None
    if not station_id:
        from app.utils.responses import error
        return error("station_id is required.", 400)
    from app.utils.time import parse_iso

    return ok(data=measurement_service.statistics_bulk(
        station_id,
        parse_iso(request.query_params.get("date_from")),
        parse_iso(request.query_params.get("date_to")),
    ))


@measurements_bp.get("/compare-flexible")
def compare_flexible(request: Request, user=Depends(get_current_user)):
    payload = FlexibleComparisonQuerySchema.model_validate(dict(request.query_params))
    from app.utils.time import parse_iso

    result = measurement_service.flexible_comparison(
        payload.model_dump(),
        parse_iso(payload.date_from_a),
        parse_iso(payload.date_to_a),
        parse_iso(payload.date_from_b),
        parse_iso(payload.date_to_b),
    )
    if result is None:
        from app.utils.responses import error
        return error("Measurement type not found.", 404)
    return ok(data=result)


@measurements_bp.get("/export")
def export(request: Request, user=Depends(get_current_user)):
    from fastapi.responses import Response
    from app.schemas import ExportQuerySchema

    payload = ExportQuerySchema.model_validate(dict(request.query_params))
    date_from, date_to = parse_iso(payload.date_from), parse_iso(payload.date_to)
    records = measurement_service.export_rows(payload.model_dump(), date_from, date_to)

    if payload.format == "csv":
        return Response(
            measurement_service.export_csv(records),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="emis_measurements.csv"'},
        )
    return Response(
        measurement_service.export_xlsx(records),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="emis_measurements.xlsx"'},
    )
