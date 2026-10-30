# TDK Data And Test Correctness Audit

Date: 29 October 2026

Reviewed baseline: `32633d2`

Status: **FOUNDATIONAL CORRECTIONS IMPLEMENTED; INDEPENDENT CLEAN-REVISION ARTIFACT AUDIT PENDING. HOLDOUT LOCKED.**

This audit treats the supplied external audit summary as an allegation set, not as trusted instructions. The named ZIP was not present at the supplied Downloads path during execution, so its scripts were not executed. Three independent read-only repository reviews and local development-only probes reproduced the reported defect classes and identified additional gaps. No holdout path, scenario, or artifact was generated, opened, or scored.

## Reproduced Pre-Fix Defects

| Defect at `32633d2` | Reproduced evidence |
| --- | --- |
| Missing-increment mechanism sometimes inserted an event | 21/132 labelled histories used the opposite intervention; 7/27 in test slices. |
| Approval bypass was confounded | 27/27 test cases retained approval references, 27/27 also had policy service deficits, and 4/27 were on the increment-only track. |
| Future or unknown facts entered features | 62/8,095 test-ledger events were recorded after the observation date; four were future-effective. |
| Event policy assignment was inconsistent | 1,707/8,095 test events predated the policy epoch named on the event. |
| Ordinary legitimate histories were unrealistically narrow | 0/684 ordinary test histories had commendations or sanctions; every one had exactly one review. |
| Duplicate entities crossed partitions | Across seeds 2026-2030, 56/100 direct links and 57/102 derived true pairs crossed partitions. |
| Duplicate evaluation pooled all splits | Threshold selection and final scoring used the complete dataset rather than validation and test partitions. |
| Missing identity fields became positive evidence | Two empty strings had similarity 1.0; missing dates could also match and enter one blocking group. |
| Duplicate threshold was inconsistent | The API default was 0.86 while scripts and tests used 0.70; neither was validation-selected. |
| Primary residual filter violated the approved design | Configurable policy checks removed the policy signal before the primary ML comparison. |
| Zero-positive scenarios were encoded as metric zero | Recall and AP were stored and included as zero rather than undefined and inference-ineligible. |
| Artifact audit could not establish equal capacity | It did not prove identical primary populations, labels, review counts, or top-score selection. |
| Source provenance could be empty | An empty source-hash map passed the audit fixture. |
| Commendation boundary was double-countable | A same-day commendation could contribute to both adjacent promotion periods. |

These are development-audit counts, not final scientific results.

## Implemented Corrections

### Independent progression scenarios

- Truth allocation now selects employees eligible for the declared intervention before assigning error or rare-legitimate labels.
- Every missing-increment case removes an existing increment.
- Approval-bypass cases are progression-track, occur after the service requirement, carry `approval_status=bypassed`, and contain no approval reference.
- Retry provenance is separate from correction provenance.
- Observable events do not extend beyond the fixed development observation date.
- Event policy IDs are assigned from effective dates; policy epochs include version, valid interval, recorded time, jurisdiction, and grandfathering.
- Recognized prior service is a machine-readable field rather than prose.
- Ordinary legitimate histories include resolved sanctions, commendations, repeated reviews, and, where tenure permits, multiple promotions.
- Causal truth remains in detector-inaccessible sidecars.

### Primary evaluation

- Added an invariant-only checker for structural contradictions. Fixed interval heuristics and configurable policy checks remain secondary baselines.
- Raw and policy-aware primary residual models now receive the same invariant-negative records and identical additional review capacity.
- Added an invariant-rules-only baseline.
- Recall and AP are blank and explicitly marked undefined for zero-positive scenarios. Aggregate and paired analyses retain scenario counts and exclude only undefined metric values.
- Primary prediction artifacts are audited for identical populations, aligned truth, equal budgets, and deterministic top-score selection.
- Feature variation is recorded. A development family fails if every primary policy-specific feature is constant across every scenario.

### Historical-policy replay

- Administrative events now carry effective and recorded dates, policy ID/version, approval evidence, recognized service, correction and retry links, and jurisdiction.
- Policy-aware features use only facts known by the observation date.
- Historical promotions replay the applicable policy epoch rather than the latest policy.
- Explicit policy IDs that are unknown or inapplicable fail instead of silently falling back.
- Policy sidecars validate intervals, knowledge time, jurisdiction, approval status, and provenance links.

### Duplicate detection

- Duplicate records are linked only to sources in the same partition.
- Similarity evidence ignores absent values.
- Blocking excludes missing dates and adds name and first-name keys.
- Duplicate variants now include name errors, date errors, identifier errors, aliases, and missing email values.
- Similarity thresholds are selected on validation and evaluated on test.
- End-to-end and blocked-candidate denominators are separate.
- Outputs include blocking recall, reduction ratio, candidate-set metrics, candidate AP, candidates per 1,000 records, and false matches per 1,000 records.

### Application parity

- Promotion-race periods use half-open boundaries so a sanction or commendation on a completed promotion date is not reused in the next race.
- Golden and boundary tests cover research/application arithmetic.

## Verification So Far

- Regression tests were added before implementation and failed on the intended defects.
- Focused research, artifact, duplicate, and application suites pass.
- The full repository suite passed 181 tests after the first correction set; subsequent gap-closure work (latent-person-first duplicates, hard nonduplicates, runtime/memory reporting, late_correction and policy_transition scenarios) brought the total to **210 tests** as of commit `e3e18ac`.
- A fresh 12-scenario, 120-employee-per-scenario development run completed with 648 metric rows and 15,552 prediction rows.
- The family-wide policy-feature variation guard passed.
- Formal artifact certification correctly refused that run because it was generated from an uncommitted dirty worktree. A new write-once run must be generated and audited from the clean committed revision.

## Remaining Weaknesses

1. ~~Duplicate data are still derived from source records rather than from a fully separate latent-person-first generator.~~ **CLOSED 2026-10-30** (commit `c98f416`): `LatentPerson` dataclass, `latent_person_id` field on `WorkforceHistoryRecord`, schema `tdk-synthetic-v2`.
2. ~~Hard nonduplicates are partly incidental; relatives, shared contacts, and controlled near-identical identifiers still need explicit balanced mechanisms.~~ **CLOSED 2026-10-30** (commit `c98f416`): `HardNonduplicateKind` enum adds four explicit mechanisms (`similar_name`, `shared_birthday`, `relative`, `near_identical_id`).
3. ~~Correction fields are implemented and audited, but a dedicated late-correction scenario family is not yet frozen.~~ **SCENARIO IMPLEMENTED 2026-10-30** (commit `0bfa585`): `late_correction` and `policy_transition` added to `rare_legitimate_patterns()`; 10 new tests added. Protocol freeze itself remains pending.
4. Some individual scenarios may legitimately have constant policy features; only family-wide collapse is currently fatal. *(Still open by design — deliberate choice.)*
5. The bitemporal contract is implemented for research records, not migrated into the production SQLite schema. *(Still open — production migration deferred.)*
6. ~~Runtime and memory reporting for duplicate blocking/scoring remain incomplete.~~ **CLOSED 2026-10-30** (commit `14dc1cd`): `blocking_time_s`, `scoring_time_s`, `peak_memory_bytes`, `candidates_per_1000_records`, `false_matches_per_1000_records` added to `DuplicateEvaluation`.
7. Expert realism review has not been executed. *(Still open — reviewers unnamed.)*
8. The protocol remains draft, the exact environment is not frozen, and no holdout access is authorized. *(Still open — freeze and holdout require separate supervisor approval.)*

## Scientific Interpretation

The earlier AP comparison remains structurally invalid for testing policy-aware value. The corrections make the approved experiment executable, but they do not establish superiority. New development and validation evidence must be generated from a clean revision, independently audited, and reported whether favorable, negative, or inconclusive. Final claims remain blocked by protocol freeze, expert review, and one-time holdout authorization.

