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
from .deterministic_checks import ValidationFinding, ValidationSeverity, summarize_findings, validate_dataset, validate_record
from .features import (
    FeatureVector,
    extract_features,
    extract_policy_aware_features,
    extract_raw_features,
    supported_feature_sets,
)
from .experiment_runner import MethodEvaluation, evaluate_statistical_baseline
from .isolation_forest import (
    IsolationForestResult,
    IsolationForestUnavailableError,
    run_isolation_forest,
    sklearn_is_available,
)
from .statistical_baselines import (
    BaselineModel,
    fit_iqr_baseline,
    fit_z_score_baseline,
    predict_baseline,
)

__all__ = [
    "AdministrativeEvent",
    "AdministrativeEventType",
    "AnomalyDefinition",
    "AnomalyType",
    "BaselineModel",
    "BinaryClassificationMetrics",
    "DatasetSplit",
    "EmployeeIdentity",
    "EmploymentTrack",
    "ExperimentConfig",
    "FeatureVector",
    "IsolationForestResult",
    "IsolationForestUnavailableError",
    "MethodEvaluation",
    "PromotionPolicy",
    "SyntheticDataset",
    "SyntheticDatasetMetadata",
    "ValidationFinding",
    "ValidationSeverity",
    "WorkforceHistoryRecord",
    "anomaly_taxonomy",
    "confusion_counts",
    "evaluate_statistical_baseline",
    "extract_features",
    "extract_policy_aware_features",
    "extract_raw_features",
    "fit_iqr_baseline",
    "fit_z_score_baseline",
    "generate_synthetic_dataset",
    "predict_baseline",
    "run_isolation_forest",
    "serialize_dataset",
    "sklearn_is_available",
    "summarize_findings",
    "supported_feature_sets",
    "split_indices",
    "validate_dataset",
    "validate_record",
]
