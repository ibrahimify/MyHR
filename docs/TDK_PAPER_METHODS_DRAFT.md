# TDK Paper Methods Draft

Status: **DEVELOPMENT DRAFT - NOT A FROZEN PROTOCOL**

This section documents implemented development work and separates the approved confirmatory design from work not yet implemented or frozen. No holdout was generated or inspected.

## Research Design

The study evaluates whether explicit workforce-progression policy context improves anomaly ranking beyond administrative features and deterministic validation. MyHR is the experimental platform. The anomaly detector produces review priorities only; personnel decisions remain with an authorized human reviewer.

Progression-anomaly detection and duplicate-record detection are separate tasks. The present methods draft concerns progression anomalies only. Current results are synthetic development evidence and cannot support a final confirmatory claim.

## Policy And Administrative Representation

The application policy engine calculates promotion service requirements, commendation credits, sanction delays, and progression eligibility. Shared golden histories test parity between SQL-backed application behavior and research calculations. Independent development scenarios additionally model fictional policy transitions, recognized prior service, delayed bulk recording, wrong-employee links, missing increment imports, approval bypasses, and batch retries.

The 2026-10-17 review found that historical policy requires at least two time dimensions: the time at which a rule or fact is effective and the time at which it is recorded. The supervisor approved a bitemporal contract with policy versions, recognized service, and correction provenance. A research-only schema and historical replay implementation now exist, while production-database migration and protocol freeze remain pending.

## Synthetic Development Data

Two generators have been used for development. The original protocol generator varies policy, population, anomaly, and rare-legitimate parameters. A separate standard-library generator constructs an administrative world and an observation ledger without importing detector, policy-feature, or original-generator code. Its source-code independence does not establish conceptual independence or real-world validity.

Each run records dataset, split, and model seeds. Scenario seed is the intended independent unit for paired comparisons. The development artifacts include complete configurations, per-record labels and scores, source revisions, dependency versions, checksums, and a `holdout_accessed: false` attestation.

## Deterministic And Statistical Methods

Deterministic checks identify explicit date contradictions, duplicate event references, unusually dense administrative activity, and policy violations. IQR and z-score methods provide statistical baselines. Isolation Forest uses continuous anomaly scores and `contamination="auto"`; known test prevalence is not passed to the model.

Raw and policy-aware representations are paired within each scenario. Wrong-policy, shuffled-policy, and single-feature ablations are retained even when unfavorable. Operational comparisons use equal nominal review capacity, while deterministic findings are currently retained above that capacity floor.

## Critical Development Limitation

The stored rule-negative experiment first removes all histories flagged by the policy validator. That same validator removes every positive service-deficit history, leaving all three policy-specific matched features constant at zero. Consequently, the saved policy-aware residual model has no varying policy-specific signal. Its reported AP difference cannot be interpreted as evidence for or against incremental policy context.

Six of twelve historical independent scenarios also had no residual positives, and the old implementation stored AP as zero. The corrected code retains zero-positive scenarios and their denominators, marks recall and AP undefined, and excludes only those undefined metric values from paired inference. A clean-revision independent development artifact (`62f482ce6ff477b9`, commit `bbc59f8`) has been generated and independently audited: 12 scenarios, 864 test histories, 108 anomalies, primary recall delta mean +0.037, 95% CI [−0.037, +0.111], sign-flip p=0.516. This confirms the corrected pipeline is executable; new protocol-scale development and validation artifacts are still required before protocol freeze.

## Development Evaluation

Saved outputs report evaluation size, positive and negative counts, alert count, confusion counts, precision, recall, F1, false-positive rate, average precision, rare-legitimate and ordinary-clean alert counts, per-class recall, runtime, and workload. Scenario means and pooled counts are kept distinct.

The approved primary endpoint is the paired scenario-level difference in recall at identical fixed additional ML review capacity after invariant-only filtering. Precision, total false alerts, and rare-legitimate false-alert rates accompany it; AP is secondary. A two-sided paired randomization procedure and scenario-clustered bootstrap interval remain draft analysis choices pending implementation checks and protocol freeze. The exact secondary multiplicity family also remains pending.

## Expert Review

The approved realism-review method uses blinded fictional histories with no model results or generated truth labels. Two independent reviewers with complementary HR-policy and information-systems expertise rate plausibility, record status, evidence sufficiency, confidence, and escalation need. Initial judgments are preserved, agreement is reported, disagreements are adjudicated against policy evidence, and genuine ambiguity is retained. Exact reviewer identities, sample size, agreement statistic, and operational form remain pending.

## Reproducibility And Audit

Experiment directories are write-once and contain a SHA-256 manifest. The independent artifact audit verifies file integrity, source hashes, provenance, confusion counts, rates, average precision from stored scores, aggregate consistency, paired differences, bootstrap intervals, sign-flip tests, and Holm adjustments. The strengthened auditor successfully rechecked the existing independent development artifact without changing it. A passing audit establishes reproducibility of the implemented arithmetic, not validity of the estimand or exchangeability assumptions.

Future independent development artifacts also write normalized truth, administrative-event, and policy-epoch sidecars. They preserve the generated employee context, complete event fields, nominal and realized mechanisms, causal explanation, policy identifier, effective and recorded dates, and whether each causal event was observed or intentionally omitted. The independent auditor enforces one-to-one event joins and prohibits truth-only fields in detector inputs. Existing write-once artifacts remain unchanged and therefore do not independently support the `39/39` mechanism attribution.

## Traceability Matrix

| Methods statement | Traceable evidence |
| --- | --- |
| Application/research policy parity | `tests/test_business_logic.py`, `tests/test_tdk_protocol_v2.py` |
| Independent generator boundary | `src/research/independent_scenarios.py`, `tests/test_independent_scenarios.py` |
| Stored model and metric implementation | `src/services/anomaly_detection/protocol_evaluation.py` |
| Independent development run | `research_outputs/independent_development/independent_development_e342bd4acf39b06b/metadata.json` |
| Clean-revision independent development run | `research_outputs/independent_development/independent_development_62f482ce6ff477b9/metadata.json` (status: verified, commit `bbc59f8`) |
| Per-record scores and denominators | Same artifact: `record_predictions.csv`, `scenario_metrics.csv` |
| Paired development summaries | Same artifact: `paired_comparisons.csv` |
| Integrity and source hashes | Same artifact: `manifest.json`; adjacent `.audit.json` |
| Constant-feature and zero-positive findings | `docs/TDK_INDEPENDENT_REVIEW_2026-10-17.md` |
| Corrected original development/validation evidence | `research_outputs/protocol_v2_verified/development_5f0f99d3ffe8dc9e/`, `validation_c5878ca7b927ccd2/` |
| Literature discovery and full text | `research_outputs/literature/20261017T215024Z_f79f81f2c2b1/`, `literature_fulltext/20261017T215119Z_4b354b03c1af/` |

## Confirmatory Boundary

The methodology direction, primary endpoint, residual boundary, temporal contract, reviewer method, and independent holdout design are approved for implementation. Their code, exact scenario matrix, feature family, analysis details, dependencies, and source revision are not frozen. The holdout remains undefined and locked until implementation, independent verification, and a separate dated protocol-freeze approval.
