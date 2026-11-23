"""
Weighted quarterly and annual accomplishment reporting models.

Ten logical entities are defined here. All weights and percentages are stored
as Numeric so calculations stay exact. Historical configurations are preserved
in `accomplishment_weight_history` and in report snapshots.
"""

from app.extensions import db
from app.utils.db_types import jsonb
from app.utils.time import utcnow

from .base import TimestampMixin


class AccomplishmentCategory(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_categories"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Percentage at LEVEL 1. ACTIVITY + DELIVERABLE must equal 100.
    weight = db.Column(db.Numeric(7, 4), nullable=False, default=50)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    indicators = db.relationship("AccomplishmentIndicator", back_populates="category")


class AccomplishmentIndicator(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_indicators"
    __table_args__ = (
        db.Index("ix_accomp_indicator_year_category", "reporting_year", "category_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_categories.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    reporting_year = db.Column(db.Integer, nullable=False, index=True)
    unit = db.Column(db.String(100), nullable=False, default="Number of activities")
    annual_target = db.Column(db.Numeric(18, 4), nullable=True)
    # Percentage at LEVEL 2, within this indicator's category and year.
    indicator_weight = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id", ondelete="SET NULL"), nullable=True)
    responsible_person = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    target_completion_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="ACTIVE", index=True)
    remarks = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    category = db.relationship("AccomplishmentCategory", back_populates="indicators")
    station = db.relationship("Station")


class AccomplishmentQuarterlyTarget(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_quarterly_targets"
    __table_args__ = (
        db.UniqueConstraint(
            "indicator_id", "reporting_year", "quarter",
            name="uq_accomp_target_indicator_year_quarter",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_indicators.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reporting_year = db.Column(db.Integer, nullable=False, index=True)
    quarter = db.Column(db.Integer, nullable=False, index=True)  # 1..4
    planned_target = db.Column(db.Numeric(18, 4), nullable=False)
    # Unapproved targets are never used in calculations.
    is_approved = db.Column(db.Boolean, nullable=False, default=False, index=True)
    remarks = db.Column(db.Text, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    indicator = db.relationship("AccomplishmentIndicator")


class AccomplishmentActual(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_actuals"
    __table_args__ = (
        # Incremental entries are allowed, but the same reference cannot repeat.
        db.UniqueConstraint(
            "indicator_id", "reporting_year", "quarter", "entry_reference",
            name="uq_accomp_actual_indicator_quarter_reference",
        ),
        db.Index("ix_accomp_actual_period", "reporting_year", "quarter"),
    )

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_indicators.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reporting_year = db.Column(db.Integer, nullable=False)
    quarter = db.Column(db.Integer, nullable=False)
    actual_quantity = db.Column(db.Numeric(18, 4), nullable=False)
    unit = db.Column(db.String(100), nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    reporting_date = db.Column(db.Date, nullable=True)
    evidence_reference = db.Column(db.String(255), nullable=True)
    entry_reference = db.Column(db.String(150), nullable=False)
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False, index=True)
    entered_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at_db = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    indicator = db.relationship("AccomplishmentIndicator")


class AccomplishmentWeightHistory(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_weight_history"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(20), nullable=False, index=True)  # CATEGORY / INDICATOR
    category_id = db.Column(db.Integer, nullable=True)
    indicator_id = db.Column(db.Integer, nullable=True)
    reporting_year = db.Column(db.Integer, nullable=True, index=True)
    old_value = db.Column(db.Numeric(7, 4), nullable=True)
    new_value = db.Column(db.Numeric(7, 4), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class AccomplishmentReport(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_number = db.Column(db.String(60), unique=True, nullable=False, index=True)
    report_type = db.Column(db.String(40), nullable=False, index=True)
    reporting_year = db.Column(db.Integer, nullable=False, index=True)
    quarter = db.Column(db.Integer, nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="DRAFT", index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    parent_report_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    prepared_by = db.Column(db.String(200), nullable=True)
    reviewed_by = db.Column(db.String(200), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(512), nullable=True)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finalized_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finalized_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    snapshots = db.relationship(
        "AccomplishmentReportSnapshot", back_populates="report",
        cascade="all, delete-orphan",
    )


class AccomplishmentReportSnapshot(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_report_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(jsonb(), nullable=False, default=dict)
    formulas = db.Column(jsonb(), nullable=False, default=dict)
    weights = db.Column(jsonb(), nullable=False, default=dict)
    created_at_db = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    report = db.relationship("AccomplishmentReport", back_populates="snapshots")


class AccomplishmentAttachment(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_attachments"

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_indicators.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    actual_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_actuals.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    report_id = db.Column(
        db.Integer, db.ForeignKey("accomplishment_reports.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    original_file_name = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(512), nullable=False)
    mime_type = db.Column(db.String(150), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class AccomplishmentSetting(TimestampMixin, db.Model):
    __tablename__ = "accomplishment_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(jsonb(), nullable=False, default=dict)
    description = db.Column(db.Text, nullable=True)


class AccomplishmentAuditLog(db.Model):
    __tablename__ = "accomplishment_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    module = db.Column(db.String(60), nullable=False, default="accomplishment")
    record_id = db.Column(db.String(100), nullable=True, index=True)
    previous_values = db.Column(jsonb(), nullable=True)
    new_values = db.Column(jsonb(), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
