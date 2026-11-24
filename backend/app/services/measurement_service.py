"""Measurement queries, trend aggregation, statistics and exports."""

import csv
import io
import math
import statistics
from collections import defaultdict
from datetime import timedelta

from app.models import ImportBatch, Measurement, MeasurementType, RawImportRecord, Station
from app.services.exceptions import ValidationAppError
from app.repositories.measurement_repository import MeasurementRepository
from app.utils.serializers import measurement_to_dict
from app.utils.time import to_iso


def data_gaps(station_id, measurement_type_id=None, date_from=None, date_to=None, limit=100):
    """Find timestamp jumps larger than the station's expected reading interval.

    Distinct observation times are compared, so a gap means no reading at all
    for that period — not merely a missing parameter.
    """
    from datetime import timezone

    from app.extensions import db

    interval = 900
    if station_id:
        station = db.session.get(Station, station_id)
        if station and station.measurement_interval_seconds:
            interval = station.measurement_interval_seconds

    query = Measurement.query.with_entities(
        Measurement.observation_time
    ).distinct()
    if station_id:
        query = query.filter(Measurement.station_id == station_id)
    if measurement_type_id:
        query = query.filter(Measurement.measurement_type_id == measurement_type_id)
    if date_from:
        query = query.filter(Measurement.observation_time >= date_from)
    if date_to:
        query = query.filter(Measurement.observation_time <= date_to)

    times = []
    for (value,) in query.order_by(Measurement.observation_time.asc()).all():
        if value is None:
            continue
        times.append(value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value)

    gaps = []
    total_missing = 0
    for previous, current in zip(times, times[1:]):
        seconds = (current - previous).total_seconds()
        missing = int(seconds // interval) - 1
        if missing >= 1:
            total_missing += missing
            gaps.append({
                "start": to_iso(previous),
                "end": to_iso(current),
                "gap_minutes": round(seconds / 60, 1),
                "missing_readings": missing,
            })

    gaps.sort(key=lambda item: item["missing_readings"], reverse=True)
    return {
        "station_id": station_id,
        "measurement_type_id": measurement_type_id,
        "interval_seconds": interval,
        "total_gaps": len(gaps),
        "total_missing_readings": total_missing,
        "gaps": gaps[:limit] if limit else gaps,
    }


def fill_gaps(station_id, measurement_type_id):
    """Insert timestamp-only placeholder rows at every gap for one parameter.

    Values stay empty (NULL) and quality_status becomes MISSING, so the gap is
    represented honestly instead of being filled with invented readings.
    """
    from datetime import datetime, timedelta, timezone

    from app.extensions import db

    station = db.session.get(Station, station_id)
    if station is None:
        raise ValidationAppError("Station not found.")
    measurement_type = db.session.get(MeasurementType, measurement_type_id)
    if measurement_type is None:
        raise ValidationAppError("Measurement type not found.")

    interval = station.measurement_interval_seconds or 900
    gaps = data_gaps(station_id, measurement_type_id, limit=None)["gaps"]

    existing = set()
    rows = db.session.query(Measurement.observation_time).filter_by(
        station_id=station_id,
        measurement_type_id=measurement_type_id,
        sensor_id=None,
    ).all()
    for (value,) in rows:
        if value is not None:
            existing.add(
                value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
            )

    created = 0
    for gap in gaps:
        current = datetime.fromisoformat(gap["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(gap["end"].replace("Z", "+00:00"))
        current += timedelta(seconds=interval)
        while current < end:
            if current not in existing:
                db.session.add(Measurement(
                    station_id=station_id,
                    measurement_type_id=measurement_type_id,
                    sensor_id=None,
                    observation_time=current,
                    quality_status="MISSING",
                    unit=measurement_type.unit,
                    source_record_identifier="GAP_FILL",
                ))
                existing.add(current)
                created += 1
                if created % 1000 == 0:
                    db.session.flush()
            current += timedelta(seconds=interval)

    db.session.commit()
    return {"created_rows": created, "gaps_processed": len(gaps)}


def observation_range(station_id=None, date_from=None, date_to=None):
    """Stored time coverage of the measurements for the given filters."""
    first, last, count = MeasurementRepository.observation_range(
        station_id, date_from, date_to
    )
    return {
        "first_observation": to_iso(first),
        "last_observation": to_iso(last),
        "total_measurements": count,
    }


def list_measurements(filters, page, per_page, date_from, date_to):
    pagination = MeasurementRepository.list_measurements(
        filters, page, per_page, date_from, date_to
    )
    return [measurement_to_dict(item) for item in pagination.items], pagination


def latest(filters, limit=200):
    """Latest reading per measurement type (optionally per station)."""
    station_id = filters.get("station_id")
    records = (
        MeasurementRepository.latest_for_station(station_id, limit)
        if station_id
        else MeasurementRepository.all_latest(limit)
    )
    seen = set()
    result = []
    for item in records:
        key = (item.station_id, item.measurement_type_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(measurement_to_dict(item))
    return result


def _bucket_start(moment, interval_minutes):
    """Round a UTC datetime down to the start of its aggregation bucket."""
    total_minutes = moment.hour * 60 + moment.minute
    if interval_minutes >= 1440:
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)
    bucket = (total_minutes // interval_minutes) * interval_minutes
    return moment.replace(
        hour=bucket // 60, minute=bucket % 60, second=0, microsecond=0
    )


def trends(params, date_from, date_to):
    """Time-bucketed series for selected measurement types at one station."""
    station_id = params["station_id"]
    type_ids = params["measurement_type_ids"]
    interval = params["interval_minutes"]
    records = MeasurementRepository.for_trends(
        station_id, type_ids, date_from, date_to
    )

    grouped = defaultdict(list)
    for item in records:
        key = (item.measurement_type_id, _bucket_start(item.observation_time, interval))
        value = item.normalized_value
        if value is not None:
            grouped[key].append(float(value))

    series = []
    for type_id in type_ids:
        measurement_type = MeasurementRepository.get_type(type_id)
        if measurement_type is None:
            continue
        method = measurement_type.aggregation_method
        points = []
        for (stored_type_id, moment), values in sorted(
            grouped.items(), key=lambda entry: entry[0][1]
        ):
            if stored_type_id != type_id or not values:
                continue
            if method == "SUM":
                value = sum(values)
            elif method == "CIRCULAR_MEAN":
                value = circular_mean(values)
            else:
                value = statistics.fmean(values)
            if value is None:
                # Opposing wind directions have no meaningful circular mean.
                continue
            points.append({"time": to_iso(moment), "value": round(value, 4)})

        series.append(
            {
                "measurement_type_id": type_id,
                "code": measurement_type.code,
                "name": measurement_type.name,
                "unit": measurement_type.unit,
                "aggregation": method,
                "points": points,
            }
        )
    return series


def circular_mean(values):
    """Average angles correctly (0° and 360° are neighbours, not opposites)."""
    if not values:
        return None
    sin_sum = sum(math.sin(math.radians(value)) for value in values)
    cos_sum = sum(math.cos(math.radians(value)) for value in values)
    if abs(sin_sum) < 1e-12 and abs(cos_sum) < 1e-12:
        return None  # directions cancel out; no meaningful mean
    angle = math.degrees(math.atan2(sin_sum, cos_sum))
    return angle % 360


def statistics_for(params, date_from, date_to):
    """Statistical summary for one measurement type.

    Missing records are never counted as zero: we compute expected observations
    from the station's configured interval and subtract actual observations.
    """
    station_id = params.get("station_id")
    type_id = params["measurement_type_id"]
    records = MeasurementRepository.for_statistics(
        station_id, type_id, date_from, date_to
    )
    measurement_type = MeasurementRepository.get_type(type_id)
    values = [
        float(item.normalized_value)
        for item in records
        if item.normalized_value is not None
    ]

    stats = {
        "station_id": station_id,
        "measurement_type_id": type_id,
        "code": measurement_type.code if measurement_type else None,
        "name": measurement_type.name if measurement_type else None,
        "unit": measurement_type.unit if measurement_type else None,
        "observations": len(values),
        "min": None,
        "max": None,
        "average": None,
        "median": None,
        "std_dev": None,
        "total": None,
        "missing_records": 0,
        "completeness_percent": None,
        "quality_breakdown": {},
    }

    breakdown = defaultdict(int)
    for item in records:
        breakdown[item.quality_status] += 1
    stats["quality_breakdown"] = dict(breakdown)

    if values:
        stats["min"] = round(min(values), 4)
        stats["max"] = round(max(values), 4)
        stats["average"] = round(statistics.fmean(values), 4)
        stats["median"] = round(statistics.median(values), 4)
        stats["std_dev"] = round(statistics.stdev(values), 4) if len(values) > 1 else 0
        stats["total"] = round(sum(values), 4)

    if measurement_type and measurement_type.is_circular and values:
        stats["circular_mean"] = round(circular_mean(values), 4)

    # Completeness: compare actual count with the expected number of slots.
    if station_id and date_from and date_to and date_to >= date_from:
        interval_seconds = MeasurementRepository.station_timezone(station_id)
        expected = int((date_to - date_from).total_seconds() / interval_seconds) + 1
        stats["missing_records"] = max(0, expected - len(records))
        stats["completeness_percent"] = (
            round(min(100, len(records) / expected * 100), 2) if expected else None
        )

    return stats


def comparison(params, date_from, date_to):
    """Compare the same measurement type across several stations."""
    type_id = params["measurement_type_id"]
    measurement_type = MeasurementRepository.get_type(type_id)
    if measurement_type is None:
        return []

    outputs = []
    for station_id in params["station_ids"]:
        stats = statistics_for(
            {"station_id": station_id, "measurement_type_id": type_id},
            date_from,
            date_to,
        )
        series = trends(
            {
                "station_id": station_id,
                "measurement_type_ids": [type_id],
                "interval_minutes": params.get("interval_minutes", 60),
            },
            date_from,
            date_to,
        )
        outputs.append(
            {
                "station_id": station_id,
                "statistics": stats,
                "series": series[0]["points"] if series else [],
            }
        )
    return outputs


def statistics_bulk(station_id, date_from=None, date_to=None):
    """
    One grouped SQL query returning basic stats for every measurement type at
    a station. Used by the per-station analytics page instead of ~20 requests.
    """
    from sqlalchemy import func

    from app.extensions import db

    query = db.session.query(
        Measurement.measurement_type_id,
        func.count(Measurement.id),
        func.min(Measurement.normalized_value),
        func.max(Measurement.normalized_value),
        func.avg(Measurement.normalized_value),
        func.sum(Measurement.normalized_value),
    ).filter(Measurement.station_id == station_id)
    if date_from:
        query = query.filter(Measurement.observation_time >= date_from)
    if date_to:
        query = query.filter(Measurement.observation_time <= date_to)

    result = {}
    for type_id, count, minimum, maximum, average, total in query.group_by(
        Measurement.measurement_type_id
    ).all():
        result[str(type_id)] = {
            "observations": count,
            "min": round(float(minimum), 4) if minimum is not None else None,
            "max": round(float(maximum), 4) if maximum is not None else None,
            "average": round(float(average), 4) if average is not None else None,
            "total": round(float(total), 4) if total is not None else None,
        }
    return result


def flexible_comparison(filters, date_from_a, date_to_a, date_from_b, date_to_b):
    """
    Compare any two user-selected periods for one station/measurement type.

    Series are aligned by elapsed time from each period's start, so a month-long
    period can be compared with another month even if the calendar dates differ.
    Buckets with no readings are omitted, never filled with zero.
    """
    from collections import defaultdict

    station_id = filters["station_id"]
    type_id = filters["measurement_type_id"]
    interval = filters["interval_minutes"]
    measurement_type = MeasurementRepository.get_type(type_id)
    if measurement_type is None:
        return None

    def build_series(date_from, date_to):
        records = MeasurementRepository.for_statistics(
            station_id, type_id, date_from, date_to
        )
        grouped = defaultdict(list)
        for item in records:
            value = item.normalized_value
            if value is None:
                continue
            bucket = _bucket_start(item.observation_time, interval)
            if bucket.tzinfo is None:
                from datetime import timezone

                bucket = bucket.replace(tzinfo=timezone.utc)
            offset_minutes = int((bucket - date_from).total_seconds() // 60)
            grouped[offset_minutes].append(float(value))

        method = measurement_type.aggregation_method
        points = []
        for offset, values in sorted(grouped.items()):
            if method == "SUM":
                value = sum(values)
            elif method == "CIRCULAR_MEAN":
                value = circular_mean(values)
            elif method == "MAX":
                value = max(values)
            elif method == "MIN":
                value = min(values)
            else:
                value = statistics.fmean(values)
            points.append(
                {
                    "offset_minutes": offset,
                    "offset_hours": round(offset / 60, 2),
                    "value": round(value, 4) if value is not None else None,
                }
            )

        stats = statistics_for(
            {"station_id": station_id, "measurement_type_id": type_id},
            date_from,
            date_to,
        )
        return {
            "date_from": to_iso(date_from),
            "date_to": to_iso(date_to),
            "observations": len(records),
            "statistics": {
                "min": stats["min"],
                "max": stats["max"],
                "average": stats["average"],
            },
            "points": points,
        }

    return {
        "measurement_type": {
            "id": measurement_type.id,
            "name": measurement_type.name,
            "code": measurement_type.code,
            "unit": measurement_type.unit,
        },
        "interval_minutes": interval,
        "period_a": build_series(date_from_a, date_to_a),
        "period_b": build_series(date_from_b, date_to_b),
    }


def export_rows(filters, date_from, date_to):
    """Select rows for export. Reuses the same filters as the measurement list."""
    pagination = MeasurementRepository.list_measurements(
        filters, 1, 50000, date_from, date_to
    )
    return pagination.items


def export_source_xlsx(station_id, date_from=None, date_to=None):
    """Export all preserved source rows as ONE sheet, with gaps filled with 0.

    Every import batch for the station is merged into a single sheet ordered by
    observation time. Rows that share a timestamp are merged (later batches
    supply columns the earlier ones lacked). Between two consecutive known
    timestamps, rows are inserted at the station's reading interval with 0 in
    every measurement column and the expected timestamp/date/time values.

    Column headers and real values still come from raw_import_records, so the
    original imported data is preserved exactly — only the synthesized gap
    rows contain zeros.
    """
    from collections import Counter
    from datetime import timedelta, timezone

    from openpyxl import Workbook

    from app.extensions import db
    from app.integrations.timestamp_parser import build_timezone, parse_timestamp

    workbook = Workbook()
    workbook.remove(workbook.active)

    station = db.session.get(Station, station_id) if station_id else None
    timezone_name = station.timezone if station and station.timezone else "Asia/Manila"
    local_tz = build_timezone(timezone_name)
    configured_interval = (
        station.measurement_interval_seconds if station and station.measurement_interval_seconds else 900
    )

    def parse_row_time(payload):
        observed = parse_timestamp(payload.get("Timestamps"), timezone_name)
        if observed is None:
            date_text = payload.get("Date")
            time_text = payload.get("Time")
            if date_text and time_text:
                observed = parse_timestamp(f"{date_text} {time_text}", timezone_name)
        if observed is not None and observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return observed

    # Collect and merge every source row across all batches, keyed by UTC time.
    merged = {}
    headers = []
    batches = ImportBatch.query.filter_by(station_id=station_id).order_by(
        ImportBatch.id.asc()
    ).all()
    for batch in batches:
        candidates = (
            RawImportRecord.query.filter_by(import_batch_id=batch.id)
            .order_by(RawImportRecord.row_number.asc())
            .all()
        )
        for record in candidates:
            payload = dict(record.raw_payload or {})
            observed = parse_row_time(payload)
            if observed is None:
                continue
            if date_from and observed < date_from:
                continue
            if date_to and observed > date_to:
                continue
            for key in payload:
                if key not in headers:
                    headers.append(key)
            if observed in merged:
                for key, value in payload.items():
                    if merged[observed].get(key) in (None, "") and value not in (None, ""):
                        merged[observed][key] = value
            else:
                merged[observed] = payload

    if not merged:
        sheet = workbook.create_sheet("no_data")
        sheet.append(["No source rows found for the selected filters."])
    else:
        if "Timestamps" in headers:
            headers.remove("Timestamps")
            headers.insert(0, "Timestamps")

        ordered_times = sorted(merged)

        # Prefer the interval actually present in the data; fall back to the
        # station's configured interval when it cannot be determined.
        deltas = [later - earlier for earlier, later in zip(ordered_times, ordered_times[1:])]
        positive = [delta for delta in deltas if delta.total_seconds() > 0]
        fill_interval = (
            Counter(positive).most_common(1)[0][0]
            if positive else timedelta(seconds=configured_interval)
        )
        if not (timedelta(seconds=60) <= fill_interval <= timedelta(days=1)):
            fill_interval = timedelta(seconds=configured_interval)

        def clean(value):
            if isinstance(value, (int, float, str)):
                return value
            return None if value is None else str(value)

        def gap_row(moment):
            local = moment.astimezone(local_tz).replace(tzinfo=None)
            row = []
            for header in headers:
                lower = header.lower()
                if lower == "timestamps":
                    row.append(local.strftime("%Y-%m-%dT%H:%M:%S"))
                elif lower.startswith("date"):
                    row.append(local.strftime("%m/%d/%Y"))
                elif lower.startswith("time"):
                    row.append(local.strftime("%I:%M:%S %p"))
                else:
                    row.append(0)
            return row

        sheet = workbook.create_sheet("source")
        sheet.append(headers)
        max_rows = 1048576  # Excel sheet limit
        for index, observed in enumerate(ordered_times):
            if index:
                cursor = ordered_times[index - 1] + fill_interval
                while cursor < observed:
                    if sheet.max_row >= max_rows - 1:
                        break
                    sheet.append(gap_row(cursor))
                    cursor += fill_interval
            payload = merged[observed]
            sheet.append([clean(payload.get(header)) for header in headers])
            if sheet.max_row >= max_rows - 1:
                break

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


def export_csv(records):
    """Build a CSV document in memory."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id", "station_id", "sensor_id", "measurement_type_id",
            "observation_time_utc", "original_value", "normalized_value",
            "unit", "quality_status", "source_record_identifier",
        ]
    )
    for item in records:
        writer.writerow(
            [
                item.id, item.station_id, item.sensor_id, item.measurement_type_id,
                to_iso(item.observation_time), item.original_value,
                item.normalized_value, item.unit, item.quality_status,
                item.source_record_identifier,
            ]
        )
    output.seek(0)
    return output.getvalue().encode("utf-8")


def export_xlsx(records):
    """Build an Excel document in memory using OpenPyXL."""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "measurements"
    sheet.append(
        [
            "id", "station_id", "sensor_id", "measurement_type_id",
            "observation_time_utc", "original_value", "normalized_value",
            "unit", "quality_status", "source_record_identifier",
        ]
    )
    for item in records:
        sheet.append(
            [
                item.id, item.station_id, item.sensor_id, item.measurement_type_id,
                to_iso(item.observation_time),
                float(item.original_value) if item.original_value is not None else None,
                float(item.normalized_value) if item.normalized_value is not None else None,
                item.unit, item.quality_status, item.source_record_identifier,
            ]
        )
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()
