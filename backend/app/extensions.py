"""
Shared infrastructure for the FastAPI application.

A small compatibility layer (`db`) keeps the existing models, repositories and
services readable: they can still say `db.Column`, `db.Model`, `db.session` and
`Model.query`, but underneath this is plain SQLAlchemy 2.0 — no Flask.
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    or_,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Query,
    relationship,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.pool import QueuePool, StaticPool


class Pagination:
    """Small replacement for Flask-SQLAlchemy's pagination result."""

    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total

    @property
    def total_pages(self):
        return (self.total + self.per_page - 1) // self.per_page if self.per_page else 0

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page * self.per_page < self.total


class PaginateQuery(Query):
    """SQLAlchemy Query with the familiar `.paginate()` helper."""

    def paginate(self, page=1, per_page=25, error_out=False):
        total = self.order_by(None).count()
        items = self.offset((page - 1) * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)


class _QueryDescriptor:
    """Makes `Model.query` work without Flask-SQLAlchemy."""

    def __get__(self, _instance, owner):
        return db.session.query(owner)


class Base(DeclarativeBase):
    query = _QueryDescriptor()


class Database:
    """Holds the engine, session factory and SQLAlchemy name aliases."""

    # Aliases so existing model files need no rewrite.
    Model = Base
    Column = Column
    Integer = Integer
    BigInteger = BigInteger
    String = String
    Text = Text
    Boolean = Boolean
    Date = Date
    DateTime = DateTime
    Float = Float
    Numeric = Numeric
    JSON = JSON
    ForeignKey = ForeignKey
    UniqueConstraint = UniqueConstraint
    Index = Index
    relationship = staticmethod(relationship)
    func = func
    or_ = staticmethod(or_)
    text = staticmethod(text)

    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._session = None

    def init(self, settings):
        """Bind the engine. Called once from create_app()."""
        if settings.DATABASE_URL.startswith("sqlite"):
            if ":memory:" in settings.DATABASE_URL:
                # In-memory tests need ONE shared connection so every worker
                # thread sees the same database (a new connection would be a
                # brand-new, empty in-memory database).
                self.engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                )
            else:
                # File-based SQLite: hand each thread its own pooled connection.
                # A single StaticPool connection shared by concurrent FastAPI
                # worker threads causes intermittent
                # "sqlite3.InterfaceError: bad parameter or other API misuse".
                self.engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=QueuePool,
                    pool_size=30,
                    max_overflow=40,
                    pool_timeout=60,
                    connect_args={"check_same_thread": False, "timeout": 30},
                )

                @event.listens_for(self.engine, "connect")
                def _sqlite_pragmas(dbapi_connection, _record):
                    # WAL + NORMAL keeps large imports much faster on a local
                    # SQLite file while staying safe for a single-user setup.
                    cursor = dbapi_connection.cursor()
                    try:
                        cursor.execute("PRAGMA journal_mode=WAL")
                        cursor.execute("PRAGMA synchronous=NORMAL")
                        # Wait up to 30s for a write lock instead of failing
                        # immediately when several requests scan/write at once.
                        cursor.execute("PRAGMA busy_timeout=30000")
                    finally:
                        cursor.close()
        else:
            self.engine = create_engine(
                settings.DATABASE_URL, **settings.SQLALCHEMY_ENGINE_OPTIONS
            )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            query_cls=PaginateQuery,
        )
        self._session = scoped_session(self.session_factory)

    @property
    def session(self):
        if self._session is None:
            raise RuntimeError("Database has not been initialized. Call db.init(settings).")
        return self._session

    def ensure_columns(self):
        """Add newer columns to databases created before this version.

        Works for both SQLite and PostgreSQL: inspects the real table, then
        issues a guarded ALTER only when the column is missing.
        """
        from sqlalchemy import inspect as sa_inspect, text as sa_text

        if self.engine is None:
            return
        inspector = sa_inspect(self.engine)
        if not inspector.has_table("stations"):
            return
        existing = {column["name"] for column in inspector.get_columns("stations")}
        with self.engine.begin() as connection:
            if "station_type" not in existing:
                connection.execute(sa_text(
                    "ALTER TABLE stations ADD COLUMN station_type "
                    "VARCHAR(30) NOT NULL DEFAULT 'AWS'"
                ))
            if inspector.has_table("users"):
                user_cols = {c["name"] for c in inspector.get_columns("users")}
                if "mfa_secret" not in user_cols:
                    connection.execute(sa_text(
                        "ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(64)"
                    ))
                if "mfa_enabled" not in user_cols:
                    connection.execute(sa_text(
                        "ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT 0"
                    ))
                if "mfa_recovery_codes" not in user_cols:
                    connection.execute(sa_text(
                        "ALTER TABLE users ADD COLUMN mfa_recovery_codes JSON"
                    ))

    def create_all(self):
        Base.metadata.create_all(self.engine)

    def drop_all(self):
        Base.metadata.drop_all(self.engine)

    def remove(self):
        if self._session is not None:
            self._session.remove()


db = Database()
