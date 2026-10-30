"""Run independent development-only scenarios without accessing a holdout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
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
    IndependentEvent,
    IndependentWorld,
    TruthCategory,
    generate_independent_world,
    independent_scenario_matrix,
)
from src.services.anomaly_detection.protocol_evaluation import evaluate_scenario


PROTOCOL_VERSION = "independent-development-v2-2026-10-29"
PROTOCOL_STATUS = "draft_independent_development_holdout_locked"


@contextmanager
def _staged_artifact_directory(final_dir: Path) -> Iterator[Path]:
    """Publish a completed artifact atomically without exposing partial output."""
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(final_dir):
        raise FileExistsError(f"Artifact already exists: {final_dir}")

    staging_dir = Path(tempfile.mkdtemp(
        prefix=f".{final_dir.name}.staging-",
        dir=final_dir.parent,
    ))
    published = False
    try:
        yield staging_dir
        if os.path.lexists(final_dir):
            raise FileExistsError(f"Artifact already exists: {final_dir}")
        staging_dir.rename(final_dir)
        published = True
    finally:
        if not published and os.path.lexists(staging_dir):
            shutil.rmtree(staging_dir)


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
    final_dir = args.output_dir / f"independent_development_{artifact_id}"

    with _staged_artifact_directory(final_dir) as run_dir:
        metric_rows = []
        prediction_rows = []
        config_rows = []
        truth_rows = []
        event_rows = []
        policy_rows = []
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
            truth_rows.extend(_record_truth_rows(world))
            event_rows.extend(_event_ledger_rows(world))
            policy_rows.extend(_policy_epoch_rows(world))
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

        _require_primary_policy_signal(metric_rows)

        metadata = {
            "title": "MyHR independent development-only scenario evaluation",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifact_id": artifact_id,
            "protocol_version": PROTOCOL_VERSION,
            "protocol_status": PROTOCOL_STATUS,
            "holdout_accessed": False,
            "run_purpose": "development",
            "artifact_schema_version": 3,
            "truth_sidecars_required": True,
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
        _write_csv(run_dir / "record_truth.csv", truth_rows)
        _write_csv(run_dir / "administrative_events.csv", event_rows)
        _write_csv(run_dir / "policy_epochs.csv", policy_rows)
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
        "output_dir": str(final_dir),
        "scenario_count": len(specs),
        "metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "holdout_accessed": False,
    }, indent=2, sort_keys=True))


def _record_truth_rows(world: IndependentWorld) -> list[dict[str, object]]:
    employees = {employee.employee_id: employee for employee in world.employees}
    rows = []
    for truth in world.truth:
        employee = employees[truth.employee_id]
        ledger_events = [_event_row(world.spec.scenario_id, employee.employee_id, event)
                         for event in employee.events]
        observed_event_ids = {event.event_id for event in employee.events}
        causal_events = [{
            "event_id": event.event_id,
            "kind": event.kind.value,
            "policy_id": event.policy_id,
            "effective_date": event.effective_date.isoformat(),
            "recorded_date": event.recorded_date.isoformat(),
            "category": event.category,
            "resolved_date": (
                event.resolved_date.isoformat() if event.resolved_date else None
            ),
            "approval_reference": event.approval_reference,
            "approval_status": event.approval_status,
            "correction_of_event_id": event.correction_of_event_id,
            "retry_of_event_id": event.retry_of_event_id,
            "recognized_service_months": event.recognized_service_months,
            "jurisdiction": event.jurisdiction,
            "level_before": event.level_before,
            "level_after": event.level_after,
            "ledger_status": (
                "observed" if event.event_id in observed_event_ids else "omitted"
            ),
        } for event in truth.causal_events]
        rows.append({
            "scenario_id": world.spec.scenario_id,
            "employee_id": truth.employee_id,
            "split": employee.split.value,
            "truth_category": truth.category.value,
            "evaluation_eligible": (
                truth.category is not TruthCategory.AMBIGUOUS_REVIEW_CASE
            ),
            "evaluation_exclusion_reason": (
                "ambiguous_review_case"
                if truth.category is TruthCategory.AMBIGUOUS_REVIEW_CASE else ""
            ),
            "nominal_anomaly_mechanism": world.spec.mechanism,
            "nominal_rare_pattern": world.spec.rare_pattern,
            "realized_mechanism": truth.realized_mechanism,
            "employment_track": truth.track.value,
            "current_level": employee.current_level or "",
            "department": employee.department,
            "role": employee.role,
            "date_of_birth": employee.date_of_birth.isoformat(),
            "hire_date": employee.hire_date.isoformat(),
            "event_count": len(ledger_events),
            "event_ledger_sha256": _rows_sha256(ledger_events),
            "causal_evidence": truth.evidence,
            "causal_events_json": json.dumps(causal_events, sort_keys=True),
        })
    return rows


def _require_primary_policy_signal(rows: list[dict[str, object]]) -> None:
    primary_policy_rows = [
        row for row in rows
        if row["method"] == "rule_negative_isolation_forest"
        and row["representation"] == "policy_matched"
        and row["operating_point"] == "fixed_review_budget"
    ]
    if not primary_policy_rows:
        raise RuntimeError("primary policy-aware metric rows are missing")
    if not any(
        int(row.get("policy_signal_nonconstant_feature_count", 0)) > 0
        for row in primary_policy_rows
    ):
        raise RuntimeError(
            "primary policy-aware features are constant across every scenario"
        )


def _event_ledger_rows(world: IndependentWorld) -> list[dict[str, object]]:
    return [
        _event_row(world.spec.scenario_id, employee.employee_id, event)
        for employee in world.employees for event in employee.events
    ]


def _event_row(
    scenario_id: str,
    employee_id: str,
    event: IndependentEvent,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "employee_id": employee_id,
        "event_id": event.event_id,
        "event_kind": event.kind.value,
        "policy_id": event.policy_id,
        "effective_date": event.effective_date.isoformat(),
        "recorded_date": event.recorded_date.isoformat(),
        "approval_reference": event.approval_reference or "",
        "approval_status": event.approval_status,
        "correction_of_event_id": event.correction_of_event_id or "",
        "retry_of_event_id": event.retry_of_event_id or "",
        "recognized_service_months": event.recognized_service_months,
        "jurisdiction": event.jurisdiction,
        "level_before": event.level_before or "",
        "level_after": event.level_after or "",
        "category": "" if event.category is None else event.category,
        "resolved_date": event.resolved_date.isoformat() if event.resolved_date else "",
    }


def _rows_sha256(rows: list[dict[str, object]]) -> str:
    canonical = sorted(
        ({key: str(value) for key, value in row.items()} for row in rows),
        key=lambda row: row["event_id"],
    )
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _policy_epoch_rows(world: IndependentWorld) -> list[dict[str, object]]:
    return [{
        "scenario_id": world.spec.scenario_id,
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "effective_from": policy.effective_from.isoformat(),
        "effective_to": (
            policy.effective_to.isoformat() if policy.effective_to else ""
        ),
        "recorded_at": policy.recorded_at.isoformat(),
        "jurisdiction": policy.jurisdiction,
        "service_months_by_level_json": json.dumps(
            policy.service_months_by_level, sort_keys=True
        ),
        "grandfather_previous_policy": policy.grandfather_previous_policy,
    } for policy in world.policies]


if __name__ == "__main__":
    main()
