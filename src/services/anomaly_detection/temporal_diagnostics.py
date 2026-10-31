"""Reusable diagnostics for paired bitemporal policy views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .effective_state import TemporalView, effective_events, visible_events
from .policy_history import (
    GrandfatheringEvidence,
    PolicyEpoch,
    assess_promotion_history,
)
from .policy_model import PromotionPolicy
from .synthetic_data import WorkforceHistoryRecord


@dataclass(frozen=True)
class TemporalDiagnosticResult:
    """One explicit, serializable summary of a temporal evaluation view."""

    view_identifier: str
    effective_through: date
    recorded_through: date
    visible_event_ids: tuple[str, ...]
    visible_event_count: int
    effective_event_ids: tuple[str, ...]
    effective_event_count: int
    promotion_assessment_count: int
    total_service_deficit_months: int


def diagnose_temporal_views(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    policy_epochs: tuple[PolicyEpoch, ...],
    entitlement_evidence: tuple[GrandfatheringEvidence, ...],
    decision_date: date,
    review_date: date,
) -> tuple[TemporalDiagnosticResult, TemporalDiagnosticResult]:
    """Compare decision-time knowledge with a later review of the same horizon.

    Both rows use ``decision_date`` as their effective-time cutoff. The
    ``later_review`` row changes only the knowledge-time and policy-knowledge
    cutoffs, allowing late-recorded corrections to be inspected without
    treating later-effective events as part of the historical decision.
    """

    views = (
        ("known_then", TemporalView.known_then(decision_date)),
        (
            "later_review",
            TemporalView.present_review(decision_date, review_date),
        ),
    )
    return tuple(
        _diagnose_view(
            view_identifier,
            temporal_view,
            record,
            policy,
            policy_epochs,
            entitlement_evidence,
        )
        for view_identifier, temporal_view in views
    )


def _diagnose_view(
    view_identifier: str,
    temporal_view: TemporalView,
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    policy_epochs: tuple[PolicyEpoch, ...],
    entitlement_evidence: tuple[GrandfatheringEvidence, ...],
) -> TemporalDiagnosticResult:
    visible = visible_events(record, temporal_view)
    effective = effective_events(record, temporal_view)
    assessments = assess_promotion_history(
        record,
        policy,
        policy_epochs,
        temporal_view,
        entitlement_evidence,
    )
    effective_through = temporal_view.effective_through
    recorded_through = temporal_view.recorded_through
    if effective_through is None or recorded_through is None:
        raise ValueError("temporal diagnostics require bounded view dates")
    return TemporalDiagnosticResult(
        view_identifier=view_identifier,
        effective_through=effective_through,
        recorded_through=recorded_through,
        visible_event_ids=tuple(event.source_id for event in visible),
        visible_event_count=len(visible),
        effective_event_ids=tuple(event.source_id for event in effective),
        effective_event_count=len(effective),
        promotion_assessment_count=len(assessments),
        total_service_deficit_months=sum(
            assessment.service_deficit_months for assessment in assessments
        ),
    )
