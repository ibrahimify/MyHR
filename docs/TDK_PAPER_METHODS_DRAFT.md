# TDK Paper Methods Draft

Status: **DEVELOPMENT DRAFT - NOT A FROZEN PROTOCOL**

This section documents implemented development work and clearly separates pending confirmatory choices. No holdout was generated or inspected.

## Research Design

The study evaluates whether explicit workforce-progression policy context improves anomaly ranking beyond administrative features and deterministic validation. MyHR is the experimental platform. The anomaly detector produces review priorities only; personnel decisions remain with an authorized human reviewer.

Progression-anomaly detection and duplicate-record detection are separate tasks. The present methods draft concerns progression anomalies only. Current results are synthetic development evidence and cannot support a final confirmatory claim.

## Policy And Administrative Representation

The application policy engine calculates promotion service requirements, commendation credits, sanction delays, and progression eligibility. Shared golden histories test parity between SQL-backed application behavior and research calculations. Independent development scenarios additionally model fictional policy transitions, recognized prior service, delayed bulk recording, wrong-employee links, missing increment imports, approval bypasses, and batch retries.

The 2026-10-17 review found that historical policy requires at least two time dimensions: the time at which a rule or fact is effective and the time at which it is recorded. A specific bitemporal schema remains pending human approval.

## Synthetic Development Data

Two generators have been used for development. The original protocol generator varies policy, population, anomaly, and rare-legitimate parameters. A separate standard-library generator constructs an administrative world and an observation ledger without importing detector, policy-feature, or original-generator code. Its source-code independence does not establish conceptual independence or real-world validity.

Each run records dataset, split, and model seeds. Scenario seed is the intended independent unit for paired comparisons. The development artifacts include complete configurations, per-record labels and scores, source revisions, dependency versions, checksums, and a `holdout_accessed: false` attestation.

## Deterministic And Statistical Methods

Deterministic checks identify explicit date contradictions, duplicate event references, unusually dense administrative activity, and policy violations. IQR and z-score methods provide statistical baselines. Isolation Forest uses continuous anomaly scores and `contamination="auto"`; known test prevalence is not passed to the model.

Raw and policy-aware representations are paired within each scenario. Wrong-policy, shuffled-policy, and single-feature ablations are retained even when unfavorable. Operational comparisons use equal nominal review capacity, while deterministic findings are currently retained above that capacity floor.

## Critical Development Limitation

The stored rule-negative experiment first removes all histories flagged by the policy validator. That same validator removes every positive service-deficit history, leaving all three policy-specific matched features constant at zero. Consequently, the saved policy-aware residual model has no varying policy-specific signal. Its reported AP difference cannot be interpreted as evidence for or against incremental policy context.

Six of twelve independent scenarios also have no residual positives. The implementation stored AP as zero for those scenarios, although the pending eligibility proposal says AP should be undefined and excluded from primary inference. Both defects are preserved in the development record. Their resolution requires a human-approved redesign before protocol freeze.

## Development Evaluation

Saved outputs report evaluation size, positive and negative counts, alert count, confusion counts, precision, recall, F1, false-positive rate, average precision, rare-legitimate and ordinary-clean alert counts, per-class recall, runtime, and workload. Scenario means and pooled counts are kept distinct.

The proposed, unapproved confirmatory endpoint is a paired scenario-level AP difference. The proposed inference uses a two-sided paired randomization procedure and a scenario-clustered bootstrap interval. The literature supports pairing on common experimental units and controlling a predeclared multiplicity family, but it does not resolve whether these assumptions fit the final MyHR scenario population. One primary endpoint, scenario eligibility, exchangeability, and secondary-test handling remain human decisions.

## Expert Review

The proposed realism review uses blinded fictional histories with no model results or generated truth labels. Two independent domain reviewers would rate plausibility, record status, evidence sufficiency, confidence, and escalation need, followed by documented adjudication. Reviewer qualifications, sample size, agreement statistic, and acceptance rule remain pending human approval.

## Reproducibility And Audit

Experiment directories are write-once and contain a SHA-256 manifest. The independent artifact audit verifies file integrity, source hashes, provenance, confusion counts, selected rates, and aggregate consistency. The 2026-10-17 review showed that it does not yet recompute AP, paired intervals, randomization tests, or multiplicity adjustments. Therefore a passing audit proves artifact integrity and selected arithmetic, not complete statistical validity.

## Traceability Matrix

| Methods statement | Traceable evidence |
| --- | --- |
| Application/research policy parity | `tests/test_business_logic.py`, `tests/test_tdk_protocol_v2.py` |
| Independent generator boundary | `src/research/independent_scenarios.py`, `tests/test_independent_scenarios.py` |
| Stored model and metric implementation | `src/services/anomaly_detection/protocol_evaluation.py` |
| Independent development run | `research_outputs/independent_development/independent_development_e342bd4acf39b06b/metadata.json` |
| Per-record scores and denominators | Same artifact: `record_predictions.csv`, `scenario_metrics.csv` |
| Paired development summaries | Same artifact: `paired_comparisons.csv` |
| Integrity and source hashes | Same artifact: `manifest.json`; adjacent `.audit.json` |
| Constant-feature and zero-positive findings | `docs/TDK_INDEPENDENT_REVIEW_2026-10-17.md` |
| Corrected original development/validation evidence | `research_outputs/protocol_v2_verified/development_5f0f99d3ffe8dc9e/`, `validation_c5878ca7b927ccd2/` |
| Literature discovery and full text | `research_outputs/literature/20261017T215024Z_f79f81f2c2b1/`, `literature_fulltext/20261017T215119Z_4b354b03c1af/` |

## Confirmatory Boundary

No final hypothesis, feature family, scenario matrix, endpoint, or holdout design is approved. The holdout remains undefined and locked. Confirmatory methods can be written only after a human records decisions and the protocol is frozen before any holdout generation.
