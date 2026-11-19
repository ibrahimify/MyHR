from dataclasses import fields

import pytest

from src.services.anomaly_detection.features import FeatureVector
from src.services.anomaly_detection.outlier_scoring import (
    OutlierScorerConfig,
    score_outliers,
)
from src.services.anomaly_detection.protocol_evaluation import (
    evaluate_residual_model_comparison,
)
from src.services.anomaly_detection.scenario_generation import (
    generate_scenario_dataset,
    scenario_matrix,
)


FEATURE_NAMES = ("stable", "signal", "constant")


def _vectors(rows: tuple[tuple[float, float, float], ...], prefix: str) -> tuple[FeatureVector, ...]:
    return tuple(
        FeatureVector(
            employee_id=f"{prefix}-{index}",
            feature_set="test",
            values=dict(zip(FEATURE_NAMES, row)),
        )
        for index, row in enumerate(rows)
    )


TRAIN = _vectors(
    (
        (0.0, 0.1, 7.0),
        (0.2, -0.1, 7.0),
        (-0.1, 0.0, 7.0),
        (0.1, 0.2, 7.0),
        (-0.2, -0.2, 7.0),
        (0.05, 0.05, 7.0),
    ),
    "train",
)
EVALUATION = _vectors(
    (
        (0.0, 0.0, 999.0),
        (0.1, -0.1, -999.0),
        (8.0, 9.0, 7.0),
    ),
    "evaluation",
)


@pytest.mark.parametrize(
    "method",
    ("isolation_forest", "local_outlier_factor", "one_class_svm", "robust_z_score", "iqr"),
)
def test_all_scorers_return_finite_scores_with_common_direction(method: str) -> None:
    result = score_outliers(
        TRAIN,
        EVALUATION,
        FEATURE_NAMES,
        OutlierScorerConfig(method=method),
        random_state=41,
    )

    assert result.employee_ids == tuple(vector.employee_id for vector in EVALUATION)
    assert len(result.scores) == len(EVALUATION)
    assert all(score == score and abs(score) != float("inf") for score in result.scores)
    assert result.scores[-1] > min(result.scores[:-1])
    assert result.feature_names == ("stable", "signal")
    assert result.dropped_feature_names == ("constant",)
    assert result.realized_parameters["score_direction"] == "larger_is_more_anomalous"
    assert result.realized_parameters["preprocessing"] == "train_fitted_robust_scaler"


def test_scorer_interface_cannot_accept_labels() -> None:
    config_fields = {field.name for field in fields(OutlierScorerConfig)}

    assert "labels" not in config_fields
    assert "review_budget" not in config_fields
    assert "anomaly_prevalence" not in config_fields


def test_isolation_forest_is_reproducible_for_fixed_seed() -> None:
    config = OutlierScorerConfig(method="isolation_forest", parameters={"n_estimators": 32})

    first = score_outliers(TRAIN, EVALUATION, FEATURE_NAMES, config, random_state=17)
    second = score_outliers(TRAIN, EVALUATION, FEATURE_NAMES, config, random_state=17)

    assert first.scores == second.scores
    assert first.realized_parameters == second.realized_parameters


def test_nonfinite_feature_value_is_rejected() -> None:
    invalid = _vectors(((0.0, float("nan"), 7.0),), "invalid")

    with pytest.raises(ValueError, match="finite"):
        score_outliers(
            TRAIN,
            invalid,
            FEATURE_NAMES,
            OutlierScorerConfig(method="iqr"),
            random_state=1,
        )


def test_all_constant_training_features_are_rejected() -> None:
    constant = _vectors(((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)), "constant")

    with pytest.raises(ValueError, match="constant"):
        score_outliers(
            constant,
            EVALUATION,
            FEATURE_NAMES,
            OutlierScorerConfig(method="robust_z_score"),
            random_state=1,
        )


def test_local_outlier_factor_rejects_too_few_training_records() -> None:
    with pytest.raises(ValueError, match="at least three"):
        score_outliers(
            TRAIN[:2],
            EVALUATION,
            FEATURE_NAMES,
            OutlierScorerConfig(method="local_outlier_factor"),
            random_state=1,
        )


def test_unknown_parameter_is_rejected_instead_of_silently_ignored() -> None:
    with pytest.raises(ValueError, match="Unsupported parameters"):
        score_outliers(
            TRAIN,
            EVALUATION,
            FEATURE_NAMES,
            OutlierScorerConfig(method="one_class_svm", parameters={"labels": (0, 1)}),
            random_state=1,
        )


def test_residual_model_comparison_uses_equal_population_and_review_capacity() -> None:
    scenario = generate_scenario_dataset(
        scenario_matrix("development", count=1, employee_count=120)[0]
    )

    result = evaluate_residual_model_comparison(scenario)

    methods = {
        "isolation_forest",
        "local_outlier_factor",
        "one_class_svm",
        "robust_z_score",
        "iqr",
    }
    representations = {
        "raw_matched",
        "raw_rate_control",
        "policy_matched",
        "wrong_policy_control",
        "shuffled_policy_control",
    }
    assert {row["method"] for row in result.metric_rows} == methods
    assert {row["representation"] for row in result.metric_rows} == representations
    assert len(result.metric_rows) == len(methods) * len(representations)
    assert len({row["evaluation_count"] for row in result.metric_rows}) == 1
    assert len({row["alert_count"] for row in result.metric_rows}) == 1
    assert all(row["operating_point"] == "fixed_review_budget" for row in result.metric_rows)
    assert all(row["comparison_status"] == "exploratory_development" for row in result.metric_rows)

    expected_ids = {
        row["employee_id"]
        for row in result.prediction_rows
        if row["method"] == "isolation_forest" and row["representation"] == "raw_matched"
    }
    for method in methods:
        for representation in representations:
            observed_ids = {
                row["employee_id"]
                for row in result.prediction_rows
                if row["method"] == method and row["representation"] == representation
            }
            assert observed_ids == expected_ids


def test_model_comparison_does_not_modify_original_protocol_evaluator() -> None:
    scenario = generate_scenario_dataset(
        scenario_matrix("development", count=1, employee_count=120)[0]
    )

    result = evaluate_residual_model_comparison(
        scenario,
        methods=(OutlierScorerConfig("robust_z_score"),),
        representations=("raw_matched",),
    )

    assert len(result.metric_rows) == 1
    assert result.metric_rows[0]["method"] == "robust_z_score"
    assert result.metric_rows[0]["representation"] == "raw_matched"
