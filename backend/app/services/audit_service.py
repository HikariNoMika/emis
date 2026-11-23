"""Central audit-logging service (framework-independent)."""

from datetime import date, datetime
from decimal import Decimal

from app.extensions import db
from app.models import AuditLog
from app.utils.request_context import get_request_info
from app.utils.time import utcnow


def _json_safe(value):
    """Convert dates/decimals into JSON-friendly values for JSONB storage."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def log_action(
    action,
    module,
    record_identifier=None,
    previous_values=None,
    new_values=None,
    user_id=None,
    commit=True,
):
    """Create an audit log entry. User/IP metadata comes from request context."""
    info = get_request_info()
    if user_id is None:
        user_id = info.get("user_id")

    entry = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        record_identifier=str(record_identifier) if record_identifier else None,
        previous_values=_json_safe(previous_values) if previous_values else None,
        new_values=_json_safe(new_values) if new_values else None,
        ip_address=info.get("ip_address"),
        user_agent=info.get("user_agent"),
        occurred_at=utcnow(),
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
