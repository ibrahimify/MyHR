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
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_tdk_protocol_experiment import (
    ANALYSIS_PLAN_VERSION,
    MIN_SEEDS_PER_CONDITION,
    PRIMARY_COMPARISON,
    PRIMARY_ENDPOINT,
    SECONDARY_COMPARISON_METRICS,
    _aggregate_rows,
    _paired_comparisons,
    _representation_control_contrasts,
    _robustness_slices,
    _utility_sensitivity,
    _write_csv,
    _write_json,
    _write_manifest,
    _validate_seed_replication,
)
from scripts.run_tdk_research_experiment import _provenance
from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.holdout_gate import (
    HoldoutAttempt,
    begin_holdout_attempt,
    finalize_holdout_attempt,
)
from src.research.independent_scenarios import (
    IndependentEvent,
    IndependentScenarioSpec,
    IndependentWorld,
    REFERENCE_DATE,
    TruthCategory,
    generate_independent_world,
    independent_condition_matrix_sha256,
    independent_covering_scenario_matrix,
    independent_scenario_matrix,
)
from src.services.anomaly_detection.protocol_evaluation import (
    evaluate_residual_model_comparison,
    evaluate_scenario,
)
from src.services.anomaly_detection.synthetic_data import (
    AdministrativeEventType,
    DatasetSplit,
)
from src.services.anomaly_detection.temporal_diagnostics import (
    diagnose_temporal_views,
)


PROTOCOL_VERSION = "independent-scenarios-v3-2026-11-19"
HOLDOUT_PROTOCOL_VERSION = "myhr-tdk-holdout-v1"
HOLDOUT_MATRIX_CONFIG = REPO_ROOT / "config" / "tdk_holdout_matrix_v1.json"
HOLDOUT_LEDGER_ROOT = REPO_ROOT.parent / ".myhr-holdout-ledgers"
ARTIFACT_SCHEMA_VERSION = 8


def _artifact_schema_metadata() -> dict[str, int]:
    return {"artifact_schema_version": ARTIFACT_SCHEMA_VERSION}


@contextmanager
def _staged_artifact_directory(
    final_dir: Path,
    holdout_attempt: HoldoutAttempt | None = None,
) -> Iterator[Path]:
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
        if holdout_attempt:
            finalize_holdout_attempt(
                holdout_attempt,
                success=True,
                detail=f"published artifact {final_dir.name}",
            )
    except BaseException as exc:
        if holdout_attempt:
            try:
                finalize_holdout_attempt(
                    holdout_attempt,
                    success=False,
                    detail=f"artifact publication failed: {type(exc).__name__}",
                )
            except Exception as ledger_error:
                exc.add_note(f"holdout ledger finalization also failed: {ledger_error}")
        raise
    finally:
        if not published and os.path.lexists(staging_dir):
            shutil.rmtree(staging_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-purpose",
        choices=(
            "independent_development",
            "independent_validation",
            "independent_holdout",
        ),
        default="independent_development",
    )
    parser.add_argument(
        "--design",
        choices=("legacy", "covering"),
        default="legacy",
        help="Use the historical 12-cell diagnostic or proposed 36-cell covering design.",
    )
    parser.add_argument(
        "--include-model-comparison",
        action="store_true",
        help="Write the exploratory five-method residual comparison as separate files.",
    )
    parser.add_argument("--employee-count", type=int, default=360)
    parser.add_argument("--seeds-per-condition", type=int, default=30)
    parser.add_argument(
        "--seed-replicate-start",
        type=int,
        default=1,
        help="One-based first replicate index, used for resumable seed shards.",
    )
    parser.add_argument(
        "--seed-count-justification",
        default="",
        help="Required written justification when using fewer than 30 seeds per condition.",
    )
    parser.add_argument("--review-budget", type=float, default=0.10)
    parser.add_argument("--target-validation-fpr", type=float, default=0.05)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs") / "independent_development",
    )
    parser.add_argument(
        "--authorization-file",
        type=Path,
        help="Untracked frozen-protocol authorization record required for holdout.",
    )
    args = parser.parse_args()
    _validate_seed_replication(
        args.seeds_per_condition,
        args.seed_count_justification,
    )
    holdout_attempt = _begin_holdout_if_authorized(args)
    condition_specs = _select_independent_conditions(
        args.run_purpose,
        args.design,
        args.employee_count,
        holdout_attempt=holdout_attempt,
    )
    _verify_holdout_condition_matrix(args.run_purpose, condition_specs)
    specs = _replicate_independent_specs(
        condition_specs,
        args.seeds_per_condition,
        start_replicate=args.seed_replicate_start,
    )
    provenance = _provenance()
    protocol_status = _protocol_status(args.run_purpose)
    protocol_version = (
        HOLDOUT_PROTOCOL_VERSION
        if args.run_purpose == "independent_holdout"
        else PROTOCOL_VERSION
    )
    holdout_accessed = args.run_purpose == "independent_holdout"
    identity = {
        "protocol_version": protocol_version,
        "protocol_status": protocol_status,
        "analysis_plan_version": ANALYSIS_PLAN_VERSION,
        "specs": [asdict(spec) for spec in specs],
        "review_budget": args.review_budget,
        "target_validation_fpr": args.target_validation_fpr,
        "seeds_per_condition": args.seeds_per_condition,
        "seed_replicate_start": args.seed_replicate_start,
        "seed_count_justification": args.seed_count_justification.strip(),
        "run_purpose": args.run_purpose,
        "design": args.design,
        "include_model_comparison": args.include_model_comparison,
        "source_sha256": provenance["source_sha256"],
        "holdout_authorization_sha256": (
            holdout_attempt.authorization_sha256 if holdout_attempt else None
        ),
    }
    artifact_id = sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    final_dir = args.output_dir / f"{args.run_purpose}_{artifact_id}"

    with _staged_artifact_directory(final_dir, holdout_attempt) as run_dir:
        metric_rows = []
        prediction_rows = []
        config_rows = []
        truth_rows = []
        event_rows = []
        policy_rows = []
        entitlement_rows = []
        temporal_view_rows = []
        model_comparison_metric_rows = []
        model_comparison_prediction_rows = []
        for spec_index, spec in enumerate(specs, start=1):
            print(
                f"[{spec_index}/{len(specs)}] evaluating {spec.scenario_id}",
                flush=True,
            )
            world = generate_independent_world(
                spec,
                holdout_attempt=holdout_attempt,
            )
            scenario = adapt_independent_world(world)
            evaluation = evaluate_scenario(
                scenario,
                review_budget=args.review_budget,
                target_validation_fpr=args.target_validation_fpr,
            )
            metric_rows.extend(evaluation.metric_rows)
            prediction_rows.extend(evaluation.prediction_rows)
            if args.include_model_comparison:
                model_comparison = evaluate_residual_model_comparison(
                    scenario,
                    review_budget=args.review_budget,
                )
                model_comparison_metric_rows.extend(model_comparison.metric_rows)
                model_comparison_prediction_rows.extend(model_comparison.prediction_rows)
            truth_rows.extend(_record_truth_rows(world))
            event_rows.extend(_event_ledger_rows(world))
            policy_rows.extend(_policy_epoch_rows(world))
            entitlement_rows.extend(_entitlement_evidence_rows(world))
            temporal_view_rows.extend(_temporal_view_rows(scenario))
            truth_counts = Counter(entry.category.value for entry in world.truth)
            config_rows.append({
                **asdict(spec),
                "condition_id": _condition_id(spec.scenario_id),
                "seed_replicate": _seed_replicate(spec.scenario_id),
                "truth_counts_json": json.dumps(dict(truth_counts), sort_keys=True),
                "policy_cards_json": json.dumps(
                    [asdict(policy) for policy in world.policies],
                    default=str,
                    sort_keys=True,
                ),
            })

        _require_primary_policy_signal(metric_rows)

        metadata = {
            "title": "MyHR independent scenario evaluation",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifact_id": artifact_id,
            "protocol_version": protocol_version,
            "protocol_status": protocol_status,
            "holdout_accessed": holdout_accessed,
            "run_purpose": {
                "independent_development": "development",
                "independent_validation": "validation",
                "independent_holdout": "holdout",
            }[args.run_purpose],
            "generator_run_purpose": args.run_purpose,
            "design": args.design,
            **_artifact_schema_metadata(),
            "analysis_plan_version": ANALYSIS_PLAN_VERSION,
            "truth_sidecars_required": True,
            "condition_count": len(condition_specs),
            "scenario_count": len(specs),
            "seeds_per_condition": args.seeds_per_condition,
            "seed_replicate_start": args.seed_replicate_start,
            "minimum_seeds_per_condition": MIN_SEEDS_PER_CONDITION,
            "seed_count_justification": args.seed_count_justification.strip(),
            "employee_count_per_scenario": args.employee_count,
            "review_budget": args.review_budget,
            "target_validation_fpr": args.target_validation_fpr,
            "model_comparison_included": args.include_model_comparison,
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
            "holdout_gate": (
                {
                    "attempt_id": holdout_attempt.attempt_id,
                    "authorization_sha256": holdout_attempt.authorization_sha256,
                    "matrix_sha256": holdout_attempt.matrix_sha256,
                    "frozen_git_commit": holdout_attempt.frozen_git_commit,
                }
                if holdout_attempt else None
            ),
            "interpretation_warning": _interpretation_warning(args.run_purpose),
        }
        _write_json(run_dir / "metadata.json", metadata)
        _write_csv(run_dir / "scenario_configs.csv", config_rows)
        _write_csv(run_dir / "scenario_metrics.csv", metric_rows)
        _write_csv(run_dir / "record_predictions.csv", prediction_rows)
        _write_csv(run_dir / "record_truth.csv", truth_rows)
        _write_csv(run_dir / "administrative_events.csv", event_rows)
        _write_csv(run_dir / "policy_epochs.csv", policy_rows)
        _write_csv(run_dir / "entitlement_evidence.csv", entitlement_rows)
        _write_csv(run_dir / "temporal_view_evaluations.csv", temporal_view_rows)
        _write_csv(run_dir / "aggregate_metrics.csv", _aggregate_rows(metric_rows))
        _write_csv(run_dir / "paired_comparisons.csv", _paired_comparisons(metric_rows))
        _write_csv(run_dir / "robustness_slices.csv", _robustness_slices(metric_rows))
        _write_csv(run_dir / "utility_sensitivity.csv", _utility_sensitivity(metric_rows))
        if args.include_model_comparison:
            _write_csv(
                run_dir / "model_comparison_metrics.csv",
                model_comparison_metric_rows,
            )
            _write_csv(
                run_dir / "model_comparison_predictions.csv",
                model_comparison_prediction_rows,
            )
            _write_csv(
                run_dir / "model_comparison_aggregates.csv",
                _aggregate_rows(model_comparison_metric_rows),
            )
            _write_csv(
                run_dir / "model_comparison_paired.csv",
                _paired_comparisons(model_comparison_metric_rows),
            )
            _write_csv(
                run_dir / "model_comparison_control_contrasts.csv",
                _representation_control_contrasts(
                    model_comparison_metric_rows
                ),
            )
            _write_csv(
                run_dir / "model_comparison_robustness.csv",
                _robustness_slices(model_comparison_metric_rows),
            )
        (run_dir / "README.md").write_text(
            "# Independent Scenario Artifact\n\n"
            f"Artifact ID: `{artifact_id}`\n\n"
            f"Purpose: `{args.run_purpose}`\n\n"
            f"Design: `{args.design}`\n\n"
            + _artifact_boundary_text(args.run_purpose),
            encoding="utf-8",
        )
        _write_manifest(run_dir)

    print(json.dumps({
        "artifact_id": artifact_id,
        "output_dir": str(final_dir),
        "scenario_count": len(specs),
        "metric_rows": len(metric_rows),
        "prediction_rows": len(prediction_rows),
        "model_comparison_metric_rows": len(model_comparison_metric_rows),
        "holdout_accessed": holdout_accessed,
    }, indent=2, sort_keys=True))


def _select_independent_conditions(
    run_purpose: str,
    design: str,
    employee_count: int,
    *,
    holdout_attempt: HoldoutAttempt | None = None,
) -> tuple[IndependentScenarioSpec, ...]:
    if design == "legacy":
        if run_purpose != "independent_development":
            raise ValueError("the legacy diagnostic has no validation design")
        return independent_scenario_matrix(employee_count)
    if design == "covering":
        return independent_covering_scenario_matrix(
            run_purpose,
            employee_count,
            holdout_attempt=holdout_attempt,
        )
    raise ValueError(f"unknown independent design: {design}")


def _protocol_status(run_purpose: str) -> str:
    purpose = {
        "independent_development": "development",
        "independent_validation": "validation",
        "independent_holdout": "holdout",
    }.get(run_purpose)
    if purpose is None:
        raise ValueError(f"unsupported run purpose: {run_purpose}")
    if purpose == "holdout":
        return "frozen_independent_holdout"
    return f"draft_independent_{purpose}_holdout_locked"


def _begin_holdout_if_authorized(
    args: argparse.Namespace,
) -> HoldoutAttempt | None:
    if args.run_purpose != "independent_holdout":
        if args.authorization_file:
            raise ValueError("holdout authorization options require holdout purpose")
        return None
    if args.design != "covering":
        raise ValueError("the frozen holdout requires the covering design")
    if args.employee_count != 120 or args.seeds_per_condition != 30:
        raise ValueError("the frozen holdout requires 120 employees and 30 seeds per condition")
    if args.seed_replicate_start != 1:
        raise ValueError("the frozen holdout must begin at seed replicate 1")
    if args.review_budget != 0.10 or args.target_validation_fpr != 0.05:
        raise ValueError("the frozen holdout operating points do not match the protocol")
    if args.authorization_file is None:
        raise ValueError("holdout authorization file is required")

    matrix_config = json.loads(HOLDOUT_MATRIX_CONFIG.read_text(encoding="utf-8"))
    if matrix_config.get("status") != "frozen":
        raise ValueError("tracked holdout configuration is not frozen")
    if args.include_model_comparison is not matrix_config["include_model_comparison"]:
        raise ValueError("the holdout model-comparison setting does not match the protocol")
    environment_digest = sha256(
        (REPO_ROOT / "research-environment.json").read_bytes()
    ).hexdigest()
    lock_digest = sha256(
        (REPO_ROOT / "requirements-research-lock.txt").read_bytes()
    ).hexdigest()
    if environment_digest != matrix_config["research_environment_sha256"]:
        raise ValueError("research environment declaration differs from the frozen protocol")
    if lock_digest != matrix_config["dependency_lock_sha256"]:
        raise ValueError("dependency lock differs from the frozen protocol")
    expected_digest = str(matrix_config["condition_matrix_sha256"])
    return begin_holdout_attempt(
        args.authorization_file,
        HOLDOUT_LEDGER_ROOT / f"{matrix_config['protocol_id']}.json",
        repository=REPO_ROOT,
        expected_matrix_sha256=expected_digest,
    )


def _verify_holdout_condition_matrix(
    run_purpose: str,
    condition_specs: tuple[IndependentScenarioSpec, ...],
) -> None:
    if run_purpose != "independent_holdout":
        return
    matrix_config = json.loads(HOLDOUT_MATRIX_CONFIG.read_text(encoding="utf-8"))
    actual_digest = independent_condition_matrix_sha256(condition_specs)
    if actual_digest != matrix_config["condition_matrix_sha256"]:
        raise ValueError("implemented holdout matrix does not match the frozen checksum")


def _interpretation_warning(run_purpose: str) -> str:
    if run_purpose == "independent_holdout":
        return (
            "This is the single frozen holdout evaluation. Interpret only the "
            "predeclared primary and secondary comparisons without post-hoc tuning."
        )
    return "Independent scenarios are development or validation evidence, not a final holdout."


def _artifact_boundary_text(run_purpose: str) -> str:
    if run_purpose == "independent_holdout":
        return (
            "This artifact is the one-time frozen holdout evaluation. Generated truth "
            "is stored only in evaluation sidecars and was not used as model input.\n"
        )
    return "This artifact is not a final holdout. The holdout was not accessed.\n"


def _replicate_independent_specs(
    conditions: tuple[IndependentScenarioSpec, ...],
    seeds_per_condition: int,
    start_replicate: int = 1,
) -> tuple[IndependentScenarioSpec, ...]:
    if seeds_per_condition < 1:
        raise ValueError("seeds_per_condition must be positive")
    if start_replicate < 1:
        raise ValueError("start_replicate must be positive")
    replicated = []
    for condition in conditions:
        for replicate_index in range(
            start_replicate - 1,
            start_replicate - 1 + seeds_per_condition,
        ):
            offset = replicate_index * 1_000_003
            spec = replace(
                condition,
                scenario_id=(
                    f"{condition.scenario_id}-seed-{replicate_index + 1:02d}"
                ),
                seed=condition.seed + offset,
                split_seed=condition.split_seed + offset,
                model_seed=condition.model_seed + offset,
            )
            spec.validate()
            replicated.append(spec)
    return tuple(replicated)


def _condition_id(scenario_id: str) -> str:
    return scenario_id.rsplit("-seed-", 1)[0]


def _seed_replicate(scenario_id: str) -> int:
    return int(scenario_id.rsplit("-seed-", 1)[1])


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
            "policy_version": event.policy_version,
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
        "policy_version": event.policy_version,
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


def _entitlement_evidence_rows(
    world: IndependentWorld,
) -> list[dict[str, object]]:
    return [{
        "scenario_id": world.spec.scenario_id,
        "entitlement_id": evidence.entitlement_id,
        "employee_id": evidence.employee_id,
        "policy_id": evidence.policy_id,
        "policy_version": evidence.policy_version,
        "relevant_event_id": evidence.relevant_event_id,
        "evidence_reference": evidence.evidence_reference,
        "recorded_at": evidence.recorded_at.isoformat(),
    } for evidence in world.entitlement_evidence]


def _temporal_view_rows(scenario: object) -> list[dict[str, object]]:
    """Persist paired knowledge views for every test-split promotion event."""

    rows: list[dict[str, object]] = []
    evidence_by_employee = getattr(
        scenario.population,
        "grandfathering_evidence_by_employee_id",
        {},
    )
    eligible = getattr(
        scenario.population,
        "evaluation_eligible_by_employee_id",
        {},
    )
    for record in scenario.dataset.records:
        employee_id = record.identity.employee_id
        if record.split is not DatasetSplit.TEST or not eligible.get(employee_id, True):
            continue
        promotions = [
            event for event in record.events
            if event.event_type is AdministrativeEventType.PROMOTION
        ]
        for promotion in promotions:
            results = diagnose_temporal_views(
                record,
                scenario.policy,
                scenario.policy_epochs,
                tuple(evidence_by_employee.get(employee_id, ())),
                promotion.event_date,
                REFERENCE_DATE,
            )
            for result in results:
                rows.append({
                    "scenario_id": scenario.config.scenario_id,
                    "employee_id": employee_id,
                    "decision_event_id": promotion.source_id,
                    "decision_effective_date": promotion.event_date.isoformat(),
                    "view_identifier": result.view_identifier,
                    "effective_through": result.effective_through.isoformat(),
                    "recorded_through": result.recorded_through.isoformat(),
                    "visible_event_ids_json": json.dumps(result.visible_event_ids),
                    "visible_event_count": result.visible_event_count,
                    "effective_event_ids_json": json.dumps(result.effective_event_ids),
                    "effective_event_count": result.effective_event_count,
                    "promotion_assessment_count": result.promotion_assessment_count,
                    "total_service_deficit_months": result.total_service_deficit_months,
                })
    return rows


if __name__ == "__main__":
    main()
