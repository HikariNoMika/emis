"""Router registration for the /api/v1 FastAPI application."""

from .alerts import alerts_bp
from .analytics import analytics_bp
from .auth import auth_bp
from .data_quality import data_quality_bp
from .dashboard import dashboard_bp
from .health import health_bp
from .imports import imports_bp
from .maintenance import maintenance_bp
from .measurement_types import measurement_types_bp
from .measurements import measurements_bp
from .reports import reports_bp
from ..api.v1.accomplishment import accomplishment_bp
from ..api.v1.accomplishment_reports import accomplishment_reports_bp
from .sensors import sensors_bp
from .stations import stations_bp
from .system import audit_bp, system_bp
from .users import users_bp


def register_routers(app, prefix):
    app.include_router(auth_bp, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(alerts_bp, prefix=f"{prefix}/alerts", tags=["alerts"])
    app.include_router(analytics_bp, prefix=f"{prefix}/analytics", tags=["analytics"])
    app.include_router(data_quality_bp, prefix=f"{prefix}/data-quality", tags=["data-quality"])
    app.include_router(health_bp, prefix=f"{prefix}/health", tags=["health"])
    app.include_router(dashboard_bp, prefix=f"{prefix}/dashboard", tags=["dashboard"])
    app.include_router(imports_bp, prefix=f"{prefix}/imports", tags=["imports"])
    app.include_router(measurements_bp, prefix=f"{prefix}/measurements", tags=["measurements"])
    app.include_router(maintenance_bp, prefix=f"{prefix}/maintenance", tags=["maintenance"])
    app.include_router(reports_bp, prefix=f"{prefix}/reports", tags=["reports"])
    app.include_router(stations_bp, prefix=f"{prefix}/stations", tags=["stations"])
    app.include_router(sensors_bp, prefix=f"{prefix}/sensors", tags=["sensors"])
    app.include_router(
        measurement_types_bp, prefix=f"{prefix}/measurement-types",
        tags=["measurement-types"],
    )
    app.include_router(users_bp, prefix=f"{prefix}/users", tags=["users"])
    app.include_router(system_bp, prefix=f"{prefix}/system", tags=["system"])
    app.include_router(audit_bp, prefix=prefix, tags=["audit"])
    app.include_router(
        accomplishment_bp, prefix=f"{prefix}/accomplishment",
        tags=["accomplishment"],
    )
    app.include_router(
        accomplishment_reports_bp, prefix=f"{prefix}/accomplishment",
        tags=["accomplishment-reports"],
    )
