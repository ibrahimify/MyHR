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

## Proposal 4 — corrected `policy_transition` construction (supersedes Proposal 2)

Proposed 2026-10-30 (post second-audit repair). Implemented in
`src/research/independent_scenarios.py`.

**Why:** The original Proposal 2 mechanism (force every promotion to 2022-06-01)
was found by the second audit (finding R2) to create genuine contradictions —
promotions before hire, same-day double promotions, insufficient service — so its
rare-legitimate labels were invalid. This proposal replaces it with a lawful
construction.

**Corrected mechanism (exact, for review):**

- Rebuild the history with a SINGLE legacy-epoch promotion L7->L6, stamped
  `policy_id="legacy-pre-2023"`, at effective date `hire_date + 30 months`
  (the legacy L7 service requirement), which is on/after hire and on/before the
  legacy epoch end `2022-12-31`.
- Any stacked second promotion is removed so there is no same-day double or order
  violation.
- The result has zero invariant findings and is a genuinely lawful legacy-policy
  promotion that the current reform-2023 policy would reject.

**Eligibility precondition (R3):** `policy_transition` is only assigned to a
PROGRESSION-track employee who already has a promotion AND whose
`hire_date + 30 months <= 2022-12-31`. Employees hired too late cannot host a
lawful legacy transition and are not selected.

**Open questions for the supervisor:** same as Proposal 2 plus — is a single
fixed `hire+30mo` transition date acceptable, or should it be distributed within
the legacy epoch?

**Status:** Proposed. Not approved. Not frozen.

## Proposal 5 — `late_correction` eligibility precondition (amends Proposal 1)

Proposed 2026-10-30 (post second-audit repair).

`late_correction` now requires a PROGRESSION-track employee with an existing
promotion (finding R3: previously the fallback required only a salary increment,
so some selected cases had no promotion to correct and produced empty causal
events with misleading "a promotion was corrected" evidence text). With the
precondition, every selected case has a real promotion to re-date and supersede.

**Status:** Proposed. Not approved. Not frozen.

## Proposal 6 — development matrix: skip unlawful `policy_transition` pairings (amends Proposal 3)

Proposed 2026-10-30 (post second-audit repair).

The 12-scenario development matrix assigns rare patterns by `index % 5`. When the
cycle would pair `policy_transition` with a population that cannot host a lawful
legacy-epoch promotion (`rapid_expansion`, hired 2021+, where
`hire+30mo > 2022-12-31`), the matrix now deterministically advances to the next
pattern. Net effect: `policy_transition` appears on 1 development scenario
(`merger_migration`) instead of 2; the `rapid_expansion` slot becomes
`grandfathered_policy`, which it can lawfully host.

This reduces `policy_transition` development coverage from a potential 2 scenarios
to 1. This is the scientifically correct tradeoff: forcing the pattern onto
`rapid_expansion` would require fabricating an unlawful promotion. If stronger
coverage is wanted, the legitimate levers are adjusting hire-year windows or
adding a dedicated hosting-population scenario — not forcing the pattern.

**Status:** Proposed. Not approved. Not frozen. Supervisor should decide whether
1-scenario development coverage of `policy_transition` is sufficient or whether a
dedicated hosting population should be added.

## Approval log

| Proposal | Proposed | Supervisor decision | Date |
| --- | --- | --- | --- |
| 1 `late_correction` definition | 2026-10-30 | _pending_ | — |
| 2 `policy_transition` definition (SUPERSEDED by #4) | 2026-10-30 | superseded | — |
| 3 development matrix composition (AMENDED by #6) | 2026-10-30 | _pending_ | — |
| 4 corrected `policy_transition` construction | 2026-10-30 | _pending_ | — |
| 5 `late_correction` eligibility precondition | 2026-10-30 | _pending_ | — |
| 6 matrix skips unlawful `policy_transition` pairings | 2026-10-30 | _pending_ | — |

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
