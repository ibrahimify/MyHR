"""Duplicate-record detection for the secondary experiment."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from string import digits
from typing import Callable, Iterable

from .metrics import BinaryClassificationMetrics
from .synthetic_data import SyntheticDataset, WorkforceHistoryRecord


DUPLICATE_METHODS = (
    "exact",
    "normalized_exact",
    "similarity",
)


@dataclass(frozen=True)
class DuplicateCandidate:
    """Potential duplicate pair with field-level review evidence."""

    left_employee_id: str
    right_employee_id: str
    method: str
    score: float
    evidence: dict[str, float | bool]


@dataclass(frozen=True)
class DuplicateEvaluation:
    method: str
    threshold: float | None
    candidates: tuple[DuplicateCandidate, ...]
    metrics: BinaryClassificationMetrics


def normalized_similarity(left: str, right: str) -> float:
    """Return a deterministic string similarity score in the range [0, 1]."""

    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.casefold().strip().split())


def normalize_identifier(value: str | None) -> str:
    if value is None:
        return ""
    normalized = normalize_text(value)
    if "-" in normalized:
        prefix, _, suffix = normalized.partition("-")
        suffix = suffix.lstrip("0") or "0"
        return f"{prefix}-{suffix}"
    return normalized.lstrip("0") or normalized


def normalize_email(value: str | None) -> str:
    return normalize_text(value)


def find_exact_duplicate_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
) -> tuple[DuplicateCandidate, ...]:
    """Find duplicates using raw exact ID fields only."""

    return _grouped_exact_candidates(
        records=records,
        method="exact",
        field_specs=(
            ("same_national_id", lambda record: record.identity.national_id or ""),
            ("same_email", lambda record: record.identity.email or ""),
        ),
    )


def find_normalized_exact_duplicate_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
) -> tuple[DuplicateCandidate, ...]:
    """Find duplicates after basic field normalization."""

    return _grouped_exact_candidates(
        records=records,
        method="normalized_exact",
        field_specs=(
            ("same_normalized_national_id", lambda record: normalize_identifier(record.identity.national_id)),
            ("same_normalized_email", lambda record: normalize_email(record.identity.email)),
        ),
    )


def find_similarity_duplicate_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
    threshold: float = 0.86,
) -> tuple[DuplicateCandidate, ...]:
    """Find likely duplicates with weighted similarity across identity fields."""

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in the range [0, 1]")
    candidates: list[DuplicateCandidate] = []
    for left, right in _blocked_similarity_pairs(records):
        name_score = normalized_similarity(left.identity.full_name, right.identity.full_name)
        dob_match = left.identity.date_of_birth == right.identity.date_of_birth
        national_id_score = _identifier_similarity(left.identity.national_id, right.identity.national_id)
        email_score = normalized_similarity(left.identity.email or "", right.identity.email or "")
        score = (
            0.35 * name_score
            + 0.30 * (1.0 if dob_match else 0.0)
            + 0.25 * national_id_score
            + 0.10 * email_score
        )
        if score >= threshold:
            candidates.append(
                DuplicateCandidate(
                    left_employee_id=left.identity.employee_id,
                    right_employee_id=right.identity.employee_id,
                    method="similarity",
                    score=score,
                    evidence={
                        "name_similarity": name_score,
                        "date_of_birth_match": dob_match,
                        "national_id_similarity": national_id_score,
                        "email_similarity": email_score,
                    },
                )
            )
    return tuple(candidates)


def evaluate_duplicate_detection(
    dataset: SyntheticDataset,
    method: str,
    threshold: float = 0.86,
) -> DuplicateEvaluation:
    """Evaluate duplicate detection against synthetic duplicate ground truth."""

    records = dataset.records
    if method == "exact":
        candidates = find_exact_duplicate_candidates(records)
        threshold_used = None
    elif method == "normalized_exact":
        candidates = find_normalized_exact_duplicate_candidates(records)
        threshold_used = None
    elif method == "similarity":
        candidates = find_similarity_duplicate_candidates(records, threshold)
        threshold_used = threshold
    else:
        raise ValueError(f"Unsupported duplicate detection method: {method}")

    predicted_pairs = {_pair_key(candidate.left_employee_id, candidate.right_employee_id) for candidate in candidates}
    true_pairs = _true_duplicate_pairs(records)
    true_positives = len(predicted_pairs & true_pairs)
    false_positives = len(predicted_pairs - true_pairs)
    false_negatives = len(true_pairs - predicted_pairs)
    total_pairs = len(records) * (len(records) - 1) // 2
    true_negatives = total_pairs - true_positives - false_positives - false_negatives
    return DuplicateEvaluation(
        method=method,
        threshold=threshold_used,
        candidates=candidates,
        metrics=BinaryClassificationMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
        ),
    )


def _record_pairs(records: tuple[WorkforceHistoryRecord, ...]) -> Iterable[tuple[WorkforceHistoryRecord, WorkforceHistoryRecord]]:
    for left_index, left in enumerate(records):
        for right in records[left_index + 1:]:
            yield left, right


def _true_duplicate_pairs(records: tuple[WorkforceHistoryRecord, ...]) -> set[tuple[str, str]]:
    source_by_id: dict[str, str] = {}
    for record in records:
        if record.duplicate_of_employee_id:
            source_by_id[record.identity.employee_id] = record.duplicate_of_employee_id
    clusters: dict[str, list[str]] = {}
    for record in records:
        employee_id = record.identity.employee_id
        root_id = employee_id
        visited: set[str] = set()
        while root_id in source_by_id:
            if root_id in visited:
                raise ValueError("duplicate source links must not contain cycles")
            visited.add(root_id)
            root_id = source_by_id[root_id]
        clusters.setdefault(root_id, []).append(employee_id)

    return {
        _pair_key(left_id, right_id)
        for employee_ids in clusters.values()
        if len(employee_ids) > 1
        for left_id, right_id in combinations(employee_ids, 2)
    }


def _grouped_exact_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
    method: str,
    field_specs: tuple[tuple[str, Callable[[WorkforceHistoryRecord], str]], ...],
) -> tuple[DuplicateCandidate, ...]:
    candidate_evidence: dict[tuple[str, str], dict[str, bool]] = {}
    records_by_id = {record.identity.employee_id: record for record in records}
    for evidence_name, key_fn in field_specs:
        groups: dict[str, list[str]] = {}
        for record in records:
            key = key_fn(record)
            if key:
                groups.setdefault(key, []).append(record.identity.employee_id)
        for employee_ids in groups.values():
            if len(employee_ids) < 2:
                continue
            for left_id, right_id in combinations(employee_ids, 2):
                key = _pair_key(left_id, right_id)
                candidate_evidence.setdefault(key, {})[evidence_name] = True

    candidates: list[DuplicateCandidate] = []
    for left_id, right_id in sorted(candidate_evidence):
        evidence = {
            evidence_name: bool(candidate_evidence[(left_id, right_id)].get(evidence_name, False))
            for evidence_name, _ in field_specs
        }
        candidates.append(
            DuplicateCandidate(
                left_employee_id=records_by_id[left_id].identity.employee_id,
                right_employee_id=records_by_id[right_id].identity.employee_id,
                method=method,
                score=1.0,
                evidence=evidence,
            )
        )
    return tuple(candidates)


def _blocked_similarity_pairs(
    records: tuple[WorkforceHistoryRecord, ...],
) -> Iterable[tuple[WorkforceHistoryRecord, WorkforceHistoryRecord]]:
    """Return reviewable candidate pairs without scanning every unrelated employee."""

    pairs: set[tuple[str, str]] = set()
    records_by_id = {record.identity.employee_id: record for record in records}
    groups: dict[object, list[str]] = {}
    for record in records:
        groups.setdefault(("dob", record.identity.date_of_birth), []).append(record.identity.employee_id)
        normalized_id = normalize_identifier(record.identity.national_id)
        if normalized_id:
            groups.setdefault(("national_id", normalized_id), []).append(record.identity.employee_id)
    for employee_ids in groups.values():
        if len(employee_ids) < 2:
            continue
        for left_id, right_id in combinations(employee_ids, 2):
            pairs.add(_pair_key(left_id, right_id))
    for left_id, right_id in sorted(pairs):
        yield records_by_id[left_id], records_by_id[right_id]


def _pair_key(left_employee_id: str, right_employee_id: str | None) -> tuple[str, str]:
    if right_employee_id is None:
        raise ValueError("right_employee_id must not be None")
    return tuple(sorted((left_employee_id, right_employee_id)))


def _identifier_similarity(left: str | None, right: str | None) -> float:
    left_normalized = normalize_identifier(left)
    right_normalized = normalize_identifier(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    left_digits = "".join(character for character in left_normalized if character in digits)
    right_digits = "".join(character for character in right_normalized if character in digits)
    if left_digits and right_digits and left_digits == right_digits:
        return 0.95
    return normalized_similarity(left_normalized, right_normalized)
