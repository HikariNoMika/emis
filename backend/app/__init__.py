"""
FastAPI application factory for EMIS.

The modular-monolith structure is preserved: routers -> services -> repositories
-> models. No Flask code remains.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .extensions import db
from .services.exceptions import AppError
from .utils.responses import error
from .utils.validation import validation_exception_handler


def create_app(environment=None):
    """Build and configure the FastAPI application."""
    settings = get_settings(environment)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Start-up: bind the database engine and ensure folders exist.
        db.init(settings)
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(settings.REPORT_FOLDER, exist_ok=True)
        if settings.ENVIRONMENT != "production":
            # Development/testing convenience. Production uses Alembic migrations.
            db.create_all()
        # Bring older databases up to date (adds station_type if missing).
        db.ensure_columns()
        # Recover imports that were interrupted by a previous restart.
        # Queued/PROCESSING batches can never resume on their own after a crash;
        # returning them to PREVIEWED lets the administrator retry safely.
        # Duplicate detection means a retry never overwrites stored readings.
        try:
            from app.models import ImportBatch

            interrupted = ImportBatch.query.filter(
                ImportBatch.status.in_(["QUEUED", "PROCESSING"])
            ).all()
            for batch in interrupted:
                batch.status = "PREVIEWED"
                batch.started_at = None
            if interrupted:
                db.session.commit()
                logging.getLogger(__name__).warning(
                    "Reset %d interrupted import(s) to PREVIEWED", len(interrupted)
                )
        except Exception as exc:
            db.session.rollback()
            logging.getLogger(__name__).warning("Could not reset imports: %s", exc)
        # Ensure the measurement catalogue and example categories exist.
        try:
            from app.services.accomplishment_service import seed_defaults
            from seed import ensure_core_data

            ensure_core_data()
            seed_defaults()
        except Exception as exc:  # tables may not exist yet before migrations
            logging.getLogger(__name__).warning("Accomplishment defaults skipped: %s", exc)
            db.session.rollback()
        yield
        # Shut-down: release pooled connections.
        db.remove()
        if db.engine is not None:
            db.engine.dispose()

    def release_session():
        """Return the request's SQLAlchemy connection to the pool."""
        try:
            yield
        finally:
            db.session.remove()

    app = FastAPI(
        title="EMIS API",
        description="Environmental Monitoring Information System",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.DEBUG,
        dependencies=[Depends(release_session)],
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store request metadata for audit logging + apply security headers.
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        from app.utils.request_context import set_request_info

        set_request_info(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        response = await call_next(request)
        # Defensive defaults recommended for admin panels handling sensitive data.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
        )
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    # ---- Error handlers ------------------------------------------------------
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError):
        return error(
            exc.message,
            exc.status_code,
            errors=exc.errors,
            code=exc.code,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException):
        return error(str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        return await validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception):
        if settings.DEBUG:
            raise exc
        return error("An unexpected error occurred.", 500, code="INTERNAL_ERROR")

    # ---- Routers -------------------------------------------------------------
    from .routes import register_routers

    register_routers(app, settings.API_PREFIX)

    return app
