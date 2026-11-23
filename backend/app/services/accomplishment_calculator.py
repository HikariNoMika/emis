"""
Pure calculation functions for accomplishment reporting.

All business calculations live here, never in route handlers. Percentages are
computed with Decimal to avoid floating-point drift, then converted to float for
JSON responses.

Formulas:
  indicator %   = (actual / planned) * 100          (None when planned is 0/missing)
  capped %      = min(indicator %, 100)              (only for weighted contribution)
  category      = SUM(capped % * indicator weight) / 100
  overall       = (activity score * activity weight / 100)
                + (deliverable score * deliverable weight / 100)
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import Measurement, Station
from app.repositories.accomplishment_repository import AccomplishmentRepository

QUARTER_RANGES = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}


def _decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _float(value):
    return float(value) if value is not None else None


def quarter_bounds(year, quarter):
    """Return (start_date, end_date) for a quarter, leap-year safe."""
    start_month, end_month = QUARTER_RANGES[quarter]
    start = date(year, start_month, 1)
    end_day = calendar.monthrange(year, end_month)[1]
    return start, date(year, end_month, end_day)


def annual_bounds(year):
    return date(year, 1, 1), date(year, 12, 31)


def accomplishment_percentage(actual, planned):
    """(actual / planned) * 100. Returns None for zero/missing planned target."""
    actual_value = _decimal(actual)
    planned_value = _decimal(planned)
    if actual_value is None or planned_value is None or planned_value <= 0:
        return None
    return (actual_value / planned_value) * Decimal("100")


def capped_percentage(percentage):
    """Cap only for weighted contribution, never for display."""
    if percentage is None:
        return None
    return min(percentage, Decimal("100"))


def sum_actuals(year, quarter=None, indicator_ids=None):
    """Sum non-cancelled actual entries per indicator."""
    totals = {}
    for actual in AccomplishmentRepository.actuals(year, quarter, indicator_ids):
        if actual.is_cancelled:
            continue
        value = _decimal(actual.actual_quantity) or Decimal("0")
        totals[actual.indicator_id] = totals.get(actual.indicator_id, Decimal("0")) + value
    return totals


def annual_actuals(year, indicator_ids=None):
    return sum_actuals(year, None, indicator_ids)


def _indicator_status(indicator, percentage, period_end):
    if indicator.status == "CANCELLED" or not indicator.is_active:
        return "CANCELLED"
    if percentage is None:
        return "UNCONFIGURED"
    if percentage >= Decimal("100"):
        return "COMPLETED"
    if indicator.target_completion_date and indicator.target_completion_date < period_end:
        return "DELAYED"
    return "IN_PROGRESS"


def _indicator_row(indicator, planned, actual, period_end):
    percentage = accomplishment_percentage(actual, planned)
    capped = capped_percentage(percentage)
    weight = _decimal(indicator.indicator_weight) or Decimal("0")
    contribution = (capped * weight / Decimal("100")) if capped is not None else None
    return {
        "id": indicator.id,
        "name": indicator.name,
        "category": indicator.category.code,
        "unit": indicator.unit,
        "planned_target": _float(planned),
        "actual_accomplishment": _float(actual),
        "percentage": _float(percentage),
        "capped_percentage": _float(capped),
        "weight": _float(weight),
        "weighted_contribution": _float(contribution),
        "status": _indicator_status(indicator, percentage, period_end),
        "remarks": indicator.remarks,
        "evidence_reference": None,
    }


def _assemble(year, period_name, period_start, period_end, targets, actuals, quarter):
    indicators = AccomplishmentRepository.indicators(year)
    categories = AccomplishmentRepository.categories()

    grouped = {code: [] for code in ("ACTIVITY", "DELIVERABLE")}
    for indicator in indicators:
        if indicator.category.code in grouped:
            grouped[indicator.category.code].append(
                _indicator_row(
                    indicator,
                    targets.get(indicator.id),
                    actuals.get(indicator.id),
                    period_end,
                )
            )

    category_results = {}
    for category in categories:
        if category.code not in grouped:
            continue
        rows = grouped[category.code]
        # A category score is only meaningful when every active indicator is configured.
        complete = bool(rows) and all(
            row["percentage"] is not None and row["status"] != "CANCELLED"
            for row in rows
        )
        score = (
            sum(Decimal(str(row["weighted_contribution"])) for row in rows)
            if complete
            else None
        )
        category_results[category.code] = {
            "name": category.name,
            "weight": _float(category.weight),
            "score": _float(score),
            "is_complete": complete,
            "indicators": rows,
        }

    total_weight = sum(
        _decimal(result["weight"]) or Decimal("0")
        for result in category_results.values()
    )
    overall = None
    if (
        total_weight == Decimal("100")
        and all(result["score"] is not None for result in category_results.values())
    ):
        overall = sum(
            Decimal(str(result["score"])) * (_decimal(result["weight"]) or Decimal("0"))
            / Decimal("100")
            for result in category_results.values()
        )

    counts = {
        "planned": len(indicators),
        "completed": 0,
        "ongoing": 0,
        "delayed": 0,
        "unconfigured": 0,
    }
    for rows in grouped.values():
        for row in rows:
            key = {
                "COMPLETED": "completed", "IN_PROGRESS": "ongoing",
                "DELAYED": "delayed", "UNCONFIGURED": "unconfigured",
            }.get(row["status"])
            if key:
                counts[key] += 1

    return {
        "year": year,
        "quarter": quarter,
        "period_name": period_name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "categories": category_results,
        "overall": _float(overall),
        "counts": counts,
        "is_complete": overall is not None,
        "remarks": (
            [] if overall is not None
            else ["Overall score withheld: required category indicators or weights are missing."]
        ),
    }


def quarterly_summary(year, quarter):
    """Compute the weighted score for one quarter."""
    start, end = quarter_bounds(year, quarter)
    indicator_ids = [item.id for item in AccomplishmentRepository.indicators(year)]
    targets = {
        target.indicator_id: target.planned_target
        for target in AccomplishmentRepository.targets(year, quarter, indicator_ids)
        if target.is_approved
    }
    actuals = sum_actuals(year, quarter, indicator_ids)
    return _assemble(year, f"Q{quarter} {year}", start, end, targets, actuals, quarter)


def annual_summary(year):
    """Compute annual scores from quarterly totals (never an average of percentages)."""
    start, end = annual_bounds(year)
    indicator_ids = [item.id for item in AccomplishmentRepository.indicators(year)]

    planned_totals = {}
    for target in AccomplishmentRepository.targets(year, None, indicator_ids):
        if target.is_approved:
            value = _decimal(target.planned_target) or Decimal("0")
            planned_totals[target.indicator_id] = (
                planned_totals.get(target.indicator_id, Decimal("0")) + value
            )

    actuals = annual_actuals(year, indicator_ids)
    return _assemble(year, f"Annual {year}", start, end, planned_totals, actuals, None)


def dashboard_summary(year):
    """Q1-Q4 cards plus an annual summary row."""
    quarters = {
        f"Q{number}": quarterly_summary(year, number) for number in range(1, 5)
    }
    return {"year": year, "quarters": quarters, "annual": annual_summary(year)}


def data_completeness(filters):
    """
    Technical KPI kept separate from accomplishment scores.

    Invalid and duplicate readings are never counted as valid. Missing readings
    are reported as missing, never as zero.
    """
    from app.utils.time import parse_iso

    query = Measurement.query
    if filters.get("station_id"):
        query = query.filter_by(station_id=filters["station_id"])
    if filters.get("sensor_id"):
        query = query.filter_by(sensor_id=filters["sensor_id"])
    if filters.get("measurement_type_id"):
        query = query.filter_by(measurement_type_id=filters["measurement_type_id"])

    date_from = parse_iso(filters.get("date_from"))
    date_to = parse_iso(filters.get("date_to"))
    if date_from:
        query = query.filter(Measurement.observation_time >= date_from)
    if date_to:
        query = query.filter(Measurement.observation_time <= date_to)

    records = query.all()
    received = len(records)
    valid = sum(1 for item in records if item.quality_status == "VALID")
    suspect = sum(1 for item in records if item.quality_status == "SUSPECT")
    invalid = sum(1 for item in records if item.quality_status in {"INVALID", "DUPLICATE"})

    interval = 900
    if filters.get("station_id"):
        station = db.session.get(Station, filters["station_id"])
        if station:
            interval = station.measurement_interval_seconds or 900

    expected = 0
    if date_from and date_to and date_to >= date_from:
        expected = int((date_to - date_from).total_seconds() / interval) + 1

    missing = max(0, expected - received)
    completeness = (valid / expected * 100) if expected else None

    return {
        "expected_readings": expected,
        "received_readings": received,
        "valid_readings": valid,
        "suspect_readings": suspect,
        "invalid_readings": invalid,
        "missing_readings": missing,
        "completeness_percent": round(completeness, 2) if completeness is not None else None,
        "note": "Data freshness from manual Excel uploads is not equipment connectivity.",
    }
