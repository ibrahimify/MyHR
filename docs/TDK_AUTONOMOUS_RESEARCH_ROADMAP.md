# TDK Autonomous Research Roadmap

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Current boundary: the authorized audit, corrections, independent scenario prototype, and adversarial development run are complete. The protocol remains draft, the final holdout remains undefined and locked, and the research PR remains unmerged.

Completed evidence is summarized in `TDK_METHODOLOGY_REVIEW_2026-10-16.md`, `TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`, and `TDK_INDEPENDENT_SCENARIO_SPEC.md`.

## 1. Supervisor Methodology Decision

- **Scientific objective:** Approve or revise the primary hypothesis, rule-negative AP endpoint, scenario eligibility, and inference plan.
- **Why it matters:** The original generator is circular and its residual count is too small; independent development evidence is inconclusive.
- **Evidence motivating it:** Corrected v2.4 artifacts and independent artifact `e342bd4acf39b06b`.
- **Files/components involved:** `TDK_PROTOCOL_CHANGE_PROPOSALS.md`, `TDK_SUPERVISOR_REVIEW_PACKAGE.md`, the experiment protocol, and Issue #10.
- **Acceptance criteria:** A dated supervisor decision records the endpoint, independent unit, capacity rule, and allowed scenario families.
- **Required validation:** Documentation cross-check against artifacts and literature.
- **Dependencies and blockers:** Requires supervisor approval.
- **Status:** Blocked on supervisor review.
- **Outcome:** Pending.

## 2. Blinded Domain-Realism Review

- **Scientific objective:** Assess whether fictional policy and administrative histories are plausible without model scores or labels.
- **Why it matters:** Synthetic correctness does not establish organizational realism.
- **Evidence motivating it:** Independent scenarios reveal policy-version false alerts absent from the original generator.
- **Files/components involved:** independent scenario cards, truth taxonomy, and a blinded review form.
- **Acceptance criteria:** 40 to 60 histories, two reviewers, realism ratings, classifications, reasons, agreement statistic, and documented adjudication.
- **Required validation:** Reviewer identities and protocol recorded; no case changed to improve metrics.
- **Dependencies and blockers:** Requires supervisor-approved assumptions and external reviewers.
- **Status:** Blocked on supervisor and reviewer availability.
- **Outcome:** Pending.

## 3. Policy-Version And Administrative-Evidence Contract

- **Scientific objective:** Represent policy epochs, jurisdiction, recognized service, effective versus recorded dates, and corrections.
- **Why it matters:** A single-current-policy model falsely flags lawful grandfathered and recognized-service histories.
- **Evidence motivating it:** Independent rules produced 39 rare-legitimate false alerts among 72 rare histories.
- **Files/components involved:** research record contract, adapter, policy history, features, golden histories, and parity tests.
- **Acceptance criteria:** Approved fields, migration design, backward compatibility, multi-policy golden histories, and no application regression.
- **Required validation:** SQL/research parity, historical-policy tests, transition-boundary tests, and full CI.
- **Dependencies and blockers:** Requires Tasks 1 and 2 to avoid encoding unreviewed assumptions.
- **Status:** Blocked on domain approval.
- **Outcome:** Pending.

## 4. Protocol Freeze And Reproducible Environment Lock

- **Scientific objective:** Freeze hypotheses, feature sets, scenario matrix, analysis, dependencies, and artifact storage before holdout generation.
- **Why it matters:** Final evidence must not be influenced by inspected outcomes or drifting dependencies.
- **Evidence motivating it:** Dependencies are recorded but broad ranges do not guarantee exact replay.
- **Files/components involved:** experiment protocol, requirements lock, source hashes, release archive, CI, and Issue #10.
- **Acceptance criteria:** Supervisor-signed protocol, exact dependency lock, immutable development archive, clean CI, and completed holdout checklist.
- **Required validation:** Fresh-environment replay and independent artifact audit.
- **Dependencies and blockers:** Requires Tasks 1 through 3.
- **Status:** Blocked on protocol approval.
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
