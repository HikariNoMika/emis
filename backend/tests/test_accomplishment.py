"""Tests for weighted quarterly/annual accomplishment reporting."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.extensions import db
from app.repositories.accomplishment_repository import AccomplishmentRepository
from app.models import (
    AccomplishmentActual,
    AccomplishmentCategory,
    AccomplishmentIndicator,
    AccomplishmentQuarterlyTarget,
    Measurement,
    MeasurementType,
    Station,
)
from app.services import accomplishment_calculator as calc
from app.services import accomplishment_service as service
from app.services import accomplishment_validation as validation
from app.services.exceptions import ValidationAppError
from tests.conftest import ensure_type


def _setup(year=2026):
    activity = AccomplishmentCategory.query.filter_by(code="ACTIVITY").first()
    deliverable = AccomplishmentCategory.query.filter_by(code="DELIVERABLE").first()

    indicators = [
        AccomplishmentIndicator(
            category_id=activity.id, name="Station inspections",
            reporting_year=year, unit="Number of inspections",
            annual_target=80, indicator_weight=100, is_active=True,
        ),
        AccomplishmentIndicator(
            category_id=deliverable.id, name="Validated datasets",
            reporting_year=year, unit="Number of datasets",
            annual_target=4, indicator_weight=100, is_active=True,
        ),
    ]
    db.session.add_all(indicators)
    db.session.commit()
    return indicators


def _target(indicator, year, quarter, planned, approved=True):
    db.session.add(
        AccomplishmentQuarterlyTarget(
            indicator_id=indicator.id, reporting_year=year, quarter=quarter,
            planned_target=planned, is_approved=approved,
        )
    )
    db.session.commit()


def _actual(indicator, year, quarter, quantity, reference):
    db.session.add(
        AccomplishmentActual(
            indicator_id=indicator.id, reporting_year=year, quarter=quarter,
            actual_quantity=quantity, entry_reference=reference,
        )
    )
    db.session.commit()


# ---- Formula tests ----------------------------------------------------------
def test_accomplishment_formula_and_overachievement():
    assert calc.accomplishment_percentage(18, 20) == Decimal("90")
    assert calc.accomplishment_percentage(25, 20) == Decimal("125")
    assert calc.capped_percentage(Decimal("125")) == Decimal("100")


def test_zero_and_missing_targets_are_na():
    assert calc.accomplishment_percentage(10, 0) is None
    assert calc.accomplishment_percentage(10, None) is None


def test_weight_validation():
    with pytest.raises(ValidationAppError):
        validation.validate_category_weights({"ACTIVITY": 60, "DELIVERABLE": 30})
    with pytest.raises(ValidationAppError):
        validation.validate_category_weights({"ACTIVITY": 100})


def test_indicator_weight_validation(app):
    activity = AccomplishmentCategory.query.filter_by(code="ACTIVITY").first()
    indicators = _setup()
    # Two ACTIVITY indicators of 100 each cannot both be valid.
    db.session.add(
        AccomplishmentIndicator(
            category_id=activity.id, name="Extra activity",
            reporting_year=2026, indicator_weight=100, is_active=True,
        )
    )
    db.session.commit()
    indicators = AccomplishmentRepository.indicators(2026)
    with pytest.raises(ValidationAppError):
        validation.validate_indicator_weights(indicators)


def test_quarterly_calculation(app):
    inspection, dataset = _setup()
    _target(inspection, 2026, 1, 20)
    _target(dataset, 2026, 1, 1)
    _actual(inspection, 2026, 1, 18, "q1-inspections")
    _actual(dataset, 2026, 1, 1, "q1-datasets")

    result = calc.quarterly_summary(2026, 1)
    assert result["categories"]["ACTIVITY"]["score"] == 90.0
    assert result["categories"]["DELIVERABLE"]["score"] == 100.0
    assert result["overall"] == 95.0
    assert result["is_complete"] is True


def test_different_quarterly_targets_and_annual_total(app):
    inspection, dataset = _setup()
    for quarter, planned in [(1, 20), (2, 30), (3, 20), (4, 10)]:
        _target(inspection, 2026, quarter, planned)
        _target(dataset, 2026, quarter, 1)
        _actual(inspection, 2026, quarter, planned, f"insp-q{quarter}")
        _actual(dataset, 2026, quarter, 1, f"data-q{quarter}")

    q2 = calc.quarterly_summary(2026, 2)
    assert q2["categories"]["ACTIVITY"]["score"] == 100.0

    annual = calc.annual_summary(2026)
    # Total planned 80, total actual 80 -> 100%. Not an average of quarters.
    assert annual["categories"]["ACTIVITY"]["score"] == 100.0


def test_incremental_actuals_are_counted_once_and_duplicates_rejected(client, auth_headers, app):
    inspection, _dataset = _setup()
    _target(inspection, 2026, 1, 20)

    first = client.post(
        "/api/v1/accomplishment/actuals",
        json={"indicator_id": inspection.id, "reporting_year": 2026, "quarter": 1,
              "actual_quantity": 10, "entry_reference": "entry-A"},
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/accomplishment/actuals",
        json={"indicator_id": inspection.id, "reporting_year": 2026, "quarter": 1,
              "actual_quantity": 8, "entry_reference": "entry-B"},
        headers=auth_headers,
    )
    assert second.status_code == 201

    duplicate = client.post(
        "/api/v1/accomplishment/actuals",
        json={"indicator_id": inspection.id, "reporting_year": 2026, "quarter": 1,
              "actual_quantity": 8, "entry_reference": "entry-B"},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409

    totals = calc.sum_actuals(2026, 1, [inspection.id])
    assert totals[inspection.id] == Decimal("18")


def test_cancelled_indicator_is_excluded(app):
    inspection, _dataset = _setup()
    inspection.is_active = False
    db.session.commit()
    result = calc.quarterly_summary(2026, 1)
    activity_indicators = result["categories"]["ACTIVITY"]["indicators"]
    assert all(row["status"] == "CANCELLED" for row in activity_indicators)


def test_unconfigured_indicator_withholds_overall(app):
    inspection, dataset = _setup()
    _target(inspection, 2026, 1, 20)
    _actual(inspection, 2026, 1, 18, "only-activity")
    # No target/actual for deliverable.
    result = calc.quarterly_summary(2026, 1)
    assert result["overall"] is None
    assert result["is_complete"] is False
    assert result["counts"]["unconfigured"] >= 1


def test_finalization_snapshot_and_historical_weights(client, auth_headers, app):
    inspection, dataset = _setup()
    for indicator, planned, actual in [(inspection, 20, 18), (dataset, 1, 1)]:
        _target(indicator, 2026, 1, planned)
        _actual(indicator, 2026, 1, actual, f"final-{indicator.id}")

    generated = client.post(
        "/api/v1/accomplishment/reports/generate",
        json={"reporting_year": 2026, "quarter": 1, "report_type": "quarterly"},
        headers=auth_headers,
    )
    assert generated.status_code == 201, generated.json()
    report_id = generated.json()["data"]["id"]

    finalized = client.post(
        f"/api/v1/accomplishment/reports/{report_id}/finalize", headers=auth_headers
    )
    assert finalized.status_code == 200, finalized.json()
    assert finalized.json()["data"]["status"] == "FINAL"

    detail = client.get(f"/api/v1/accomplishment/reports/{report_id}", headers=auth_headers)
    frozen = detail.json()["data"]["snapshots"][0]["snapshot"]
    assert frozen["overall"] == 95.0

    # Change a weight afterwards: the finalized snapshot must not change.
    service.update_weights(
        {
            "reporting_year": 2026,
            "category_weights": {"ACTIVITY": 40, "DELIVERABLE": 60},
            "indicator_weights": [
                {"indicator_id": inspection.id, "weight": 100},
                {"indicator_id": dataset.id, "weight": 100},
            ],
            "reason": "test historical preservation",
        },
        user_id=1,
    )
    detail_again = client.get(
        f"/api/v1/accomplishment/reports/{report_id}", headers=auth_headers
    )
    assert detail_again.json()["data"]["snapshots"][0]["snapshot"]["overall"] == 95.0

    revision = client.post(
        f"/api/v1/accomplishment/reports/{report_id}/revise",
        json={"remarks": "authorized correction"}, headers=auth_headers,
    )
    assert revision.status_code == 201
    assert revision.json()["data"]["status"] == "REVISED"
    assert revision.json()["data"]["parent_report_id"] == report_id


def test_delete_target_and_actual(client, auth_headers, app):
    inspection, _dataset = _setup()
    target = client.post(
        "/api/v1/accomplishment/targets",
        json={"indicator_id": inspection.id, "reporting_year": 2026,
              "quarter": 1, "planned_target": 20, "is_approved": True},
        headers=auth_headers,
    ).json()["data"]
    actual = client.post(
        "/api/v1/accomplishment/actuals",
        json={"indicator_id": inspection.id, "reporting_year": 2026,
              "quarter": 1, "actual_quantity": 5, "entry_reference": "delete-me"},
        headers=auth_headers,
    ).json()["data"]

    assert client.delete(f"/api/v1/accomplishment/targets/{target['id']}",
                         headers=auth_headers).status_code == 200
    assert client.delete(f"/api/v1/accomplishment/actuals/{actual['id']}",
                         headers=auth_headers).status_code == 200

    targets = client.get("/api/v1/accomplishment/targets?year=2026",
                         headers=auth_headers).json()["data"]
    actuals = client.get("/api/v1/accomplishment/actuals?year=2026",
                         headers=auth_headers).json()["data"]
    assert targets == []
    assert actuals == []


def test_data_completeness_excludes_invalid(client, auth_headers, app):
    station = Station(station_code="ACC-001", name="Completeness Station",
                      timezone="Asia/Manila", measurement_interval_seconds=900)
    mtype = ensure_type(code="air_temperature", name="Air temperature",
                            category="ATMOSPHERIC", unit="degC")
    db.session.add_all([station, mtype])
    db.session.commit()

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, status in enumerate(["VALID", "VALID", "INVALID", "SUSPECT"]):
        db.session.add(
            Measurement(
                station_id=station.id, measurement_type_id=mtype.id,
                observation_time=start + timedelta(minutes=15 * index),
                normalized_value=20, unit="degC", quality_status=status,
            )
        )
    db.session.commit()

    response = client.get(
        "/api/v1/accomplishment/data-completeness",
        params={
            "station_id": station.id,
            "date_from": "2026-01-01T00:00:00Z",
            "date_to": "2026-01-01T01:00:00Z",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["received_readings"] == 4
    assert data["valid_readings"] == 2
    assert data["invalid_readings"] == 1
    assert data["suspect_readings"] == 1
    assert data["missing_readings"] > 0
