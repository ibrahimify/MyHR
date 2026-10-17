"""Independent scenario families for the locked TDK v2 protocol.

The generator deliberately does not call feature extraction or model code. It
simulates histories from policy and population parameters, then injects errors
through a separate set of mechanisms. Holdout scenarios are intentionally not
defined here while the protocol is in draft state.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from hashlib import sha256
import json
from random import Random

from .policy_model import PromotionPolicy
from .synthetic_data import (
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


REFERENCE_DATE = date(2026, 12, 31)
PROGRESSION_ANOMALIES = (
    AnomalyType.INCONSISTENT_DATES,
    AnomalyType.FREQUENT_PROMOTIONS,
    AnomalyType.EXCESSIVE_SANCTIONS,
    AnomalyType.UNUSUAL_ADMIN_INTERVAL,
)


@dataclass(frozen=True)
class PopulationProfile:
    profile_id: str
    promotion_track_ratio: float
    earliest_hire_year: int
    latest_hire_year: int
    commendation_probability: float
    sanction_probability: float
    performance_review_probability: float


@dataclass(frozen=True)
class ScenarioConfig:
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
    anomaly_rate: float = 0.10
    rare_legitimate_rate: float = 0.05
    train_ratio: float = 0.60
    validation_ratio: float = 0.20
    test_ratio: float = 0.20

    def validate(self) -> None:
        if self.run_purpose not in {"development", "validation"}:
            raise ValueError("v2 holdout scenarios remain locked")
        if self.employee_count < 100:
            raise ValueError("employee_count must be at least 100 for scenario experiments")
        if self.policy_profile not in policy_profiles():
            raise ValueError(f"unknown policy profile: {self.policy_profile}")
        if self.population_profile not in population_profiles():
            raise ValueError(f"unknown population profile: {self.population_profile}")
        if self.anomaly_mechanism not in {"mixed_calendar", "mixed_process", "mixed_density"}:
            raise ValueError(f"unknown anomaly mechanism: {self.anomaly_mechanism}")
        if self.rare_pattern not in {"credit_mix", "credit_with_delay", "boundary_case"}:
            raise ValueError(f"unknown rare pattern: {self.rare_pattern}")
        if self.anomaly_rate <= 0 or self.rare_legitimate_rate <= 0:
            raise ValueError("scenario rates must be positive")
        if self.anomaly_rate + self.rare_legitimate_rate >= 0.5:
            raise ValueError("scenario rates leave too little ordinary-clean data")
        if abs(self.train_ratio + self.validation_ratio + self.test_ratio - 1.0) > 1e-9:
            raise ValueError("split ratios must sum to 1.0")

    def run_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return sha256(payload).hexdigest()[:16]


@dataclass(frozen=True)
class ScenarioDataset:
    config: ScenarioConfig
    policy: PromotionPolicy
    population: PopulationProfile
    dataset: SyntheticDataset


def policy_profiles() -> dict[str, PromotionPolicy]:
    """Return deliberately different policy configurations."""

    return {
        "standard": PromotionPolicy(),
        "accelerated": PromotionPolicy(
            service_months_by_level={"L7": 30, "L6": 30, "L5": 36, "L4": 42, "L3": 42, "L2": 54},
            commendation_month_credit={1: 2, 2: 4, 3: 7},
            sanction_month_delay={1: 2, 2: 5, 3: 10},
        ),
        "conservative": PromotionPolicy(
            service_months_by_level={"L7": 42, "L6": 42, "L5": 48, "L4": 54, "L3": 54, "L2": 60},
            commendation_month_credit={1: 1, 2: 2, 3: 4},
            sanction_month_delay={1: 4, 2: 8, 3: 12},
        ),
    }


def population_profiles() -> dict[str, PopulationProfile]:
    return {
        "balanced": PopulationProfile("balanced", 0.80, 2012, 2023, 0.42, 0.16, 0.72),
        "experienced": PopulationProfile("experienced", 0.88, 2008, 2020, 0.55, 0.20, 0.84),
        "mixed_workforce": PopulationProfile("mixed_workforce", 0.62, 2014, 2024, 0.34, 0.12, 0.58),
    }


def scenario_matrix(run_purpose: str, count: int = 30, employee_count: int = 600) -> tuple[ScenarioConfig, ...]:
    """Build a predeclared development or validation matrix.

    The seed ranges are separate. No holdout seed range exists while the
    protocol is locked.
    """

    if run_purpose not in {"development", "validation"}:
        raise ValueError("holdout scenario generation is locked")
    if count < 1:
        raise ValueError("count must be positive")
    base = 31000 if run_purpose == "development" else 51000
    policies = tuple(policy_profiles())
    populations = tuple(population_profiles())
    mechanisms = ("mixed_calendar", "mixed_process", "mixed_density")
    rare_patterns = ("credit_mix", "credit_with_delay", "boundary_case")
    anomaly_rates = (0.06, 0.10, 0.14)
    rare_rates = (0.03, 0.05, 0.08)
    configs = []
    for index in range(count):
        policy_index = index % len(policies)
        population_index = (index // len(policies)) % len(populations)
        mechanism_index = (index // (len(policies) * len(populations))) % len(mechanisms)
        rare_index = (policy_index + 2 * population_index + mechanism_index) % len(rare_patterns)
        anomaly_rate_index = (policy_index + population_index + mechanism_index) % len(anomaly_rates)
        rare_rate_index = (2 * policy_index + population_index + 2 * mechanism_index) % len(rare_rates)
        config = ScenarioConfig(
            scenario_id=f"{run_purpose[:3]}-{index + 1:03d}",
            run_purpose=run_purpose,
            dataset_seed=base + index * 11 + 1,
            split_seed=base + index * 11 + 3,
            model_seed=base + index * 11 + 7,
            employee_count=employee_count,
            policy_profile=policies[policy_index],
            population_profile=populations[population_index],
            anomaly_mechanism=mechanisms[mechanism_index],
            rare_pattern=rare_patterns[rare_index],
            anomaly_rate=anomaly_rates[anomaly_rate_index],
            rare_legitimate_rate=rare_rates[rare_rate_index],
        )
        config.validate()
        configs.append(config)
    return tuple(configs)


def generate_scenario_dataset(config: ScenarioConfig) -> ScenarioDataset:
    config.validate()
    policy = policy_profiles()[config.policy_profile]
    population = population_profiles()[config.population_profile]
    split_by_index = _split_assignments(config)
    labels = _label_assignments(config, split_by_index)
    records = []
    for index in range(config.employee_count):
        record_rng = _record_rng(config, index)
        record = _simulate_base_history(index, split_by_index[index], policy, population, record_rng)
        label = labels[index]
        if label is AnomalyType.POLICY_LEGITIMATE_RARE_CASE:
            record = _inject_rare_legitimate(record, policy, config.rare_pattern, record_rng)
        elif label is not AnomalyType.CLEAN:
            record = _inject_anomaly(record, policy, label, config.anomaly_mechanism, record_rng)
        records.append(record)

    split_counts = Counter(record.split.value for record in records)
    label_counts = Counter(label.value for record in records for label in record.anomaly_labels)
    dataset = SyntheticDataset(
        records=tuple(records),
        metadata=SyntheticDatasetMetadata(
            schema_version="tdk-scenario-v2",
            run_id=config.run_id(),
            seed=config.dataset_seed,
            employee_count=config.employee_count,
            split_counts={split.value: split_counts.get(split.value, 0) for split in DatasetSplit},
            label_counts={label.value: label_counts.get(label.value, 0) for label in AnomalyType},
        ),
    )
    return ScenarioDataset(config=config, policy=policy, population=population, dataset=dataset)


def _split_assignments(config: ScenarioConfig) -> dict[int, DatasetSplit]:
    indices = list(range(config.employee_count))
    Random(config.split_seed).shuffle(indices)
    train_end = int(config.employee_count * config.train_ratio)
    validation_end = train_end + int(config.employee_count * config.validation_ratio)
    assignments = {}
    for index in indices[:train_end]:
        assignments[index] = DatasetSplit.TRAIN
    for index in indices[train_end:validation_end]:
        assignments[index] = DatasetSplit.VALIDATION
    for index in indices[validation_end:]:
        assignments[index] = DatasetSplit.TEST
    return assignments


def _label_assignments(
    config: ScenarioConfig,
    split_by_index: dict[int, DatasetSplit],
) -> dict[int, AnomalyType]:
    labels = {index: AnomalyType.CLEAN for index in split_by_index}
    rng = Random(config.dataset_seed + 101)
    for split in DatasetSplit:
        candidates = [index for index, value in split_by_index.items() if value is split]
        rng.shuffle(candidates)
        anomaly_count = round(len(candidates) * config.anomaly_rate)
        rare_count = round(len(candidates) * config.rare_legitimate_rate)
        promotion_candidates = [index for index in candidates if _is_promotion_index(index, config, split)]
        anomaly_candidates = promotion_candidates + [index for index in candidates if index not in promotion_candidates]
        selected_anomalies = anomaly_candidates[:anomaly_count]
        remaining_promotion = [index for index in promotion_candidates if index not in selected_anomalies]
        if len(remaining_promotion) < rare_count:
            raise ValueError("not enough promotion-track records for rare legitimate allocation")
        for offset, index in enumerate(selected_anomalies):
            labels[index] = PROGRESSION_ANOMALIES[offset % len(PROGRESSION_ANOMALIES)]
        for index in remaining_promotion[:rare_count]:
            labels[index] = AnomalyType.POLICY_LEGITIMATE_RARE_CASE
    return labels


def _is_promotion_index(index: int, config: ScenarioConfig, split: DatasetSplit) -> bool:
    profile = population_profiles()[config.population_profile]
    rng = _record_rng(config, index)
    return rng.random() < profile.promotion_track_ratio


def _record_rng(config: ScenarioConfig, index: int) -> Random:
    return Random(config.dataset_seed * 1_000_003 + index * 97)


def _simulate_base_history(
    index: int,
    split: DatasetSplit,
    policy: PromotionPolicy,
    population: PopulationProfile,
    rng: Random,
) -> WorkforceHistoryRecord:
    employee_number = index + 1
    track = EmploymentTrack.PROMOTION if rng.random() < population.promotion_track_ratio else EmploymentTrack.OTHER
    hire_date = date(
        rng.randint(population.earliest_hire_year, population.latest_hire_year),
        rng.randint(1, 12),
        rng.randint(1, 28),
    )
    events = [AdministrativeEvent(
        AdministrativeEventType.HIRE,
        hire_date,
        f"S2-HIRE-{employee_number:05d}",
        level_after="L7" if track is EmploymentTrack.PROMOTION else None,
    )]
    current_level = "L7" if track is EmploymentTrack.PROMOTION else None
    race_start = hire_date
    promotion_step = 0
    if track is EmploymentTrack.PROMOTION:
        while current_level in policy.service_months_by_level and promotion_step < 3:
            required = policy.required_service_months(current_level) or 36
            role_events, credit, delay = _normal_role_events(
                employee_number,
                promotion_step,
                race_start,
                required,
                policy,
                population,
                rng,
            )
            wait_months = max(12, required - credit + delay + rng.randint(0, 14))
            promotion_date = _add_months(race_start, wait_months)
            if promotion_date > REFERENCE_DATE - timedelta(days=120):
                events.extend(event for event in role_events if event.event_date <= REFERENCE_DATE)
                break
            events.extend(role_events)
            next_level = _next_level(current_level)
            if next_level is None:
                break
            events.append(AdministrativeEvent(
                AdministrativeEventType.PROMOTION,
                promotion_date,
                f"S2-PROM-{employee_number:05d}-{promotion_step + 1}",
                level_before=current_level,
                level_after=next_level,
            ))
            current_level = next_level
            race_start = promotion_date
            promotion_step += 1

    for year in range(hire_date.year + 1, REFERENCE_DATE.year + 1):
        increment_date = _safe_date(year, hire_date.month, hire_date.day) + timedelta(days=rng.randint(-25, 25))
        if increment_date <= REFERENCE_DATE:
            events.append(AdministrativeEvent(
                AdministrativeEventType.SALARY_INCREMENT,
                increment_date,
                f"S2-INC-{employee_number:05d}-{year}",
            ))
        if rng.random() < population.performance_review_probability:
            review_date = _safe_date(year, min(12, hire_date.month + 1), hire_date.day)
            if review_date <= REFERENCE_DATE:
                events.append(AdministrativeEvent(
                    AdministrativeEventType.PERFORMANCE_REVIEW,
                    review_date,
                    f"S2-REV-{employee_number:05d}-{year}",
                    value_after=rng.randint(55, 96),
                ))

    identity = EmployeeIdentity(
        employee_id=f"S2-{employee_number:05d}",
        full_name=f"Synthetic Person {employee_number:05d}",
        date_of_birth=date(rng.randint(1965, 2002), rng.randint(1, 12), rng.randint(1, 28)),
        national_id=f"S2N-{employee_number:08d}",
        email=f"person{employee_number:05d}@scenario.invalid",
    )
    return WorkforceHistoryRecord(
        identity=identity,
        split=split,
        employment_track=track,
        current_level=current_level,
        department=("Engineering", "Operations", "Finance", "HR", "Compliance")[index % 5],
        role="Progression role" if track is EmploymentTrack.PROMOTION else "Increment-only role",
        hire_date=hire_date,
        events=tuple(sorted(events, key=lambda event: (event.event_date, event.source_id))),
    )


def _normal_role_events(
    employee_number: int,
    step: int,
    race_start: date,
    required_months: int,
    policy: PromotionPolicy,
    population: PopulationProfile,
    rng: Random,
) -> tuple[list[AdministrativeEvent], int, int]:
    events = []
    credits = 0
    delays = 0
    commendation_count = rng.choices((0, 1, 2, 3), weights=(42, 33, 18, 7))[0]
    if rng.random() > population.commendation_probability:
        commendation_count = 0
    for offset in range(commendation_count):
        category = rng.choice(tuple(policy.commendation_month_credit))
        credits += policy.commendation_credit(category)
        events.append(AdministrativeEvent(
            AdministrativeEventType.COMMENDATION,
            _add_months(race_start, 3 + offset * 3 + rng.randint(0, 1)),
            f"S2-COM-{employee_number:05d}-{step}-{offset}",
            category=category,
        ))
    if rng.random() < population.sanction_probability:
        category = rng.choice(tuple(policy.sanction_month_delay))
        resolved = rng.random() < 0.45
        issued = _add_months(race_start, rng.randint(4, 8))
        resolved_date = _add_months(issued, 1) if resolved else None
        if not resolved:
            delays += policy.sanction_delay(category)
        events.append(AdministrativeEvent(
            AdministrativeEventType.SANCTION,
            issued,
            f"S2-SAN-{employee_number:05d}-{step}",
            category=category,
            is_resolved=resolved,
            resolved_date=resolved_date,
        ))
    return events, credits, delays


def _inject_anomaly(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    label: AnomalyType,
    mechanism: str,
    rng: Random,
) -> WorkforceHistoryRecord:
    events = list(record.events)
    employee_id = record.identity.employee_id
    if label is AnomalyType.INCONSISTENT_DATES:
        event_type = AdministrativeEventType.PROMOTION if mechanism != "mixed_process" else AdministrativeEventType.ORGANIZATION_CHANGE
        events.append(AdministrativeEvent(
            event_type,
            record.hire_date - timedelta(days=rng.randint(30, 500)),
            f"S2-BAD-DATE-{employee_id}",
            level_before="L7" if event_type is AdministrativeEventType.PROMOTION else None,
            level_after="L6" if event_type is AdministrativeEventType.PROMOTION else None,
        ))
    elif label is AnomalyType.FREQUENT_PROMOTIONS:
        events = [event for event in events if event.event_type not in {
            AdministrativeEventType.PROMOTION,
            AdministrativeEventType.COMMENDATION,
            AdministrativeEventType.SANCTION,
        }]
        required = policy.required_service_months("L7") or 36
        observed = rng.randint(8, max(9, required - 10))
        partial_credit = rng.choice((0, 1, 2))
        for offset in range(partial_credit):
            events.append(AdministrativeEvent(
                AdministrativeEventType.COMMENDATION,
                _add_months(record.hire_date, 3 + offset * 4),
                f"S2-PARTIAL-COM-{employee_id}-{offset}",
                category=1,
            ))
        events.append(AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            _add_months(record.hire_date, observed),
            f"S2-FAST-PROM-{employee_id}",
            level_before="L7",
            level_after="L6",
        ))
    elif label is AnomalyType.EXCESSIVE_SANCTIONS:
        count = rng.randint(4, 8) if mechanism != "mixed_density" else rng.randint(6, 10)
        for offset in range(count):
            events.append(AdministrativeEvent(
                AdministrativeEventType.SANCTION,
                _add_months(record.hire_date, 2 + offset * rng.choice((1, 2, 3))),
                f"S2-SAN-BURST-{employee_id}-{offset}",
                category=rng.choice(tuple(policy.sanction_month_delay)),
                is_resolved=rng.random() < 0.25,
            ))
    elif label is AnomalyType.UNUSUAL_ADMIN_INTERVAL:
        anchor = _add_months(record.hire_date, rng.randint(12, 36))
        gap_days = rng.choice((2, 7, 21, 45))
        events.extend((
            AdministrativeEvent(
                AdministrativeEventType.SALARY_INCREMENT,
                anchor,
                f"S2-CLOSE-INC-A-{employee_id}",
            ),
            AdministrativeEvent(
                AdministrativeEventType.SALARY_INCREMENT,
                anchor + timedelta(days=gap_days),
                f"S2-CLOSE-INC-B-{employee_id}",
            ),
        ))
    current_level = "L6" if label is AnomalyType.FREQUENT_PROMOTIONS else record.current_level
    return WorkforceHistoryRecord(
        identity=record.identity,
        split=record.split,
        employment_track=record.employment_track,
        current_level=current_level,
        department=record.department,
        role=record.role,
        hire_date=record.hire_date,
        events=tuple(sorted(events, key=lambda event: (event.event_date, event.source_id))),
        anomaly_labels=(label,),
    )


def _inject_rare_legitimate(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    pattern: str,
    rng: Random,
) -> WorkforceHistoryRecord:
    if record.employment_track is not EmploymentTrack.PROMOTION:
        raise ValueError("rare progression histories require the promotion track")
    events = [event for event in record.events if event.event_type not in {
        AdministrativeEventType.PROMOTION,
        AdministrativeEventType.COMMENDATION,
        AdministrativeEventType.SANCTION,
    }]
    required = policy.required_service_months("L7") or 36
    categories = list(policy.commendation_month_credit)
    rng.shuffle(categories)
    chosen = (categories * 2)[:rng.randint(2, 3)]
    credit = sum(policy.commendation_credit(category) for category in chosen)
    delay = 0
    if pattern == "credit_with_delay":
        sanction_category = min(policy.sanction_month_delay)
        delay = policy.sanction_delay(sanction_category)
        if credit <= delay:
            strongest = max(policy.commendation_month_credit, key=policy.commendation_credit)
            chosen = [strongest] * policy.max_commendations_per_role
            credit = sum(policy.commendation_credit(category) for category in chosen)
        events.append(AdministrativeEvent(
            AdministrativeEventType.SANCTION,
            _add_months(record.hire_date, 7),
            f"S2-RARE-SAN-{record.identity.employee_id}",
            category=sanction_category,
            is_resolved=False,
        ))
    target_shortfall = max(1, credit - delay)
    if pattern == "boundary_case":
        observed = required - target_shortfall + rng.choice((0, 1))
    else:
        observed = required - target_shortfall + rng.randint(0, 2)
    for offset, category in enumerate(chosen):
        events.append(AdministrativeEvent(
            AdministrativeEventType.COMMENDATION,
            _add_months(record.hire_date, 4 + offset * 5),
            f"S2-RARE-COM-{record.identity.employee_id}-{offset}",
            category=category,
        ))
    events.append(AdministrativeEvent(
        AdministrativeEventType.PROMOTION,
        _add_months(record.hire_date, observed),
        f"S2-RARE-PROM-{record.identity.employee_id}",
        level_before="L7",
        level_after="L6",
    ))
    return WorkforceHistoryRecord(
        identity=record.identity,
        split=record.split,
        employment_track=record.employment_track,
        current_level="L6",
        department=record.department,
        role=record.role,
        hire_date=record.hire_date,
        events=tuple(sorted(events, key=lambda event: (event.event_date, event.source_id))),
        anomaly_labels=(AnomalyType.POLICY_LEGITIMATE_RARE_CASE,),
    )


def _next_level(level: str) -> str | None:
    levels = ("L7", "L6", "L5", "L4", "L3", "L2", "L1")
    try:
        index = levels.index(level)
    except ValueError:
        return None
    return levels[index + 1] if index + 1 < len(levels) else None


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return _safe_date(year, month, value.day)


def _safe_date(year: int, month: int, day: int) -> date:
    return date(year, max(1, min(month, 12)), max(1, min(day, 28)))
