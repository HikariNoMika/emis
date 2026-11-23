"""
Future synchronization service (structure only).

The real implementation will call OfficialApiConnector, normalize the response
through normalizer.py and call the same import processor used by Excel/CSV.
Keeping this path shared guarantees API data and uploaded data end up in one
consistent measurement table with the same duplicate prevention.
"""


class SyncService:
    def run_incremental_sync(self):
        raise NotImplementedError(
            "Scheduled in Phase 7 after official API documentation is available."
        )

    def run_historical_backfill(self, start_date, end_date):
        raise NotImplementedError(
            "Scheduled in Phase 7 after official API documentation is available."
        )
