"""Database queries for measurements, trends and statistics."""

from app.extensions import db
from app.models import Measurement, MeasurementType, Station


class MeasurementRepository:
    @staticmethod
    def list_measurements(filters, page, per_page, date_from=None, date_to=None):
        query = Measurement.query
        if filters.get("station_id"):
            query = query.filter_by(station_id=filters["station_id"])
        if filters.get("sensor_id"):
            query = query.filter_by(sensor_id=filters["sensor_id"])
        if filters.get("measurement_type_id"):
            query = query.filter_by(measurement_type_id=filters["measurement_type_id"])
        if filters.get("quality_status"):
            query = query.filter_by(quality_status=filters["quality_status"])
        if date_from:
            query = query.filter(Measurement.observation_time >= date_from)
        if date_to:
            query = query.filter(Measurement.observation_time <= date_to)
        return query.order_by(Measurement.observation_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def latest_for_station(station_id, limit=200):
        return (
            Measurement.query.filter_by(station_id=station_id)
            .order_by(Measurement.observation_time.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def all_latest(limit=1000):
        return Measurement.query.order_by(
            Measurement.observation_time.desc()
        ).limit(limit).all()

    @staticmethod
    def for_trends(station_id, type_ids, date_from=None, date_to=None):
        query = Measurement.query.filter_by(station_id=station_id).filter(
            Measurement.measurement_type_id.in_(type_ids)
        )
        if date_from:
            query = query.filter(Measurement.observation_time >= date_from)
        if date_to:
            query = query.filter(Measurement.observation_time <= date_to)
        return query.order_by(Measurement.observation_time.asc()).all()

    @staticmethod
    def for_statistics(station_id, type_id, date_from=None, date_to=None):
        query = Measurement.query.filter_by(measurement_type_id=type_id)
        if station_id:
            query = query.filter_by(station_id=station_id)
        if date_from:
            query = query.filter(Measurement.observation_time >= date_from)
        if date_to:
            query = query.filter(Measurement.observation_time <= date_to)
        return query.order_by(Measurement.observation_time.asc()).all()

    @staticmethod
    def station_timezone(station_id):
        station = db.session.get(Station, station_id)
        return station.measurement_interval_seconds if station else 900

    @staticmethod
    def get_type(type_id):
        return db.session.get(MeasurementType, type_id)
