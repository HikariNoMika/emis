"""Data-quality flag queries and resolution."""

from app.extensions import db
from app.models import DataQualityFlag
from app.utils.serializers import quality_flag_to_dict
from app.utils.time import utcnow

from .audit_service import log_action
from .exceptions import NotFoundError


def summary():
    """Counts for the quality dashboard."""
    flags = DataQualityFlag.query.all()
    by_status = {}
    by_severity = {}
    for flag in flags:
        by_status[flag.quality_status] = by_status.get(flag.quality_status, 0) + 1
        by_severity[flag.severity] = by_severity.get(flag.severity, 0) + 1
    return {
        "total_flags": len(flags),
        "open_flags": sum(1 for flag in flags if flag.resolution_status == "OPEN"),
        "by_status": by_status,
        "by_severity": by_severity,
    }


def list_flags(filters, page, per_page):
    query = DataQualityFlag.query
    for field in (
        "station_id", "measurement_type_id", "quality_status",
        "severity", "resolution_status",
    ):
        if filters.get(field):
            query = query.filter(getattr(DataQualityFlag, field) == filters[field])
    return query.order_by(DataQualityFlag.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_flag(flag_id):
    flag = db.session.get(DataQualityFlag, flag_id)
    if flag is None:
        raise NotFoundError("Quality flag not found.")
    return flag


def resolve_flag(flag, resolution_status, remarks, user_id):
    """Record how an administrator resolved a flag. Never edits source data."""
    if flag.resolution_status == resolution_status and flag.admin_remarks == remarks:
        return flag  # nothing changed

    previous = {
        "resolution_status": flag.resolution_status,
        "admin_remarks": flag.admin_remarks,
    }
    flag.resolution_status = resolution_status
    flag.admin_remarks = remarks
    if resolution_status in {"RESOLVED", "IGNORED"}:
        flag.resolved_at = utcnow()
        flag.resolved_by_id = user_id
    else:
        flag.resolved_at = None
        flag.resolved_by_id = None

    log_action(
        "QUALITY_FLAG_RESOLVED",
        "data_quality",
        record_identifier=flag.id,
        previous_values=previous,
        new_values={
            "resolution_status": flag.resolution_status,
            "admin_remarks": flag.admin_remarks,
        },
        user_id=user_id,
        commit=False,
    )
    db.session.commit()
    return flag
