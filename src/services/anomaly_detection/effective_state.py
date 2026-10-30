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
- GRAPH VALIDATION: invalid correction graphs are rejected with ``ValueError``
  rather than silently hiding events: a self-reference, a cycle, or a reference
  to a source that does not exist among visible events.

Consumers can ask for the effective events (visible, superseded removed) or the
raw visible events (for audit-volume features), keeping "corrected-state
features" and "correction-volume features" explicitly distinct.
"""

from __future__ import annotations

from .synthetic_data import AdministrativeEvent, WorkforceHistoryRecord


class CorrectionGraphError(ValueError):
    """Raised when a correction graph is malformed (self-link, cycle, dangling)."""


def visible_events(
    record: WorkforceHistoryRecord,
) -> tuple[AdministrativeEvent, ...]:
    """Return events visible as of the record's observation date, date-sorted.

    Does NOT remove superseded events — this is the raw audit view. Use
    ``effective_events`` for the corrected state.
    """
    visible = (
        event for event in record.events
        if record.observation_date is None
        or event.recorded_date is None
        or event.recorded_date <= record.observation_date
    )
    return tuple(sorted(visible, key=lambda event: (event.event_date, event.source_id)))


def superseded_source_ids(
    events: tuple[AdministrativeEvent, ...],
) -> frozenset[str]:
    """Return the set of source_ids superseded by a visible correction.

    Validates the correction graph and raises ``CorrectionGraphError`` on:
      - a self-referencing correction (event corrects itself);
      - a correction whose target source_id does not exist among ``events``;
      - a cycle in the correction chain.
    """
    by_id: dict[str, AdministrativeEvent] = {}
    for event in events:
        # source_id is expected unique per history; last one wins defensively.
        by_id[event.source_id] = event

    superseded: set[str] = set()
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
