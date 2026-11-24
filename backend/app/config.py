"""
Environment-based configuration for the FastAPI backend.

No framework-specific config objects are used: values are read from environment
variables (loaded from backend/.env) with development-safe defaults.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _database_url():
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://emis:emis@localhost:5432/emis",
    )
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


class Settings:
    """All application settings in one place."""

    def __init__(self, environment=None):
        self.ENVIRONMENT = environment or os.getenv("APP_ENV", "development")
        self.DEBUG = self.ENVIRONMENT == "development"
        self.TESTING = self.ENVIRONMENT == "testing"

        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-change-me")
        self.JWT_ALGORITHM = "HS256"
        self.JWT_ACCESS_TOKEN_EXPIRES = timedelta(
            minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))
        )
        self.JWT_REFRESH_TOKEN_EXPIRES = timedelta(
            days=int(os.getenv("JWT_REFRESH_DAYS", "30"))
        )

        if self.TESTING:
            self.DATABASE_URL = "sqlite:///:memory:"
        else:
            self.DATABASE_URL = _database_url()
        self.SQLALCHEMY_ENGINE_OPTIONS = (
            {} if self.TESTING else {"pool_pre_ping": True, "pool_recycle": 280}
        )

        self.UPLOAD_FOLDER = os.getenv(
            "UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads")
        )
        self.REPORT_FOLDER = os.getenv(
            "REPORT_FOLDER", os.path.join(os.getcwd(), "static", "reports")
        )
        self.ALLOWED_IMPORT_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}
        self.MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

        self.CORS_ORIGINS = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]

        self.DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Manila")
        self.DEFAULT_MEASUREMENT_INTERVAL_SECONDS = int(
            os.getenv("DEFAULT_MEASUREMENT_INTERVAL_SECONDS", "900")
        )

        # SMTP for security notifications (MFA setup codes, etc.).
        self.SMTP_HOST = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
        self.SMTP_FROM = os.getenv("SMTP_FROM", "EMIS <no-reply@emis.local>")

        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", self.REDIS_URL)
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", self.REDIS_URL)

        self.API_PREFIX = "/api/v1"

    def validate_production(self):
        """Fail fast when production secrets are left at defaults."""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY.startswith("dev-only"):
                raise RuntimeError("SECRET_KEY must be set in production")
            if self.JWT_SECRET_KEY.startswith("dev-only"):
                raise RuntimeError("JWT_SECRET_KEY must be set in production")


def get_settings(environment=None):
    settings = Settings(environment)
    settings.validate_production()
    return settings
