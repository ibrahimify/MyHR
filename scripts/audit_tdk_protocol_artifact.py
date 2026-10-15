"""Independently verify a saved TDK protocol artifact from stored evidence."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any


COUNT_COLUMNS = (
    "evaluation_count",
    "positive_count",
    "negative_count",
    "alert_count",
    "true_positives",
    "false_positives",
    "true_negatives",
    "false_negatives",
    "rare_legitimate_count",
    "rare_legitimate_flagged",
    "ordinary_clean_count",
    "ordinary_clean_flagged",
)
RATE_COLUMNS = (
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "alert_rate",
    "rare_legitimate_flagged_rate",
    "ordinary_clean_flagged_rate",
)


class ArtifactAuditError(RuntimeError):
    """Raised when a saved research artifact fails an integrity check."""


def audit_artifact(run_dir: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Verify checksums, provenance, denominators, and stored predictions."""

    run_dir = run_dir.resolve()
    repo_root = (repo_root or Path.cwd()).resolve()
    metadata = _read_json(run_dir / "metadata.json")
    manifest = _read_json(run_dir / "manifest.json")
    _verify_boundary(metadata)
    _verify_manifest(run_dir, manifest)
    _verify_source_revision(metadata, repo_root)

    metric_rows = _read_csv(run_dir / "scenario_metrics.csv")
    prediction_rows = _read_csv(run_dir / "record_predictions.csv")
    aggregate_rows = _read_csv(run_dir / "aggregate_metrics.csv")
    _verify_scenario_metrics(metric_rows, prediction_rows)
    _verify_aggregates(metric_rows, aggregate_rows)

    scenarios = {row["scenario_id"] for row in metric_rows}
    return {
        "status": "verified",
        "artifact_id": metadata["artifact_id"],
        "run_purpose": metadata["run_purpose"],
        "protocol_version": metadata["protocol_version"],
        "holdout_accessed": metadata["holdout_accessed"],
        "scenario_count": len(scenarios),
        "scenario_metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "manifest_file_count": len(manifest["files"]),
        "selected_results": _selected_results(aggregate_rows),
    }


def _verify_boundary(metadata: dict[str, Any]) -> None:
    if metadata.get("holdout_accessed") is not False:
        raise ArtifactAuditError("artifact does not attest holdout_accessed=false")
    if metadata.get("run_purpose") not in {"development", "validation"}:
        raise ArtifactAuditError("only development or validation artifacts may be audited here")
    if "holdout_locked" not in str(metadata.get("protocol_status", "")):
        raise ArtifactAuditError("artifact protocol status does not preserve the holdout lock")


def _verify_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("algorithm") != "sha256":
        raise ArtifactAuditError("unsupported manifest algorithm")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ArtifactAuditError("manifest has no files")
    actual_files = {
        path.name for path in run_dir.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_files != set(files):
        raise ArtifactAuditError("manifest file set does not match artifact directory")
    for name, expected in files.items():
        actual = sha256((run_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ArtifactAuditError(f"checksum mismatch: {name}")


def _verify_source_revision(metadata: dict[str, Any], repo_root: Path) -> None:
    provenance = metadata.get("provenance", {})
    if provenance.get("git_dirty") is not False:
        raise ArtifactAuditError("artifact was not generated from a clean worktree")
    revision = provenance.get("git_commit")
    hashes = provenance.get("source_sha256", {})
    if not revision or not isinstance(hashes, dict):
        raise ArtifactAuditError("source revision provenance is incomplete")
    for relative_path, expected in hashes.items():
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative_path}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            raise ArtifactAuditError(f"cannot read {relative_path} at source revision")
        if sha256(result.stdout).hexdigest() != expected:
            raise ArtifactAuditError(f"source hash mismatch: {relative_path}")


def _verify_scenario_metrics(
    metric_rows: list[dict[str, str]],
    prediction_rows: list[dict[str, str]],
) -> None:
    predictions: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in prediction_rows:
        predictions[_key(row)].append(row)
    if len(predictions) != len(metric_rows):
        raise ArtifactAuditError("prediction groups do not match scenario metric rows")

    for stored in metric_rows:
        rows = predictions.get(_key(stored), [])
        if not rows:
            raise ArtifactAuditError(f"missing predictions for {_key(stored)}")
        if len({row["employee_id"] for row in rows}) != len(rows):
            raise ArtifactAuditError(f"duplicate employee predictions for {_key(stored)}")
        truth = [_parse_bool(row["ground_truth_anomaly"]) for row in rows]
        predicted = [_parse_bool(row["predicted_anomaly"]) for row in rows]
        labels = [set(row["labels"].split("|")) for row in rows]
        tp = sum(expected and observed for expected, observed in zip(truth, predicted))
        fp = sum(not expected and observed for expected, observed in zip(truth, predicted))
        tn = sum(not expected and not observed for expected, observed in zip(truth, predicted))
        fn = sum(expected and not observed for expected, observed in zip(truth, predicted))
        rare_mask = ["policy_legitimate_rare_case" in item for item in labels]
        clean_mask = [item == {"clean"} for item in labels]
        counts = {
            "evaluation_count": len(rows),
            "positive_count": sum(truth),
            "negative_count": len(rows) - sum(truth),
            "alert_count": sum(predicted),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "rare_legitimate_count": sum(rare_mask),
            "rare_legitimate_flagged": sum(flag and rare for flag, rare in zip(predicted, rare_mask)),
            "ordinary_clean_count": sum(clean_mask),
            "ordinary_clean_flagged": sum(flag and clean for flag, clean in zip(predicted, clean_mask)),
        }
        for column, actual in counts.items():
            if int(stored[column]) != actual:
                raise ArtifactAuditError(f"{column} mismatch for {_key(stored)}")
        rates = {
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
            "f1": _ratio(2 * tp, 2 * tp + fp + fn),
            "false_positive_rate": _ratio(fp, fp + tn),
            "alert_rate": _ratio(sum(predicted), len(rows)),
            "rare_legitimate_flagged_rate": _ratio(
                counts["rare_legitimate_flagged"], counts["rare_legitimate_count"]
            ),
            "ordinary_clean_flagged_rate": _ratio(
                counts["ordinary_clean_flagged"], counts["ordinary_clean_count"]
            ),
        }
        for column, actual in rates.items():
            if abs(float(stored[column]) - actual) > 1e-12:
                raise ArtifactAuditError(f"{column} mismatch for {_key(stored)}")


def _verify_aggregates(
    metric_rows: list[dict[str, str]],
    aggregate_rows: list[dict[str, str]],
) -> None:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in metric_rows:
        groups[(row["method"], row["representation"], row["operating_point"])].append(row)
    if len(groups) != len(aggregate_rows):
        raise ArtifactAuditError("aggregate groups do not match scenario metrics")
    indexed = {
        (row["method"], row["representation"], row["operating_point"]): row
        for row in aggregate_rows
    }
    for key, rows in groups.items():
        stored = indexed.get(key)
        if stored is None:
            raise ArtifactAuditError(f"missing aggregate row for {key}")
        if int(stored["scenario_count"]) != len(rows):
            raise ArtifactAuditError(f"scenario count mismatch for {key}")
        for column in COUNT_COLUMNS:
            if int(stored[f"{column}_total"]) != sum(int(row[column]) for row in rows):
                raise ArtifactAuditError(f"aggregate {column} mismatch for {key}")
        for column in RATE_COLUMNS:
            actual = mean(float(row[column]) for row in rows)
            if abs(float(stored[f"{column}_mean"]) - actual) > 1e-12:
                raise ArtifactAuditError(f"aggregate {column} mismatch for {key}")


def _selected_results(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        method = row["method"]
        operating_point = row["operating_point"]
        if not (
            (method == "deterministic_policy_rules" and operating_point == "rules_fixed")
            or (
                method == "policy_rules_plus_isolation_forest"
                and operating_point == "rules_first_budget_floor"
            )
        ):
            continue
        average_precision_column = (
            "average_precision_mean"
            if "average_precision_mean" in row
            else "pr_auc_mean"
        )
        selected.append({
            "method": method,
            "representation": row["representation"],
            "operating_point": operating_point,
            "evaluation_count": int(row["evaluation_count_total"]),
            "alert_count": int(row["alert_count_total"]),
            "true_positives": int(row["true_positives_total"]),
            "false_positives": int(row["false_positives_total"]),
            "false_negatives": int(row["false_negatives_total"]),
            "rare_legitimate_flagged": int(row["rare_legitimate_flagged_total"]),
            "rare_legitimate_count": int(row["rare_legitimate_count_total"]),
            "f1_mean": float(row["f1_mean"]),
            "average_precision_mean": float(row[average_precision_column]),
        })
    return selected


def _key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["scenario_id"],
        row["method"],
        row["representation"],
        row["operating_point"],
    )


def _parse_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ArtifactAuditError(f"invalid boolean value: {value}")


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ArtifactAuditError(f"missing artifact file: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ArtifactAuditError(f"missing artifact file: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = audit_artifact(args.run_dir, args.repo_root)
    except ArtifactAuditError as exc:
        raise SystemExit(f"artifact audit failed: {exc}") from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
