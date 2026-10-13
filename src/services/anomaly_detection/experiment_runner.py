"""Entry points for reproducible research experiments."""

from dataclasses import dataclass

from .features import POLICY_AWARE_FEATURE_SET, RAW_FEATURE_SET, FeatureVector, extract_features
from .metrics import BinaryClassificationMetrics, confusion_counts
from .statistical_baselines import BaselineModel, fit_iqr_baseline, fit_z_score_baseline, predict_baseline
from .synthetic_data import AnomalyType, DatasetSplit, ExperimentConfig, SyntheticDataset, WorkforceHistoryRecord


def describe_experiment(config: ExperimentConfig) -> dict[str, int | float | str]:
    """Return metadata for an experiment run without executing models."""

    config.validate()
    return {
        "run_id": config.run_id(),
        "seed": config.seed,
        "employee_count": config.employee_count,
        "anomaly_rate": config.anomaly_rate,
        "rare_legitimate_rate": config.rare_legitimate_rate,
    }


@dataclass(frozen=True)
class MethodEvaluation:
    method: str
    feature_set: str
    feature_names: tuple[str, ...]
    metrics: BinaryClassificationMetrics
    rare_legitimate_false_positives: int
    predicted_positive_count: int


DEFAULT_BASELINE_FEATURES = (
    "promotion_count",
    "sanction_count",
    "commendation_count",
    "min_promotion_interval_months",
    "min_salary_increment_interval_days",
)

DEFAULT_POLICY_AWARE_FEATURES = (
    "promotion_count",
    "sanction_count",
    "min_salary_increment_interval_days",
    "policy_service_deficit_months",
    "policy_service_deficit_ratio",
    "policy_unexplained_short_promotion",
)


def evaluate_statistical_baseline(
    dataset: SyntheticDataset,
    feature_set: str,
    method: str,
    feature_names: tuple[str, ...] | None = None,
) -> MethodEvaluation:
    """Train a statistical baseline on train records and evaluate test records."""

    if feature_set not in (RAW_FEATURE_SET, POLICY_AWARE_FEATURE_SET):
        raise ValueError(f"Unsupported feature set: {feature_set}")
    feature_names = feature_names or (
        DEFAULT_POLICY_AWARE_FEATURES if feature_set == POLICY_AWARE_FEATURE_SET else DEFAULT_BASELINE_FEATURES
    )
    train_records = _records_for_split(dataset, DatasetSplit.TRAIN)
    test_records = _records_for_split(dataset, DatasetSplit.TEST)
    train_vectors = tuple(extract_features(record, feature_set) for record in train_records)
    test_vectors = tuple(extract_features(record, feature_set) for record in test_records)

    model = _fit_baseline(method, train_vectors, feature_names)
    predictions = predict_baseline(model, test_vectors)
    y_true = [record.has_anomaly for record in test_records]
    metrics = confusion_counts(y_true, predictions)
    return MethodEvaluation(
        method=method,
        feature_set=feature_set,
        feature_names=feature_names,
        metrics=metrics,
        rare_legitimate_false_positives=_rare_legitimate_false_positives(test_records, predictions),
        predicted_positive_count=sum(predictions),
    )


def _fit_baseline(
    method: str,
    train_vectors: tuple[FeatureVector, ...],
    feature_names: tuple[str, ...],
) -> BaselineModel:
    if method == "z_score":
        return fit_z_score_baseline(train_vectors, feature_names)
    if method == "iqr":
        return fit_iqr_baseline(train_vectors, feature_names)
    raise ValueError(f"Unsupported baseline method: {method}")


def _records_for_split(dataset: SyntheticDataset, split: DatasetSplit) -> tuple[WorkforceHistoryRecord, ...]:
    return tuple(record for record in dataset.records if record.split is split)


def _rare_legitimate_false_positives(
    records: tuple[WorkforceHistoryRecord, ...],
    predictions: list[bool],
) -> int:
    return sum(
        1
        for record, predicted in zip(records, predictions)
        if predicted and AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
    )
