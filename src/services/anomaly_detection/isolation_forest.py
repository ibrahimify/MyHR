"""Isolation Forest experiment boundary."""

from dataclasses import dataclass

from .features import FeatureVector

MODEL_NAME = "isolation_forest"


class IsolationForestUnavailableError(RuntimeError):
    """Raised when scikit-learn is not installed for model experiments."""


@dataclass(frozen=True)
class IsolationForestResult:
    method: str
    feature_names: tuple[str, ...]
    predictions: tuple[bool, ...]
    scores: tuple[float, ...]


@dataclass(frozen=True)
class IsolationForestScores:
    """Continuous scores where larger values indicate greater abnormality."""

    method: str
    feature_names: tuple[str, ...]
    scores: tuple[float, ...]


def sklearn_is_available() -> bool:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        return False
    return True


def run_isolation_forest(
    train_vectors: tuple[FeatureVector, ...],
    test_vectors: tuple[FeatureVector, ...],
    feature_names: tuple[str, ...],
    contamination: float,
    random_state: int,
) -> IsolationForestResult:
    """Fit Isolation Forest and return outlier predictions for test vectors.

    The dependency is intentionally optional at this stage. This lets the
    research pipeline document the model boundary before deciding whether the
    application package should include scikit-learn.
    """

    if not sklearn_is_available():
        raise IsolationForestUnavailableError(
            "scikit-learn is required to run Isolation Forest experiments"
        )
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5")

    from sklearn.ensemble import IsolationForest

    train_matrix = _matrix(train_vectors, feature_names)
    test_matrix = _matrix(test_vectors, feature_names)
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(train_matrix)
    raw_predictions = model.predict(test_matrix)
    scores = model.decision_function(test_matrix)
    return IsolationForestResult(
        method=MODEL_NAME,
        feature_names=feature_names,
        predictions=tuple(prediction == -1 for prediction in raw_predictions),
        scores=tuple(float(score) for score in scores),
    )


def score_isolation_forest(
    train_vectors: tuple[FeatureVector, ...],
    evaluation_vectors: tuple[FeatureVector, ...],
    feature_names: tuple[str, ...],
    random_state: int,
) -> IsolationForestScores:
    """Fit without a label-derived contamination rate and return ranking scores."""

    if not sklearn_is_available():
        raise IsolationForestUnavailableError(
            "scikit-learn is required to run Isolation Forest experiments"
        )
    from sklearn.ensemble import IsolationForest

    train_matrix = _matrix(train_vectors, feature_names)
    evaluation_matrix = _matrix(evaluation_vectors, feature_names)
    model = IsolationForest(contamination="auto", random_state=random_state)
    model.fit(train_matrix)
    scores = tuple(float(-score) for score in model.score_samples(evaluation_matrix))
    return IsolationForestScores(
        method=MODEL_NAME,
        feature_names=feature_names,
        scores=scores,
    )


def _matrix(feature_vectors: tuple[FeatureVector, ...], feature_names: tuple[str, ...]) -> list[list[float]]:
    if not feature_vectors:
        raise ValueError("feature_vectors must not be empty")
    if not feature_names:
        raise ValueError("feature_names must not be empty")
    return [
        [vector.values[name] for name in feature_names]
        for vector in feature_vectors
    ]
