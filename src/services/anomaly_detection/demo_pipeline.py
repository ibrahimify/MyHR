"""Application-facing orchestration for the synthetic anomaly-review demo.

This module does not implement a second detector. It converts the existing
development scenario, policy-assessment, deterministic-check, and protocol
evaluation outputs into presentation-safe records for the desktop UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    IndependentScenarioSpec,
    generate_independent_world,
    independent_scenario_matrix,
)

from .deterministic_checks import validate_invariant_record
from .policy_history import GrandfatheringEvidence, assess_promotion_history
from .protocol_evaluation import evaluate_fixed_budget_demo
from .synthetic_data import DatasetSplit, WorkforceHistoryRecord


ProgressCallback = Callable[[int, str], None]
CancellationCallback = Callable[[], bool]


@dataclass(frozen=True)
class DemoScenarioOption:
    index: int
    scenario_id: str
    population: str
    mechanism: str
    rare_pattern: str
    employee_count: int


@dataclass(frozen=True)
class DemoEvent:
    source_id: str
    event_type: str
    effective_date: date
    recorded_date: date
    category: int | None
    level_before: str | None
    level_after: str | None
    policy_id: str | None
    policy_version: str | None
    recognized_service_months: int
    correction_of_event_id: str | None


@dataclass(frozen=True)
class DemoPolicyCalculation:
    event_source_id: str
    policy_id: str
    policy_version: str
    observed_service_months: int
    required_service_months: int
    commendation_credit_months: int
    sanction_delay_months: int
    adjusted_service_months: int
    service_deficit_months: int
    raw_service_deficit_months: int
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class DemoEmployeeEvidence:
    employee_id: str
    full_name: str
    split: str
    employment_track: str
    department: str
    role: str
    current_level: str
    hire_date: date
    events: tuple[DemoEvent, ...]
    calculations: tuple[DemoPolicyCalculation, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class DemoQueueItem:
    employee_id: str
    employment_track: str
    source: str
    reason: str
    reason_code: str
    anomaly_score: float | None
    priority: str


@dataclass(frozen=True)
class DemoMethodComparison:
    representation: str
    label: str
    evaluation_count: int
    review_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float | None
    average_precision: float | None
    rare_legitimate_flagged: int
    rare_legitimate_count: int


@dataclass(frozen=True)
class DemoEvaluationSummary:
    evaluation_count: int
    positive_count: int
    deterministic_alert_count: int
    ml_review_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float | None


@dataclass(frozen=True)
class DemoRunResult:
    scenario: DemoScenarioOption
    train_count: int
    model_fit_count: int
    validation_count: int
    test_count: int
    eligible_test_count: int
    residual_test_count: int
    review_budget_fraction: float
    model_estimators: int
    queue: tuple[DemoQueueItem, ...]
    evidence_by_employee_id: dict[str, DemoEmployeeEvidence]
    comparisons: tuple[DemoMethodComparison, ...]
    evaluation: DemoEvaluationSummary


_REPRESENTATION_LABELS = {
    "raw_matched": "Raw features",
    "policy_matched": "Policy-aware features",
    "wrong_policy_control": "Wrong-policy control",
    "shuffled_policy_control": "Shuffled-policy control",
}


def demo_scenario_options(employee_count: int = 240) -> tuple[DemoScenarioOption, ...]:
    """Return three fixed, predeclared development scenarios for the UI."""

    specs = independent_scenario_matrix(employee_count=employee_count)
    selected = (specs[0], specs[len(specs) // 2], specs[-1])
    return tuple(_scenario_option(index, spec) for index, spec in enumerate(selected))


def run_demo_scenario(
    option_index: int,
    *,
    employee_count: int = 240,
    review_budget: float = 0.10,
    progress: ProgressCallback | None = None,
    cancelled: CancellationCallback | None = None,
) -> DemoRunResult:
    """Run one development-only scenario through the verified evaluator."""

    options = demo_scenario_options(employee_count)
    if option_index < 0 or option_index >= len(options):
        raise ValueError("unknown demonstration scenario")
    specs = independent_scenario_matrix(employee_count=employee_count)
    selected_specs = (specs[0], specs[len(specs) // 2], specs[-1])
    spec = selected_specs[option_index]
    option = options[option_index]

    _ensure_not_cancelled(cancelled)
    _report(progress, 8, "generate")
    world = generate_independent_world(spec)
    scenario = adapt_independent_world(world)

    _ensure_not_cancelled(cancelled)
    _report(progress, 28, "separate")
    records = tuple(scenario.dataset.records)
    eligibility = getattr(
        scenario.population,
        "evaluation_eligible_by_employee_id",
        {},
    )
    train = tuple(record for record in records if record.split is DatasetSplit.TRAIN)
    validation = tuple(record for record in records if record.split is DatasetSplit.VALIDATION)
    test = tuple(record for record in records if record.split is DatasetSplit.TEST)
    eligible_test = tuple(
        record for record in test
        if eligibility.get(record.identity.employee_id, True)
    )
    eligible_train = tuple(
        record for record in train
        if eligibility.get(record.identity.employee_id, True)
    )
    model_fit = tuple(
        record for record in eligible_train
        if not validate_invariant_record(record)
    )

    _ensure_not_cancelled(cancelled)
    _report(progress, 45, "model")
    model_estimators = 25
    evaluation = evaluate_fixed_budget_demo(
        scenario,
        review_budget=review_budget,
        n_estimators=model_estimators,
        cancelled=cancelled,
        progress=(
            None
            if progress is None
            else lambda index, total: _report(
                progress,
                48 + int(24 * index / max(total, 1)),
                "model",
            )
        ),
    )

    _ensure_not_cancelled(cancelled)
    _report(progress, 76, "evidence")
    queue, residual_ids = _review_queue(scenario, eligible_test, evaluation.prediction_rows)
    evidence = {
        record.identity.employee_id: _employee_evidence(scenario, record)
        for record in eligible_test
    }
    comparisons = _method_comparisons(evaluation.metric_rows)
    summary = _evaluation_summary(evaluation.metric_rows)

    _ensure_not_cancelled(cancelled)
    _report(progress, 100, "complete")
    return DemoRunResult(
        scenario=option,
        train_count=len(train),
        model_fit_count=len(model_fit),
        validation_count=len(validation),
        test_count=len(test),
        eligible_test_count=len(eligible_test),
        residual_test_count=len(residual_ids),
        review_budget_fraction=review_budget,
        model_estimators=model_estimators,
        queue=queue,
        evidence_by_employee_id=evidence,
        comparisons=comparisons,
        evaluation=summary,
    )


def _scenario_option(index: int, spec: IndependentScenarioSpec) -> DemoScenarioOption:
    return DemoScenarioOption(
        index=index,
        scenario_id=spec.scenario_id,
        population=spec.population,
        mechanism=spec.mechanism,
        rare_pattern=spec.rare_pattern,
        employee_count=spec.employee_count,
    )


def _review_queue(scenario, eligible_test, prediction_rows):
    records_by_id = {
        record.identity.employee_id: record for record in eligible_test
    }
    queue: list[DemoQueueItem] = []
    rule_ids: set[str] = set()
    for record in eligible_test:
        findings = validate_invariant_record(record)
        if not findings:
            continue
        rule_ids.add(record.identity.employee_id)
        queue.append(DemoQueueItem(
            employee_id=record.identity.employee_id,
            employment_track=record.employment_track.value,
            source="deterministic",
            reason=findings[0].message,
            reason_code=findings[0].code,
            anomaly_score=None,
            priority="rule",
        ))

    policy_rows = [
        row for row in prediction_rows
        if row["method"] == "rule_negative_isolation_forest"
        and row["representation"] == "policy_matched"
        and row["operating_point"] == "fixed_review_budget"
    ]
    residual_ids = {str(row["employee_id"]) for row in policy_rows}
    flagged = sorted(
        (row for row in policy_rows if bool(row["predicted_anomaly"])),
        key=lambda row: (-float(row["score"]), str(row["employee_id"])),
    )
    high_cutoff = max(1, (len(flagged) + 2) // 3)
    medium_cutoff = max(high_cutoff + 1, 2 * high_cutoff)
    for index, row in enumerate(flagged):
        employee_id = str(row["employee_id"])
        record = records_by_id[employee_id]
        priority = "high" if index < high_cutoff else "medium" if index < medium_cutoff else "low"
        queue.append(DemoQueueItem(
            employee_id=employee_id,
            employment_track=record.employment_track.value,
            source="statistical",
            reason="Unusual progression pattern within the fixed review capacity",
            reason_code="statistical_suspicion",
            anomaly_score=float(row["score"]),
            priority=priority,
        ))
    queue.sort(key=lambda item: (
        item.source != "deterministic",
        -(item.anomaly_score or 0.0),
        item.employee_id,
    ))
    return tuple(queue), residual_ids


def _employee_evidence(scenario, record: WorkforceHistoryRecord) -> DemoEmployeeEvidence:
    evidence = _grandfathering_evidence(scenario, record)
    evidence_by_event: dict[str, list[GrandfatheringEvidence]] = {}
    for item in evidence:
        evidence_by_event.setdefault(item.event_source_id, []).append(item)
    assessments = assess_promotion_history(
        record,
        scenario.policy,
        scenario.policy_epochs,
        grandfathering_evidence=evidence,
    )
    events_by_id = {event.source_id: event for event in record.events}
    calculations = []
    for assessment in assessments:
        event = events_by_id.get(assessment.event_source_id)
        calculations.append(DemoPolicyCalculation(
            event_source_id=assessment.event_source_id,
            policy_id=(event.policy_id if event and event.policy_id else "default-policy"),
            policy_version=(event.policy_version if event and event.policy_version else "current"),
            observed_service_months=assessment.observed_service_months,
            required_service_months=assessment.required_service_months,
            commendation_credit_months=assessment.commendation_credit_months,
            sanction_delay_months=assessment.sanction_delay_months,
            adjusted_service_months=assessment.adjusted_service_months,
            service_deficit_months=assessment.service_deficit_months,
            raw_service_deficit_months=assessment.raw_service_deficit_months,
            evidence_references=tuple(
                item.evidence_reference
                for item in evidence_by_event.get(assessment.event_source_id, ())
            ),
        ))
    limitations = []
    if not calculations:
        limitations.append("no_promotion_calculation")
    if not evidence:
        limitations.append("no_exception_evidence")
    if record.identity.national_id is None or record.identity.email is None:
        limitations.append("identity_fields_omitted")
    return DemoEmployeeEvidence(
        employee_id=record.identity.employee_id,
        full_name=record.identity.full_name,
        split=record.split.value,
        employment_track=record.employment_track.value,
        department=record.department,
        role=record.role,
        current_level=record.current_level,
        hire_date=record.hire_date,
        events=tuple(DemoEvent(
            source_id=event.source_id,
            event_type=event.event_type.value,
            effective_date=event.event_date,
            recorded_date=event.recorded_date or event.event_date,
            category=event.category,
            level_before=event.level_before,
            level_after=event.level_after,
            policy_id=event.policy_id,
            policy_version=event.policy_version,
            recognized_service_months=event.recognized_service_months,
            correction_of_event_id=event.correction_of_source_id,
        ) for event in sorted(record.events, key=lambda item: (item.event_date, item.source_id))),
        calculations=tuple(calculations),
        limitations=tuple(limitations),
    )


def _method_comparisons(metric_rows) -> tuple[DemoMethodComparison, ...]:
    by_representation = {
        str(row["representation"]): row
        for row in metric_rows
        if row["method"] == "rule_negative_isolation_forest"
        and row["operating_point"] == "fixed_review_budget"
        and row["representation"] in _REPRESENTATION_LABELS
    }
    missing = set(_REPRESENTATION_LABELS) - set(by_representation)
    if missing:
        raise ValueError(f"missing demonstration comparisons: {sorted(missing)}")
    counts = {int(row["evaluation_count"]) for row in by_representation.values()}
    budgets = {int(row["alert_count"]) for row in by_representation.values()}
    if len(counts) != 1 or len(budgets) != 1:
        raise ValueError("comparison methods do not use equal populations and review budgets")
    return tuple(
        DemoMethodComparison(
            representation=name,
            label=_REPRESENTATION_LABELS[name],
            evaluation_count=int(row["evaluation_count"]),
            review_count=int(row["alert_count"]),
            true_positives=int(row["true_positives"]),
            false_positives=int(row["false_positives"]),
            false_negatives=int(row["false_negatives"]),
            precision=float(row["precision"]),
            recall=None if row["recall"] is None else float(row["recall"]),
            average_precision=(
                None if row["average_precision"] is None else float(row["average_precision"])
            ),
            rare_legitimate_flagged=int(row["rare_legitimate_flagged"]),
            rare_legitimate_count=int(row["rare_legitimate_count"]),
        )
        for name in _REPRESENTATION_LABELS
        for row in (by_representation[name],)
    )


def _evaluation_summary(metric_rows) -> DemoEvaluationSummary:
    row = next(
        row for row in metric_rows
        if row["method"] == "rule_negative_isolation_forest"
        and row["representation"] == "policy_matched"
        and row["operating_point"] == "fixed_review_budget"
    )
    deterministic = next(
        item for item in metric_rows
        if item["method"] == "deterministic_invariant_rules"
        and item["operating_point"] == "rules_fixed"
    )
    return DemoEvaluationSummary(
        evaluation_count=int(row["evaluation_count"]),
        positive_count=int(row["positive_count"]),
        deterministic_alert_count=int(deterministic["alert_count"]),
        ml_review_count=int(row["alert_count"]),
        true_positives=int(row["true_positives"]),
        false_positives=int(row["false_positives"]),
        false_negatives=int(row["false_negatives"]),
        precision=float(row["precision"]),
        recall=None if row["recall"] is None else float(row["recall"]),
    )


def _grandfathering_evidence(scenario, record) -> tuple[GrandfatheringEvidence, ...]:
    by_employee = getattr(
        scenario.population,
        "grandfathering_evidence_by_employee_id",
        {},
    )
    return tuple(by_employee.get(record.identity.employee_id, ()))


def _report(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback is not None:
        callback(value, message)


def _ensure_not_cancelled(callback: CancellationCallback | None) -> None:
    if callback is not None and callback():
        raise InterruptedError("demonstration run cancelled")
