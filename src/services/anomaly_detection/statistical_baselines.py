"""Simple statistical baselines for anomaly-detection experiments."""

from dataclasses import dataclass
from statistics import mean, pstdev

from .features import FeatureVector

BASELINE_METHODS = (
    "z_score",
    "iqr",
)


@dataclass(frozen=True)
class BaselineModel:
    method: str
    feature_names: tuple[str, ...]
    center: dict[str, float]
    spread: dict[str, float]
    lower_bounds: dict[str, float]
    upper_bounds: dict[str, float]


def fit_z_score_baseline(
    feature_vectors: tuple[FeatureVector, ...],
    feature_names: tuple[str, ...],
    threshold: float = 3.0,
) -> BaselineModel:
    """Fit a z-score baseline from training feature vectors."""

    if threshold <= 0:
        raise ValueError("threshold must be positive")
    columns = _columns(feature_vectors, feature_names)
    center = {name: mean(values) for name, values in columns.items()}
    spread = {name: pstdev(values) or 1.0 for name, values in columns.items()}
    lower_bounds = {name: center[name] - threshold * spread[name] for name in feature_names}
    upper_bounds = {name: center[name] + threshold * spread[name] for name in feature_names}
    return BaselineModel(
        method="z_score",
        feature_names=feature_names,
        center=center,
        spread=spread,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
    )


def fit_iqr_baseline(
    feature_vectors: tuple[FeatureVector, ...],
    feature_names: tuple[str, ...],
    multiplier: float = 1.5,
) -> BaselineModel:
    """Fit an interquartile-range baseline from training feature vectors."""

    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    columns = _columns(feature_vectors, feature_names)
    lower_bounds: dict[str, float] = {}
    upper_bounds: dict[str, float] = {}
    center: dict[str, float] = {}
    spread: dict[str, float] = {}

    for name, values in columns.items():
        sorted_values = sorted(values)
        q1 = _percentile(sorted_values, 0.25)
        q3 = _percentile(sorted_values, 0.75)
        iqr = q3 - q1
        center[name] = _percentile(sorted_values, 0.50)
        spread[name] = iqr
        lower_bounds[name] = q1 - multiplier * iqr
        upper_bounds[name] = q3 + multiplier * iqr

    return BaselineModel(
        method="iqr",
        feature_names=feature_names,
        center=center,
        spread=spread,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
    )


def predict_baseline(model: BaselineModel, feature_vectors: tuple[FeatureVector, ...]) -> list[bool]:
    """Return True for records outside any learned feature boundary."""

    predictions: list[bool] = []
    for vector in feature_vectors:
        is_outlier = any(
            vector.values[name] < model.lower_bounds[name]
            or vector.values[name] > model.upper_bounds[name]
            for name in model.feature_names
        )
        predictions.append(is_outlier)
    return predictions


def _columns(feature_vectors: tuple[FeatureVector, ...], feature_names: tuple[str, ...]) -> dict[str, list[float]]:
    if not feature_vectors:
        raise ValueError("feature_vectors must not be empty")
    if not feature_names:
        raise ValueError("feature_names must not be empty")
    return {
        name: [vector.values[name] for vector in feature_vectors]
        for name in feature_names
    }


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        raise ValueError("sorted_values must not be empty")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
