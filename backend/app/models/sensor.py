"""Sensors / equipment and the measurement types they produce."""

from app.extensions import db
from app.utils.db_types import jsonb

from .base import TimestampMixin


class Sensor(TimestampMixin, db.Model):
    """A sensor or data-logging device installed at a station.

    Stations do NOT all have the same ports or sensors, so there is no assumption
    about identical equipment. A port is just a label used by the importer.
    """

    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    port_number = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    model = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=True)
    serial_number = db.Column(db.String(100), nullable=True, index=True)

    installation_date = db.Column(db.Date, nullable=True)
    calibration_date = db.Column(db.Date, nullable=True)
    next_calibration_date = db.Column(db.Date, nullable=True)

    operational_status = db.Column(
        db.String(30), nullable=False, default="ACTIVE", index=True
    )
    description = db.Column(db.Text, nullable=True)
    # Free-form device configuration (addresses, scaling factors, etc.).
    configuration = db.Column(jsonb(), nullable=True, default=dict)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, index=True)

    station = db.relationship("Station", back_populates="sensors")
    measurement_type_links = db.relationship(
        "SensorMeasurementType",
        back_populates="sensor",
        cascade="all, delete-orphan",
    )
    measurements = db.relationship("Measurement", back_populates="sensor")
    maintenance_records = db.relationship(
        "MaintenanceRecord", back_populates="sensor"
    )

    def __repr__(self):
        return f"<Sensor {self.name} station_id={self.station_id}>"


class SensorMeasurementType(db.Model):
    """Flexible link table between a sensor and the values it produces.

    This solves the VP-4 style case where ONE physical sensor reports air
    temperature, relative humidity, pressure and VPD. Storing the relationship
    as rows (instead of fixed columns on `sensors`) means new measurement types
    can be added without changing the equipment schema.

    `column_hint` remembers the original spreadsheet column name, which helps
    the importer map future files from the same station.
    """

    __tablename__ = "sensor_measurement_types"
    __table_args__ = (
        db.UniqueConstraint(
            "sensor_id", "measurement_type_id", "column_hint",
            name="uq_sensor_measurement_column",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(
        db.Integer, db.ForeignKey("sensors.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    measurement_type_id = db.Column(
        db.Integer, db.ForeignKey("measurement_types.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    column_hint = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now())

    sensor = db.relationship("Sensor", back_populates="measurement_type_links")
    measurement_type = db.relationship(
        "MeasurementType", back_populates="sensor_links"
    )

    def __repr__(self):
        return (
            f"<SensorMeasurementType sensor_id={self.sensor_id} "
            f"type_id={self.measurement_type_id}>"
        )
