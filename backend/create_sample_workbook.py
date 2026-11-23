"""
Generate a small SAMPLE monitoring workbook for importer testing.

This is NOT the real Salacafe workbook. It exists because the reference file was
not provided. The headers intentionally use human-readable names so you can see
that the importer matches by header text, not by column position.

Usage:
    python create_sample_workbook.py [output_path]
"""

import sys
from datetime import datetime, timedelta

from openpyxl import Workbook

HEADERS = [
    "Timestamp",
    "Port",
    "Air Temperature (degC)",
    "Relative Humidity (%)",
    "Wind Speed (m/s)",
    "Solar Radiation (W/m2)",
    "Soil Water Content (%)",
    "Battery (%)",
]


def build_workbook(path):
    workbook = Workbook()

    metadata = workbook.active
    metadata.title = "Metadata"
    metadata_rows = [
        ["Station code", "06-02478"],
        ["Station name", "Salacafe"],
        ["Site", "DENRFMB-WATERSHED"],
        ["Device serial", "929"],
        ["Latitude", 6.11582],
        ["Longitude", 124.846231],
        ["Timezone", "Asia/Manila"],
        ["Measurement interval (s)", 900],
    ]
    for row in metadata_rows:
        metadata.append(row)

    config = workbook.create_sheet("Config 1")
    config.append(HEADERS)
    start = datetime(2026, 1, 1, 0, 0, 0)
    for index in range(12):
        config.append(
            [
                (start + timedelta(minutes=15 * index)).strftime("%Y-%m-%d %H:%M:%S"),
                str((index % 8) + 1),
                round(24 + index * 0.2, 2),
                65 + index * 4,      # intentionally exceeds 100 near the end
                round(1.5 + index * 0.05, 2),
                round(300 + index * 10, 2),
                0,                   # suspicious zero channel, kept as-is
                round(95 - index * 0.5, 2),
            ]
        )

    raw = workbook.create_sheet("Raw Config 1")
    raw.append(HEADERS + ["Raw Status"])
    for row in config.iter_rows(min_row=2, values_only=True):
        raw.append(list(row) + ["OK"])

    workbook.save(path)
    print(f"Sample workbook written to {path}")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "sample_salacafe_workbook.xlsx"
    build_workbook(output)
