"""CSV connector. Presents a CSV file as a single virtual sheet."""

import pandas as pd

from .base import BaseConnector, json_safe
from .excel_connector import detect_header_row


def _read_csv(path, **kwargs):
    """Try common encodings so files exported from different systems work."""
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            frame = pd.read_csv(path, encoding=encoding, **kwargs)
            # DENR-style telemetry exports provide Unix milliseconds plus
            # separate date/time text columns. Normalize them into one
            # 'Timestamps' ISO column so the generic importer can parse them.
            if "UnixTimestamp" in frame.columns:
                stamps = pd.to_datetime(frame["UnixTimestamp"], unit="ms", utc=True)
                frame["Timestamps"] = stamps.dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
                frame = frame.drop(columns=["UnixTimestamp"])
            return frame
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_error = exc
    raise last_error or ValueError("Could not decode CSV file.")


class CsvConnector(BaseConnector):
    def inspect(self, path, preview_rows=50):
        # A CSV's first row is normally the header. Detect it anyway in case the
        # export contains a title block before the real columns.
        raw_top = _read_csv(path, header=None, nrows=25)
        header_row = detect_header_row(raw_top) if not raw_top.empty else 0
        frame = _read_csv(path, skiprows=header_row)
        frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
        headers = [str(column).strip() for column in frame.columns]
        rows = [
            {headers[index]: json_safe(value) for index, value in enumerate(row)}
            for row in frame.itertuples(index=False, name=None)
        ]
        return {
            "sheets": [
                {
                    "name": "csv",
                    "headers": headers,
                    "preview_rows": rows[:preview_rows],
                    "row_count": len(rows),
                }
            ],
            "metadata": {},
            "metadata_text": [],
            "warnings": ["CSV files have no Metadata sheet; station must be selected manually."],
        }

    def read_rows(self, path, sheet_name="csv"):
        frame = _read_csv(path)
        headers = [str(column).strip() for column in frame.columns]
        rows = [
            {headers[index]: json_safe(value) for index, value in enumerate(row)}
            for row in frame.itertuples(index=False, name=None)
        ]
        return headers, rows
