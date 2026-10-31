# TDK Synthetic Data Contract

> **Status note, 2026-10-29:** This contract documents development generators and the approved invariant-negative redesign. It does not establish external validity or evidence for policy-aware model superiority. The earlier independent artifact remains preserved as a failed design in which deterministic policy filtering made all three policy-specific residual features constant zero. The corrected implementation must still pass clean-revision development and validation audits before protocol freeze.

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This document defines the data contract for the TDK experiments. It is not an experimental result and must not be cited as evidence of model performance.

## Record Structure

Each synthetic employee history contains:

- Identity fields: employee ID, full name, date of birth, optional national ID, optional email.
- Organizational fields: department, role, employment track, current level, hire date.
- Administrative events: hire, promotion, commendation, sanction, salary increment, performance review, and organization change.
- Bitemporal evidence: effective date, recorded date, policy ID and version, jurisdiction, approval status and reference, recognized service, and correction or retry provenance.
- Observation date: the latest knowledge time available to feature extraction.
- Dataset split: train, validation, or test.
- Ground-truth labels: clean, injected anomaly classes, or rare legitimate policy cases.
- Optional duplicate link: the employee ID of the source record when a record is intentionally duplicated.

## Employment Tracks

- Promotion track: employees assigned to L7-L1 style career progression rules.
- Other track: employees who receive annual salary increments but do not participate in the promotion race.

The generator must keep these tracks separate because forcing every employee into promotion eligibility would create unrealistic HR behavior.

## Anomaly Taxonomy

| Label | Ground truth anomaly? | Meaning | Expected signal |
| --- | --- | --- | --- |
| `clean` | No | Administrative history follows the modeled policy and contains no injected data-quality issue. | No deterministic inconsistency and no unusual pattern beyond normal variation. |
| `inconsistent_dates` | Yes | Events occur before required predecessors or after impossible reference dates. | Negative service intervals, event order violations, or future-dated records. |
| `frequent_promotions` | Yes | Promotion intervals are too short after accounting for policy credits and delays. | Short raw promotion gaps that remain unexplained after policy conditioning. |
| `excessive_sanctions` | Yes | Employee history contains unusually many disciplinary actions. | Sanction count or frequency above baseline and peer-context thresholds. |
| `duplicate_record` | Yes | Two records likely describe the same person with different raw identifiers or normalized values. | High identity-field similarity despite non-identical values. |
| `unusual_admin_interval` | Yes | Administrative intervals are unusual but not directly illegal. | Outlier gaps between reviews, increments, sanctions, or promotions. |
| `policy_legitimate_rare_case` | No | A rare-looking history is legitimate because policy context explains it. | Raw features appear unusual, while policy-aware features explain the record. |

## Scientific Guardrails

- Rare legitimate policy cases are not counted as ground-truth errors.
- Experiments must report false positives on rare legitimate cases separately.
- No synthetic result is valid unless the seed, generation configuration, split, anomaly counts, and run ID are saved with the output.
- The paper must distinguish deterministic policy violations from statistical anomalies.
- Progression-anomaly evaluation excludes `duplicate_record`; duplicate identity matching is a separate pairwise task.
- Ground-truth-only fields such as `duplicate_of_employee_id` must never be exposed as model features.

## Generator Rules

- The generator is deterministic for a fixed `ExperimentConfig`.
- The run ID is derived from the generation configuration.
- Dataset partitions are train, validation, and test.
- Metadata records the split counts and label counts.
- True anomalies and rare legitimate policy cases are distributed across train, validation, and test splits when counts allow.
- Duplicate records must link back to a source employee ID.
- Every latent duplicate cluster must remain within one partition.
- Missing identity values are absence of evidence and never receive a perfect similarity score.
- The generator creates HR-like histories only for experimentation; it is not a claim about real employee distributions.

### Independent Development V2

The original `tdk-synthetic-v1` generator is retained for historical development diagnostics and the secondary duplicate task. The independent progression generator uses `independent-development-v2`, which:

- uses separate dataset, split, and model seeds;
- varies policy, workforce composition, anomaly prevalence, rare-case prevalence, and injection mechanisms;
- generates records without calling feature extraction or model code;
- gives ordinary legitimate histories commendations, resolved sanctions, repeated reviews, and multiple promotions where tenure permits;
- allocates each injected mechanism only to records that can realize it without known track or timing confounds;
- keeps effective time and recorded time separate and replays the applicable policy version;
- verifies that every clean and rare-legitimate completed promotion satisfies its assigned policy;
- defines development and validation matrices but deliberately defines no holdout matrix while the protocol is draft.

The v2 scenario families are synthetic stress tests. They do not establish external validity for a real organization.

## Deterministic Validation Baseline

The deterministic checker is the first non-ML baseline. It reports explainable findings for explicit administrative inconsistencies, including:

- missing hire events;
- events before the recorded hire date;
- promotion events on employees outside the promotion track;
- invalid promotion level order;
- promotion intervals below the deterministic 12-month minimum;
- salary increment intervals below the deterministic 300-day minimum;
- exact duplicate employee IDs or national IDs.

For the primary ML comparison, only structural invariants are used as a filter: missing hire evidence, events before hire, promotions on the increment-only track, and invalid level order. Fixed interval heuristics and configurable policy checks remain separate secondary baselines so they cannot consume the signal intended for the primary comparison.

Protocol v2 also evaluates `deterministic_policy_rules`, which adds an explicit service-deficit check under the scenario's true policy. This stronger baseline prevents a policy-aware ML representation from receiving credit merely for reconstructing a rule that can be evaluated exactly.

## Feature Representations

The experiments compare two feature representations for the same employee histories:

- Raw features: policy-agnostic counts and intervals, such as promotion count, sanction count, commendation count, performance review count, minimum promotion interval, and minimum salary-increment interval.
- Policy-aware features: policy-conditioned residual signals rather than raw short-promotion intervals. The default experiment uses core event signals plus remaining service deficit, deficit ratio, and whether a short promotion remains unexplained after commendation credits and sanction delays.

The key comparison is not whether a model can flag unusual histories in general. The key comparison is whether policy-aware features reduce false positives on rare but legitimate histories without hiding injected administrative errors.

## Statistical Baseline And Model Boundary

The first statistical baselines are intentionally simple:

- z-score boundary: flags a record if any selected feature is outside the training mean by a configured number of standard deviations;
- IQR boundary: flags a record if any selected feature is outside the interquartile range boundary.

These baselines are not expected to be the strongest possible methods. They provide transparent comparison points before Isolation Forest is evaluated.

Isolation Forest is represented by an explicit experiment boundary. Research dependencies are listed in `requirements-research.txt`, while desktop runtime dependencies remain in `requirements.txt`. This keeps the research environment reproducible without automatically increasing the packaged desktop application's dependency footprint.

Protocol v2 fits Isolation Forest with `contamination="auto"` and treats the model output as a continuous ranking score. It does not pass the synthetic anomaly prevalence into the model threshold. Thresholds are selected on validation data, while the equal-budget comparison alerts the same number of test records for every representation.

Every method evaluation must report:

- method name;
- feature set;
- feature names;
- precision, recall, F1 score, and false-positive rate;
- predicted positive count;
- false positives on rare legitimate policy cases.
- rare-legitimate and ordinary-clean denominators and false-positive rates.

## Duplicate-Record Detection

Duplicate detection is a secondary experiment. It compares:

- raw exact matching on unchanged identifiers;
- normalized exact matching on normalized national IDs and emails;
- weighted similarity matching across name, date of birth, national ID, and email.

Entity clusters remain within one split. The similarity threshold is selected on validation and applied once to test. Reports separate blocking recall and reduction ratio from candidate-scoring and end-to-end metrics, and include explicit pair and record denominators. Similarity candidates retain field-level evidence so a human reviewer can see why a pair was suggested. The detector recommends review and never merges records automatically.
