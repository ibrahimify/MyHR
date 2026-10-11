# TDK Synthetic Data Contract

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This document defines the data contract for the TDK experiments. It is not an experimental result and must not be cited as evidence of model performance.

## Record Structure

Each synthetic employee history contains:

- Identity fields: employee ID, full name, date of birth, optional national ID, optional email.
- Organizational fields: department, role, employment track, current level, hire date.
- Administrative events: hire, promotion, commendation, sanction, salary increment, performance review, and organization change.
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

## Generator Rules

- The generator is deterministic for a fixed `ExperimentConfig`.
- The run ID is derived from the generation configuration.
- Dataset partitions are train, validation, and test.
- Metadata records the split counts and label counts.
- Duplicate records must link back to a source employee ID.
- The generator creates HR-like histories only for experimentation; it is not a claim about real employee distributions.

## Deterministic Validation Baseline

The deterministic checker is the first non-ML baseline. It reports explainable findings for explicit administrative inconsistencies, including:

- missing hire events;
- events before the recorded hire date;
- promotion events on employees outside the promotion track;
- invalid promotion level order;
- promotion intervals below the deterministic 12-month minimum;
- salary increment intervals below the deterministic 300-day minimum;
- exact duplicate employee IDs or national IDs.

These checks are intentionally conservative. They are designed to catch directly checkable problems, not to replace statistical anomaly detection or policy-aware machine-learning features.

## Feature Representations

The experiments compare two feature representations for the same employee histories:

- Raw features: policy-agnostic counts and intervals, such as promotion count, sanction count, commendation count, performance review count, minimum promotion interval, and minimum salary-increment interval.
- Policy-aware features: raw features plus explicit progression context, including required service months, commendation credit months, sanction delay months, policy-adjusted service months, remaining service deficit, and whether policy explains a raw short-promotion signal.

The key comparison is not whether a model can flag unusual histories in general. The key comparison is whether policy-aware features reduce false positives on rare but legitimate histories without hiding injected administrative errors.

## Statistical Baseline And Model Boundary

The first statistical baselines are intentionally simple:

- z-score boundary: flags a record if any selected feature is outside the training mean by a configured number of standard deviations;
- IQR boundary: flags a record if any selected feature is outside the interquartile range boundary.

These baselines are not expected to be the strongest possible methods. They provide transparent comparison points before Isolation Forest is evaluated.

Isolation Forest is represented by an explicit experiment boundary. The code can run the model when scikit-learn is installed, but scikit-learn is not yet added to the application dependency list. This keeps the research dependency decision separate from the packaged desktop application.

Every method evaluation must report:

- method name;
- feature set;
- feature names;
- precision, recall, F1 score, and false-positive rate;
- predicted positive count;
- false positives on rare legitimate policy cases.
