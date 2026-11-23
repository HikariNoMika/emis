"""Audit logs and configurable system settings."""

from app.extensions import db
from app.utils.db_types import jsonb
from app.utils.time import utcnow

from .base import TimestampMixin


class AuditLog(TimestampMixin, db.Model):
    """Record of an important administrative action.

    `previous_values` and `new_values` are JSONB snapshots. They let an auditor
    answer "who changed this station's coordinates, and from what to what?".
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        index=True
    )
    action = db.Column(db.String(80), nullable=False, index=True)
    module = db.Column(db.String(60), nullable=False, index=True)
    record_identifier = db.Column(db.String(100), nullable=True, index=True)
    previous_values = db.Column(jsonb(), nullable=True)
    new_values = db.Column(jsonb(), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    occurred_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by user_id={self.user_id}>"


class SystemSetting(TimestampMixin, db.Model):
    """A key/value setting stored as JSONB.

    Examples: station_status_thresholds, data_quality_rules, alert_thresholds,
    import_settings, default_timezone, report_settings.
    """

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(jsonb(), nullable=False, default=dict)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    updated_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self):
        return f"<SystemSetting {self.key}>"
