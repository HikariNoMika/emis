"""Station health endpoints."""

from fastapi import APIRouter, Depends

from app.extensions import db
from app.models import Station
from app.services import health_service
from app.services.exceptions import NotFoundError
from app.utils.responses import ok
from app.utils.security import get_current_user
from app.utils.serializers import station_status_to_dict

health_bp = APIRouter()


@health_bp.get("/stations")
def current_health(user=Depends(get_current_user)):
    return ok(data=health_service.current_status())


@health_bp.post("/refresh")
def refresh_health(station_id: int | None = None, user=Depends(get_current_user)):
    if station_id:
        station = db.session.get(Station, station_id)
        if station is None:
            raise NotFoundError("Station not found.")
        snapshot = health_service.evaluate_station(
            station,
            health_service._thresholds(),
            health_service._alert_thresholds(),
        )
        db.session.commit()
        return ok(data=[station_status_to_dict(snapshot)])
    return ok(data=health_service.refresh_all(), message="Health status refreshed.")
