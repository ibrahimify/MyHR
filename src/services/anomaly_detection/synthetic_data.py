"""Synthetic workforce-history contracts and generator for experiments."""

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
from enum import Enum
from hashlib import sha256
from random import Random
from typing import Callable


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
    note: str = ""


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

    @property
    def has_anomaly(self) -> bool:
        non_anomalous_labels = {AnomalyType.CLEAN, AnomalyType.POLICY_LEGITIMATE_RARE_CASE}
        return any(label not in non_anomalous_labels for label in self.anomaly_labels)


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
    """Generate deterministic synthetic histories with documented labels."""

    config.validate()
    rng = seeded_random(config)
    split_by_index = _split_by_index(config.employee_count, config)
    label_plan = _label_plan(config, rng, split_by_index)

    records: list[WorkforceHistoryRecord] = []
    for index in range(config.employee_count):
        record = _base_record(index, split_by_index[index], rng)
        label = label_plan[index]
        if label is not AnomalyType.CLEAN:
            record = _apply_label(record, label, records, rng)
        records.append(record)

    metadata = SyntheticDatasetMetadata(
        schema_version="tdk-synthetic-v1",
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
    indices = list(range(config.employee_count))
    rng.shuffle(indices)

    anomaly_count = int(config.employee_count * config.anomaly_rate)
    rare_count = int(config.employee_count * config.rare_legitimate_rate)
    true_anomalies = (
        AnomalyType.INCONSISTENT_DATES,
        AnomalyType.FREQUENT_PROMOTIONS,
        AnomalyType.EXCESSIVE_SANCTIONS,
        AnomalyType.DUPLICATE_RECORD,
        AnomalyType.UNUSUAL_ADMIN_INTERVAL,
    )

    for offset, index in enumerate(indices[:anomaly_count]):
        plan[index] = true_anomalies[offset % len(true_anomalies)]
    if plan.get(0) is AnomalyType.DUPLICATE_RECORD and config.employee_count > 1:
        swap_index = next(index for index in range(1, config.employee_count) if plan[index] is not AnomalyType.DUPLICATE_RECORD)
        plan[0], plan[swap_index] = plan[swap_index], plan[0]
    rare_start = anomaly_count
    for index in indices[rare_start:rare_start + rare_count]:
        plan[index] = AnomalyType.POLICY_LEGITIMATE_RARE_CASE
    if anomaly_count >= len(DatasetSplit):
        _spread_label_group_across_splits(plan, split_by_index, _is_true_anomaly)
    if rare_count >= len(DatasetSplit):
        _spread_label_group_across_splits(
            plan,
            split_by_index,
            lambda label: label is AnomalyType.POLICY_LEGITIMATE_RARE_CASE,
        )
    return plan


def _spread_label_group_across_splits(
    plan: dict[int, AnomalyType],
    split_by_index: dict[int, DatasetSplit],
    predicate: Callable[[AnomalyType], bool],
) -> None:
    for split in DatasetSplit:
        split_indices_for_label = [
            index for index, label in plan.items()
            if split_by_index[index] is split and predicate(label)
        ]
        if split_indices_for_label:
            continue

        target_indices = [
            index for index, label in plan.items()
            if split_by_index[index] is split and label is AnomalyType.CLEAN
        ]
        source_indices = [
            index for index, label in plan.items()
            if predicate(label)
            and _count_labels_in_split(plan, split_by_index, split_by_index[index], predicate) > 1
        ]
        if target_indices and source_indices:
            target_index = min(target_indices)
            source_index = min(source_indices)
            plan[target_index], plan[source_index] = plan[source_index], plan[target_index]


def _is_true_anomaly(label: AnomalyType) -> bool:
    return label not in (AnomalyType.CLEAN, AnomalyType.POLICY_LEGITIMATE_RARE_CASE)


def _count_labels_in_split(
    plan: dict[int, AnomalyType],
    split_by_index: dict[int, DatasetSplit],
    split: DatasetSplit,
    predicate: Callable[[AnomalyType], bool],
) -> int:
    return sum(
        1 for index, label in plan.items()
        if split_by_index[index] is split and predicate(label)
    )


def _base_record(index: int, split: DatasetSplit, rng: Random) -> WorkforceHistoryRecord:
    employee_number = index + 1
    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    full_name = f"{first_name} {last_name}"
    track = EmploymentTrack.PROMOTION if index % 5 != 0 else EmploymentTrack.OTHER
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
        events.append(
            AdministrativeEvent(
                event_type=AdministrativeEventType.SANCTION,
                event_date=_safe_date(max(hire_year + 1, 2022), rng.randint(1, 12), rng.randint(1, 28)),
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
        source = rng.choice(existing_records)
        identity = EmployeeIdentity(
            employee_id=employee_id,
            full_name=_shorten_name(source.identity.full_name),
            date_of_birth=source.identity.date_of_birth,
            national_id=_drop_leading_zeroes(source.identity.national_id),
            email=source.identity.email,
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
            if event.event_type is not AdministrativeEventType.PROMOTION
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
