"""Automated data-quality findings."""

from app.extensions import db
from app.utils.time import utcnow

from .base import TimestampMixin


class DataQualityFlag(TimestampMixin, db.Model):
    """A quality check result attached to a measurement (or to a missing slot).

    Quality checks NEVER change the source measurement. They only create or
    update these flags. That is why severity, explanation and resolution are
    stored separately from the value itself.
    """

    __tablename__ = "data_quality_flags"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    sensor_id = db.Column(
        db.Integer, db.ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True
    )
    measurement_type_id = db.Column(
        db.Integer, db.ForeignKey("measurement_types.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    # Note: measurements has a composite primary key (id, observation_time),
    # so a single-column foreign key to measurements.id is not valid in
    # PostgreSQL. We keep the id as a plain string reference plus the station /
    # type / timestamp columns, which together locate the exact measurement.
    measurement_id = db.Column(db.String(36), nullable=True, index=True)
    import_batch_id = db.Column(
        db.Integer, db.ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    observation_time = db.Column(
        db.DateTime(timezone=True), nullable=True, index=True
    )
    original_value = db.Column(db.Numeric(18, 6), nullable=True)
    unit = db.Column(db.String(40), nullable=True)

    rule_code = db.Column(db.String(80), nullable=False, index=True)
    quality_status = db.Column(
        db.String(20), nullable=False, default="UNVERIFIED", index=True
    )  # VALID | SUSPECT | INVALID | MISSING | UNVERIFIED
    severity = db.Column(
        db.String(20), nullable=False, default="INFO", index=True
    )  # INFO | WARNING | CRITICAL
    expected_range = db.Column(db.String(100), nullable=True)
    actual_condition = db.Column(db.String(255), nullable=True)
    explanation = db.Column(db.Text, nullable=True)

    resolution_status = db.Column(
        db.String(20), nullable=False, default="OPEN", index=True
    )  # OPEN | ACKNOWLEDGED | RESOLVED | IGNORED
    admin_remarks = db.Column(db.Text, nullable=True)
    resolved_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    station = db.relationship("Station")
    sensor = db.relationship("Sensor")
    measurement_type = db.relationship(
        "MeasurementType", back_populates="quality_flags"
    )
    resolved_by = db.relationship("User")

    def __repr__(self):
        return f"<DataQualityFlag {self.rule_code} status={self.quality_status}>"
