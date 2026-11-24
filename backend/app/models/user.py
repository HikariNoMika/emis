"""User accounts and login history."""

from app.extensions import db
from app.utils.time import utcnow

from .base import TimestampMixin


class User(TimestampMixin, db.Model):
    """An administrator account.

    Only administrators exist in phase 1. The role column is kept so other
    roles (e.g. viewer) can be added later without a schema change.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="admin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Multi-factor authentication (TOTP). Secret is only set after enrolment;
    # recovery codes are stored hashed and single-use.
    mfa_secret = db.Column(db.String(64), nullable=True)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    mfa_recovery_codes = db.Column(db.JSON, nullable=True, default=list)

    # Relationships (convenience only; foreign keys live on the child tables).
    login_history = db.relationship(
        "LoginHistory", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = db.relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"


class LoginHistory(db.Model):
    """A record of each successful login / logout event."""

    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event = db.Column(db.String(20), nullable=False)  # LOGIN or LOGOUT
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    occurred_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = db.relationship("User", back_populates="login_history")

    def __repr__(self):
        return f"<LoginHistory {self.event} user_id={self.user_id}>"
