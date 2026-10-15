# TDK Autonomous Research Roadmap

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Current boundary: development and validation work only. The final holdout is locked, the protocol is draft, and the research PR must remain unmerged.

This file contains exactly five prioritized actionable tasks. Completed work is summarized in each task's outcome and then replaced only when another scientifically justified task is available.

## 1. Independent Scientific And Methodological Review

- **Scientific objective:** Attempt to invalidate the current development and validation conclusions, explain the rules-only versus hybrid result, and identify one defensible primary hypothesis and endpoint for supervisor approval.
- **Why it matters:** Current evidence comes from one synthetic generator family. Rules alone have mean scenario F1 `0.880`, above the policy-aware cascade's `0.840`, so ranking quality cannot be presented as universal operational superiority.
- **Evidence motivating it:** `TDK_RESEARCH_AUDIT_2026-10-15.md`, the verified v2 artifacts, the 12-paper corpus, and the development/validation report.
- **Files/components involved:** `docs/TDK_RESEARCH_AUDIT_2026-10-15.md`, `docs/TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`, `docs/TDK_LITERATURE_REVIEW.md`, `research_outputs/protocol_v2_verified/`, protocol evaluation and analysis code.
- **Acceptance criteria:** Exact pooled and scenario-level denominators are independently reproduced; fairness, leakage, circularity, thresholding, and multiplicity risks are documented; one primary hypothesis and endpoint are proposed without changing the draft protocol.
- **Required validation:** Independent methodology, ML/statistics, scenario-design, and replication reviews; checksum verification; recomputation from saved record predictions and scenario metrics.
- **Dependencies and blockers:** Supervisor approval is required to adopt a primary endpoint or alter the protocol. No holdout access is permitted.
- **Status:** In progress.
- **Outcome:** Pending.

## 2. Strengthen The Proposed Experimental Design

- **Scientific objective:** Convert confirmed audit findings into a versioned protocol-change proposal covering endpoints, multiplicity, equal-budget comparisons, rule-conditional value, uncertainty, recall safeguards, and operational utility.
- **Why it matters:** A statistically significant ranking difference may be operationally inferior to deterministic rules when it adds unnecessary reviews.
- **Evidence motivating it:** The policy-aware cascade finds 19 additional validation anomalies over rules alone but adds 55 false alerts at the fixed 10% budget; cost sensitivity changes the preferred method.
- **Files/components involved:** protocol analysis script, `protocol_evaluation.py`, protocol tests, and a separate protocol-change proposal document.
- **Acceptance criteria:** Every proposal names its estimand, independent unit, denominator, decision rule, multiplicity family, and rationale; technical defects have regression tests; scientific changes remain explicitly pending supervisor approval.
- **Required validation:** Unit tests for statistical procedures and alert-budget logic; independent recomputation of any revised development-only analysis; no result-based feature tuning.
- **Dependencies and blockers:** Depends on Task 1. Protocol adoption is blocked on supervisor review.
- **Status:** Planned.
- **Outcome:** Pending.

## 3. Design An Independent Development-Only Scenario Generator

- **Scientific objective:** Implement a separately specified generator for development-only stress tests with different policy transitions, populations, event processes, anomaly mechanisms, and rare-legitimate histories.
- **Why it matters:** Different random seeds from the same generator do not establish external validity or eliminate conceptual circularity.
- **Evidence motivating it:** Current validation scenarios use disjoint seeds but share generation code and domain assumptions with development scenarios.
- **Files/components involved:** a new isolated research generator module, data-contract documentation, generator property tests, and development-only artifact output.
- **Acceptance criteria:** No imports from detector, feature, or current scenario-generation modules; no detector formula is copied into anomaly construction; labels arise from independently specified event mechanisms; policies and distributions differ materially from v2; all outputs are explicitly development-only.
- **Required validation:** Dependency-boundary tests, reproducibility tests, property tests, label audit, adversarial edge cases, and review by the independent scenario-design role.
- **Dependencies and blockers:** Depends on Task 1 design findings. Expert review may improve realism but is not required to build a development prototype. Holdout generation remains prohibited.
- **Status:** Planned.
- **Outcome:** Pending.

## 4. Run Adversarial Development-Only Validation

- **Scientific objective:** Test the frozen current methods against independent development-only scenarios, negative controls, ablations, and reproducibility checks without optimizing features from the outcomes.
- **Why it matters:** The strongest current result may depend on generator-specific shortcuts or favorable policy alignment.
- **Evidence motivating it:** Correct-policy features outperform shuffled and wrong-policy controls in v2, but only inside the original generator family.
- **Files/components involved:** independent scenario artifacts, existing frozen feature representations, analysis code, tests, and an adversarial validation report.
- **Acceptance criteria:** All predeclared methods run on all scenarios; failures and unfavorable results remain; rule-only and hybrid comparisons use explicit alert counts and cost assumptions; robustness claims are limited to observed conditions.
- **Required validation:** Clean rerun, artifact checksum verification, paired scenario-level uncertainty, corrected inferential reporting, and independent replication.
- **Dependencies and blockers:** Depends on Tasks 2 and 3. It must not trigger holdout creation or protocol optimization.
- **Status:** Planned.
- **Outcome:** Pending.

## 5. Prepare The Supervisor-Ready Research Package

- **Scientific objective:** Present the research question, literature basis, verified evidence, negative findings, proposed protocol decisions, limitations, and reproducible commands in a concise review package.
- **Why it matters:** Scientific governance decisions must be made from transparent evidence before protocol freeze or holdout access.
- **Evidence motivating it:** Issue #10 remains open specifically for supervisor review and protocol freeze.
- **Files/components involved:** experiment protocol, audit, literature review, verified report, proposed changes, roadmap, references, artifact manifests, and GitHub Issue #10.
- **Acceptance criteria:** Established findings, development observations, proposals, and unresolved questions are visibly separated; exact denominators and uncertainty are included; supervisor decisions are explicit; no final-validity language is used.
- **Required validation:** Documentation cross-check against source and artifacts, citation verification, full test suite, CI and security checks, and draft PR review.
- **Dependencies and blockers:** Depends on Tasks 1 through 4. Protocol freeze and holdout access require supervisor approval.
- **Status:** Planned.
- **Outcome:** Pending.
