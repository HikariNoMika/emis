"""
All SQLAlchemy models.

Importing this package registers every table with SQLAlchemy's metadata, which
is required for migrations and for `db.create_all()` in tests.
"""

from .accomplishment import (
    AccomplishmentActual,
    AccomplishmentAttachment,
    AccomplishmentAuditLog,
    AccomplishmentCategory,
    AccomplishmentIndicator,
    AccomplishmentQuarterlyTarget,
    AccomplishmentReport,
    AccomplishmentReportSnapshot,
    AccomplishmentSetting,
    AccomplishmentWeightHistory,
)
from .alerts import Alert, AlertHistory
from .base import TimestampMixin
from .imports import DataSource, ImportBatch, RawImportRecord
from .maintenance import MaintenanceRecord
from .measurement import Measurement, MeasurementType
from .quality import DataQualityFlag
from .reports import Report
from .sensor import Sensor, SensorMeasurementType
from .station import Station, StationStatus
from .sync_log import SyncLog
from .system import AuditLog, SystemSetting
from .user import LoginHistory, User

__all__ = [
    "AccomplishmentActual",
    "AccomplishmentAttachment",
    "AccomplishmentAuditLog",
    "AccomplishmentCategory",
    "AccomplishmentIndicator",
    "AccomplishmentQuarterlyTarget",
    "AccomplishmentReport",
    "AccomplishmentReportSnapshot",
    "AccomplishmentSetting",
    "AccomplishmentWeightHistory",
    "Alert",
    "AlertHistory",
    "AuditLog",
    "DataQualityFlag",
    "DataSource",
    "ImportBatch",
    "LoginHistory",
    "MaintenanceRecord",
    "Measurement",
    "MeasurementType",
    "RawImportRecord",
    "Report",
    "Sensor",
    "SensorMeasurementType",
    "Station",
    "StationStatus",
    "SyncLog",
    "SystemSetting",
    "TimestampMixin",
    "User",
]
