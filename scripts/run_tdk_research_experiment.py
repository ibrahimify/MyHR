"""Generate reproducible TDK research artifacts for paper tables.

The smoke script proves the pipeline is wired. This script writes reviewable
artifacts that can be cited while drafting the paper.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
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
    evaluate_duplicate_detection,
    evaluate_statistical_baseline,
    extract_features,
    generate_synthetic_dataset,
    run_isolation_forest,
    sklearn_is_available,
)
from src.services.anomaly_detection.experiment_runner import (
    DEFAULT_BASELINE_FEATURES,
    DEFAULT_POLICY_AWARE_FEATURES,
)


PROTOCOL_VERSION = "draft-v2-2026-10-15"
PROTOCOL_STATUS = "draft_holdout_locked"
PROVENANCE_SOURCE_PATHS = (
    "src/services/promotion_policy.py",
    "src/services/anomaly_detection/synthetic_data.py",
    "src/services/anomaly_detection/policy_model.py",
    "src/services/anomaly_detection/policy_history.py",
    "src/services/anomaly_detection/features.py",
    "src/services/anomaly_detection/isolation_forest.py",
    "src/services/anomaly_detection/metrics.py",
    "src/services/anomaly_detection/deterministic_checks.py",
    "src/services/anomaly_detection/statistical_baselines.py",
    "src/services/anomaly_detection/experiment_runner.py",
    "src/services/anomaly_detection/duplicate_detection.py",
    "src/services/anomaly_detection/scenario_generation.py",
    "src/services/anomaly_detection/protocol_evaluation.py",
    "src/research/independent_scenarios.py",
    "src/research/independent_scenario_adapter.py",
    "scripts/run_tdk_research_experiment.py",
    "scripts/run_tdk_research_multiseed.py",
    "scripts/run_tdk_protocol_experiment.py",
    "scripts/run_tdk_independent_development.py",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MyHR TDK research artifacts.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--employee-count", type=int, default=1000)
    parser.add_argument("--anomaly-rate", type=float, default=0.10)
    parser.add_argument("--rare-legitimate-rate", type=float, default=0.05)
    parser.add_argument("--output-dir", type=Path, default=Path("research_outputs"))
    args = parser.parse_args()

    config = ExperimentConfig(
        seed=args.seed,
        employee_count=args.employee_count,
        anomaly_rate=args.anomaly_rate,
        rare_legitimate_rate=args.rare_legitimate_rate,
    )
    dataset = generate_synthetic_dataset(config)
    metadata = _metadata(dataset, config)
    run_dir = args.output_dir / str(metadata["artifact_run_id"])
    run_dir.mkdir(parents=True, exist_ok=False)
    method_rows = _method_rows(dataset, config)
    duplicate_rows, candidate_rows = _duplicate_rows(dataset)

    _write_json(run_dir / "metadata.json", metadata)
    _write_csv(run_dir / "method_metrics.csv", method_rows)
    _write_csv(run_dir / "duplicate_metrics.csv", duplicate_rows)
    _write_csv(run_dir / "duplicate_candidates.csv", candidate_rows)
    _write_readme(run_dir, metadata)

    print(json.dumps({
        "artifact_run_id": metadata["artifact_run_id"],
        "dataset_run_id": dataset.metadata.run_id,
        "output_dir": str(run_dir),
        "method_rows": len(method_rows),
        "duplicate_rows": len(duplicate_rows),
        "duplicate_candidate_rows": len(candidate_rows),
    }, indent=2, sort_keys=True))


def _metadata(dataset: Any, config: ExperimentConfig) -> dict[str, Any]:
    provenance = _provenance()
    artifact_identity = {
        "dataset_run_id": dataset.metadata.run_id,
        "protocol_version": PROTOCOL_VERSION,
        "source_sha256": provenance["source_sha256"],
        "configuration": {
            "seed": config.seed,
            "employee_count": config.employee_count,
            "anomaly_rate": config.anomaly_rate,
            "rare_legitimate_rate": config.rare_legitimate_rate,
        },
    }
    artifact_run_id = sha256(
        json.dumps(artifact_identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "title": "MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_run_id": artifact_run_id,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "schema_version": dataset.metadata.schema_version,
        "dataset_run_id": dataset.metadata.run_id,
        "seed": config.seed,
        "employee_count": config.employee_count,
        "anomaly_rate": config.anomaly_rate,
        "rare_legitimate_rate": config.rare_legitimate_rate,
        "split_counts": dataset.metadata.split_counts,
        "label_counts": dataset.metadata.label_counts,
        "provenance": provenance,
        "interpretation_warning": (
            "These artifacts are reproducible experiment outputs. They should be reviewed before use in the paper."
        ),
    }


def _provenance() -> dict[str, Any]:
    packages = {}
    for package in ("scikit-learn", "numpy", "pandas", "scipy"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "not-installed"
    return {
        "command": [sys.executable, *sys.argv],
        "git_commit": _git_output("rev-parse", "HEAD"),
        "git_dirty": bool(_git_output("status", "--porcelain")),
        "python_version": sys.version,
        "platform": platform.platform(),
        "packages": packages,
        "source_sha256": {
            relative_path: sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
            for relative_path in PROVENANCE_SOURCE_PATHS
        },
    }


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _method_rows(dataset: Any, config: ExperimentConfig) -> list[dict[str, Any]]:
    rows = [
        _evaluation_row(evaluate_statistical_baseline(dataset, "raw", "iqr")),
        _evaluation_row(evaluate_statistical_baseline(dataset, "policy_aware", "iqr")),
        _evaluation_row(evaluate_statistical_baseline(dataset, "raw", "z_score")),
        _evaluation_row(evaluate_statistical_baseline(dataset, "policy_aware", "z_score")),
    ]
    if sklearn_is_available():
        rows.append(_isolation_forest_row(dataset, "raw", DEFAULT_BASELINE_FEATURES, config.seed))
        rows.append(_isolation_forest_row(dataset, "policy_aware", DEFAULT_POLICY_AWARE_FEATURES, config.seed))
    return rows


def _evaluation_row(evaluation: Any) -> dict[str, Any]:
    return {
        "task": "anomaly_detection",
        "method": evaluation.method,
        "feature_set": evaluation.feature_set,
        "feature_names": "|".join(evaluation.feature_names),
        "evaluation_count": int(evaluation.evaluation_count),
        "ground_truth_positive_count": int(evaluation.ground_truth_positive_count),
        "ground_truth_negative_count": int(evaluation.ground_truth_negative_count),
        "predicted_positive_count": int(evaluation.predicted_positive_count),
        "alert_rate": _safe_rate(evaluation.predicted_positive_count, evaluation.evaluation_count),
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
        **_metrics_dict(evaluation.metrics),
    }


def _isolation_forest_row(
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
    predictions = list(result.predictions)
    y_true = [record.has_progression_anomaly for record in test_records]
    rare_legitimate_count = sum(
        AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
        for record in test_records
    )
    rare_false_positives = sum(
        1
        for record, predicted in zip(test_records, predictions)
        if predicted and AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
    )
    clean_count = sum(
        AnomalyType.CLEAN in record.anomaly_labels
        for record in test_records
    )
    clean_false_positives = sum(
        1
        for record, predicted in zip(test_records, predictions)
        if predicted and AnomalyType.CLEAN in record.anomaly_labels
    )
    predicted_positive_count = int(sum(bool(prediction) for prediction in predictions))
    return {
        "task": "anomaly_detection",
        "method": result.method,
        "feature_set": feature_set,
        "feature_names": "|".join(feature_names),
        "evaluation_count": len(test_records),
        "ground_truth_positive_count": int(sum(y_true)),
        "ground_truth_negative_count": int(len(y_true) - sum(y_true)),
        "predicted_positive_count": predicted_positive_count,
        "alert_rate": _safe_rate(predicted_positive_count, len(test_records)),
        "rare_legitimate_count": rare_legitimate_count,
        "rare_legitimate_false_positives": int(rare_false_positives),
        "rare_legitimate_false_positive_rate": _safe_rate(
            rare_false_positives,
            rare_legitimate_count,
        ),
        "clean_count": clean_count,
        "clean_false_positives": clean_false_positives,
        "clean_false_positive_rate": _safe_rate(clean_false_positives, clean_count),
        **_metrics_dict(confusion_counts(y_true, predictions)),
    }


def _duplicate_rows(dataset: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metric_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for evaluation in (
        evaluate_duplicate_detection(dataset, "exact"),
        evaluate_duplicate_detection(dataset, "normalized_exact"),
        evaluate_duplicate_detection(dataset, "similarity", threshold=0.70),
    ):
        metric_rows.append({
            "task": "duplicate_detection",
            "method": evaluation.method,
            "threshold": "" if evaluation.threshold is None else evaluation.threshold,
            "candidate_count": len(evaluation.candidates),
            **_metrics_dict(evaluation.metrics),
        })
        for candidate in evaluation.candidates:
            candidate_rows.append({
                "method": evaluation.method,
                "threshold": "" if evaluation.threshold is None else evaluation.threshold,
                "left_employee_id": candidate.left_employee_id,
                "right_employee_id": candidate.right_employee_id,
                "score": float(candidate.score),
                "evidence_json": json.dumps(candidate.evidence, sort_keys=True),
            })
    return metric_rows, candidate_rows


def _metrics_dict(metrics: Any) -> dict[str, Any]:
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


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(run_dir: Path, metadata: dict[str, Any]) -> None:
    (run_dir / "README.md").write_text(
        "\n".join([
            "# MyHR TDK Research Run",
            "",
            f"Artifact run ID: `{metadata['artifact_run_id']}`",
            f"Dataset run ID: `{metadata['dataset_run_id']}`",
            f"Seed: `{metadata['seed']}`",
            f"Employee count: `{metadata['employee_count']}`",
            "",
            "Files:",
            "",
            "- `metadata.json`: run configuration and dataset label counts.",
            "- `method_metrics.csv`: anomaly-detection method metrics.",
            "- `duplicate_metrics.csv`: duplicate-detection method metrics.",
            "- `duplicate_candidates.csv`: candidate duplicate pairs with evidence.",
            "",
            "Do not treat these numbers as final paper claims until the methodology and outputs are reviewed.",
            "",
        ]),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
