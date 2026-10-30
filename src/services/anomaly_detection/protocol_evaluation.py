"""Validation-driven evaluation for the TDK v2 research protocol."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil, inf
from time import perf_counter
from .deterministic_checks import (
    validate_invariant_record,
    validate_record,
    validate_record_with_policy,
)
from .features import FeatureVector, extract_policy_aware_features, extract_raw_features
from .isolation_forest import score_isolation_forest
from .metrics import BinaryClassificationMetrics, confusion_counts
from .policy_model import PromotionPolicy
from .scenario_generation import ScenarioDataset, policy_profiles
from .statistical_baselines import fit_iqr_baseline, fit_z_score_baseline, score_baseline
from .synthetic_data import AnomalyType, DatasetSplit, WorkforceHistoryRecord


COMMON_CORE_FEATURES = (
    "event_count",
    "promotion_count",
    "sanction_count",
    "salary_increment_count",
    "performance_review_count",
    "min_salary_increment_interval_days",
)
RAW_MATCHED_FEATURES = COMMON_CORE_FEATURES + (
    "min_promotion_interval_months",
    "commendation_count",
    "months_since_hire",
)
POLICY_MATCHED_FEATURES = COMMON_CORE_FEATURES + (
    "policy_service_deficit_months",
    "policy_service_deficit_ratio",
    "policy_unexplained_short_promotion",
)


@dataclass(frozen=True)
class FeatureRepresentation:
    name: str
    feature_names: tuple[str, ...]
    policy_mode: str


@dataclass(frozen=True)
class ThresholdSelection:
    mode: str
    threshold: float
    validation_metrics: BinaryClassificationMetrics
    validation_alert_count: int
    constraint_satisfied: bool = True


@dataclass(frozen=True)
class ScenarioEvaluation:
    metric_rows: tuple[dict[str, object], ...]
    prediction_rows: tuple[dict[str, object], ...]


def feature_representations() -> tuple[FeatureRepresentation, ...]:
    """Return the predeclared representations and negative controls."""

    return (
        FeatureRepresentation("raw_matched", RAW_MATCHED_FEATURES, "raw"),
        FeatureRepresentation("policy_matched", POLICY_MATCHED_FEATURES, "true"),
        FeatureRepresentation(
            "raw_without_commendation",
            tuple(name for name in RAW_MATCHED_FEATURES if name != "commendation_count"),
            "raw",
        ),
        FeatureRepresentation(
            "raw_interval_ablation",
            COMMON_CORE_FEATURES + ("min_promotion_interval_months",),
            "raw",
        ),
        FeatureRepresentation(
            "policy_deficit_months_ablation",
            COMMON_CORE_FEATURES + ("policy_service_deficit_months",),
            "true",
        ),
        FeatureRepresentation(
            "policy_deficit_ratio_ablation",
            COMMON_CORE_FEATURES + ("policy_service_deficit_ratio",),
            "true",
        ),
        FeatureRepresentation(
            "policy_unexplained_ablation",
            COMMON_CORE_FEATURES + ("policy_unexplained_short_promotion",),
            "true",
        ),
        FeatureRepresentation("wrong_policy_control", POLICY_MATCHED_FEATURES, "wrong"),
        FeatureRepresentation("shuffled_policy_control", POLICY_MATCHED_FEATURES, "shuffled"),
    )


def evaluate_scenario(
    scenario: ScenarioDataset,
    review_budget: float = 0.10,
    target_validation_fpr: float = 0.05,
) -> ScenarioEvaluation:
    """Fit on train, choose thresholds on validation, and report test results."""

    if not 0 < review_budget < 0.5:
        raise ValueError("review_budget must be between 0 and 0.5")
    if not 0 <= target_validation_fpr < 0.5:
        raise ValueError("target_validation_fpr must be between 0 and 0.5")
    train = _records(scenario, DatasetSplit.TRAIN)
    validation = _records(scenario, DatasetSplit.VALIDATION)
    test = _records(scenario, DatasetSplit.TEST)
    validation_truth = [record.has_progression_anomaly for record in validation]
    test_truth = [record.has_progression_anomaly for record in test]
    policy_rule_started = perf_counter()
    policy_rule_train_scores = tuple(
        float(len(validate_record_with_policy(
            record, scenario.policy, scenario.policy_epochs
        )))
        for record in train
    )
    policy_rule_validation_scores = tuple(
        float(len(validate_record_with_policy(
            record, scenario.policy, scenario.policy_epochs
        )))
        for record in validation
    )
    policy_rule_scores = tuple(
        float(len(validate_record_with_policy(
            record, scenario.policy, scenario.policy_epochs
        )))
        for record in test
    )
    policy_rule_runtime_ms = (perf_counter() - policy_rule_started) * 1000
    invariant_rule_started = perf_counter()
    invariant_rule_train_scores = tuple(
        float(len(validate_invariant_record(record))) for record in train
    )
    invariant_rule_validation_scores = tuple(
        float(len(validate_invariant_record(record))) for record in validation
    )
    invariant_rule_scores = tuple(
        float(len(validate_invariant_record(record))) for record in test
    )
    invariant_rule_runtime_ms = (perf_counter() - invariant_rule_started) * 1000
    metric_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    iforest_scores: dict[str, tuple[tuple[float, ...], tuple[float, ...], float]] = {}

    for representation in feature_representations():
        train_vectors = _vectors(train, representation, scenario)
        validation_vectors = _vectors(validation, representation, scenario)
        test_vectors = _vectors(test, representation, scenario)
        started = perf_counter()
        combined_scores = score_isolation_forest(
            train_vectors,
            validation_vectors + test_vectors,
            representation.feature_names,
            scenario.config.model_seed,
        ).scores
        validation_scores = combined_scores[:len(validation_vectors)]
        test_scores = combined_scores[len(validation_vectors):]
        runtime_ms = (perf_counter() - started) * 1000
        if representation.name in {"raw_matched", "policy_matched"}:
            iforest_scores[representation.name] = (validation_scores, test_scores, runtime_ms)
        selections = (
            _select_threshold(validation_truth, validation_scores, "validation_f1"),
            _select_threshold(
                validation_truth,
                validation_scores,
                "validation_target_fpr",
                target_fpr=target_validation_fpr,
            ),
        )
        fixed_predictions = _top_budget_predictions(
            test_scores,
            review_budget,
            tuple(record.identity.employee_id for record in test),
        )
        row, records = _evaluation_output(
            scenario,
            test,
            test_truth,
            test_scores,
            fixed_predictions,
            method="isolation_forest",
            representation=representation.name,
            operating_point="fixed_review_budget",
            threshold=None,
            validation_selection=None,
            runtime_ms=runtime_ms,
        )
        row.update(_feature_variation_columns(test_vectors, representation))
        metric_rows.append(row)
        prediction_rows.extend(records)
        for selection in selections:
            predictions = [score >= selection.threshold for score in test_scores]
            row, records = _evaluation_output(
                scenario,
                test,
                test_truth,
                test_scores,
                predictions,
                method="isolation_forest",
                representation=representation.name,
                operating_point=selection.mode,
                threshold=selection.threshold,
                validation_selection=selection,
                runtime_ms=runtime_ms,
            )
            row.update(_feature_variation_columns(test_vectors, representation))
            metric_rows.append(row)
            prediction_rows.extend(records)

    for method, fit in (("iqr", fit_iqr_baseline), ("z_score", fit_z_score_baseline)):
        for representation in feature_representations()[:2]:
            train_vectors = _vectors(train, representation, scenario)
            validation_vectors = _vectors(validation, representation, scenario)
            test_vectors = _vectors(test, representation, scenario)
            started = perf_counter()
            model = fit(train_vectors, representation.feature_names)
            validation_scores = score_baseline(model, validation_vectors)
            test_scores = score_baseline(model, test_vectors)
            runtime_ms = (perf_counter() - started) * 1000
            for operating_point, selection in (
                ("fixed_review_budget", None),
                ("validation_f1", _select_threshold(validation_truth, validation_scores, "validation_f1")),
                (
                    "validation_target_fpr",
                    _select_threshold(
                        validation_truth,
                        validation_scores,
                        "validation_target_fpr",
                        target_fpr=target_validation_fpr,
                    ),
                ),
            ):
                predictions = (
                    _top_budget_predictions(
                        test_scores,
                        review_budget,
                        tuple(record.identity.employee_id for record in test),
                    )
                    if selection is None
                    else [score >= selection.threshold for score in test_scores]
                )
                row, records = _evaluation_output(
                    scenario,
                    test,
                    test_truth,
                    test_scores,
                    predictions,
                    method=method,
                    representation=representation.name,
                    operating_point=operating_point,
                    threshold=None if selection is None else selection.threshold,
                    validation_selection=selection,
                    runtime_ms=runtime_ms,
                )
                metric_rows.append(row)
                prediction_rows.extend(records)

    started = perf_counter()
    deterministic_validation_scores = tuple(float(len(validate_record(record))) for record in validation)
    deterministic_scores = tuple(float(len(validate_record(record))) for record in test)
    deterministic_runtime_ms = (perf_counter() - started) * 1000
    deterministic_predictions = [score > 0 for score in deterministic_scores]
    row, records = _evaluation_output(
        scenario,
        test,
        test_truth,
        deterministic_scores,
        deterministic_predictions,
        method="deterministic_rules",
        representation="explicit_checks",
        operating_point="rules_fixed",
        threshold=0.0,
        validation_selection=None,
        runtime_ms=deterministic_runtime_ms,
    )
    metric_rows.append(row)
    prediction_rows.extend(records)

    invariant_rule_predictions = [score > 0 for score in invariant_rule_scores]
    row, records = _evaluation_output(
        scenario,
        test,
        test_truth,
        invariant_rule_scores,
        invariant_rule_predictions,
        method="deterministic_invariant_rules",
        representation="structural_contradictions",
        operating_point="rules_fixed",
        threshold=0.0,
        validation_selection=None,
        runtime_ms=invariant_rule_runtime_ms,
    )
    metric_rows.append(row)
    prediction_rows.extend(records)

    policy_rule_predictions = [score > 0 for score in policy_rule_scores]
    row, records = _evaluation_output(
        scenario,
        test,
        test_truth,
        policy_rule_scores,
        policy_rule_predictions,
        method="deterministic_policy_rules",
        representation="true_policy_checks",
        operating_point="rules_fixed",
        threshold=0.0,
        validation_selection=None,
        runtime_ms=policy_rule_runtime_ms,
    )
    metric_rows.append(row)
    prediction_rows.extend(records)

    for representation in feature_representations():
        representation_name = representation.name
        residual_train = tuple(
            record for record, score in zip(train, invariant_rule_train_scores)
            if score <= 0
        )
        residual_validation = tuple(
            record for record, score in zip(validation, invariant_rule_validation_scores)
            if score <= 0
        )
        residual_test = tuple(
            record for record, score in zip(test, invariant_rule_scores)
            if score <= 0
        )
        residual_validation_truth = [
            record.has_progression_anomaly for record in residual_validation
        ]
        residual_test_truth = [record.has_progression_anomaly for record in residual_test]
        train_vectors = _vectors(residual_train, representation, scenario)
        validation_vectors = _vectors(residual_validation, representation, scenario)
        test_vectors = _vectors(residual_test, representation, scenario)
        started = perf_counter()
        residual_scores = score_isolation_forest(
            train_vectors,
            validation_vectors + test_vectors,
            representation.feature_names,
            scenario.config.model_seed,
        ).scores
        residual_validation_scores = residual_scores[:len(validation_vectors)]
        residual_test_scores = residual_scores[len(validation_vectors):]
        runtime_ms = (perf_counter() - started) * 1000 + invariant_rule_runtime_ms
        selections = (
            _select_threshold(
                residual_validation_truth,
                residual_validation_scores,
                "validation_f1",
            ),
            _select_threshold(
                residual_validation_truth,
                residual_validation_scores,
                "validation_target_fpr",
                target_fpr=target_validation_fpr,
            ),
        )
        for operating_point, selection in (
            ("fixed_review_budget", None),
            ("validation_f1", selections[0]),
            ("validation_target_fpr", selections[1]),
        ):
            predictions = (
                _top_budget_predictions(
                    residual_test_scores,
                    review_budget,
                    tuple(record.identity.employee_id for record in residual_test),
                )
                if selection is None
                else [score >= selection.threshold for score in residual_test_scores]
            )
            row, records = _evaluation_output(
                scenario,
                residual_test,
                residual_test_truth,
                residual_test_scores,
                predictions,
                method="rule_negative_isolation_forest",
                representation=representation_name,
                operating_point=operating_point,
                threshold=None if selection is None else selection.threshold,
                validation_selection=selection,
                runtime_ms=runtime_ms,
            )
            row.update(_feature_variation_columns(test_vectors, representation))
            metric_rows.append(row)
            prediction_rows.extend(records)

    for representation in ("raw_matched", "policy_matched"):
        validation_iforest, test_iforest, iforest_runtime_ms = iforest_scores[representation]
        validation_scores = _cascade_scores(policy_rule_validation_scores, validation_iforest)
        test_scores = _cascade_scores(policy_rule_scores, test_iforest)
        selections = (
            _select_cascade_threshold(
                validation_truth,
                policy_rule_validation_scores,
                validation_iforest,
                "validation_f1",
            ),
            _select_cascade_threshold(
                validation_truth,
                policy_rule_validation_scores,
                validation_iforest,
                "validation_target_fpr",
                target_fpr=target_validation_fpr,
            ),
        )
        for operating_point, selection in (
            ("rules_first_budget_floor", None),
            ("validation_f1", selections[0]),
            ("validation_target_fpr", selections[1]),
        ):
            predictions = (
                _rules_first_budget_predictions(
                    policy_rule_scores,
                    test_iforest,
                    review_budget,
                    tuple(record.identity.employee_id for record in test),
                )
                if selection is None
                else [
                    rule_score > 0
                    or (rule_score <= 0 and model_score >= selection.threshold)
                    for rule_score, model_score in zip(policy_rule_scores, test_iforest)
                ]
            )
            row, records = _evaluation_output(
                scenario,
                test,
                test_truth,
                test_scores,
                predictions,
                method="policy_rules_plus_isolation_forest",
                representation=representation,
                operating_point=operating_point,
                threshold=None if selection is None else selection.threshold,
                validation_selection=selection,
                runtime_ms=iforest_runtime_ms + policy_rule_runtime_ms,
            )
            metric_rows.append(row)
            prediction_rows.extend(records)
    return ScenarioEvaluation(tuple(metric_rows), tuple(prediction_rows))


def _records(scenario: ScenarioDataset, split: DatasetSplit) -> tuple[WorkforceHistoryRecord, ...]:
    eligibility = getattr(
        scenario.population,
        "evaluation_eligible_by_employee_id",
        {},
    )
    return tuple(
        record for record in scenario.dataset.records
        if record.split is split
        and eligibility.get(record.identity.employee_id, True)
    )


def _vectors(
    records: tuple[WorkforceHistoryRecord, ...],
    representation: FeatureRepresentation,
    scenario: ScenarioDataset,
) -> tuple[FeatureVector, ...]:
    if representation.policy_mode == "raw":
        return tuple(extract_raw_features(record) for record in records)
    if representation.policy_mode == "shuffled":
        observed = tuple(
            extract_policy_aware_features(
                record,
                scenario.policy,
                scenario.policy_epochs,
            )
            for record in records
        )
        return _frequency_preserving_policy_permutation(
            observed,
            scenario.config.model_seed,
        )
    wrong_policy = _wrong_policy(scenario.config.policy_profile)
    vectors = []
    for record in records:
        if representation.policy_mode == "true":
            policy = scenario.policy
            policy_epochs = scenario.policy_epochs
        elif representation.policy_mode == "wrong":
            policy = wrong_policy
            policy_epochs = ()
        else:
            raise ValueError(f"unsupported policy mode: {representation.policy_mode}")
        vectors.append(extract_policy_aware_features(record, policy, policy_epochs))
    return tuple(vectors)


def _wrong_policy(true_profile: str) -> PromotionPolicy:
    profiles = policy_profiles()
    profile_names = tuple(profiles)
    index = profile_names.index(true_profile)
    return profiles[profile_names[(index + 1) % len(profile_names)]]


def _frequency_preserving_policy_permutation(
    vectors: tuple[FeatureVector, ...],
    seed: int,
) -> tuple[FeatureVector, ...]:
    """Permute observed policy signals without changing their frequencies.

    The former control selected one of three stock profiles by employee hash;
    that was random reassignment, not a shuffle of the scenario's observed
    policy context. This rotation uses every observed policy-signal row exactly
    once and is deterministic for a scenario/model seed.
    """

    if len(vectors) < 2:
        return vectors
    policy_columns = (
        "policy_service_deficit_months",
        "policy_service_deficit_ratio",
        "policy_unexplained_short_promotion",
    )
    order = sorted(
        range(len(vectors)),
        key=lambda index: sha256(
            f"{seed}:{vectors[index].employee_id}".encode("utf-8")
        ).digest(),
    )
    donor_by_target = {
        target: order[(position + 1) % len(order)]
        for position, target in enumerate(order)
    }
    permuted = []
    for target_index, vector in enumerate(vectors):
        donor = vectors[donor_by_target[target_index]]
        values = dict(vector.values)
        for column in policy_columns:
            values[column] = donor.values[column]
        permuted.append(FeatureVector(vector.employee_id, vector.feature_set, values))
    return tuple(permuted)


def _select_threshold(
    y_true: list[bool],
    scores: tuple[float, ...],
    mode: str,
    target_fpr: float = 0.05,
) -> ThresholdSelection:
    if len(y_true) != len(scores) or not scores:
        raise ValueError("validation truth and scores must be non-empty and aligned")
    candidates = [inf, *sorted(set(scores), reverse=True)]
    selections = []
    for threshold in candidates:
        predictions = [score >= threshold for score in scores]
        metrics = confusion_counts(y_true, predictions)
        selections.append((threshold, metrics, sum(predictions)))
    if mode == "validation_f1":
        threshold, metrics, alerts = max(
            selections,
            key=lambda item: (item[1].f1, item[1].precision, item[1].recall, -item[2], item[0]),
        )
    elif mode == "validation_target_fpr":
        feasible = [item for item in selections if item[1].false_positive_rate <= target_fpr + 1e-12]
        if feasible:
            threshold, metrics, alerts = max(
                feasible,
                key=lambda item: (item[1].recall, item[1].precision, -item[2], item[0]),
            )
            constraint_satisfied = True
        else:
            threshold, metrics, alerts = min(
                selections,
                key=lambda item: (item[1].false_positive_rate, item[2], -item[0]),
            )
            constraint_satisfied = False
    else:
        raise ValueError(f"unsupported threshold mode: {mode}")
    return ThresholdSelection(
        mode,
        threshold,
        metrics,
        alerts,
        constraint_satisfied if mode == "validation_target_fpr" else True,
    )


def _top_budget_predictions(
    scores: tuple[float, ...],
    fraction: float,
    tie_keys: tuple[str, ...] | None = None,
) -> list[bool]:
    alert_count = max(1, ceil(len(scores) * fraction))
    if tie_keys is not None and len(tie_keys) != len(scores):
        raise ValueError("tie keys and scores must be aligned")
    keys = tie_keys or tuple(str(index) for index in range(len(scores)))
    ranked = sorted(
        range(len(scores)),
        key=lambda index: (-scores[index], sha256(keys[index].encode("utf-8")).digest()),
    )
    selected = set(ranked[:alert_count])
    return [index in selected for index in range(len(scores))]


def _rules_first_budget_predictions(
    deterministic_scores: tuple[float, ...],
    model_scores: tuple[float, ...],
    fraction: float,
    tie_keys: tuple[str, ...] | None = None,
) -> list[bool]:
    """Keep every rule finding and use ML only to fill remaining capacity."""

    if len(deterministic_scores) != len(model_scores) or not model_scores:
        raise ValueError("cascade score inputs must be non-empty and aligned")
    if tie_keys is not None and len(tie_keys) != len(model_scores):
        raise ValueError("tie keys and scores must be aligned")
    keys = tie_keys or tuple(str(index) for index in range(len(model_scores)))
    rule_indices = {
        index for index, score in enumerate(deterministic_scores) if score > 0
    }
    nominal_budget = max(1, ceil(len(model_scores) * fraction))
    target_alert_count = max(nominal_budget, len(rule_indices))
    residual_ranked = sorted(
        (index for index in range(len(model_scores)) if index not in rule_indices),
        key=lambda index: (
            -model_scores[index],
            sha256(keys[index].encode("utf-8")).digest(),
        ),
    )
    selected = rule_indices | set(
        residual_ranked[:target_alert_count - len(rule_indices)]
    )
    return [index in selected for index in range(len(model_scores))]


def _select_cascade_threshold(
    y_true: list[bool],
    deterministic_scores: tuple[float, ...],
    model_scores: tuple[float, ...],
    mode: str,
    target_fpr: float = 0.05,
) -> ThresholdSelection:
    """Select an ML threshold while deterministic rule findings remain mandatory."""

    if (
        len(y_true) != len(deterministic_scores)
        or len(y_true) != len(model_scores)
        or not y_true
    ):
        raise ValueError("cascade validation inputs must be non-empty and aligned")
    residual_scores = [
        model_score
        for rule_score, model_score in zip(deterministic_scores, model_scores)
        if rule_score <= 0
    ]
    candidates = [inf, *sorted(set(residual_scores), reverse=True)]
    selections = []
    for threshold in candidates:
        predictions = [
            rule_score > 0
            or (rule_score <= 0 and model_score >= threshold)
            for rule_score, model_score in zip(deterministic_scores, model_scores)
        ]
        metrics = confusion_counts(y_true, predictions)
        selections.append((threshold, metrics, sum(predictions)))
    if mode == "validation_f1":
        threshold, metrics, alerts = max(
            selections,
            key=lambda item: (item[1].f1, item[1].precision, item[1].recall, -item[2], item[0]),
        )
    elif mode == "validation_target_fpr":
        feasible = [item for item in selections if item[1].false_positive_rate <= target_fpr + 1e-12]
        if feasible:
            threshold, metrics, alerts = max(
                feasible,
                key=lambda item: (item[1].recall, item[1].precision, -item[2], item[0]),
            )
            constraint_satisfied = True
        else:
            threshold, metrics, alerts = min(
                selections,
                key=lambda item: (item[1].false_positive_rate, item[2], -item[0]),
            )
            constraint_satisfied = False
    else:
        raise ValueError(f"unsupported threshold mode: {mode}")
    return ThresholdSelection(
        mode,
        threshold,
        metrics,
        alerts,
        constraint_satisfied if mode == "validation_target_fpr" else True,
    )


def _cascade_scores(
    deterministic_scores: tuple[float, ...],
    model_scores: tuple[float, ...],
) -> tuple[float, ...]:
    """Prioritize explicit rule findings, then rank remaining records by ML."""

    if len(deterministic_scores) != len(model_scores):
        raise ValueError("cascade score inputs must be aligned")
    order = sorted(range(len(model_scores)), key=lambda index: (model_scores[index], index))
    rank_by_index = {
        index: rank / max(1, len(model_scores) - 1)
        for rank, index in enumerate(order)
    }
    return tuple(
        2.0 + deterministic if deterministic > 0 else rank_by_index[index]
        for index, deterministic in enumerate(deterministic_scores)
    )


def _evaluation_output(
    scenario: ScenarioDataset,
    records: tuple[WorkforceHistoryRecord, ...],
    y_true: list[bool],
    scores: tuple[float, ...],
    predictions: list[bool],
    *,
    method: str,
    representation: str,
    operating_point: str,
    threshold: float | None,
    validation_selection: ThresholdSelection | None,
    runtime_ms: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    metrics = confusion_counts(y_true, predictions)
    rare_mask = [AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in records]
    clean_mask = [record.anomaly_labels == (AnomalyType.CLEAN,) for record in records]
    rare_count = sum(rare_mask)
    rare_flagged = sum(predicted and rare for predicted, rare in zip(predictions, rare_mask))
    clean_count = sum(clean_mask)
    clean_flagged = sum(predicted and clean for predicted, clean in zip(predictions, clean_mask))
    alert_count = sum(predictions)
    positive_count = sum(y_true)
    recall_defined = positive_count > 0
    average_precision = _average_precision(y_true, scores)
    row: dict[str, object] = {
        **_scenario_columns(scenario),
        "method": method,
        "representation": representation,
        "operating_point": operating_point,
        "threshold": "" if threshold is None else threshold,
        "evaluation_count": len(records),
        "positive_count": positive_count,
        "negative_count": len(y_true) - positive_count,
        "alert_count": alert_count,
        "alert_rate": _ratio(alert_count, len(records)),
        "true_positives": metrics.true_positives,
        "false_positives": metrics.false_positives,
        "true_negatives": metrics.true_negatives,
        "false_negatives": metrics.false_negatives,
        "precision": metrics.precision,
        "recall": metrics.recall if recall_defined else "",
        "recall_defined": recall_defined,
        "f1": metrics.f1,
        "false_positive_rate": metrics.false_positive_rate,
        "average_precision": "" if average_precision is None else average_precision,
        "average_precision_defined": average_precision is not None,
        "paired_recall_eligible": recall_defined,
        "paired_average_precision_eligible": average_precision is not None,
        "rare_legitimate_count": rare_count,
        "rare_legitimate_flagged": rare_flagged,
        "rare_legitimate_flagged_rate": _ratio(rare_flagged, rare_count),
        "ordinary_clean_count": clean_count,
        "ordinary_clean_flagged": clean_flagged,
        "ordinary_clean_flagged_rate": _ratio(clean_flagged, clean_count),
        "anomalies_found_per_100_reviews": 100 * _ratio(metrics.true_positives, alert_count),
        "rare_legitimate_reviews_per_1000_employees": 1000 * _ratio(rare_flagged, len(records)),
        "missed_anomalies_per_1000_employees": 1000 * _ratio(metrics.false_negatives, len(records)),
        "runtime_ms": runtime_ms,
        "validation_alert_count": "" if validation_selection is None else validation_selection.validation_alert_count,
        "validation_precision": "" if validation_selection is None else validation_selection.validation_metrics.precision,
        "validation_recall": "" if validation_selection is None else validation_selection.validation_metrics.recall,
        "validation_fpr": "" if validation_selection is None else validation_selection.validation_metrics.false_positive_rate,
        "validation_constraint_satisfied": (
            "" if validation_selection is None else validation_selection.constraint_satisfied
        ),
    }
    for anomaly_type in (
        AnomalyType.INCONSISTENT_DATES,
        AnomalyType.FREQUENT_PROMOTIONS,
        AnomalyType.EXCESSIVE_SANCTIONS,
        AnomalyType.UNUSUAL_ADMIN_INTERVAL,
    ):
        mask = [anomaly_type in record.anomaly_labels for record in records]
        count = sum(mask)
        found = sum(predicted and expected for predicted, expected in zip(predictions, mask))
        row[f"{anomaly_type.value}_count"] = count
        row[f"{anomaly_type.value}_recall"] = "" if count == 0 else _ratio(found, count)

    prediction_rows = [{
        **_scenario_columns(scenario),
        "employee_id": record.identity.employee_id,
        "method": method,
        "representation": representation,
        "operating_point": operating_point,
        "score": score,
        "predicted_anomaly": predicted,
        "ground_truth_anomaly": expected,
        "labels": "|".join(label.value for label in record.anomaly_labels),
        "evaluation_eligible": True,
    } for record, score, predicted, expected in zip(records, scores, predictions, y_true)]
    return row, prediction_rows


def _scenario_columns(scenario: ScenarioDataset) -> dict[str, object]:
    config = scenario.config
    return {
        "scenario_id": config.scenario_id,
        "run_purpose": config.run_purpose,
        "dataset_run_id": scenario.dataset.metadata.run_id,
        "dataset_seed": config.dataset_seed,
        "split_seed": config.split_seed,
        "model_seed": config.model_seed,
        "policy_profile": config.policy_profile,
        "population_profile": config.population_profile,
        "anomaly_mechanism": config.anomaly_mechanism,
        "rare_pattern": config.rare_pattern,
        "configured_anomaly_rate": config.anomaly_rate,
        "configured_rare_rate": config.rare_legitimate_rate,
    }


def _feature_variation_columns(
    vectors: tuple[FeatureVector, ...],
    representation: FeatureRepresentation,
) -> dict[str, object]:
    unique_counts = {
        name: len({vector.values[name] for vector in vectors})
        for name in representation.feature_names
    }
    policy_names = {
        "policy_service_deficit_months",
        "policy_service_deficit_ratio",
        "policy_unexplained_short_promotion",
    }
    return {
        "constant_feature_count": sum(
            count <= 1 for count in unique_counts.values()
        ),
        "nonconstant_feature_count": sum(
            count > 1 for count in unique_counts.values()
        ),
        "policy_signal_nonconstant_feature_count": sum(
            unique_counts.get(name, 0) > 1 for name in policy_names
        ),
        "feature_unique_counts_json": json.dumps(
            unique_counts, sort_keys=True
        ),
    }


def _average_precision(
    y_true: list[bool],
    scores: tuple[float, ...],
) -> float | None:
    if not any(y_true):
        return None
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y_true, scores))


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
