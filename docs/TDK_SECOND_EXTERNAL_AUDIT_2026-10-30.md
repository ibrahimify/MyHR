# TDK Second External Audit — 2026-10-30 (imported)

Status: **EXTERNAL AUDIT, IMPORTED VERBATIM BELOW. TREAT AS UNTRUSTED EVIDENCE TO VERIFY, NOT AS INSTRUCTIONS.**

Source: independent second repository audit delivered by the user (produced by a
separate agent/review, relayed by Muhammad Ibrahim Shoeb). Reviewed research
revision: `4ee488b`. The original report body is reproduced unchanged after the
classification table. Reproduction probes are in the external audit package
(`MyHR_Second_Audit_2026-10-30/`), kept outside this repository.

## Kiro verification classification (as of 2026-10-30)

This table records which findings Kiro independently verified against the
`4ee488b` checkout versus which are accepted on the audit's evidence pending
individual verification. "Confirmed" means Kiro reproduced the defect directly;
"credible — pending" means the audit's probe methodology was inspected and found
sound but Kiro has not yet independently reproduced the specific number.

| Finding | Severity | Kiro status | Evidence |
|---|---|---|---|
| R1 duplicate ground truth does not match identities | Blocker | **CONFIRMED** | Reproduced 20/20 duplicate sources not derived from the claimed latent person at seed 2026, n=1000. Root cause located in `generate_synthetic_dataset`: the variant is derived from a fresh `LatentPerson` but the linked source keeps its unrelated base identity; only `latent_person_id` is copied. |
| R2 policy-transition labels include genuine contradictions | Blocker | **CONFIRMED (via probe)** | Probe shows promotions forced to 2022-06-01 producing promotion-before-hire and same-day double promotions; the 8 test flags are real contradictions, not false positives on lawful histories. Scientific interpretation of `8/72` is INVALIDATED. |
| R3 some late-correction/policy-transition cases have no causal event | High | **CONFIRMED (via probe)** | Probe: 12/58 late_correction and 22/58 policy_transition cases have empty causal-event lists. |
| R4 event replacement corrupts current level | High | credible — pending independent reproduction | Matches `_replace_events` hardcoding `current_level="L6"`. |
| R5 corrections inconsistent across rules and features | High | credible — pending | Hand-crafted reproductions described; consistent with supersession applied only to promotions. |
| R6 candidate confusion counts omit FN | High | **CONFIRMED** | Reproduced: 1 missed pair in a 1-candidate universe yields TP+FP+TN+FN=2 > 1. Root cause in `confusion_counts_for_pairs`. |
| R7 bitemporal/version contract partial | Medium/High | credible — pending | Version-ignore and future-effective concerns consistent with `_policy_for_promotion`. |
| R8 hard nonduplicates often not co-partitioned | Medium | credible — pending | Probe shows 3/4 hard pairs span partitions. |
| R9 peak memory is not peak; exports omit timing/memory | Medium | credible — pending | `tracemalloc.compare_to` measures retained diff, not high-water mark; this is clearly correct in principle. |
| R10 source-provenance completeness not enforced | Medium | credible — pending | Auditor rejects empty but accepts partial subset. |
| R11 paper/protocol/status disagree | Medium | credible — pending | Documentation reconciliation needed. |

Repair order being followed: R1 and R6 first (confirmed, contained), then R2/R3/R4,
then regenerate evidence, then remaining findings. Each fix gets a failing
regression test first and independent read-only verification. The holdout remains
locked; no feature expansion; artifacts preserved unchanged.

## Codex takeover status

The first R6 repair was insufficient because it accepted only a universe size and
could not verify pair membership. The takeover repair uses an explicit pair set,
rejects out-of-universe predictions, treats out-of-universe truth as a blocking
miss, and exports the method-specific candidate-universe size. R7 is **partially
resolved**, not closed: version identity and future-effective exclusion are
implemented, while employee-level grandfathering and distinct knowledge-time
views remain open. Artifact `274067cbb57f1dc2` predates the final R6 repair; do
not cite its duplicate candidate-set metrics. The original report below remains
unchanged.

---

# Original external audit report (verbatim)

# MyHR second repository audit — 30 October 2026

## Executive verdict

The project still follows the submitted TDK abstract: an offline MyHR application, a formal progression model, rules-first/raw-versus-policy-aware Isolation Forest evaluation, separate duplicate detection, synthetic histories, evidence-rich human review, and explicit limitations. Many first-audit defects were repaired. However, the newest generators introduce serious ground-truth errors, the bitemporal implementation remains incomplete, candidate-set metrics contain a counting defect, and several “gap closed” statements are stronger than their tests support. Do not freeze the protocol or present the latest artifact as a valid estimate of false-alert behavior until the high-priority findings below are resolved.

This is a completed read-only code/data audit, not a protocol modification, code repair, supervisor approval, or holdout authorization. No production source, repository test, paper, protocol, saved historical artifact, GitHub issue, or PR was changed. All new evidence was written outside the Git repository. The worktree remained clean.

## Reviewed snapshot and branches

Research revision: `4ee488b759bcf7c4bd21cc3ab954e4fb48f9a2e7`.

| Remote branch | Tip | Review result |
|---|---|---|
| master | 7d9ed70 | Unchanged Project Lab checkpoint |
| thesis | 8fd7434 | Unchanged pre-packaging application |
| thesis-final-polish | a9dac4b | Unchanged polished application; still lacks the race-boundary fixes present on research |
| research/policy-aware-anomaly | 4ee488b | 16 new commits since ecad126; primary focus of fresh source, tests, data, and manuscript audit |
| maintenance/research-repository-hygiene | b6df03b | Unchanged; merged into and reachable from research |

The application branches are successive ancestors; maintenance is also reachable from research. Their unchanged status does not mean they receive fixes committed only to research. In particular, `thesis-final-polish` still uses inclusive `issued_at >= race_start` in six places where research changed the boundary. Prepare an isolated application-only backport if that is the branch used for the BSc package; do not merge unready research merely to deliver that fix.

I compared all branch tips/history and reviewed all changes since the prior audit, with source examination of the affected data, policy, evaluation, metrics, reporting, tests, and paper. I did not rerun old branch suites or inspect every unchanged UI asset.

Live GitHub checks at review time: PR #1 open, draft, targeting `thesis-final-polish`; head `4ee488b`; both Python test checks and GitGuardian passed.

## Verification performed

- Complete current suite: **212 tests passed in 105.435 seconds**.
- Nine external adversarial contract checks: **nine assertion failures, no execution errors**. They are evidence probes, not additions to the production test count or automatic approval of new domain semantics.
- Citation registry: valid, 18 bibliography/provenance entries and 15 claims; Holm and reliability full-text claims remain unverified. Strict local full-text verification was unavailable because the preserved literature artifact is outside Git.
- Regenerated the existing independent development matrix: 12 scenarios × 360 employees = **4,320 histories**, including **864 test histories**.
- Created a new development artifact outside Git, with identity `db1a15646d9e76ba`, 648 metric rows, 46,644 prediction rows, 57,562 administrative-event rows, 24 policy epochs, and 4,320 truth rows. The artifact auditor returned **verified**, `holdout_accessed: false`.
- Re-derived primary recall delta **0.0092592593**, interval **[-0.0462962963, 0.0833333333]**, sign-flip **p=1.0**, matching the roadmap to reported precision. Reproducing these numbers does not repair their input labels.
- Independent environment: Python 3.12.14, scikit-learn 1.8.0, NumPy 2.3.5, pandas 2.2.3, PySide6 6.11.0, SQLAlchemy 2.0.49. This is not the historical 3.13.5/research-lock environment. Numerical agreement here does not establish universal bitwise reproducibility.
- The historical on-disk experiments and rendered DOCX/PDF are not in the clone; this audit did not inspect their bytes. The regenerated artifact has its own metadata/source revision and must not replace the earlier artifact, even though its deterministic artifact ID is the same.
- No protected holdout was generated, inspected, or scored. The destructive demo seeder was reviewed as source and was not executed.

## Improvements verified since the previous audit

The omission intervention now actually removes an existing increment. Approval-bypass cases explicitly carry `approval_status=bypassed`, no approval reference, and adequate service on a progression track. Ordinary histories now include commendations, resolved sanctions, multiple reviews and sometimes multiple promotions. Structured historical policy fields exist and reach the adapter. The primary residual gate now uses invariant checks and equal populations/budgets. Zero-positive recall/AP are explicitly undefined. Missing identity values no longer count as positive matching evidence. Validation threshold selection and test-partition duplicate evaluation exist. The same-day commendation race-boundary double-count fix is present on research. These are material improvements and should be preserved.

## Confirmed findings

### R1 — Blocker: latent-person duplicate ground truth does not match the identities

**Source:** `src/services/anomaly_detection/synthetic_data.py:366`, `:390`, `:407`.

Each duplicate is derived from a newly generated `LatentPerson`, but its referenced source keeps its unrelated original identity. Only `latent_person_id` is copied onto the source. There is no source-identity derivation in the final-record loop.

**Reproduction:** seed 2026, 1,000 employees, anomaly_rate 0.10, rare_legitimate_rate 0.04. All **20/20** duplicate/source pairs have sources not derived from the claimed latent person. Example: duplicate `EMP-0023` derives from **Anna Schmidt / LATENT-000000**, but its linked source is `EMP-0002`, **Bence Kovacs / NID-000002**. The test split has four ground-truth duplicate pairs; all three matchers return zero true positives in the probe. Those false negatives cannot be interpreted as matcher quality against genuine variants of one person.

**Why 212 tests miss it:** new tests check latent ID presence/format, tag equality, and partition containment, not whether both identities came from the same latent facts. A shared tag does not make two unrelated identities the same person.

**Repair contract:** generate one latent entity per complete cluster; derive the canonical identity and all variants from it; assign the cluster once; preserve an explicit derivation/corruption ledger. Enforce that one source cannot be silently overwritten with another latent-person assignment and exclude cluster members from hard-nonduplicate mutation. Test identity derivation, not just matching tags. Keep old artifacts as invalidated/superseded development evidence; do not rewrite them.

### R2 — Blocker: new policy-transition “rare legitimate” labels include genuine contradictions

**Source:** `src/research/independent_scenarios.py:635`.

Every promotion in a selected history is re-dated to **2022-06-01**, regardless of hire date, prior promotions, or required service. This can create promotions before employment, inadequate service, two level changes on one day, and event-order dependence on hashed IDs. The evidence text nevertheless says the history satisfies the historical policy.

**Across all 4,320 histories:** 58 policy-transition-labelled rare cases; 11 have invariant findings; 36 have policy-rule findings. **Test split:** 12 policy-transition rare cases; eight receive findings; two have promotions before hire. All eight reported test rare-legitimate flags come from this malformed family.

Examples:

- `ind-dev-05 / I-00041`: hired **2023-09-26**, promotion **2022-06-01**.
- `ind-dev-05 / I-00024`: hired **2022-04-28**, promoted **2022-06-01**, despite a 30-month service requirement and no sufficient compensating evidence.
- `ind-dev-10 / I-00203`: both L7→L6 and L6→L5 moved to **2022-06-01**.

Therefore the current **8/72** is a reproducible *alert count among generator-labelled rare cases*, not a validated false-positive rate on genuinely lawful histories. For these examples the checker has a substantive reason to flag the record; the ground truth is wrong. This is different from the older 39/72 historical-policy counterexample.

**Why tests miss it:** the new transition fixture uses only the stable-administration population and one seed. It checks that some cases/legacy IDs exist and that invariant findings are absent in that fixture, not policy validity across every matrix cell and each realized case. The artifact auditor checks rows/provenance, not the semantic truth of the rare-legitimate label.

**Repair contract:** build a transition history whose hire, eligibility, decision date, and policy epochs are mutually consistent by construction. Preserve subsequent promotions on a coherent timeline. Hand-derive at least one valid older-policy case and one genuinely invalid near-match. Run universal per-case contracts over all populations, sizes, and declared development seeds; do not adjust cases to favor a method. The exact new scenario design still needs the recorded human decision required by the repository.

### R3 — High: some “late correction” and “policy transition” cases do nothing

**Sources:** `independent_scenarios.py:336`, `:599`, `:631`, `:642`.

The eligibility fallback for both new patterns requires an increment rather than a suitable promotion. Some selected employees consequently have no promotion to correct or re-stamp, yet receive rare-legitimate labels and explanatory text asserting an intervention.

**Across all partitions:** **12/58 late-correction** cases and **22/58 policy-transition** cases have empty causal-event lists. Six of the 72 test rare cases have no realized intervention. This dilutes mechanism-specific denominators and makes “coverage” claims too strong.

**Repair contract:** require the actual preconditions before truth allocation, or explicitly classify a different realized mechanism instead of claiming a correction/transition. Require nonempty, applicable causal evidence for every intentionally altered case. An empty list can be legitimate for ordinary records, not as a silent substitute for a promised intervention.

### R4 — High: event replacement corrupts current level

**Source:** `independent_scenarios.py:664`.

`_replace_events()` sets `current_level="L6"` whenever any promotion exists. It ignores the last active promotion's resulting level. In the 12×360 probe **240/4,320 histories** have `current_level` inconsistent with their last non-superseded promotion. For example, a history ending at L5 can be reset to L6 by adding a sanction or another unrelated intervention.

Derive current level from the effective event state and observation date, with explicit ordering and correction handling. Add a per-history state invariant; schema checks that a progression employee has some level do not establish the right level. This currently contaminates records even if the matched numeric feature set does not use current level directly.

### R5 — High: corrections have inconsistent meaning across rules and features

**Sources:** `src/services/anomaly_detection/policy_history.py:59`, `:73`, `:164`; `features.py:134`; `deterministic_checks.py:validate_invariant_record`.

Supersession is applied only to the list of promotions assessed by the policy engine. Superseded commendations and sanctions still enter credit/delay calculations; raw event features and invariant checks still see superseded invalid facts.

**Handcrafted reproductions:**

1. Correct a +6-month commendation to +1 month via a visible correction link. The policy engine grants **7 months**, not 1.
2. Correct a wrongly recorded L7→L8 promotion to L7→L6. Policy assessment excludes the old promotion, but invariant filtering still flags the old invalid level change, removing the repaired history from the primary comparison.
3. A promotion referencing itself as its correction target disappears from assessment without an error. More generally, the auditor checks that targets exist but does not reject self-links, cycles, wrong event kinds, or branching correction conflicts.

**Repair contract:** centralize a pure snapshot/effective-state resolver shared by deterministic checks and feature extraction. Preserve raw audit evidence separately. Define corrected-state features versus correction-volume features explicitly, apply supersession to all relevant fact types, and validate correction graphs. Do not silently give the policy representation repaired facts while the raw representation receives contradictory active facts without describing that as an additional experimental factor.

### R6 — High: candidate-set confusion counts are arithmetically wrong

**Source:** `src/services/anomaly_detection/duplicate_detection.py:314`.

The helper calculates `TN = candidate_pair_count - TP - FP`, omitting FN. For a candidate universe with one real duplicate, and no predicted match, it returns TP=0, FP=0, **TN=1, FN=1**: two counted outcomes for one candidate.

Use the declared candidate universe consistently and subtract TP, FP, and FN. Verify predicted/truth pairs belong to that universe. Do not mask impossible denominators by clamping negative TN to zero. Exact/email matches can also fall outside the similarity block, so their candidate-set metrics need method-specific candidate universes or an explicitly shared one. Test full count conservation and precision/recall/FPR against independent hand-calculated examples.

The current F1 threshold ordering does not use TN, so this specific TN bug does not by itself prove threshold selection changes. It does corrupt candidate counts, negative denominators, and candidate false-positive rates.

### R7 — Medium/high: the bitemporal/version contract is not fully enforced

**Sources:** `policy_history.py:124`; `features.py:134`; `scripts/audit_tdk_protocol_artifact.py:465`.

- `policy_version` is carried but ignored by `_policy_for_promotion`. A promotion naming a real policy ID and a nonexistent version is accepted.
- A policy-wide `grandfather_previous_policy=True` permits out-of-interval use without employee-level grandfathering entitlement evidence. Both generated epochs set the flag. This is broader than proving a particular employee's exception.
- Recorded-time visibility is filtered, but a future-effective promotion already recorded is counted as a completed promotion and assessed. A fixture with a 2027-01-01 promotion, recorded in 2026, enters the 2026-12-31 feature snapshot. If planned events are intended, give them a distinct role rather than mixing them with completed histories.
- Policy knowledge time is fixed to `promotion.recorded_date`, while event visibility uses `record.observation_date`. The contract must distinguish “what was known at the original decision” from “best corrected reconstruction as of a later review”; retroactively recorded policy amendments need fixtures for both.
- The artifact auditor rejects any event recorded before its effective date. Advance-approved future facts are possible if included in the chosen domain; the implementation and auditor currently have different implicit assumptions. Specify the domain instead of relying on either convention accidentally.

At minimum, enforce version identity, explicit entitlement, time-view semantics, and valid correction provenance before claiming full historical replay. The implementation is a useful partial research contract, not a complete bitemporal database model.

### R8 — Medium: hard nonduplicates often are not hard pairs in the evaluated split

**Source:** `synthetic_data.py:414`.

Exactly four targets are modified across the whole dataset. Anchors are chosen without matching the target's partition, and the anchor relationship is not stored. In the seed-2026 probe the shared-birthday pair spans validation/test, the relative pair spans test/train, and the near-ID pair spans train/test. Thus these intended pairs are not jointly present in the test comparison; only the similar-name pair is co-partitioned, in train.

This does not prove there are no incidental hard negatives in test. It proves presence of mechanism tags across the dataset is not evidence that all four intended pair mechanisms were evaluated. Generate and record hard-negative pairs inside each required evaluation partition, preserve the anchor ID, and test that both endpoints are scored/blocked as intended. Do not mutate a duplicate's canonical source while injecting a hard negative.

### R9 — Medium: reported “peak memory” is not peak memory, and exports omit runtime/memory

**Sources:** `duplicate_detection.py:201`, `:235`; `scripts/run_tdk_research_experiment.py:_duplicate_rows`.

The field is the largest retained per-line snapshot difference, not the high-water allocation. In an instrumentation probe that allocated and released an 8 MB temporary scoring buffer, the function returned **24,368 bytes**, while tracemalloc's actual peak was **8,126,894 bytes**. These numbers describe the probe, not production workload memory.

Blocking is also performed twice in the similarity path: once in the timed blocking phase and again inside scoring. Exact methods incur an unnecessary similarity-block computation. This makes separate timing labels misleading. `tracemalloc.stop()` also turns off caller-owned tracing and is not protected by `finally` on failure.

Finally, `_duplicate_rows()` exports no blocking time, scoring time, or memory fields. The dataclass properties and export disagree over whether “candidates per 1,000” means all blocked pairs or surfaced alerts.

Use `get_traced_memory()` with an explicitly documented Python-allocation scope (not total process RSS), preserve tracing ownership, measure the actual phases once, and serialize measured values and units. Current tests only require nonnegative numbers and will pass for a constant zero; add a transient-allocation and export-contract regression.

### R10 — Medium: source provenance verification still permits partial coverage

**Source:** `scripts/audit_tdk_protocol_artifact.py:136`.

The checker rejects empty hashes but accepts any nonempty subset, without enforcing the complete required source-path set. A direct probe retained only the hash of `scripts/run_tdk_independent_development.py`, removed the other 18 entries from an in-memory metadata copy, and the verifier accepted it. A single legitimate file hash can therefore satisfy that portion of certification after all the other source entries are removed. Required-source completeness should be schema/version-defined and tested. Hashes attest to stored bytes; they do not independently prove the executed scientific model or label meaning.

### R11 — Medium: current paper, protocol, status, and generated package disagree

- `docs/TDK_PAPER_DRAFT.md:486` says the approved redesign “is not yet implemented,” while `:532` says the boundary, schema, endpoint, and zero-positive handling are implemented.
- `:561` has a duplicated, broken paragraph ending beginning “icated checks”.
- The conclusion remains centered on the old constant-feature experiment while also mentioning newer executable evidence. Keep the old diagnosis as historical, and clearly separate the new implementation and its unresolved label defects.
- The protocol's implemented-boundary section still describes the full-policy residual filter and then says the newer design is not fully implemented. The live scenario specification lists only the original three rare patterns. These are active documents, not immutable dated reports.
- The latest roadmap correctly calls new scenario definitions exploratory and pending approval; earlier “gap closed” lines are historical entries and need clear supersession, not silent erasure. The paper should not turn current invalid transition labels into a historical-policy false-positive claim.
- The paper builder still targets old saved artifact paths and historical figure values, and its generated decision sheet still offers recommendations as if methodology choices were pending. Historical figures are not inherently wrong, but every table/figure must bind explicitly to an audited run and its interpretation; the new paper and generated package need synchronized status, provenance, and page-by-page rendering before delivery.
- The decision record says “supervisor answers relayed by Muhammad Ibrahim Shoeb.” The visible conversation establishes Ibrahim's own approval, not independent supervisor endorsement. Record the actual approver accurately unless a supervisor communication exists elsewhere. This does not retract Ibrahim's implementation authorization.

## Additional gaps and limits to make explicit

### Primary experiment

The primary invariant-negative raw/policy comparison has equal populations and budgets, which is good. But wrong-policy controls and feature ablations run on the whole population, not as corresponding primary residual comparisons. A whole-population control cannot by itself establish attribution in the primary residual population. Add approved controls to the same population or narrow the claim.

The “shuffled” policy control samples from three stock profiles by employee hash rather than permuting the actual policy/epoch assignments. It changes multiple things, including temporal context. Rename it as a random-policy control or implement the predeclared permutation. The matched policy columns are three transformations of one deficit; equal column count is not equal information content. Include transparent deficit-only rules and acknowledge the engineering-representation contribution rather than claiming isolated causal policy value from dimension matching alone.

The independent matrix still has one seed per population×error cell, with rare pattern tied to the cell index, fixed employee count and rates. It cannot separately identify effects of population, error, rare pattern and random realization. The stated 30-seed primary-condition requirement or justified alternative remains unmet. The exact experimental population, noninferiority meaning of “preserving detection,” multiplicity family, and power/replication plan must be fixed before final evaluation.

### Data coverage

A finite synthetic suite cannot cover “all edge cases.” Publish a requirement-to-fixture matrix and explicitly exclude unsupported mechanisms. Remaining priorities include leap dates/month ends, rehire and multiple employment spells, transfers and track changes, missing or conflicting policy versions, actual corrected sanctions/commendations, incomplete evidence and ambiguity, zero/all-positive or empty residual populations, ties/zero review capacity, multi-error histories, and training/population shifts.

The independent generator still produces 83/4,320 histories with hire age under 16 because DOB is independent of hiring. This is a realism-contract issue, not a legal claim about minimum employment age. The original-v2 anomaly allocation still prioritizes promotion-track candidates. Do not claim Other-track coverage of all general administrative errors without testing it. The ambiguous category is still mapped to CLEAN by the adapter; retain an explicit indeterminate/adjudication state before using the promised realism review.

The standalone 300-person demo seeder uses a fixed May-2026 reference date and has no research labels or train/validation/test contract. Treat it as UI/demo data, not the research benchmark. It resets `myhr.db`; the audit did not execute it.

### Application and packaging

Research anomaly evaluation is still CLI/service code: there are no imports from the anomaly package in main.py, src/ui, or src/database. Do not imply that a production anomaly-review UI or full research-to-SQL pipeline is implemented. The existing promotion-evidence UI is a separate implemented contribution. Bitemporal fields remain research-only; production migration is deferred and must be stated as such.

Pin and test a reproducible environment before freeze. CI currently uses broad research dependency ranges on Python 3.12, while the saved lock describes a Python-3.13.5 environment. The regenerated artifact ID depends on sources/configuration, not installed package versions, so identical IDs are not a guarantee of identical numerical environments. Keep environment metadata and manifest as the authority and never overwrite an old run.

## Alignment with the submitted abstract

| Abstract promise | Current assessment | Completion requirement |
|---|---|---|
| Formal progression model, credits/delays, policy changes | Implemented in part; current corrections/version gaps | Repair snapshot/correction/version semantics; independent golden fixtures |
| Raw and policy-conditioned Isolation Forest | Implemented; equal primary capacity works | Valid labels and approved repeated-scenario design, residual controls |
| Rule checks and contextual statistical baselines | Implemented | Explicit rule scope and honest baseline comparisons |
| Reproducible injected errors and rare legitimate histories | Infrastructure works; new rare labels invalid | Fix R2/R3, regenerate versioned development evidence |
| Separate duplicate matching against exact/normalized | Implemented but current identity ground truth broken | Fix R1/R6/R8 before interpreting results |
| Precision, recall, F1, FPR, workload, runtime | Core metrics exist; candidate FPR and runtime/memory exports defective | Fix R6/R9 and independent metric/export tests |
| Explainable human review | Findings and promotion evidence exist; no anomaly-review UI | Scope implementation claims accurately; usability remains optional |
| User study if time permits | Not performed | Can be omitted honestly; distinguish it from the protocol's required realism review |
| Future real-world validation | Still future | Retain limitation; do not imply external validity |

The abstract does not require a favorable policy-aware result. It does require a valid controlled comparison; malformed labels cannot be salvaged by passing artifact hashes or reframing the result positively.

## Recommended repair sequence for the local engineer

1. Freeze feature expansion while repairing correctness; retain every inspected artifact and mark its exact limitations. No holdout access.
2. Add failing regression fixtures for R1–R7. Fix canonical latent identities and lawful transition construction first, then no-op eligibility, current-level derivation, central effective-state resolution, and count conservation.
3. Strengthen tests to validate actual identity derivation, every causal intervention, every declared legitimate case, all matrix cells/populations, and independent expected arithmetic. Keep metadata/infrastructure tests, but stop using their count as scientific certification.
4. Correct the duplicate candidate universe, hard-negative pair placement, threshold edge cases, timing/memory measurement and CSV exports.
5. Strengthen source-provenance completeness and causal-label auditing. The current audited artifact proves reproducibility but not label validity.
6. Regenerate development and validation from a clean committed revision with an exact recorded environment; run arithmetic/provenance and independent semantic checks. Make no post-hoc seed selection.
7. Resolve the documented scenario proposals and reviewer nomination, approve the final matrix and analysis, and only then consider a separate freeze decision.
8. Rewrite active paper/status documents around the final verified implementation; bind figures to artifacts, rebuild the package, render every page, and reconcile title/registration fields with the author.
9. Backport stable application-only boundary fixes to the intended thesis packaging branch through an isolated reviewed change. Keep research PR #1 draft unless the author separately authorizes its merge.

## Reproduction files in this package

- `probe_current.py`: current development-world, duplicate-identity, hard-negative placement, metric and snapshot probes.
- `test_adversarial_current.py`: nine contract assertions; all fail at the reviewed revision. They document gaps rather than proving these are the only defects.
- `probe_results.json`, `memory_export_probe.json`, `audit_scope.json`: numeric evidence and environment/snapshot details.
- `full_tests.txt`, `adversarial_tests.txt`: complete run logs.
- `development_run.txt`, `artifact_audit.txt`, and `development_artifacts/independent_development_db1a15646d9e76ba/`: freshly generated, audited development evidence. Never merge it over an earlier run of the same ID.

Run from a checkout of the reviewed revision with dependencies installed:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
PYTHONPATH=. python /path/to/probe_current.py
PYTHONPATH=. python /path/to/test_adversarial_current.py -v
python scripts/audit_tdk_protocol_artifact.py /path/to/development_artifacts/independent_development_db1a15646d9e76ba
```

On Windows Command Prompt, set `QT_QPA_PLATFORM=offscreen` and `PYTHONPATH=.` as separate `set` commands. The probes write only next to their own files. No protected data or paid service is needed.

