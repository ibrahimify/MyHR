"""Central effective-state resolver for administrative histories.

Second-audit finding R5: supersession (corrections) was handled ad hoc — only
promotions were filtered in the policy engine, while commendation/sanction credit
calculations, raw features, and invariant checks all saw superseded (invalid)
facts. Different components therefore disagreed about what the "current" facts
were.

This module centralizes the resolution shared by deterministic checks, policy
history, and feature extraction:

- VISIBILITY: an event is visible only if recorded on or before the observation
  date (``recorded_date <= observation_date``; ``None`` observation date or
  ``None`` recorded date means always visible).
- SUPERSESSION: an event referenced by another visible event's
  ``correction_of_source_id`` is superseded. The correction carries the
  effective fact; the superseded record is preserved as raw audit evidence but
  excluded from the effective state.
- GRAPH VALIDATION: structurally invalid correction graphs are rejected with
  ``CorrectionGraphError`` rather than silently hiding events: a self-reference
  or a cycle. A correction whose target is not among the currently visible
  events is treated as legitimate partial visibility (nothing to supersede),
  not as an error.

Consumers can ask for the effective events (visible, superseded removed) or the
raw visible events (for audit-volume features), keeping "corrected-state
features" and "correction-volume features" explicitly distinct.
"""

from __future__ import annotations

from .synthetic_data import AdministrativeEvent, WorkforceHistoryRecord


class CorrectionGraphError(ValueError):
    """Raised when a correction graph is malformed (self-link, cycle, dangling)."""


def _event_is_visible(event: AdministrativeEvent, observation_date) -> bool:
    """An event is visible as of ``observation_date`` when both:

    - it has been RECORDED by then (``recorded_date <= observation_date``), and
    - it has taken EFFECT by then (``event_date <= observation_date``).

    The second condition (finding R7.3) excludes a promotion that is already
    recorded but whose effective date is still in the future — such an event is
    a planned/advance-recorded fact, not a completed one, and must not be counted
    as a completed promotion in a current-history snapshot. A ``None``
    observation date means no as-of cutoff (all events visible).
    """
    if observation_date is None:
        return True
    if event.recorded_date is not None and event.recorded_date > observation_date:
        return False
    if event.event_date > observation_date:
        return False
    return True


def visible_events(
    record: WorkforceHistoryRecord,
) -> tuple[AdministrativeEvent, ...]:
    """Return events visible as of the record's observation date, date-sorted.

    Visibility requires both recorded-by and effective-by the observation date
    (see ``_event_is_visible``). Does NOT remove superseded events — this is the
    raw audit view. Use ``effective_events`` for the corrected state.
    """
    visible = (
        event for event in record.events
        if _event_is_visible(event, record.observation_date)
    )
    return tuple(sorted(visible, key=lambda event: (event.event_date, event.source_id)))


def superseded_source_ids(
    events: tuple[AdministrativeEvent, ...],
) -> frozenset[str]:
    """Return the set of source_ids superseded by a visible correction.

    Validates the correction graph and raises ``CorrectionGraphError`` on:
      - a self-referencing correction (event corrects itself);
      - a cycle in the correction chain.

    A correction whose target source_id is not present among ``events`` is NOT
    an error: under the bitemporal contract the target may simply be invisible
    as of the observation date (recorded later, or effective later). Such a
    correction has nothing visible to supersede and is skipped.
    """
    by_id: dict[str, AdministrativeEvent] = {}
    for event in events:
        if event.source_id in by_id:
            raise CorrectionGraphError(
                f"duplicate source_id {event.source_id!r} in correction graph"
            )
        by_id[event.source_id] = event

    superseded: set[str] = set()
    correction_by_target: dict[str, str] = {}
    for event in events:
        target = event.correction_of_source_id
        if target is None:
            continue
        if target == event.source_id:
            raise CorrectionGraphError(
                f"event {event.source_id!r} corrects itself"
            )
        if target not in by_id:
            # The correction's target is not among the currently VISIBLE events.
            # This is a legitimate partial-visibility state under the bitemporal
            # contract (e.g. the original became invisible as of the observation
            # date while its correction is visible), not a malformed graph. There
            # is nothing visible to supersede, so skip rather than raise.
            continue
        target_event = by_id[target]
        if event.event_type is not target_event.event_type:
            raise CorrectionGraphError(
                f"event {event.source_id!r} of type {event.event_type.value!r} "
                f"cannot correct {target!r} of type {target_event.event_type.value!r}"
            )
        previous_correction = correction_by_target.get(target)
        if previous_correction is not None:
            raise CorrectionGraphError(
                f"events {previous_correction!r} and {event.source_id!r} both "
                f"correct target {target!r}"
            )
        correction_by_target[target] = event.source_id
        superseded.add(target)

    # Detect cycles: follow correction_of_source_id links; a cycle means an
    # event is (transitively) its own correction target.
    for event in events:
        seen: set[str] = set()
        current: AdministrativeEvent | None = event
        while current is not None and current.correction_of_source_id is not None:
            if current.source_id in seen:
                raise CorrectionGraphError(
                    f"correction cycle detected at {current.source_id!r}"
                )
            seen.add(current.source_id)
            current = by_id.get(current.correction_of_source_id)

    return frozenset(superseded)


def effective_events(
    record: WorkforceHistoryRecord,
) -> tuple[AdministrativeEvent, ...]:
    """Return the effective (corrected-state) events for the record.

    These are the visible events with superseded records removed. The correction
    events themselves remain (they carry the effective fact). Raises
    ``CorrectionGraphError`` on a malformed correction graph.
    """
    events = visible_events(record)
    superseded = superseded_source_ids(events)
    return tuple(event for event in events if event.source_id not in superseded)
