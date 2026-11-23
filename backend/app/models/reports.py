"""Generated report records (history of produced files)."""

from app.extensions import db
from app.utils.db_types import jsonb
from app.utils.time import utcnow

from .base import TimestampMixin


class Report(TimestampMixin, db.Model):
    """One generated report file.

    Report data is always derived from the database at generation time. The
    generated file is stored on disk and its metadata is recorded here so the
    generation history can be listed and downloaded later.
    """

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    report_number = db.Column(db.String(60), unique=True, nullable=False, index=True)
    report_type = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)

    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    date_from = db.Column(db.DateTime(timezone=True), nullable=True)
    date_to = db.Column(db.DateTime(timezone=True), nullable=True)
    measurement_type_ids = db.Column(jsonb(), nullable=True, default=list)
    parameters = db.Column(jsonb(), nullable=True, default=dict)

    file_format = db.Column(db.String(10), nullable=False, default="pdf")
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="GENERATED", index=True)
    generated_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    station = db.relationship("Station")

    def __repr__(self):
        return f"<Report {self.report_number}>"
