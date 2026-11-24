"""
Model -> JSON-dict converters.

Keeping these in one place means every endpoint returns the same shape for the
same object. Decimal columns are converted to float, dates to ISO strings.
"""

from .time import to_iso


def _number(value):
    return float(value) if value is not None else None


def _date(value):
    return value.isoformat() if value else None


def station_to_dict(station):
    return {
        "id": station.id,
        "station_code": station.station_code,
        "name": station.name,
        "station_type": station.station_type,
        "site_name": station.site_name,
        "description": station.description,
        "latitude": _number(station.latitude),
        "longitude": _number(station.longitude),
        "elevation": _number(station.elevation),
        "timezone": station.timezone,
        "measurement_interval_seconds": station.measurement_interval_seconds,
        "installation_date": _date(station.installation_date),
        "operational_status": station.operational_status,
        "device_serial_number": station.device_serial_number,
        "remarks": station.remarks,
        "is_archived": station.is_archived,
        "created_at": to_iso(station.created_at),
        "updated_at": to_iso(station.updated_at),
    }


def sensor_to_dict(sensor):
    return {
        "id": sensor.id,
        "station_id": sensor.station_id,
        "station_name": sensor.station.name if sensor.station else None,
        "port_number": sensor.port_number,
        "name": sensor.name,
        "model": sensor.model,
        "manufacturer": sensor.manufacturer,
        "serial_number": sensor.serial_number,
        "installation_date": _date(sensor.installation_date),
        "calibration_date": _date(sensor.calibration_date),
        "next_calibration_date": _date(sensor.next_calibration_date),
        "operational_status": sensor.operational_status,
        "description": sensor.description,
        "configuration": sensor.configuration,
        "is_archived": sensor.is_archived,
        "created_at": to_iso(sensor.created_at),
        "updated_at": to_iso(sensor.updated_at),
        "measurement_types": [
            {
                "id": link.measurement_type.id,
                "code": link.measurement_type.code,
                "name": link.measurement_type.name,
                "unit": link.measurement_type.unit,
                "column_hint": link.column_hint,
            }
            for link in sensor.measurement_type_links
            if link.measurement_type
        ],
    }


def measurement_type_to_dict(mt):
    return {
        "id": mt.id,
        "code": mt.code,
        "name": mt.name,
        "category": mt.category,
        "unit": mt.unit,
        "expected_min": _number(mt.expected_min),
        "expected_max": _number(mt.expected_max),
        "is_circular": mt.is_circular,
        "aggregation_method": mt.aggregation_method,
        "description": mt.description,
    }


def measurement_to_dict(measurement):
    return {
        "id": measurement.id,
        "station_id": measurement.station_id,
        "sensor_id": measurement.sensor_id,
        "measurement_type_id": measurement.measurement_type_id,
        "observation_time": to_iso(measurement.observation_time),
        "original_value": _number(measurement.original_value),
        "original_text": measurement.original_text,
        "normalized_value": _number(measurement.normalized_value),
        "unit": measurement.unit,
        "quality_status": measurement.quality_status,
        "source_record_identifier": measurement.source_record_identifier,
        "processed_at": to_iso(measurement.processed_at),
        "created_at": to_iso(measurement.created_at),
    }


def station_status_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "station_id": snapshot.station_id,
        "status": snapshot.status,
        "last_observation_time": to_iso(snapshot.last_observation_time),
        "expected_next_time": to_iso(snapshot.expected_next_time),
        "data_freshness_minutes": snapshot.data_freshness_minutes,
        "connectivity_state": snapshot.connectivity_state,
        "battery_percentage": _number(snapshot.battery_percentage),
        "notes": snapshot.notes,
        "recorded_at": to_iso(snapshot.recorded_at),
    }


def maintenance_to_dict(record):
    return {
        "id": record.id,
        "station_id": record.station_id,
        "sensor_id": record.sensor_id,
        "maintenance_type": record.maintenance_type,
        "maintenance_date": _date(record.maintenance_date),
        "performed_by": record.performed_by,
        "description": record.description,
        "findings": record.findings,
        "action_taken": record.action_taken,
        "calibration_details": record.calibration_details,
        "next_maintenance_date": _date(record.next_maintenance_date),
        "remarks": record.remarks,
        "created_at": to_iso(record.created_at),
    }


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "last_login_at": to_iso(user.last_login_at),
        "created_at": to_iso(user.created_at),
    }


def accomplishment_indicator_to_dict(item):
    return {
        "id": item.id,
        "category_id": item.category_id,
        "category_code": item.category.code if item.category else None,
        "name": item.name,
        "description": item.description,
        "reporting_year": item.reporting_year,
        "unit": item.unit,
        "annual_target": _number(item.annual_target),
        "indicator_weight": _number(item.indicator_weight),
        "station_id": item.station_id,
        "responsible_person": item.responsible_person,
        "start_date": _date(item.start_date),
        "target_completion_date": _date(item.target_completion_date),
        "status": item.status,
        "remarks": item.remarks,
        "is_active": item.is_active,
    }


def accomplishment_target_to_dict(item):
    return {
        "id": item.id,
        "indicator_id": item.indicator_id,
        "reporting_year": item.reporting_year,
        "quarter": item.quarter,
        "planned_target": _number(item.planned_target),
        "is_approved": item.is_approved,
        "remarks": item.remarks,
    }


def accomplishment_actual_to_dict(item):
    return {
        "id": item.id,
        "indicator_id": item.indicator_id,
        "reporting_year": item.reporting_year,
        "quarter": item.quarter,
        "actual_quantity": _number(item.actual_quantity),
        "unit": item.unit,
        "completion_date": _date(item.completion_date),
        "reporting_date": _date(item.reporting_date),
        "evidence_reference": item.evidence_reference,
        "entry_reference": item.entry_reference,
        "is_cancelled": item.is_cancelled,
        "entered_by_id": item.entered_by_id,
        "created_at": to_iso(item.created_at),
    }


def accomplishment_report_to_dict(item):
    return {
        "id": item.id,
        "report_number": item.report_number,
        "report_type": item.report_type,
        "reporting_year": item.reporting_year,
        "quarter": item.quarter,
        "status": item.status,
        "version": item.version,
        "parent_report_id": item.parent_report_id,
        "prepared_by": item.prepared_by,
        "reviewed_by": item.reviewed_by,
        "remarks": item.remarks,
        "file_name": item.file_name,
        "generated_at": to_iso(item.generated_at),
        "finalized_at": to_iso(item.finalized_at),
        "created_at": to_iso(item.created_at),
    }


def report_to_dict(report):
    return {
        "id": report.id,
        "report_number": report.report_number,
        "report_type": report.report_type,
        "title": report.title,
        "station_id": report.station_id,
        "station_name": report.station.name if report.station else None,
        "date_from": to_iso(report.date_from),
        "date_to": to_iso(report.date_to),
        "measurement_type_ids": report.measurement_type_ids,
        "file_format": report.file_format,
        "file_name": report.file_name,
        "status": report.status,
        "generated_at": to_iso(report.generated_at),
    }


def quality_flag_to_dict(flag):
    return {
        "id": flag.id,
        "station_id": flag.station_id,
        "sensor_id": flag.sensor_id,
        "measurement_type_id": flag.measurement_type_id,
        "measurement_id": flag.measurement_id,
        "observation_time": to_iso(flag.observation_time),
        "original_value": _number(flag.original_value),
        "unit": flag.unit,
        "rule_code": flag.rule_code,
        "quality_status": flag.quality_status,
        "severity": flag.severity,
        "expected_range": flag.expected_range,
        "actual_condition": flag.actual_condition,
        "explanation": flag.explanation,
        "resolution_status": flag.resolution_status,
        "admin_remarks": flag.admin_remarks,
        "resolved_at": to_iso(flag.resolved_at),
        "created_at": to_iso(flag.created_at),
    }


def alert_to_dict(alert):
    return {
        "id": alert.id,
        "alert_number": alert.alert_number,
        "station_id": alert.station_id,
        "sensor_id": alert.sensor_id,
        "category": alert.category,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "status": alert.status,
        "condition_key": alert.condition_key,
        "first_seen_at": to_iso(alert.first_seen_at),
        "last_seen_at": to_iso(alert.last_seen_at),
        "acknowledged_at": to_iso(alert.acknowledged_at),
        "resolved_at": to_iso(alert.resolved_at),
        "remarks": alert.remarks,
        "created_at": to_iso(alert.created_at),
    }


def import_batch_to_dict(batch):
    return {
        "id": batch.id,
        "batch_number": batch.batch_number,
        "data_source_id": batch.data_source_id,
        "station_id": batch.station_id,
        "original_filename": batch.original_filename,
        "sheet_names": batch.sheet_names or [],
        "file_size_bytes": batch.file_size_bytes,
        "file_imported_at": to_iso(batch.file_imported_at),
        "status": batch.status,
        "total_rows": batch.total_rows,
        "imported_rows": batch.imported_rows,
        "duplicate_rows": batch.duplicate_rows,
        "error_count": batch.error_count,
        "warning_count": batch.warning_count,
        "completed_at": to_iso(batch.completed_at),
    }
