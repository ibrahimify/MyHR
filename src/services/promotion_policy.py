"""Pure promotion-race arithmetic shared by application and research code."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionRaceInput:
    """Inputs collected from SQL records or experimental histories."""

    has_next_level: bool
    base_months: int | None
    months_elapsed: int
    commendation_credit_months: int = 0
    active_sanction_delay_months: int = 0


@dataclass(frozen=True)
class PromotionRaceOutcome:
    """Deterministic promotion-race result."""

    has_next_level: bool
    base_months: int | None
    months_elapsed: int
    commendation_credit_months: int
    active_sanction_delay_months: int
    adjusted_service_months: int
    months_remaining: int | None
    eligible: bool
    progress_pct: int


def calculate_promotion_race(inputs: PromotionRaceInput) -> PromotionRaceOutcome:
    """Apply the MyHR race equation without database, UI, or clock dependencies."""

    if inputs.months_elapsed < 0:
        raise ValueError("months_elapsed must not be negative")
    if inputs.commendation_credit_months < 0:
        raise ValueError("commendation_credit_months must not be negative")
    if inputs.active_sanction_delay_months < 0:
        raise ValueError("active_sanction_delay_months must not be negative")
    if not inputs.has_next_level or inputs.base_months is None:
        return PromotionRaceOutcome(
            has_next_level=False,
            base_months=None,
            months_elapsed=inputs.months_elapsed,
            commendation_credit_months=0,
            active_sanction_delay_months=0,
            adjusted_service_months=inputs.months_elapsed,
            months_remaining=None,
            eligible=False,
            progress_pct=0,
        )
    if inputs.base_months <= 0:
        raise ValueError("base_months must be positive when a next level exists")

    adjusted_service = (
        inputs.months_elapsed
        + inputs.commendation_credit_months
        - inputs.active_sanction_delay_months
    )
    months_remaining = max(0, inputs.base_months - adjusted_service)
    progress_pct = max(0, min(100, int(adjusted_service / inputs.base_months * 100)))
    return PromotionRaceOutcome(
        has_next_level=True,
        base_months=inputs.base_months,
        months_elapsed=inputs.months_elapsed,
        commendation_credit_months=inputs.commendation_credit_months,
        active_sanction_delay_months=inputs.active_sanction_delay_months,
        adjusted_service_months=adjusted_service,
        months_remaining=months_remaining,
        eligible=months_remaining == 0,
        progress_pct=progress_pct,
    )
