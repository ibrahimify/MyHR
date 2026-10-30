"""Deterministic validation checks for explicit administrative inconsistencies."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from .synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    EmploymentTrack,
    SyntheticDataset,
    WorkforceHistoryRecord,
)
from .effective_state import effective_events
from .policy_model import PromotionPolicy


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationFinding:
    """Explainable deterministic finding for audit and experiment baselines."""

    code: str
    severity: ValidationSeverity
    employee_id: str
    message: str
    event_source_id: str | None = None
    expected_anomaly_type: AnomalyType | None = None


def date_is_not_after(left: datetime | None, right: datetime | None) -> bool:
    """Return True when the date order is valid or incomplete."""

    if left is None or right is None:
        return True
    return left <= right


def has_duplicate_identifier(identifier: str | None, seen_identifiers: set[str]) -> bool:
    """Check exact duplicate IDs while keeping state outside the function."""

    if not identifier:
        return False
    normalized = identifier.strip().lower()
    if normalized in seen_identifiers:
        return True
    seen_identifiers.add(normalized)
    return False


def validate_invariant_record(
    record: WorkforceHistoryRecord,
) -> tuple[ValidationFinding, ...]:
    """Return structural contradictions independent of configurable policy."""

    findings: list[ValidationFinding] = []
    employee_id = record.identity.employee_id
    events = _effective_record_events(record)
    hire_events = [event for event in events if event.event_type is AdministrativeEventType.HIRE]

    if not hire_events:
        findings.append(
            ValidationFinding(
                code="missing_hire_event",
                severity=ValidationSeverity.ERROR,
                employee_id=employee_id,
                message="No hire event exists for the employee history.",
                expected_anomaly_type=AnomalyType.INCONSISTENT_DATES,
            )
        )

    for event in events:
        if event.event_date < record.hire_date:
            findings.append(
                ValidationFinding(
                    code="event_before_hire_date",
                    severity=ValidationSeverity.ERROR,
                    employee_id=employee_id,
                    event_source_id=event.source_id,
                    message=f"{event.event_type.value} event occurs before the recorded hire date.",
                    expected_anomaly_type=AnomalyType.INCONSISTENT_DATES,
                )
            )

    if record.employment_track is EmploymentTrack.OTHER:
        for event in _events_of_type(events, AdministrativeEventType.PROMOTION):
            findings.append(
                ValidationFinding(
                    code="promotion_on_other_track",
                    severity=ValidationSeverity.ERROR,
                    employee_id=employee_id,
                    event_source_id=event.source_id,
                    message="Employee is on the other track but has a promotion event.",
                    expected_anomaly_type=AnomalyType.INCONSISTENT_DATES,
                )
            )

    findings.extend(_validate_promotion_level_order(record, events))
    return tuple(findings)


def validate_record(record: WorkforceHistoryRecord) -> tuple[ValidationFinding, ...]:
    """Return structural and fixed administrative-interval findings."""

    events = _effective_record_events(record)
    findings = list(validate_invariant_record(record))
    findings.extend(_validate_short_promotion_intervals(record, events))
    findings.extend(_validate_salary_increment_intervals(record, events))
    return tuple(findings)


def validate_record_with_policy(
    record: WorkforceHistoryRecord,
    policy: PromotionPolicy,
    policy_epochs: tuple[object, ...] = (),
) -> tuple[ValidationFinding, ...]:
    """Add explicit policy violations to the policy-agnostic checks."""

    from .policy_history import assess_promotion_history

    findings = list(validate_record(record))
    for event in _events_of_type(
        _effective_record_events(record), AdministrativeEventType.PROMOTION
    ):
        if event.approval_status == "bypassed":
            findings.append(ValidationFinding(
                code="promotion_approval_bypassed",
                severity=ValidationSeverity.ERROR,
                employee_id=record.identity.employee_id,
                event_source_id=event.source_id,
                message="Promotion approval workflow was explicitly bypassed.",
                expected_anomaly_type=AnomalyType.FREQUENT_PROMOTIONS,
            ))
    for assessment in assess_promotion_history(record, policy, policy_epochs):
        if assessment.service_deficit_months <= 0:
            continue
        findings.append(ValidationFinding(
            code="promotion_policy_service_deficit",
            severity=ValidationSeverity.ERROR,
            employee_id=record.identity.employee_id,
            event_source_id=assessment.event_source_id,
            message=(
                "Completed promotion lacks "
                f"{assessment.service_deficit_months} required service month(s) "
                "after policy credits and delays."
            ),
            expected_anomaly_type=AnomalyType.FREQUENT_PROMOTIONS,
        ))
    return tuple(findings)


def validate_dataset(dataset: SyntheticDataset) -> tuple[ValidationFinding, ...]:
    """Return deterministic findings for all records, including exact duplicate IDs."""

    findings: list[ValidationFinding] = []
    findings.extend(_validate_exact_identifiers(dataset.records))
    for record in dataset.records:
        findings.extend(validate_record(record))
    return tuple(findings)


def summarize_findings(findings: tuple[ValidationFinding, ...]) -> dict[str, int]:
    """Count findings by code for compact experiment reporting."""

    return dict(Counter(finding.code for finding in findings))


def _validate_promotion_level_order(
    record: WorkforceHistoryRecord,
    events: tuple[AdministrativeEvent, ...],
) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    promotions = _events_of_type(events, AdministrativeEventType.PROMOTION)
    for event in promotions:
        if event.level_before and event.level_after and not _level_progresses(event.level_before, event.level_after):
            findings.append(
                ValidationFinding(
                    code="invalid_promotion_level_order",
                    severity=ValidationSeverity.ERROR,
                    employee_id=record.identity.employee_id,
                    event_source_id=event.source_id,
                    message=f"Promotion level order is invalid: {event.level_before} to {event.level_after}.",
                    expected_anomaly_type=AnomalyType.INCONSISTENT_DATES,
                )
            )

    return tuple(findings)


def _validate_short_promotion_intervals(
    record: WorkforceHistoryRecord,
    events: tuple[AdministrativeEvent, ...],
) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    previous_promotion: AdministrativeEvent | None = None
    for event in _events_of_type(events, AdministrativeEventType.PROMOTION):
        if previous_promotion is not None:
            months = _months_between(previous_promotion.event_date, event.event_date)
            if months < 12:
                findings.append(
                    ValidationFinding(
                        code="promotion_interval_too_short",
                        severity=ValidationSeverity.ERROR,
                        employee_id=record.identity.employee_id,
                        event_source_id=event.source_id,
                        message=(
                            f"Promotion interval is {months} months, below the "
                            "deterministic 12-month minimum."
                        ),
                        expected_anomaly_type=AnomalyType.FREQUENT_PROMOTIONS,
                    )
                )
        previous_promotion = event
    return tuple(findings)


def _validate_salary_increment_intervals(
    record: WorkforceHistoryRecord,
    events: tuple[AdministrativeEvent, ...],
) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    increments = _events_of_type(events, AdministrativeEventType.SALARY_INCREMENT)
    previous_increment: AdministrativeEvent | None = None

    for event in increments:
        if previous_increment is not None:
            days = (event.event_date - previous_increment.event_date).days
            if days < 300:
                findings.append(
                    ValidationFinding(
                        code="salary_increment_interval_too_short",
                        severity=ValidationSeverity.ERROR,
                        employee_id=record.identity.employee_id,
                        event_source_id=event.source_id,
                        message=f"Salary increment interval is {days} days, below the deterministic 300-day minimum.",
                        expected_anomaly_type=AnomalyType.UNUSUAL_ADMIN_INTERVAL,
                    )
                )
        previous_increment = event

    return tuple(findings)


def _validate_exact_identifiers(records: tuple[WorkforceHistoryRecord, ...]) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    seen_employee_ids: set[str] = set()
    seen_national_ids: set[str] = set()

    for record in records:
        if has_duplicate_identifier(record.identity.employee_id, seen_employee_ids):
            findings.append(
                ValidationFinding(
                    code="duplicate_employee_id",
                    severity=ValidationSeverity.ERROR,
                    employee_id=record.identity.employee_id,
                    message="Employee ID appears more than once in the dataset.",
                    expected_anomaly_type=AnomalyType.DUPLICATE_RECORD,
                )
            )
        if has_duplicate_identifier(record.identity.national_id, seen_national_ids):
            findings.append(
                ValidationFinding(
                    code="duplicate_national_id",
                    severity=ValidationSeverity.ERROR,
                    employee_id=record.identity.employee_id,
                    message="National ID appears more than once in the dataset.",
                    expected_anomaly_type=AnomalyType.DUPLICATE_RECORD,
                )
            )

    return tuple(findings)


def _events_of_type(
    events: tuple[AdministrativeEvent, ...],
    event_type: AdministrativeEventType,
) -> tuple[AdministrativeEvent, ...]:
    return tuple(event for event in events if event.event_type is event_type)


def _effective_record_events(
    record: WorkforceHistoryRecord,
) -> tuple[AdministrativeEvent, ...]:
    # Use the central effective-state resolver (finding R5): invariant checks
    # evaluate the corrected state, so a superseded invalid record (e.g. a
    # wrongly recorded promotion that was later corrected) is not flagged as a
    # contradiction. Superseded records remain available as raw audit evidence
    # via effective_state.visible_events for correction-volume features.
    return effective_events(record)


def _level_progresses(level_before: str, level_after: str) -> bool:
    try:
        before_number = int(level_before.upper().removeprefix("L"))
        after_number = int(level_after.upper().removeprefix("L"))
    except ValueError:
        return False
    return after_number < before_number


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month

