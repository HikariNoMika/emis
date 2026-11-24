"""Read-only dashboard endpoints."""

from fastapi import APIRouter, Depends, Query

from app.services import dashboard_service
from app.utils.responses import ok
from app.utils.security import get_current_user

dashboard_bp = APIRouter()


@dashboard_bp.get("/summary")
def summary(user=Depends(get_current_user)):
    return ok(data=dashboard_service.summary())


@dashboard_bp.get("/data-progress")
def data_progress(year: int | None = Query(None), user=Depends(get_current_user)):
    """Quarter-by-quarter data processing progress for a year (default: current)."""
    return ok(data=dashboard_service.data_progress(year))


@dashboard_bp.get("/environmental-summary")
def environmental_summary(limit: int = Query(200, ge=1, le=500), user=Depends(get_current_user)):
    return ok(data=dashboard_service.environmental_summary(limit))


@dashboard_bp.get("/station-status")
def station_status(user=Depends(get_current_user)):
    return ok(data=dashboard_service.station_status())


@dashboard_bp.get("/recent-alerts")
def recent_alerts(limit: int = Query(10, ge=1, le=50), user=Depends(get_current_user)):
    return ok(data=dashboard_service.recent_alerts(limit))
