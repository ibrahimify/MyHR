"""Research utilities for policy-aware anomaly detection.

This package is intentionally separate from the production UI. It will host the
TDK research pipeline for synthetic data, policy-aware features, deterministic
checks, baselines, model experiments, duplicate detection, and metrics.
"""

from .metrics import BinaryClassificationMetrics, confusion_counts
from .policy_model import PromotionPolicy
from .synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyDefinition,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    ExperimentConfig,
    WorkforceHistoryRecord,
    anomaly_taxonomy,
    split_indices,
)

__all__ = [
    "AdministrativeEvent",
    "AdministrativeEventType",
    "AnomalyDefinition",
    "AnomalyType",
    "BinaryClassificationMetrics",
    "DatasetSplit",
    "EmployeeIdentity",
    "EmploymentTrack",
    "ExperimentConfig",
    "PromotionPolicy",
    "WorkforceHistoryRecord",
    "anomaly_taxonomy",
    "confusion_counts",
    "split_indices",
]
