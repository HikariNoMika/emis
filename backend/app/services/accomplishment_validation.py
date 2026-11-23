"""Validation rules for weights, targets and report finalization."""

from decimal import Decimal

from app.repositories.accomplishment_repository import AccomplishmentRepository
from app.services.exceptions import ValidationAppError

from . import accomplishment_calculator as calc


def _as_decimal(value):
    return Decimal(str(value if value is not None else 0))


def validate_category_weights(weights):
    """Category weights must exist for ACTIVITY and DELIVERABLE and total 100."""
    missing = [code for code in ("ACTIVITY", "DELIVERABLE") if code not in weights]
    if missing:
        raise ValidationAppError(f"Missing category weights: {', '.join(missing)}")
    total = sum(_as_decimal(value) for value in weights.values())
    if total != Decimal("100"):
        raise ValidationAppError(
            f"Category weights must total 100%. Current total: {total}%."
        )
    return True


def validate_indicator_weights(indicators):
    """Within each category and year, indicator weights must total 100%."""
    grouped = {}
    for indicator in indicators:
        key = (indicator.category.code, indicator.reporting_year)
        grouped.setdefault(key, []).append(indicator)

    errors = []
    for (category, year), items in grouped.items():
        total = sum(_as_decimal(item.indicator_weight) for item in items)
        if total != Decimal("100"):
            errors.append(
                f"{category} {year} indicator weights total {total}%, expected 100%."
            )
    if errors:
        raise ValidationAppError(" ".join(errors))
    return True


def category_weight_map():
    """Return current category weights as a dict of code -> Decimal."""
    return {
        category.code: _as_decimal(category.weight)
        for category in AccomplishmentRepository.categories()
        if category.is_active
    }


def finalization_issues(year, quarter):
    """
    List every problem that prevents finalizing a period.

    Returns a list of human-readable strings. An empty list means the period
    can be finalized.
    """
    issues = []
    categories = AccomplishmentRepository.categories()
    indicators = AccomplishmentRepository.indicators(year)

    try:
        validate_category_weights(
            {category.code: category.weight for category in categories if category.is_active}
        )
    except ValidationAppError as exc:
        issues.append(exc.message)

    try:
        validate_indicator_weights(indicators)
    except ValidationAppError as exc:
        issues.append(exc.message)

    indicator_ids = [item.id for item in indicators]
    targets = {
        target.indicator_id: target
        for target in AccomplishmentRepository.targets(year, quarter, indicator_ids)
        if target.is_approved
    }
    actuals = calc.sum_actuals(year, quarter, indicator_ids)

    for indicator in indicators:
        if indicator.status == "CANCELLED" or not indicator.is_active:
            continue
        target = targets.get(indicator.id)
        if target is None or _as_decimal(target.planned_target) <= 0:
            issues.append(
                f"Indicator '{indicator.name}' has no approved target greater than zero "
                f"for Q{quarter}."
            )
        if indicator.id not in actuals or actuals[indicator.id] <= 0:
            issues.append(
                f"Indicator '{indicator.name}' has no actual accomplishment for Q{quarter}."
            )

    return issues


def ensure_can_finalize(year, quarter):
    issues = finalization_issues(year, quarter)
    if issues:
        raise ValidationAppError("Cannot finalize report: " + " ".join(issues))
    return True
