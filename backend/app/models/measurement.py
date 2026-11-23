"""Measurement type definitions and the time-series measurement records."""

import uuid

from app.extensions import db
from app.utils.time import utcnow

from .base import TimestampMixin


class MeasurementType(TimestampMixin, db.Model):
    """A kind of environmental value, e.g. 'air_temperature'.

    Keeping types in a table (rather than hard-coded strings) makes the system
    expandable: adding a new parameter is a data change, not a code change.
    """

    __tablename__ = "measurement_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(
        db.String(50), nullable=False, index=True
    )  # ATMOSPHERIC, WIND, PRECIPITATION, SOLAR, SOIL, EQUIPMENT
    unit = db.Column(db.String(40), nullable=False)
    expected_min = db.Column(db.Numeric(18, 6), nullable=True)
    expected_max = db.Column(db.Numeric(18, 6), nullable=True)
    # Wind direction is circular (0 and 360 are the same) and needs special stats.
    is_circular = db.Column(db.Boolean, nullable=False, default=False)
    # How values should be aggregated: AVG, SUM, CIRCULAR_MEAN, NONE.
    aggregation_method = db.Column(db.String(30), nullable=False, default="AVG")
    description = db.Column(db.Text, nullable=True)

    sensor_links = db.relationship(
        "SensorMeasurementType", back_populates="measurement_type"
    )
    measurements = db.relationship("Measurement", back_populates="measurement_type")
    quality_flags = db.relationship(
        "DataQualityFlag", back_populates="measurement_type"
    )

    def __repr__(self):
        return f"<MeasurementType {self.code}>"


class Measurement(db.Model):
    """One normalized environmental reading at one point in time.

    This is the only table converted into a TimescaleDB hypertable.

    TimescaleDB rule: every unique index (and the primary key) must contain the
    time-partitioning column. That is why `observation_time` is part of the
    composite primary key and of the duplicate-prevention unique constraint.

    We use a UUID string for `id` instead of an auto-incrementing integer so the
    same model works on PostgreSQL and on SQLite (used by the tests) without
    special sequence handling.

    Original data is never destroyed:
      * `raw_payload` on RawImportRecord keeps the untouched spreadsheet row;
      * `original_value` / `original_text` keep what the file said;
      * `normalized_value` holds any converted value we compute ourselves.
    """

    __tablename__ = "measurements"
    __table_args__ = (
        db.UniqueConstraint(
            "station_id",
            "sensor_id",
            "measurement_type_id",
            "observation_time",
            name="uq_measurement_station_sensor_type_time",
        ),
        db.Index("ix_measurements_type_time", "measurement_type_id", "observation_time"),
        db.Index("ix_measurements_station_time", "station_id", "observation_time"),
        db.Index("ix_measurements_sensor_time", "sensor_id", "observation_time"),
        db.Index(
            "ix_measurements_station_type_time",
            "station_id", "measurement_type_id", "observation_time",
        ),
    )

    # Composite primary key: UUID + observation time (required by TimescaleDB).
    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    observation_time = db.Column(
        db.DateTime(timezone=True), nullable=False, primary_key=True, index=True
    )

    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    sensor_id = db.Column(
        db.Integer, db.ForeignKey("sensors.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    measurement_type_id = db.Column(
        db.Integer, db.ForeignKey("measurement_types.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    import_batch_id = db.Column(
        db.Integer, db.ForeignKey("import_batches.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    raw_import_record_id = db.Column(
        db.Integer, db.ForeignKey("raw_import_records.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )

    original_value = db.Column(db.Numeric(18, 6), nullable=True)
    original_text = db.Column(db.String(100), nullable=True)
    normalized_value = db.Column(db.Numeric(18, 6), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    quality_status = db.Column(
        db.String(20), nullable=False, default="UNVERIFIED", index=True
    )
    source_record_identifier = db.Column(db.String(150), nullable=True, index=True)

    # Distinguish observation time (from the file) from processing time (ours).
    processed_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    station = db.relationship("Station", back_populates="measurements")
    sensor = db.relationship("Sensor", back_populates="measurements")
    measurement_type = db.relationship(
        "MeasurementType", back_populates="measurements"
    )
    import_batch = db.relationship("ImportBatch", back_populates="measurements")
    raw_record = db.relationship("RawImportRecord", back_populates="measurements")

    def __repr__(self):
        return (
            f"<Measurement {self.measurement_type_id} "
            f"@ {self.observation_time} = {self.normalized_value}>"
        )
