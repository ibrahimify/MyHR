"""Synthetic workforce-history contracts and generator for experiments."""

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from enum import Enum
from hashlib import sha256
from random import Random


class DatasetSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class EmploymentTrack(str, Enum):
    PROMOTION = "promotion"
    OTHER = "other"


class AdministrativeEventType(str, Enum):
    HIRE = "hire"
    PROMOTION = "promotion"
    COMMENDATION = "commendation"
    SANCTION = "sanction"
    SALARY_INCREMENT = "salary_increment"
    PERFORMANCE_REVIEW = "performance_review"
    ORGANIZATION_CHANGE = "organization_change"


class AnomalyType(str, Enum):
    CLEAN = "clean"
    INCONSISTENT_DATES = "inconsistent_dates"
    FREQUENT_PROMOTIONS = "frequent_promotions"
    EXCESSIVE_SANCTIONS = "excessive_sanctions"
    DUPLICATE_RECORD = "duplicate_record"
    UNUSUAL_ADMIN_INTERVAL = "unusual_admin_interval"
    POLICY_LEGITIMATE_RARE_CASE = "policy_legitimate_rare_case"


class HardNonduplicateKind(str, Enum):
    """Explicit mechanism for a hard nonduplicate record.

    Hard nonduplicates are real distinct individuals that share surface
    features likely to trigger naive similarity detectors.  They are NOT
    true duplicates and must never appear in _true_duplicate_pairs.
    """

    SIMILAR_NAME = "similar_name"        # same first name, different family
    SHARED_BIRTHDAY = "shared_birthday"  # same date_of_birth, different person
    RELATIVE = "relative"                # same family name, different DOB
    NEAR_IDENTICAL_ID = "near_identical_id"  # identifier one-digit apart


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration shared by synthetic data and experiment runners."""

    seed: int = 2026
    employee_count: int = 1000
    anomaly_rate: float = 0.08
    rare_legitimate_rate: float = 0.04
    train_ratio: float = 0.60
    validation_ratio: float = 0.20
    test_ratio: float = 0.20

    def validate(self) -> None:
        if self.employee_count <= 0:
            raise ValueError("employee_count must be positive")
        for name in ("anomaly_rate", "rare_legitimate_rate", "train_ratio", "validation_ratio", "test_ratio"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        ratio_total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(ratio_total - 1.0) > 1e-9:
            raise ValueError("train, validation, and test ratios must sum to 1.0")
        if self.anomaly_rate + self.rare_legitimate_rate >= 1:
            raise ValueError("anomaly_rate and rare_legitimate_rate must leave room for clean records")

    def run_id(self) -> str:
        payload = repr(sorted(asdict(self).items())).encode("utf-8")
        return sha256(payload).hexdigest()[:12]


def seeded_random(config: ExperimentConfig) -> Random:
    config.validate()
    return Random(config.seed)


def split_indices(count: int, config: ExperimentConfig) -> dict[str, list[int]]:
    """Return deterministic train/validation/test index partitions."""

    if count < 0:
        raise ValueError("count must be non-negative")
    rng = seeded_random(config)
    indices = list(range(count))
    rng.shuffle(indices)

    train_end = int(count * config.train_ratio)
    validation_end = train_end + int(count * config.validation_ratio)

    return {
        DatasetSplit.TRAIN.value: indices[:train_end],
        DatasetSplit.VALIDATION.value: indices[train_end:validation_end],
        DatasetSplit.TEST.value: indices[validation_end:],
    }


@dataclass(frozen=True)
class EmployeeIdentity:
    """Identity fields needed for employee history and duplicate experiments."""

    employee_id: str
    full_name: str
    date_of_birth: date
    national_id: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class LatentPerson:
    """A fictional base entity from which one or more duplicate records are derived.

    The latent person is generated first, outside any dataset partition.
    Each record derived from this person inherits or mutates its identity
    fields.  Storing the latent_person_id on every derived record allows
    the auditor to verify partition containment by construction rather than
    by checking a pointer chain after the fact.
    """

    latent_person_id: str
    full_name: str
    date_of_birth: date
    national_id: str | None
    email: str | None


@dataclass(frozen=True)
class AdministrativeEvent:
    """One timestamped administrative event in an employee history."""

    event_type: AdministrativeEventType
    event_date: date
    source_id: str
    level_before: str | None = None
    level_after: str | None = None
    value_before: float | int | str | None = None
    value_after: float | int | str | None = None
    category: int | str | None = None
    is_resolved: bool = False
    resolved_date: date | None = None
    note: str = ""
    recorded_date: date | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    approval_reference: str | None = None
    approval_status: str | None = None
    recognized_service_months: int = 0
    correction_of_source_id: str | None = None
    retry_of_source_id: str | None = None
    jurisdiction: str = "organization-wide"


@dataclass(frozen=True)
class WorkforceHistoryRecord:
    """One synthetic employee history with ground-truth anomaly labels."""

    identity: EmployeeIdentity
    split: DatasetSplit
    employment_track: EmploymentTrack
    current_level: str | None
    department: str
    role: str
    hire_date: date
    events: tuple[AdministrativeEvent, ...]
    anomaly_labels: tuple[AnomalyType, ...] = (AnomalyType.CLEAN,)
    duplicate_of_employee_id: str | None = None
    observation_date: date | None = None
    # Latent-person-first duplicate provenance.  Set on every record derived
    # from a LatentPerson cluster (source and all variants).  None for all
    # non-duplicate records.
    latent_person_id: str | None = None
    # Explicit mechanism for hard nonduplicates.  Set only on records
    # intentionally generated as confusable-but-distinct individuals.
    hard_nonduplicate_kind: HardNonduplicateKind | None = None
    # The anchor employee_id whose surface features this hard nonduplicate was
    # made to resemble. Recorded so the intended difficult pair is traceable and
    # verifiable as jointly present in one partition.
    hard_nonduplicate_anchor_id: str | None = None

    @property
    def has_anomaly(self) -> bool:
        non_anomalous_labels = {AnomalyType.CLEAN, AnomalyType.POLICY_LEGITIMATE_RARE_CASE}
        return any(label not in non_anomalous_labels for label in self.anomaly_labels)

    @property
    def has_progression_anomaly(self) -> bool:
        progression_labels = {
            AnomalyType.INCONSISTENT_DATES,
            AnomalyType.FREQUENT_PROMOTIONS,
            AnomalyType.EXCESSIVE_SANCTIONS,
            AnomalyType.UNUSUAL_ADMIN_INTERVAL,
        }
        return any(label in progression_labels for label in self.anomaly_labels)


@dataclass(frozen=True)
class SyntheticDatasetMetadata:
    """Reproducibility metadata stored beside generated histories."""

    schema_version: str
    run_id: str
    seed: int
    employee_count: int
    split_counts: dict[str, int]
    label_counts: dict[str, int]


@dataclass(frozen=True)
class SyntheticDataset:
    """Generated dataset plus metadata required for paper evidence."""

    records: tuple[WorkforceHistoryRecord, ...]
    metadata: SyntheticDatasetMetadata


@dataclass(frozen=True)
class AnomalyDefinition:
    """Documented anomaly class used by generator, tests, and paper tables."""

    anomaly_type: AnomalyType
    definition: str
    expected_signal: str
    ground_truth_label: bool


def anomaly_taxonomy() -> tuple[AnomalyDefinition, ...]:
    """Return the fixed anomaly taxonomy for the first TDK experiments."""

    return (
        AnomalyDefinition(
            anomaly_type=AnomalyType.CLEAN,
            definition="Administrative history follows the modeled policy and contains no injected data-quality issue.",
            expected_signal="No deterministic inconsistency and no unusual pattern beyond normal variation.",
            ground_truth_label=False,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.INCONSISTENT_DATES,
            definition="One or more administrative events occur before their required predecessor or after an impossible reference date.",
            expected_signal="Negative service intervals, event order violations, or future-dated records.",
            ground_truth_label=True,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.FREQUENT_PROMOTIONS,
            definition="Promotion intervals are shorter than expected after accounting for policy credits and delays.",
            expected_signal="Short raw promotion gaps that remain unexplained after policy conditioning.",
            ground_truth_label=True,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.EXCESSIVE_SANCTIONS,
            definition="The employee history contains an unusually high number or density of disciplinary actions.",
            expected_signal="Sanction count or sanction frequency above baseline and peer-context thresholds.",
            ground_truth_label=True,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.DUPLICATE_RECORD,
            definition="Two employee records likely describe the same person with different identifiers or normalized values.",
            expected_signal="High similarity across identity fields despite non-identical raw values.",
            ground_truth_label=True,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.UNUSUAL_ADMIN_INTERVAL,
            definition="Administrative events have unusually long or short intervals that are not directly illegal.",
            expected_signal="Outlier gaps between reviews, increments, sanctions, or promotions.",
            ground_truth_label=True,
        ),
        AnomalyDefinition(
            anomaly_type=AnomalyType.POLICY_LEGITIMATE_RARE_CASE,
            definition="A rare-looking history is legitimate because policy context explains it, such as valid commendation credit.",
            expected_signal="Raw features appear unusual, while policy-aware features explain the record.",
            ground_truth_label=False,
        ),
    )


FIRST_NAMES = (
    "Anna",
    "Bence",
    "Csilla",
    "Daniel",
    "Eva",
    "Farid",
    "Gabriel",
    "Hanna",
    "Ibrahim",
    "Julia",
    "Katalin",
    "Laura",
    "Marcus",
    "Nora",
    "Omar",
    "Priya",
)

LAST_NAMES = (
    "Kovacs",
    "Nagy",
    "Toth",
    "Schmidt",
    "Novak",
    "Chen",
    "Hassan",
    "Yilmaz",
    "Shoeb",
    "Keller",
    "Miller",
    "Brown",
)

DEPARTMENTS = ("Engineering", "Finance", "Operations", "HR", "Data", "Compliance")

PROMOTION_ROLES = (
    "Junior Specialist",
    "Specialist",
    "Senior Specialist",
    "Team Lead",
    "Manager",
    "Director",
)

OTHER_ROLES = ("Janitor", "Receptionist", "Driver", "Maintenance Assistant", "Security Guard")

LEVELS = ("L7", "L6", "L5", "L4", "L3", "L2", "L1")


def generate_synthetic_dataset(config: ExperimentConfig) -> SyntheticDataset:
    """Generate deterministic synthetic histories with documented labels.

    Duplicate records are generated latent-person-first: for each cluster, a
    fictional base entity (LatentPerson) is created outside any partition, then
    all records in the cluster—the source and every variant—are derived from it.
    This guarantees partition containment by construction rather than by
    post-hoc pointer checking.

    Hard nonduplicate records are explicitly generated as confusable-but-distinct
    individuals.  They share surface features (name, DOB, identifier) with other
    records but are NOT true duplicates and must not appear in true_duplicate_pairs.
    """
    config.validate()
    rng = seeded_random(config)
    split_by_index = _split_by_index(config.employee_count, config)
    label_plan = _label_plan(config, rng, split_by_index)

    base_records = [
        _base_record(index, split_by_index[index], rng)
        for index in range(config.employee_count)
    ]

    # --- Latent-person-first duplicate generation ---
    # Identify which indices will become DUPLICATE_RECORD.
    duplicate_indices = [
        index for index, label in label_plan.items()
        if label is AnomalyType.DUPLICATE_RECORD
    ]
    # For each duplicate index, find a non-duplicate source in the same partition.
    # Generate a latent person for each cluster (one per duplicate record).
    latent_persons: dict[int, LatentPerson] = {}
    duplicate_source_ids: dict[int, str] = {}  # duplicate_index -> source employee_id
    used_source_indices: set[int] = set()
    for cluster_num, dup_idx in enumerate(sorted(duplicate_indices)):
        dup_split = split_by_index[dup_idx]
        same_split_sources = [
            index for index, label in label_plan.items()
            if label is AnomalyType.CLEAN
            and split_by_index[index] is dup_split
            and index != dup_idx
            and index not in used_source_indices
        ]
        if not same_split_sources:
            raise ValueError(
                f"latent-person duplicate generation: no source candidate in partition "
                f"{dup_split.value} for duplicate at index {dup_idx}"
            )
        source_index = same_split_sources[cluster_num % len(same_split_sources)]
        used_source_indices.add(source_index)
        latent_persons[dup_idx] = _generate_latent_person(cluster_num, rng)
        duplicate_source_ids[dup_idx] = base_records[source_index].identity.employee_id

    # Map each source record to the latent person it must become. The source
    # record's identity is overwritten with the latent person's canonical
    # identity so that the source genuinely IS that person; each duplicate is a
    # corrupted copy of the same facts. This is what makes the pair a real
    # same-person cluster rather than two unrelated identities sharing a tag.
    source_to_latent: dict[str, LatentPerson] = {}  # source employee_id -> latent person
    for dup_idx, latent in latent_persons.items():
        src_id = duplicate_source_ids[dup_idx]
        source_to_latent[src_id] = latent

    # Canonicalize source identities before deriving variants. Duplicate records
    # are then copied from this canonical source record, including the same
    # employment and administrative history, rather than retaining an unrelated
    # independently generated history.
    canonical_base_records: list[WorkforceHistoryRecord] = []
    for record in base_records:
        latent_for_source = source_to_latent.get(record.identity.employee_id)
        if latent_for_source is None:
            canonical_base_records.append(record)
            continue
        canonical_base_records.append(replace(
            record,
            identity=_canonical_latent_identity(
                latent_for_source, record.identity.employee_id
            ),
            latent_person_id=latent_for_source.latent_person_id,
        ))
    canonical_by_id = {
        record.identity.employee_id: record for record in canonical_base_records
    }

    # Apply labels and build final records.
    records: list[WorkforceHistoryRecord] = []
    for index, record in enumerate(canonical_base_records):
        label = label_plan[index]
        if label is AnomalyType.DUPLICATE_RECORD:
            person = latent_persons[index]
            src_id = duplicate_source_ids[index]
            variant = index % 4
            record = _apply_latent_person_duplicate(
                canonical_by_id[src_id],
                person,
                src_id,
                record.identity.employee_id,
                variant,
            )
        elif label is not AnomalyType.CLEAN:
            # All other anomaly types use the original _apply_label path.
            non_duplicate_sources = tuple(
                r for i, r in enumerate(canonical_base_records)
                if label_plan[i] is not AnomalyType.DUPLICATE_RECORD
            )
            record = _apply_label(record, label, non_duplicate_sources, rng)
        records.append(record)

    # --- Hard nonduplicate injection ---
    # Add one explicit hard nonduplicate record for each HardNonduplicateKind.
    # Each (anchor, target) pair must be CO-PARTITIONED so the intended difficult
    # negative is jointly present in the evaluated split (finding R8). We prefer
    # the TEST split (the evaluated partition) and fall back to whichever split
    # has enough clean records. Cluster members (duplicate sources, tagged with
    # latent_person_id) are excluded so a hard-nonduplicate mutation can never
    # overwrite a canonical duplicate-source identity. The anchor employee_id is
    # recorded on the target so the pair is traceable.
    hard_nonduplicate_kinds = list(HardNonduplicateKind)
    hard_rng = Random(config.seed ^ 0xDEAD_BEEF)
    clean_by_split: dict[DatasetSplit, list[WorkforceHistoryRecord]] = {}
    for r in records:
        if r.anomaly_labels == (AnomalyType.CLEAN,) and r.latent_person_id is None:
            clean_by_split.setdefault(r.split, []).append(r)
    # Order splits by preference: TEST first, then VALIDATION, then TRAIN.
    split_preference = [DatasetSplit.TEST, DatasetSplit.VALIDATION, DatasetSplit.TRAIN]
    needed = 2 * len(hard_nonduplicate_kinds)
    host_split = next(
        (s for s in split_preference if len(clean_by_split.get(s, [])) >= needed),
        None,
    )
    if host_split is not None:
        pool = list(clean_by_split[host_split])
        hard_rng.shuffle(pool)
        used_ids: set[str] = set()
        for kind_idx, kind in enumerate(hard_nonduplicate_kinds):
            anchor = pool[kind_idx * 2]
            target_record = pool[kind_idx * 2 + 1]
            modified = _apply_hard_nonduplicate(target_record, kind, anchor)
            for list_idx, r in enumerate(records):
                if r.identity.employee_id == target_record.identity.employee_id:
                    records[list_idx] = modified
                    break

    metadata = SyntheticDatasetMetadata(
        schema_version="tdk-synthetic-v2",
        run_id=config.run_id(),
        seed=config.seed,
        employee_count=config.employee_count,
        split_counts=_split_counts(records),
        label_counts=_label_counts(records),
    )
    return SyntheticDataset(records=tuple(records), metadata=metadata)


def serialize_dataset(dataset: SyntheticDataset) -> dict[str, object]:
    """Return a deterministic JSON-compatible view for tests and artifacts."""

    return {
        "metadata": asdict(dataset.metadata),
        "records": [_record_to_dict(record) for record in dataset.records],
    }


def _split_by_index(count: int, config: ExperimentConfig) -> dict[int, DatasetSplit]:
    splits = split_indices(count, config)
    by_index: dict[int, DatasetSplit] = {}
    for split_name, indices in splits.items():
        split = DatasetSplit(split_name)
        for index in indices:
            by_index[index] = split
    return by_index


def _label_plan(
    config: ExperimentConfig,
    rng: Random,
    split_by_index: dict[int, DatasetSplit],
) -> dict[int, AnomalyType]:
    plan = {index: AnomalyType.CLEAN for index in range(config.employee_count)}
    anomaly_count = int(config.employee_count * config.anomaly_rate)
    rare_count = int(config.employee_count * config.rare_legitimate_rate)
    true_anomalies = (
        AnomalyType.INCONSISTENT_DATES,
        AnomalyType.FREQUENT_PROMOTIONS,
        AnomalyType.EXCESSIVE_SANCTIONS,
        AnomalyType.DUPLICATE_RECORD,
        AnomalyType.UNUSUAL_ADMIN_INTERVAL,
    )

    split_indices = {
        split: [index for index, index_split in split_by_index.items() if index_split is split]
        for split in DatasetSplit
    }
    for indices in split_indices.values():
        rng.shuffle(indices)

    anomaly_allocations = _allocate_count_by_split(anomaly_count, split_indices)
    rare_allocations = _allocate_count_by_split(rare_count, split_indices)

    anomaly_offset = 0
    for split in DatasetSplit:
        for _ in range(anomaly_allocations[split]):
            index = split_indices[split].pop()
            plan[index] = true_anomalies[anomaly_offset % len(true_anomalies)]
            anomaly_offset += 1

    rare_candidates = {
        split: [
            index for index in split_indices[split]
            if _employment_track_for_index(index) is EmploymentTrack.PROMOTION
        ]
        for split in DatasetSplit
    }
    if any(len(rare_candidates[split]) < rare_allocations[split] for split in DatasetSplit):
        raise ValueError("rare_legitimate_rate exceeds available promotion-track records")
    for split in DatasetSplit:
        for _ in range(rare_allocations[split]):
            index = rare_candidates[split].pop()
            plan[index] = AnomalyType.POLICY_LEGITIMATE_RARE_CASE

    if plan.get(0) is AnomalyType.DUPLICATE_RECORD and config.employee_count > 1:
        swap_index = next(index for index in range(1, config.employee_count) if plan[index] is not AnomalyType.DUPLICATE_RECORD)
        plan[0], plan[swap_index] = plan[swap_index], plan[0]
    return plan


def _allocate_count_by_split(
    count: int,
    split_indices: dict[DatasetSplit, list[int]],
) -> dict[DatasetSplit, int]:
    total = sum(len(indices) for indices in split_indices.values())
    if count <= 0 or total == 0:
        return {split: 0 for split in DatasetSplit}

    raw_allocations = {
        split: count * len(indices) / total
        for split, indices in split_indices.items()
    }
    allocations = {
        split: min(int(raw_allocations[split]), len(split_indices[split]))
        for split in DatasetSplit
    }
    remaining = count - sum(allocations.values())
    ordered_splits = sorted(
        DatasetSplit,
        key=lambda split: raw_allocations[split] - int(raw_allocations[split]),
        reverse=True,
    )
    while remaining > 0:
        changed = False
        for split in ordered_splits:
            if allocations[split] < len(split_indices[split]):
                allocations[split] += 1
                remaining -= 1
                changed = True
                if remaining == 0:
                    break
        if not changed:
            break
    return allocations


def _base_record(index: int, split: DatasetSplit, rng: Random) -> WorkforceHistoryRecord:
    employee_number = index + 1
    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    full_name = f"{first_name} {last_name}"
    track = _employment_track_for_index(index)
    department = DEPARTMENTS[index % len(DEPARTMENTS)]
    hire_year = rng.randint(2014, 2024)
    hire_month = rng.randint(1, 12)
    hire_day = min(rng.randint(1, 28), 28)
    hire_date = date(hire_year, hire_month, hire_day)

    events = [
        AdministrativeEvent(
            event_type=AdministrativeEventType.HIRE,
            event_date=hire_date,
            source_id=f"HIRE-{employee_number:04d}",
            level_after="L7" if track is EmploymentTrack.PROMOTION else None,
            note="Synthetic hire event",
        )
    ]

    current_level: str | None = None
    if track is EmploymentTrack.PROMOTION:
        current_level = "L7"
        role = PROMOTION_ROLES[min(index % len(PROMOTION_ROLES), len(PROMOTION_ROLES) - 1)]
        promotion_count = min((2026 - hire_year) // 3, 3)
        for step in range(1, promotion_count + 1):
            before = LEVELS[step - 1]
            after = LEVELS[step]
            current_level = after
            events.append(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=_safe_date(hire_year + step * 3, hire_month, hire_day),
                    source_id=f"PROM-{employee_number:04d}-{step}",
                    level_before=before,
                    level_after=after,
                    note="Synthetic regular promotion",
                )
            )
    else:
        role = OTHER_ROLES[index % len(OTHER_ROLES)]

    for year in range(hire_year + 1, 2027):
        events.append(
            AdministrativeEvent(
                event_type=AdministrativeEventType.SALARY_INCREMENT,
                event_date=_safe_date(year, hire_month, hire_day),
                source_id=f"INC-{employee_number:04d}-{year}",
                value_before=1000 + employee_number,
                value_after=1030 + employee_number,
                note="Synthetic annual increment",
            )
        )
        if year >= 2022 and year % 2 == 0:
            events.append(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PERFORMANCE_REVIEW,
                    event_date=_safe_date(year, min(hire_month + 1, 12), hire_day),
                    source_id=f"REV-{employee_number:04d}-{year}",
                    value_after=rng.randint(62, 94),
                    note="Synthetic periodic performance review",
                )
            )

    if rng.random() < 0.18:
        events.append(
            AdministrativeEvent(
                event_type=AdministrativeEventType.COMMENDATION,
                event_date=_safe_date(max(hire_year + 1, 2022), rng.randint(1, 12), rng.randint(1, 28)),
                source_id=f"COM-{employee_number:04d}-1",
                category=rng.choice((1, 2, 3)),
                note="Synthetic commendation",
            )
        )
    if rng.random() < 0.10:
        promotion_dates = [
            event.event_date
            for event in events
            if event.event_type is AdministrativeEventType.PROMOTION
        ]
        last_promotion_date = max(promotion_dates, default=hire_date)
        sanction_date = min(last_promotion_date + timedelta(days=1), date(2026, 12, 31))
        events.append(
            AdministrativeEvent(
                event_type=AdministrativeEventType.SANCTION,
                event_date=sanction_date,
                source_id=f"SAN-{employee_number:04d}-1",
                category=rng.choice((1, 2)),
                note="Synthetic sanction",
            )
        )

    return WorkforceHistoryRecord(
        identity=EmployeeIdentity(
            employee_id=f"EMP-{employee_number:04d}",
            full_name=full_name,
            date_of_birth=_safe_date(rng.randint(1970, 2001), rng.randint(1, 12), rng.randint(1, 28)),
            national_id=f"NID-{employee_number:06d}",
            email=f"{first_name.lower()}.{last_name.lower()}{employee_number}@synthetic.myhr",
        ),
        split=split,
        employment_track=track,
        current_level=current_level,
        department=department,
        role=role,
        hire_date=hire_date,
        events=tuple(sorted(events, key=lambda event: (event.event_date, event.source_id))),
    )


def _employment_track_for_index(index: int) -> EmploymentTrack:
    return EmploymentTrack.PROMOTION if index % 5 != 0 else EmploymentTrack.OTHER


def _apply_label(
    record: WorkforceHistoryRecord,
    label: AnomalyType,
    existing_records: list[WorkforceHistoryRecord],
    rng: Random,
) -> WorkforceHistoryRecord:
    employee_id = record.identity.employee_id
    events = list(record.events)

    if label is AnomalyType.INCONSISTENT_DATES:
        events.append(
            AdministrativeEvent(
                event_type=AdministrativeEventType.PROMOTION,
                event_date=_safe_date(record.hire_date.year - 1, record.hire_date.month, record.hire_date.day),
                source_id=f"BAD-DATE-{employee_id}",
                level_before="L7",
                level_after="L6",
                note="Injected date inconsistency: promotion before hire",
            )
        )
    elif label is AnomalyType.FREQUENT_PROMOTIONS:
        events.extend(
            (
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=_safe_date(record.hire_date.year, min(record.hire_date.month + 2, 12), record.hire_date.day),
                    source_id=f"FAST-PROM-1-{employee_id}",
                    level_before="L7",
                    level_after="L6",
                    note="Injected frequent promotion",
                ),
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=_safe_date(record.hire_date.year, min(record.hire_date.month + 4, 12), record.hire_date.day),
                    source_id=f"FAST-PROM-2-{employee_id}",
                    level_before="L6",
                    level_after="L5",
                    note="Injected frequent promotion",
                ),
            )
        )
    elif label is AnomalyType.EXCESSIVE_SANCTIONS:
        for offset in range(5):
            events.append(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.SANCTION,
                    event_date=_safe_date(2026, 1 + offset, 10),
                    source_id=f"MANY-SAN-{employee_id}-{offset}",
                    category=2,
                    note="Injected excessive sanctions",
                )
            )
    elif label is AnomalyType.DUPLICATE_RECORD and existing_records:
        same_partition_sources = [
            candidate for candidate in existing_records
            if candidate.split is record.split
            and candidate.identity.employee_id != record.identity.employee_id
        ]
        if not same_partition_sources:
            raise ValueError("duplicate generation requires a source in the same partition")
        source = rng.choice(same_partition_sources)
        variant = int("".join(character for character in employee_id if character.isdigit())) % 4
        identity = EmployeeIdentity(
            employee_id=employee_id,
            full_name=(
                _shorten_name(source.identity.full_name)
                if variant in {0, 3}
                else _name_typo(source.identity.full_name)
                if variant == 1
                else source.identity.full_name
            ),
            date_of_birth=(
                _variant_birth_date(source.identity.date_of_birth)
                if variant in {1, 3}
                else source.identity.date_of_birth
            ),
            national_id=(
                _transpose_identifier(source.identity.national_id)
                if variant in {2, 3}
                else _drop_leading_zeroes(source.identity.national_id)
            ),
            email=None if variant == 2 else _variant_email(source.identity.email),
        )
        return replace(
            record,
            identity=identity,
            anomaly_labels=(label,),
            duplicate_of_employee_id=source.identity.employee_id,
        )
    elif label is AnomalyType.UNUSUAL_ADMIN_INTERVAL:
        events.extend(
            (
                AdministrativeEvent(
                    event_type=AdministrativeEventType.SALARY_INCREMENT,
                    event_date=date(2026, 3, 1),
                    source_id=f"CLOSE-INC-1-{employee_id}",
                    value_before=3000,
                    value_after=3090,
                    note="Injected unusually short increment interval",
                ),
                AdministrativeEvent(
                    event_type=AdministrativeEventType.SALARY_INCREMENT,
                    event_date=date(2026, 3, 3),
                    source_id=f"CLOSE-INC-2-{employee_id}",
                    value_before=3090,
                    value_after=3180,
                    note="Injected unusually short increment interval",
                ),
            )
        )
    elif label is AnomalyType.POLICY_LEGITIMATE_RARE_CASE:
        events = [
            event for event in events
            if event.event_type not in (
                AdministrativeEventType.PROMOTION,
                AdministrativeEventType.SANCTION,
            )
        ]
        events.extend(
            (
                AdministrativeEvent(
                    event_type=AdministrativeEventType.COMMENDATION,
                    event_date=_safe_date(record.hire_date.year + 1, record.hire_date.month, record.hire_date.day),
                    source_id=f"RARE-COM-{employee_id}",
                    category=3,
                    note="Rare legitimate case: high commendation credit",
                ),
                AdministrativeEvent(
                    event_type=AdministrativeEventType.COMMENDATION,
                    event_date=_safe_date(record.hire_date.year + 1, min(record.hire_date.month + 6, 12), record.hire_date.day),
                    source_id=f"RARE-COM-2-{employee_id}",
                    category=3,
                    note="Rare legitimate case: second valid commendation credit",
                ),
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=_safe_date(record.hire_date.year + 2, record.hire_date.month, record.hire_date.day),
                    source_id=f"RARE-PROM-{employee_id}",
                    level_before="L7",
                    level_after="L6",
                    note="Rare legitimate promotion explained by commendation credit",
                ),
            )
        )

    return replace(
        record,
        events=tuple(sorted(events, key=lambda event: (event.event_date, event.source_id))),
        anomaly_labels=(label,),
    )


# ---------------------------------------------------------------------------
# Latent-person-first duplicate generation
# ---------------------------------------------------------------------------

def _generate_latent_person(index: int, rng: Random) -> LatentPerson:
    """Generate a fictional base entity outside any dataset partition.

    The latent person is never inserted into the dataset directly.  All
    duplicate records are derived from it, guaranteeing partition containment
    by construction.
    """
    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index * 7 + 3) % len(LAST_NAMES)]  # offset to avoid FIRST_NAMES alignment
    full_name = f"{first_name} {last_name}"
    # Keep latent duplicate entities old enough for every generated employment
    # start. The ordinary generator currently starts histories no earlier than
    # 2016, so a 1995 upper bound leaves a conservative adult margin.
    dob = _safe_date(rng.randint(1970, 1995), rng.randint(1, 12), rng.randint(1, 28))
    national_id = f"LATENT-{index:06d}"
    email = f"{first_name.lower()}.{last_name.lower()}.latent{index}@synthetic.myhr"
    return LatentPerson(
        latent_person_id=f"LP-{index:06d}",
        full_name=full_name,
        date_of_birth=dob,
        national_id=national_id,
        email=email,
    )


def _canonical_latent_identity(
    person: LatentPerson,
    employee_id: str,
) -> EmployeeIdentity:
    """Return the uncorrupted canonical identity of a latent person.

    This is the identity assigned to the *source* record of a duplicate cluster,
    so the source genuinely IS the latent person. Each duplicate variant is a
    corrupted copy of these same facts (see ``_derive_duplicate_identity``). The
    source and its variants therefore form a real same-person cluster rather than
    merely sharing a ``latent_person_id`` tag.
    """
    return EmployeeIdentity(
        employee_id=employee_id,
        full_name=person.full_name,
        date_of_birth=person.date_of_birth,
        national_id=person.national_id,
        email=person.email,
    )


def _derive_duplicate_identity(
    person: LatentPerson,
    employee_id: str,
    variant: int,
) -> EmployeeIdentity:
    """Derive a mutated identity from a latent person for one dataset record.

    variant 0: first name only, transposed identifier
    variant 1: name typo, date-of-birth swap
    variant 2: exact name, no email, dropped-leading-zero identifier
    variant 3: first name only, date-of-birth swap, transposed identifier
    """
    full_name = (
        _shorten_name(person.full_name) if variant in {0, 3}
        else _name_typo(person.full_name) if variant == 1
        else person.full_name
    )
    date_of_birth = (
        _variant_birth_date(person.date_of_birth) if variant in {1, 3}
        else person.date_of_birth
    )
    national_id = (
        _transpose_identifier(person.national_id) if variant in {0, 3}
        else _drop_leading_zeroes(person.national_id)
    )
    email = (
        None if variant == 2
        else _variant_email(person.email)
    )
    return EmployeeIdentity(
        employee_id=employee_id,
        full_name=full_name,
        date_of_birth=date_of_birth,
        national_id=national_id,
        email=email,
    )


def _apply_latent_person_duplicate(
    record: WorkforceHistoryRecord,
    person: LatentPerson,
    source_employee_id: str,
    duplicate_employee_id: str,
    variant: int,
) -> WorkforceHistoryRecord:
    """Replace the identity of *record* with a latent-person-derived variant.

    The returned record carries both ``duplicate_of_employee_id`` (pointing to
    the source record in the same partition) and ``latent_person_id`` (the
    shared origin for the whole cluster).
    """
    identity = _derive_duplicate_identity(person, duplicate_employee_id, variant)
    return replace(
        record,
        identity=identity,
        anomaly_labels=(AnomalyType.DUPLICATE_RECORD,),
        duplicate_of_employee_id=source_employee_id,
        latent_person_id=person.latent_person_id,
    )


# ---------------------------------------------------------------------------
# Hard nonduplicate generation
# ---------------------------------------------------------------------------

def _apply_hard_nonduplicate(
    record: WorkforceHistoryRecord,
    kind: HardNonduplicateKind,
    anchor: WorkforceHistoryRecord,
) -> WorkforceHistoryRecord:
    """Return *record* with an identity modified to share surface features
    with *anchor* without being a true duplicate.

    The resulting record is a genuinely distinct person who will confuse
    naive similarity detectors.  It is NOT labelled DUPLICATE_RECORD and
    must NOT appear in _true_duplicate_pairs.
    """
    identity = record.identity
    if kind is HardNonduplicateKind.SIMILAR_NAME:
        # Same first name, different family name
        first = anchor.identity.full_name.split()[0]
        last = identity.full_name.split()[-1] if " " in identity.full_name else identity.full_name
        identity = replace(identity, full_name=f"{first} {last}")
    elif kind is HardNonduplicateKind.SHARED_BIRTHDAY:
        # Same date_of_birth, different name
        identity = replace(identity, date_of_birth=anchor.identity.date_of_birth)
    elif kind is HardNonduplicateKind.RELATIVE:
        # Same family name, different DOB and first name
        family = anchor.identity.full_name.split()[-1] if " " in anchor.identity.full_name else anchor.identity.full_name
        first = identity.full_name.split()[0] if " " in identity.full_name else identity.full_name
        identity = replace(identity, full_name=f"{first} {family}")
    elif kind is HardNonduplicateKind.NEAR_IDENTICAL_ID:
        # National ID one character transposed
        identity = replace(identity, national_id=_transpose_identifier(anchor.identity.national_id))
    return replace(
        record,
        identity=identity,
        anomaly_labels=(AnomalyType.CLEAN,),
        hard_nonduplicate_kind=kind,
        hard_nonduplicate_anchor_id=anchor.identity.employee_id,
        duplicate_of_employee_id=None,
        latent_person_id=None,
    )


def _split_counts(records: list[WorkforceHistoryRecord]) -> dict[str, int]:
    counts = Counter(record.split.value for record in records)
    return {split.value: counts.get(split.value, 0) for split in DatasetSplit}


def _label_counts(records: list[WorkforceHistoryRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for label in record.anomaly_labels:
            counts[label.value] += 1
    return {label.value: counts.get(label.value, 0) for label in AnomalyType}


def _record_to_dict(record: WorkforceHistoryRecord) -> dict[str, object]:
    return {
        "identity": _dataclass_with_dates(record.identity),
        "split": record.split.value,
        "employment_track": record.employment_track.value,
        "current_level": record.current_level,
        "department": record.department,
        "role": record.role,
        "hire_date": record.hire_date.isoformat(),
        "events": [_event_to_dict(event) for event in record.events],
        "anomaly_labels": [label.value for label in record.anomaly_labels],
        "duplicate_of_employee_id": record.duplicate_of_employee_id,
        "latent_person_id": record.latent_person_id,
        "hard_nonduplicate_kind": (
            record.hard_nonduplicate_kind.value if record.hard_nonduplicate_kind else None
        ),
        "hard_nonduplicate_anchor_id": record.hard_nonduplicate_anchor_id,
        "observation_date": (
            record.observation_date.isoformat() if record.observation_date else None
        ),
        "has_anomaly": record.has_anomaly,
    }


def _event_to_dict(event: AdministrativeEvent) -> dict[str, object]:
    data = _dataclass_with_dates(event)
    data["event_type"] = event.event_type.value
    return data


def _dataclass_with_dates(instance: object) -> dict[str, object]:
    data = asdict(instance)
    for key, value in list(data.items()):
        if isinstance(value, date):
            data[key] = value.isoformat()
        elif isinstance(value, Enum):
            data[key] = value.value
    return data


def _safe_date(year: int, month: int, day: int) -> date:
    return date(year, max(1, min(month, 12)), max(1, min(day, 28)))


def _shorten_name(full_name: str) -> str:
    return full_name.split()[0] if " " in full_name else full_name


def _drop_leading_zeroes(value: str | None) -> str | None:
    if value is None:
        return None
    prefix, _, suffix = value.partition("-")
    return f"{prefix}-{suffix.lstrip('0') or '0'}" if suffix else value.lstrip("0")


def _variant_email(value: str | None) -> str | None:
    if value is None or "@" not in value:
        return value
    local, _, domain = value.partition("@")
    local = local.replace(".", "")
    return f"{local}@{domain}"


def _name_typo(value: str) -> str:
    if len(value) < 4:
        return value
    return f"{value[:1]}{value[2:3]}{value[1:2]}{value[3:]}"


def _variant_birth_date(value: date) -> date:
    if value.day <= 12 and value.month != value.day:
        return _safe_date(value.year, value.day, value.month)
    return _safe_date(value.year, value.month, value.day + 1)


def _transpose_identifier(value: str | None) -> str | None:
    if value is None or len(value) < 2:
        return value
    characters = list(value)
    characters[-1], characters[-2] = characters[-2], characters[-1]
    return "".join(characters)
