"""Pydantic request/response schemas used by the FastAPI routers."""

from .accomplishment import (
    ActualCreate,
    ActualUpdate,
    AttachmentUpload,
    CategoryOut,
    DataCompletenessQuery,
    IndicatorCreate,
    IndicatorUpdate,
    ReportGenerate,
    ReportRevise,
    SummaryQuery,
    TargetCreate,
    TargetUpdate,
    WeightsUpdate,
)
from .alerts import AlertActionSchema, AlertQuerySchema
from .auth import (
    ChangePasswordSchema,
    LoginSchema,
    MFACodeSchema,
    MFADisableSchema,
    MFAVerifySchema,
    UserSchema,
    validate_password_policy,
)
from .imports import ImportMappingSchema, ImportQuerySchema
from .maintenance import MaintenanceQuerySchema, MaintenanceSchema
from .measurement_types import MeasurementTypeSchema
from .measurements import (
    ComparisonQuerySchema,
    ExportQuerySchema,
    FillGapsSchema,
    FlexibleComparisonQuerySchema,
    MeasurementQuerySchema,
    StatisticsQuerySchema,
    TrendsQuerySchema,
)
from .quality import QualityFlagQuerySchema, ResolveFlagSchema
from .reports import ReportGenerateSchema
from .sensors import SensorMeasurementTypesSchema, SensorQuerySchema, SensorSchema
from .stations import ClearDataSchema, StationQuerySchema, StationSchema
from .system import AuditLogFilterSchema, SystemSettingSchema
from .users import (
    ResetPasswordSchema,
    UserCreateSchema,
    UserProfileUpdateSchema,
    UserQuerySchema,
    UserUpdateSchema,
)

__all__ = [
    "ActualCreate", "ActualUpdate", "AlertActionSchema", "AlertQuerySchema", "AuditLogFilterSchema",
    "AttachmentUpload", "CategoryOut", "ChangePasswordSchema",
    "ClearDataSchema", "ComparisonQuerySchema", "DataCompletenessQuery", "ExportQuerySchema",
    "FillGapsSchema", "FlexibleComparisonQuerySchema", "ImportMappingSchema",
    "ImportQuerySchema", "IndicatorCreate",
    "IndicatorUpdate", "LoginSchema",
    "MFACodeSchema", "MFADisableSchema", "MFAVerifySchema",
    "MaintenanceQuerySchema", "MaintenanceSchema", "MeasurementQuerySchema",
    "MeasurementTypeSchema", "QualityFlagQuerySchema", "ReportGenerate",
    "ReportGenerateSchema", "ReportRevise",
    "ResolveFlagSchema", "SensorMeasurementTypesSchema", "SensorQuerySchema",
    "SensorSchema", "StationQuerySchema", "StationSchema",
    "StatisticsQuerySchema", "SummaryQuery", "SystemSettingSchema", "UserProfileUpdateSchema",
    "TargetCreate", "TargetUpdate", "TrendsQuerySchema", "UserSchema",
    "WeightsUpdate", "validate_password_policy",
]
