# TDK Autonomous Research Roadmap

## Certified Artifact With New Scenario Families - 2026-10-30

- Adding `late_correction` and `policy_transition` to `rare_legitimate_patterns()` changed the 12-scenario development matrix composition (patterns now assigned `index % 5`: patterns 0,1 appear 3x; patterns 2,3,4 appear 2x). This genuinely exercises the new mechanisms in the development run.
- **Two bugs found and fixed while generating the artifact** (the harness exposed them before they could corrupt evidence):
  - `assess_promotion_history` evaluated both a correction-superseded promotion and its correction as independent events, and the re-dated erroneous event fell outside its declared policy epoch (crash: "declared policy reform-2023 is not applicable"). Fix: exclude any promotion whose `source_id` appears as a `correction_of_source_id` on a visible event (bitemporal "preserve later-recorded corrections" rule); stamp the erroneous event with the policy applicable at its earlier date. Commit `3e9edd2`.
  - The erroneous event used `approval_status="pending_correction"`, outside the auditor's accepted domain `{approved, bypassed}`. Fix: use `approved` (the mis-filing was approved at the time; the error was the date). Commit `0f1f32c`.
- **Certified artifact `db1a15646d9e76ba`** generated from clean commit `0f1f32c`. Audit status: **verified**. `holdout_accessed: false`. 12 scenarios, 864 test histories, 108 anomalies, 72 rare-legitimate, 57,562 administrative events, 24 policy epochs, 4,320 truth rows.
- Primary residual endpoint (`fixed_review_budget`, `rule_negative_isolation_forest`): recall delta mean `+0.009`, 95% CI `[-0.046, +0.083]`, sign-flip p=1.0. **No evidence of policy-aware advantage** — consistent with prior artifact `62f482ce6ff477b9`. AP delta mean `+0.021` (secondary).
- New scientific signal: deterministic current-policy rules now flag **8/72 rare-legitimate histories** (prior artifact: 0/72). The new late-correction and policy-transition scenarios surface exactly the lawful-but-unusual false alerts that motivate the bitemporal contract. This is a preserved finding, not a tuned result.
- All 212 tests pass (210 + 2 new supersession regression tests).
- The final holdout was not generated, inspected, scored, or unlocked. PR #1 remains draft and unmerged.

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
