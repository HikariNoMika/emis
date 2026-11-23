"""System health, settings and audit-log queries."""

from sqlalchemy import text

from app.extensions import db
from app.models import AuditLog, SystemSetting
from app.utils.time import utcnow

from .audit_service import log_action


def database_is_reachable():
    """Run a trivial query to confirm the database connection works."""
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception:
        db.session.rollback()
        return False


def health_payload():
    """Build the public health-check response (no credentials or secrets)."""
    db_ok = database_is_reachable()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "server_time": utcnow().isoformat(),
        "api_version": "v1",
    }


def list_settings():
    """Return all system settings as a key -> value dictionary."""
    settings = SystemSetting.query.order_by(SystemSetting.key).all()
    return {setting.key: setting.value for setting in settings}


def update_setting(key, value, user_id, description=None, category=None):
    """Insert or update one setting and record the change in the audit log."""
    setting = SystemSetting.query.filter_by(key=key).first()
    previous = setting.value if setting else None

    if setting is None:
        setting = SystemSetting(key=key)
        db.session.add(setting)

    setting.value = value
    if description is not None:
        setting.description = description
    if category is not None:
        setting.category = category

    log_action(
        "SYSTEM_SETTING_UPDATED",
        "system",
        record_identifier=key,
        previous_values={"value": previous},
        new_values={"value": value},
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return setting


def list_audit_logs(filters, page, per_page):
    """Return a paginated query result for the audit-log viewer."""
    query = AuditLog.query

    if filters.get("user_id"):
        query = query.filter(AuditLog.user_id == filters["user_id"])
    if filters.get("module"):
        query = query.filter(AuditLog.module == filters["module"])
    if filters.get("action"):
        query = query.filter(AuditLog.action == filters["action"])
    if filters.get("date_from"):
        query = query.filter(AuditLog.occurred_at >= filters["date_from"])
    if filters.get("date_to"):
        query = query.filter(AuditLog.occurred_at <= filters["date_to"])

    query = query.order_by(AuditLog.occurred_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination
