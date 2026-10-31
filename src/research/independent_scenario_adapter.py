"""Neutral adapter from independent ledgers to research evaluation records."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.services.anomaly_detection.policy_model import PromotionPolicy
from src.services.anomaly_detection.policy_history import (
    GrandfatheringEvidence,
    PolicyEpoch,
)
from src.services.anomaly_detection.scenario_generation import ScenarioDataset
from src.services.anomaly_detection.synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    SyntheticDataset,
    SyntheticDatasetMetadata,
    WorkforceHistoryRecord,
)

from .independent_scenarios import (
    REFERENCE_DATE,
    IndependentEventKind,
    IndependentScenarioSpec,
    IndependentSplit,
    IndependentTrack,
    IndependentWorld,
    TruthCategory,
)


@dataclass(frozen=True)
class AdapterPopulation:
    profile_id: str
    evaluation_eligible_by_employee_id: dict[str, bool]
    evaluation_exclusion_reason_by_employee_id: dict[str, str]
    truth_category_by_employee_id: dict[str, str]
    grandfathering_evidence_by_employee_id: dict[
        str, tuple[GrandfatheringEvidence, ...]
    ]


@dataclass(frozen=True)
class AdapterConfig:
    scenario_id: str
    run_purpose: str
    dataset_seed: int
    split_seed: int
    model_seed: int
    employee_count: int
    policy_profile: str
    population_profile: str
    anomaly_mechanism: str
    rare_pattern: str
    anomaly_rate: float
    rare_legitimate_rate: float


def adapt_independent_world(world: IndependentWorld) -> ScenarioDataset:
    """Expose observable records to the detector and attach truth for evaluation."""

    truth_by_employee = {entry.employee_id: entry for entry in world.truth}
    records = []
    for employee in world.employees:
        truth = truth_by_employee[employee.employee_id]
        records.append(WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id=employee.employee_id,
                full_name=f"Independent Employee {employee.employee_id[2:]}",
                date_of_birth=employee.date_of_birth,
                national_id=None,
                email=None,
            ),
            split=_split(employee.split),
            employment_track=(
                EmploymentTrack.PROMOTION
                if employee.track is IndependentTrack.PROGRESSION
                else EmploymentTrack.OTHER
            ),
            current_level=employee.current_level,
            department=employee.department,
            role=employee.role,
            hire_date=employee.hire_date,
            events=tuple(
                _event(event) for event in employee.events
            ),
            anomaly_labels=_labels(truth.category, truth.mechanism),
            observation_date=REFERENCE_DATE,
        ))
    labels = Counter(label.value for record in records for label in record.anomaly_labels)
    splits = Counter(record.split.value for record in records)
    spec = world.spec
    entitlement_by_employee: dict[str, list[GrandfatheringEvidence]] = {}
    for evidence in world.entitlement_evidence:
        entitlement_by_employee.setdefault(evidence.employee_id, []).append(
            GrandfatheringEvidence(
                employee_id=evidence.employee_id,
                policy_id=evidence.policy_id,
                policy_version=evidence.policy_version,
                event_source_id=evidence.relevant_event_id,
                evidence_reference=evidence.evidence_reference,
                recorded_at=evidence.recorded_at,
            )
        )
    config = AdapterConfig(
        scenario_id=spec.scenario_id,
        run_purpose=spec.run_purpose,
        dataset_seed=spec.seed,
        split_seed=spec.split_seed,
        model_seed=spec.model_seed,
        employee_count=spec.employee_count,
        policy_profile="standard",
        population_profile=spec.population,
        anomaly_mechanism=spec.mechanism,
        rare_pattern=spec.rare_pattern,
        anomaly_rate=spec.error_rate,
        rare_legitimate_rate=spec.rare_rate,
    )
    current_policy = max(world.policies, key=lambda item: item.effective_from)
    return ScenarioDataset(
        config=config,  # type: ignore[arg-type]
        policy=PromotionPolicy(service_months_by_level=current_policy.service_months_by_level),
        policy_epochs=tuple(
            PolicyEpoch(
                policy_id=card.policy_id,
                version=card.version,
                valid_from=card.effective_from,
                valid_to=card.effective_to,
                recorded_at=card.recorded_at,
                jurisdiction=card.jurisdiction,
                policy=PromotionPolicy(
                    service_months_by_level=card.service_months_by_level
                ),
                grandfather_previous_policy=card.grandfather_previous_policy,
            )
            for card in world.policies
        ),
        population=AdapterPopulation(  # type: ignore[arg-type]
            profile_id=spec.population,
            evaluation_eligible_by_employee_id={
                entry.employee_id: (
                    entry.category is not TruthCategory.AMBIGUOUS_REVIEW_CASE
                )
                for entry in world.truth
            },
            evaluation_exclusion_reason_by_employee_id={
                entry.employee_id: "ambiguous_review_case"
                for entry in world.truth
                if entry.category is TruthCategory.AMBIGUOUS_REVIEW_CASE
            },
            truth_category_by_employee_id={
                entry.employee_id: entry.category.value for entry in world.truth
            },
            grandfathering_evidence_by_employee_id={
                employee_id: tuple(evidence)
                for employee_id, evidence in entitlement_by_employee.items()
            },
        ),
        dataset=SyntheticDataset(
            records=tuple(records),
            metadata=SyntheticDatasetMetadata(
                schema_version="independent-development-v2",
                run_id=spec.scenario_id,
                seed=spec.seed,
                employee_count=spec.employee_count,
                split_counts=dict(splits),
                label_counts=dict(labels),
            ),
        ),
    )


def _split(value: IndependentSplit) -> DatasetSplit:
    return DatasetSplit(value.value)


def _event_kind(value: IndependentEventKind) -> AdministrativeEventType:
    return AdministrativeEventType(value.value)


def _event(value) -> AdministrativeEvent:
    return AdministrativeEvent(
        event_type=_event_kind(value.kind),
        event_date=value.effective_date,
        source_id=value.event_id,
        level_before=value.level_before,
        level_after=value.level_after,
        category=value.category,
        is_resolved=value.resolved_date is not None,
        resolved_date=value.resolved_date,
        note=(
            f"policy={value.policy_id}; recorded={value.recorded_date.isoformat()}; "
            f"approval={value.approval_reference or ''}"
        ),
        recorded_date=value.recorded_date,
        policy_id=value.policy_id,
        policy_version=value.policy_version,
        approval_reference=value.approval_reference,
        approval_status=value.approval_status,
        recognized_service_months=value.recognized_service_months,
        correction_of_source_id=value.correction_of_event_id,
        retry_of_source_id=value.retry_of_event_id,
        jurisdiction=value.jurisdiction,
    )


def _labels(category: TruthCategory, mechanism: str) -> tuple[AnomalyType, ...]:
    if category is TruthCategory.AMBIGUOUS_REVIEW_CASE:
        # Ambiguous cases remain present for review and provenance but are not
        # coerced into either side of the binary evaluation target.
        return ()
    if category is TruthCategory.ORDINARY_LEGITIMATE:
        return (AnomalyType.CLEAN,)
    if category is TruthCategory.RARE_LEGITIMATE:
        return (AnomalyType.POLICY_LEGITIMATE_RARE_CASE,)
    return ({
        "wrong_employee_link": AnomalyType.EXCESSIVE_SANCTIONS,
        "missing_increment_import": AnomalyType.UNUSUAL_ADMIN_INTERVAL,
        "approval_bypass": AnomalyType.FREQUENT_PROMOTIONS,
        "batch_retry": AnomalyType.UNUSUAL_ADMIN_INTERVAL,
    }[mechanism],)
