"""Data sources, uploaded batches and untouched raw records."""

from app.extensions import db
from app.utils.db_types import jsonb
from app.utils.time import utcnow

from .base import TimestampMixin


class DataSource(TimestampMixin, db.Model):
    """Where monitoring data comes from: excel, csv, or a future official API."""

    __tablename__ = "data_sources"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    source_type = db.Column(
        db.String(30), nullable=False, default="excel"
    )  # excel | csv | official_api
    description = db.Column(db.Text, nullable=True)
    config = db.Column(jsonb(), nullable=True, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    import_batches = db.relationship("ImportBatch", back_populates="data_source")

    def __repr__(self):
        return f"<DataSource {self.code}>"


class ImportBatch(TimestampMixin, db.Model):
    """One uploaded file and everything learned about it.

    The workflow is:
      UPLOADED -> INSPECTED -> PREVIEWED -> PROCESSED -> COMPLETED / FAILED

    Nothing is written to `measurements` until the administrator confirms.
    """

    __tablename__ = "import_batches"

    id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.String(60), unique=True, nullable=False, index=True)

    data_source_id = db.Column(
        db.Integer, db.ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )

    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(512), nullable=False)
    file_checksum = db.Column(db.String(64), nullable=True, index=True)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    file_imported_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )

    # Results of the inspection step, stored as flexible JSONB documents.
    sheet_names = db.Column(jsonb(), nullable=True, default=list)
    detected_metadata = db.Column(jsonb(), nullable=True, default=dict)
    column_mapping = db.Column(jsonb(), nullable=True, default=dict)
    warnings = db.Column(jsonb(), nullable=True, default=list)

    status = db.Column(
        db.String(30), nullable=False, default="UPLOADED", index=True
    )
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    imported_rows = db.Column(db.Integer, nullable=False, default=0)
    duplicate_rows = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    warning_count = db.Column(db.Integer, nullable=False, default=0)

    uploaded_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    data_source = db.relationship("DataSource", back_populates="import_batches")
    station = db.relationship("Station", back_populates="import_batches")
    raw_records = db.relationship(
        "RawImportRecord", back_populates="import_batch", cascade="all, delete-orphan"
    )
    measurements = db.relationship("Measurement", back_populates="import_batch")

    def __repr__(self):
        return f"<ImportBatch {self.batch_number}>"


class RawImportRecord(TimestampMixin, db.Model):
    """An untouched source row kept forever for traceability.

    Even when a row is rejected or flagged as a duplicate, its original content
    remains here. This satisfies the requirement that imported environmental
    data is never silently modified or deleted.
    """

    __tablename__ = "raw_import_records"

    id = db.Column(db.Integer, primary_key=True)
    import_batch_id = db.Column(
        db.Integer, db.ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sheet_name = db.Column(db.String(100), nullable=True)
    row_number = db.Column(db.Integer, nullable=True)
    source_record_identifier = db.Column(db.String(150), nullable=True, index=True)
    observation_time = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    # The exact row as read from Excel/CSV (header -> original cell value).
    raw_payload = db.Column(jsonb(), nullable=False, default=dict)
    is_processed = db.Column(db.Boolean, nullable=False, default=False)
    processing_note = db.Column(db.Text, nullable=True)

    import_batch = db.relationship("ImportBatch", back_populates="raw_records")
    measurements = db.relationship("Measurement", back_populates="raw_record")

    def __repr__(self):
        return (
            f"<RawImportRecord batch={self.import_batch_id} "
            f"row={self.row_number}>"
        )
