"""Station endpoints."""

from fastapi import APIRouter, Depends, Query

from app.extensions import db
from app.repositories.station_repository import StationRepository
from app.schemas import ClearDataSchema, StationQuerySchema, StationSchema
from app.services import station_service
from app.services.exceptions import NotFoundError
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import station_to_dict

stations_bp = APIRouter()


@stations_bp.get("")
def list_stations(filters: StationQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = StationRepository.list_stations(
        data, data["page"], data["per_page"]
    )
    return paginated(
        [station_to_dict(s) for s in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@stations_bp.post("", status_code=201)
def create_station(payload: StationSchema, user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not data.get("station_code") or not data.get("name"):
        from app.utils.responses import error
        return error("station_code and name are required.", 400, errors={
            "station_code": ["This field is required."]
        })
    station = station_service.create_station(data, user.id)
    return ok(data=station_to_dict(station), message="Station created.")


@stations_bp.get("/map-data")
def map_data(user=Depends(get_current_user)):
    return ok(data=station_service.map_data())


@stations_bp.get("/{station_id}")
def get_station(station_id: int, user=Depends(get_current_user)):
    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")
    return ok(data=station_service.station_detail(station))


@stations_bp.put("/{station_id}")
def update_station(station_id: int, payload: StationSchema, user=Depends(get_current_user)):
    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")
    data = payload.model_dump(exclude_unset=True)
    station_service.update_station(station, data, user.id)
    return ok(data=station_to_dict(station), message="Station updated.")


@stations_bp.delete("/{station_id}")
def archive_station(station_id: int, user=Depends(get_current_user)):
    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")
    station_service.archive_station(station, user.id)
    return ok(message="Station archived. Historical data was preserved.")


@stations_bp.delete("/{station_id}/data")
def clear_station_data(station_id: int, payload: ClearDataSchema, user=Depends(get_current_user)):
    """Permanently delete all readings and imports for one station.

    The station and its sensors are kept. Requires the administrator's current
    password as a safety check, since this action cannot be undone.
    """
    from app.utils.security import verify_password
    from app.models import User

    current_user = db.session.get(User, user.id)
    if current_user is None or not verify_password(current_user.password_hash, payload.password):
        from app.utils.responses import error
        return error("Incorrect password. Data was not cleared.", 403)

    station = StationRepository.find_by_id(station_id)
    if station is None:
        raise NotFoundError("Station not found.")
    result = station_service.clear_station_data(station, user.id)
    return ok(
        data=result,
        message=(
            f"Cleared {result['measurements_deleted']:,} readings and "
            f"{result['import_batches_deleted']} import(s) for {station.name}."
        ),
    )


@stations_bp.get("/{station_id}/sensors")
def station_sensors(station_id: int, user=Depends(get_current_user)):
    items, _ = station_service.related_records(station_id, "sensors")
    return ok(data=items)


@stations_bp.get("/{station_id}/measurements")
def station_measurements(
    station_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    measurement_type_id: int | None = None,
    user=Depends(get_current_user),
):
    items, pagination = station_service.related_records(
        station_id, "measurements", page, per_page, measurement_type_id
    )
    return paginated(items, page, per_page, pagination.total if pagination else 0)


@stations_bp.get("/{station_id}/status")
def station_status(station_id: int, user=Depends(get_current_user)):
    return ok(data=station_service.related_records(station_id, "status")[0])


@stations_bp.get("/{station_id}/maintenance")
def station_maintenance(station_id: int, user=Depends(get_current_user)):
    return ok(data=station_service.related_records(station_id, "maintenance")[0])


@stations_bp.get("/{station_id}/imports")
def station_imports(station_id: int, user=Depends(get_current_user)):
    return ok(data=station_service.related_records(station_id, "imports")[0])


@stations_bp.get("/{station_id}/history")
def station_history(station_id: int, user=Depends(get_current_user)):
    return ok(data=station_service.station_history(station_id))
