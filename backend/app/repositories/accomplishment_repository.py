"""Data access for accomplishment entities."""

from app.extensions import db
from app.models import (
    AccomplishmentActual,
    AccomplishmentCategory,
    AccomplishmentIndicator,
    AccomplishmentQuarterlyTarget,
    AccomplishmentReport,
)


class AccomplishmentRepository:
    @staticmethod
    def categories():
        return AccomplishmentCategory.query.order_by(AccomplishmentCategory.id).all()

    @staticmethod
    def category_by_code(code):
        return AccomplishmentCategory.query.filter_by(code=code).first()

    @staticmethod
    def indicators(year=None, category_code=None, active_only=True):
        query = AccomplishmentIndicator.query
        if year is not None:
            query = query.filter_by(reporting_year=year)
        if category_code:
            query = query.join(AccomplishmentCategory).filter(
                AccomplishmentCategory.code == category_code
            )
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(AccomplishmentIndicator.id).all()

    @staticmethod
    def indicator_by_id(indicator_id):
        return db.session.get(AccomplishmentIndicator, indicator_id)

    @staticmethod
    def targets(year, quarter=None, indicator_ids=None):
        query = AccomplishmentQuarterlyTarget.query.filter_by(reporting_year=year)
        if quarter is not None:
            query = query.filter_by(quarter=quarter)
        if indicator_ids:
            query = query.filter(
                AccomplishmentQuarterlyTarget.indicator_id.in_(indicator_ids)
            )
        return query.all()

    @staticmethod
    def target_by_id(target_id):
        return db.session.get(AccomplishmentQuarterlyTarget, target_id)

    @staticmethod
    def actuals(year, quarter=None, indicator_ids=None):
        query = AccomplishmentActual.query.filter_by(reporting_year=year)
        if quarter is not None:
            query = query.filter_by(quarter=quarter)
        if indicator_ids:
            query = query.filter(
                AccomplishmentActual.indicator_id.in_(indicator_ids)
            )
        return query.all()

    @staticmethod
    def actual_by_id(actual_id):
        return db.session.get(AccomplishmentActual, actual_id)

    @staticmethod
    def duplicate_actual_exists(indicator_id, year, quarter, entry_reference, exclude_id=None):
        query = AccomplishmentActual.query.filter_by(
            indicator_id=indicator_id,
            reporting_year=year,
            quarter=quarter,
            entry_reference=entry_reference,
        )
        if exclude_id:
            query = query.filter(AccomplishmentActual.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def report_by_id(report_id):
        return db.session.get(AccomplishmentReport, report_id)
