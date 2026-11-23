"""Alerts and their status-change history."""

from app.extensions import db
from app.utils.time import utcnow

from .base import TimestampMixin


class Alert(TimestampMixin, db.Model):
    """An alert raised by a rule, an import, or an administrator.

    `condition_key` prevents duplicate alerts for the same ongoing problem,
    e.g. `LOW_BATTERY:<station_id>:<sensor_id>`. While an alert with that key is
    active, the rule engine updates `last_seen_at` instead of creating a new row.
    """

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    alert_number = db.Column(db.String(60), unique=True, nullable=False, index=True)

    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    sensor_id = db.Column(
        db.Integer, db.ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True
    )
    category = db.Column(
        db.String(40), nullable=False, index=True
    )  # ENVIRONMENTAL, EQUIPMENT, BATTERY, COMMUNICATION,
       # MISSING_DATA, DATA_QUALITY, CALIBRATION, MAINTENANCE
    severity = db.Column(
        db.String(20), nullable=False, default="INFO", index=True
    )  # INFO | WARNING | CRITICAL
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(20), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE | ACKNOWLEDGED | RESOLVED
    condition_key = db.Column(db.String(255), nullable=True, index=True)

    first_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    acknowledged_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    remarks = db.Column(db.Text, nullable=True)

    station = db.relationship("Station")
    sensor = db.relationship("Sensor")
    acknowledged_by = db.relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id])
    history = db.relationship(
        "AlertHistory", back_populates="alert", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Alert {self.alert_number} {self.status}>"


class AlertHistory(db.Model):
    """Immutable trail of every status change on an alert."""

    __tablename__ = "alert_history"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(
        db.Integer, db.ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    action = db.Column(db.String(40), nullable=False)
    previous_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    performed_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )

    alert = db.relationship("Alert", back_populates="history")
    performed_by = db.relationship("User")

    def __repr__(self):
        return f"<AlertHistory alert_id={self.alert_id} action={self.action}>"
