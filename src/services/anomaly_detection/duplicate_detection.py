"""Duplicate-record detection for the secondary experiment."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from string import digits

from .metrics import BinaryClassificationMetrics, confusion_counts
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

    candidates: list[DuplicateCandidate] = []
    for left, right in _record_pairs(records):
        same_national_id = bool(left.identity.national_id and left.identity.national_id == right.identity.national_id)
        same_email = bool(left.identity.email and left.identity.email == right.identity.email)
        if same_national_id or same_email:
            candidates.append(
                DuplicateCandidate(
                    left_employee_id=left.identity.employee_id,
                    right_employee_id=right.identity.employee_id,
                    method="exact",
                    score=1.0,
                    evidence={
                        "same_national_id": same_national_id,
                        "same_email": same_email,
                    },
                )
            )
    return tuple(candidates)


def find_normalized_exact_duplicate_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
) -> tuple[DuplicateCandidate, ...]:
    """Find duplicates after basic field normalization."""

    candidates: list[DuplicateCandidate] = []
    for left, right in _record_pairs(records):
        same_national_id = (
            bool(left.identity.national_id and right.identity.national_id)
            and normalize_identifier(left.identity.national_id) == normalize_identifier(right.identity.national_id)
        )
        same_email = (
            bool(left.identity.email and right.identity.email)
            and normalize_email(left.identity.email) == normalize_email(right.identity.email)
        )
        if same_national_id or same_email:
            candidates.append(
                DuplicateCandidate(
                    left_employee_id=left.identity.employee_id,
                    right_employee_id=right.identity.employee_id,
                    method="normalized_exact",
                    score=1.0,
                    evidence={
                        "same_normalized_national_id": same_national_id,
                        "same_normalized_email": same_email,
                    },
                )
            )
    return tuple(candidates)


def find_similarity_duplicate_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
    threshold: float = 0.86,
) -> tuple[DuplicateCandidate, ...]:
    """Find likely duplicates with weighted similarity across identity fields."""

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in the range [0, 1]")
    candidates: list[DuplicateCandidate] = []
    for left, right in _record_pairs(records):
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

    all_pairs = tuple(_record_pairs(records))
    predicted_pairs = {_pair_key(candidate.left_employee_id, candidate.right_employee_id) for candidate in candidates}
    true_pairs = {
        _pair_key(record.identity.employee_id, record.duplicate_of_employee_id)
        for record in records
        if record.duplicate_of_employee_id
    }
    y_true = [_pair_key(left.identity.employee_id, right.identity.employee_id) in true_pairs for left, right in all_pairs]
    y_pred = [_pair_key(left.identity.employee_id, right.identity.employee_id) in predicted_pairs for left, right in all_pairs]
    return DuplicateEvaluation(
        method=method,
        threshold=threshold_used,
        candidates=candidates,
        metrics=confusion_counts(y_true, y_pred),
    )


def _record_pairs(records: tuple[WorkforceHistoryRecord, ...]) -> tuple[tuple[WorkforceHistoryRecord, WorkforceHistoryRecord], ...]:
    pairs: list[tuple[WorkforceHistoryRecord, WorkforceHistoryRecord]] = []
    for left_index, left in enumerate(records):
        for right in records[left_index + 1:]:
            pairs.append((left, right))
    return tuple(pairs)


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
