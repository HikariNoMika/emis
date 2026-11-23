"""Sync log table reserved for the future official API integration."""

from app.extensions import db
from app.utils.db_types import jsonb
from app.utils.time import utcnow

from .base import TimestampMixin


class SyncLog(TimestampMixin, db.Model):
    """One run of the future official-API synchronizer.

    No rows are written by Phases 1-6. The table exists so the integration can
    record request counts, pagination, retries, errors and duplicate counts
    without another schema change later.
    """

    __tablename__ = "sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False, default="official_api", index=True)
    sync_type = db.Column(db.String(30), nullable=False, default="incremental")
    status = db.Column(db.String(20), nullable=False, default="STARTED", index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    records_received = db.Column(db.Integer, nullable=False, default=0)
    records_created = db.Column(db.Integer, nullable=False, default=0)
    records_duplicate = db.Column(db.Integer, nullable=False, default=0)
    pages_fetched = db.Column(db.Integer, nullable=False, default=0)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    details = db.Column(jsonb(), nullable=True, default=dict)
