# Research Issue Disposition

Date: 2026-10-29  
Branch reviewed: `maintenance/research-repository-hygiene`  
Research PR: [#1](https://github.com/ibrahimify/MyHR/pull/1), draft and unmerged

## Purpose And Decision Boundary

This document reviews GitHub issues [#2](https://github.com/ibrahimify/MyHR/issues/2) through [#11](https://github.com/ibrahimify/MyHR/issues/11) against their exact `Done when` criteria and the evidence currently present in the repository. It recommends issue disposition only; it does not close or edit any issue.

An implementation can satisfy its engineering acceptance criteria without validating the TDK hypothesis. Closing a foundational implementation issue must therefore not be interpreted as protocol approval, external validity, holdout readiness, or evidence that policy-aware machine learning outperforms another method. Issue #10 remains open, the protocol remains draft, and the holdout remains locked.

## Summary

| Issue | Recommendation | Reason |
| --- | --- | --- |
| #2 Schema and taxonomy | **Close with evidence** | The documented contract, typed structures, labels, and tests satisfy every stated criterion. |
| #3 Synthetic generator | **Close with evidence** | Determinism, metadata, splits, labels, and edge cases are implemented and tested; final scientific scenario validity remains under #10. |
| #4 Deterministic checks | **Close with evidence** | Explainable findings and clean/error/rare-case tests exist. |
| #5 Feature extraction | **Close with evidence** | Both representations and their intended rare-case distinction are implemented and tested; the later residual experiment exposed a separate validity failure. |
| #6 Baselines and Isolation Forest | **Rescope** | The software and metrics exist, but the central scientific comparison is not estimable from the inspected residual design. |
| #7 Duplicate detection | **Close with evidence** | All three matching methods, metrics, and field-level explanations exist and are tested. |
| #8 Reports and figures | **Rescope** | Reproducible tabular artifacts exist, but final paper-ready figures and approved final results do not. |
| #9 Thesis/TDK scope audit | **Close with evidence** | The required pass/fail checklist and residual-risk lists exist. |
| #10 Non-circular validation | **Keep open** | Supervisor review, protocol freeze, and a scientifically adequate residual design remain unresolved; holdout work is forbidden. |
| #11 Literature workflow | **Keep open** | Tests and two live sources pass, but the required live Semantic Scholar smoke test remains incomplete. |

## Issue Reviews

### #2 Define synthetic workforce-history schema and anomaly taxonomy

**Recommendation: Close with evidence.**

**Acceptance evidence**

- The schema and anomaly definitions are documented in [TDK_SYNTHETIC_DATA_CONTRACT.md](TDK_SYNTHETIC_DATA_CONTRACT.md), including record fields, employment tracks, anomaly labels, expected signals, and scientific guardrails.
- Typed structures, `ExperimentConfig`, `AnomalyType`, `WorkforceHistoryRecord`, metadata, and dataset containers are implemented in `src/services/anomaly_detection/synthetic_data.py` by commit [`02897f9`](https://github.com/ibrahimify/MyHR/commit/02897f9).
- `tests/test_anomaly_detection_skeleton.py` verifies the taxonomy, non-anomalous rare-legitimate labels, anomalous injected-error labels, stable run IDs, and deterministic partitions.
- The document explicitly makes no experimental performance claim.

**Residual limitations**

- The contract describes synthetic development data, not real workforce distributions or external validity.
- Later protocol-v2 and independent scenario structures extend the original contract; they do not invalidate completion of this foundational issue.

### #3 Implement reproducible synthetic dataset generator

**Recommendation: Close with evidence.**

**Acceptance evidence**

- `generate_synthetic_dataset()` and deterministic configuration-derived run IDs were introduced in commit [`22c16d9`](https://github.com/ibrahimify/MyHR/commit/22c16d9).
- `tests/test_anomaly_detection_skeleton.py` verifies repeatability for a fixed seed, split and label metadata, duplicate source links, proportional label distribution, policy-valid clean/rare histories, track restrictions, and invalid configuration handling.
- `src/services/anomaly_detection/scenario_generation.py` and `tests/test_tdk_protocol_v2.py` add separate dataset/split/model seeds, development/validation separation, scenario-dimension coverage, and a locked holdout boundary.
- Generated CSV/JSON metadata and tabular outputs are consumed by the experiment runners documented in [TDK_RESEARCH_VERIFICATION.md](TDK_RESEARCH_VERIFICATION.md).

**Residual limitations**

- The original generator is retained as development history and has documented generator-detector coupling. It must not supply final evidence.
- Scenario realism and a future holdout design require human approval under #10. Closing #3 records engineering completion only.

### #4 Implement deterministic administrative validation checks

**Recommendation: Close with evidence.**

**Acceptance evidence**

- Commit [`2d9d80e`](https://github.com/ibrahimify/MyHR/commit/2d9d80e) added `ValidationFinding`, record-level checks, dataset checks, finding codes, severity, explanations, and relevant event IDs in `src/services/anomaly_detection/deterministic_checks.py`.
- `tests/test_anomaly_detection_skeleton.py` covers explainable inconsistent dates, short promotion and increment intervals, clean histories, and side-effect boundaries.
- `tests/test_tdk_protocol_v2.py` covers explicit policy-rule separation between legitimate and unexplained short promotions and earlier historical promotion violations.

**Residual limitations**

- The independent scenarios exposed false alerts when current-policy logic was applied across historical policy transitions: the preserved result is `39/72` rare-legitimate alerts. Historical policy modelling remains a pending human decision under #10.
- These checks are a baseline and data-quality safeguard, not an automatic personnel-decision system.

### #5 Implement raw and policy-aware feature extraction

**Recommendation: Close with evidence.**

**Acceptance evidence**

- Commit [`b4c45d2`](https://github.com/ibrahimify/MyHR/commit/b4c45d2) added raw and policy-aware transformations for the same `WorkforceHistoryRecord` inputs in `src/services/anomaly_detection/features.py`.
- `tests/test_anomaly_detection_skeleton.py` verifies raw counts and intervals, policy explanations for rare-legitimate promotions, policy-residual feature selection, and rejection of unknown feature sets.
- [TDK_SYNTHETIC_DATA_CONTRACT.md](TDK_SYNTHETIC_DATA_CONTRACT.md) documents both representations and their intended comparison.

**Residual limitations**

- The independent residual experiment found that all three policy-specific residual features became constant zero after deterministic filtering. The recorded AP difference therefore does not test incremental policy context.
- Feature redesign is a protocol decision and remains pending under #10. Closing #5 recognizes the implemented interface, not scientific adequacy of the current residual representation.

### #6 Run statistical baselines and Isolation Forest comparison

**Recommendation: Rescope to "Maintain development-only baseline implementations; final comparison governed by #10."**

**Criteria already satisfied**

- Commits [`c5ce693`](https://github.com/ibrahimify/MyHR/commit/c5ce693) and [`f3a6148`](https://github.com/ibrahimify/MyHR/commit/f3a6148) added z-score, IQR, raw Isolation Forest, policy-aware Isolation Forest, research dependencies, smoke verification, and metric reporting.
- Experiment outputs include precision, recall, F1, false-positive rate, workload-related counts/rates, runtime, method, seed, configuration, timestamp, and provenance. Later protocol artifacts add explicit denominators, average precision, equal-budget comparisons, paired uncertainty, controls, and write-once manifests.
- Relevant behavior is covered by `tests/test_anomaly_detection_skeleton.py`, `tests/test_tdk_protocol_v2.py`, and `tests/test_protocol_artifact_audit.py`.

**Why the original goal is not complete**

- [TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md](TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md) records that the original generator is coupled to the detector and that the independent residual design has no varying policy-specific signal after filtering.
- Six of twelve independent scenarios have no residual positives. The current residual AP comparison is arithmetically reproducible but scientifically vacuous for the stated policy-aware hypothesis.
- The issue should retain the implemented methods as development baselines while transferring any claim-bearing comparison, threshold selection, scenario eligibility, and final evaluation to #10.

**Residual limitations**

- No result may be promoted to final paper evidence from this issue alone.
- Rescoping must preserve all negative and inconclusive results and must not unlock or define the holdout.

### #7 Implement duplicate-record detection experiment

**Recommendation: Close with evidence.**

**Acceptance evidence**

- Commit [`829f608`](https://github.com/ibrahimify/MyHR/commit/829f608) added raw exact, normalized exact, and weighted similarity matching in `src/services/anomaly_detection/duplicate_detection.py`.
- `DuplicateEvaluation` reports precision, recall, F1, false-positive rate, and confusion counts.
- Candidate records preserve field-level evidence for name, date of birth, national ID, and email.
- `tests/test_anomaly_detection_skeleton.py` verifies method separation, recovery of normalized/similar variants, review evidence, and duplicate ground-truth sibling pairs.

**Residual limitations**

- This is a separate pairwise task and must not be pooled with progression-anomaly metrics.
- Threshold generalization to real organizational data has not been established; findings remain human-review suggestions, never automatic merges.

### #8 Create reproducible experiment reports and paper figures

**Recommendation: Rescope to "Generate final traceable paper tables and figures after protocol approval."**

**Criteria already satisfied**

- Commits [`4b20011`](https://github.com/ibrahimify/MyHR/commit/4b20011) and [`ed494cf`](https://github.com/ibrahimify/MyHR/commit/ed494cf) added single-run and multi-seed CSV/JSON artifact generation with run IDs, seeds, metadata, method metrics, duplicate metrics, and comparisons.
- `scripts/run_tdk_protocol_experiment.py` now emits scenario configuration, record predictions, aggregate metrics, paired comparisons, robustness slices, utility sensitivity, and a checksum manifest.
- `scripts/audit_tdk_protocol_artifact.py` independently recomputes metric rows, paired inference, denominators, and hashes; adversarial coverage exists in `tests/test_protocol_artifact_audit.py`.

**Why the original issue should not close unchanged**

- The repository contains reproducible result tables but no implemented paper-figure generation (`matplotlib` is documented for later figures).
- Existing development and validation artifacts are diagnostics, not approved final paper results. A fresh run can regenerate development evidence, but no final paper numbers can exist before protocol approval and the one-time locked evaluation.
- The narrowed issue should require every eventual table and figure to cite its artifact run ID, source revision, configuration, and seeds, without selecting favorable rows.

**Residual limitations**

- Final figure content and claim-bearing tables are blocked by #10.
- Existing write-once artifacts and manifests must be preserved; cleanup must not rewrite or selectively delete their files.

### #9 Audit thesis and TDK scope before implementation freeze

**Recommendation: Close with evidence.**

**Acceptance evidence**

- Commit [`3bb1d49`](https://github.com/ibrahimify/MyHR/commit/3bb1d49) added [SCOPE_AUDIT.md](SCOPE_AUDIT.md).
- The audit records pass/complete, mostly complete, partial, optional, and not-final states for the thesis and TDK components with implementation references.
- It explicitly lists remaining packaging risks and pre-final-result requirements, including clean-environment tests, private-output checks, protocol approval, dependency/scenario freeze, one-time holdout execution, artifact preservation, and limitation reporting.

**Residual limitations**

- The scope audit's review date was refreshed during repository maintenance; this does not change any scientific status.
- Closing #9 does not mean packaging, protocol freeze, or final TDK evidence is complete.

### #10 Implement non-circular validation protocol for policy-aware anomaly detection

**Recommendation: Keep open.**

**Completed evidence**

- Commits [`20c21dc`](https://github.com/ibrahimify/MyHR/commit/20c21dc), [`697344a`](https://github.com/ibrahimify/MyHR/commit/697344a), and [`414a5b7`](https://github.com/ibrahimify/MyHR/commit/414a5b7) implement development/validation scenario matrices, separate seeds, controls, ablations, validation-selected operating points, equal-budget comparisons, parity tests, artifact auditing, causal sidecars, and documented corrections.
- Tests cover generator/detector separation, development/validation seed disjointness, the holdout lock, scenario coverage, reproducibility, policy parity, threshold selection, equal budgets, deterministic-rule precedence, controls, and artifact integrity.
- The current roadmap and report preserve the negative finding that the independent residual experiment cannot test incremental policy-aware value.

**Unmet `Done when` criteria and blockers**

- The required supervisor review of the protocol and scenario matrix has not occurred.
- The central residual design lacks varying policy-specific signal after deterministic filtering; it cannot answer the primary hypothesis as implemented.
- Historical policy modelling, endpoint eligibility, review-capacity rules, expert-review design, and holdout-generation design remain pending human decisions.
- The protocol is not frozen. No holdout scenario or seed is defined, and no holdout result has been inspected. This is the correct locked state and must remain so.

**Required disposition guardrail**

- Keep #10 open. Do not close it based on passing tests, artifact reproducibility, or development results; those establish engineering integrity, not protocol approval or scientific validity.

### #11 Add reproducible scholarly literature workflow

**Recommendation: Keep open until the final free Semantic Scholar live check is recorded.**

**Completed evidence**

- Commit [`5105b5c`](https://github.com/ibrahimify/MyHR/commit/5105b5c) added free direct clients, retry/rate-limit handling, optional environment-only keys, query configuration, identifier normalization, legal full-text retrieval, checksums, provenance, verification scripts, the literature review, and the bibliography.
- [TDK_LITERATURE_WORKFLOW.md](TDK_LITERATURE_WORKFLOW.md) records successful live OpenAlex and arXiv checks, DOI/arXiv verification, citation-network construction, and verified local metadata/full-text artifacts.
- `tests/test_literature_workflow.py` covers all three clients, key redaction, DOI/arXiv lookups, citation networks, cross-source merging, PDF safety, text extraction, and artifact verification.
- No paid service is enabled, and the outside paid-service suggestion on the issue is not part of the approved workflow.

**Unmet `Done when` criterion**

- All three APIs have not yet passed a reliable real-query smoke test in the recorded environment. Anonymous Semantic Scholar access returned HTTP `429`; the remaining step is the documented smoke run with a free `SEMANTIC_SCHOLAR_API_KEY`.

**Residual limitations**

- Automated client tests do not substitute for the missing live service check.
- Full-text legality and citation correctness require continued human review when the corpus is refreshed.

## Recommended Maintainer Sequence

1. Close #2, #3, #4, #5, #7, and #9 individually with links to this review and their evidence commits. State explicitly that closure records implementation completion only.
2. Edit the scope of #6 and #8 before any closure decision. Keep their development evidence and limitations visible, and cross-link #10 for all claim-bearing work.
3. Keep #10 open and unchanged until qualified human methodology review. Do not generate, inspect, score, or unlock a holdout.
4. Keep #11 open until a free-key Semantic Scholar live smoke artifact is verified and recorded. Do not adopt a paid workaround.
5. Keep PR #1 draft and unmerged. Issue disposition does not authorize merging or protocol approval.

## Verification Basis

This disposition was derived from the issue bodies and comments, the cited commits, the current research documentation, source implementations, automated tests, and the draft PR status. It does not alter protocol definitions, artifacts, issue state, PR state, or the holdout boundary.
