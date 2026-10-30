# TDK Paper Methods Draft

Status: **DEVELOPMENT DRAFT - NOT A FROZEN PROTOCOL**

This section documents implemented development work and separates the approved confirmatory design from work not yet implemented or frozen. No holdout was generated or inspected.

## Research Design

The study evaluates whether explicit workforce-progression policy context improves anomaly ranking beyond administrative features and deterministic validation. MyHR is the experimental platform. The anomaly detector produces review priorities only; personnel decisions remain with an authorized human reviewer.

Progression-anomaly detection and duplicate-record detection are separate tasks. The present methods draft concerns progression anomalies only. Current results are synthetic development evidence and cannot support a final confirmatory claim.

## Policy And Administrative Representation

The application policy engine calculates promotion service requirements, commendation credits, sanction delays, and progression eligibility. Shared golden histories test parity between SQL-backed application behavior and research calculations. Independent development scenarios additionally model fictional policy transitions, recognized prior service, delayed bulk recording, wrong-employee links, missing increment imports, approval bypasses, and batch retries.

The 2026-10-17 review found that historical policy requires at least two time
dimensions: the time at which a rule or fact is effective and the time at which
it is recorded. The project author approved a bitemporal contract with policy
versions, recognized service, correction provenance, and employee-specific
entitlement evidence linked to the applicable policy version and event. A
research-only schema implements separate `known_then` and `later_review` views.
Production-database migration, protocol-scale verification, and protocol freeze
remain pending.

## Synthetic Development Data

Two generators have been used for development. The original protocol generator varies policy, population, anomaly, and rare-legitimate parameters. A separate standard-library generator constructs an administrative world and an observation ledger without importing detector, policy-feature, or original-generator code. Its source-code independence does not establish conceptual independence or real-world validity.

Each run records dataset, split, and model seeds. Scenario seed is the intended
independent unit for paired comparisons. Every included protocol-scale condition
uses 30 independent scenario seeds unless a written pre-run power or feasibility
justification approves another number. The development artifacts include
complete configurations, per-record labels and scores, source revisions,
dependency versions, checksums, and a `holdout_accessed: false` attestation.

Compatible scenario construction is predeclared. Stable-administration and
merger/migration populations may host all five rare-legitimate patterns;
rapid-expansion scenarios exclude legacy policy transitions under the current
hire window. Late corrections require an existing promotion and lawful
one-to-one supersession. Grandfathering requires employee-, policy-version-, and
event-linked entitlement evidence. Infeasible combinations are reported and
omitted rather than forced. The final balanced cell allocation is not frozen.

## Deterministic And Statistical Methods

Deterministic checks identify explicit date contradictions, duplicate event references, unusually dense administrative activity, and policy violations. IQR and z-score methods provide statistical baselines. Isolation Forest uses continuous anomaly scores and `contamination="auto"`; known test prevalence is not passed to the model.

Raw and policy-aware representations are paired within each scenario. Wrong-policy, shuffled-policy, and single-feature ablations are retained even when unfavorable. Operational comparisons use equal nominal review capacity, while deterministic findings are currently retained above that capacity floor. Queue size is `ceil(0.10 n)`; for the current 72-record scenario tests, the nominal 10% capacity therefore selects 8 records (11.11%).

## Historical Failure And Corrected Development Run

An early rule-negative experiment removed every positive service-deficit history, leaving all three policy-specific matched features constant at zero. Its AP difference cannot be interpreted as evidence for or against incremental policy context. This failure is preserved as a design diagnostic; it is not the current result.

The corrected code retains zero-positive scenarios and their denominators, marks recall and AP undefined when appropriate, and excludes only undefined values from metric-specific paired inference. Artifact `4feea4508de1bb05`, generated from clean commit `56597d3`, passed the strengthened audit: 12 scenarios, 864 eligible test histories, 108 anomalies, 72 generated rare-legitimate labels, 900 metric rows, 64,800 prediction rows, and `holdout_accessed: false`. Twenty-four grandfathering labels lack independently established employee entitlement. At equal additional review capacity, the primary scenario-level recall difference for policy-aware minus raw Isolation Forest was +0.0278, 95% bootstrap interval [-0.0278, +0.1019], paired sign-flip p=0.6875. Wrong-policy context selected exactly the same alert membership as policy-matched context, while three single-policy-feature ablations each found 42 anomalies compared with 39 for the full representation. No advantage or correct-policy effect was demonstrated in this exploratory development run; the interval does not establish equivalence. New protocol-scale development and validation artifacts are still required before protocol freeze.

## Development Evaluation

Saved outputs report evaluation size, positive and negative counts, alert count, confusion counts, precision, recall, F1, false-positive rate, average precision, rare-legitimate and ordinary-clean alert counts, per-class recall, runtime, and workload. Scenario means and pooled counts are kept distinct.

The approved primary endpoint is the paired scenario-level difference in recall
at identical fixed additional ML review capacity after invariant-only filtering.
Precision and total false alerts accompany it descriptively. The predeclared
secondary family contains paired policy-aware-versus-raw differences in AP,
rare-legitimate false-alert rate, and ordinary-legitimate false-alert rate;
Holm's step-down adjustment is applied across those three two-sided tests. A
two-sided paired randomization procedure and scenario-clustered bootstrap
interval remain subject to implementation checks and protocol freeze.
Zero-positive scenarios remain in design and denominator tables; recall and AP
are undefined and excluded only from their metric-specific paired inference.

## Expert Review

The approved realism-review method uses 48 blinded fictional histories with no
model results or generated truth labels: 12 ordinary legitimate, 12 rare
legitimate, 12 administrative-error, and 12 ambiguous or evidence-insufficient
cases. Two independent reviewers with complementary HR-policy and
information-systems expertise rate plausibility, record status, evidence
sufficiency, confidence, and escalation need. Initial judgments are preserved.
Raw agreement and unweighted Cohen's kappa with a case-bootstrap interval are
reported for four-category record status. Disagreements and any insufficient-
evidence rating are adjudicated against cited policy evidence; unresolved cases
remain ambiguous. Exact reviewer identities, qualifications, sampling output,
seed, order randomizations, and packet checksum remain pending.

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
| Current repaired independent development run | `research_outputs/independent_development/independent_development_4feea4508de1bb05/metadata.json` (status: verified, commit `56597d3`) |
| Per-record scores and denominators | Same artifact: `record_predictions.csv`, `scenario_metrics.csv` |
| Paired development summaries | Same artifact: `paired_comparisons.csv` |
| Integrity and source hashes | Same artifact: `manifest.json`; adjacent `.audit.json` |
| Constant-feature and zero-positive findings | `docs/TDK_INDEPENDENT_REVIEW_2026-10-17.md` |
| Corrected original development/validation evidence | `research_outputs/protocol_v2_verified/development_5f0f99d3ffe8dc9e/`, `validation_c5878ca7b927ccd2/` |
| Literature discovery and full text | `research_outputs/literature/20261017T215024Z_f79f81f2c2b1/`, `literature_fulltext/20261017T215119Z_4b354b03c1af/` |

## Confirmatory Boundary

The methodology direction, primary endpoint, residual boundary, entitlement and
temporal contract, compatibility rules, repeated-seed rule, reviewer procedure,
and secondary Holm family are approved for protocol preparation. The exact
balanced scenario matrix, concrete example set, reviewer identities, feature
family, dependencies, source revision, and final analysis implementation are not
frozen. The holdout remains undefined and locked until implementation,
independent verification, and a separate dated protocol-freeze approval.
