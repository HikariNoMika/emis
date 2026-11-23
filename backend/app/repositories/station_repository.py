"""Database queries for stations and their related records."""

from app.extensions import db
from app.models import (
    ImportBatch,
    MaintenanceRecord,
    Measurement,
    Sensor,
    Station,
    StationStatus,
)


class StationRepository:
    @staticmethod
    def find_by_id(station_id):
        return db.session.get(Station, station_id)

    @staticmethod
    def find_by_code(station_code, exclude_id=None):
        query = Station.query.filter_by(station_code=station_code)
        if exclude_id is not None:
            query = query.filter(Station.id != exclude_id)
        return query.first()

    @staticmethod
    def list_stations(filters, page, per_page):
        """Search and filter stations, then paginate the result."""
        query = Station.query.filter_by(is_archived=filters["is_archived"])

        if filters.get("search"):
            term = f"%{filters['search']}%"
            query = query.filter(
                db.or_(
                    Station.station_code.ilike(term),
                    Station.name.ilike(term),
                    Station.site_name.ilike(term),
                    Station.device_serial_number.ilike(term),
                )
            )
        if filters.get("status"):
            query = query.filter(Station.operational_status == filters["status"])

        return query.order_by(Station.name).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def list_all_active():
        """All non-archived stations (used by the map and dropdown lists)."""
        return Station.query.filter_by(is_archived=False).order_by(Station.name).all()

    @staticmethod
    def sensors_for_station(station_id, include_archived=False):
        query = Sensor.query.filter_by(station_id=station_id)
        if not include_archived:
            query = query.filter_by(is_archived=False)
        return query.order_by(Sensor.port_number, Sensor.name).all()

    @staticmethod
    def measurements_for_station(station_id, page, per_page, measurement_type_id=None):
        query = Measurement.query.filter_by(station_id=station_id)
        if measurement_type_id:
            query = query.filter_by(measurement_type_id=measurement_type_id)
        return query.order_by(Measurement.observation_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def status_history(station_id, limit=50):
        return (
            StationStatus.query.filter_by(station_id=station_id)
            .order_by(StationStatus.recorded_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def maintenance_for_station(station_id):
        return (
            MaintenanceRecord.query.filter_by(station_id=station_id)
            .order_by(MaintenanceRecord.maintenance_date.desc())
            .all()
        )

    @staticmethod
    def imports_for_station(station_id):
        return (
            ImportBatch.query.filter_by(station_id=station_id)
            .order_by(ImportBatch.file_imported_at.desc())
            .all()
        )
