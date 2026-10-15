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
    effective_from: date
    service_months_by_level: dict[str, int]
    grandfather_previous_policy: bool


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
        if not 0 < self.error_rate < 0.3 or not 0 < self.rare_rate < 0.3:
            raise ValueError("scenario rates must be between zero and 0.3")


@dataclass(frozen=True)
class IndependentEvent:
    event_id: str
    kind: IndependentEventKind
    effective_date: date
    recorded_date: date
    policy_id: str
    level_before: str | None = None
    level_after: str | None = None
    category: int | None = None
    resolved_date: date | None = None
    approval_reference: str | None = None
    correction_of_event_id: str | None = None


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
    evidence: str


@dataclass(frozen=True)
class IndependentWorld:
    spec: IndependentScenarioSpec
    policies: tuple[IndependentPolicyCard, ...]
    employees: tuple[IndependentEmployeeLedger, ...]
    truth: tuple[IndependentTruthEntry, ...]


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
    return "grandfathered_policy", "recognized_prior_service", "delayed_bulk_recording"


def independent_scenario_matrix(
    employee_count: int = 360,
) -> tuple[IndependentScenarioSpec, ...]:
    """Return 12 predeclared development-only scenarios."""

    specs = []
    for index, (population, mechanism) in enumerate(
        (population, mechanism)
        for population in population_families()
        for mechanism in anomaly_mechanisms()
    ):
        specs.append(IndependentScenarioSpec(
            scenario_id=f"ind-dev-{index + 1:02d}",
            run_purpose="independent_development",
            seed=81001 + index * 17,
            split_seed=81003 + index * 17,
            model_seed=81007 + index * 17,
            employee_count=employee_count,
            population=population,
            mechanism=mechanism,
            rare_pattern=rare_legitimate_patterns()[index % len(rare_legitimate_patterns())],
        ))
    return tuple(specs)


def generate_independent_world(spec: IndependentScenarioSpec) -> IndependentWorld:
    spec.validate()
    policies = _policy_cards()
    split_by_index = _split_assignments(spec)
    truth_plan = _truth_plan(spec, split_by_index)
    employees = []
    truth = []
    for index in range(spec.employee_count):
        rng = Random(spec.seed * 100_003 + index * 97)
        employee = _base_employee(index, split_by_index[index], spec, policies, rng)
        category = truth_plan[index]
        mechanism = "none"
        evidence = "No injected administrative discrepancy."
        if category is TruthCategory.RARE_LEGITIMATE:
            employee, evidence = _apply_rare_case(employee, spec.rare_pattern, policies, rng)
            mechanism = spec.rare_pattern
        elif category is not TruthCategory.ORDINARY_LEGITIMATE:
            employee, evidence = _apply_error(employee, spec.mechanism, policies, rng)
            mechanism = spec.mechanism
        employees.append(employee)
        truth.append(IndependentTruthEntry(
            employee_id=employee.employee_id,
            category=category,
            mechanism=mechanism,
            evidence=evidence,
        ))
    return IndependentWorld(spec, policies, tuple(employees), tuple(truth))


def _policy_cards() -> tuple[IndependentPolicyCard, ...]:
    return (
        IndependentPolicyCard(
            "legacy-2018",
            date(2018, 1, 1),
            {"L7": 30, "L6": 30, "L5": 42, "L4": 48, "L3": 54, "L2": 60},
            True,
        ),
        IndependentPolicyCard(
            "reform-2023",
            date(2023, 1, 1),
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
    split_by_index: dict[int, IndependentSplit],
) -> dict[int, TruthCategory]:
    result = {index: TruthCategory.ORDINARY_LEGITIMATE for index in split_by_index}
    rng = Random(spec.seed + 41)
    for split in IndependentSplit:
        indices = [index for index, assigned in split_by_index.items() if assigned is split]
        rng.shuffle(indices)
        error_count = max(2, round(len(indices) * spec.error_rate))
        rare_count = max(2, round(len(indices) * spec.rare_rate))
        error_category = (
            TruthCategory.EXPLICIT_POLICY_VIOLATION
            if spec.mechanism == "approval_bypass"
            else TruthCategory.CONFIRMED_PROCESS_ERROR
            if spec.mechanism == "wrong_employee_link"
            else TruthCategory.CONFIRMED_RECORDING_ERROR
        )
        for index in indices[:error_count]:
            result[index] = error_category
        for index in indices[error_count:error_count + rare_count]:
            result[index] = TruthCategory.RARE_LEGITIMATE
    return result


def _base_employee(
    index: int,
    split: IndependentSplit,
    spec: IndependentScenarioSpec,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> IndependentEmployeeLedger:
    hire_ranges = {
        "stable_administration": (2012, 2020),
        "rapid_expansion": (2021, 2025),
        "merger_migration": (2015, 2024),
    }
    first_year, last_year = hire_ranges[spec.population]
    hire_date = date(rng.randint(first_year, last_year), rng.randint(1, 12), rng.randint(1, 28))
    track_probability = 0.82 if spec.population != "rapid_expansion" else 0.68
    track = (
        IndependentTrack.PROGRESSION
        if rng.random() < track_probability
        else IndependentTrack.INCREMENT_ONLY
    )
    employee_id = f"I-{index + 1:05d}"
    events = [_event(spec.seed, index, 0, IndependentEventKind.HIRE, hire_date, "legacy-2018")]
    increment_date = _add_months(hire_date, 12)
    sequence = 1
    while increment_date <= REFERENCE_DATE:
        events.append(_event(
            spec.seed, index, sequence, IndependentEventKind.SALARY_INCREMENT,
            increment_date, "reform-2023" if increment_date >= date(2023, 1, 1) else "legacy-2018",
        ))
        sequence += 1
        increment_date = _add_months(increment_date, 12)
    current_level = None
    if track is IndependentTrack.PROGRESSION:
        current_level = "L7"
        promotion_date = _add_months(hire_date, 36)
        if promotion_date <= REFERENCE_DATE:
            events.append(_event(
                spec.seed, index, sequence, IndependentEventKind.PROMOTION,
                promotion_date, "reform-2023", level_before="L7", level_after="L6",
            ))
            current_level = "L6"
            sequence += 1
    events.append(_event(
        spec.seed, index, sequence, IndependentEventKind.PERFORMANCE_REVIEW,
        min(REFERENCE_DATE, _add_months(hire_date, 18)), "reform-2023",
    ))
    return IndependentEmployeeLedger(
        employee_id=employee_id,
        split=split,
        track=track,
        current_level=current_level,
        department=("Operations", "Engineering", "Finance")[index % 3],
        role="Specialist" if track is IndependentTrack.PROGRESSION else "Support",
        date_of_birth=date(rng.randint(1965, 2001), rng.randint(1, 12), rng.randint(1, 28)),
        hire_date=hire_date,
        events=tuple(sorted(events, key=lambda item: (item.effective_date, item.event_id))),
    )


def _apply_error(
    employee: IndependentEmployeeLedger,
    mechanism: str,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> tuple[IndependentEmployeeLedger, str]:
    events = list(employee.events)
    if mechanism == "wrong_employee_link":
        start = max(employee.hire_date, date(2024, 1, 1))
        for offset in range(5):
            events.append(_event(
                rng.randint(1, 1_000_000), offset, len(events), IndependentEventKind.SANCTION,
                start + timedelta(days=offset * 45), "reform-2023", category=1,
            ))
        evidence = "Five sanction events from another employee were linked during migration."
    elif mechanism == "missing_increment_import":
        increments = [event for event in events if event.kind is IndependentEventKind.SALARY_INCREMENT]
        if len(increments) >= 3:
            removed = increments[len(increments) // 2]
            events.remove(removed)
        else:
            events.append(_event(
                rng.randint(1, 1_000_000), 1, len(events), IndependentEventKind.SALARY_INCREMENT,
                min(REFERENCE_DATE, _add_months(employee.hire_date, 30)), "reform-2023",
            ))
        evidence = "One approved annual increment was omitted from an imported history."
    elif mechanism == "approval_bypass":
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        events.append(_event(
            rng.randint(1, 1_000_000), 2, len(events), IndependentEventKind.PROMOTION,
            _add_months(employee.hire_date, 14), "reform-2023",
            level_before="L7", level_after="L6",
        ))
        evidence = "A promotion was recorded after an approval workflow was bypassed."
    elif mechanism == "batch_retry":
        increments = [event for event in events if event.kind is IndependentEventKind.SALARY_INCREMENT]
        anchor = increments[-1] if increments else events[0]
        events.append(_event(
            rng.randint(1, 1_000_000), 3, len(events), IndependentEventKind.SALARY_INCREMENT,
            anchor.effective_date, anchor.policy_id,
            correction_of_event_id=anchor.event_id,
        ))
        evidence = "A retried import batch created a second increment record."
    else:
        raise ValueError(f"unsupported mechanism: {mechanism}")
    return _replace_events(employee, events), evidence


def _apply_rare_case(
    employee: IndependentEmployeeLedger,
    pattern: str,
    policies: tuple[IndependentPolicyCard, ...],
    rng: Random,
) -> tuple[IndependentEmployeeLedger, str]:
    events = list(employee.events)
    if pattern == "grandfathered_policy" and employee.track is IndependentTrack.PROGRESSION:
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        events.append(_event(
            rng.randint(1, 1_000_000), 4, len(events), IndependentEventKind.PROMOTION,
            _add_months(employee.hire_date, 30), "legacy-2018",
            level_before="L7", level_after="L6",
        ))
        evidence = "A documented grandfathering clause retained the earlier service requirement."
    elif pattern == "recognized_prior_service" and employee.track is IndependentTrack.PROGRESSION:
        events = [event for event in events if event.kind is not IndependentEventKind.PROMOTION]
        events.append(_event(
            rng.randint(1, 1_000_000), 5, len(events), IndependentEventKind.PROMOTION,
            _add_months(employee.hire_date, 24), "reform-2023",
            level_before="L7", level_after="L6",
        ))
        evidence = "Twelve months of prior public service were formally recognized."
    else:
        delayed = []
        for event in events:
            if event.kind is IndependentEventKind.SALARY_INCREMENT:
                delayed.append(IndependentEvent(
                    **{**event.__dict__, "recorded_date": event.effective_date + timedelta(days=120)}
                ))
            else:
                delayed.append(event)
        events = delayed
        evidence = "A documented administrative backlog delayed recording without changing effective dates."
    return _replace_events(employee, events), evidence


def _replace_events(
    employee: IndependentEmployeeLedger,
    events: list[IndependentEvent],
) -> IndependentEmployeeLedger:
    return IndependentEmployeeLedger(
        employee_id=employee.employee_id,
        split=employee.split,
        track=employee.track,
        current_level=(
            "L6" if any(event.kind is IndependentEventKind.PROMOTION for event in events)
            else employee.current_level
        ),
        department=employee.department,
        role=employee.role,
        date_of_birth=employee.date_of_birth,
        hire_date=employee.hire_date,
        events=tuple(sorted(events, key=lambda item: (item.effective_date, item.event_id))),
    )


def _event(
    seed: int,
    employee_index: int,
    sequence: int,
    kind: IndependentEventKind,
    effective_date: date,
    policy_id: str,
    **kwargs: object,
) -> IndependentEvent:
    digest = sha256(f"{seed}:{employee_index}:{sequence}".encode("utf-8")).hexdigest()[:14]
    return IndependentEvent(
        event_id=f"EV-{digest}",
        kind=kind,
        effective_date=effective_date,
        recorded_date=effective_date + timedelta(days=(employee_index + sequence) % 19),
        policy_id=policy_id,
        approval_reference=f"AR-{digest[2:10]}",
        **kwargs,
    )


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, 28))
