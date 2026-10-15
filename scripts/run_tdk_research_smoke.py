"""Run a small reproducible TDK research smoke experiment.

This script is intentionally small: it verifies that synthetic data generation,
feature extraction, statistical baselines, and Isolation Forest are wired
together. It is not a final experiment runner for paper results.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services.anomaly_detection import (
    AnomalyType,
    DatasetSplit,
    ExperimentConfig,
    confusion_counts,
    evaluate_statistical_baseline,
    extract_features,
    evaluate_duplicate_detection,
    generate_synthetic_dataset,
    run_isolation_forest,
    sklearn_is_available,
)
from src.services.anomaly_detection.experiment_runner import (
    DEFAULT_BASELINE_FEATURES,
    DEFAULT_POLICY_AWARE_FEATURES,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MyHR TDK research smoke verification.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--employee-count", type=int, default=300)
    parser.add_argument("--anomaly-rate", type=float, default=0.10)
    parser.add_argument("--rare-legitimate-rate", type=float, default=0.05)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    config = ExperimentConfig(
        seed=args.seed,
        employee_count=args.employee_count,
        anomaly_rate=args.anomaly_rate,
        rare_legitimate_rate=args.rare_legitimate_rate,
    )
    dataset = generate_synthetic_dataset(config)

    report: dict[str, Any] = {
        "experiment": {
            "run_id": dataset.metadata.run_id,
            "seed": dataset.metadata.seed,
            "employee_count": dataset.metadata.employee_count,
            "split_counts": dataset.metadata.split_counts,
            "label_counts": dataset.metadata.label_counts,
        },
        "statistical_baselines": [
            _evaluation_to_dict(evaluate_statistical_baseline(dataset, "raw", "iqr")),
            _evaluation_to_dict(evaluate_statistical_baseline(dataset, "policy_aware", "iqr")),
            _evaluation_to_dict(evaluate_statistical_baseline(dataset, "raw", "z_score")),
            _evaluation_to_dict(evaluate_statistical_baseline(dataset, "policy_aware", "z_score")),
        ],
        "isolation_forest": [],
        "duplicate_detection": [
            _duplicate_evaluation_to_dict(evaluate_duplicate_detection(dataset, "exact")),
            _duplicate_evaluation_to_dict(evaluate_duplicate_detection(dataset, "normalized_exact")),
            _duplicate_evaluation_to_dict(evaluate_duplicate_detection(dataset, "similarity", threshold=0.70)),
        ],
    }

    if sklearn_is_available():
        report["isolation_forest"].append(_isolation_forest_to_dict(dataset, "raw", DEFAULT_BASELINE_FEATURES, config.seed))
        report["isolation_forest"].append(
            _isolation_forest_to_dict(dataset, "policy_aware", DEFAULT_POLICY_AWARE_FEATURES, config.seed)
        )
    else:
        report["isolation_forest_unavailable"] = "Install requirements-research.txt to run Isolation Forest."

    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def _evaluation_to_dict(evaluation: Any) -> dict[str, Any]:
    metrics = evaluation.metrics
    return {
        "method": evaluation.method,
        "feature_set": evaluation.feature_set,
        "feature_names": list(evaluation.feature_names),
        "evaluation_count": int(evaluation.evaluation_count),
        "predicted_positive_count": int(evaluation.predicted_positive_count),
        "rare_legitimate_count": int(evaluation.rare_legitimate_count),
        "rare_legitimate_false_positives": int(evaluation.rare_legitimate_false_positives),
        "rare_legitimate_false_positive_rate": _safe_rate(
            evaluation.rare_legitimate_false_positives,
            evaluation.rare_legitimate_count,
        ),
        "clean_count": int(evaluation.clean_count),
        "clean_false_positives": int(evaluation.clean_false_positives),
        "clean_false_positive_rate": _safe_rate(
            evaluation.clean_false_positives,
            evaluation.clean_count,
        ),
        "metrics": _metrics_to_dict(metrics),
    }


def _isolation_forest_to_dict(
    dataset: Any,
    feature_set: str,
    feature_names: tuple[str, ...],
    seed: int,
) -> dict[str, Any]:
    train_records = tuple(
        record for record in dataset.records
        if record.split is DatasetSplit.TRAIN
        and AnomalyType.DUPLICATE_RECORD not in record.anomaly_labels
    )
    test_records = tuple(
        record for record in dataset.records
        if record.split is DatasetSplit.TEST
        and AnomalyType.DUPLICATE_RECORD not in record.anomaly_labels
    )
    train_vectors = tuple(extract_features(record, feature_set) for record in train_records)
    test_vectors = tuple(extract_features(record, feature_set) for record in test_records)
    result = run_isolation_forest(
        train_vectors=train_vectors,
        test_vectors=test_vectors,
        feature_names=feature_names,
        contamination=0.10,
        random_state=seed,
    )
    y_true = [record.has_progression_anomaly for record in test_records]
    predictions = list(result.predictions)
    rare_legitimate_count = sum(
        AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
        for record in test_records
    )
    rare_false_positives = int(sum(
        1
        for record, predicted in zip(test_records, predictions)
        if predicted and AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
    ))
    clean_count = sum(AnomalyType.CLEAN in record.anomaly_labels for record in test_records)
    clean_false_positives = sum(
        1
        for record, predicted in zip(test_records, predictions)
        if predicted and AnomalyType.CLEAN in record.anomaly_labels
    )
    return {
        "method": result.method,
        "feature_set": feature_set,
        "feature_names": list(feature_names),
        "evaluation_count": len(test_records),
        "predicted_positive_count": int(sum(bool(prediction) for prediction in predictions)),
        "rare_legitimate_count": rare_legitimate_count,
        "rare_legitimate_false_positives": rare_false_positives,
        "rare_legitimate_false_positive_rate": _safe_rate(
            rare_false_positives,
            rare_legitimate_count,
        ),
        "clean_count": clean_count,
        "clean_false_positives": clean_false_positives,
        "clean_false_positive_rate": _safe_rate(clean_false_positives, clean_count),
        "metrics": _metrics_to_dict(confusion_counts(y_true, predictions)),
    }


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _duplicate_evaluation_to_dict(evaluation: Any) -> dict[str, Any]:
    return {
        "method": evaluation.method,
        "threshold": evaluation.threshold,
        "candidate_count": len(evaluation.candidates),
        "metrics": _metrics_to_dict(evaluation.metrics),
        "sample_candidates": [
            {
                "left_employee_id": candidate.left_employee_id,
                "right_employee_id": candidate.right_employee_id,
                "score": float(candidate.score),
                "evidence": candidate.evidence,
            }
            for candidate in evaluation.candidates[:3]
        ],
    }


def _metrics_to_dict(metrics: Any) -> dict[str, float | int]:
    return {
        "true_positives": int(metrics.true_positives),
        "false_positives": int(metrics.false_positives),
        "true_negatives": int(metrics.true_negatives),
        "false_negatives": int(metrics.false_negatives),
        "precision": float(metrics.precision),
        "recall": float(metrics.recall),
        "f1": float(metrics.f1),
        "false_positive_rate": float(metrics.false_positive_rate),
    }


if __name__ == "__main__":
    main()
