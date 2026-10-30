"""Duplicate-record detection for the secondary experiment."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from string import digits
import time
import tracemalloc
from typing import Callable, Iterable

from .metrics import BinaryClassificationMetrics
from .synthetic_data import DatasetSplit, SyntheticDataset, WorkforceHistoryRecord


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
    partition: str
    record_count: int
    total_pair_count: int
    blocked_pair_count: int
    true_pair_count: int
    blocked_true_pair_count: int
    candidate_metrics: BinaryClassificationMetrics
    candidate_average_precision: float | None
    # Runtime and memory measurements (protocol requirement).
    # blocking_time_s: wall-clock seconds spent building the candidate set.
    # scoring_time_s: wall-clock seconds spent computing similarity scores.
    # peak_memory_bytes: peak tracemalloc allocation delta during full evaluation.
    blocking_time_s: float = 0.0
    scoring_time_s: float = 0.0
    peak_memory_bytes: int = 0

    @property
    def blocking_recall(self) -> float:
        return (
            self.blocked_true_pair_count / self.true_pair_count
            if self.true_pair_count else 0.0
        )

    @property
    def reduction_ratio(self) -> float:
        return (
            1.0 - self.blocked_pair_count / self.total_pair_count
            if self.total_pair_count else 0.0
        )

    @property
    def candidates_per_1000_records(self) -> float:
        """Number of candidate pairs surfaced per 1,000 evaluated records."""
        return (
            self.blocked_pair_count / self.record_count * 1000
            if self.record_count else 0.0
        )

    @property
    def false_matches_per_1000_records(self) -> float:
        """Number of false-positive pairs per 1,000 evaluated records."""
        return (
            self.metrics.false_positives / self.record_count * 1000
            if self.record_count else 0.0
        )


def normalized_similarity(left: str, right: str) -> float:
    """Return a deterministic string similarity score in the range [0, 1]."""

    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
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
    threshold: float = 0.70,
) -> tuple[DuplicateCandidate, ...]:
    """Find likely duplicates with weighted similarity across identity fields."""

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in the range [0, 1]")
    candidates: list[DuplicateCandidate] = []
    for left, right in _blocked_similarity_pairs(records):
        name_score = normalized_similarity(left.identity.full_name, right.identity.full_name)
        dob_match = (
            left.identity.date_of_birth is not None
            and right.identity.date_of_birth is not None
            and left.identity.date_of_birth == right.identity.date_of_birth
        )
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
    threshold: float = 0.70,
    split: DatasetSplit = DatasetSplit.TEST,
) -> DuplicateEvaluation:
    """Evaluate duplicate detection on one entity-disjoint partition.

    Measures wall-clock time for blocking and scoring separately, and peak
    tracemalloc allocation across the full evaluation.  Both are stored on
    the returned DuplicateEvaluation for protocol reporting.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    records = tuple(record for record in dataset.records if record.split is split)
    scored_candidates: tuple[DuplicateCandidate, ...] = ()
    threshold_used: float | None = None

    # --- Blocking phase (timed) ---
    block_start = time.perf_counter()
    blocked_pairs_raw = tuple(_blocked_similarity_pairs(records))
    blocking_time_s = time.perf_counter() - block_start

    blocked_pairs = {
        _pair_key(left.identity.employee_id, right.identity.employee_id)
        for left, right in blocked_pairs_raw
    }

    # --- Scoring / candidate selection phase (timed) ---
    score_start = time.perf_counter()
    if method == "exact":
        candidates = find_exact_duplicate_candidates(records)
    elif method == "normalized_exact":
        candidates = find_normalized_exact_duplicate_candidates(records)
    elif method == "similarity":
        scored_candidates = _scored_similarity_candidates(records)
        candidates = tuple(
            candidate for candidate in scored_candidates
            if candidate.score >= threshold
        )
        threshold_used = threshold
    else:
        raise ValueError(f"Unsupported duplicate detection method: {method}")
    scoring_time_s = time.perf_counter() - score_start

    # --- Peak memory ---
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
    peak_memory_bytes = max((stat.size_diff for stat in top_stats), default=0)

    predicted_pairs = {_pair_key(candidate.left_employee_id, candidate.right_employee_id) for candidate in candidates}
    true_pairs = _true_duplicate_pairs(records)
    true_positives = len(predicted_pairs & true_pairs)
    false_positives = len(predicted_pairs - true_pairs)
    false_negatives = len(true_pairs - predicted_pairs)
    total_pairs = len(records) * (len(records) - 1) // 2
    true_negatives = total_pairs - true_positives - false_positives - false_negatives
    blocked_true_pairs = blocked_pairs & true_pairs
    candidate_metrics = confusion_counts_for_pairs(
        predicted_pairs,
        blocked_true_pairs,
        len(blocked_pairs),
    )
    candidate_average_precision = None
    if scored_candidates and blocked_true_pairs:
        from sklearn.metrics import average_precision_score

        candidate_average_precision = float(average_precision_score(
            [
                _pair_key(candidate.left_employee_id, candidate.right_employee_id)
                in blocked_true_pairs
                for candidate in scored_candidates
            ],
            [candidate.score for candidate in scored_candidates],
        ))
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
        partition=split.value,
        record_count=len(records),
        total_pair_count=total_pairs,
        blocked_pair_count=len(blocked_pairs),
        true_pair_count=len(true_pairs),
        blocked_true_pair_count=len(blocked_pairs & true_pairs),
        candidate_metrics=candidate_metrics,
        candidate_average_precision=candidate_average_precision,
        blocking_time_s=blocking_time_s,
        scoring_time_s=scoring_time_s,
        peak_memory_bytes=max(peak_memory_bytes, 0),
    )


def select_similarity_threshold(
    dataset: SyntheticDataset,
    split: DatasetSplit = DatasetSplit.VALIDATION,
) -> float:
    """Select a similarity threshold from one non-test partition by F1."""

    records = tuple(record for record in dataset.records if record.split is split)
    scored = _scored_similarity_candidates(records)
    if not scored:
        raise ValueError("similarity threshold selection requires blocked pairs")
    true_pairs = _true_duplicate_pairs(records)
    thresholds = sorted({candidate.score for candidate in scored}, reverse=True)
    selections = []
    for threshold in thresholds:
        predicted = {
            _pair_key(candidate.left_employee_id, candidate.right_employee_id)
            for candidate in scored
            if candidate.score >= threshold
        }
        metrics = confusion_counts_for_pairs(predicted, true_pairs, len(scored))
        selections.append((metrics.f1, metrics.precision, metrics.recall, threshold))
    return max(selections)[3]


def confusion_counts_for_pairs(
    predicted_pairs: set[tuple[str, str]],
    true_pairs: set[tuple[str, str]],
    candidate_pair_count: int,
) -> BinaryClassificationMetrics:
    """Return candidate-set metrics without counting unblocked pairs as negatives."""

    true_positives = len(predicted_pairs & true_pairs)
    false_positives = len(predicted_pairs - true_pairs)
    false_negatives = len(true_pairs - predicted_pairs)
    true_negatives = candidate_pair_count - true_positives - false_positives
    return BinaryClassificationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        true_negatives=max(true_negatives, 0),
        false_negatives=false_negatives,
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
        if record.identity.date_of_birth is not None:
            groups.setdefault(("dob", record.identity.date_of_birth), []).append(record.identity.employee_id)
        normalized_id = normalize_identifier(record.identity.national_id)
        if normalized_id:
            groups.setdefault(("national_id", normalized_id), []).append(record.identity.employee_id)
        normalized_name = normalize_text(record.identity.full_name)
        if normalized_name:
            groups.setdefault(("name", normalized_name), []).append(record.identity.employee_id)
            groups.setdefault(
                ("first_name", normalized_name.split()[0]), []
            ).append(record.identity.employee_id)
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


def _scored_similarity_candidates(
    records: tuple[WorkforceHistoryRecord, ...],
) -> tuple[DuplicateCandidate, ...]:
    return find_similarity_duplicate_candidates(records, threshold=0.0)
