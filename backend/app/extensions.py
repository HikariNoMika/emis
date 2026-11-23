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
from sqlalchemy.pool import StaticPool


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
            # SQLite (in-memory OR local file) shares one connection across the
            # FastAPI worker threads. Without this, long-lived scoped sessions
            # exhaust the default 5-connection QueuePool.
            self.engine = create_engine(
                settings.DATABASE_URL,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )
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

    def create_all(self):
        Base.metadata.create_all(self.engine)

    def drop_all(self):
        Base.metadata.drop_all(self.engine)

    def remove(self):
        if self._session is not None:
            self._session.remove()


db = Database()
