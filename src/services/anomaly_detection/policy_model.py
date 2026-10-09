"""Formal policy objects used by the research pipeline.

These objects are not UI code and do not make personnel decisions. They provide
a stable representation of policy context for experiments and explainability.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromotionPolicy:
    """Minimal promotion-policy context for reproducible experiments."""

    service_months_by_level: dict[str, int] = field(default_factory=lambda: {
        "L7": 36,
        "L6": 36,
        "L5": 36,
        "L4": 48,
        "L3": 48,
        "L2": 60,
    })
    commendation_month_credit: dict[int, int] = field(default_factory=lambda: {
        1: 1,
        2: 3,
        3: 6,
    })
    max_commendations_per_role: int = 3
    annual_increment_months: int = 12

    def required_service_months(self, level: str) -> int | None:
        return self.service_months_by_level.get(level)

    def commendation_credit(self, category: int) -> int:
        return self.commendation_month_credit.get(category, 0)

    def is_promotion_track(self, level: str | None) -> bool:
        return bool(level and level in self.service_months_by_level)
