"""Duplicate-record detection boundary for the secondary experiment."""

from difflib import SequenceMatcher


def normalized_similarity(left: str, right: str) -> float:
    """Return a deterministic string similarity score in the range [0, 1]."""

    left_norm = " ".join(left.casefold().split())
    right_norm = " ".join(right.casefold().split())
    return SequenceMatcher(None, left_norm, right_norm).ratio()
