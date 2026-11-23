"""
Station health evaluation.

IMPORTANT: this system currently receives data through file uploads. A late
upload means DATA IS STALE, not that equipment is offline. We therefore compute
ONLINE / DELAYED / OFFLINE from data freshness and always report connectivity as
NOT_REPORTED. Real device communication can replace that field later without
changing the status model.
"""

from datetime import timedelta, timezone

from app.extensions import db
from app.models import (
    Alert,
    Measurement,
    MeasurementType,
    Station,
    StationStatus,
    SystemSetting,
)
from app.utils.serializers import station_status_to_dict
from app.utils.time import utcnow

from . import alert_service


def _aware(value):
    """SQLite returns naive datetimes; treat them as UTC for calculations."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _thresholds():
    setting = SystemSetting.query.filter_by(key="station_status_thresholds").first()
    values = setting.value if setting and isinstance(setting.value, dict) else {}
    return {
        "delayed_minutes": int(values.get("delayed_minutes", 30)),
        "offline_minutes": int(values.get("offline_minutes", 120)),
    }


def _alert_thresholds():
    setting = SystemSetting.query.filter_by(key="alert_thresholds").first()
    values = setting.value if setting and isinstance(setting.value, dict) else {}
    return {
        "warning": float(values.get("battery_warning_percent", 30)),
        "critical": float(values.get("battery_critical_percent", 15)),
    }


def _latest_measurement(station_id, type_code):
    measurement_type = MeasurementType.query.filter_by(code=type_code).first()
    if measurement_type is None:
        return None
    return (
        Measurement.query.filter_by(
            station_id=station_id, measurement_type_id=measurement_type.id
        )
        .order_by(Measurement.observation_time.desc())
        .first()
    )


def evaluate_station(station, thresholds, battery_thresholds):
    """Compute and store one health snapshot for a station."""
    latest = (
        Measurement.query.filter_by(station_id=station.id)
        .order_by(Measurement.observation_time.desc())
        .first()
    )
    now = utcnow()
    last_observation = _aware(latest.observation_time) if latest else None
    freshness = None
    if last_observation:
        freshness = max(0, int((now - last_observation).total_seconds() // 60))

    battery_measurement = _latest_measurement(station.id, "battery_percentage")
    battery = None
    if battery_measurement and battery_measurement.normalized_value is not None:
        battery = float(battery_measurement.normalized_value)

    if station.operational_status == "MAINTENANCE":
        status = "MAINTENANCE"
    elif latest is None:
        status = "UNKNOWN"
    elif freshness > thresholds["offline_minutes"]:
        status = "OFFLINE"
    elif freshness > thresholds["delayed_minutes"]:
        status = "DELAYED"
    else:
        status = "ONLINE"

    expected_next = None
    if last_observation:
        expected_next = last_observation + timedelta(
            seconds=station.measurement_interval_seconds
        )

    snapshot = StationStatus(
        station_id=station.id,
        status=status,
        last_observation_time=last_observation,
        expected_next_time=expected_next,
        data_freshness_minutes=freshness,
        connectivity_state="NOT_REPORTED",
        battery_percentage=battery,
        notes="Status derived from data freshness; equipment connectivity not reported.",
        recorded_at=now,
    )
    db.session.add(snapshot)
    if station.operational_status != "MAINTENANCE":
        station.operational_status = status

    # Battery alerts with deduplication.
    if battery is not None:
        if battery <= battery_thresholds["critical"]:
            alert_service.raise_alert(
                "BATTERY", "CRITICAL", "Critical battery level",
                f"Battery at {battery}% for {station.name}.",
                f"LOW_BATTERY:{station.id}", station.id,
            )
        elif battery <= battery_thresholds["warning"]:
            alert_service.raise_alert(
                "BATTERY", "WARNING", "Low battery level",
                f"Battery at {battery}% for {station.name}.",
                f"LOW_BATTERY:{station.id}", station.id,
            )
        else:
            _recover_alert(f"LOW_BATTERY:{station.id}")

    if status in {"DELAYED", "OFFLINE"}:
        alert_service.raise_alert(
            "MISSING_DATA", "WARNING" if status == "DELAYED" else "CRITICAL",
            f"Data is {status.lower()}",
            f"Latest observation for {station.name} was {freshness} minutes ago.",
            f"MISSING_DATA:{station.id}", station.id,
        )
    else:
        _recover_alert(f"MISSING_DATA:{station.id}")

    return snapshot


def _recover_alert(condition_key):
    """Resolve an active alert when its condition has recovered."""
    alert = Alert.query.filter_by(
        condition_key=condition_key, status="ACTIVE"
    ).first()
    if alert:
        alert_service.resolve(
            alert,
            user_id=None,
            remarks="Condition recovered automatically.",
        )


def refresh_all():
    """Evaluate every active station and return the newest snapshots."""
    thresholds = _thresholds()
    battery_thresholds = _alert_thresholds()
    stations = Station.query.filter_by(is_archived=False).all()
    snapshots = [
        evaluate_station(station, thresholds, battery_thresholds)
        for station in stations
    ]
    db.session.commit()
    return [station_status_to_dict(snapshot) for snapshot in snapshots]


def current_status():
    """Latest snapshot per active station."""
    stations = Station.query.filter_by(is_archived=False).all()
    result = []
    for station in stations:
        latest = (
            StationStatus.query.filter_by(station_id=station.id)
            .order_by(StationStatus.recorded_at.desc())
            .first()
        )
        result.append(
            station_status_to_dict(latest) if latest else {
                "station_id": station.id,
                "status": station.operational_status,
                "connectivity_state": "NOT_REPORTED",
            }
        )
    return result
