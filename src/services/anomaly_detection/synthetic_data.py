"""Synthetic workforce-history contracts for reproducible experiments."""

from dataclasses import asdict, dataclass
from datetime import date
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
