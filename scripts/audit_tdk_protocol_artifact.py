"""Independently verify a saved TDK protocol artifact from stored evidence."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from datetime import date
from hashlib import sha256
from itertools import product
from math import isfinite
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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
    "average_precision",
    "anomalies_found_per_100_reviews",
    "rare_legitimate_reviews_per_1000_employees",
    "missed_anomalies_per_1000_employees",
)
LEGACY_AUDITED_PAIR_METRICS = (
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "average_precision",
    "alert_rate",
    "rare_legitimate_flagged_rate",
    "ordinary_clean_flagged_rate",
    "anomalies_found_per_100_reviews",
    "rare_legitimate_reviews_per_1000_employees",
    "missed_anomalies_per_1000_employees",
)
PAIR_METRICS = LEGACY_AUDITED_PAIR_METRICS + (
    "false_positives",
    "inconsistent_dates_recall",
    "frequent_promotions_recall",
    "excessive_sanctions_recall",
    "unusual_admin_interval_recall",
)
PRIMARY_COMPARISON = (
    "rule_negative_isolation_forest",
    "fixed_review_budget",
)
PRIMARY_ENDPOINT = "recall"
SECONDARY_COMPARISON_METRICS = (
    "average_precision",
    "rare_legitimate_flagged_rate",
    "ordinary_clean_flagged_rate",
)
CONTROL_CONTRAST_METRICS = (
    "recall",
    "precision",
    "average_precision",
    "false_positives",
    "rare_legitimate_flagged_rate",
)
CONTROL_CONTRASTS = (
    ("policy_matched", "raw_matched", "policy_minus_raw"),
    ("policy_matched", "raw_rate_control", "policy_minus_raw_rate"),
    ("policy_matched", "wrong_policy_control", "policy_minus_wrong_policy"),
    ("policy_matched", "shuffled_policy_control", "policy_minus_shuffled_policy"),
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
    _verify_research_environment(metadata, repo_root)

    metric_rows = _read_csv(run_dir / "scenario_metrics.csv")
    prediction_rows = _read_csv(run_dir / "record_predictions.csv")
    aggregate_rows = _read_csv(run_dir / "aggregate_metrics.csv")
    paired_rows = _read_csv(run_dir / "paired_comparisons.csv")
    config_rows = _read_csv(run_dir / "scenario_configs.csv")
    _verify_declared_matrix(metadata, config_rows, metric_rows)
    _verify_scenario_metrics(metric_rows, prediction_rows)
    _verify_aggregates(metric_rows, aggregate_rows)
    paired_schema = _verify_paired_comparisons(metric_rows, paired_rows)
    truth_sidecars = _verify_truth_sidecars(
        run_dir,
        prediction_rows,
        required=metadata.get("truth_sidecars_required") is True,
        protocol_version=str(metadata.get("protocol_version", "")),
        artifact_schema_version=int(metadata.get("artifact_schema_version", 0)),
    )
    model_comparison = _verify_model_comparison(run_dir, metadata)

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
        "paired_comparison_rows": len(paired_rows),
        "paired_comparison_schema": paired_schema,
        "truth_sidecars": truth_sidecars,
        "model_comparison": model_comparison,
        "manifest_file_count": len(manifest["files"]),
        "selected_results": _selected_results(aggregate_rows),
    }


def _verify_model_comparison(
    run_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    names = (
        "model_comparison_metrics.csv",
        "model_comparison_predictions.csv",
        "model_comparison_aggregates.csv",
        "model_comparison_paired.csv",
        "model_comparison_control_contrasts.csv",
        "model_comparison_robustness.csv",
    )
    present = tuple(name for name in names if (run_dir / name).is_file())
    required = metadata.get("model_comparison_included") is True
    if not present:
        if required:
            raise ArtifactAuditError("declared model comparison files are missing")
        return {"present": False}
    if present != names:
        raise ArtifactAuditError("model comparison file set is incomplete")

    metric_rows = _read_csv(run_dir / names[0])
    prediction_rows = _read_csv(run_dir / names[1])
    aggregate_rows = _read_csv(run_dir / names[2])
    paired_rows = _read_csv(run_dir / names[3])
    contrast_rows = _read_csv(run_dir / names[4])
    _verify_scenario_metrics(metric_rows, prediction_rows)
    _verify_aggregates(metric_rows, aggregate_rows)
    paired_schema = _verify_paired_comparisons(metric_rows, paired_rows)
    _verify_control_contrasts(metric_rows, contrast_rows)

    expected_methods = {
        "isolation_forest",
        "local_outlier_factor",
        "one_class_svm",
        "robust_z_score",
        "iqr",
    }
    expected_representations = {
        "raw_matched",
        "raw_rate_control",
        "policy_matched",
        "wrong_policy_control",
        "shuffled_policy_control",
    }
    by_scenario: dict[str, list[dict[str, str]]] = defaultdict(list)
    predictions_by_scenario: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in metric_rows:
        by_scenario[row["scenario_id"]].append(row)
        if row.get("comparison_status") != "exploratory_development":
            raise ArtifactAuditError("model comparison status is not exploratory")
        parameters = json.loads(row["scorer_parameters_json"])
        if parameters.get("preprocessing") != "train_fitted_robust_scaler":
            raise ArtifactAuditError("model comparison preprocessing is inconsistent")
        if parameters.get("score_direction") != "larger_is_more_anomalous":
            raise ArtifactAuditError("model comparison score direction is inconsistent")
        if {"labels", "review_budget", "anomaly_prevalence"}.intersection(parameters):
            raise ArtifactAuditError("evaluation information leaked into scorer parameters")
    for row in prediction_rows:
        predictions_by_scenario[row["scenario_id"]].append(row)

    expected_matrix = set(product(expected_methods, expected_representations))
    for scenario_id, rows in by_scenario.items():
        actual_matrix = {(row["method"], row["representation"]) for row in rows}
        if actual_matrix != expected_matrix:
            raise ArtifactAuditError(
                f"model comparison matrix is incomplete for {scenario_id}"
            )
        if len({int(row["evaluation_count"]) for row in rows}) != 1:
            raise ArtifactAuditError("model comparison populations differ")
        if len({int(row["alert_count"]) for row in rows}) != 1:
            raise ArtifactAuditError("model comparison review capacities differ")
        groups: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in predictions_by_scenario[scenario_id]:
            groups[(row["method"], row["representation"])].add(row["employee_id"])
        if set(groups) != expected_matrix or len({frozenset(ids) for ids in groups.values()}) != 1:
            raise ArtifactAuditError("model comparison employee populations differ")

    return {
        "present": True,
        "scenario_count": len(by_scenario),
        "metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "paired_schema": paired_schema,
        "control_contrast_rows": len(contrast_rows),
    }


def _verify_control_contrasts(
    metric_rows: list[dict[str, str]],
    stored_rows: list[dict[str, str]],
) -> None:
    expected = _audit_control_contrasts(metric_rows)
    key_fields = ("method", "operating_point", "contrast")
    stored = {
        tuple(row[field] for field in key_fields): row
        for row in stored_rows
    }
    if len(stored) != len(stored_rows) or len(stored) != len(expected):
        raise ArtifactAuditError("control contrast groups do not match metrics")
    string_fields = {
        "method",
        "operating_point",
        "contrast",
        "reference_representation",
        "comparator_representation",
        "comparison_status",
        "inference_unit",
    }
    for item in expected:
        key = tuple(str(item[field]) for field in key_fields)
        row = stored.get(key)
        if row is None:
            raise ArtifactAuditError(f"missing control contrast: {key}")
        for column, actual in item.items():
            if actual == "":
                if row[column] != "":
                    raise ArtifactAuditError(f"control contrast {column} must be blank")
            elif column in string_fields or column.endswith("_condition_seed_counts"):
                if row[column] != str(actual):
                    raise ArtifactAuditError(f"control contrast {column} mismatch")
            elif (
                column in {"scenario_count", "condition_count", "holm_family_size"}
                or column.endswith("_scenario_count")
                or column.endswith("_condition_count")
            ):
                if int(row[column]) != int(actual):
                    raise ArtifactAuditError(f"control contrast {column} mismatch")
            elif abs(_parse_float(row[column], column) - float(actual)) > 1e-12:
                raise ArtifactAuditError(f"control contrast {column} mismatch")


def _audit_control_contrasts(
    rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    indexed = {
        (row["scenario_id"], row["method"], row["representation"], row["operating_point"]): row
        for row in rows
    }
    output: list[dict[str, object]] = []
    for method in sorted({row["method"] for row in rows}):
        for operating_point in sorted({row["operating_point"] for row in rows}):
            family = []
            for reference, comparator, contrast in CONTROL_CONTRASTS:
                pairs = []
                for scenario_id in sorted({row["scenario_id"] for row in rows}):
                    left = indexed.get((scenario_id, method, reference, operating_point))
                    right = indexed.get((scenario_id, method, comparator, operating_point))
                    if left is not None and right is not None:
                        pairs.append((left, right))
                if not pairs:
                    continue
                item: dict[str, object] = {
                    "method": method,
                    "operating_point": operating_point,
                    "contrast": contrast,
                    "reference_representation": reference,
                    "comparator_representation": comparator,
                    "comparison_status": "exploratory_development",
                    "scenario_count": len(pairs),
                    "condition_count": len({
                        _condition_id(left["scenario_id"]) for left, _ in pairs
                    }),
                    "inference_unit": "scenario_seed_condition_stratified",
                }
                for metric in CONTROL_CONTRAST_METRICS:
                    grouped: dict[str, list[float]] = defaultdict(list)
                    for left, right in pairs:
                        if left[metric] == "" or right[metric] == "":
                            continue
                        grouped[_condition_id(left["scenario_id"])].append(
                            _parse_float(left[metric], metric)
                            - _parse_float(right[metric], metric)
                        )
                    item[f"{metric}_scenario_count"] = sum(map(len, grouped.values()))
                    item[f"{metric}_condition_count"] = len(grouped)
                    if not grouped:
                        for suffix in (
                            "delta_mean", "delta_median", "delta_std",
                            "delta_ci95_low", "delta_ci95_high",
                            "delta_sign_flip_p", "delta_holm_p",
                        ):
                            item[f"{metric}_{suffix}"] = ""
                        item[f"{metric}_condition_seed_counts"] = ""
                        continue
                    summary = _audit_condition_balanced_summary(
                        grouped,
                        _stable_seed(
                            "control", method, operating_point, contrast, metric
                        ),
                    )
                    item[f"{metric}_delta_mean"] = summary["mean"]
                    item[f"{metric}_delta_median"] = summary["median"]
                    item[f"{metric}_delta_std"] = summary["std"]
                    item[f"{metric}_delta_ci95_low"] = summary["ci_low"]
                    item[f"{metric}_delta_ci95_high"] = summary["ci_high"]
                    item[f"{metric}_delta_sign_flip_p"] = summary["sign_flip_p"]
                    item[f"{metric}_delta_holm_p"] = ""
                    item[f"{metric}_condition_seed_counts"] = "|".join(
                        str(value) for value in summary["seed_counts"]
                    )
                family.append(item)
            locations = [
                (item, metric)
                for item in family
                for metric in CONTROL_CONTRAST_METRICS
                if item.get(f"{metric}_delta_sign_flip_p") not in {"", None}
            ]
            adjusted = _holm_adjusted_pvalues([
                float(item[f"{metric}_delta_sign_flip_p"])
                for item, metric in locations
            ])
            for (item, metric), value in zip(locations, adjusted):
                item[f"{metric}_delta_holm_p"] = value
            for item in family:
                item["holm_family_size"] = len(locations)
            output.extend(family)
    return output


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
    if not revision or not isinstance(hashes, dict) or not hashes:
        raise ArtifactAuditError("source revision provenance is incomplete")
    # Enforce COMPLETE required-source coverage (finding R10): a non-empty subset
    # is not sufficient. Every declared provenance source path must be present,
    # so provenance cannot be partially stripped and still certify.
    from scripts.run_tdk_research_experiment import PROVENANCE_SOURCE_PATHS

    missing = [path for path in PROVENANCE_SOURCE_PATHS if path not in hashes]
    if missing:
        raise ArtifactAuditError(
            "source provenance is missing required paths: " + ", ".join(sorted(missing))
        )
    revision_check = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if revision_check.returncode != 0:
        raise ArtifactAuditError("source revision is not a resolvable commit")
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


def _verify_research_environment(metadata: dict[str, Any], repo_root: Path) -> None:
    """Verify environment provenance for schema-v8 and later artifacts."""
    if int(metadata.get("artifact_schema_version", 0)) < 8:
        return

    provenance = metadata.get("provenance", {})
    environment = provenance.get("research_environment")
    if not isinstance(environment, dict):
        raise ArtifactAuditError("research environment provenance is missing")
    if environment.get("mismatches") != []:
        raise ArtifactAuditError("artifact records research environment drift")

    expected_python = str(environment.get("expected_python_version", ""))
    recorded_python = str(provenance.get("python_version", ""))
    if not expected_python or not recorded_python.startswith(expected_python + " "):
        raise ArtifactAuditError("recorded Python does not match the declared runtime")

    lock_file = environment.get("lock_file")
    if lock_file != "requirements-research-lock.txt":
        raise ArtifactAuditError("research lock path is not the declared repository lock")
    revision = provenance.get("git_commit")
    result = subprocess.run(
        ["git", "show", f"{revision}:{lock_file}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ArtifactAuditError("cannot read research lock at source revision")
    if sha256(result.stdout).hexdigest() != environment.get("lock_sha256"):
        raise ArtifactAuditError("research lock checksum does not match source revision")

    expected_packages: dict[str, str] = {}
    for raw_line in result.stdout.decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ArtifactAuditError("research lock contains a non-exact entry")
        package, package_version = line.split("==", 1)
        expected_packages[package.casefold()] = package_version
    if provenance.get("packages") != expected_packages:
        raise ArtifactAuditError("recorded packages do not match the research lock")


def _verify_declared_matrix(
    metadata: dict[str, Any],
    config_rows: list[dict[str, str]],
    metric_rows: list[dict[str, str]],
) -> None:
    config_scenarios = [row["scenario_id"] for row in config_rows]
    if len(set(config_scenarios)) != len(config_scenarios):
        raise ArtifactAuditError("duplicate scenario configuration rows")
    if int(metadata["scenario_count"]) != len(config_scenarios):
        raise ArtifactAuditError("metadata scenario count does not match configurations")
    if "seeds_per_condition" in metadata:
        seeds_per_condition = int(metadata["seeds_per_condition"])
        condition_count = int(metadata["condition_count"])
        if len(config_rows) != condition_count * seeds_per_condition:
            raise ArtifactAuditError("condition and seed counts do not match configurations")
        by_condition: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in config_rows:
            if not row.get("condition_id") or not row.get("seed_replicate"):
                raise ArtifactAuditError("seed provenance columns are incomplete")
            by_condition[row["condition_id"]].append(row)
        if len(by_condition) != condition_count:
            raise ArtifactAuditError("declared condition count is incorrect")
        replicate_start = int(metadata.get("seed_replicate_start", 1))
        expected_replicates = set(range(
            replicate_start,
            replicate_start + seeds_per_condition,
        ))
        for condition_id, rows in by_condition.items():
            replicates = {int(row["seed_replicate"]) for row in rows}
            if replicates != expected_replicates:
                raise ArtifactAuditError(
                    f"seed replicates are incomplete for {condition_id}"
                )
            seed_columns = (
                ("seed", "split_seed", "model_seed")
                if "seed" in rows[0]
                else ("dataset_seed", "split_seed", "model_seed")
            )
            for column in seed_columns:
                if len({row[column] for row in rows}) != seeds_per_condition:
                    raise ArtifactAuditError(
                        f"{column} is not unique across {condition_id} replicates"
                    )
    metric_scenarios = {row["scenario_id"] for row in metric_rows}
    if set(config_scenarios) != metric_scenarios:
        raise ArtifactAuditError("scenario metrics do not match declared configurations")

    expected = _expected_metric_suffixes(str(metadata["protocol_version"]))
    if expected is None:
        return
    for scenario_id in config_scenarios:
        actual = {
            (row["method"], row["representation"], row["operating_point"])
            for row in metric_rows if row["scenario_id"] == scenario_id
        }
        if actual != expected:
            raise ArtifactAuditError(f"metric matrix is incomplete for {scenario_id}")


def _expected_metric_suffixes(protocol_version: str) -> set[tuple[str, str, str]] | None:
    supported = {
        "independent-development-v1-2026-10-16",
        "independent-development-v2-2026-10-29",
    }
    if protocol_version not in supported:
        return None
    validation_points = {"fixed_review_budget", "validation_f1", "validation_target_fpr"}
    paired_methods = {"iqr", "z_score"}
    result = {
        (method, representation, point)
        for method in paired_methods
        for representation in {"raw_matched", "policy_matched"}
        for point in validation_points
    }
    isolation_representations = {
        "raw_matched", "policy_matched", "policy_deficit_months_ablation",
        "policy_deficit_ratio_ablation", "policy_unexplained_ablation",
        "raw_interval_ablation", "raw_without_commendation",
        "shuffled_policy_control", "wrong_policy_control",
    }
    result.update({
        ("isolation_forest", representation, point)
        for representation in isolation_representations for point in validation_points
    })
    result.update({
        ("rule_negative_isolation_forest", representation, point)
        for representation in isolation_representations for point in validation_points
    })
    result.update({
        ("policy_rules_plus_isolation_forest", representation, point)
        for representation in {"raw_matched", "policy_matched"}
        for point in {"rules_first_budget_floor", "validation_f1", "validation_target_fpr"}
    })
    result.update({
        ("deterministic_rules", "explicit_checks", "rules_fixed"),
        ("deterministic_policy_rules", "true_policy_checks", "rules_fixed"),
    })
    if protocol_version == "independent-development-v2-2026-10-29":
        result.add((
            "deterministic_invariant_rules",
            "structural_contradictions",
            "rules_fixed",
        ))
    return result


def _verify_scenario_metrics(
    metric_rows: list[dict[str, str]],
    prediction_rows: list[dict[str, str]],
) -> None:
    predictions: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in prediction_rows:
        predictions[_key(row)].append(row)
    metric_keys = [_key(row) for row in metric_rows]
    if len(set(metric_keys)) != len(metric_keys):
        raise ArtifactAuditError("duplicate scenario metric rows")
    if set(predictions) != set(metric_keys):
        raise ArtifactAuditError("prediction groups do not match scenario metric rows")

    _verify_primary_pair_populations(predictions)

    for stored in metric_rows:
        rows = predictions.get(_key(stored), [])
        if not rows:
            raise ArtifactAuditError(f"missing predictions for {_key(stored)}")
        if len({row["employee_id"] for row in rows}) != len(rows):
            raise ArtifactAuditError(f"duplicate employee predictions for {_key(stored)}")
        truth = [_parse_bool(row["ground_truth_anomaly"]) for row in rows]
        predicted = [_parse_bool(row["predicted_anomaly"]) for row in rows]
        scores = [_parse_float(row["score"], "score") for row in rows]
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
        positive_count = counts["positive_count"]
        has_defined_flags = "recall_defined" in stored
        if has_defined_flags:
            if _parse_bool(stored["recall_defined"]) != (positive_count > 0):
                raise ArtifactAuditError(f"recall eligibility mismatch for {_key(stored)}")
            if _parse_bool(stored["average_precision_defined"]) != (positive_count > 0):
                raise ArtifactAuditError(
                    f"average-precision eligibility mismatch for {_key(stored)}"
                )
            if positive_count == 0 and (stored["recall"] or stored["average_precision"]):
                raise ArtifactAuditError(
                    f"undefined metrics must be blank for {_key(stored)}"
                )
        rates = {
            "precision": _ratio(tp, tp + fp),
            "f1": _ratio(2 * tp, 2 * tp + fp + fn),
            "false_positive_rate": _ratio(fp, fp + tn),
            "alert_rate": _ratio(sum(predicted), len(rows)),
            "rare_legitimate_flagged_rate": _ratio(
                counts["rare_legitimate_flagged"], counts["rare_legitimate_count"]
            ),
            "ordinary_clean_flagged_rate": _ratio(
                counts["ordinary_clean_flagged"], counts["ordinary_clean_count"]
            ),
            "anomalies_found_per_100_reviews": 100 * _ratio(tp, sum(predicted)),
            "rare_legitimate_reviews_per_1000_employees": 1000 * _ratio(
                counts["rare_legitimate_flagged"], len(rows)
            ),
            "missed_anomalies_per_1000_employees": 1000 * _ratio(fn, len(rows)),
        }
        if positive_count > 0 or not has_defined_flags:
            rates["recall"] = _ratio(tp, tp + fn)
            rates["average_precision"] = _average_precision(truth, scores)
        for column, actual in rates.items():
            if abs(float(stored[column]) - actual) > 1e-12:
                raise ArtifactAuditError(f"{column} mismatch for {_key(stored)}")


def _verify_primary_pair_populations(
    predictions: dict[tuple[str, str, str, str], list[dict[str, str]]],
) -> None:
    """Verify that the primary raw and policy models see identical records."""

    scenario_points = {
        (scenario_id, operating_point)
        for scenario_id, method, representation, operating_point in predictions
        if method == "rule_negative_isolation_forest"
        and representation in {"raw_matched", "policy_matched"}
    }
    for scenario_id, operating_point in scenario_points:
        raw = predictions.get((
            scenario_id,
            "rule_negative_isolation_forest",
            "raw_matched",
            operating_point,
        ))
        policy = predictions.get((
            scenario_id,
            "rule_negative_isolation_forest",
            "policy_matched",
            operating_point,
        ))
        if raw is None or policy is None:
            raise ArtifactAuditError("primary raw/policy prediction group is incomplete")
        raw_by_id = {row["employee_id"]: row for row in raw}
        policy_by_id = {row["employee_id"]: row for row in policy}
        if set(raw_by_id) != set(policy_by_id):
            raise ArtifactAuditError("primary raw/policy populations are not identical")
        for employee_id in raw_by_id:
            raw_row = raw_by_id[employee_id]
            policy_row = policy_by_id[employee_id]
            if (
                raw_row["ground_truth_anomaly"]
                != policy_row["ground_truth_anomaly"]
                or raw_row["labels"] != policy_row["labels"]
            ):
                raise ArtifactAuditError("primary raw/policy truth rows are not aligned")
        if operating_point == "fixed_review_budget":
            raw_alerts = sum(_parse_bool(row["predicted_anomaly"]) for row in raw)
            policy_alerts = sum(
                _parse_bool(row["predicted_anomaly"]) for row in policy
            )
            if raw_alerts != policy_alerts:
                raise ArtifactAuditError("primary raw/policy review budgets differ")
            _verify_top_score_selection(raw, raw_alerts)
            _verify_top_score_selection(policy, policy_alerts)

        residual_groups = {
            representation: rows
            for (candidate_scenario, method, representation, point), rows
            in predictions.items()
            if candidate_scenario == scenario_id
            and method == "rule_negative_isolation_forest"
            and point == operating_point
        }
        reference_ids = set(raw_by_id)
        for representation, rows in residual_groups.items():
            if {row["employee_id"] for row in rows} != reference_ids:
                raise ArtifactAuditError(
                    "residual control population differs for "
                    f"{scenario_id}/{operating_point}/{representation}"
                )
        if operating_point == "fixed_review_budget":
            alert_counts = {
                representation: sum(
                    _parse_bool(row["predicted_anomaly"]) for row in rows
                )
                for representation, rows in residual_groups.items()
            }
            if len(set(alert_counts.values())) > 1:
                raise ArtifactAuditError(
                    f"residual control review budgets differ: {alert_counts}"
                )


def _verify_top_score_selection(
    rows: list[dict[str, str]],
    alert_count: int,
) -> None:
    ranked = sorted(
        rows,
        key=lambda row: (
            -_parse_float(row["score"], "score"),
            sha256(row["employee_id"].encode("utf-8")).digest(),
        ),
    )
    expected = {row["employee_id"] for row in ranked[:alert_count]}
    actual = {
        row["employee_id"] for row in rows
        if _parse_bool(row["predicted_anomaly"])
    }
    if actual != expected:
        raise ArtifactAuditError("fixed-budget predictions are not top-score selections")


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
            values = [float(row[column]) for row in rows if row[column] != ""]
            if f"{column}_scenario_count" in stored:
                if int(stored[f"{column}_scenario_count"]) != len(values):
                    raise ArtifactAuditError(
                        f"aggregate {column} eligibility count mismatch for {key}"
                    )
            if not values:
                if stored[f"{column}_mean"]:
                    raise ArtifactAuditError(
                        f"aggregate undefined {column} must be blank for {key}"
                    )
                continue
            actual = mean(values)
            if abs(float(stored[f"{column}_mean"]) - actual) > 1e-12:
                raise ArtifactAuditError(f"aggregate {column} mismatch for {key}")


def _verify_paired_comparisons(
    metric_rows: list[dict[str, str]],
    paired_rows: list[dict[str, str]],
) -> dict[str, Any]:
    stored_columns = set(paired_rows[0]) if paired_rows else set()
    audited_metrics = (
        tuple(
            metric for metric in PAIR_METRICS
            if f"{metric}_scenario_count" in stored_columns
        )
        if paired_rows
        else PAIR_METRICS
    )
    missing_legacy = [
        metric for metric in LEGACY_AUDITED_PAIR_METRICS
        if metric not in audited_metrics
    ]
    if missing_legacy:
        raise ArtifactAuditError(
            "paired comparison schema omits required legacy metrics: "
            + ", ".join(missing_legacy)
        )
    include_declared_plan = "comparison_role" in stored_columns
    condition_aware = "inference_unit" in stored_columns
    expected = _recompute_paired_comparisons(
        metric_rows,
        include_declared_plan=include_declared_plan,
        pair_metrics=audited_metrics,
        condition_aware=condition_aware,
    )
    if len(expected) != len(paired_rows):
        raise ArtifactAuditError("paired comparison groups do not match scenario metrics")
    stored_keys = [
        (row["method"], row["operating_point"]) for row in paired_rows
    ]
    if len(set(stored_keys)) != len(stored_keys):
        raise ArtifactAuditError("duplicate paired comparison rows")
    stored_by_key = {
        (row["method"], row["operating_point"]): row
        for row in paired_rows
    }
    for item in expected:
        key = (str(item["method"]), str(item["operating_point"]))
        stored = stored_by_key.get(key)
        if stored is None:
            raise ArtifactAuditError(f"missing paired comparison for {key}")
        for column, actual in item.items():
            if column in {"method", "operating_point"}:
                continue
            if actual == "":
                if stored[column] != "":
                    raise ArtifactAuditError(f"paired {column} must be blank for {key}")
                continue
            if column in {
                "method", "operating_point", "comparison_role",
                "primary_endpoint", "inference_unit",
            } or column.endswith("_condition_seed_counts"):
                if stored[column] != str(actual):
                    raise ArtifactAuditError(f"paired {column} mismatch for {key}")
            elif column in {
                "scenario_count", "condition_count",
                "secondary_family_declared_size",
                "secondary_family_tested_size",
            } or column.endswith("_condition_count"):
                if int(stored[column]) != actual:
                    raise ArtifactAuditError(f"paired {column} mismatch for {key}")
            elif abs(_parse_float(stored[column], column) - float(actual)) > 1e-12:
                raise ArtifactAuditError(f"paired {column} mismatch for {key}")
    unavailable_metrics = [
        metric for metric in PAIR_METRICS if metric not in audited_metrics
    ]
    return {
        "audited_metrics": list(audited_metrics),
        "unavailable_newer_metrics": unavailable_metrics,
        "declared_plan_columns_present": include_declared_plan,
    }


def _verify_truth_sidecars(
    run_dir: Path,
    prediction_rows: list[dict[str, str]],
    *,
    required: bool = False,
    protocol_version: str = "",
    artifact_schema_version: int = 0,
) -> dict[str, Any]:
    names = (
        "record_truth.csv",
        "administrative_events.csv",
        "policy_epochs.csv",
    )
    if artifact_schema_version >= 5:
        names += ("entitlement_evidence.csv",)
    if artifact_schema_version >= 6:
        names += ("temporal_view_evaluations.csv",)
    existing = [name for name in names if (run_dir / name).is_file()]
    if not existing:
        if required:
            raise ArtifactAuditError("required truth sidecars are missing")
        return {"present": False}
    if len(existing) != len(names):
        raise ArtifactAuditError("truth sidecar set is incomplete")

    truth_rows = _read_csv(run_dir / names[0])
    event_rows = _read_csv(run_dir / names[1])
    policy_rows = _read_csv(run_dir / names[2])
    entitlement_rows = (
        _read_csv(run_dir / "entitlement_evidence.csv")
        if artifact_schema_version >= 5 else []
    )
    if artifact_schema_version >= 6:
        temporal_rows = _read_csv(run_dir / "temporal_view_evaluations.csv")
    else:
        temporal_rows = []
    truth_keys = [(row["scenario_id"], row["employee_id"]) for row in truth_rows]
    if len(set(truth_keys)) != len(truth_keys):
        raise ArtifactAuditError("duplicate record truth rows")
    truth_key_set = set(truth_keys)
    prediction_keys = {
        (row["scenario_id"], row["employee_id"]) for row in prediction_rows
    }
    if not prediction_keys.issubset(truth_key_set):
        raise ArtifactAuditError("predictions reference employees missing from record truth")
    if truth_rows and "evaluation_eligible" in truth_rows[0]:
        eligible_test_keys = {
            (row["scenario_id"], row["employee_id"])
            for row in truth_rows
            if row["split"] == "test" and _parse_bool(row["evaluation_eligible"])
        }
        ineligible_keys = {
            (row["scenario_id"], row["employee_id"])
            for row in truth_rows
            if not _parse_bool(row["evaluation_eligible"])
        }
        if prediction_keys & ineligible_keys:
            raise ArtifactAuditError(
                "evaluation-ineligible employees appear in predictions"
            )
        if prediction_keys != eligible_test_keys:
            raise ArtifactAuditError(
                "prediction membership does not match eligible test truth"
            )

    require_bitemporal = _requires_bitemporal_contract(
        protocol_version,
        artifact_schema_version,
    )
    policy_keys = [(
        row["scenario_id"],
        row["policy_id"],
        row.get("policy_version", "") if require_bitemporal else "",
    ) for row in policy_rows]
    if len(set(policy_keys)) != len(policy_keys):
        raise ArtifactAuditError("duplicate policy epoch rows")
    policy_key_set = set(policy_keys)
    policy_by_key = {}
    for row in policy_rows:
        effective_from = _parse_iso_date(row["effective_from"], "policy effective_from")
        if require_bitemporal:
            required_columns = {
                "policy_version", "effective_to", "recorded_at", "jurisdiction"
            }
            if not required_columns.issubset(row):
                raise ArtifactAuditError("bitemporal policy columns are incomplete")
            effective_to = (
                _parse_iso_date(row["effective_to"], "policy effective_to")
                if row["effective_to"] else None
            )
            recorded_at = _parse_iso_date(row["recorded_at"], "policy recorded_at")
            if effective_to is not None and effective_to < effective_from:
                raise ArtifactAuditError("policy effective interval is reversed")
            if not row["policy_version"] or not row["jurisdiction"]:
                raise ArtifactAuditError("policy version or jurisdiction is empty")
            policy_by_key[(
                row["scenario_id"], row["policy_id"], row["policy_version"]
            )] = {
                "policy_version": row["policy_version"],
                "effective_from": effective_from,
                "effective_to": effective_to,
                "recorded_at": recorded_at,
                "jurisdiction": row["jurisdiction"],
                "grandfather": _parse_bool(row["grandfather_previous_policy"]),
            }
        try:
            service = json.loads(row["service_months_by_level_json"])
        except json.JSONDecodeError as exc:
            raise ArtifactAuditError("invalid policy service mapping JSON") from exc
        if not isinstance(service, dict) or not service:
            raise ArtifactAuditError("policy service mapping is empty")

    if require_bitemporal:
        epochs_by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (scenario_id, _, _), epoch in policy_by_key.items():
            epochs_by_scenario[scenario_id].append(epoch)
        for scenario_id, epochs in epochs_by_scenario.items():
            ordered = sorted(epochs, key=lambda epoch: epoch["effective_from"])
            for previous, current in zip(ordered, ordered[1:]):
                previous_end = previous["effective_to"]
                if previous_end is None or current["effective_from"] <= previous_end:
                    raise ArtifactAuditError(
                        f"policy epochs overlap in {scenario_id}"
                    )
                if (current["effective_from"] - previous_end).days != 1:
                    raise ArtifactAuditError(
                        f"policy epochs have a gap in {scenario_id}"
                    )

    event_keys = set()
    events_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    events_by_employee: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in event_rows:
        employee_key = (row["scenario_id"], row["employee_id"])
        if employee_key not in truth_key_set:
            raise ArtifactAuditError("event references employee missing from record truth")
        policy_key = (
            row["scenario_id"],
            row["policy_id"],
            row.get("policy_version", "") if require_bitemporal else "",
        )
        if policy_key not in policy_key_set:
            raise ArtifactAuditError("event references unknown policy epoch")
        event_key = (row["scenario_id"], row["employee_id"], row["event_id"])
        if event_key in event_keys:
            raise ArtifactAuditError("duplicate administrative event rows")
        event_keys.add(event_key)
        events_by_key[event_key] = row
        events_by_employee[employee_key].append(row)
        effective_date = _parse_iso_date(row["effective_date"], "event effective_date")
        recorded_date = _parse_iso_date(row["recorded_date"], "event recorded_date")
        if recorded_date < effective_date:
            raise ArtifactAuditError("event was recorded before it became effective")
        if require_bitemporal:
            for column in (
                "recognized_service_months",
                "jurisdiction",
                "approval_status",
                "retry_of_event_id",
                "policy_version",
            ):
                if column not in row:
                    raise ArtifactAuditError("bitemporal event columns are incomplete")
            if int(row["recognized_service_months"]) < 0:
                raise ArtifactAuditError("recognized service cannot be negative")
            policy_epoch = policy_by_key[policy_key]
            in_interval = (
                policy_epoch["effective_from"] <= effective_date
                and (
                    policy_epoch["effective_to"] is None
                    or effective_date <= policy_epoch["effective_to"]
                )
            )
            if not in_interval and not policy_epoch["grandfather"]:
                raise ArtifactAuditError("event policy is not effective for event date")
            if policy_epoch["recorded_at"] > recorded_date:
                raise ArtifactAuditError("event uses a policy version not yet recorded")
            if row["jurisdiction"] != policy_epoch["jurisdiction"]:
                raise ArtifactAuditError("event and policy jurisdictions differ")
            if row["approval_status"] not in {"approved", "bypassed"}:
                raise ArtifactAuditError("event approval status is invalid")
            if (
                row["approval_status"] == "bypassed"
                and row["approval_reference"]
            ):
                raise ArtifactAuditError("bypassed event retains approval evidence")
        if row["resolved_date"]:
            _parse_iso_date(row["resolved_date"], "event resolved_date")
        if row["category"]:
            int(row["category"])

    entitlement_by_event: dict[tuple[str, str, str], dict[str, str]] = {}
    entitlement_ids: set[tuple[str, str]] = set()
    for row in entitlement_rows:
        entitlement_id = (row["scenario_id"], row["entitlement_id"])
        if entitlement_id in entitlement_ids:
            raise ArtifactAuditError("duplicate entitlement evidence ID")
        entitlement_ids.add(entitlement_id)
        employee_key = (row["scenario_id"], row["employee_id"])
        if employee_key not in truth_key_set:
            raise ArtifactAuditError("entitlement references unknown employee")
        event_key = (
            row["scenario_id"],
            row["employee_id"],
            row["relevant_event_id"],
        )
        event = events_by_key.get(event_key)
        if event is None:
            raise ArtifactAuditError("entitlement references unknown employee event")
        policy = policy_by_key.get((
            row["scenario_id"], row["policy_id"], row["policy_version"]
        ))
        if policy is None or policy["policy_version"] != row["policy_version"]:
            raise ArtifactAuditError("entitlement references unknown policy version")
        if not row["evidence_reference"]:
            raise ArtifactAuditError("entitlement evidence reference is empty")
        recorded_at = _parse_iso_date(row["recorded_at"], "entitlement recorded_at")
        event_recorded_at = _parse_iso_date(
            event["recorded_date"], "event recorded_date"
        )
        if recorded_at > event_recorded_at:
            raise ArtifactAuditError("entitlement was not known when event was recorded")
        if event_key in entitlement_by_event:
            raise ArtifactAuditError("multiple entitlement records reference one event")
        entitlement_by_event[event_key] = row

    if artifact_schema_version >= 5:
        for event_key, event in events_by_key.items():
            policy = policy_by_key[(
                event["scenario_id"],
                event["policy_id"],
                event["policy_version"],
            )]
            effective_date = _parse_iso_date(
                event["effective_date"], "event effective_date"
            )
            in_interval = (
                policy["effective_from"] <= effective_date
                and (
                    policy["effective_to"] is None
                    or effective_date <= policy["effective_to"]
                )
            )
            if not in_interval and policy["grandfather"]:
                entitlement = entitlement_by_event.get(event_key)
                if entitlement is None:
                    raise ArtifactAuditError(
                        "out-of-interval policy use lacks event-linked entitlement"
                    )
                if (
                    entitlement["policy_id"] != event["policy_id"]
                    or entitlement["policy_version"] != event["policy_version"]
                ):
                    raise ArtifactAuditError(
                        "entitlement policy does not match the relevant event"
                    )

    if artifact_schema_version >= 6:
        _verify_temporal_view_rows(
            temporal_rows,
            events_by_key,
            events_by_employee,
        )

    for row in event_rows:
        correction_id = row.get("correction_of_event_id", "")
        retry_id = row.get("retry_of_event_id", "")
        if correction_id and retry_id:
            raise ArtifactAuditError("event cannot be both a correction and a retry")
        if correction_id and (
            row["scenario_id"], row["employee_id"], correction_id
        ) not in events_by_key:
            raise ArtifactAuditError("event correction target does not exist")
        if retry_id and (
            row["scenario_id"], row["employee_id"], retry_id
        ) not in events_by_key:
            raise ArtifactAuditError("event retry target does not exist")

    for row in truth_rows:
        if not row["truth_category"] or not row["realized_mechanism"]:
            raise ArtifactAuditError("record truth category or realized mechanism is empty")
        if row["employment_track"] not in {"progression", "increment_only"}:
            raise ArtifactAuditError("record truth has unknown employment track")
        if row["split"] not in {"train", "validation", "test"}:
            raise ArtifactAuditError("record truth has unknown split")
        if row["employment_track"] == "progression" and not row["current_level"]:
            raise ArtifactAuditError("progression record has no current level")
        if row["employment_track"] == "increment_only" and row["current_level"]:
            raise ArtifactAuditError("increment-only record unexpectedly has a level")
        _parse_iso_date(row["date_of_birth"], "employee date_of_birth")
        _parse_iso_date(row["hire_date"], "employee hire_date")
        if not row["department"] or not row["role"]:
            raise ArtifactAuditError("record truth employee context is incomplete")
        employee_key = (row["scenario_id"], row["employee_id"])
        employee_events = events_by_employee.get(employee_key, [])
        if int(row["event_count"]) != len(employee_events):
            raise ArtifactAuditError("employee event count does not match event ledger")
        if row["event_ledger_sha256"] != _event_rows_sha256(employee_events):
            raise ArtifactAuditError("employee event ledger checksum mismatch")
        try:
            causal_events = json.loads(row["causal_events_json"])
        except json.JSONDecodeError as exc:
            raise ArtifactAuditError("invalid causal event JSON") from exc
        if not isinstance(causal_events, list):
            raise ArtifactAuditError("causal events must be a JSON list")
        for event in causal_events:
            required = {
                "event_id", "kind", "policy_id", "effective_date", "recorded_date",
                "category", "resolved_date", "approval_reference",
                "correction_of_event_id", "level_before", "level_after", "ledger_status",
            }
            if not isinstance(event, dict) or not required.issubset(event):
                raise ArtifactAuditError("causal event evidence is incomplete")
            if require_bitemporal and not event.get("policy_version"):
                raise ArtifactAuditError("causal event policy version is missing")
            causal_policy_key = (
                row["scenario_id"],
                str(event["policy_id"]),
                str(event.get("policy_version", "")) if require_bitemporal else "",
            )
            if causal_policy_key not in policy_key_set:
                raise ArtifactAuditError("causal event references unknown policy epoch")
            _parse_iso_date(str(event["effective_date"]), "causal effective_date")
            _parse_iso_date(str(event["recorded_date"]), "causal recorded_date")
            if event["resolved_date"] is not None:
                _parse_iso_date(str(event["resolved_date"]), "causal resolved_date")
            if event["ledger_status"] not in {"observed", "omitted"}:
                raise ArtifactAuditError("causal event has unknown ledger status")
            event_key = (row["scenario_id"], row["employee_id"], str(event["event_id"]))
            ledger_event = events_by_key.get(event_key)
            if event["ledger_status"] == "omitted":
                if ledger_event is not None:
                    raise ArtifactAuditError("omitted causal event is present in event ledger")
                continue
            if ledger_event is None:
                raise ArtifactAuditError("observed causal event is missing from event ledger")
            expected = {
                "event_kind": str(event["kind"]),
                "policy_id": str(event["policy_id"]),
                "effective_date": str(event["effective_date"]),
                "recorded_date": str(event["recorded_date"]),
                "category": "" if event["category"] is None else str(event["category"]),
                "resolved_date": "" if event["resolved_date"] is None else str(event["resolved_date"]),
                "approval_reference": "" if event["approval_reference"] is None else str(event["approval_reference"]),
                "correction_of_event_id": "" if event["correction_of_event_id"] is None else str(event["correction_of_event_id"]),
                "level_before": "" if event["level_before"] is None else str(event["level_before"]),
                "level_after": "" if event["level_after"] is None else str(event["level_after"]),
            }
            if require_bitemporal:
                expected["policy_version"] = str(event["policy_version"])
            if any(ledger_event[field] != value for field, value in expected.items()):
                raise ArtifactAuditError("causal event does not match event ledger")

    forbidden_prediction_fields = {
        "truth_category",
        "realized_mechanism",
        "employment_track",
        "causal_evidence",
        "causal_events_json",
    }
    for row in prediction_rows:
        if forbidden_prediction_fields.intersection(row):
            raise ArtifactAuditError("truth-only fields leaked into prediction rows")
    return {
        "present": True,
        "artifact_schema_version": artifact_schema_version,
        "policy_event_version_links_verified": require_bitemporal,
        "legacy_schema_limitations": (
            [
                "event-level policy versions are unavailable in schema-v3 sidecars",
                "employee-linked entitlement and temporal views are unavailable",
            ]
            if artifact_schema_version < 5
            else []
        ),
        "record_truth_rows": len(truth_rows),
        "administrative_event_rows": len(event_rows),
        "policy_epoch_rows": len(policy_rows),
        "entitlement_evidence_rows": len(entitlement_rows),
        "temporal_view_rows": len(temporal_rows),
    }


def _requires_bitemporal_contract(
    protocol_version: str,
    artifact_schema_version: int,
) -> bool:
    return (
        artifact_schema_version >= 5
        and protocol_version.startswith("independent-")
    )


def _verify_temporal_view_rows(
    rows: list[dict[str, str]],
    events_by_key: dict[tuple[str, str, str], dict[str, str]],
    events_by_employee: dict[tuple[str, str], list[dict[str, str]]],
) -> None:
    if not rows:
        raise ArtifactAuditError("temporal-view artifact rows are missing")
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row["scenario_id"],
            row["employee_id"],
            row["decision_event_id"],
        )
        event = events_by_key.get(key)
        if event is None or event["event_kind"] != "promotion":
            raise ArtifactAuditError(
                "temporal view references an unknown non-promotion decision"
            )
        decision_date = _parse_iso_date(
            row["decision_effective_date"], "temporal decision date"
        )
        if decision_date != _parse_iso_date(
            event["effective_date"], "event effective date"
        ):
            raise ArtifactAuditError("temporal decision date does not match event")
        if _parse_iso_date(row["effective_through"], "effective through") != decision_date:
            raise ArtifactAuditError("temporal views do not share the decision horizon")
        visible_ids = json.loads(row["visible_event_ids_json"])
        effective_ids = json.loads(row["effective_event_ids_json"])
        if not isinstance(visible_ids, list) or not isinstance(effective_ids, list):
            raise ArtifactAuditError("temporal event identifiers are not JSON lists")
        if int(row["visible_event_count"]) != len(visible_ids):
            raise ArtifactAuditError("temporal visible-event count mismatch")
        if int(row["effective_event_count"]) != len(effective_ids):
            raise ArtifactAuditError("temporal effective-event count mismatch")
        employee_events = {
            item["event_id"]: item
            for item in events_by_employee[(row["scenario_id"], row["employee_id"])]
        }
        if not set(visible_ids).issubset(employee_events):
            raise ArtifactAuditError("temporal view contains an unknown event")
        if not set(effective_ids).issubset(visible_ids):
            raise ArtifactAuditError("effective temporal events are not visible")
        if int(row["promotion_assessment_count"]) < 0:
            raise ArtifactAuditError("temporal assessment count is negative")
        if int(row["total_service_deficit_months"]) < 0:
            raise ArtifactAuditError("temporal service deficit is negative")
        grouped[key].append(row)

    for key, pair in grouped.items():
        by_view = {row["view_identifier"]: row for row in pair}
        if set(by_view) != {"known_then", "later_review"} or len(pair) != 2:
            raise ArtifactAuditError(f"temporal view pair is incomplete for {key}")
        decision_date = _parse_iso_date(
            by_view["known_then"]["decision_effective_date"],
            "temporal decision date",
        )
        if _parse_iso_date(
            by_view["known_then"]["recorded_through"], "known-then cutoff"
        ) != decision_date:
            raise ArtifactAuditError("known-then knowledge cutoff is incorrect")
        later_cutoff = _parse_iso_date(
            by_view["later_review"]["recorded_through"], "later-review cutoff"
        )
        if later_cutoff < decision_date:
            raise ArtifactAuditError("later-review cutoff precedes decision")
        known_ids = json.loads(by_view["known_then"]["visible_event_ids_json"])
        employee_events = {
            item["event_id"]: item
            for item in events_by_employee[(key[0], key[1])]
        }
        if any(
            _parse_iso_date(employee_events[event_id]["recorded_date"], "recorded date")
            > decision_date
            for event_id in known_ids
        ):
            raise ArtifactAuditError("later knowledge leaked into known-then view")


def _event_rows_sha256(rows: list[dict[str, str]]) -> str:
    canonical = sorted(rows, key=lambda row: row["event_id"])
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _recompute_paired_comparisons(
    rows: list[dict[str, str]],
    *,
    include_declared_plan: bool = False,
    pair_metrics: tuple[str, ...] = PAIR_METRICS,
    condition_aware: bool = False,
) -> list[dict[str, object]]:
    metric_keys = [
        (row["scenario_id"], row["method"], row["representation"], row["operating_point"])
        for row in rows
    ]
    if len(set(metric_keys)) != len(metric_keys):
        raise ArtifactAuditError("duplicate metric rows prevent paired comparison")
    indexed = {key: row for key, row in zip(metric_keys, rows)}
    methods = sorted({row["method"] for row in rows if row["method"] != "deterministic_rules"})
    operating_points = sorted({
        row["operating_point"] for row in rows if row["method"] != "deterministic_rules"
    })
    comparisons: list[dict[str, object]] = []
    for method in methods:
        for operating_point in operating_points:
            relevant_scenarios = sorted({
                row["scenario_id"] for row in rows
                if row["method"] == method
                and row["operating_point"] == operating_point
                and row["representation"] in {"raw_matched", "policy_matched"}
            })
            pairs = []
            for scenario_id in relevant_scenarios:
                raw = indexed.get((scenario_id, method, "raw_matched", operating_point))
                policy = indexed.get((scenario_id, method, "policy_matched", operating_point))
                if raw is None or policy is None:
                    raise ArtifactAuditError(
                        f"incomplete raw/policy pair for {(scenario_id, method, operating_point)}"
                    )
                pairs.append((raw, policy))
            if not pairs:
                continue
            item: dict[str, object] = {
                "method": method,
                "operating_point": operating_point,
                "scenario_count": len(pairs),
            }
            if condition_aware:
                item["condition_count"] = len({
                    _condition_id(raw["scenario_id"])
                    for raw, _ in pairs
                })
                item["inference_unit"] = "scenario_seed_condition_stratified"
            is_primary = (method, operating_point) == PRIMARY_COMPARISON
            if include_declared_plan:
                item["comparison_role"] = (
                    "primary_raw_vs_policy" if is_primary else "exploratory"
                )
                item["primary_endpoint"] = PRIMARY_ENDPOINT if is_primary else ""
                item["secondary_family_declared_size"] = (
                    len(SECONDARY_COMPARISON_METRICS) if is_primary else 0
                )
                item["secondary_family_tested_size"] = 0
                item["primary_recall_sign_flip_p"] = ""
            for metric in pair_metrics:
                eligible_pairs = [
                    (raw, policy) for raw, policy in pairs
                    if raw[metric] != "" and policy[metric] != ""
                ]
                deltas_by_condition: dict[str, list[float]] = defaultdict(list)
                for raw, policy in eligible_pairs:
                    deltas_by_condition[_condition_id(raw["scenario_id"])].append(
                        _parse_float(policy[metric], metric)
                        - _parse_float(raw[metric], metric)
                    )
                deltas = [
                    value
                    for condition_values in deltas_by_condition.values()
                    for value in condition_values
                ]
                item[f"{metric}_scenario_count"] = len(deltas)
                if condition_aware:
                    item[f"{metric}_condition_count"] = len(deltas_by_condition)
                if not deltas:
                    for suffix in (
                        "delta_mean", "delta_median", "delta_std",
                        "delta_ci95_low", "delta_ci95_high",
                        "delta_sign_flip_p",
                    ):
                        item[f"{metric}_{suffix}"] = ""
                    if include_declared_plan:
                        item[f"{metric}_delta_holm_all_p"] = ""
                        item[f"{metric}_delta_holm_secondary_p"] = ""
                    if condition_aware:
                        item[f"{metric}_condition_seed_counts"] = ""
                    continue
                prefix = f"{metric}_delta"
                if condition_aware:
                    summary = _audit_condition_balanced_summary(
                        deltas_by_condition,
                        _stable_seed(method, operating_point, metric),
                    )
                    item[f"{prefix}_mean"] = summary["mean"]
                    item[f"{prefix}_median"] = summary["median"]
                    item[f"{prefix}_std"] = summary["std"]
                    item[f"{prefix}_ci95_low"] = summary["ci_low"]
                    item[f"{prefix}_ci95_high"] = summary["ci_high"]
                    item[f"{prefix}_sign_flip_p"] = summary["sign_flip_p"]
                    item[f"{metric}_condition_seed_counts"] = "|".join(
                        str(value) for value in summary["seed_counts"]
                    )
                else:
                    ci_low, ci_high = _bootstrap_mean_ci(
                        deltas, _stable_seed(method, operating_point, metric)
                    )
                    item[f"{prefix}_mean"] = mean(deltas)
                    item[f"{prefix}_median"] = median(deltas)
                    item[f"{prefix}_std"] = stdev(deltas) if len(deltas) > 1 else 0.0
                    item[f"{prefix}_ci95_low"] = ci_low
                    item[f"{prefix}_ci95_high"] = ci_high
                    item[f"{prefix}_sign_flip_p"] = _paired_sign_flip_pvalue(
                        deltas, _stable_seed("sign", method, operating_point, metric)
                    )
                if include_declared_plan:
                    item[f"{metric}_delta_holm_all_p"] = ""
                    item[f"{metric}_delta_holm_secondary_p"] = ""
            comparisons.append(item)
    pvalue_locations = [
        (item, f"{metric}_delta_sign_flip_p")
        for item in comparisons
        for metric in LEGACY_AUDITED_PAIR_METRICS
        if metric in pair_metrics
        if item.get(f"{metric}_delta_sign_flip_p") not in {"", None}
    ]
    adjusted = _holm_adjusted_pvalues([
        float(item[key]) for item, key in pvalue_locations
    ])
    for (item, key), value in zip(pvalue_locations, adjusted):
        item[key.replace("_sign_flip_p", "_holm_all_p")] = value
    if include_declared_plan:
        primary_rows = [
            item for item in comparisons
            if (item["method"], item["operating_point"]) == PRIMARY_COMPARISON
        ]
        if len(primary_rows) > 1:
            raise ArtifactAuditError("primary comparison is not unique")
        if primary_rows:
            primary = primary_rows[0]
            locations = [
                (metric, f"{metric}_delta_sign_flip_p")
                for metric in SECONDARY_COMPARISON_METRICS
                if primary.get(f"{metric}_delta_sign_flip_p") not in {"", None}
            ]
            adjusted_secondary = _holm_adjusted_pvalues([
                float(primary[key]) for _, key in locations
            ])
            for (metric, _), value in zip(locations, adjusted_secondary):
                primary[f"{metric}_delta_holm_secondary_p"] = value
            primary["secondary_family_tested_size"] = len(locations)
            primary["primary_recall_sign_flip_p"] = primary.get(
                "recall_delta_sign_flip_p",
                "",
            )
    return comparisons


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


def _parse_float(value: str, column: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ArtifactAuditError(f"invalid numeric value in {column}: {value}") from exc
    if not isfinite(parsed):
        raise ArtifactAuditError(f"non-finite numeric value in {column}: {value}")
    return parsed


def _parse_iso_date(value: str, column: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ArtifactAuditError(f"invalid ISO date in {column}: {value}") from exc


def _average_precision(y_true: list[bool], scores: list[float]) -> float:
    if not any(y_true):
        return 0.0
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y_true, scores))


def _stable_seed(*parts: str) -> int:
    digest = sha256(":".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _condition_id(scenario_id: str) -> str:
    return scenario_id.rsplit("-seed-", 1)[0]


def _audit_condition_balanced_summary(
    deltas_by_condition: dict[str, list[float]],
    seed: int,
    bootstrap_samples: int = 10000,
    sign_flip_samples: int = 100000,
) -> dict[str, object]:
    """Independently reproduce condition-balanced paired inference."""

    import numpy as np

    ordered = [
        np.asarray(deltas_by_condition[key], dtype=float)
        for key in sorted(deltas_by_condition)
    ]
    condition_count = len(ordered)
    rng = np.random.default_rng(seed)
    selected_conditions = rng.integers(
        0,
        condition_count,
        size=(bootstrap_samples, condition_count),
    )
    sampled_means = np.empty_like(selected_conditions, dtype=float)
    for slot in range(condition_count):
        for condition_index, values in enumerate(ordered):
            selected_rows = np.flatnonzero(
                selected_conditions[:, slot] == condition_index
            )
            if selected_rows.size == 0:
                continue
            seed_indices = rng.integers(
                0,
                values.size,
                size=(selected_rows.size, values.size),
            )
            sampled_means[selected_rows, slot] = values[seed_indices].mean(axis=1)
    bootstrap_effects = sampled_means.mean(axis=1)
    ci_low, ci_high = np.quantile(bootstrap_effects, (0.025, 0.975))

    weighted = np.concatenate([
        values / (condition_count * values.size)
        for values in ordered
    ])
    nonzero = weighted[np.abs(weighted) > 1e-15]
    if nonzero.size == 0:
        sign_flip_p = 1.0
    else:
        observed = abs(float(nonzero.sum()))
        if nonzero.size <= 18:
            statistics = (
                abs(sum(sign * value for sign, value in zip(signs, nonzero)))
                for signs in product((-1.0, 1.0), repeat=int(nonzero.size))
            )
            total = 2 ** int(nonzero.size)
            sign_flip_p = (
                sum(value >= observed - 1e-15 for value in statistics) / total
            )
        else:
            signs = rng.choice((-1.0, 1.0), size=(sign_flip_samples, nonzero.size))
            statistics = np.abs(signs @ nonzero)
            extreme = int(np.count_nonzero(statistics >= observed - 1e-15))
            sign_flip_p = (extreme + 1) / (sign_flip_samples + 1)

    condition_means = [float(values.mean()) for values in ordered]
    return {
        "mean": mean(condition_means),
        "median": median(condition_means),
        "std": stdev(condition_means) if condition_count > 1 else 0.0,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "sign_flip_p": sign_flip_p,
        "seed_counts": tuple(int(values.size) for values in ordered),
    }


def _bootstrap_mean_ci(
    values: list[float],
    seed: int,
    samples: int = 10000,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    import numpy as np

    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    sampled = data[rng.integers(0, data.size, size=(samples, data.size))]
    means = sampled.mean(axis=1)
    low, high = np.quantile(means, (0.025, 0.975))
    return float(low), float(high)


def _paired_sign_flip_pvalue(
    values: list[float],
    seed: int,
    samples: int = 100000,
) -> float:
    import numpy as np

    magnitudes = np.asarray(
        [abs(value) for value in values if abs(value) > 1e-15], dtype=float
    )
    if magnitudes.size == 0:
        return 1.0
    observed = abs(sum(values))
    if magnitudes.size <= 18:
        statistics = (
            abs(sum(sign * magnitude for sign, magnitude in zip(signs, magnitudes)))
            for signs in product((-1.0, 1.0), repeat=int(magnitudes.size))
        )
        total = 2 ** int(magnitudes.size)
        return sum(value >= observed - 1e-15 for value in statistics) / total
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(samples, magnitudes.size))
    statistics = np.abs(signs @ magnitudes)
    extreme = int(np.count_nonzero(statistics >= observed - 1e-15))
    return (extreme + 1) / (samples + 1)


def _holm_adjusted_pvalues(pvalues: list[float]) -> list[float]:
    if any(value < 0 or value > 1 for value in pvalues):
        raise ArtifactAuditError("p-values must be between zero and one")
    order = sorted(range(len(pvalues)), key=lambda index: pvalues[index])
    adjusted = [1.0] * len(pvalues)
    running_max = 0.0
    total = len(pvalues)
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, (total - rank) * pvalues[index]))
        adjusted[index] = running_max
    return adjusted


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
