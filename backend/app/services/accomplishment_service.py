"""Business logic for indicators, targets, actuals, weights and report lifecycle."""

import uuid
from decimal import Decimal

from app.extensions import db
from app.models import (
    AccomplishmentActual,
    AccomplishmentAuditLog,
    AccomplishmentCategory,
    AccomplishmentIndicator,
    AccomplishmentQuarterlyTarget,
    AccomplishmentReport,
    AccomplishmentReportSnapshot,
    AccomplishmentSetting,
    AccomplishmentWeightHistory,
)
from app.repositories.accomplishment_repository import AccomplishmentRepository as Repo
from app.utils.request_context import get_request_info
from app.utils.serializers import (
    accomplishment_actual_to_dict,
    accomplishment_indicator_to_dict,
    accomplishment_report_to_dict,
    accomplishment_target_to_dict,
)
from app.utils.time import utcnow

from . import accomplishment_calculator as calc
from . import accomplishment_validation as validation
from .audit_service import log_action
from .exceptions import ConflictError, NotFoundError, ValidationAppError

FORMULAS = {
    "indicator": "(actual / planned) * 100; N/A when planned is zero or missing",
    "capped": "min(indicator_percentage, 100) used only for weighted contribution",
    "category": "SUM(capped_indicator_percentage * indicator_weight) / 100",
    "overall": "(activity_score * activity_weight / 100) + (deliverable_score * deliverable_weight / 100)",
    "annual": "SUM(Q1..Q4 actuals) / SUM(Q1..Q4 approved targets) * 100 per indicator",
}


def _audit(action, record_id, previous=None, new=None, user_id=None):
    info = get_request_info()
    db.session.add(
        AccomplishmentAuditLog(
            user_id=user_id or info.get("user_id"),
            action=action,
            module="accomplishment",
            record_id=str(record_id) if record_id else None,
            previous_values=previous,
            new_values=new,
            ip_address=info.get("ip_address"),
        )
    )


def seed_defaults():
    """Create the two example categories and settings if they do not exist."""
    defaults = [
        ("ACTIVITY", "Activities", 50),
        ("DELIVERABLE", "Deliverables", 50),
    ]
    for code, name, weight in defaults:
        if Repo.category_by_code(code) is None:
            db.session.add(
                AccomplishmentCategory(
                    code=code, name=name, weight=weight,
                    description="Default example weight. Not an official standard.",
                )
            )
    if AccomplishmentSetting.query.filter_by(key="report_headers").first() is None:
        db.session.add(
            AccomplishmentSetting(
                key="report_headers",
                value={"agency": "Environmental Monitoring Information System"},
                description="Configurable report header. No official logo or signatory is assumed.",
            )
        )
    if AccomplishmentSetting.query.filter_by(key="example_weights_note").first() is None:
        db.session.add(
            AccomplishmentSetting(
                key="example_weights_note",
                value={"note": "50/50 category weights are configurable examples, not official standards."},
            )
        )
    db.session.commit()


# ---------------------------------------------------------------------------
# Categories and indicators
# ---------------------------------------------------------------------------
def categories():
    return [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "weight": float(item.weight),
            "description": item.description,
            "is_active": item.is_active,
        }
        for item in Repo.categories()
    ]


def indicators(year=None, category_code=None):
    return [
        accomplishment_indicator_to_dict(item)
        for item in Repo.indicators(year, category_code, active_only=False)
    ]


def get_indicator(indicator_id):
    indicator = Repo.indicator_by_id(indicator_id)
    if indicator is None:
        raise NotFoundError("Indicator not found.")
    return indicator


def create_indicator(data, user_id):
    category = Repo.category_by_code(data.pop("category_code"))
    if category is None:
        raise ValidationAppError("Unknown category code.")
    indicator = AccomplishmentIndicator(
        category_id=category.id, created_by_id=user_id, **data
    )
    db.session.add(indicator)
    db.session.flush()
    _audit("INDICATOR_CREATED", indicator.id, new=accomplishment_indicator_to_dict(indicator))
    log_action("ACCOMP_INDICATOR_CREATED", "accomplishment", indicator.id,
               new_values=accomplishment_indicator_to_dict(indicator), user_id=user_id,
               commit=False)
    db.session.commit()
    return indicator


def update_indicator(indicator, data, user_id):
    previous = accomplishment_indicator_to_dict(indicator)
    weight_changed = "indicator_weight" in data and data["indicator_weight"] != previous["indicator_weight"]
    old_weight = indicator.indicator_weight
    category_code = data.pop("category_code", None)
    if category_code:
        category = Repo.category_by_code(category_code)
        if category is None:
            raise ValidationAppError("Unknown category code.")
        indicator.category_id = category.id

    for field, value in data.items():
        setattr(indicator, field, value)

    if weight_changed:
        db.session.add(
            AccomplishmentWeightHistory(
                scope="INDICATOR",
                category_id=indicator.category_id,
                indicator_id=indicator.id,
                reporting_year=indicator.reporting_year,
                old_value=old_weight,
                new_value=indicator.indicator_weight,
                reason="Indicator weight updated",
                changed_by_id=user_id,
            )
        )
    _audit("INDICATOR_UPDATED", indicator.id, previous, accomplishment_indicator_to_dict(indicator))
    log_action("ACCOMP_INDICATOR_UPDATED", "accomplishment", indicator.id,
               previous_values=previous,
               new_values=accomplishment_indicator_to_dict(indicator),
               user_id=user_id, commit=False)
    db.session.commit()
    return indicator


# ---------------------------------------------------------------------------
# Targets and actuals
# ---------------------------------------------------------------------------
def delete_indicator(indicator, user_id):
    """Delete an indicator and its targets/actuals (cascaded by foreign keys)."""
    previous = accomplishment_indicator_to_dict(indicator)
    db.session.delete(indicator)
    _audit("INDICATOR_DELETED", indicator.id, previous=previous)
    log_action("ACCOMP_INDICATOR_DELETED", "accomplishment", indicator.id,
               previous_values=previous, user_id=user_id, commit=False)
    db.session.commit()


def create_target(data, user_id):
    if Repo.indicator_by_id(data["indicator_id"]) is None:
        raise ValidationAppError("Indicator does not exist.")
    existing = AccomplishmentQuarterlyTarget.query.filter_by(
        indicator_id=data["indicator_id"],
        reporting_year=data["reporting_year"],
        quarter=data["quarter"],
    ).first()
    if existing:
        raise ConflictError("A target already exists for this indicator, year and quarter.")
    target = AccomplishmentQuarterlyTarget(updated_by_id=user_id, **data)
    db.session.add(target)
    db.session.flush()
    _audit("TARGET_CREATED", target.id, new=accomplishment_target_to_dict(target))
    db.session.commit()
    return target


def update_target(target, data, user_id):
    previous = accomplishment_target_to_dict(target)
    for field, value in data.items():
        setattr(target, field, value)
    target.updated_by_id = user_id
    _audit("TARGET_UPDATED", target.id, previous, accomplishment_target_to_dict(target))
    db.session.commit()
    return target


def delete_target(target, user_id):
    """Remove a quarterly target. Snapshots of finalized reports are unaffected."""
    previous = accomplishment_target_to_dict(target)
    db.session.delete(target)
    _audit("TARGET_DELETED", target.id, previous=previous)
    log_action("ACCOMP_TARGET_DELETED", "accomplishment", target.id,
               previous_values=previous, user_id=user_id, commit=False)
    db.session.commit()


def targets(year=None, quarter=None, indicator_id=None):
    items = Repo.targets(year or 0, quarter)
    if indicator_id:
        items = [item for item in items if item.indicator_id == indicator_id]
    if year is None:
        items = AccomplishmentQuarterlyTarget.query.all()
    return [accomplishment_target_to_dict(item) for item in items]


def create_actual(data, user_id):
    if Repo.indicator_by_id(data["indicator_id"]) is None:
        raise ValidationAppError("Indicator does not exist.")
    if Repo.duplicate_actual_exists(
        data["indicator_id"], data["reporting_year"], data["quarter"],
        data["entry_reference"],
    ):
        raise ConflictError(
            "An accomplishment entry with this reference already exists for this quarter."
        )
    actual = AccomplishmentActual(entered_by_id=user_id, **data)
    db.session.add(actual)
    db.session.flush()
    _audit("ACTUAL_CREATED", actual.id, new=accomplishment_actual_to_dict(actual))
    log_action("ACCOMP_ACTUAL_CREATED", "accomplishment", actual.id,
               new_values=accomplishment_actual_to_dict(actual), user_id=user_id,
               commit=False)
    db.session.commit()
    return actual


def update_actual(actual, data, user_id):
    previous = accomplishment_actual_to_dict(actual)
    for field, value in data.items():
        setattr(actual, field, value)
    _audit("ACTUAL_UPDATED", actual.id, previous, accomplishment_actual_to_dict(actual))
    db.session.commit()
    return actual


def delete_actual(actual, user_id):
    """Remove an accomplishment entry (not an environmental measurement)."""
    previous = accomplishment_actual_to_dict(actual)
    db.session.delete(actual)
    _audit("ACTUAL_DELETED", actual.id, previous=previous)
    log_action("ACCOMP_ACTUAL_DELETED", "accomplishment", actual.id,
               previous_values=previous, user_id=user_id, commit=False)
    db.session.commit()


def actuals(year=None, quarter=None, indicator_id=None):
    if year is None:
        items = AccomplishmentActual.query.all()
    else:
        items = Repo.actuals(year, quarter)
    if indicator_id:
        items = [item for item in items if item.indicator_id == indicator_id]
    return [accomplishment_actual_to_dict(item) for item in items]


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------
def update_weights(data, user_id):
    """Validate and save both weight levels. Invalid totals are rejected."""
    category_weights = data["category_weights"]
    validation.validate_category_weights(category_weights)

    year = data["reporting_year"]
    indicators = Repo.indicators(year)
    updates = {item["indicator_id"]: Decimal(str(item["weight"])) for item in data["indicator_weights"]}

    # Apply indicator updates first so validation sees the proposed values.
    previous_weights = {}
    for indicator in indicators:
        previous_weights[indicator.id] = str(indicator.indicator_weight)
        if indicator.id in updates:
            indicator.indicator_weight = updates[indicator.id]
    validation.validate_indicator_weights(indicators)

    for code, weight in category_weights.items():
        category = Repo.category_by_code(code)
        if category is None:
            raise ValidationAppError(f"Unknown category '{code}'.")
        old = category.weight
        if Decimal(str(old)) != Decimal(str(weight)):
            category.weight = weight
            db.session.add(
                AccomplishmentWeightHistory(
                    scope="CATEGORY", category_id=category.id,
                    reporting_year=year, old_value=old, new_value=weight,
                    reason=data.get("reason") or "Category weight updated",
                    changed_by_id=user_id,
                )
            )
    for indicator in indicators:
        if indicator.id in updates and previous_weights[indicator.id] != str(updates[indicator.id]):
            db.session.add(
                AccomplishmentWeightHistory(
                    scope="INDICATOR", indicator_id=indicator.id,
                    category_id=indicator.category_id, reporting_year=year,
                    old_value=Decimal(previous_weights[indicator.id]),
                    new_value=updates[indicator.id],
                    reason=data.get("reason") or "Indicator weight updated",
                    changed_by_id=user_id,
                )
            )

    _audit("WEIGHTS_UPDATED", year, previous_weights,
           {str(key): str(value) for key, value in updates.items()})
    log_action("ACCOMP_WEIGHTS_UPDATED", "accomplishment", year,
               new_values={"category_weights": category_weights,
                           "indicator_weights": data["indicator_weights"]},
               user_id=user_id, commit=False)
    db.session.commit()
    return categories()


def weight_history():
    rows = AccomplishmentWeightHistory.query.order_by(
        AccomplishmentWeightHistory.changed_at.desc()
    ).limit(200).all()
    return [
        {
            "id": row.id,
            "scope": row.scope,
            "category_id": row.category_id,
            "indicator_id": row.indicator_id,
            "year": row.reporting_year,
            "old_value": float(row.old_value) if row.old_value is not None else None,
            "new_value": float(row.new_value),
            "reason": row.reason,
            "changed_by_id": row.changed_by_id,
            "changed_at": row.changed_at.isoformat() if row.changed_at else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _snapshot_payload(payload):
    year = payload["reporting_year"]
    quarter = payload.get("quarter")
    if quarter:
        data = calc.quarterly_summary(year, quarter)
    else:
        data = calc.annual_summary(year)
    return {
        "data": data,
        "weights": {
            "categories": categories(),
            "indicators": [
                {
                    "id": item["id"], "category": item["category_code"],
                    "weight": item["indicator_weight"], "year": item["reporting_year"],
                }
                for item in indicators(year)
            ],
        },
        "formulas": FORMULAS,
    }


def generate_report(payload, user_id):
    snapshot = _snapshot_payload(payload)
    report = AccomplishmentReport(
        report_number=f"ACC-{uuid.uuid4().hex[:10].upper()}",
        report_type=payload["report_type"],
        reporting_year=payload["reporting_year"],
        quarter=payload.get("quarter"),
        status="DRAFT",
        version=1,
        prepared_by=payload.get("prepared_by"),
        reviewed_by=payload.get("reviewed_by"),
        remarks=payload.get("remarks"),
        generated_at=utcnow(),
        created_by_id=user_id,
    )
    db.session.add(report)
    db.session.flush()
    db.session.add(
        AccomplishmentReportSnapshot(
            report_id=report.id, version=1,
            snapshot=snapshot["data"], weights=snapshot["weights"],
            formulas=snapshot["formulas"],
        )
    )
    _audit("REPORT_GENERATED", report.id, new=accomplishment_report_to_dict(report))
    db.session.commit()
    return report


def reports():
    return [
        accomplishment_report_to_dict(item)
        for item in AccomplishmentReport.query.order_by(
            AccomplishmentReport.created_at.desc()
        ).all()
    ]


def get_report(report_id):
    report = Repo.report_by_id(report_id)
    if report is None:
        raise NotFoundError("Accomplishment report not found.")
    return report


def report_detail(report_id):
    report = get_report(report_id)
    snapshots = [
        {
            "id": item.id,
            "version": item.version,
            "snapshot": item.snapshot,
            "weights": item.weights,
            "formulas": item.formulas,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in sorted(report.snapshots, key=lambda row: row.version, reverse=True)
    ]
    return {**accomplishment_report_to_dict(report), "snapshots": snapshots}


def finalize_report(report_id, user_id):
    """Validate, compute and freeze a report. Previous snapshots stay untouched."""
    report = get_report(report_id)
    if report.status in ("FINAL", "REVISED"):
        raise ConflictError("This report version is already finalized.")

    quarter = report.quarter
    if quarter:
        validation.ensure_can_finalize(report.reporting_year, quarter)
    else:
        # Annual finalization requires every quarter to be finalizable.
        for number in range(1, 5):
            validation.ensure_can_finalize(report.reporting_year, number)

    snapshot = _snapshot_payload(
        {"reporting_year": report.reporting_year, "quarter": quarter}
    )
    db.session.add(
        AccomplishmentReportSnapshot(
            report_id=report.id,
            version=report.version,
            snapshot=snapshot["data"],
            weights=snapshot["weights"],
            formulas=snapshot["formulas"],
        )
    )
    previous = accomplishment_report_to_dict(report)
    report.status = "FINAL"
    report.finalized_at = utcnow()
    report.finalized_by_id = user_id
    _audit("REPORT_FINALIZED", report.id, previous, accomplishment_report_to_dict(report))
    log_action("ACCOMP_REPORT_FINALIZED", "accomplishment", report.id,
               previous_values=previous,
               new_values=accomplishment_report_to_dict(report),
               user_id=user_id, commit=False)
    db.session.commit()
    return report


def revise_report(report_id, payload, user_id):
    """Create a new authorized revision linked to the previous version."""
    original = get_report(report_id)
    if original.status != "FINAL":
        raise ConflictError("Only a FINAL report can be revised.")

    snapshot = _snapshot_payload(
        {"reporting_year": original.reporting_year, "quarter": original.quarter}
    )
    revision = AccomplishmentReport(
        report_number=f"ACC-{uuid.uuid4().hex[:10].upper()}",
        report_type=original.report_type,
        reporting_year=original.reporting_year,
        quarter=original.quarter,
        status="REVISED",
        version=original.version + 1,
        parent_report_id=original.id,
        prepared_by=original.prepared_by,
        reviewed_by=payload.get("reviewed_by") or original.reviewed_by,
        remarks=payload.get("remarks"),
        generated_at=utcnow(),
        finalized_at=utcnow(),
        finalized_by_id=user_id,
        created_by_id=user_id,
    )
    db.session.add(revision)
    db.session.flush()
    db.session.add(
        AccomplishmentReportSnapshot(
            report_id=revision.id, version=revision.version,
            snapshot=snapshot["data"], weights=snapshot["weights"],
            formulas=snapshot["formulas"],
        )
    )
    _audit("REPORT_REVISED", revision.id,
           accomplishment_report_to_dict(original),
           accomplishment_report_to_dict(revision))
    log_action("ACCOMP_REPORT_REVISED", "accomplishment", revision.id,
               previous_values=accomplishment_report_to_dict(original),
               new_values=accomplishment_report_to_dict(revision),
               user_id=user_id, commit=False)
    db.session.commit()
    return revision
