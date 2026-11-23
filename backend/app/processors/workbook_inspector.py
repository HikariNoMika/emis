"""Step 2-4 of the import workflow: inspect file, sheets, metadata and columns."""

import os

from app.integrations.csv_connector import CsvConnector
from app.integrations.excel_connector import ExcelConnector
from app.integrations.normalizer import (
    detect_station_from_snapshot,
    guess_column_roles,
    measurement_types_as_dicts,
)


def get_connector(original_filename):
    """Choose a connector from the file extension."""
    extension = os.path.splitext(str(original_filename))[1].lower()
    if extension in {".xlsx", ".xlsm"}:
        return ExcelConnector()
    if extension == ".csv":
        return CsvConnector()
    raise ValueError(f"Unsupported file type: {extension or '(none)'}")


def inspect_file(path, original_filename):
    """Read the file structure without writing anything to the database."""
    connector = get_connector(original_filename)
    return connector.inspect(path)


def choose_sheet(snapshot, explicit_sheet=None):
    """Pick the sheet that looks most like processed measurements.

    Preference order:
      1. the sheet the administrator selected,
      2. a sheet called 'Config 1',
      3. any other non-Metadata sheet that has mapped measurement columns,
      4. the first sheet with headers.
    """
    sheets = snapshot.get("sheets", [])
    if explicit_sheet:
        for sheet in sheets:
            if sheet["name"] == explicit_sheet:
                return sheet
    for sheet in sheets:
        if sheet["name"].strip().lower() == "config 1":
            return sheet
    for sheet in sheets:
        if "metadata" in sheet["name"].lower():
            continue
        if sheet.get("headers"):
            return sheet
    return sheets[0] if sheets else None


def suggest_mapping(snapshot, measurement_types, stations, explicit_sheet=None):
    """
    Build an editable mapping proposal using sheet headers and metadata.

    The returned dictionary is stored on the import batch as JSONB. The
    administrator can change any field in the preview screen before processing.
    """
    type_dicts = measurement_types_as_dicts(measurement_types)
    sheet = choose_sheet(snapshot, explicit_sheet)
    headers = sheet["headers"] if sheet else []
    roles = guess_column_roles(headers, type_dicts)

    detected_station = detect_station_from_snapshot(snapshot, stations)

    mapping = {
        "sheet_name": sheet["name"] if sheet else None,
        "timestamp_column": roles["timestamp_column"],
        "port_column": roles["port_column"],
        "measurement_columns": roles["measurement_columns"],
        # Extra reference data recovered from the workbook (metadata + ports).
        "port_layout": sheet.get("port_layout", {}) if sheet else {},
        "recovered_headers": sheet.get("recovered_headers", {}) if sheet else {},
        "metadata": snapshot.get("metadata", {}),
        # port value -> sensor id. Left empty on purpose: the administrator must
        # map ports to real sensors so we never invent equipment.
        "sensor_mapping": {},
        "timezone": None,
        "station_id": detected_station.id if detected_station else None,
    }
    # Attribute each measurement column to the port whose banner spans it.
    # This comes from the workbook itself, so stations with different port
    # layouts are handled without hard-coded assumptions.
    headers = sheet["headers"] if sheet else []
    measurement_ports = {}
    for header in roles["measurement_columns"]:
        if header not in headers:
            continue
        column_index = headers.index(header)
        for port, bounds in (mapping.get("port_layout") or {}).items():
            start = bounds.get("start")
            end = bounds.get("end")
            end = len(headers) if end is None else end
            if start is not None and start <= column_index < end:
                measurement_ports[header] = port
                break
    mapping["measurement_ports"] = measurement_ports

    warnings = list(snapshot.get("warnings", []))

    if not mapping["timestamp_column"]:
        warnings.append("No timestamp column was detected. Select one before processing.")
    if not mapping["measurement_columns"]:
        warnings.append("No measurement columns were detected. Review the mapping.")
    # The workbook's Metadata sheet is authoritative for the observation
    # timezone; the station record is only a fallback.
    metadata_timezone = (snapshot.get("metadata", {}).get("station") or {}).get("timezone")
    if metadata_timezone:
        mapping["timezone"] = str(metadata_timezone)

    if detected_station is None:
        warnings.append("Station could not be detected from metadata. Select one manually.")
    elif not mapping.get("timezone"):
        mapping["timezone"] = detected_station.timezone

    return mapping, warnings, detected_station
