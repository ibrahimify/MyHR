"""Label-free outlier scorers with a shared, train-fitted preprocessing contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler
from sklearn.svm import OneClassSVM

from .features import FeatureVector


SUPPORTED_METHODS = (
    "isolation_forest",
    "local_outlier_factor",
    "one_class_svm",
    "robust_z_score",
    "iqr",
)


@dataclass(frozen=True)
class OutlierScorerConfig:
    """Fixed method choice and explicitly declared unsupervised parameters."""

    method: str
    parameters: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OutlierScores:
    """Scores aligned to evaluation employees; larger always means more anomalous."""

    method: str
    employee_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    dropped_feature_names: tuple[str, ...]
    scores: tuple[float, ...]
    realized_parameters: Mapping[str, object]


def score_outliers(
    train_vectors: Sequence[FeatureVector],
    evaluation_vectors: Sequence[FeatureVector],
    feature_names: Sequence[str],
    config: OutlierScorerConfig,
    *,
    random_state: int,
) -> OutlierScores:
    """Fit without labels and score evaluation rows under a common contract."""

    if config.method not in SUPPORTED_METHODS:
        raise ValueError(f"Unsupported outlier method: {config.method}")
    if not train_vectors:
        raise ValueError("Outlier scoring requires at least one training record")
    if not evaluation_vectors:
        raise ValueError("Outlier scoring requires at least one evaluation record")

    requested_names = tuple(feature_names)
    if not requested_names or len(set(requested_names)) != len(requested_names):
        raise ValueError("Feature names must be non-empty and unique")

    train_matrix = _feature_matrix(train_vectors, requested_names)
    evaluation_matrix = _feature_matrix(evaluation_vectors, requested_names)
    retained_mask = np.ptp(train_matrix, axis=0) > np.finfo(float).eps
    if not retained_mask.any():
        raise ValueError("All requested training features are constant")

    retained_names = tuple(name for name, keep in zip(requested_names, retained_mask) if keep)
    dropped_names = tuple(name for name, keep in zip(requested_names, retained_mask) if not keep)
    scaler = RobustScaler()
    scaled_train = scaler.fit_transform(train_matrix[:, retained_mask])
    scaled_evaluation = scaler.transform(evaluation_matrix[:, retained_mask])

    scores, method_parameters = _score_scaled(
        scaled_train,
        scaled_evaluation,
        config,
        random_state=random_state,
    )
    if not np.isfinite(scores).all():
        raise ValueError(f"{config.method} produced a non-finite anomaly score")

    realized_parameters: dict[str, object] = {
        "preprocessing": "train_fitted_robust_scaler",
        "score_direction": "larger_is_more_anomalous",
        "random_state": random_state,
        "training_records": len(train_vectors),
        "evaluation_records": len(evaluation_vectors),
        **method_parameters,
    }
    return OutlierScores(
        method=config.method,
        employee_ids=tuple(vector.employee_id for vector in evaluation_vectors),
        feature_names=retained_names,
        dropped_feature_names=dropped_names,
        scores=tuple(float(score) for score in scores),
        realized_parameters=realized_parameters,
    )


def _feature_matrix(vectors: Sequence[FeatureVector], feature_names: tuple[str, ...]) -> np.ndarray:
    rows: list[list[float]] = []
    for vector in vectors:
        missing = tuple(name for name in feature_names if name not in vector.values)
        if missing:
            raise ValueError(f"Feature vector {vector.employee_id} is missing: {', '.join(missing)}")
        rows.append([float(vector.values[name]) for name in feature_names])
    matrix = np.asarray(rows, dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError("Outlier scoring requires finite feature values")
    return matrix


def _score_scaled(
    train: np.ndarray,
    evaluation: np.ndarray,
    config: OutlierScorerConfig,
    *,
    random_state: int,
) -> tuple[np.ndarray, dict[str, object]]:
    parameters = dict(config.parameters)
    if config.method == "isolation_forest":
        _reject_unknown(parameters, {"n_estimators", "max_samples"})
        n_estimators = int(parameters.get("n_estimators", 100))
        max_samples = parameters.get("max_samples", "auto")
        model = IsolationForest(
            contamination="auto",
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=1,
        )
        model.fit(train)
        return -model.score_samples(evaluation), {
            "n_estimators": n_estimators,
            "max_samples": max_samples,
            "contamination": "auto",
        }

    if config.method == "local_outlier_factor":
        _reject_unknown(parameters, {"n_neighbors"})
        if len(train) < 3:
            raise ValueError("Local Outlier Factor requires at least three training records")
        requested_neighbors = int(parameters.get("n_neighbors", 20))
        n_neighbors = min(requested_neighbors, len(train) - 1)
        model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination="auto",
            novelty=True,
            n_jobs=1,
        )
        model.fit(train)
        return -model.score_samples(evaluation), {
            "n_neighbors": n_neighbors,
            "requested_n_neighbors": requested_neighbors,
            "contamination": "auto",
            "novelty": True,
        }

    if config.method == "one_class_svm":
        _reject_unknown(parameters, {"nu", "gamma", "max_iter"})
        nu = float(parameters.get("nu", 0.1))
        gamma = parameters.get("gamma", "scale")
        max_iter = int(parameters.get("max_iter", 100_000))
        model = OneClassSVM(kernel="rbf", nu=nu, gamma=gamma, max_iter=max_iter)
        model.fit(train)
        return -model.score_samples(evaluation), {
            "kernel": "rbf",
            "nu": nu,
            "gamma": gamma,
            "max_iter": max_iter,
            "fit_status": int(model.fit_status_),
            "n_iter": int(model.n_iter_),
        }

    if config.method == "robust_z_score":
        _reject_unknown(parameters, set())
        center = np.median(train, axis=0)
        mad_scale = 1.4826 * np.median(np.abs(train - center), axis=0)
        fallback = np.std(train, axis=0, ddof=0)
        scale = np.where(mad_scale > np.finfo(float).eps, mad_scale, fallback)
        scale = np.where(scale > np.finfo(float).eps, scale, 1.0)
        scores = np.max(np.abs((evaluation - center) / scale), axis=1)
        return scores, {"aggregation": "maximum_absolute_robust_z"}

    _reject_unknown(parameters, set())
    q1 = np.quantile(train, 0.25, axis=0)
    q3 = np.quantile(train, 0.75, axis=0)
    spread = q3 - q1
    fallback = np.std(train, axis=0, ddof=0)
    scale = np.where(spread > np.finfo(float).eps, spread, fallback)
    scale = np.where(scale > np.finfo(float).eps, scale, 1.0)
    lower_excess = (q1 - evaluation) / scale
    upper_excess = (evaluation - q3) / scale
    scores = np.max(np.maximum(lower_excess, upper_excess), axis=1)
    return scores, {"aggregation": "maximum_normalized_iqr_exceedance"}


def _reject_unknown(parameters: Mapping[str, object], supported: set[str]) -> None:
    unknown = sorted(set(parameters) - supported)
    if unknown:
        raise ValueError(f"Unsupported parameters: {', '.join(unknown)}")
