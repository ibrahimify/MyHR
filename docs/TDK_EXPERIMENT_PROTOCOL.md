# TDK Experiment Protocol

Protocol status: **DRAFT - HOLDOUT LOCKED**

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Human methodology decisions were recorded on 29 October 2026, with an author
decision addendum on 30 October 2026, in
`TDK_SUPERVISOR_DECISIONS_2026-10-29.md`. They approve the design for
implementation and protocol preparation, not protocol freeze. This protocol
must be implemented, verified, independently reviewed, and marked `FROZEN` at a
recorded source revision before any holdout scenario is generated or executed.

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

For the primary residual comparison, deterministic filtering is restricted to invariant contradictions that are independent of configurable progression policy. The same invariant checks and findings apply to both ML pipelines. Configurable policy checks remain part of the rule-only baseline and complete rules-plus-ML workflow, both reported secondarily. ML must demonstrate incremental value at equal additional review capacity.

## Data Partitions

- Seeds `2026-2030`: development-only and permanently ineligible for final claims.
- Protocol-development scenarios: may be generated and inspected while implementing this document.
- Validation scenarios: used for thresholds, hyperparameters, and feature-family decisions.
- Locked holdout scenarios: not generated or inspected until the generator, invariant-rule boundary, feature definitions, review-capacity objective, zero-positive treatment, scenario matrix, and analysis script are frozen.

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
- policy transitions and lawful historical exceptions;
- effective-time and recorded-time variation;
- recognized-service and correction-provenance mechanisms.

The holdout matrix must cover policy transitions, lawful exceptions, administrative errors, populations, and repeated seeds. Its causal truth stays outside model inputs. At least one holdout scenario family must use a generation mechanism implemented independently from the detector's policy residual calculation.

### Approved scenario compatibility boundary

Protocol-scale conditions may combine any of the four anomaly mechanisms with a
population and rare-legitimate pattern only when both interventions' source
records and eligibility preconditions can be satisfied without contradiction.
The approved population-pattern combinations are:

| Population | Compatible rare-legitimate patterns |
| --- | --- |
| Stable administration | grandfathered policy, recognized prior service, delayed bulk recording, late correction, policy transition |
| Rapid expansion | grandfathered policy, recognized prior service, delayed bulk recording, late correction |
| Merger or migration | grandfathered policy, recognized prior service, delayed bulk recording, late correction, policy transition |

`late_correction` requires a progression-track employee with an existing
promotion, valid one-to-one correction provenance, and a lawful corrected
history. `policy_transition` additionally requires that a 30-month legacy
service requirement can be completed no later than 31 December 2022; it is
therefore incompatible with the current rapid-expansion hire window.
Grandfathering requires employee-, policy-version-, and event-linked entitlement
evidence. Recognized prior service requires decision-linked service evidence.
Delayed bulk recording changes recorded time, not effective time. Incompatible
or infeasible cells are reported and omitted rather than populated with forced
records. The final frequency allocation remains part of the unfrozen matrix.

## Comparisons And Ablations

Every comparison uses the same scenario, split, model-seed budget, and evaluation records.

The primary comparison applies identical invariant checks to both representations, preserves those findings, and allocates an identical additional ML review budget over the same remaining records. The complete rules-plus-ML queue is a secondary operational analysis.

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

1. Recall at an identical fixed top-10% additional ML review budget as the primary endpoint.
2. Precision, total false alerts, and rare-legitimate false-alert counts and rates at that capacity.
3. Average Precision as a secondary ranking metric without selecting a test threshold.
4. A threshold selected on validation data for a predeclared target false-positive rate as a secondary analysis.
5. Validation-maximized F1 as a secondary analysis, using the same search budget for both representations.

The configured anomaly prevalence must not be passed directly as a known test threshold. No threshold may be selected from holdout labels.

For the primary residual comparison, invariant findings are preserved outside the additional ML budget. Raw and policy-aware ML receive the same number of additional review slots over the same remaining records. For the secondary complete workflow, every deterministic policy finding is preserved and reported separately from the equal ML allocation; the queue must not hide findings merely to fit a nominal capacity.

Zero-positive scenarios are retained and reported with their counts and denominators. Recall and AP are marked undefined for those scenarios and excluded from scenario-level paired inference for those metrics under a predeclared eligibility indicator. They must never be assigned zero, removed after inspection, or used to choose scenario families. Pooled counts across all scenarios are reported separately and cannot replace scenario-level inference.

## Metrics And Denominators

For every method and scenario, save:

- evaluation record count;
- true anomaly count and non-anomaly count;
- alert count and alert rate;
- true positives, false positives, true negatives, and false negatives;
- precision, recall, F1, false-positive rate, and average precision;
- rare-legitimate count, flagged count, and flagged rate;
- ordinary-clean count, flagged count, and flagged rate;
- recall per anomaly class;
- runtime and review workload.
- zero-positive eligibility status for recall and AP inference.

Counts must never be reported without denominators. Aggregate tables include both mean per-scenario rates and pooled numerators/denominators.

## Statistical Analysis

- Use 30 independent scenario seeds for every predeclared protocol-scale
  condition unless a written power or feasibility justification for another
  count is approved before that condition is run. Methods remain paired within
  each scenario seed.
- Analyze paired raw-versus-policy differences within the same scenario, with recall at fixed capacity as the primary difference.
- Report mean and median differences, variability, 95% paired bootstrap confidence intervals, and a paired sign-flip/permutation test.
- Treat scenario seeds, not individual records from one generated organization, as the primary independent units.
- Report failures and negative findings. Do not select seeds or scenarios based on favorable outcomes.
- Predeclare one confirmatory secondary family containing the paired
  policy-aware-versus-raw differences in (1) AP, (2) rare-legitimate false-alert
  rate, and (3) ordinary-legitimate false-alert rate. Apply Holm's step-down
  adjustment across these three two-sided tests.
- Report precision and total false alerts alongside the primary endpoint as
  descriptive companion measures; at fixed queue size they are algebraically
  tied to true positives. Treat threshold analyses, per-class results, controls,
  ablations, and utility sensitivity as exploratory.

## Operational Utility

The value claim is evaluated at equal review capacity. Report anomalies found per 100 reviews and rare-legitimate employees unnecessarily reviewed per 1,000 employees.

Include a sensitivity table for multiple cost ratios between:

- reviewing a false alert;
- missing a genuine administrative error;
- falsely escalating legitimate exceptional behavior.

No single cost ratio may be presented as universally correct.

## Bitemporal Policy And Evidence Contract

Every policy and administrative fact used by the final experiment must carry:

- a stable identifier and version;
- valid-from and valid-to times describing when it was effective;
- recorded-at time describing when the system learned it;
- jurisdiction or applicability scope where relevant;
- recognized-service evidence;
- correction provenance linking amendments to the superseded record.
- for any grandfathering or comparable exception, an entitlement evidence
  record linked to the employee, applicable policy ID and version, relevant
  administrative event, evidence reference, and recorded/knowledge time.

Every historical decision is evaluated under two explicit views:

- `known_then`: facts effective by the decision date and recorded by that date,
  using policy knowledge available by that date;
- `later_review`: the same effective decision horizon, while admitting facts,
  corrections, and policy amendments recorded by the later review date.

Both views must be tested and stored distinctly. Later-recorded evidence must
not be silently treated as known at the original decision. Prediction inputs
must not contain causal truth, generated labels, or mechanism identifiers.

## Blinded Expert Realism Review

Before protocol freeze, two independent reviewers with complementary HR-policy
and information-systems expertise review the same predeclared sample of 48
synthetic histories. Reviewer identities and qualifications must be entered in
the two empty nomination slots before execution. The sample is stratified as 12
ordinary legitimate, 12 rare legitimate, 12 administrative-error, and 12
ambiguous or evidence-insufficient histories, with coverage balanced across
included populations, policy versions, and compatible mechanisms as far as the
frozen candidate pool permits. Selection uses a recorded seed from development
or validation candidates only and is independent of model scores.

Reviewers are blinded to generated labels, model scores, model findings, and
each other's first-pass ratings. Both receive the same cases in independently
randomized order. Preserve initial judgments and reasons. Report raw agreement
and unweighted Cohen's kappa with a 95% scenario-bootstrap interval for the
four-category record-status item; report raw agreement for the remaining
categorical items. After both first passes are locked, disagreements and any
`Insufficient evidence` rating are reviewed jointly against cited policy and
record evidence. Store the initial ratings, evidence citation, adjudicated
outcome, and reason separately. If evidence does not resolve the case, retain it
as ambiguous and exclude it from binary ground truth rather than forcing
agreement.

## Duplicate-Detection Protocol

- Generate latent people first and derive complete entity clusters.
- Keep each entity within one partition.
- Separate blocking from scoring evaluation.
- Include typos, transpositions, missing fields, aliases, diacritics, date errors, identifier errors, and conflicting fields.
- Include hard nonduplicates such as similar names, shared birthdays, relatives, shared contacts, and near-identical identifiers.
- Select similarity threshold on validation only.
- Report blocking recall, reduction ratio, precision, recall, F1, average precision, candidates per 1,000 records, false matches per 1,000 records, runtime, and memory.

## Artifact Requirements

Every run must store:

- protocol version and status;
- complete configuration;
- exact command line;
- Git commit and dirty-state flag;
- hashes of generator, feature, policy, and evaluation sources;
- Python and package versions;
- seeds and policy configuration;
- per-record labels, scores, predictions, anomaly class, zero-positive eligibility, and causal truth in a detector-inaccessible sidecar;
- policy versions, effective times, recorded times, recognized-service evidence, and correction provenance;
- per-scenario and aggregate metrics;
- artifact checksums.

Artifact directories are write-once. A command must refuse to overwrite an existing run.

## Holdout Unlock Checklist

The holdout remains locked until all items are true:

- all research tests pass;
- synthetic clean and rare-legitimate histories satisfy the formal policy;
- application and research policy engines pass shared golden-history tests;
- task definitions and feature families are frozen;
- invariant-rule boundary, fixed review capacity, zero-positive treatment, and secondary threshold objectives are frozen;
- robustness scenario matrix is frozen;
- bitemporal policy and administrative-evidence contract is implemented and tested;
- the two reviewer identities and qualifications are nominated, and the
  predeclared sampling, agreement, and adjudication protocol is signed before
  distribution;
- analysis code produces complete denominators and uncertainty estimates;
- artifact provenance is write-once and verified;
- supervisor approves the protocol.

After unlocking, the holdout is run once. Any later change creates a new protocol version and a new holdout family; the original result remains archived.

## Implemented Draft Protocol Boundary

The v2 implementation currently provides:

- separate development and validation seed ranges with no holdout seed definition;
- three policy profiles, three population profiles, three anomaly-mechanism families, and three rare-legitimate patterns;
- independent dataset, split, and model seeds;
- a pure promotion-race calculation shared by the desktop business logic and research features;
- golden-history parity tests between SQL-backed application behavior and research records;
- raw and policy-matched Isolation Forest representations;
- single-feature policy ablations, a raw no-commendation ablation, wrong-policy control, and shuffled-policy control;
- continuous Isolation Forest scores fitted with `contamination="auto"`;
- average precision, equal review-budget evaluation, validation-F1 thresholds, and validation target-FPR thresholds;
- policy-agnostic deterministic checks, full deterministic policy checks, IQR, and z-score comparisons;
- a policy-rules-plus-ML cascade that retains every explicit policy finding and uses ML only to fill the remaining nominal review capacity;
- a rule-negative residual experiment that fits and evaluates ML only after deterministic policy findings are removed;
- paired bootstrap intervals, paired sign-flip tests, operational workload measures, and cost sensitivity;
- Holm-adjusted exploratory p-values across the generated comparison family;
- write-once artifacts containing per-record predictions, provenance, and SHA-256 checksums.

Implementation does not change the protocol status. The holdout remains locked until the checklist above is reviewed and the protocol is explicitly frozen with supervisor approval.

The 29 October decisions supersede the earlier full-policy residual gate and
AP-primary interpretation. The 30 October addendum approves lawful correction
and transition eligibility, employee-linked entitlement evidence, explicit
decision-time and later-review views, 30 repeated seeds per selected condition,
and the three-endpoint Holm family. As of 30 October 2026 the invariant-only
residual boundary, recall-primary endpoint, equal additional ML budget,
entitlement evidence structure, temporal-view primitives, and population-pattern
compatibility guard exist in development code and tests. They remain unfrozen.
The exact protocol-scale frequency allocation, concrete example review, two
human reviewer nominations, reviewer execution, environment freeze, independent
final verification, and holdout authorization are incomplete. Existing
artifacts remain development diagnostics; the protocol is not frozen and the
holdout is locked.
