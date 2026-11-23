"""Shared model helpers."""

from app.extensions import db
from app.utils.time import utcnow


class TimestampMixin:
    """Adds created_at / updated_at columns to a model.

    Mixins are a simple way to avoid repeating the same two columns in every
    table. There is no hidden magic here — SQLAlchemy copies these columns onto
    any model that inherits from this class.
    """

    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
