"""Alert lifecycle: creation with deduplication, acknowledgement and resolution."""

import uuid

from app.extensions import db
from app.models import Alert, AlertHistory
from app.utils.time import utcnow

from .audit_service import log_action
from .exceptions import ConflictError, NotFoundError


def raise_alert(category, severity, title, message, condition_key,
                station_id=None, sensor_id=None):
    """
    Create an alert, or update an existing ongoing one.

    The condition_key (e.g. LOW_BATTERY:3:5) prevents repeated alerts for the
    same condition. While the alert is active we only refresh last_seen_at.
    """
    existing = None
    if condition_key:
        existing = Alert.query.filter_by(
            condition_key=condition_key, status="ACTIVE"
        ).first()

    if existing:
        existing.last_seen_at = utcnow()
        # Escalate severity if a later reading is worse.
        severity_rank = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}
        if severity_rank.get(severity, 0) > severity_rank.get(existing.severity, 0):
            existing.severity = severity
        db.session.commit()
        return existing

    alert = Alert(
        alert_number=f"ALT-{uuid.uuid4().hex[:10].upper()}",
        category=category,
        severity=severity,
        title=title,
        message=message,
        condition_key=condition_key,
        station_id=station_id,
        sensor_id=sensor_id,
        status="ACTIVE",
        first_seen_at=utcnow(),
        last_seen_at=utcnow(),
    )
    db.session.add(alert)
    db.session.flush()
    db.session.add(
        AlertHistory(
            alert_id=alert.id,
            action="CREATED",
            new_status="ACTIVE",
            created_at=utcnow(),
        )
    )
    db.session.commit()
    return alert


def list_alerts(filters, page, per_page):
    query = Alert.query
    for field in ("station_id", "category", "severity", "status"):
        if filters.get(field):
            query = query.filter(getattr(Alert, field) == filters[field])
    return query.order_by(Alert.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_alert(alert_id):
    alert = db.session.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError("Alert not found.")
    return alert


def _change_status(alert, action, new_status, user_id, remarks):
    if alert.status == new_status:
        raise ConflictError(f"Alert is already {new_status}.")

    previous = alert.status
    alert.status = new_status
    alert.remarks = remarks or alert.remarks

    if new_status == "ACKNOWLEDGED":
        alert.acknowledged_by_id = user_id
        alert.acknowledged_at = utcnow()
    elif new_status == "RESOLVED":
        alert.resolved_by_id = user_id
        alert.resolved_at = utcnow()

    db.session.add(
        AlertHistory(
            alert_id=alert.id,
            action=action,
            previous_status=previous,
            new_status=new_status,
            remarks=remarks,
            performed_by_id=user_id,
            created_at=utcnow(),
        )
    )
    log_action(
        action,
        "alerts",
        record_identifier=alert.alert_number,
        previous_values={"status": previous},
        new_values={"status": new_status, "remarks": remarks},
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return alert


def acknowledge(alert, user_id, remarks):
    return _change_status(alert, "ALERT_ACKNOWLEDGED", "ACKNOWLEDGED", user_id, remarks)


def resolve(alert, user_id, remarks):
    return _change_status(alert, "ALERT_RESOLVED", "RESOLVED", user_id, remarks)


def history(alert_id):
    get_alert(alert_id)
    rows = (
        AlertHistory.query.filter_by(alert_id=alert_id)
        .order_by(AlertHistory.created_at.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "action": row.action,
            "previous_status": row.previous_status,
            "new_status": row.new_status,
            "remarks": row.remarks,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
