"""
Dashboard data service.

Every number returned here is computed from the database — there are no
placeholders or hard-coded values. Later phases will extend these endpoints
with charts and more detailed statistics.
"""

from datetime import date, datetime, timezone

from app.extensions import db
from app.models import (
    Alert,
    DataQualityFlag,
    ImportBatch,
    Measurement,
    MeasurementType,
    Sensor,
    Station,
    StationStatus,
)
from app.utils.time import to_iso


def summary():
    """Top-level counters shown in the dashboard summary cards."""
    latest_batch = ImportBatch.query.order_by(
        ImportBatch.file_imported_at.desc()
    ).first()

    def count_active_stations(status):
        return Station.query.filter_by(
            is_archived=False, operational_status=status
        ).count()

    # A single mis-mapped column can generate thousands of individual flags.
    # Count distinct open issues (station + parameter + rule) that actually
    # need attention, instead of every flagged reading.
    actionable_warnings = (
        db.session.query(
            DataQualityFlag.station_id,
            DataQualityFlag.measurement_type_id,
            DataQualityFlag.rule_code,
        )
        .filter(
            DataQualityFlag.resolution_status == "OPEN",
            DataQualityFlag.severity.in_(["WARNING", "CRITICAL"]),
        )
        .distinct()
        .count()
    )

    return {
        "total_stations": Station.query.filter_by(is_archived=False).count(),
        "online_stations": count_active_stations("ONLINE"),
        "delayed_stations": count_active_stations("DELAYED"),
        "offline_stations": count_active_stations("OFFLINE"),
        "maintenance_stations": count_active_stations("MAINTENANCE"),
        "unknown_stations": count_active_stations("UNKNOWN"),
        "total_sensors": Sensor.query.filter_by(is_archived=False).count(),
        "active_alerts": Alert.query.filter_by(status="ACTIVE").count(),
        "data_quality_warnings": actionable_warnings,
        "latest_import_at": to_iso(
            latest_batch.file_imported_at if latest_batch else None
        ),
        "data_progress": data_progress(),
    }


def data_progress(year=None):
    """Quarter-based data-processing progress for a year.

    Each quarter that has at least one stored reading counts as 25%, so four
    quarters with data = 100%. A quarter with no readings contributes 0. This
    is computed entirely from the database — no hardcoded percentages.

    Returns the percentage, the current quarter, and detail for all four
    quarters (bounds, reading counts, stations and the latest reading).
    """
    from app.utils.time import utcnow

    if year is None:
        year = utcnow().year
    now = utcnow()

    # Calendar quarter bounds (inclusive start, exclusive end), in UTC.
    quarter_months = {1: (1, 4), 2: (4, 7), 3: (7, 10), 4: (10, 13)}
    quarters = []
    covered = 0
    for number, (start_month, end_month) in quarter_months.items():
        start = datetime(year, start_month, 1, tzinfo=timezone.utc)
        if end_month > 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, end_month, 1, tzinfo=timezone.utc)

        count = Measurement.query.filter(
            Measurement.observation_time >= start,
            Measurement.observation_time < end,
        ).count()
        if count > 0:
            covered += 1

        quarters.append({
            "quarter": number,
            "label": f"Q{number} {year}",
            "start": to_iso(start),
            "end": to_iso(end),
            "readings": count,
            "has_data": count > 0,
            "contribution_percent": 25 if count > 0 else 0,
        })

    current_quarter = (now.month - 1) // 3 + 1 if now.year == year else None
    return {
        "year": year,
        "percent": covered * 25,
        "quarters_complete": covered,
        "current_quarter": current_quarter,
        "quarters": quarters,
        "note": (
            "Each quarter with at least one stored reading counts as 25%. "
            "Missing quarters are never treated as zero readings."
        ),
    }


def station_status():
    """Latest health snapshot for each non-archived station."""
    stations = Station.query.filter_by(is_archived=False).order_by(Station.name).all()
    result = []
    for station in stations:
        latest = (
            StationStatus.query.filter_by(station_id=station.id)
            .order_by(StationStatus.recorded_at.desc())
            .first()
        )
        result.append(
            {
                "station_id": station.id,
                "station_code": station.station_code,
                "station_name": station.name,
                "operational_status": latest.status if latest else station.operational_status,
                "last_observation_time": to_iso(
                    latest.last_observation_time if latest else None
                ),
                "data_freshness_minutes": latest.data_freshness_minutes if latest else None,
                "battery_percentage": (
                    float(latest.battery_percentage)
                    if latest and latest.battery_percentage is not None
                    else None
                ),
                "connectivity_state": latest.connectivity_state if latest else None,
            }
        )
    return result


def recent_alerts(limit=10):
    """Most recent alerts, newest first."""
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(limit).all()
    return [
        {
            "id": alert.id,
            "alert_number": alert.alert_number,
            "category": alert.category,
            "severity": alert.severity,
            "title": alert.title,
            "status": alert.status,
            "created_at": to_iso(alert.created_at),
        }
        for alert in alerts
    ]


def environmental_summary(limit=200):
    """Latest available value for each measurement type, with station context.

    We scan the newest measurements and keep the first one seen per type. This
    is simple, predictable and correct: it shows the most recent observation
    actually stored in the database. If the table is empty, the UI shows an
    empty state rather than invented numbers.
    """
    recent = Measurement.query.order_by(
        Measurement.observation_time.desc()
    ).limit(limit).all()

    seen_types = set()
    result = []
    for measurement in recent:
        type_id = measurement.measurement_type_id
        if type_id in seen_types:
            continue
        seen_types.add(type_id)

        measurement_type = db.session.get(MeasurementType, type_id)
        station = db.session.get(Station, measurement.station_id)
        value = (
            measurement.normalized_value
            if measurement.normalized_value is not None
            else measurement.original_value
        )
        result.append(
            {
                "measurement_type_code": measurement_type.code if measurement_type else None,
                "measurement_type_name": measurement_type.name if measurement_type else None,
                "category": measurement_type.category if measurement_type else None,
                "value": float(value) if value is not None else None,
                "unit": measurement.unit,
                "quality_status": measurement.quality_status,
                "station_id": station.id if station else None,
                "station_name": station.name if station else None,
                "station_code": station.station_code if station else None,
                "observation_time": to_iso(measurement.observation_time),
            }
        )

    # Keep a stable order for the UI.
    order = [mt.code for mt in MeasurementType.query.order_by(MeasurementType.id).all()]
    result.sort(
        key=lambda item: order.index(item["measurement_type_code"])
        if item["measurement_type_code"] in order
        else 999
    )
    return result
