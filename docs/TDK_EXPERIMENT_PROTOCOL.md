# TDK Experiment Protocol

Protocol status: **DRAFT - HOLDOUT LOCKED**

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This protocol prevents further feature tuning against the same observed outputs. It must be reviewed and marked `FROZEN` before any holdout scenario is executed.

## Research Questions

1. Does policy context improve progression-anomaly ranking beyond raw administrative features and explicit deterministic rules?
2. Does any advantage generalize across employee populations, anomaly mechanisms, policy configurations, prevalence levels, and random seeds?
3. At a fixed review budget or false-positive rate, does policy context reduce costly false alerts on legitimate exceptional histories without hiding genuine errors?

## Separate Tasks

### Progression Anomaly Detection

Positive classes:

- inconsistent dates;
- unexplained frequent promotions;
- excessive sanctions;
- unusual administrative intervals.

`duplicate_record` is excluded from this task because identity duplication requires pairwise identity features.

### Duplicate Detection

Duplicate detection is evaluated independently using entity-level ground truth, entity-disjoint partitions, blocking metrics, and validation-selected similarity thresholds.

### Deterministic Validation

Explicit rule violations are evaluated as a separate baseline and as part of a rules-plus-ML review pipeline. ML must demonstrate incremental value beyond rules alone.

## Data Partitions

- Seeds `2026-2030`: development-only and permanently ineligible for final claims.
- Protocol-development scenarios: may be generated and inspected while implementing this document.
- Validation scenarios: used for thresholds, hyperparameters, and feature-family decisions.
- Locked holdout scenarios: not generated or inspected until the generator, feature definitions, threshold objectives, and analysis script are frozen.

Dataset seed, split seed, and model seed must be recorded separately. Records from one latent person or organization must never cross partitions in duplicate-detection experiments.

## Scenario Families

The final matrix must include multiple values for:

- employee count;
- anomaly prevalence;
- rare-legitimate prevalence;
- missing-data and typing-noise levels;
- promotion service requirements;
- commendation credits;
- sanction delays and resolution states;
- anomaly severity;
- employee-track mixture;
- rare-legitimate mechanisms not used to design the features.

At least one holdout scenario family must use a generation mechanism implemented independently from the detector's policy residual calculation.

## Comparisons And Ablations

Every comparison uses the same scenario, split, model-seed budget, and evaluation records.

Required representations:

- common policy-agnostic core;
- raw interval representation;
- raw representation without commendation-count shortcut;
- one policy-residual feature at a time;
- matched-dimension raw plus policy representation;
- complete frozen policy-aware representation;
- shuffled-policy control;
- wrong-policy control;
- deterministic policy checks;
- rules-plus-ML cascade.

Feature families must be frozen before the holdout is opened. Unfavorable ablations remain in the result set.

## Threshold Protocol

Isolation Forest produces continuous anomaly scores. Results must include:

1. PR-AUC without selecting a test threshold.
2. Precision and recall at a fixed top-10% review budget for both representations.
3. A threshold selected on validation data for a predeclared target false-positive rate.
4. Validation-maximized F1 as a secondary analysis, using the same search budget for both representations.

The configured anomaly prevalence must not be passed directly as a known test threshold. No threshold may be selected from holdout labels.

## Metrics And Denominators

For every method and scenario, save:

- evaluation record count;
- true anomaly count and non-anomaly count;
- alert count and alert rate;
- true positives, false positives, true negatives, and false negatives;
- precision, recall, F1, false-positive rate, and PR-AUC;
- rare-legitimate count, flagged count, and flagged rate;
- ordinary-clean count, flagged count, and flagged rate;
- recall per anomaly class;
- runtime and review workload.

Counts must never be reported without denominators. Aggregate tables include both mean per-scenario rates and pooled numerators/denominators.

## Statistical Analysis

- Use at least 30 independent scenario seeds per primary condition unless a documented power analysis supports another count.
- Analyze paired raw-versus-policy differences within the same scenario.
- Report mean and median differences, variability, 95% paired bootstrap confidence intervals, and a paired sign-flip/permutation test.
- Treat scenario seeds, not individual records from one generated organization, as the primary independent units.
- Report failures and negative findings. Do not select seeds or scenarios based on favorable outcomes.

## Operational Utility

The value claim is evaluated at equal review capacity. Report anomalies found per 100 reviews and rare-legitimate employees unnecessarily reviewed per 1,000 employees.

Include a sensitivity table for multiple cost ratios between:

- reviewing a false alert;
- missing a genuine administrative error;
- falsely escalating legitimate exceptional behavior.

No single cost ratio may be presented as universally correct.

## Duplicate-Detection Protocol

- Generate latent people first and derive complete entity clusters.
- Keep each entity within one partition.
- Separate blocking from scoring evaluation.
- Include typos, transpositions, missing fields, aliases, diacritics, date errors, identifier errors, and conflicting fields.
- Include hard nonduplicates such as similar names, shared birthdays, relatives, shared contacts, and near-identical identifiers.
- Select similarity threshold on validation only.
- Report blocking recall, reduction ratio, precision, recall, F1, PR-AUC, candidates per 1,000 records, false matches per 1,000 records, runtime, and memory.

## Artifact Requirements

Every run must store:

- protocol version and status;
- complete configuration;
- exact command line;
- Git commit and dirty-state flag;
- hashes of generator, feature, policy, and evaluation sources;
- Python and package versions;
- seeds and policy configuration;
- per-record labels, scores, predictions, and anomaly class;
- per-scenario and aggregate metrics;
- artifact checksums.

Artifact directories are write-once. A command must refuse to overwrite an existing run.

## Holdout Unlock Checklist

The holdout remains locked until all items are true:

- all research tests pass;
- synthetic clean and rare-legitimate histories satisfy the formal policy;
- application and research policy engines pass shared golden-history tests;
- task definitions and feature families are frozen;
- validation threshold objectives are frozen;
- robustness scenario matrix is frozen;
- analysis code produces complete denominators and uncertainty estimates;
- artifact provenance is write-once and verified;
- supervisor approves the protocol.

After unlocking, the holdout is run once. Any later change creates a new protocol version and a new holdout family; the original result remains archived.
