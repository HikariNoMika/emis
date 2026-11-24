"""Monitoring stations and their health snapshots."""

from app.constants import STATION_TYPES
from app.extensions import db
from app.utils.time import utcnow

from .base import TimestampMixin


class Station(TimestampMixin, db.Model):
    """A physical environmental monitoring station.

    Stations are never hard-deleted once measurements exist. Instead we set
    `is_archived = True`, which hides the station from normal lists while
    keeping all of its history intact.
    """

    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    station_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    # Which family of source/view this station belongs to (AWS, AWLS, ...).
    station_type = db.Column(
        db.String(30), nullable=False, default="AWS", index=True
    )
    site_name = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # GPS coordinates. Both may be null until a survey is available — the map
    # simply skips stations without coordinates instead of plotting (0, 0).
    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)
    elevation = db.Column(db.Numeric(10, 2), nullable=True)

    timezone = db.Column(db.String(64), nullable=False, default="Asia/Manila")
    measurement_interval_seconds = db.Column(
        db.Integer, nullable=False, default=900
    )
    installation_date = db.Column(db.Date, nullable=True)

    operational_status = db.Column(
        db.String(30), nullable=False, default="UNKNOWN", index=True
    )
    device_serial_number = db.Column(db.String(100), nullable=True, index=True)
    remarks = db.Column(db.Text, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, index=True)

    # Relationships
    sensors = db.relationship(
        "Sensor", back_populates="station", cascade="all, delete-orphan"
    )
    measurements = db.relationship("Measurement", back_populates="station")
    import_batches = db.relationship("ImportBatch", back_populates="station")
    maintenance_records = db.relationship(
        "MaintenanceRecord", back_populates="station"
    )
    status_snapshots = db.relationship("StationStatus", back_populates="station")

    def __repr__(self):
        return f"<Station {self.station_code} {self.name}>"


class StationStatus(db.Model):
    """A point-in-time health snapshot for a station.

    Several snapshots are kept so historical freshness can be charted. The
    latest row (highest id / recorded_at) is the current status.

    IMPORTANT: `data_freshness` and `connectivity_state` are separate fields.
    A late Excel upload means stale DATA, not necessarily a broken station.
    """

    __tablename__ = "station_status"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    status = db.Column(
        db.String(20), nullable=False, default="UNKNOWN", index=True
    )  # ONLINE, DELAYED, OFFLINE, MAINTENANCE, UNKNOWN
    last_observation_time = db.Column(db.DateTime(timezone=True), nullable=True)
    expected_next_time = db.Column(db.DateTime(timezone=True), nullable=True)
    data_freshness_minutes = db.Column(db.Integer, nullable=True)
    connectivity_state = db.Column(
        db.String(20), nullable=True
    )  # CONNECTED, DISCONNECTED, NOT_REPORTED
    battery_percentage = db.Column(db.Numeric(6, 2), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    station = db.relationship("Station", back_populates="status_snapshots")

    def __repr__(self):
        return f"<StationStatus station_id={self.station_id} status={self.status}>"
