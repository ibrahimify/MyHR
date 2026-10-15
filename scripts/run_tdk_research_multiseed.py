"""Run multiple reproducible TDK experiments and aggregate results.

This script is used to check whether observed method differences are stable
across seeds. It does not create final paper claims by itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from pathlib import Path
from random import Random
from statistics import mean, median, stdev
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services.anomaly_detection import ExperimentConfig, generate_synthetic_dataset
from scripts.run_tdk_research_experiment import (
    PROTOCOL_STATUS,
    PROTOCOL_VERSION,
    _duplicate_rows,
    _method_rows,
    _provenance,
    _write_csv,
    _write_json,
)


METRIC_COLUMNS = (
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "alert_rate",
    "rare_legitimate_false_positive_rate",
    "clean_false_positive_rate",
)

COUNT_COLUMNS = (
    "evaluation_count",
    "ground_truth_positive_count",
    "ground_truth_negative_count",
    "predicted_positive_count",
    "true_positives",
    "false_positives",
    "true_negatives",
    "false_negatives",
    "rare_legitimate_count",
    "rare_legitimate_false_positives",
    "clean_count",
    "clean_false_positives",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-seed MyHR TDK research evaluation.")
    parser.add_argument("--seeds", type=str, default="2026,2027,2028,2029,2030")
    parser.add_argument("--employee-count", type=int, default=1000)
    parser.add_argument("--anomaly-rate", type=float, default=0.10)
    parser.add_argument("--rare-legitimate-rate", type=float, default=0.05)
    parser.add_argument(
        "--run-purpose",
        choices=("development", "validation", "holdout"),
        default="development",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("research_outputs") / "multi_seed")
    args = parser.parse_args()

    if args.run_purpose == "holdout" and PROTOCOL_STATUS != "frozen":
        raise RuntimeError("Holdout execution is locked until the research protocol is frozen")

    seeds = _parse_seeds(args.seeds)
    provenance = _provenance()
    run_dir = args.output_dir / _run_folder_name(
        seeds=seeds,
        employee_count=args.employee_count,
        anomaly_rate=args.anomaly_rate,
        rare_legitimate_rate=args.rare_legitimate_rate,
        run_purpose=args.run_purpose,
        source_hashes=provenance["source_sha256"],
    )
    run_dir.mkdir(parents=True, exist_ok=False)

    method_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    metadata_rows: list[dict[str, Any]] = []

    for seed in seeds:
        config = ExperimentConfig(
            seed=seed,
            employee_count=args.employee_count,
            anomaly_rate=args.anomaly_rate,
            rare_legitimate_rate=args.rare_legitimate_rate,
        )
        dataset = generate_synthetic_dataset(config)
        metadata_rows.append({
            "seed": seed,
            "run_id": dataset.metadata.run_id,
            "employee_count": dataset.metadata.employee_count,
            "split_counts_json": json.dumps(dataset.metadata.split_counts, sort_keys=True),
            "label_counts_json": json.dumps(dataset.metadata.label_counts, sort_keys=True),
        })
        for row in _method_rows(dataset, config):
            method_rows.append({"seed": seed, "run_id": dataset.metadata.run_id, **row})
        seed_duplicate_rows, _ = _duplicate_rows(dataset)
        for row in seed_duplicate_rows:
            duplicate_rows.append({"seed": seed, "run_id": dataset.metadata.run_id, **row})

    aggregate_rows = _aggregate_method_rows(method_rows)
    duplicate_aggregate_rows = _aggregate_duplicate_rows(duplicate_rows)
    comparison_rows = _comparison_rows(method_rows)

    _write_json(run_dir / "metadata.json", {
        "title": "MyHR multi-seed TDK research evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "run_purpose": args.run_purpose,
        "seeds": seeds,
        "employee_count": args.employee_count,
        "anomaly_rate": args.anomaly_rate,
        "rare_legitimate_rate": args.rare_legitimate_rate,
        "provenance": provenance,
        "interpretation_warning": "Use these aggregates as stability evidence only after methodology review.",
    })
    _write_csv(run_dir / "seed_metadata.csv", metadata_rows)
    _write_csv(run_dir / "per_seed_method_metrics.csv", method_rows)
    _write_csv(run_dir / "aggregate_method_metrics.csv", aggregate_rows)
    _write_csv(run_dir / "per_seed_duplicate_metrics.csv", duplicate_rows)
    _write_csv(run_dir / "aggregate_duplicate_metrics.csv", duplicate_aggregate_rows)
    _write_csv(run_dir / "method_comparisons.csv", comparison_rows)
    _write_readme(run_dir, seeds, args.employee_count)

    print(json.dumps({
        "output_dir": str(run_dir),
        "seed_count": len(seeds),
        "method_rows": len(method_rows),
        "aggregate_rows": len(aggregate_rows),
        "comparison_rows": len(comparison_rows),
    }, indent=2, sort_keys=True))


def _parse_seeds(value: str) -> list[int]:
    seeds = [int(seed.strip()) for seed in value.split(",") if seed.strip()]
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def _run_folder_name(
    seeds: list[int],
    employee_count: int,
    anomaly_rate: float,
    rare_legitimate_rate: float,
    run_purpose: str,
    source_hashes: dict[str, str],
) -> str:
    identity = {
        "protocol_version": PROTOCOL_VERSION,
        "run_purpose": run_purpose,
        "seeds": seeds,
        "employee_count": employee_count,
        "anomaly_rate": anomaly_rate,
        "rare_legitimate_rate": rare_legitimate_rate,
        "source_sha256": source_hashes,
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{run_purpose}_n{employee_count}_k{len(seeds)}_{digest}"


def _aggregate_method_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["feature_set"])].append(row)
    return [
        {
            "task": "anomaly_detection",
            "method": method,
            "feature_set": feature_set,
            **_metric_summary(group),
        }
        for (method, feature_set), group in sorted(groups.items())
    ]


def _aggregate_duplicate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["method"]].append(row)
    return [
        {
            "task": "duplicate_detection",
            "method": method,
            **_metric_summary(group),
        }
        for method, group in sorted(groups.items())
    ]


def _comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seed: dict[int, dict[tuple[str, str], dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_seed[int(row["seed"])][(row["method"], row["feature_set"])] = row

    comparisons = []
    for method in ("iqr", "z_score", "isolation_forest"):
        raw_wins = policy_wins = ties = 0
        precision_deltas: list[float] = []
        recall_deltas: list[float] = []
        f1_deltas: list[float] = []
        fpr_deltas: list[float] = []
        rare_fp_rate_deltas: list[float] = []
        clean_fp_rate_deltas: list[float] = []
        for seed, seed_rows in by_seed.items():
            raw = seed_rows.get((method, "raw"))
            policy = seed_rows.get((method, "policy_aware"))
            if raw is None or policy is None:
                continue
            raw_f1 = float(raw["f1"])
            policy_f1 = float(policy["f1"])
            if policy_f1 > raw_f1:
                policy_wins += 1
            elif raw_f1 > policy_f1:
                raw_wins += 1
            else:
                ties += 1
            precision_deltas.append(float(policy["precision"]) - float(raw["precision"]))
            recall_deltas.append(float(policy["recall"]) - float(raw["recall"]))
            f1_deltas.append(policy_f1 - raw_f1)
            fpr_deltas.append(float(policy["false_positive_rate"]) - float(raw["false_positive_rate"]))
            rare_fp_rate_deltas.append(
                float(policy["rare_legitimate_false_positive_rate"])
                - float(raw["rare_legitimate_false_positive_rate"])
            )
            clean_fp_rate_deltas.append(
                float(policy["clean_false_positive_rate"])
                - float(raw["clean_false_positive_rate"])
            )
        total = raw_wins + policy_wins + ties
        comparison = {
            "method": method,
            "seed_count": total,
            "policy_f1_wins": policy_wins,
            "raw_f1_wins": raw_wins,
            "ties": ties,
            "policy_f1_win_rate": policy_wins / total if total else 0.0,
            "mean_precision_delta_policy_minus_raw": _safe_mean(precision_deltas),
            "mean_recall_delta_policy_minus_raw": _safe_mean(recall_deltas),
            "mean_f1_delta_policy_minus_raw": _safe_mean(f1_deltas),
            "mean_false_positive_rate_delta_policy_minus_raw": _safe_mean(fpr_deltas),
            "mean_rare_legitimate_fp_rate_delta_policy_minus_raw": _safe_mean(rare_fp_rate_deltas),
            "mean_clean_fp_rate_delta_policy_minus_raw": _safe_mean(clean_fp_rate_deltas),
        }
        for index, (name, values) in enumerate((
            ("precision_delta_policy_minus_raw", precision_deltas),
            ("recall_delta_policy_minus_raw", recall_deltas),
            ("f1_delta_policy_minus_raw", f1_deltas),
            ("false_positive_rate_delta_policy_minus_raw", fpr_deltas),
            ("rare_legitimate_fp_rate_delta_policy_minus_raw", rare_fp_rate_deltas),
            ("clean_fp_rate_delta_policy_minus_raw", clean_fp_rate_deltas),
        )):
            comparison.update(_paired_difference_summary(name, values, seed=20261015 + index))
        comparisons.append(comparison)
    return comparisons


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"seed_count": len(rows)}
    for metric in METRIC_COLUMNS:
        values = [float(row[metric]) for row in rows if metric in row and row[metric] != ""]
        if not values:
            continue
        summary[f"{metric}_mean"] = _safe_mean(values)
        summary[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
        summary[f"{metric}_min"] = min(values)
        summary[f"{metric}_max"] = max(values)
    for column in COUNT_COLUMNS:
        values = [int(row[column]) for row in rows if column in row and row[column] != ""]
        if values:
            summary[f"{column}_total"] = sum(values)
    if "true_positives_total" in summary:
        tp = summary["true_positives_total"]
        fp = summary["false_positives_total"]
        tn = summary["true_negatives_total"]
        fn = summary["false_negatives_total"]
        pooled_precision = _safe_ratio(tp, tp + fp)
        pooled_recall = _safe_ratio(tp, tp + fn)
        summary["precision_pooled"] = pooled_precision
        summary["recall_pooled"] = pooled_recall
        summary["f1_pooled"] = _safe_ratio(
            2 * pooled_precision * pooled_recall,
            pooled_precision + pooled_recall,
        )
        summary["false_positive_rate_pooled"] = _safe_ratio(fp, fp + tn)
    if "evaluation_count_total" in summary:
        summary["alert_rate_pooled"] = _safe_ratio(
            summary.get("predicted_positive_count_total", 0),
            summary["evaluation_count_total"],
        )
    if "rare_legitimate_count_total" in summary:
        summary["rare_legitimate_false_positive_rate_pooled"] = _safe_ratio(
            summary.get("rare_legitimate_false_positives_total", 0),
            summary["rare_legitimate_count_total"],
        )
    if "clean_count_total" in summary:
        summary["clean_false_positive_rate_pooled"] = _safe_ratio(
            summary.get("clean_false_positives_total", 0),
            summary["clean_count_total"],
        )
    return summary


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _paired_difference_summary(name: str, values: list[float], seed: int) -> dict[str, float]:
    ci_low, ci_high = _bootstrap_mean_ci(values, seed=seed)
    return {
        f"median_{name}": median(values) if values else 0.0,
        f"{name}_std": stdev(values) if len(values) > 1 else 0.0,
        f"{name}_bootstrap_ci95_low": ci_low,
        f"{name}_bootstrap_ci95_high": ci_high,
        f"{name}_sign_flip_p": _paired_sign_flip_pvalue(values, seed=seed),
    }


def _bootstrap_mean_ci(values: list[float], seed: int, samples: int = 10000) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = Random(seed)
    size = len(values)
    bootstrap_means = sorted(
        mean(values[rng.randrange(size)] for _ in range(size))
        for _ in range(samples)
    )
    return (
        _percentile(bootstrap_means, 0.025),
        _percentile(bootstrap_means, 0.975),
    )


def _paired_sign_flip_pvalue(values: list[float], seed: int, samples: int = 100000) -> float:
    magnitudes = [abs(value) for value in values if abs(value) > 1e-15]
    if not magnitudes:
        return 1.0
    observed = abs(sum(values))
    if len(magnitudes) <= 18:
        statistics = (
            abs(sum(sign * magnitude for sign, magnitude in zip(signs, magnitudes)))
            for signs in product((-1.0, 1.0), repeat=len(magnitudes))
        )
        total = 2 ** len(magnitudes)
        extreme = sum(statistic >= observed - 1e-15 for statistic in statistics)
        return extreme / total

    rng = Random(seed)
    extreme = 0
    for _ in range(samples):
        statistic = abs(sum((1.0 if rng.random() >= 0.5 else -1.0) * value for value in magnitudes))
        extreme += statistic >= observed - 1e-15
    return (extreme + 1) / (samples + 1)


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


def _write_readme(run_dir: Path, seeds: list[int], employee_count: int) -> None:
    (run_dir / "README.md").write_text(
        "\n".join([
            "# MyHR Multi-Seed Research Evaluation",
            "",
            f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
            f"Employee count per seed: `{employee_count}`",
            "",
            "Files:",
            "",
            "- `metadata.json`: multi-seed configuration.",
            "- `seed_metadata.csv`: per-seed run IDs and label counts.",
            "- `per_seed_method_metrics.csv`: anomaly-detection metrics for each seed.",
            "- `aggregate_method_metrics.csv`: mean/std/min/max anomaly-detection metrics.",
            "- `per_seed_duplicate_metrics.csv`: duplicate-detection metrics for each seed.",
            "- `aggregate_duplicate_metrics.csv`: mean/std/min/max duplicate metrics.",
            "- `method_comparisons.csv`: raw vs policy-aware deltas and win rates.",
            "",
            "Use these outputs as stability evidence, not as final claims until reviewed.",
            "",
        ]),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
