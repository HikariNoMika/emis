"""Reusable SQLAlchemy column types."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


def jsonb():
    """
    Return a column type that is JSONB on PostgreSQL and plain JSON elsewhere.

    Using a variant (instead of JSONB directly) lets the test suite run on
    in-memory SQLite while production still gets real PostgreSQL JSONB with its
    indexing and query operators.
    """
    return JSON().with_variant(JSONB, "postgresql")
