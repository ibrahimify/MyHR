"""Run independent development-only scenarios without accessing a holdout."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_tdk_protocol_experiment import (
    _aggregate_rows,
    _paired_comparisons,
    _robustness_slices,
    _utility_sensitivity,
    _write_csv,
    _write_json,
    _write_manifest,
)
from scripts.run_tdk_research_experiment import _provenance
from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    generate_independent_world,
    independent_scenario_matrix,
)
from src.services.anomaly_detection.protocol_evaluation import evaluate_scenario


PROTOCOL_VERSION = "independent-development-v1-2026-10-16"
PROTOCOL_STATUS = "draft_independent_development_holdout_locked"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employee-count", type=int, default=360)
    parser.add_argument("--review-budget", type=float, default=0.10)
    parser.add_argument("--target-validation-fpr", type=float, default=0.05)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs") / "independent_development",
    )
    args = parser.parse_args()
    specs = independent_scenario_matrix(args.employee_count)
    provenance = _provenance()
    identity = {
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "specs": [asdict(spec) for spec in specs],
        "review_budget": args.review_budget,
        "target_validation_fpr": args.target_validation_fpr,
        "source_sha256": provenance["source_sha256"],
    }
    artifact_id = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    run_dir = args.output_dir / f"independent_development_{artifact_id}"
    run_dir.mkdir(parents=True, exist_ok=False)

    metric_rows = []
    prediction_rows = []
    config_rows = []
    for spec in specs:
        world = generate_independent_world(spec)
        scenario = adapt_independent_world(world)
        evaluation = evaluate_scenario(
            scenario,
            review_budget=args.review_budget,
            target_validation_fpr=args.target_validation_fpr,
        )
        metric_rows.extend(evaluation.metric_rows)
        prediction_rows.extend(evaluation.prediction_rows)
        truth_counts = Counter(entry.category.value for entry in world.truth)
        config_rows.append({
            **asdict(spec),
            "truth_counts_json": json.dumps(dict(truth_counts), sort_keys=True),
            "policy_cards_json": json.dumps(
                [asdict(policy) for policy in world.policies],
                default=str,
                sort_keys=True,
            ),
        })

    metadata = {
        "title": "MyHR independent development-only scenario evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_id": artifact_id,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "holdout_accessed": False,
        "run_purpose": "development",
        "scenario_count": len(specs),
        "employee_count_per_scenario": args.employee_count,
        "review_budget": args.review_budget,
        "target_validation_fpr": args.target_validation_fpr,
        "provenance": provenance,
        "interpretation_warning": (
            "Independent scenarios are adversarial development evidence, not a final holdout."
        ),
    }
    _write_json(run_dir / "metadata.json", metadata)
    _write_csv(run_dir / "scenario_configs.csv", config_rows)
    _write_csv(run_dir / "scenario_metrics.csv", metric_rows)
    _write_csv(run_dir / "record_predictions.csv", prediction_rows)
    _write_csv(run_dir / "aggregate_metrics.csv", _aggregate_rows(metric_rows))
    _write_csv(run_dir / "paired_comparisons.csv", _paired_comparisons(metric_rows))
    _write_csv(run_dir / "robustness_slices.csv", _robustness_slices(metric_rows))
    _write_csv(run_dir / "utility_sensitivity.csv", _utility_sensitivity(metric_rows))
    (run_dir / "README.md").write_text(
        "# Independent Development Scenario Artifact\n\n"
        f"Artifact ID: `{artifact_id}`\n\n"
        "This artifact is development-only. The final holdout was not accessed.\n",
        encoding="utf-8",
    )
    _write_manifest(run_dir)
    print(json.dumps({
        "artifact_id": artifact_id,
        "output_dir": str(run_dir),
        "scenario_count": len(specs),
        "metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "holdout_accessed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
