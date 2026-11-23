"""
Excel (.xlsx / .xlsm) connector.

The importer is deliberately NOT tied to fixed column positions. For every
sheet we look at the first 25 rows, guess which row is the header row by
counting populated cells and measurement keywords, then read that sheet using
the guessed header. This lets the same code handle future workbooks whose
layout differs from the Salacafe reference file.
"""

import pandas as pd

from .base import BaseConnector, json_safe

# Words that usually appear in a real header row (not in title/metadata rows).
HEADER_KEYWORDS = (
    "temp", "humid", "wind", "rain", "solar", "soil", "battery", "batt",
    "pressure", "time", "date", "port", "sensor", "vpd", "radiation",
    "moisture", "voltage", "gust", "direction",
)


def detect_header_row(raw_dataframe):
    """Return the index of the most likely header row (0-based)."""
    best_row = 0
    best_score = -1
    for index in range(min(len(raw_dataframe), 25)):
        values = [str(cell).strip().lower() for cell in raw_dataframe.iloc[index].tolist()]
        populated = sum(1 for value in values if value and value != "nan")
        keyword_bonus = sum(
            3 for value in values if any(keyword in value for keyword in HEADER_KEYWORDS)
        )
        score = populated + keyword_bonus
        if score > best_score:
            best_score = score
            best_row = index
    return best_row


def read_sheet(excel_file, sheet_name, max_preview_rows=None):
    """Read one sheet and return (headers, rows)."""
    raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=30)
    if raw.empty:
        return [], []
    header_row = detect_header_row(raw)
    frame = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row)
    # Drop fully empty columns and rows.
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if max_preview_rows:
        frame = frame.head(max_preview_rows)
    headers = [str(column).strip() for column in frame.columns]
    rows = [
        {headers[index]: json_safe(value) for index, value in enumerate(row)}
        for row in frame.itertuples(index=False, name=None)
    ]
    return headers, rows


def read_station_code(excel_file):
    """The station code is printed in the first cell of the Config sheet."""
    for sheet_name in excel_file.sheet_names:
        if "config" not in sheet_name.lower() or "raw" in sheet_name.lower():
            continue
        frame = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=2)
        if not frame.empty:
            value = json_safe(frame.iloc[0, 0])
            if value:
                return str(value).strip()
    return None


def extract_metadata(excel_file):
    """
    Parse the 'Metadata' sheet into a STRUCTured document.

    The reference workbook stores metadata as:
      column A = section, column B = key, column C = value
    Its Sensors section repeats Port # / Name / Serial Number rows, so we also
    build a list of sensors with their port numbers.

    Returns (metadata_dict, all_text_values). The metadata_dict is stored
    unchanged in ImportBatch.detected_metadata and shown in the preview.
    """
    metadata = {
        "raw_pairs": [],
        "sections": {},
        "station": {},
        "sensors": [],
    }
    text_values = []
    current_section = None
    current_sensor = {}

    def flush_sensor():
        if current_sensor:
            metadata["sensors"].append(dict(current_sensor))
            current_sensor.clear()

    for sheet_name in excel_file.sheet_names:
        if "metadata" not in sheet_name.lower():
            continue
        frame = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        for row in frame.itertuples(index=False, name=None):
            cells = [json_safe(cell) for cell in row]
            text_values.extend(str(cell) for cell in cells if cell is not None)
            while cells and cells[-1] is None:
                cells.pop()
            if not cells:
                continue

            section = None
            key = None
            value = None
            if len(cells) == 1:
                section = str(cells[0]).strip()
            elif len(cells) == 2:
                key, value = str(cells[0]).strip(), cells[1]
            else:
                section = str(cells[0]).strip()
                key, value = str(cells[1]).strip(), cells[2]

            if section and key is None:
                flush_sensor()
                current_section = section
                metadata["sections"][section] = {}
            if key is not None:
                metadata["raw_pairs"].append([key, value])
                if current_section:
                    metadata["sections"].setdefault(current_section, {})[key] = value

                # Interpret repeated sensor keys as a new sensor block.
                if key == "Port #":
                    flush_sensor()
                    current_sensor["port"] = int(value) if value is not None else None
                elif current_sensor and key in {
                    "Name", "Serial Number", "Meta", "Value", "Status", "Version", "Coefficient"
                }:
                    current_sensor[key] = value

                # Normalized station-level fields.
                station_keys = {
                    "Device Name": "name",
                    "Site Name": "site",
                    "Serial Number": "device_serial",
                    "Measurement Interval": "interval_seconds",
                    "Latitude": "latitude",
                    "Longitude": "longitude",
                    "Current Time Zone": "timezone",
                    "Logger Time": "logger_time",
                    "Altitude": "altitude",
                    "Device Type": "device_type",
                    "Firmware Version": "firmware_version",
                }
                if key in station_keys and key != "Port #":
                    # The Sensors section repeats "Serial Number" for each port.
                    # Keep the FIRST occurrence (device serial from Configuration).
                    station_field = station_keys[key]
                    if station_field not in metadata["station"]:
                        metadata["station"][station_field] = value

    flush_sensor()
    return metadata, text_values


def recover_headers_from_raw_sheet(excel_file, primary_sheet, raw_sheet):
    """
    The reference workbook's processed sheet has corrupted header labels
    ('System.Xml.XmlElement'), while the hidden Raw Config 1 sheet has clean
    names. Recover labels by aligning the two sheets by shared header text.

    Returns (headers, recovered_columns) where recovered_columns maps the
    original (corrupted) header to the recovered label.
    """
    from .normalizer import MEASUREMENT_ALIASES, _normalize_header, guess_measurement_type

    primary_headers, _ = read_sheet(excel_file, primary_sheet)
    raw_headers, _ = read_sheet(excel_file, raw_sheet)

    all_codes = {code for _alias, code in MEASUREMENT_ALIASES}

    def code_of(header):
        normalized = _normalize_header(header)
        if not normalized:
            return None
        if "time" in normalized or "date" in normalized:
            return "TIMESTAMP"
        return guess_measurement_type(header, all_codes)

    # Match columns by the measurement each one represents, not by exact text.
    # The processed sheet uses labels like "% Relative Humidity" while the raw
    # sheet says "raw  Relative Humidity" — exact text matching fails there.
    offsets = []
    primary_codes = [code_of(header) for header in primary_headers]
    raw_codes = [code_of(header) for header in raw_headers]
    for primary_index, code in enumerate(primary_codes):
        if code is None:
            continue
        for raw_index, raw_code in enumerate(raw_codes):
            if raw_code == code:
                offsets.append(raw_index - primary_index)
                break
    offset = 1 if not offsets else max(set(offsets), key=offsets.count)

    recovered = {}
    headers = list(primary_headers)
    for index, header in enumerate(headers):
        if _normalize_header(header):
            continue  # readable header: keep it
        raw_index = index + offset
        if 0 <= raw_index < len(raw_headers):
            candidate = str(raw_headers[raw_index]).strip()
            if _normalize_header(candidate):
                headers[index] = candidate
                recovered[str(header)] = candidate
    return headers, recovered


def read_port_layout(excel_file, sheet_name):
    """
    Read the port banner rows (usually rows 1-2) and return a mapping of each
    port number to the column indexes it covers. This lets the importer tell
    which physical port produced each measurement without assuming that every
    station has the same ports.
    """
    import re

    raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=5)
    port_columns = {}
    for row_index in range(min(len(raw), 5)):
        for column_index, cell in enumerate(raw.iloc[row_index].tolist()):
            match = re.search(r"port\s*#?\s*(\d+)", str(cell), re.I)
            if match:
                port_columns[int(match.group(1))] = column_index

    ranges = {}
    ports = sorted(port_columns)
    for position, port in enumerate(ports):
        start = port_columns[port]
        end = port_columns[ports[position + 1]] if position + 1 < len(ports) else None
        ranges[str(port)] = {"start": start, "end": end}
    return ranges


class ExcelConnector(BaseConnector):
    def inspect(self, path, preview_rows=50):
        warnings = []
        excel_file = pd.ExcelFile(path)
        sheets = []
        raw_sheet_name = next(
            (name for name in excel_file.sheet_names if "raw config" in name.lower()),
            None,
        )
        for name in excel_file.sheet_names:
            try:
                headers, rows = read_sheet(excel_file, name)
            except Exception as exc:  # a malformed sheet must not fail the whole file
                warnings.append(f"Could not fully read sheet '{name}': {exc}")
                headers, rows = [], []

            recovered_headers = {}
            port_layout = {}
            if "config" in name.lower() and "raw" not in name.lower() and raw_sheet_name:
                try:
                    headers, recovered_headers = recover_headers_from_raw_sheet(
                        excel_file, name, raw_sheet_name
                    )
                    rows = [
                        {recovered_headers.get(key, key): value for key, value in row.items()}
                        for row in rows
                    ]
                    port_layout = read_port_layout(excel_file, name)
                except Exception as exc:
                    warnings.append(f"Could not recover headers from raw sheet: {exc}")

            sheets.append(
                {
                    "name": name,
                    "headers": headers,
                    "preview_rows": rows[:preview_rows],
                    "row_count": len(rows),
                    "recovered_headers": recovered_headers,
                    "port_layout": port_layout,
                }
            )

        metadata, metadata_text = extract_metadata(excel_file)
        station_code = read_station_code(excel_file)
        if station_code:
            metadata["station"]["code"] = station_code
            metadata_text.append(station_code)
        known_sheets = {"config 1", "raw config 1", "metadata"}
        found = {sheet["name"].lower() for sheet in sheets}
        for expected in known_sheets:
            if expected not in found:
                warnings.append(f"Expected sheet '{expected}' was not found.")

        return {
            "sheets": sheets,
            "metadata": json_safe(metadata),
            "metadata_text": metadata_text[:500],
            "warnings": warnings,
        }

    def read_rows(self, path, sheet_name):
        excel_file = pd.ExcelFile(path)
        return read_sheet(excel_file, sheet_name)
