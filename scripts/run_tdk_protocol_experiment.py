"""Run the locked-holdout TDK v2 development or validation protocol."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_tdk_research_experiment import _provenance
from src.services.anomaly_detection.protocol_evaluation import evaluate_scenario
from src.services.anomaly_detection.scenario_generation import (
    ScenarioConfig,
    generate_scenario_dataset,
    scenario_matrix,
)


PROTOCOL_VERSION = "draft-v2.4-2026-10-16"
PROTOCOL_STATUS = "draft_validation_holdout_locked"
ANALYSIS_PLAN_VERSION = "approved-evaluation-v1-2026-10-30"
MIN_SEEDS_PER_CONDITION = 30
PRIMARY_COMPARISON = (
    "rule_negative_isolation_forest",
    "fixed_review_budget",
)
PRIMARY_ENDPOINT = "recall"
SECONDARY_COMPARISON_METRICS = (
    "average_precision",
    "precision",
    "false_positives",
    "false_positive_rate",
    "rare_legitimate_flagged_rate",
    "ordinary_clean_flagged_rate",
    "anomalies_found_per_100_reviews",
    "rare_legitimate_reviews_per_1000_employees",
    "missed_anomalies_per_1000_employees",
    "inconsistent_dates_recall",
    "frequent_promotions_recall",
    "excessive_sanctions_recall",
    "unusual_admin_interval_recall",
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
SUMMARY_METRICS = (
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
    "runtime_ms",
)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MyHR TDK v2 protocol.")
    parser.add_argument(
        "--run-purpose",
        required=True,
        choices=("development", "validation", "holdout"),
    )
    parser.add_argument(
        "--scenario-count",
        type=int,
        default=30,
        help="Number of predeclared condition cells before seed replication.",
    )
    parser.add_argument("--seeds-per-condition", type=int, default=30)
    parser.add_argument(
        "--seed-count-justification",
        default="",
        help="Required written justification when using fewer than 30 seeds per condition.",
    )
    parser.add_argument("--employee-count", type=int, default=600)
    parser.add_argument("--review-budget", type=float, default=0.10)
    parser.add_argument("--target-validation-fpr", type=float, default=0.05)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs") / "protocol_v2",
    )
    args = parser.parse_args()
    if args.run_purpose == "holdout":
        raise RuntimeError("Holdout execution is locked while the protocol status is draft")

    _validate_seed_replication(
        args.seeds_per_condition,
        args.seed_count_justification,
    )

    condition_configs = scenario_matrix(
        args.run_purpose,
        args.scenario_count,
        args.employee_count,
    )
    configs = _replicate_scenario_configs(
        condition_configs,
        args.seeds_per_condition,
    )
    provenance = _provenance()
    identity = {
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "analysis_plan_version": ANALYSIS_PLAN_VERSION,
        "run_purpose": args.run_purpose,
        "scenario_configs": [asdict(config) for config in configs],
        "review_budget": args.review_budget,
        "target_validation_fpr": args.target_validation_fpr,
        "seeds_per_condition": args.seeds_per_condition,
        "seed_count_justification": args.seed_count_justification.strip(),
        "source_sha256": provenance["source_sha256"],
    }
    artifact_id = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    metric_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    dataset_rows: list[dict[str, object]] = []
    for config in configs:
        scenario = generate_scenario_dataset(config)
        evaluation = evaluate_scenario(
            scenario,
            review_budget=args.review_budget,
            target_validation_fpr=args.target_validation_fpr,
        )
        metric_rows.extend(evaluation.metric_rows)
        prediction_rows.extend(evaluation.prediction_rows)
        dataset_rows.append({
            **asdict(config),
            "condition_id": _condition_id(config.scenario_id),
            "seed_replicate": _seed_replicate(config.scenario_id),
            "dataset_run_id": scenario.dataset.metadata.run_id,
            "schema_version": scenario.dataset.metadata.schema_version,
            "split_counts_json": json.dumps(scenario.dataset.metadata.split_counts, sort_keys=True),
            "label_counts_json": json.dumps(scenario.dataset.metadata.label_counts, sort_keys=True),
            "policy_json": json.dumps(asdict(scenario.policy), sort_keys=True),
            "population_json": json.dumps(asdict(scenario.population), sort_keys=True),
        })

    aggregate_rows = _aggregate_rows(metric_rows)
    comparison_rows = _paired_comparisons(metric_rows)
    robustness_rows = _robustness_slices(metric_rows)
    utility_rows = _utility_sensitivity(metric_rows)
    run_dir = args.output_dir / f"{args.run_purpose}_{artifact_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "title": "MyHR TDK v2 policy-aware anomaly-detection protocol",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_id": artifact_id,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "analysis_plan_version": ANALYSIS_PLAN_VERSION,
        "holdout_accessed": False,
        "run_purpose": args.run_purpose,
        "condition_count": len(condition_configs),
        "scenario_count": len(configs),
        "seeds_per_condition": args.seeds_per_condition,
        "minimum_seeds_per_condition": MIN_SEEDS_PER_CONDITION,
        "seed_count_justification": args.seed_count_justification.strip(),
        "employee_count_per_scenario": args.employee_count,
        "review_budget": args.review_budget,
        "target_validation_fpr": args.target_validation_fpr,
        "analysis_plan": {
            "primary_method": PRIMARY_COMPARISON[0],
            "primary_operating_point": PRIMARY_COMPARISON[1],
            "primary_endpoint": PRIMARY_ENDPOINT,
            "secondary_comparison_family": list(SECONDARY_COMPARISON_METRICS),
            "secondary_multiplicity_adjustment": "Holm",
            "zero_positive_treatment": (
                "Retain scenario; recall and average precision are undefined and "
                "excluded only from their paired inference."
            ),
        },
        "provenance": provenance,
        "interpretation_warning": (
            "Development and validation outputs are protocol checks, not final holdout evidence."
        ),
    }
    _write_json(run_dir / "metadata.json", metadata)
    _write_csv(run_dir / "scenario_configs.csv", dataset_rows)
    _write_csv(run_dir / "scenario_metrics.csv", metric_rows)
    _write_csv(run_dir / "record_predictions.csv", prediction_rows)
    _write_csv(run_dir / "aggregate_metrics.csv", aggregate_rows)
    _write_csv(run_dir / "paired_comparisons.csv", comparison_rows)
    _write_csv(run_dir / "robustness_slices.csv", robustness_rows)
    _write_csv(run_dir / "utility_sensitivity.csv", utility_rows)
    _write_readme(run_dir, metadata)
    _write_manifest(run_dir)
    print(json.dumps({
        "artifact_id": artifact_id,
        "output_dir": str(run_dir),
        "scenario_count": len(configs),
        "metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "holdout_accessed": False,
    }, indent=2, sort_keys=True))


def _validate_seed_replication(
    seeds_per_condition: int,
    justification: str,
) -> None:
    if seeds_per_condition < 1:
        raise ValueError("seeds_per_condition must be positive")
    if (
        seeds_per_condition < MIN_SEEDS_PER_CONDITION
        and not justification.strip()
    ):
        raise ValueError(
            "fewer than 30 seeds per condition requires a written justification"
        )


def _replicate_scenario_configs(
    conditions: tuple[ScenarioConfig, ...],
    seeds_per_condition: int,
) -> tuple[ScenarioConfig, ...]:
    if seeds_per_condition < 1:
        raise ValueError("seeds_per_condition must be positive")
    replicated = []
    for condition in conditions:
        for replicate_index in range(seeds_per_condition):
            offset = replicate_index * 1_000_003
            config = replace(
                condition,
                scenario_id=(
                    f"{condition.scenario_id}-seed-{replicate_index + 1:02d}"
                ),
                dataset_seed=condition.dataset_seed + offset,
                split_seed=condition.split_seed + offset,
                model_seed=condition.model_seed + offset,
            )
            config.validate()
            replicated.append(config)
    return tuple(replicated)


def _condition_id(scenario_id: str) -> str:
    return scenario_id.rsplit("-seed-", 1)[0]


def _seed_replicate(scenario_id: str) -> int:
    return int(scenario_id.rsplit("-seed-", 1)[1])


def _aggregate_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["method"]), str(row["representation"]), str(row["operating_point"]))].append(row)
    output = []
    for (method, representation, operating_point), group in sorted(groups.items()):
        item: dict[str, object] = {
            "method": method,
            "representation": representation,
            "operating_point": operating_point,
            "scenario_count": len(group),
        }
        for metric in SUMMARY_METRICS:
            values = [
                float(row[metric]) for row in group
                if row.get(metric) not in {"", None}
            ]
            item[f"{metric}_scenario_count"] = len(values)
            if not values:
                for suffix in ("mean", "median", "std", "ci95_low", "ci95_high"):
                    item[f"{metric}_{suffix}"] = ""
                continue
            ci_low, ci_high = _bootstrap_mean_ci(values, seed=_stable_seed(method, representation, operating_point, metric))
            item[f"{metric}_mean"] = mean(values)
            item[f"{metric}_median"] = median(values)
            item[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
            item[f"{metric}_ci95_low"] = ci_low
            item[f"{metric}_ci95_high"] = ci_high
        for column in COUNT_COLUMNS:
            item[f"{column}_total"] = sum(int(row[column]) for row in group)
        output.append(item)
    return output


def _paired_comparisons(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    indexed = {
        (str(row["scenario_id"]), str(row["method"]), str(row["representation"]), str(row["operating_point"])): row
        for row in rows
    }
    comparisons = []
    methods = sorted({str(row["method"]) for row in rows if row["method"] != "deterministic_rules"})
    operating_points = sorted({str(row["operating_point"]) for row in rows if row["method"] != "deterministic_rules"})
    scenario_ids = sorted({str(row["scenario_id"]) for row in rows})
    for method in methods:
        for operating_point in operating_points:
            pairs = []
            for scenario_id in scenario_ids:
                raw = indexed.get((scenario_id, method, "raw_matched", operating_point))
                policy = indexed.get((scenario_id, method, "policy_matched", operating_point))
                if raw is not None and policy is not None:
                    pairs.append((raw, policy))
            if not pairs:
                continue
            item: dict[str, object] = {
                "method": method,
                "operating_point": operating_point,
                "scenario_count": len(pairs),
            }
            is_primary_comparison = (method, operating_point) == PRIMARY_COMPARISON
            item["comparison_role"] = (
                "primary_raw_vs_policy" if is_primary_comparison else "exploratory"
            )
            item["primary_endpoint"] = (
                PRIMARY_ENDPOINT if is_primary_comparison else ""
            )
            item["secondary_family_declared_size"] = (
                len(SECONDARY_COMPARISON_METRICS) if is_primary_comparison else 0
            )
            item["secondary_family_tested_size"] = 0
            item["primary_recall_sign_flip_p"] = ""
            for metric in PAIR_METRICS:
                eligible_pairs = [
                    (raw, policy) for raw, policy in pairs
                    if raw.get(metric) not in {"", None}
                    and policy.get(metric) not in {"", None}
                ]
                deltas = [
                    float(policy[metric]) - float(raw[metric])
                    for raw, policy in eligible_pairs
                ]
                item[f"{metric}_scenario_count"] = len(deltas)
                if not deltas:
                    for suffix in (
                        "delta_mean", "delta_median", "delta_std",
                        "delta_ci95_low", "delta_ci95_high",
                        "delta_sign_flip_p",
                    ):
                        item[f"{metric}_{suffix}"] = ""
                    item[f"{metric}_delta_holm_all_p"] = ""
                    item[f"{metric}_delta_holm_secondary_p"] = ""
                    continue
                ci_low, ci_high = _bootstrap_mean_ci(
                    deltas,
                    seed=_stable_seed(method, operating_point, metric),
                )
                item[f"{metric}_delta_mean"] = mean(deltas)
                item[f"{metric}_delta_median"] = median(deltas)
                item[f"{metric}_delta_std"] = stdev(deltas) if len(deltas) > 1 else 0.0
                item[f"{metric}_delta_ci95_low"] = ci_low
                item[f"{metric}_delta_ci95_high"] = ci_high
                item[f"{metric}_delta_sign_flip_p"] = _paired_sign_flip_pvalue(
                    deltas,
                    seed=_stable_seed("sign", method, operating_point, metric),
                )
                item[f"{metric}_delta_holm_all_p"] = ""
                item[f"{metric}_delta_holm_secondary_p"] = ""
            comparisons.append(item)
    pvalue_locations = [
        (item, f"{metric}_delta_sign_flip_p")
        for item in comparisons
        for metric in LEGACY_AUDITED_PAIR_METRICS
        if item.get(f"{metric}_delta_sign_flip_p") not in {"", None}
    ]
    adjusted = _holm_adjusted_pvalues([
        float(item[key]) for item, key in pvalue_locations
    ])
    for (item, key), adjusted_pvalue in zip(pvalue_locations, adjusted):
        item[key.replace("_sign_flip_p", "_holm_all_p")] = adjusted_pvalue

    primary_rows = [
        item for item in comparisons
        if (item["method"], item["operating_point"]) == PRIMARY_COMPARISON
    ]
    if len(primary_rows) > 1:
        raise ValueError("primary comparison must produce at most one row")
    if primary_rows:
        primary = primary_rows[0]
        secondary_locations = [
            (metric, f"{metric}_delta_sign_flip_p")
            for metric in SECONDARY_COMPARISON_METRICS
            if primary.get(f"{metric}_delta_sign_flip_p") not in {"", None}
        ]
        secondary_adjusted = _holm_adjusted_pvalues([
            float(primary[key]) for _, key in secondary_locations
        ])
        for (metric, _), adjusted_pvalue in zip(
            secondary_locations,
            secondary_adjusted,
        ):
            primary[f"{metric}_delta_holm_secondary_p"] = adjusted_pvalue
        primary["secondary_family_tested_size"] = len(secondary_locations)
        primary["primary_recall_sign_flip_p"] = primary.get(
            "recall_delta_sign_flip_p",
            "",
        )
    return comparisons


def _robustness_slices(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    dimensions = (
        "policy_profile",
        "population_profile",
        "anomaly_mechanism",
        "rare_pattern",
        "configured_anomaly_rate",
        "configured_rare_rate",
    )
    output = []
    for dimension in dimensions:
        groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            key = (
                str(row[dimension]),
                str(row["method"]),
                str(row["representation"]),
                str(row["operating_point"]),
            )
            groups[key].append(row)
        for (group_value, method, representation, operating_point), group in sorted(groups.items()):
            item: dict[str, object] = {
                "slice_dimension": dimension,
                "slice_value": group_value,
                "method": method,
                "representation": representation,
                "operating_point": operating_point,
                "scenario_count": len(group),
            }
            for metric in SUMMARY_METRICS[:-1]:
                values = [
                    float(row[metric]) for row in group
                    if row.get(metric) not in {"", None}
                ]
                item[f"{metric}_scenario_count"] = len(values)
                if values:
                    item[f"{metric}_mean"] = mean(values)
                    item[f"{metric}_min"] = min(values)
                    item[f"{metric}_max"] = max(values)
                else:
                    item[f"{metric}_mean"] = ""
                    item[f"{metric}_min"] = ""
                    item[f"{metric}_max"] = ""
            output.append(item)
    return output


def _utility_sensitivity(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    cost_profiles = (
        ("review_1_miss_2_rare_1", 1.0, 2.0, 1.0),
        ("review_1_miss_5_rare_2", 1.0, 5.0, 2.0),
        ("review_1_miss_10_rare_5", 1.0, 10.0, 5.0),
    )
    output = []
    for row in rows:
        for name, review_cost, miss_cost, rare_escalation_cost in cost_profiles:
            alerts = int(row["alert_count"])
            fp = int(row["false_positives"])
            fn = int(row["false_negatives"])
            rare = int(row["rare_legitimate_flagged"])
            output.append({
                "scenario_id": row["scenario_id"],
                "method": row["method"],
                "representation": row["representation"],
                "operating_point": row["operating_point"],
                "cost_profile": name,
                "review_cost": review_cost,
                "miss_cost": miss_cost,
                "rare_escalation_cost": rare_escalation_cost,
                "review_count": alerts,
                "false_positive_count": fp,
                "false_negative_count": fn,
                "rare_legitimate_flagged_count": rare,
                "total_cost": alerts * review_cost + fn * miss_cost + rare * rare_escalation_cost,
                "cost_per_1000_employees": 1000 * (
                    alerts * review_cost + fn * miss_cost + rare * rare_escalation_cost
                ) / int(row["evaluation_count"]),
            })
    return output


def _stable_seed(*parts: str) -> int:
    digest = sha256(":".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


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

    magnitudes = np.asarray([abs(value) for value in values if abs(value) > 1e-15], dtype=float)
    if magnitudes.size == 0:
        return 1.0
    observed = abs(sum(values))
    if magnitudes.size <= 18:
        statistics = (
            abs(sum(sign * magnitude for sign, magnitude in zip(signs, magnitudes)))
            for signs in product((-1.0, 1.0), repeat=int(magnitudes.size))
        )
        total = 2 ** int(magnitudes.size)
        return sum(statistic >= observed - 1e-15 for statistic in statistics) / total
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(samples, magnitudes.size))
    statistics = np.abs(signs @ magnitudes)
    extreme = int(np.count_nonzero(statistics >= observed - 1e-15))
    return (extreme + 1) / (samples + 1)


def _holm_adjusted_pvalues(pvalues: list[float]) -> list[float]:
    """Return Holm-adjusted p-values for one declared comparison family."""

    if any(value < 0 or value > 1 for value in pvalues):
        raise ValueError("p-values must be between zero and one")
    order = sorted(range(len(pvalues)), key=lambda index: pvalues[index])
    adjusted = [1.0] * len(pvalues)
    running_max = 0.0
    total = len(pvalues)
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, (total - rank) * pvalues[index]))
        adjusted[index] = running_max
    return adjusted


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(run_dir: Path, metadata: dict[str, Any]) -> None:
    (run_dir / "README.md").write_text(
        "\n".join((
            "# MyHR TDK v2 Protocol Artifact",
            "",
            f"Artifact ID: `{metadata['artifact_id']}`",
            f"Purpose: `{metadata['run_purpose']}`",
            f"Protocol: `{metadata['protocol_version']}`",
            f"Status: `{metadata['protocol_status']}`",
            "Holdout accessed: `false`",
            "",
            "This artifact contains scenario configuration, per-scenario metrics,",
            "per-record scores and predictions, paired comparisons, utility",
            "sensitivity, robustness slices, provenance, and file checksums.",
            "",
            "Development and validation results are not final holdout evidence.",
            "",
        )),
        encoding="utf-8",
    )


def _write_manifest(run_dir: Path) -> None:
    files = sorted(path for path in run_dir.iterdir() if path.is_file() and path.name != "manifest.json")
    _write_json(run_dir / "manifest.json", {
        "algorithm": "sha256",
        "files": {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in files
        },
    })


if __name__ == "__main__":
    main()
