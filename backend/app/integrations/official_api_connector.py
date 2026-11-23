"""
Placeholder for the future official monitoring website API connector.

No endpoint, authentication method or response format is invented here. This
file exists only to define the SHAPE of the integration. Implementation starts
in Phase 7, after official documentation and authorized credentials exist.

The connector will eventually:
  * authenticate using credentials stored in system settings / environment,
  * support historical backfill and incremental synchronization,
  * handle pagination, retries, timeouts and rate limits,
  * write sync logs to the database, and
  * feed records through normalizer.py into the same measurement structure.
"""

from .base import BaseConnector


class OfficialApiConnector(BaseConnector):
    def __init__(self, config=None):
        self.config = config or {}

    def inspect(self, path=None):
        raise NotImplementedError(
            "Official API inspection is intentionally unimplemented. "
            "Wait for official API documentation and authorized access details."
        )

    def read_rows(self, path=None, sheet_name=None):
        raise NotImplementedError(
            "Official API retrieval is intentionally unimplemented. "
            "Wait for official API documentation and authorized access details."
        )
