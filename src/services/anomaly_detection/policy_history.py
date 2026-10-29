"""Policy assessments for every completed promotion in an employee history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .policy_model import PromotionPolicy, PromotionRaceInput, calculate_promotion_race
from .synthetic_data import AdministrativeEvent, AdministrativeEventType, WorkforceHistoryRecord


@dataclass(frozen=True)
class PolicyEpoch:
    """One bitemporal policy version available to historical replay."""

    policy_id: str
    version: str
    valid_from: date
    valid_to: date | None
    recorded_at: date
    jurisdiction: str
    policy: PromotionPolicy
    grandfather_previous_policy: bool = False

    def applies(self, effective_date: date, known_at: date, jurisdiction: str) -> bool:
        return (
            self.valid_from <= effective_date
            and (self.valid_to is None or effective_date <= self.valid_to)
            and self.recorded_at <= known_at
            and self.jurisdiction == jurisdiction
        )


@dataclass(frozen=True)
class PromotionPolicyAssessment:
    """Policy evidence calculated at one completed promotion."""

    event_source_id: str
    observed_service_months: int
    required_service_months: int
    commendation_credit_months: int
    sanction_delay_months: int
    adjusted_service_months: int
    service_deficit_months: int
    raw_service_deficit_months: int

    @property
    def required_service_denominator(self) -> int:
        return self.required_service_months or 1


def assess_promotion_history(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    policy_epochs: tuple[PolicyEpoch, ...] = (),
) -> tuple[PromotionPolicyAssessment, ...]:
    """Evaluate every completed promotion under the supplied policy."""

    events = tuple(sorted(
        (
            event for event in record.events
            if record.observation_date is None
            or event.recorded_date is None
            or event.recorded_date <= record.observation_date
        ),
        key=lambda event: (event.event_date, event.source_id),
    ))
    promotions = tuple(
        event for event in events
        if event.event_type is AdministrativeEventType.PROMOTION
    )
    assessments = []
    previous_level_start = record.hire_date
    for promotion in promotions:
        if promotion.level_before is None:
            previous_level_start = promotion.event_date
            continue
        applicable_policy = _policy_for_promotion(promotion, policy, policy_epochs)
        observed_months = (
            _months_between(previous_level_start, promotion.event_date)
            + max(0, promotion.recognized_service_months)
        )
        required_months = (
            applicable_policy.required_service_months(promotion.level_before) or 0
        )
        credit_months = _commendation_credit_between(
            events, previous_level_start, promotion.event_date, applicable_policy
        )
        delay_months = _active_sanction_delay_between(
            events, previous_level_start, promotion.event_date, applicable_policy
        )
        race = calculate_promotion_race(PromotionRaceInput(
            has_next_level=required_months > 0,
            base_months=required_months or None,
            months_elapsed=max(observed_months, 0),
            commendation_credit_months=credit_months,
            active_sanction_delay_months=delay_months,
        ))
        assessments.append(PromotionPolicyAssessment(
            event_source_id=promotion.source_id,
            observed_service_months=observed_months,
            required_service_months=required_months,
            commendation_credit_months=credit_months,
            sanction_delay_months=delay_months,
            adjusted_service_months=race.adjusted_service_months,
            service_deficit_months=race.months_remaining or 0,
            raw_service_deficit_months=max(required_months - observed_months, 0),
        ))
        previous_level_start = promotion.event_date
    return tuple(assessments)


def _policy_for_promotion(
    promotion: AdministrativeEvent,
    fallback: PromotionPolicy,
    policy_epochs: tuple[PolicyEpoch, ...],
) -> PromotionPolicy:
    if not policy_epochs:
        return fallback
    known_at = promotion.recorded_date or promotion.event_date
    applicable = [
        epoch for epoch in policy_epochs
        if epoch.applies(promotion.event_date, known_at, promotion.jurisdiction)
    ]
    if promotion.policy_id:
        matching_id = [
            epoch for epoch in policy_epochs
            if epoch.policy_id == promotion.policy_id
            and epoch.recorded_at <= known_at
            and epoch.jurisdiction == promotion.jurisdiction
            and (
                epoch.applies(
                    promotion.event_date,
                    known_at,
                    promotion.jurisdiction,
                )
                or epoch.grandfather_previous_policy
            )
        ]
        if not matching_id:
            raise ValueError(
                f"declared policy {promotion.policy_id} is not applicable to "
                f"promotion {promotion.source_id}"
            )
        applicable = matching_id
    if not applicable:
        raise ValueError(
            f"no policy epoch applies to promotion {promotion.source_id}"
        )
    return max(applicable, key=lambda epoch: (epoch.valid_from, epoch.recorded_at)).policy


def _commendation_credit_between(
    events: tuple[AdministrativeEvent, ...],
    start: date,
    cutoff: date,
    policy: PromotionPolicy,
) -> int:
    credits = [
        policy.commendation_credit(int(event.category))
        for event in events
        if event.event_type is AdministrativeEventType.COMMENDATION
        and event.event_date > start
        and event.event_date <= cutoff
        and isinstance(event.category, int)
    ]
    return sum(sorted(credits, reverse=True)[:policy.max_commendations_per_role])


def _active_sanction_delay_between(
    events: tuple[AdministrativeEvent, ...],
    start: date,
    cutoff: date,
    policy: PromotionPolicy,
) -> int:
    return sum(
        policy.sanction_delay(int(event.category))
        for event in events
        if event.event_type is AdministrativeEventType.SANCTION
        and event.event_date > start
        and event.event_date <= cutoff
        and (not event.is_resolved or event.resolved_date is None or event.resolved_date > cutoff)
        and isinstance(event.category, int)
    )


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month
