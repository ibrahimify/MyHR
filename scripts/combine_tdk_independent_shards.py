"""Combine complete, audited seed shards into one write-once research artifact."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_tdk_protocol_artifact import audit_artifact
from scripts.run_tdk_independent_development import (
    _require_primary_policy_signal,
    _staged_artifact_directory,
)
from scripts.run_tdk_protocol_experiment import (
    MIN_SEEDS_PER_CONDITION,
    _aggregate_rows,
    _paired_comparisons,
    _representation_control_contrasts,
    _robustness_slices,
    _utility_sensitivity,
    _write_csv,
    _write_json,
    _write_manifest,
)


RAW_FILES = (
    "scenario_configs.csv",
    "scenario_metrics.csv",
    "record_predictions.csv",
    "record_truth.csv",
    "administrative_events.csv",
    "policy_epochs.csv",
    "entitlement_evidence.csv",
    "temporal_view_evaluations.csv",
)
MODEL_RAW_FILES = (
    "model_comparison_metrics.csv",
    "model_comparison_predictions.csv",
)
IDENTITY_FIELDS = (
    "protocol_version",
    "protocol_status",
    "analysis_plan_version",
    "run_purpose",
    "generator_run_purpose",
    "design",
    "artifact_schema_version",
    "condition_count",
    "employee_count_per_scenario",
    "review_budget",
    "target_validation_fpr",
    "model_comparison_included",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shards", nargs="+", type=Path)
    parser.add_argument("--expected-seeds-per-condition", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs") / "independent_combined",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    if args.expected_seeds_per_condition < MIN_SEEDS_PER_CONDITION:
        raise ValueError(
            f"combined evidence requires at least {MIN_SEEDS_PER_CONDITION} seeds per condition"
        )

    shards = tuple(path.resolve() for path in args.shards)
    metadata_by_shard = []
    configs_by_shard = []
    for path in shards:
        audit_artifact(path, args.repo_root)
        metadata_by_shard.append(_read_json(path / "metadata.json"))
        configs_by_shard.append(_read_csv(path / "scenario_configs.csv"))
    base, combined_configs = _validate_shard_set(
        metadata_by_shard,
        configs_by_shard,
        expected_seeds_per_condition=args.expected_seeds_per_condition,
    )

    metric_rows = [
        row
        for shard in shards
        for row in _read_csv(shard / "scenario_metrics.csv")
    ]
    include_models = base["model_comparison_included"] is True
    if include_models:
        model_metrics = [
            row
            for shard in shards
            for row in _read_csv(shard / "model_comparison_metrics.csv")
        ]

    artifact_identity = {
        "source_revision": base["provenance"]["git_commit"],
        "input_artifact_ids": sorted(item["artifact_id"] for item in metadata_by_shard),
        "expected_seeds_per_condition": args.expected_seeds_per_condition,
        "scenario_ids": sorted(row["scenario_id"] for row in combined_configs),
    }
    artifact_id = sha256(
        json.dumps(artifact_identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    final_dir = (
        args.output_dir
        / f"{base['generator_run_purpose']}_combined_{artifact_id}"
    )
    metadata = dict(base)
    provenance = dict(base["provenance"])
    provenance["command"] = [sys.executable, *sys.argv]
    provenance["combined_input_artifact_ids"] = artifact_identity[
        "input_artifact_ids"
    ]
    metadata.update({
        "title": "MyHR combined independent scenario evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_id": artifact_id,
        "scenario_count": len(combined_configs),
        "seeds_per_condition": args.expected_seeds_per_condition,
        "seed_replicate_start": 1,
        "minimum_seeds_per_condition": MIN_SEEDS_PER_CONDITION,
        "seed_count_justification": "",
        "combined_from_artifact_ids": artifact_identity["input_artifact_ids"],
        "provenance": provenance,
        "interpretation_warning": (
            "Combined development or validation evidence is not a final holdout."
        ),
    })

    _require_primary_policy_signal(metric_rows)
    with _staged_artifact_directory(final_dir) as run_dir:
        _write_json(run_dir / "metadata.json", metadata)
        for name in RAW_FILES:
            if name == "scenario_configs.csv":
                _write_csv(run_dir / name, combined_configs)
            elif name == "scenario_metrics.csv":
                _write_csv(run_dir / name, metric_rows)
            else:
                _concatenate_csv_files(
                    run_dir / name,
                    tuple(shard / name for shard in shards),
                )
        _write_csv(run_dir / "aggregate_metrics.csv", _aggregate_rows(metric_rows))
        _write_csv(run_dir / "paired_comparisons.csv", _paired_comparisons(metric_rows))
        _write_csv(run_dir / "robustness_slices.csv", _robustness_slices(metric_rows))
        _write_csv(run_dir / "utility_sensitivity.csv", _utility_sensitivity(metric_rows))

        if include_models:
            for name in MODEL_RAW_FILES:
                if name == "model_comparison_metrics.csv":
                    _write_csv(run_dir / name, model_metrics)
                else:
                    _concatenate_csv_files(
                        run_dir / name,
                        tuple(shard / name for shard in shards),
                    )
            _write_csv(
                run_dir / "model_comparison_aggregates.csv",
                _aggregate_rows(model_metrics),
            )
            _write_csv(
                run_dir / "model_comparison_paired.csv",
                _paired_comparisons(model_metrics),
            )
            _write_csv(
                run_dir / "model_comparison_control_contrasts.csv",
                _representation_control_contrasts(model_metrics),
            )
            _write_csv(
                run_dir / "model_comparison_robustness.csv",
                _robustness_slices(model_metrics),
            )
        (run_dir / "README.md").write_text(
            "# Combined Independent Scenario Artifact\n\n"
            f"Artifact ID: `{artifact_id}`\n\n"
            f"Purpose: `{base['run_purpose']}`\n\n"
            f"Seeds per condition: `{args.expected_seeds_per_condition}`\n\n"
            "Every input shard passed the independent artifact audit. "
            "The final holdout was not accessed.\n",
            encoding="utf-8",
        )
        _write_manifest(run_dir)

    print(json.dumps({
        "artifact_id": artifact_id,
        "output_dir": str(final_dir),
        "condition_count": int(base["condition_count"]),
        "scenario_count": len(combined_configs),
        "seeds_per_condition": args.expected_seeds_per_condition,
        "holdout_accessed": False,
    }, indent=2, sort_keys=True))


def _validate_shard_set(
    metadata_by_shard: list[dict[str, Any]],
    configs_by_shard: list[list[dict[str, str]]],
    *,
    expected_seeds_per_condition: int,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not metadata_by_shard or len(metadata_by_shard) != len(configs_by_shard):
        raise ValueError("metadata and configuration shards must be non-empty and aligned")
    base = metadata_by_shard[0]
    if base.get("holdout_accessed") is not False:
        raise ValueError("input shard does not preserve the holdout lock")
    source_revision = base.get("provenance", {}).get("git_commit")
    provenance_fields = (
        "python_version",
        "platform",
        "packages",
        "source_sha256",
    )
    for metadata in metadata_by_shard[1:]:
        for field in IDENTITY_FIELDS:
            if metadata.get(field) != base.get(field):
                raise ValueError(f"input shards disagree on {field}")
        if metadata.get("provenance", {}).get("git_commit") != source_revision:
            raise ValueError("input shards were generated from different revisions")
        for field in provenance_fields:
            if metadata.get("provenance", {}).get(field) != base.get(
                "provenance", {}
            ).get(field):
                raise ValueError(
                    f"input shards were generated in different {field} environments"
                )
        if metadata.get("holdout_accessed") is not False:
            raise ValueError("input shard does not preserve the holdout lock")

    combined = [row for shard in configs_by_shard for row in shard]
    scenario_ids = [row["scenario_id"] for row in combined]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("input shards contain overlapping scenarios")
    by_condition: dict[str, set[int]] = defaultdict(set)
    for row in combined:
        by_condition[row["condition_id"]].add(int(row["seed_replicate"]))
    if len(by_condition) != int(base["condition_count"]):
        raise ValueError("input shards do not contain the declared condition set")
    expected = set(range(1, expected_seeds_per_condition + 1))
    for condition_id, replicates in by_condition.items():
        if replicates != expected:
            raise ValueError(
                f"seed replicates are incomplete for {condition_id}: "
                f"expected {sorted(expected)}, found {sorted(replicates)}"
            )
    return base, sorted(combined, key=lambda row: row["scenario_id"])


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _concatenate_csv_files(output: Path, inputs: tuple[Path, ...]) -> None:
    """Concatenate aligned CSV files without retaining record-level rows in memory."""
    if not inputs:
        raise ValueError("CSV concatenation requires at least one input")
    fieldnames: list[str] | None = None
    with output.open("w", newline="", encoding="utf-8") as destination:
        writer: csv.DictWriter[str] | None = None
        for path in inputs:
            with path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source)
                current = list(reader.fieldnames or ())
                if not current:
                    raise ValueError(f"CSV input has no header: {path}")
                if fieldnames is None:
                    fieldnames = current
                    writer = csv.DictWriter(destination, fieldnames=fieldnames)
                    writer.writeheader()
                elif current != fieldnames:
                    raise ValueError(f"CSV headers disagree for {path}")
                assert writer is not None
                writer.writerows(reader)


if __name__ == "__main__":
    main()
