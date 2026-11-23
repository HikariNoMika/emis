"""Maintenance and calibration records."""

from app.extensions import db

from .base import TimestampMixin


class MaintenanceRecord(TimestampMixin, db.Model):
    """Work performed on a station or a specific sensor.

    `sensor_id` is optional so a technician can log general station visits as
    well as sensor-specific calibration work.
    """

    __tablename__ = "maintenance_records"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    sensor_id = db.Column(
        db.Integer, db.ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True,
        index=True
    )
    maintenance_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # ROUTINE, CORRECTIVE, CALIBRATION, REPLACEMENT, INSPECTION
    maintenance_date = db.Column(db.Date, nullable=False, index=True)
    performed_by = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    findings = db.Column(db.Text, nullable=True)
    action_taken = db.Column(db.Text, nullable=True)
    calibration_details = db.Column(db.Text, nullable=True)
    next_maintenance_date = db.Column(db.Date, nullable=True, index=True)
    remarks = db.Column(db.Text, nullable=True)

    station = db.relationship("Station", back_populates="maintenance_records")
    sensor = db.relationship("Sensor", back_populates="maintenance_records")

    def __repr__(self):
        return (
            f"<MaintenanceRecord station_id={self.station_id} "
            f"type={self.maintenance_type}>"
        )
