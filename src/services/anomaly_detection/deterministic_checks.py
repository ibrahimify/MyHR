"""Deterministic validation checks for explicit administrative inconsistencies."""

from datetime import datetime


def date_is_not_after(left: datetime | None, right: datetime | None) -> bool:
    """Return True when the date order is valid or incomplete."""

    if left is None or right is None:
        return True
    return left <= right


def has_duplicate_identifier(identifier: str | None, seen_identifiers: set[str]) -> bool:
    """Check exact duplicate IDs while keeping state outside the function."""

    if not identifier:
        return False
    normalized = identifier.strip().lower()
    if normalized in seen_identifiers:
        return True
    seen_identifiers.add(normalized)
    return False
