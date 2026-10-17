"""UTC clock helpers for the application's timezone-naive database fields."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC while preserving the existing naive-datetime schema contract."""
    return datetime.now(UTC).replace(tzinfo=None)
