"""
EXAMPLE-ONLY seed for the weighted accomplishment module.

DO NOT RUN IN PRODUCTION. This creates illustrative indicators, approved
quarterly targets and actual accomplishments so the dashboard math can be
verified. All records are marked "EXAMPLE" in remarks and use year 2025 by
default so they do not mix with real reporting data.

Usage:
    python seed_accomplishment_example.py            # year 2025
    python seed_accomplishment_example.py 2024       # a different year
"""

import os
import sys

from app.config import get_settings
from app.extensions import db
from app.models import (
    AccomplishmentActual,
    AccomplishmentCategory,
    AccomplishmentIndicator,
    AccomplishmentQuarterlyTarget,
    User,
)

EXAMPLE_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
EXAMPLE_MARKER = "EXAMPLE ONLY - not an official target or accomplishment"

# (name, category, unit, weight, annual target, [Q1..Q4 targets], [Q1..Q4 actuals])
EXAMPLES = [
    # --- Category A: ACTIVITIES (weights total 100) ---
    ("Station inspection", "ACTIVITY", "Number of inspections", 30, 80,
     [20, 20, 20, 20], [18, 20, 19, 17]),
    ("Environmental monitoring", "ACTIVITY", "Number of activities", 30, 80,
     [20, 20, 20, 20], [20, 20, 20, 20]),
    ("Sensor maintenance", "ACTIVITY", "Number of equipment units", 20, 40,
     [10, 10, 10, 10], [8, 10, 10, 10]),
    ("Data validation", "ACTIVITY", "Number of datasets", 20, 40,
     [10, 10, 10, 10], [10, 10, 10, 10]),
    # --- Category B: DELIVERABLES (weights total 100) ---
    ("Quarterly accomplishment reports", "DELIVERABLE", "Number of reports", 40, 4,
     [1, 1, 1, 1], [1, 1, 1, 1]),
    ("Validated environmental datasets", "DELIVERABLE", "Number of datasets", 35, 8,
     [2, 2, 2, 2], [2, 2, 2, 1]),
    ("Station monitoring summaries", "DELIVERABLE", "Number of reports", 25, 4,
     [1, 1, 1, 1], [1, 1, 0, 1]),
]


def main():
    settings = get_settings(os.getenv("APP_ENV", "development"))
    db.init(settings)

    existing = AccomplishmentIndicator.query.filter_by(
        reporting_year=EXAMPLE_YEAR
    ).count()
    if existing:
        print(
            f"[skip] Year {EXAMPLE_YEAR} already has {existing} indicators. "
            "Choose another year as an argument or delete them first."
        )
        return

    categories = {
        row.code: row for row in AccomplishmentCategory.query.all()
    }
    admin = User.query.first()
    admin_id = admin.id if admin else None

    for name, category_code, unit, weight, annual_target, targets, actuals in EXAMPLES:
        indicator = AccomplishmentIndicator(
            category_id=categories[category_code].id,
            name=name,
            description=EXAMPLE_MARKER,
            reporting_year=EXAMPLE_YEAR,
            unit=unit,
            annual_target=annual_target,
            indicator_weight=weight,
            status="ACTIVE",
            is_active=True,
            remarks=EXAMPLE_MARKER,
            created_by_id=admin_id,
        )
        db.session.add(indicator)
        db.session.flush()

        for quarter, (planned, actual) in enumerate(zip(targets, actuals), start=1):
            db.session.add(
                AccomplishmentQuarterlyTarget(
                    indicator_id=indicator.id,
                    reporting_year=EXAMPLE_YEAR,
                    quarter=quarter,
                    planned_target=planned,
                    is_approved=True,
                    remarks=EXAMPLE_MARKER,
                    updated_by_id=admin_id,
                )
            )
            db.session.add(
                AccomplishmentActual(
                    indicator_id=indicator.id,
                    reporting_year=EXAMPLE_YEAR,
                    quarter=quarter,
                    actual_quantity=actual,
                    unit=unit,
                    entry_reference=f"EXAMPLE-{EXAMPLE_YEAR}-Q{quarter}-{indicator.id}",
                    evidence_reference=EXAMPLE_MARKER,
                    entered_by_id=admin_id,
                )
            )
        print(f"[created] {name} ({category_code}, weight {weight}%)")

    db.session.commit()
    print(f"\nExample accomplishment data for {EXAMPLE_YEAR} created.")
    print("Open Quarterly Accomplishment and select year", EXAMPLE_YEAR)
    print("Expected Q1: Activities 93%, Deliverables 100%, Overall 96.5%")
    print("This is EXAMPLE data. Delete the indicators when finished.")
    db.remove()


if __name__ == "__main__":
    main()
