"""Database queries for sensors."""

from app.extensions import db
from app.models import Measurement, Sensor, Station


class SensorRepository:
    @staticmethod
    def find_by_id(sensor_id):
        return db.session.get(Sensor, sensor_id)

    @staticmethod
    def list_sensors(filters, page, per_page):
        query = Sensor.query.filter_by(is_archived=filters["is_archived"])

        if filters.get("search"):
            term = f"%{filters['search']}%"
            query = query.filter(
                db.or_(
                    Sensor.name.ilike(term),
                    Sensor.model.ilike(term),
                    Sensor.serial_number.ilike(term),
                    Sensor.port_number.ilike(term),
                )
            )
        if filters.get("station_id"):
            query = query.filter_by(station_id=filters["station_id"])
        if filters.get("status"):
            query = query.filter_by(operational_status=filters["status"])

        return query.order_by(Sensor.name).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def measurements_for_sensor(sensor_id, page, per_page):
        return (
            Measurement.query.filter_by(sensor_id=sensor_id)
            .order_by(Measurement.observation_time.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def latest_measurement_for_sensor(sensor_id):
        return (
            Measurement.query.filter_by(sensor_id=sensor_id)
            .order_by(Measurement.observation_time.desc())
            .first()
        )

    @staticmethod
    def station_exists(station_id):
        return db.session.get(Station, station_id) is not None
