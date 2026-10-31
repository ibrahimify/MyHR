"""Independent development-only administrative-world simulator.

This module intentionally imports no MyHR detector, policy, feature, or existing
synthetic-generator code. It produces an observable event ledger and a separate
truth ledger. A neutral adapter may translate those ledgers for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from hashlib import sha256
from random import Random


REFERENCE_DATE = date(2026, 12, 31)
_MIN_GENERATED_HIRE_AGE = 18
# Keep the old 37-value RNG range width so unrelated generation does not drift.
_MAX_GENERATED_HIRE_AGE = 54


class IndependentSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class IndependentTrack(str, Enum):
    PROGRESSION = "progression"
    INCREMENT_ONLY = "increment_only"


class IndependentEventKind(str, Enum):
    HIRE = "hire"
    PROMOTION = "promotion"
    SALARY_INCREMENT = "salary_increment"
    SANCTION = "sanction"
    COMMENDATION = "commendation"
    PERFORMANCE_REVIEW = "performance_review"


class TruthCategory(str, Enum):
    ORDINARY_LEGITIMATE = "ordinary_legitimate"
    RARE_LEGITIMATE = "rare_legitimate"
    EXPLICIT_POLICY_VIOLATION = "explicit_policy_violation"
    CONFIRMED_RECORDING_ERROR = "confirmed_recording_error"
    CONFIRMED_PROCESS_ERROR = "confirmed_process_error"
    AMBIGUOUS_REVIEW_CASE = "ambiguous_review_case"


@dataclass(frozen=True)
class IndependentPolicyCard:
    policy_id: str
    version: str
    effective_from: date
    effective_to: date | None
    recorded_at: date
    jurisdiction: str
    service_months_by_level: dict[str, int]
    grandfather_previous_policy: bool


@dataclass(frozen=True)
class IndependentEntitlementEvidence:
    """Observable evidence authorizing one event under a named policy version."""

    entitlement_id: str
    employee_id: str
    policy_id: str
    policy_version: str
    relevant_event_id: str
    evidence_reference: str
    recorded_at: date


@dataclass(frozen=True)
class IndependentScenarioSpec:
    scenario_id: str
    run_purpose: str
    seed: int
    split_seed: int
    model_seed: int
    employee_count: int
    population: str
    mechanism: str
    rare_pattern: str
    error_rate: float = 0.12
    rare_rate: float = 0.08

    def validate(self) -> None:
        if self.run_purpose != "independent_development":
            raise ValueError("independent scenarios are development-only; holdout is undefined")
        if self.employee_count < 120:
            raise ValueError("employee_count must be at least 120")
        if self.population not in population_families():
            raise ValueError(f"unknown population: {self.population}")
        if self.mechanism not in anomaly_mechanisms():
            raise ValueError(f"unknown mechanism: {self.mechanism}")
        if self.rare_pattern not in rare_legitimate_patterns():
            raise ValueError(f"unknown rare pattern: {self.rare_pattern}")
        compatible = compatible_rare_patterns_by_population()[self.population]
        if self.rare_pattern not in compatible:
            raise ValueError(
                "incompatible scenario combination: "
                f"population {self.population!r} cannot lawfully host "
                f"rare pattern {self.rare_pattern!r}"
            )
        if not 0 < self.error_rate < 0.3 or not 0 < self.rare_rate < 0.3:
            raise ValueError("scenario rates must be between zero and 0.3")


@dataclass(frozen=True)
class IndependentEvent:
    event_id: str
    kind: IndependentEventKind
    effective_date: date
    recorded_date: date
    policy_id: str
    policy_version: str
    level_before: str | None = None
    level_after: str | None = None
    category: int | None = None
    resolved_date: date | None = None
    approval_reference: str | None = None
    approval_status: str = "approved"
    correction_of_event_id: str | None = None
    retry_of_event_id: str | None = None
    recognized_service_months: int = 0
    jurisdiction: str = "organization-wide"


@dataclass(frozen=True)
class IndependentEmployeeLedger:
    employee_id: str
    split: IndependentSplit
    track: IndependentTrack
    current_level: str | None
    department: str
    role: str
    date_of_birth: date
    hire_date: date
    events: tuple[IndependentEvent, ...]


@dataclass(frozen=True)
class IndependentTruthEntry:
    employee_id: str
    category: TruthCategory
    mechanism: str
    realized_mechanism: str
    evidence: str
    track: IndependentTrack
    causal_events: tuple[IndependentEvent, ...]


@dataclass(frozen=True)
class IndependentWorld:
    spec: IndependentScenarioSpec
    policies: tuple[IndependentPolicyCard, ...]
    employees: tuple[IndependentEmployeeLedger, ...]
    truth: tuple[IndependentTruthEntry, ...]
    entitlement_evidence: tuple[IndependentEntitlementEvidence, ...]


def population_families() -> tuple[str, ...]:
    return "stable_administration", "rapid_expansion", "merger_migration"


def anomaly_mechanisms() -> tuple[str, ...]:
    return (
        "wrong_employee_link",
        "missing_increment_import",
        "approval_bypass",
        "batch_retry",
    )


def rare_legitimate_patterns() -> tuple[str, ...]:
    return (
        "grandfathered_policy",
        "recognized_prior_service",
        "delayed_bulk_recording",
        "late_correction",
        "policy_transition",
    )


def compatible_rare_patterns_by_population() -> dict[str, tuple[str, ...]]:
    """Return the predeclared lawful population/pattern combinations.

    Rapid-expansion employees are hired from 2021 onward, so that population
    cannot reliably host a promotion completed inside the legacy epoch. The
    remaining patterns select eligible employees within each population.
    """

    return {
        population: tuple(
            pattern for pattern in rare_legitimate_patterns()
            if (
                pattern != "policy_transition"
                or _population_can_host_policy_transition(population)
            )
        )
        for population in population_families()
    }


# Single source of truth for the per-population hire-year windows. Used both by
# _base_employee (to draw hire dates) and by independent_scenario_matrix (to
# decide which rare patterns a population can lawfully host).
_HIRE_YEAR_RANGES: dict[str, tuple[int, int]] = {
    "stable_administration": (2012, 2020),
    "rapid_expansion": (2021, 2025),
    "merger_migration": (2015, 2024),
}

# The legacy service requirement a policy_transition promotion must satisfy, and
# the last day of the legacy policy epoch. A population can host a lawful
# policy_transition case only if its earliest possible hire can reach a
# legacy-epoch promotion that meets this requirement.
_LEGACY_L7_SERVICE_MONTHS = 30
_LEGACY_EPOCH_END = date(2022, 12, 31)


def _population_can_host_policy_transition(population: str) -> bool:
    """True when the population's earliest hire can earn a lawful legacy-epoch
    promotion (hire + legacy L7 service <= legacy epoch end)."""

    first_year, _ = _HIRE_YEAR_RANGES[population]
    earliest_hire = date(first_year, 1, 1)
    return _add_months(earliest_hire, _LEGACY_L7_SERVICE_MONTHS) <= _LEGACY_EPOCH_END


def independent_scenario_matrix(
    employee_count: int = 360,
) -> tuple[IndependentScenarioSpec, ...]:
    """Return 12 predeclared development-only scenarios."""

    specs = []
    patterns = rare_legitimate_patterns()
    for index, (population, mechanism) in enumerate(
        (population, mechanism)
        for population in population_families()
        for mechanism in anomaly_mechanisms()
    ):
        # Assign the rare pattern by the stable index cycle, but never pair
        # policy_transition with a population whose hire window cannot host a
        # lawful legacy-epoch promotion (e.g. rapid_expansion, hired 2021+).
        # Pairing it there would be scientifically invalid: no lawful legacy
        # transition case exists, so the only way to fill the slot would be to
        # fabricate a promotion that violates the legacy service/epoch rules.
        # When the cycle lands on policy_transition for such a population, we
        # deterministically advance to the next pattern in the cycle instead.
        rare_pattern = patterns[index % len(patterns)]
        if rare_pattern not in compatible_rare_patterns_by_population()[population]:
            rare_pattern = patterns[(index + 1) % len(patterns)]
        specs.append(IndependentScenarioSpec(
            scenario_id=f"ind-dev-{index + 1:02d}",
            run_purpose="independent_development",
            seed=81001 + index * 17,
            split_seed=81003 + index * 17,
            model_seed=81007 + index * 17,
            employee_count=employee_count,
            population=population,
            mechanism=mechanism,
            rare_pattern=rare_pattern,
        ))
    return tuple(specs)


def generate_independent_world(spec: IndependentScenarioSpec) -> IndependentWorld:
    spec.validate()
    policies = _policy_cards()
    split_by_index = _split_assignments(spec)
    base_employees = tuple(
        _base_employee(
            index,
            split_by_index[index],
            spec,
            policies,
            Random(spec.seed * 100_003 + index * 97),
        )
        for index in range(spec.employee_count)
    )
    truth_plan = _truth_plan(spec, base_employees)
    employees = []
    truth = []
    entitlement_evidence = []
    for index, base_employee in enumerate(base_employees):
        rng = Random(spec.seed * 100_003 + index * 97)
        employee = base_employee
        category = truth_plan[index]
        mechanism = "none"
        realized_mechanism = "none"
        evidence = "No injected administrative discrepancy."
        causal_events: tuple[IndependentEvent, ...] = ()
        if category is TruthCategory.RARE_LEGITIMATE:
            mechanism = spec.rare_pattern
            employee, evidence, realized_mechanism, causal_events = _apply_rare_case(
                employee, spec.rare_pattern, policies, rng
            )
            if spec.rare_pattern == "grandfathered_policy":
                if len(causal_events) != 1:
                    raise ValueError(
                        "grandfathered policy case requires one relevant event"
                    )
                promotion = causal_events[0]
                policy = next(
                    card for card in policies
                    if card.policy_id == promotion.policy_id
                    and card.version == promotion.policy_version
                )
                entitlement_evidence.append(IndependentEntitlementEvidence(
                    entitlement_id=f"ENT-{employee.employee_id}-{promotion.event_id}",
                    employee_id=employee.employee_id,
                    policy_id=policy.policy_id,
                    policy_version=policy.version,
                    relevant_event_id=promotion.event_id,
                    evidence_reference=f"GF-{employee.employee_id}-{promotion.event_id}",
                    recorded_at=min(
                        promotion.effective_date,
                        promotion.recorded_date,
                    ) - timedelta(days=30),
                ))
        elif category is not TruthCategory.ORDINARY_LEGITIMATE:
            employee, evidence, causal_events = _apply_error(
                employee, spec.mechanism, policies, rng
            )
            mechanism = spec.mechanism
            realized_mechanism = spec.mechanism
        employees.append(employee)
        truth.append(IndependentTruthEntry(
            employee_id=employee.employee_id,
            category=category,
            mechanism=mechanism,
            realized_mechanism=realized_mechanism,
            evidence=evidence,
            track=employee.track,
            causal_events=causal_events,
        ))
    return IndependentWorld(
        spec=spec,
        policies=policies,
        employees=tuple(employees),
        truth=tuple(truth),
        entitlement_evidence=tuple(entitlement_evidence),
    )


def _policy_cards() -> tuple[IndependentPolicyCard, ...]:
    return (
        IndependentPolicyCard(
            "legacy-pre-2023",
            "1.0",
            date(2010, 1, 1),
            date(2022, 12, 31),
            date(2009, 12, 1),
            "organization-wide",
            {"L7": 30, "L6": 30, "L5": 42, "L4": 48, "L3": 54, "L2": 60},
            True,
        ),
        IndependentPolicyCard(
            "reform-2023",
            "2.0",
            date(2023, 1, 1),
            None,
            date(2022, 10, 1),
            "organization-wide",
            {"L7": 36, "L6": 36, "L5": 42, "L4": 48, "L3": 54, "L2": 60},
            True,
        ),
    )


def _split_assignments(spec: IndependentScenarioSpec) -> dict[int, IndependentSplit]:
    indices = list(range(spec.employee_count))
    Random(spec.split_seed).shuffle(indices)
    train_end = round(spec.employee_count * 0.60)
    validation_end = round(spec.employee_count * 0.80)
    result = {}
    for index in indices[:train_end]:
        result[index] = IndependentSplit.TRAIN
    for index in indices[train_end:validation_end]:
        result[index] = IndependentSplit.VALIDATION
    for index in indices[validation_end:]:
        result[index] = IndependentSplit.TEST
    return result


def _truth_plan(
    spec: IndependentScenarioSpec,
    employees: tuple[IndependentEmployeeLedger, ...],
) -> dict[int, TruthCategory]:
    result = {
        index: TruthCategory.ORDINARY_LEGITIMATE
        for index in range(len(employees))
    }
    rng = Random(spec.seed + 41)
    for split in IndependentSplit:
        indices = [
            index for index, employee in enumerate(employees)
            if employee.split is split
        ]
        error_count = max(2, round(len(indices) * spec.error_rate))
        rare_count = max(2, round(len(indices) * spec.rare_rate))
        error_candidates = [
            index for index in indices
            if _eligible_for_error(employees[index], spec.mechanism)
        ]
        rng.shuffle(error_candidates)
        selected_errors = error_candidates[:error_count]
        if len(selected_errors) != error_count:
            raise ValueError(
                f"insufficient {spec.mechanism} candidates in {split.value}"
            )
        rare_candidates = [
            index for index in indices
            if index not in selected_errors
            and _eligible_for_rare_case(employees[index], spec.rare_pattern)
        ]
        rng.shuffle(rare_candidates)
        selected_rare = rare_candidates[:rare_count]
        if len(selected_rare) != rare_count:
            raise ValueError(
                f"insufficient {spec.rare_pattern} candidates in {split.value}"
            )
        error_category = (
            TruthCategory.EXPLICIT_POLICY_VIOLATION
            if spec.mechanism == "approval_bypass"
            else TruthCategory.CONFIRMED_PROCESS_ERROR
            if spec.mechanism == "wrong_employee_link"
            else TruthCategory.CONFIRMED_RECORDING_ERROR
        )
        for index in selected_errors:
            result[index] = error_category
        for index in selected_rare:
            result[index] = TruthCategory.RARE_LEGITIMATE
    return result


def _eligible_for_error(
    employee: IndependentEmployeeLedger,
    mechanism: str,
) -> bool:
    if mechanism in {"missing_increment_import", "batch_retry"}:
        return any(
            event.kind is IndependentEventKind.SALARY_INCREMENT
            for event in employee.events
        )
    if mechanism == "approval_bypass":
        return (
            employee.track is IndependentTrack.PROGRESSION
            and _add_months(employee.hire_date, 36) <= REFERENCE_DATE
        )
    return True


def _eligible_for_rare_case(
    employee: IndependentEmployeeLedger,
    pattern: str,
) -> bool:
    if pattern == "grandfathered_policy":
        return (
            employee.track is IndependentTrack.PROGRESSION
            and employee.hire_date <= _LEGACY_EPOCH_END
            and _add_months(employee.hire_date, 30) <= REFERENCE_DATE
        )
    if pattern == "recognized_prior_service":
        return (
            employee.track is IndependentTrack.PROGRESSION
            and _add_months(employee.hire_date, 24) <= REFERENCE_DATE
        )
    if pattern == "late_correction":
        # The late-correction intervention re-dates and supersedes an EXISTING
        # promotion, so the employee must be on the progression track and
        # already carry at least one promotion event to correct (R3).
        return (
            employee.track is IndependentTrack.PROGRESSION
            and _has_promotion(employee)
        )
    if pattern == "policy_transition":
        # The transition intervention rebuilds a single legacy-epoch promotion,
        # so the employee must already have a promotion to transition (R3) and
        # must have been hired early enough that a legacy-epoch (<= 2022-12-31)
        # promotion can still satisfy the legacy L7 service requirement of 30
        # months.  Otherwise no lawful legacy-epoch promotion exists for them.
        return (
            employee.track is IndependentTrack.PROGRESSION
            and _has_promotion(employee)
            and _add_months(employee.hire_date, 30) <= date(2022, 12, 31)
        )
    # Remaining patterns operate on salary increments (delayed_bulk_recording).
    return any(
        event.kind is IndependentEventKind.SALARY_INCREMENT
        and event.effective_date + timedelta(days=120) <= REFERENCE_DATE
        for event in employee.events
    )


def _has_promotion(employee: IndependentEmployeeLedger) -> bool:
    return any(
        event.kind is IndependentEventKind.PROMOTION
        for event in employee.events
    )


def _base_employee(
    index: int,
    split: IndependentSplit,
    spec: IndependentScenarioSpec,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> IndependentEmployeeLedger:
    first_year, last_year = _HIRE_YEAR_RANGES[spec.population]
    hire_date = date(rng.randint(first_year, last_year), rng.randint(1, 12), rng.randint(1, 28))
    track_probability = 0.82 if spec.population != "rapid_expansion" else 0.68
    track = (
        IndependentTrack.PROGRESSION
        if rng.random() < track_probability
        else IndependentTrack.INCREMENT_ONLY
    )
    employee_id = f"I-{index + 1:05d}"
    events = [_event(
        policies,
        spec.seed,
        index,
        0,
        IndependentEventKind.HIRE,
        hire_date,
        _policy_id_for_date(hire_date),
    )]
    increment_date = _add_months(hire_date, 12)
    sequence = 1
    while increment_date <= REFERENCE_DATE:
        events.append(_event(
            policies,
            spec.seed, index, sequence, IndependentEventKind.SALARY_INCREMENT,
            increment_date, _policy_id_for_date(increment_date),
        ))
        sequence += 1
        increment_date = _add_months(increment_date, 12)
    current_level = None
    if track is IndependentTrack.PROGRESSION:
        current_level = "L7"
        promotion_date = _add_months(hire_date, 36)
        if promotion_date <= REFERENCE_DATE:
            events.append(_event(
                policies,
                spec.seed, index, sequence, IndependentEventKind.PROMOTION,
                promotion_date, _policy_id_for_date(promotion_date),
                level_before="L7", level_after="L6",
            ))
            current_level = "L6"
            sequence += 1
            second_promotion_date = _add_months(promotion_date, 36)
            if second_promotion_date <= REFERENCE_DATE:
                events.append(_event(
                    policies,
                    spec.seed,
                    index,
                    sequence,
                    IndependentEventKind.PROMOTION,
                    second_promotion_date,
                    _policy_id_for_date(second_promotion_date),
                    level_before="L6",
                    level_after="L5",
                ))
                current_level = "L5"
                sequence += 1

    commendation_date = _add_months(hire_date, 9)
    if rng.random() < 0.28 and commendation_date <= REFERENCE_DATE:
        events.append(_event(
            policies,
            spec.seed,
            index,
            sequence,
            IndependentEventKind.COMMENDATION,
            commendation_date,
            _policy_id_for_date(commendation_date),
            category=1 + index % 3,
        ))
        sequence += 1

    sanction_date = _add_months(hire_date, 15)
    resolved_date = sanction_date + timedelta(days=90)
    if rng.random() < 0.18 and resolved_date <= REFERENCE_DATE:
        events.append(_event(
            policies,
            spec.seed,
            index,
            sequence,
            IndependentEventKind.SANCTION,
            sanction_date,
            _policy_id_for_date(sanction_date),
            category=1 + index % 2,
            resolved_date=resolved_date,
        ))
        sequence += 1

    review_date = _add_months(hire_date, 12)
    review_count = 0
    while review_date <= REFERENCE_DATE and review_count < 5:
        events.append(_event(
            policies,
            spec.seed,
            index,
            sequence,
            IndependentEventKind.PERFORMANCE_REVIEW,
            review_date,
            _policy_id_for_date(review_date),
        ))
        sequence += 1
        review_count += 1
        review_date = _add_months(review_date, 12)
    return IndependentEmployeeLedger(
        employee_id=employee_id,
        split=split,
        track=track,
        current_level=current_level,
        department=("Operations", "Engineering", "Finance")[index % 3],
        role="Specialist" if track is IndependentTrack.PROGRESSION else "Support",
        date_of_birth=_birth_date_for_hire(hire_date, rng),
        hire_date=hire_date,
        events=tuple(sorted(events, key=lambda item: (item.effective_date, item.event_id))),
    )


def _apply_error(
    employee: IndependentEmployeeLedger,
    mechanism: str,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> tuple[IndependentEmployeeLedger, str, tuple[IndependentEvent, ...]]:
    events = list(employee.events)
    causal_events = []
    if mechanism == "wrong_employee_link":
        start = max(employee.hire_date, date(2024, 1, 1))
        for offset in range(5):
            injected = _event(
                policies,
                rng.randint(1, 1_000_000), offset, len(events), IndependentEventKind.SANCTION,
                start + timedelta(days=offset * 45), "reform-2023", category=1,
            )
            events.append(injected)
            causal_events.append(injected)
        evidence = "Five sanction events from another employee were linked during migration."
    elif mechanism == "missing_increment_import":
        increments = [event for event in events if event.kind is IndependentEventKind.SALARY_INCREMENT]
        if not increments:
            raise ValueError("missing-increment intervention requires an increment")
        removed = increments[len(increments) // 2]
        events.remove(removed)
        causal_events.append(removed)
        evidence = "One approved annual increment was omitted from an imported history."
    elif mechanism == "approval_bypass":
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        injected = _event(
            policies,
            rng.randint(1, 1_000_000), 2, len(events), IndependentEventKind.PROMOTION,
            _add_months(employee.hire_date, 36),
            _policy_id_for_date(_add_months(employee.hire_date, 36)),
            level_before="L7", level_after="L6", approval_reference=None,
            approval_status="bypassed",
        )
        events.append(injected)
        causal_events.append(injected)
        evidence = "A promotion was recorded after an approval workflow was bypassed."
    elif mechanism == "batch_retry":
        increments = [event for event in events if event.kind is IndependentEventKind.SALARY_INCREMENT]
        anchor = increments[-1] if increments else events[0]
        injected = _event(
            policies,
            rng.randint(1, 1_000_000), 3, len(events), IndependentEventKind.SALARY_INCREMENT,
            anchor.effective_date, anchor.policy_id,
            retry_of_event_id=anchor.event_id,
        )
        events.append(injected)
        causal_events.append(injected)
        evidence = "A retried import batch created a second increment record."
    else:
        raise ValueError(f"unsupported mechanism: {mechanism}")
    return _replace_events(employee, events), evidence, tuple(causal_events)


def _apply_rare_case(
    employee: IndependentEmployeeLedger,
    pattern: str,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> tuple[IndependentEmployeeLedger, str, str, tuple[IndependentEvent, ...]]:
    events = list(employee.events)
    if pattern == "grandfathered_policy":
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        promotion_date = max(
            _add_months(employee.hire_date, 30),
            date(2023, 1, 1),
        )
        injected = _event(
            policies,
            rng.randint(1, 1_000_000), 4, len(events), IndependentEventKind.PROMOTION,
            promotion_date, "legacy-pre-2023",
            level_before="L7", level_after="L6",
        )
        events.append(injected)
        evidence = "A documented grandfathering clause retained the earlier service requirement."
        mechanism = pattern
        causal_events = (injected,)
    elif pattern == "recognized_prior_service":
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        injected = _event(
            policies,
            rng.randint(1, 1_000_000), 5, len(events), IndependentEventKind.PROMOTION,
            _add_months(employee.hire_date, 24),
            _policy_id_for_date(_add_months(employee.hire_date, 24)),
            level_before="L7", level_after="L6", recognized_service_months=12,
        )
        events.append(injected)
        evidence = "Twelve months of prior public service were formally recognized."
        mechanism = pattern
        causal_events = (injected,)
    elif pattern == "delayed_bulk_recording":
        delayed = []
        causal_events_list = []
        for event in events:
            if (
                event.kind is IndependentEventKind.SALARY_INCREMENT
                and event.effective_date + timedelta(days=120) <= REFERENCE_DATE
            ):
                delayed_event = IndependentEvent(
                    **{**event.__dict__, "recorded_date": event.effective_date + timedelta(days=120)}
                )
                delayed.append(delayed_event)
                causal_events_list.append(delayed_event)
            else:
                delayed.append(event)
        events = delayed
        evidence = "A documented administrative backlog delayed recording without changing effective dates."
        mechanism = "delayed_bulk_recording"
        causal_events = tuple(causal_events_list)
    elif pattern == "late_correction":
        # A promotion was initially recorded with the wrong date (off by one
        # year), then a correction event was filed that supersedes it.  The
        # corrected effective date is policy-compliant; the original was not.
        # The rare-legitimate label marks the corrected history as lawful.
        promotion_events = [e for e in events if e.kind is IndependentEventKind.PROMOTION]
        if promotion_events:
            original = promotion_events[-1]
            # Original event had an erroneous effective date one year earlier.
            # The policy_id must reflect the policy applicable at that (wrong)
            # date, exactly as a real mis-filed record would have been stamped.
            erroneous_date = _add_months(original.effective_date, -12)
            # The mis-filed promotion was approved at the time (the error was
            # in the recorded date, not the approval). The correction later
            # supersedes it. Approval status stays within the audited domain
            # {approved, bypassed}; the correction_of link marks it superseded.
            erroneous = IndependentEvent(
                **{**original.__dict__,
                   "event_id": f"ERR-{original.event_id}",
                   "effective_date": erroneous_date,
                   "recorded_date": erroneous_date + timedelta(days=3),
                   "policy_id": _policy_id_for_date(erroneous_date),
                   "policy_version": _policy_version_for_event(
                       policies,
                       _policy_id_for_date(erroneous_date),
                       erroneous_date,
                   ),
                   "approval_status": "approved",
                   }
            )
            # Correction event supersedes the erroneous one
            corrected = IndependentEvent(
                **{**original.__dict__,
                   "event_id": f"COR-{original.event_id}",
                   "recorded_date": original.effective_date + timedelta(days=14),
                   "correction_of_event_id": erroneous.event_id,
                   "approval_status": "approved",
                   }
            )
            events = [e for e in events if e.event_id != original.event_id]
            events.extend([erroneous, corrected])
            causal_events = (corrected,)
        else:
            causal_events = ()
        evidence = "An initially mis-dated promotion was corrected via a formal amendment; the amended date satisfies the applicable policy."
        mechanism = "late_correction"
    else:  # policy_transition
        # Employee was hired under the legacy-pre-2023 policy and earned a
        # single lawful promotion inside that epoch.  The service requirement
        # is evaluated under the policy effective at the promotion date, not
        # the current reform-2023 policy.  This is the core scenario motivating
        # the bitemporal contract.
        #
        # Eligibility (see _eligible_for_rare_case) guarantees the employee is
        # on the progression track, already has a promotion, and was hired
        # early enough that a legacy-epoch promotion can meet the legacy L7
        # service requirement (30 months) on/before 2022-12-31.  We therefore
        # rebuild the promotion history as a SINGLE legacy-epoch L7->L6
        # promotion at a lawful date, discarding any stacked second promotion
        # so there is no same-day double promotion and no order violation.
        legacy_service_months = 30
        legacy_epoch_end = date(2022, 12, 31)
        # Earliest lawful date: hire + legacy L7 service requirement. This is
        # on/after hire_date by construction and, by eligibility, on/before the
        # legacy epoch end, so it sits strictly inside the legacy epoch.
        transition_date = _add_months(employee.hire_date, legacy_service_months)
        if transition_date > legacy_epoch_end:
            # Defensive: eligibility already rules this out; never reached in
            # practice, but keeps the invariant explicit.
            transition_date = legacy_epoch_end
        non_promotions = [
            event for event in events
            if event.kind is not IndependentEventKind.PROMOTION
        ]
        legacy_promotion = _event(
            policies,
            rng.randint(1, 1_000_000),
            6,
            len(non_promotions),
            IndependentEventKind.PROMOTION,
            transition_date,
            "legacy-pre-2023",
            level_before="L7",
            level_after="L6",
        )
        events = non_promotions + [legacy_promotion]
        causal_events = (legacy_promotion,)
        evidence = "Single legacy-pre-2023 promotion earned inside the legacy epoch; it satisfies the then-current 30-month service requirement even though the current reform-2023 policy requires more service."
        mechanism = "policy_transition"
    return _replace_events(employee, events), evidence, mechanism, causal_events


def _replace_events(
    employee: IndependentEmployeeLedger,
    events: list[IndependentEvent],
) -> IndependentEmployeeLedger:
    # A promotion is superseded when its event_id is referenced by another
    # event's correction_of_event_id.  The current level is the level_after of
    # the LAST effective (non-superseded) promotion ordered by
    # (effective_date, event_id).  With no effective promotion, keep the
    # employee's existing current_level.
    superseded_ids = {
        event.correction_of_event_id
        for event in events
        if event.correction_of_event_id is not None
    }
    effective_promotions = [
        event for event in events
        if event.kind is IndependentEventKind.PROMOTION
        and event.event_id not in superseded_ids
    ]
    if effective_promotions:
        last_promotion = max(
            effective_promotions,
            key=lambda item: (item.effective_date, item.event_id),
        )
        current_level = last_promotion.level_after
    else:
        current_level = employee.current_level
    return IndependentEmployeeLedger(
        employee_id=employee.employee_id,
        split=employee.split,
        track=employee.track,
        current_level=current_level,
        department=employee.department,
        role=employee.role,
        date_of_birth=employee.date_of_birth,
        hire_date=employee.hire_date,
        events=tuple(sorted(events, key=lambda item: (item.effective_date, item.event_id))),
    )


def _event(
    policies: tuple[IndependentPolicyCard, ...],
    seed: int,
    employee_index: int,
    sequence: int,
    kind: IndependentEventKind,
    effective_date: date,
    policy_id: str,
    **kwargs: object,
) -> IndependentEvent:
    digest = sha256(f"{seed}:{employee_index}:{sequence}".encode("utf-8")).hexdigest()[:14]
    approval_reference = kwargs.pop(
        "approval_reference", f"AR-{digest[2:10]}"
    )
    return IndependentEvent(
        event_id=f"EV-{digest}",
        kind=kind,
        effective_date=effective_date,
        recorded_date=min(
            REFERENCE_DATE,
            effective_date + timedelta(days=(employee_index + sequence) % 19),
        ),
        policy_id=policy_id,
        policy_version=_policy_version_for_event(
            policies, policy_id, effective_date
        ),
        approval_reference=approval_reference,
        **kwargs,
    )


def _policy_version_for_event(
    policies: tuple[IndependentPolicyCard, ...],
    policy_id: str,
    effective_date: date,
) -> str:
    """Resolve the exact policy version stamped on an event at creation time."""

    matching_id = [card for card in policies if card.policy_id == policy_id]
    effective = [
        card
        for card in matching_id
        if card.effective_from <= effective_date
        and (card.effective_to is None or effective_date <= card.effective_to)
    ]
    if len(effective) == 1:
        return effective[0].version
    # A uniquely named earlier policy may be selected after its effective
    # period when an explicit grandfathering entitlement authorizes it.
    if not effective and len(matching_id) == 1:
        return matching_id[0].version
    raise ValueError(
        "cannot resolve one policy version for event: "
        f"policy_id={policy_id!r}, effective_date={effective_date.isoformat()}"
    )


def _policy_id_for_date(value: date) -> str:
    return (
        "reform-2023" if value >= date(2023, 1, 1)
        else "legacy-pre-2023"
    )


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, 28))


def _birth_date_for_hire(hire_date: date, rng: Random) -> date:
    """Generate DOB and hire date as one plausible pair.

    The sampled age is a realism constraint for fictional data, not a legal
    minimum-employment-age claim. Account for whether the birthday has occurred
    by the hire date so the realized age equals the sampled age.
    """

    age_at_hire = rng.randint(
        _MIN_GENERATED_HIRE_AGE,
        _MAX_GENERATED_HIRE_AGE,
    )
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    birth_year = hire_date.year - age_at_hire
    if (month, day) > (hire_date.month, hire_date.day):
        birth_year -= 1
    return date(birth_year, month, day)
