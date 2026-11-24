"""Shared, bounded vocabularies used across the API."""

# Station "source type" drives which view a station belongs to. Adding a new
# source type only needs a new entry here plus a UI option — no new table.
STATION_TYPES = ("AWS", "AWLS")

STATION_TYPE_LABELS = {
    "AWS": "Automated Weather Station",
    "AWLS": "Automated Water Level Station",
}
