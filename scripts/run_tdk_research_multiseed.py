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
from pathlib import Path
from statistics import mean, stdev
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services.anomaly_detection import ExperimentConfig, generate_synthetic_dataset
from scripts.run_tdk_research_experiment import _duplicate_rows, _method_rows, _write_csv, _write_json


METRIC_COLUMNS = (
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "rare_legitimate_false_positives",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-seed MyHR TDK research evaluation.")
    parser.add_argument("--seeds", type=str, default="2026,2027,2028,2029,2030")
    parser.add_argument("--employee-count", type=int, default=1000)
    parser.add_argument("--anomaly-rate", type=float, default=0.10)
    parser.add_argument("--rare-legitimate-rate", type=float, default=0.05)
    parser.add_argument("--output-dir", type=Path, default=Path("research_outputs") / "multi_seed")
    args = parser.parse_args()

    seeds = _parse_seeds(args.seeds)
    run_dir = args.output_dir / _run_folder_name(seeds, args.employee_count)
    run_dir.mkdir(parents=True, exist_ok=True)

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
        "seeds": seeds,
        "employee_count": args.employee_count,
        "anomaly_rate": args.anomaly_rate,
        "rare_legitimate_rate": args.rare_legitimate_rate,
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


def _run_folder_name(seeds: list[int], employee_count: int) -> str:
    return f"seeds_{seeds[0]}_{seeds[-1]}_n{employee_count}_k{len(seeds)}"


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
        rare_fp_deltas: list[float] = []
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
            rare_fp_deltas.append(
                float(policy["rare_legitimate_false_positives"]) - float(raw["rare_legitimate_false_positives"])
            )
        total = raw_wins + policy_wins + ties
        comparisons.append({
            "method": method,
            "seed_count": total,
            "policy_f1_wins": policy_wins,
            "raw_f1_wins": raw_wins,
            "ties": ties,
            "policy_f1_win_rate": policy_wins / total if total else 0.0,
            "mean_precision_delta_policy_minus_raw": _safe_mean(precision_deltas),
            "mean_recall_delta_policy_minus_raw": _safe_mean(recall_deltas),
            "mean_f1_delta_policy_minus_raw": _safe_mean(f1_deltas),
            "mean_rare_legitimate_fp_delta_policy_minus_raw": _safe_mean(rare_fp_deltas),
        })
    return comparisons


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"seed_count": len(rows)}
    for metric in METRIC_COLUMNS:
        values = [float(row[metric]) for row in rows if metric in row and row[metric] != ""]
        summary[f"{metric}_mean"] = _safe_mean(values)
        summary[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
        summary[f"{metric}_min"] = min(values) if values else 0.0
        summary[f"{metric}_max"] = max(values) if values else 0.0
    return summary


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


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
