# TDK Autonomous Research Roadmap

## Second External Audit — Invalidations And R1/R6 Repairs - 2026-10-30

A second independent repository audit (imported verbatim to `docs/TDK_SECOND_EXTERNAL_AUDIT_2026-10-30.md`, reviewed revision `4ee488b`) found serious ground-truth defects that the 212 green tests missed because those tests checked metadata, not meaning. Kiro independently reproduced the confirmed findings before acting. This entry supersedes the scientific interpretations below where they conflict.

**INVALIDATED SCIENTIFIC INTERPRETATIONS (do not cite):**

- **The `8/72` policy-transition reading is INVALIDATED (finding R2, confirmed).** The `policy_transition` generator forced every promotion to 2022-06-01 regardless of hire date or prior promotions, creating promotions-before-hire, insufficient-service, and same-day double promotions. The 8 deterministic flags are responses to **genuine contradictions**, not false positives on lawful histories. The earlier framing ("8/12 policy-transition cases falsely flagged", "lawful-but-unusual false alerts motivating the bitemporal contract") must not be used. The arithmetic (`8` flags) is reproducible; its interpretation as a lawful-history false-positive rate is wrong.
- **The latent-person-first duplicate "fix" (commit `c98f416`) was broken (finding R1, confirmed).** Duplicate variants were derived from a fresh latent person, but the linked source kept an unrelated base identity — only the `latent_person_id` tag was shared. All 20/20 duplicate/source pairs were unrelated identities. The duplicate-matching ground truth was invalid, so any duplicate-detection result from that code is not interpretable.
- **Artifact `db1a15646d9e76ba` is preserved UNCHANGED as invalidated exploratory evidence.** It is not deleted or rewritten (per audit guidance). It must not be cited as a valid estimate of false-alert behavior or duplicate-matcher quality. A corrected development artifact must be regenerated only after R1–R4 are fixed and the scenario definitions are approved.

**REPAIRS COMPLETED THIS SESSION (local only, not pushed):**

- **R1 (duplicate ground truth) — FIXED and independently verified.** The source record of each duplicate cluster now receives the latent person's canonical identity (`_canonical_latent_identity`), so source and variant are genuinely the same person. Cluster members are excluded from hard-nonduplicate mutation. New regression tests (`tests/test_second_audit_repairs.py::R1*`) check identity *derivation*, not just tags; the audit's own adversarial check `test_source_identity_comes_from_shared_latent_person` now passes. A read-only independent auditor confirmed 20/20 source identities match the latent person, 0 mismatches, partition containment intact, 0 hard-nonduplicates carrying a latent tag.
- **R6 (candidate confusion counts) — FIXED after takeover review.** The first repair accepted only a universe size and capped TN, which could conserve counts while assigning pairs to the wrong universe. `confusion_counts_for_pairs` now accepts the explicit pair set, rejects predictions outside it, intersects truth with it, and partitions that set exactly. Similarity uses its blocked-pair set; exact and normalized-exact methods use the complete partition pair set. Candidate-universe size is exported separately, and candidates per 1,000 now means surfaced review candidates. Hand-calculated membership, blocking-miss, rejection, and conservation tests pass.
- 219 tests pass (212 + 7 new semantic regression tests). Holdout remains locked. No feature expansion. No push/merge.

**R2/R3/R4 — FIXED and independently verified (2026-10-30, local only):**

- **R2 (lawful transition construction).** `policy_transition` now rebuilds a single legacy-epoch L7->L6 promotion at `hire+30 months` (within the legacy epoch, on/after hire), stamped `legacy-pre-2023`. Zero invariant findings on all policy_transition rare cases; no promotion-before-hire, no same-day double. Eligibility requires `hire+30mo <= 2022-12-31`. Recorded as Proposal 4 (supersedes Proposal 2) in `TDK_PROTOCOL_CHANGE_PROPOSALS.md`.
- **R3 (no-op rare cases).** `late_correction` and `policy_transition` eligibility now require a PROGRESSION-track employee with an existing promotion. Across `independent_scenario_matrix(360)`, 0 rare-legitimate cases have empty causal events (was 12/58 late_correction + 22/58 policy_transition). Recorded as Proposal 5.
- **R4 (current-level corruption).** `_replace_events` now sets `current_level` to the last effective (non-superseded) promotion's `level_after` instead of hardcoding `L6`. 0/4320 histories mismatch (was 240/4320).
- **Scenario-definition side effect (Proposal 6):** honest eligibility revealed `rapid_expansion` (hired 2021+) cannot host a lawful legacy transition, so the matrix now skips that pairing; `policy_transition` appears on 1 development scenario instead of 2. Recorded as a pending proposal; reduced coverage is the correct tradeoff, pending supervisor decision.
- Independent read-only auditor re-derived all three from generated data: R2/R3/R4 all PASS, no test-value shortcuts, 12 scenarios intact.
- 224 tests pass (219 + 5 new R2/R3/R4 semantic regression tests).

**CORRECTED ARTIFACT REGENERATED (2026-10-30, local commit `abaf175`):**

- New development artifact `274067cbb57f1dc2` generated from the clean committed R1–R4/R6 fixes. Audit status: **verified**, `holdout_accessed: false`. 12 scenarios, 864 test histories, 57,547 administrative events, 24 policy epochs, 4,320 truth rows.
- **Deterministic policy rules now flag 0/72 test-split rare-legitimate histories** (was 8/72 with the broken `policy_transition` generator). This directly confirms the R2 fix: once the transition histories are genuinely lawful, the current-policy checks correctly leave them unflagged. The invalid `8/72` "false positives on lawful histories" reading is replaced by a clean `0/72`.
- Primary residual endpoint (`fixed_review_budget`): recall delta mean `+0.0185`, 95% CI `[-0.0278, +0.0741]`, sign-flip p=0.75. **No policy-aware advantage was demonstrated in this exploratory development run.** The interval does not establish equivalence or absence of a potentially useful effect.
- Independently re-derived (code-path, read-only, not an independent review): 0/72 flagged and +0.0185 confirmed from raw CSVs.
- This is an EXPLORATORY development artifact from scenario definitions still PENDING supervisor approval (Proposals 1,4,5,6). It is not confirmatory evidence. The invalidated `db1a15646d9e76ba` is preserved unchanged.

**R5 fixed; R7 partially repaired and explicitly incomplete (2026-10-30, local):**

- **R5 (correction semantics).** New central `effective_state` resolver (visibility + supersession + graph validation) used by policy history, deterministic checks, and features. Corrected +6mo commendation now yields 1mo (was 7); corrected unresolved sanction yields 0 delay; superseded invalid promotion not flagged; self-link/cycle raise; invisible correction does not supersede. Independent auditor: all checks PASS. Local commit `63c5dcf`.
- **R7 (PARTIAL: bitemporal/version enforcement).** `_policy_for_promotion` rejects a real policy ID paired with a nonexistent version (R7.1), and `effective_state` excludes future-effective events from completed-history views (R7.3). However, employee-level grandfathering entitlement (R7.2) and separate knowledge-time versus observation-time views (R7.4) remain unimplemented modeling requirements. R7 must not be described as closed.
- 234 tests pass.

**R8, R9, R10 — FIXED and independently verified (2026-10-30, local):**

- **R8 (hard-nonduplicate co-partitioning).** Added `hard_nonduplicate_anchor_id` field; injection now selects anchor+target from the SAME split (preferring TEST, with VALIDATION/TRAIN fallback), so the intended difficult pair is jointly present in the evaluated partition and traceable. Independent auditor: all 4 hard pairs co-partitioned and in TEST across seeds 2026/2027/2028; none leak into true pairs. Fallback regime also covered by test.
- **R9 (memory measurement/exports).** `peak_memory_bytes` now uses `tracemalloc.get_traced_memory()` (true high-water mark, not retained snapshot diff); `tracemalloc.stop()` in a `finally`, caller tracing state preserved; blocking computed once and reused via a `blocked_pairs` argument (no double blocking); CSV export now includes `blocking_time_s`, `scoring_time_s`, `peak_memory_bytes`. Independent auditor: all structural guarantees PASS, candidate equivalence confirmed.
- **R10 (provenance completeness).** The artifact auditor now requires provenance `source_sha256` to cover the COMPLETE `PROVENANCE_SOURCE_PATHS` set, not an arbitrary non-empty subset. Independent auditor: subset rejected, complete set accepted, and artifact `274067cbb57f1dc2` still audits "verified" under the stricter check.
- Two brittle pre-existing tests updated to match corrected behavior (threshold-default inspection; audit fixtures now supply complete provenance). 244 tests pass.

**R11 — RECONCILED (2026-10-30, documentation only):**

- Removed the duplicated/corrupted paragraph fragment in the paper conclusion (`TDK_PAPER_DRAFT.md`).
- Fixed the implementation-status contradiction: the invariant-only residual boundary, recall-primary endpoint, equal budget, and bitemporal contract are now described as IMPLEMENTED (and exercised by the current development artifacts) but NOT frozen; expert review and the holdout matrix remain unimplemented. Protocol `Implemented Draft Protocol Boundary` section updated to match.
- Corrected the approver attribution across the decision records: the 29 October decisions are the project author's (Ibrahim's) own implementation authorizations, not a separately documented independent supervisor endorsement. The earlier "supervisor answers relayed by..." phrasing overstated independence and was corrected in `TDK_SUPERVISOR_DECISIONS_2026-10-29.md`, `TDK_SUPERVISOR_DECISION_SHEET.md`, and the paper.
- Updated the paper conclusion so it no longer presents an invalid transition reading as a historical-policy false-positive claim: the older `39/72` is marked historical, the intermediate `8/72` is marked INVALIDATED, and the corrected artifact `274067cbb57f1dc2` (0/72 flagged, recall delta +0.0185, no advantage) is cited as the current exploratory diagnostic.
- Doc-sensitive tests (supervisor package) still pass. 245 tests pass.

## SECOND-AUDIT REPAIR STATUS — R7 remains partial (2026-10-30)

R1–R6 and R8–R10 have implementation repairs with semantic regression coverage; R11 was reconciled. R7 is only partially repaired because R7.2 and R7.4 remain open. The scenario definitions (Proposals 1,4,5,6) remain PENDING human approval; expert-reviewer nomination, protocol freeze, and holdout authorization remain human-gated. The holdout was never generated, inspected, scored, or unlocked. Artifact `274067cbb57f1dc2` predates the final explicit-universe R6 repair: its progression-anomaly diagnostics are unaffected, but its duplicate candidate-set metrics must not be cited and require regeneration from the repaired revision.

## Scientific-Scope Correction For New Scenario Families - 2026-10-30

An independent review (Codex, relayed by Muhammad Ibrahim Shoeb) correctly flagged that the preceding entry overstated the scientific standing of the new scenario work. This entry supersedes it on interpretation; the engineering facts below remain accurate.

- **Artifact `db1a15646d9e76ba` is an EXPLORATORY development artifact, not confirmatory evidence.** The auditor returned `verified`, which attests only to reproducibility of the implemented arithmetic, provenance integrity, and `holdout_accessed: false`. It does not attest to scientific validity, approved scenario definitions, or any policy-aware claim.
- **The `late_correction` and `policy_transition` scenario definitions are PENDING HUMAN APPROVAL.** Supervisor Decision 4 (2026-10-29) approves the bitemporal *contract capability* (policy versions, recognized service, correction provenance, effective/recorded time) and Decision 6 requires the holdout matrix to *cover* policy transitions and lawful exceptions. Neither decision approves the specific implementation details added here: the −12-month mis-dating mechanism, the `legacy-pre-2023` re-stamp with a 2022-06-01 effective date, one-record-per-pattern injection, or the `index % 5` matrix composition. Per AGENTS.md ("Do not silently change ... scenario definitions ... Record proposed changes separately for supervisor approval"), these are recorded as a pending proposal in `TDK_PROTOCOL_CHANGE_PROPOSALS.md` and must not be treated as frozen.
- **The readings were re-derived through an independent code path** by `scripts/reproduce_db1a15646d9e76ba_readings.py`, which reads only the artifact CSVs and does not import the generator, `protocol_evaluation.py`, or the auditor. This is a **code-path re-derivation, not an independent review**: the same author (Kiro) implemented both the scenario code and the re-derivation, so it does not substitute for verification by a separate read-only auditor or human.
  - **Denominator resolved (corrected).** An earlier draft wrote `8/348`; that was **wrong** — 348 pools train+validation+test, but only the test split is evaluated. The correct pooled denominator is the **test-split rare-legitimate count = 72**, giving **8/72 = 11.1%** on the test split. The auditor's `rare_legitimate_count` sums to exactly 72 across the 12 scenarios, confirming this. The term `8/72` is a pooled **test-split** rate and must always be labelled as such.
  - **Scenario-level attribution:** of the 72 test rare-legitimate records, 12 are `policy_transition`; **all 8 flags fall on `policy_transition` cases (8/12 = 66.7% of policy-transition test cases), and 0/60 of the other four patterns.** Zero flags came from `late_correction`, confirming the supersession fix.
  - (c) **recall delta +0.0093, paired bootstrap 95% CI [-0.0463, +0.0833]** re-derived to four decimals with a fresh bootstrap (seed 20261030). No evidence of policy-aware advantage.
  - These remain **exploratory** readings from an unapproved scenario definition. A separate read-only auditor still needs to verify the raw rows, denominator, scenario membership, and the all-policy-transition attribution before any document cites them as settled.
- **Feature development is paused.** Next work is paper completion and the supervisor package, not new scenarios.
- **Correction to earlier framing:** "all remaining work is human-gated" was inaccurate. Unblocked, non-gated work includes paper completion, traceability checks, figure/table generation, citation verification (`scripts/verify_tdk_citations.py --require-local-artifact`), and independent artifact auditing. Human-gated items are specifically: scenario-definition approval, protocol freeze, expert-reviewer nomination, and holdout authorization.
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

### Engineering facts (unchanged, accurate)

- Adding `late_correction` and `policy_transition` to `rare_legitimate_patterns()` changed the 12-scenario development matrix composition (patterns assigned `index % 5`).
- Two real bugs were found and fixed while generating the artifact:
  - `assess_promotion_history` evaluated both a correction-superseded promotion and its correction as independent events, and the re-dated erroneous event fell outside its declared policy epoch. Fix: exclude any promotion whose `source_id` appears as a `correction_of_source_id` on a visible event; stamp the erroneous event with the policy applicable at its earlier date. Commit `3e9edd2`.
  - The erroneous event used an approval status outside the auditor's accepted domain. Fix: use `approved`. Commit `0f1f32c`.
- Artifact `db1a15646d9e76ba` was generated from clean commit `0f1f32c`: 12 scenarios, 864 test histories, 108 anomalies, 72 rare-legitimate, 57,562 administrative events, 24 policy epochs, 4,320 truth rows.
- Provisional readings (pending independent read-only verification): primary residual endpoint recall delta mean `+0.009`, 95% CI `[-0.046, +0.083]`, sign-flip p=1.0 (no evidence of advantage); deterministic rules flagged **8 of 72 test-split rare-legitimate histories (11.1%)**, all 8 on `policy_transition` cases (8/12 of policy-transition test cases).
- All 212 tests pass.

## Runtime/Memory Reporting And Late-Correction Scenarios - 2026-10-30

- **Runtime/memory reporting for duplicate detection** (audit gap closed): `evaluate_duplicate_detection` now measures `blocking_time_s`, `scoring_time_s`, and `peak_memory_bytes` (tracemalloc). Added computed properties `candidates_per_1000_records` and `false_matches_per_1000_records` (zero-safe). 8 new tests (`DuplicateRuntimeMemoryTests`). Commit `14dc1cd`.
- **Late-correction scenario family** (audit gap closed): added `late_correction` and `policy_transition` to `rare_legitimate_patterns()`. `late_correction` injects an erroneous event and a `correction_of_event_id`-linked correction; `policy_transition` re-stamps a promotion to the `legacy-pre-2023` epoch. Both produce rare-legitimate records not flagged by invariant rules. 10 new tests (`LateCorrectionAndPolicyTransitionScenarioTests`). Commit `0bfa585`.
- All 210 tests pass after both changes.
- Remaining blockers: blinded expert review (reviewers unnamed); protocol freeze (pending dated supervisor approval); holdout (locked until freeze).
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

## Latent-Person-First Duplicates And Hard Nonduplicates - 2026-10-30

- Root gap from audit: duplicate records were derived from an existing source record in the dataset. Partition containment was enforced by a pointer-chain check after the fact, not by construction.
- Fix: `LatentPerson` dataclass represents a fictional base entity generated outside all partitions. Every cluster member (source + variants) is derived from the latent person and carries `latent_person_id`. Partition assignment for duplicate records is resolved before derivation, so cross-partition leakage is structurally impossible.
- `HardNonduplicateKind` enum adds four explicit mechanisms: `similar_name`, `shared_birthday`, `relative`, `near_identical_id`. One record per kind is injected into every generated dataset (when enough clean records are available). Hard nonduplicates are CLEAN-labelled with no `duplicate_of_employee_id` pointer and must not appear in `_true_duplicate_pairs`.
- New fields on `WorkforceHistoryRecord`: `latent_person_id` (cluster provenance), `hard_nonduplicate_kind` (confusability mechanism). Schema version bumped to `tdk-synthetic-v2`.
- 11 new tests added: `LatentPersonFirstDuplicateTests` (6) and `HardNonduplicateTests` (5). All 192 tests pass. Commit `c98f416`.
- Remaining duplicate gaps: dedicated late-correction scenario family (bitemporal contract tested, scenario type not frozen); runtime/memory reporting for duplicate blocking/scoring.
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

## Clean-Revision Artifact Generation And Audit - 2026-10-30

- Root cause of prior audit failure: `_provenance()` hashed on-disk file bytes (CRLF on Windows), while the auditor re-reads source via `git show` (LF). Mismatch was deterministic on Windows with `autocrlf=true`.
- Fix: `_git_object_bytes()` helper reads content via `git show HEAD:<path>` so both sides hash the same byte stream. No test fixtures, seeds, or scientific values were changed. Commit `bbc59f8`.
- New certified independent development artifact `62f482ce6ff477b9` generated from clean committed worktree at `bbc59f8`. Artifact audit status: **verified**. `holdout_accessed: false`.
- Artifact contains: 12 scenarios, 864 test histories, 108 labelled anomalies, 72 broadly labelled rare-legitimate histories, 648 metric rows, 46,656 prediction rows, 57,485 administrative events, 24 policy epochs, 4,320 truth sidecar rows.
- Primary residual endpoint (fixed_review_budget, `rule_negative_isolation_forest`): recall delta mean `+0.037`, 95% CI `[-0.037, 0.111]`, sign-flip p=0.516. No evidence for policy-aware advantage at this sample size.
- AP delta mean `+0.048` (secondary; zero-positive scenario handling eligibility pending explicit count in future artifact schema).
- Deterministic policy rules: 62 TP, 0 FP, 46 FN of 108 anomalies. Rare-legitimate flagged: 0/72.
- Rules-plus-IF (policy_matched, rules_first_budget_floor): 82 TP, 20 FP, 26 FN; rare-legitimate flagged 2/72.
- All 181 tests pass locally. Focused research suite (52 tests) confirmed post-fix.
- Remaining blockers unchanged: latent-person-first duplicate generation, hard nonduplicate mechanisms, dedicated correction scenarios, duplicate runtime/memory, blinded expert review, environment freeze, dated protocol-freeze approval.
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

## Data And Test Correctness Milestone - 2026-10-29

- The external audit allegations were independently reproduced at baseline revision `32633d2`; exact counts, corrections, and remaining limitations are recorded in `TDK_DATA_TEST_CORRECTNESS_AUDIT_2026-10-29.md`.
- The primary residual pipeline now uses invariant-only filtering, identical residual populations, and equal additional ML review capacity. Invariant rules, configurable policy rules, and the complete workflow remain separately reported.
- Zero-positive scenarios remain in denominator tables while recall and AP are explicitly undefined and excluded from paired inference only under recorded eligibility flags.
- Independent scenarios now realize their declared interventions: omissions remove records, approval bypass is explicit and unconfounded by service or track, event visibility respects recorded time, and ordinary legitimate histories contain varied administrative activity.
- Historical replay now carries policy versions and valid/recorded times, jurisdiction, approval evidence, recognized service, and separate correction/retry provenance. Applicable historical policy replaces latest-policy replay for research features.
- Duplicate entities are partition-contained; thresholds are selected on validation and evaluated on test; missing values provide no similarity evidence; blocking and scoring denominators are reported separately.
- The artifact auditor now rejects empty source provenance and verifies primary population identity, truth alignment, equal budgets, top-score selection, bitemporal consistency, and provenance links.
- A development-only 12-scenario smoke matrix completed and passed the family-wide feature-variation guard. Its artifact is intentionally uncertified because it was generated from an uncommitted worktree; it is not evidence for the paper.
- Remaining blockers include latent-person-first duplicate generation, explicit hard-nonduplicate mechanisms, dedicated correction scenarios, duplicate runtime/memory evidence, blinded expert review, clean-revision development and validation artifacts, exact environment freeze, and dated protocol-freeze approval.
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

## Supervisor Methodology Decisions - 2026-10-29

- The supervisor decisions relayed by Muhammad Ibrahim Shoeb approve the methodology for implementation; they do not freeze the protocol or unlock the holdout.
- The primary experiment remains raw-versus-policy-aware residual Isolation Forest, with deterministic filtering restricted to invariant contradictions. The complete rules-plus-ML queue is secondary.
- Recall at identical fixed additional review capacity is the primary endpoint. Precision, total false alerts, and rare-legitimate false-alert rates accompany it; Average Precision is secondary with predeclared undefined handling for zero-positive scenarios.
- Both pipelines preserve the same invariant findings and receive the same additional ML budget over the same remaining records.
- A bitemporal contract is approved for implementation, including policy versions, effective and recorded times, recognized service, and correction provenance.
- The realism review uses two independent reviewers with complementary HR-policy and information-systems expertise, blinded to labels and model scores, with preserved initial judgments, agreement reporting, evidence-based adjudication, and retained ambiguity.
- The final holdout matrix must be independently specified across policy transitions, lawful exceptions, administrative errors, populations, and repeated seeds, with causal truth outside model inputs.
- Next unblocked milestone: independently audit the clean-revision implementation, generate new versioned development and validation artifacts, and close the remaining generator and duplicate-evaluation gaps. The holdout remains locked until a separately approved protocol freeze.
- Documentation synchronization passed an independent read-only audit after stale AP-primary, pending-decision, reviewer-sample, and residual-population wording was corrected. All 168 tests and strict citation verification passed; no experiment or holdout-like path was accessed.

## Supervisor Paper Package - 2026-10-29

- Prepared the English supervisor-review manuscript under the final title **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**. The rendered paper contains 31 pages of main text and 35 pages in total; the title page, abstract, references, and appendices remain outside the main-text count.
- The paper reports the constant-feature failure as a design failure rather than a null, tie, or equivalence result. It preserves `0.3616` versus `0.3621` only as reproducible arithmetic and limits the historical-policy artifact claim to `39/72` constructed rare-legitimate histories.
- Added 11 reproducible figures, formal progression and evaluation equations, denominator tables, artifact traceability, a one-page human decision sheet, and an English-only TDK-specific document build. The original Hungarian source templates remain unchanged outside the repository.
- Microsoft Word rendered the authoritative DOCX and PDF. Every page was rasterized and visually inspected. The prescribed LibreOffice-based helper could not run because LibreOffice is not installed; this tooling limitation is recorded rather than hidden.
- Local verification passed all 168 tests, all three canonical experiment artifact audits, strict citation verification, and both canonical literature-artifact checks. GitHub push and pull-request CI runs also passed for revision `94868c2`. Every artifact audit reported `holdout_accessed: false`.
- Evidence inventory now reports 35 candidates and 444 files. The five canonical artifacts are complete; six legacy, interrupted, or unmanifested candidates remain preserved and are not cited as current authority.
- PR #1 remains draft, mergeable, and unmerged. Issue #10 remains the implementation and freeze tracker. No issue or branch has been deleted, the approved methodology has not yet been frozen, and no holdout command has been executed.
- Kiro CLI is not installed in the environment, so no Kiro credits were used. A fresh independent read-only agent performed the required adversarial manuscript and evidence review instead; its duplicate-denominator, zero-positive-scenario, citation-scope, and package-provenance findings were corrected before delivery.

## Research and Citation Governance - 2026-10-29

- Added the sixth workflow role, Research & Citation Specialist, and the repository `researcher` skill.
- Added free direct API support for Crossref alongside OpenAlex, Semantic Scholar, and arXiv. OpenAlex, arXiv, and Crossref passed a live smoke query. Semantic Scholar remains correctly configured but anonymous live access returned HTTP 429; a free key is still an optional setup item.
- Audited all 18 bibliography entries, corrected identified metadata, preserved the existing 16-paper full-text artifact, and recorded two unresolved full-text evidence gaps without deleting or weakening prior history.
- Added a centralized citation provenance registry and claim-to-source evidence ledger. CI now validates deduplication, DOI consistency, source provenance, evidence type, claim status, and full-text review state.
- The Independent Auditor must verify citations and claim scope before recommending research changes for human review. This process change does not approve a protocol decision, alter an endpoint, or access the holdout.

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Current boundary: the authorized audit, corrections, independent scenario prototype, adversarial development run, independent hostile review, and targeted literature check are complete. The hostile review found that the current residual comparison does not isolate policy context because its three policy-specific features are constant after rule filtering. The protocol remains draft, the final holdout remains undefined and locked, and the research PR remains unmerged.

Completed evidence is summarized in `archive/research-audits/TDK_METHODOLOGY_REVIEW_2026-10-16.md`, `TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`, `TDK_INDEPENDENT_SCENARIO_SPEC.md`, and `TDK_INDEPENDENT_REVIEW_2026-10-17.md`. The six human methodology decisions are recorded in `TDK_SUPERVISOR_DECISIONS_2026-10-29.md`; implementation and protocol freeze remain pending. `README.md` and `RESEARCH_HANDOVER.md` provide the current documentation entry point and full handover.

## Verified Unblocked Work - 2026-10-18

- Independent review re-derived the stored residual AP values, paired interval, and `39/72` false-alert count without changing code or protocol.
- Literature artifacts `20261017T215024Z_f79f81f2c2b1` and `20261017T215119Z_4b354b03c1af` passed checksum, credential, paid-service, and holdout checks. Semantic Scholar was rate-limited; OpenAlex and arXiv completed.
- A blinded expert-review packet and traceable methods draft are prepared but not approved or distributed.
- Deprecated `datetime.utcnow()` calls were replaced by a tested naive-UTC compatibility helper; the database timestamp contract is unchanged.
- Local verification passed all 125 tests. Commit `ad7c543` passed push CI, pull-request CI, and GitGuardian checks before this roadmap evidence update.
- The holdout was not generated, inspected, scored, or unlocked.

## Unblocked Defensibility Work - 2026-10-18

- Supervisor-facing documents now state that the residual experiment was structurally unable to test policy-aware value; they no longer present the AP values as a tie or merely inconclusive evidence.
- The development artifact auditor now independently recomputes AP from stored scores, operational rates, paired scenario differences, bootstrap intervals, sign-flip tests, and Holm adjustments. The unchanged artifact `e342bd4acf39b06b` passed the strengthened audit across 636 metric rows and 15 paired-comparison rows.
- Future independent development artifacts write normalized `record_truth.csv`, `administrative_events.csv`, and `policy_epochs.csv` sidecars. Nominal and realized mechanisms remain separate; complete event fields and observed-versus-omitted causal status are preserved; the auditor enforces causal joins; and truth-only fields are prohibited from prediction rows.
- Three residual-design alternatives are documented as proposals only. No design is approved or implemented, and existing write-once artifacts remain unchanged.
- A fresh hostile code review found incomplete event provenance and metric-key completeness checks. Both blockers were corrected with adversarial tests rather than waived.
- Local verification passed all 134 tests. Commit `414a5b7` passed both GitHub Python test jobs and GitGuardian security checks.
- Documentation was classified into current authority, pending decisions, and preserved archives. Stale claims about residual AP and the `39/72` denominator were corrected without rewriting dated audit history or changing the draft protocol.
- A repository-grounded research handover and reusable beginner-to-defense ChatGPT tutor prompt were added. Historical plans, audits, rendered guides, and project-lab deliverables were moved to `docs/archive/`; no research evidence was deleted.
- Post-cleanup verification passed all 134 tests, Python compilation checks, local Markdown-link resolution, `git diff --check`, and the independent artifact audit. Artifact `e342bd4acf39b06b` remained verified with `holdout_accessed: false`.

## Repository Preservation Maintenance - 2026-10-29

- Issue #12 and draft PR #13 isolate non-destructive repository maintenance from research PR #1. PR #1 remains draft and unmerged.
- Independent-development artifacts are now written to a process-owned staging directory and atomically published only after successful completion. Failed runs remove only their own staging directory, deterministic retries remain possible, and completed artifacts cannot be overwritten.
- A read-only evidence inventory verified 34 local artifact candidates containing 434 files and 642,648,992 bytes. Twenty-eight candidates passed manifest or release-sidecar checks; all five artifacts cited by the current research documents are present and complete. Six legacy, interrupted, or unmanifested candidates remain preserved for human review.
- The inventory treats holdout-like paths as opaque and reports private research notes only as aggregate counts. Seven private-note files were counted; their names and contents were not emitted. No holdout-like entry was encountered or inspected.
- Documentation now distinguishes live authority, dated evidence, derivative summaries, pending decisions, and archives. The archive manifest records SHA-256 checksums for all preserved project-lab, planning, and early research files.
- An issue-disposition review recommends evidence-based closure of implementation issues #2, #3, #4, #5, #7, and #9; rescoping #6 and #8; and keeping #10 and #11 open. No issue state was changed during the review.
- The 173 tracked `tmp_*` UI-review files are inventoried separately. No temporary capture, research artifact, private file, or historical document was deleted or relocated.
- An independent hostile maintenance review found an opaque-entry classification flaw, duplicate release-sidecar ambiguity, an incomplete archive-manifest claim, and one stale note. All four findings were corrected and covered by adversarial tests before commit.
- Verification passed all 150 tests, focused artifact-publication and evidence-inventory tests, Python compilation, relative Markdown-link resolution, archive checksum verification, and `git diff --check`.
- The draft protocol, hypotheses, endpoints, scenario definitions, scientific interpretations, and holdout boundary were not changed.

## 1. Supervisor Methodology Decision

- **Scientific objective:** Implement the approved invariant-negative residual comparison, recall-at-fixed-capacity endpoint, scenario eligibility, and inference plan.
- **Why it matters:** The original generator is circular and its residual count is too small; independent development evidence is inconclusive.
- **Evidence motivating it:** Corrected v2.4 artifacts, independent artifact `e342bd4acf39b06b`, and the critical feature-validity finding in the independent review.
- **Files/components involved:** `TDK_PROTOCOL_CHANGE_PROPOSALS.md`, `TDK_SUPERVISOR_REVIEW_PACKAGE.md`, the experiment protocol, and Issue #10.
- **Acceptance criteria:** A dated supervisor decision records the endpoint, independent unit, capacity rule, and allowed scenario families.
- **Required validation:** Documentation cross-check against artifacts and literature.
- **Dependencies and blockers:** Requires implementation, independent verification, and a separate dated freeze approval.
- **Status:** Approved for implementation; freeze pending.
- **Outcome:** Residual ML remains primary with invariant-only filtering, equal ML capacity, and recall at fixed capacity as the primary endpoint.

## 2. Blinded Domain-Realism Review

- **Scientific objective:** Assess whether fictional policy and administrative histories are plausible without model scores or labels.
- **Why it matters:** Synthetic correctness does not establish organizational realism.
- **Evidence motivating it:** Independent scenarios reveal policy-version false alerts absent from the original generator.
- **Files/components involved:** `TDK_EXPERT_REVIEW_PACKET.md`, independent scenario cards, truth taxonomy, and a blinded review form.
- **Acceptance criteria:** A human-approved sample size, two complementary reviewers, realism ratings, classifications, reasons, a predeclared agreement statistic, documented adjudication, and preserved ambiguity.
- **Required validation:** Reviewer identities and protocol recorded; no case changed to improve metrics.
- **Dependencies and blockers:** Requires two named qualified reviewers before execution.
- **Status:** Method approved; reviewer nomination and execution pending.
- **Outcome:** The result-blind questionnaire is drafted. Blinding, preserved initial judgments, agreement, evidence-based adjudication, and retained ambiguity are approved.

## 3. Policy-Version And Administrative-Evidence Contract

- **Scientific objective:** Represent policy epochs, jurisdiction, recognized service, effective versus recorded dates, and corrections.
- **Why it matters:** A single-current-policy model falsely flags lawful grandfathered and recognized-service histories.
- **Evidence motivating it:** Independent rules produced 39 rare-legitimate false alerts among 72 rare histories. Source regeneration identified all 39 realized transition histories as flagged, but this mechanism label is not preserved per record in the stored artifact.
- **Files/components involved:** research record contract, adapter, policy history, features, golden histories, and parity tests.
- **Acceptance criteria:** Approved fields, migration design, backward compatibility, multi-policy golden histories, and no application regression.
- **Required validation:** SQL/research parity, historical-policy tests, transition-boundary tests, and full CI.
- **Dependencies and blockers:** Requires implementation, migration design, and golden-history validation.
- **Status:** Approved for implementation.
- **Outcome:** The approved contract includes policy versions, effective and recorded times, recognized service, and correction provenance. Application behavior remains unchanged until tested implementation is complete.

## 4. Protocol Freeze And Reproducible Environment Lock

- **Scientific objective:** Freeze hypotheses, feature sets, scenario matrix, analysis, dependencies, and artifact storage before holdout generation.
- **Why it matters:** Final evidence must not be influenced by inspected outcomes or drifting dependencies.
- **Evidence motivating it:** Dependencies are recorded but broad ranges do not guarantee exact replay.
- **Files/components involved:** experiment protocol, requirements lock, source hashes, release archive, CI, and Issue #10.
- **Acceptance criteria:** Supervisor-signed protocol, exact dependency lock, immutable development archive, clean CI, and completed holdout checklist.
- **Required validation:** Fresh-environment replay and independent artifact audit.
- **Dependencies and blockers:** Requires implementation and verification of Tasks 1 through 3 plus a dated freeze approval.
- **Status:** Not frozen.
- **Outcome:** Pending.

## 5. One-Time Locked Holdout Evaluation

- **Scientific objective:** Generate and evaluate the independently specified holdout exactly once after freeze.
- **Why it matters:** Only untouched evidence can support the final confirmatory claim.
- **Evidence motivating it:** All current outputs are development or validation diagnostics.
- **Files/components involved:** frozen generator, analysis script, artifact archive, paper results, and supervisor record.
- **Acceptance criteria:** One clean run, complete provenance and denominators, preserved negative results, independent replication, and no post-result tuning.
- **Required validation:** Manifest audit, statistical reproduction, CI/security checks, and supervisor sign-off.
- **Dependencies and blockers:** Explicit supervisor approval and completed freeze checklist. Holdout specification and seeds remain undefined until then.
- **Status:** Blocked. Do not start.
- **Outcome:** Pending.
