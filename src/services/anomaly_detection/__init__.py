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
    SyntheticDataset,
    SyntheticDatasetMetadata,
    WorkforceHistoryRecord,
    anomaly_taxonomy,
    generate_synthetic_dataset,
    serialize_dataset,
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
    "SyntheticDataset",
    "SyntheticDatasetMetadata",
    "WorkforceHistoryRecord",
    "anomaly_taxonomy",
    "confusion_counts",
    "generate_synthetic_dataset",
    "serialize_dataset",
    "split_indices",
]
