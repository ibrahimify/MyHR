"""Deterministic helpers for future synthetic workforce-history generation."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from random import Random


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
        "train": indices[:train_end],
        "validation": indices[train_end:validation_end],
        "test": indices[validation_end:],
    }
