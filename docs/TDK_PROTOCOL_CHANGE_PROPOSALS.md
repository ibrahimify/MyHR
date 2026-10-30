# TDK Protocol Change Proposals

Status: **PROPOSALS ONLY — PENDING HUMAN (SUPERVISOR) APPROVAL.**

This document records proposed changes to scenario definitions, mechanisms, and
evaluation details that were implemented in code but are **not** yet approved as
protocol. Per `AGENTS.md`, scenario definitions must not be silently changed;
proposed changes are recorded here separately for supervisor approval. Nothing in
this document is frozen, and none of it authorizes holdout access.

---

## Proposal 1 — `late_correction` rare-legitimate scenario definition

Proposed 2026-10-30. Implemented in code at commit `0f1f32c`
(`src/research/independent_scenarios.py`, `_apply_rare_case`). Tested, but the
*definition* below is a proposal, not an approved specification.

**Intent:** Model a promotion that was initially recorded with an erroneous date
and later corrected, so that the corrected (effective) history is policy-compliant
and should be treated as a rare-legitimate case rather than an error.

**Proposed mechanism (exact, for review):**

- Take the last promotion event in the base history as the original.
- Inject an erroneous copy with the effective date moved **−12 months**, stamped
  with the policy applicable at that earlier date (`_policy_id_for_date`), recorded
  3 days after its (wrong) effective date, `approval_status="approved"`.
- Inject a correction event carrying `correction_of_event_id` pointing to the
  erroneous event, recorded 14 days after the true effective date,
  `approval_status="approved"`.
- The correction supersedes the erroneous event; `assess_promotion_history` drops
  any promotion whose `source_id` is referenced by a visible `correction_of_source_id`.

**Open questions for the supervisor:**

1. Is −12 months the right mis-dating magnitude, or should it vary across scenarios?
2. Should more than one correction case per scenario be injected?
3. Is approving the erroneous event at filing time (vs a distinct pre-correction
   status) the correct administrative model?

**Status:** Proposed. Not approved. Not frozen.

---

## Proposal 2 — `policy_transition` rare-legitimate scenario definition

Proposed 2026-10-30. Implemented in code at commit `0bfa585` / `3e9edd2`
(`src/research/independent_scenarios.py`, `_apply_rare_case`).

**Intent:** Model an employee promoted under an earlier policy epoch whose service
requirement must be evaluated under the policy effective at the promotion date, not
the current policy. This is the core case motivating the bitemporal contract
(Supervisor Decision 4).

**Proposed mechanism (exact, for review):**

- Re-stamp the promotion event to `policy_id="legacy-pre-2023"` with effective date
  `2022-06-01` and recorded date `2022-06-03`.
- The promotion satisfies the then-current (legacy) service requirement even where
  the current `reform-2023` policy would reject it.

**Open questions for the supervisor:**

1. Is a single fixed `2022-06-01` effective date acceptable, or should transition
   dates be distributed across the legacy epoch?
2. Should the transition cover increments and other event types, not only promotions?
3. Is the legacy/reform two-epoch model sufficient, or are more epochs needed?

**Status:** Proposed. Not approved. Not frozen.

---

## Proposal 3 — development matrix composition change

Adding two rare patterns changed the 12-scenario development matrix assignment from
`index % 3` (3 patterns, 4 each) to `index % 5` (patterns 0,1 appear 3×; patterns
2,3,4 appear 2×). This is a **development-only** composition change. It does not
define the holdout matrix, which remains undefined and locked under Decision 6.

**Status:** Proposed for development use. Holdout matrix unaffected and still
requires an independent frozen specification.

---

## Approval log

| Proposal | Proposed | Supervisor decision | Date |
| --- | --- | --- | --- |
| 1 `late_correction` definition | 2026-10-30 | _pending_ | — |
| 2 `policy_transition` definition | 2026-10-30 | _pending_ | — |
| 3 development matrix composition | 2026-10-30 | _pending_ | — |

## Pending independent verification

The exploratory readings from artifact `db1a15646d9e76ba` were re-derived through
an independent code path (`scripts/reproduce_db1a15646d9e76ba_readings.py`) by the
same author who wrote the scenario code. This is **not** an independent review. A
separate read-only auditor (human or distinct agent) must still verify:

- the raw `record_predictions.csv` / `record_truth.csv` rows;
- that the denominator is the **test-split** rare-legitimate count (72), not the
  all-splits count (348);
- scenario membership of the 8 flagged records;
- that all 8 flags are `policy_transition` cases and none are `late_correction`.

Corrected denominator statement for all documents: **8 of 72 test-split
rare-legitimate records (11.1%)**; scenario-level, **8 of 12 policy-transition
test cases (66.7%)**; **0 of 60** other-pattern test cases.
