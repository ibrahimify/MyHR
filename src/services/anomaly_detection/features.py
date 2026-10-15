"""Feature extraction for anomaly-detection experiments."""

from dataclasses import dataclass
from datetime import date

from .policy_history import PromotionPolicyAssessment, assess_promotion_history
from .policy_model import PromotionPolicy
from .synthetic_data import AdministrativeEvent, AdministrativeEventType, EmploymentTrack, WorkforceHistoryRecord

RAW_FEATURE_SET = "raw"
POLICY_AWARE_FEATURE_SET = "policy_aware"


@dataclass(frozen=True)
class FeatureVector:
    """Named numeric features for one employee history."""

    employee_id: str
    feature_set: str
    values: dict[str, float]


def supported_feature_sets() -> tuple[str, str]:
    return RAW_FEATURE_SET, POLICY_AWARE_FEATURE_SET


def extract_raw_features(record: WorkforceHistoryRecord) -> FeatureVector:
    """Extract policy-agnostic event-count and interval features."""

    events = _sorted_events(record)
    promotions = _events_of_type(events, AdministrativeEventType.PROMOTION)
    increments = _events_of_type(events, AdministrativeEventType.SALARY_INCREMENT)
    sanctions = _events_of_type(events, AdministrativeEventType.SANCTION)
    commendations = _events_of_type(events, AdministrativeEventType.COMMENDATION)
    reviews = _events_of_type(events, AdministrativeEventType.PERFORMANCE_REVIEW)

    values = {
        "event_count": float(len(events)),
        "promotion_count": float(len(promotions)),
        "sanction_count": float(len(sanctions)),
        "commendation_count": float(len(commendations)),
        "salary_increment_count": float(len(increments)),
        "performance_review_count": float(len(reviews)),
        "employment_track_is_promotion": 1.0 if record.employment_track is EmploymentTrack.PROMOTION else 0.0,
        "months_since_hire": float(_months_between(record.hire_date, _last_event_date(events, record.hire_date))),
        "min_promotion_interval_months": float(_min_month_interval(promotions)),
        "min_salary_increment_interval_days": float(_min_day_interval(increments)),
    }
    return FeatureVector(employee_id=record.identity.employee_id, feature_set=RAW_FEATURE_SET, values=values)


def extract_policy_aware_features(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy | None = None,
) -> FeatureVector:
    """Extract features that condition raw history on explicit progression policy."""

    policy = policy or PromotionPolicy()
    raw = extract_raw_features(record).values
    events = _sorted_events(record)
    assessments = assess_promotion_history(record, policy)
    service_context = _promotion_service_context(assessments)

    values = dict(raw)
    values.update(service_context)
    values.update({
        "policy_track_eligible": 1.0 if policy.is_promotion_track(record.current_level) else 0.0,
        "other_track_increment_only": 1.0 if record.employment_track is EmploymentTrack.OTHER else 0.0,
    })
    return FeatureVector(employee_id=record.identity.employee_id, feature_set=POLICY_AWARE_FEATURE_SET, values=values)


def extract_features(
    record: WorkforceHistoryRecord,
    feature_set: str,
    policy: PromotionPolicy | None = None,
) -> FeatureVector:
    if feature_set == RAW_FEATURE_SET:
        return extract_raw_features(record)
    if feature_set == POLICY_AWARE_FEATURE_SET:
        return extract_policy_aware_features(record, policy)
    raise ValueError(f"Unsupported feature set: {feature_set}")


def _promotion_service_context(
    assessments: tuple[PromotionPolicyAssessment, ...],
) -> dict[str, float]:
    if not assessments:
        return {
            "latest_promotion_observed_service_months": 0.0,
            "latest_promotion_required_service_months": 0.0,
            "policy_commendation_credit_months": 0.0,
            "policy_sanction_delay_months": 0.0,
            "policy_adjusted_service_months": 0.0,
            "policy_service_deficit_months": 0.0,
            "policy_raw_service_deficit_months": 0.0,
            "policy_adjusted_service_ratio": 0.0,
            "policy_service_deficit_ratio": 0.0,
            "policy_unexplained_short_promotion": 0.0,
            "policy_explains_short_promotion": 0.0,
        }

    latest = assessments[-1]
    max_deficit = max(assessments, key=lambda item: item.service_deficit_months)
    max_raw_deficit = max(assessments, key=lambda item: item.raw_service_deficit_months)
    unexplained = any(item.service_deficit_months > 0 for item in assessments)
    explained = any(
        item.raw_service_deficit_months > 0 and item.service_deficit_months == 0
        for item in assessments
    )

    return {
        "latest_promotion_observed_service_months": float(latest.observed_service_months),
        "latest_promotion_required_service_months": float(latest.required_service_months),
        "policy_commendation_credit_months": float(latest.commendation_credit_months),
        "policy_sanction_delay_months": float(latest.sanction_delay_months),
        "policy_adjusted_service_months": float(latest.adjusted_service_months),
        "policy_service_deficit_months": float(max_deficit.service_deficit_months),
        "policy_raw_service_deficit_months": float(max_raw_deficit.raw_service_deficit_months),
        "policy_adjusted_service_ratio": float(
            latest.adjusted_service_months / latest.required_service_denominator
        ),
        "policy_service_deficit_ratio": float(
            max_deficit.service_deficit_months / max_deficit.required_service_denominator
        ),
        "policy_unexplained_short_promotion": 1.0 if unexplained else 0.0,
        "policy_explains_short_promotion": 1.0 if explained else 0.0,
    }


def _sorted_events(record: WorkforceHistoryRecord) -> tuple[AdministrativeEvent, ...]:
    return tuple(sorted(record.events, key=lambda event: (event.event_date, event.source_id)))


def _events_of_type(
    events: tuple[AdministrativeEvent, ...],
    event_type: AdministrativeEventType,
) -> tuple[AdministrativeEvent, ...]:
    return tuple(event for event in events if event.event_type is event_type)


def _last_event_date(events: tuple[AdministrativeEvent, ...], fallback: date) -> date:
    return events[-1].event_date if events else fallback


def _min_month_interval(events: tuple[AdministrativeEvent, ...]) -> int:
    if len(events) < 2:
        return 0
    return min(_months_between(left.event_date, right.event_date) for left, right in zip(events, events[1:]))


def _min_day_interval(events: tuple[AdministrativeEvent, ...]) -> int:
    if len(events) < 2:
        return 0
    return min((right.event_date - left.event_date).days for left, right in zip(events, events[1:]))


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month
