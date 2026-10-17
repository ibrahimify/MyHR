# Independent Hostile Methodology Review - 2026-10-17

## Review Status

This is an independent adversarial review of the MyHR TDK research branch `research/policy-aware-anomaly` at revision `697344a`. It does not approve any protocol, endpoint, scenario family, implementation decision, holdout access, or publication claim.

The final holdout was not generated, inspected, scored, inferred, or unlocked. This review used only repository source, documentation, tests, and stored development/validation artifacts. The reviewed worktree was clean before this report was created. Pull request #1 was open and unmerged, relevant research issues remained open, and the latest visible CI runs were passing.

## Readiness Assessment

**Not ready for protocol freeze, holdout execution, or a claim that policy-aware ML adds residual ranking value.** The central proposed comparison is structurally invalid in the current implementation: the rule-negative filter forces all three policy-specific features in `policy_matched` to zero. The reported policy-aware residual result therefore does not measure incremental policy context.

The stored arithmetic is internally reproducible under the implemented conventions, including `0.3621` versus `0.3616`, the reported interval, and 39 rare-legitimate false alerts out of 72 rare histories. Those conventions conflict with the pending scenario-eligibility proposal because six of twelve scenarios have no residual positives and are assigned AP zero instead of being excluded as undefined. The resulting interval is descriptive development output, not a valid estimate for the proposed primary endpoint.

## Scope And Evidence

Reviewed documents included:

- `AGENTS.md`
- `docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md`
- `docs/TDK_EXPERIMENT_PROTOCOL.md`
- `docs/TDK_PROTOCOL_CHANGE_PROPOSALS.md`
- `docs/TDK_SUPERVISOR_REVIEW_PACKAGE.md`
- `docs/TDK_METHODOLOGY_REVIEW_2026-10-16.md`
- `docs/TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`
- `docs/TDK_INDEPENDENT_SCENARIO_SPEC.md`
- `docs/TDK_RESEARCH_VERIFICATION.md`

The principal stored artifact was:

`research_outputs/independent_development/independent_development_e342bd4acf39b06b/`

Exact files used for recomputation were:

- `record_predictions.csv` for labels, scores, predictions, scenario identifiers, methods, representations, and operating points;
- `scenario_metrics.csv` for stored per-scenario denominators and AP values;
- `paired_comparisons.csv` for the stored paired summary and confidence interval;
- `scenario_configs.csv` for scenario-level population, mechanism, rare-pattern, seeds, and truth-count metadata;
- `metadata.json` for revision, dependency, command, purpose, and holdout attestations;
- `manifest.json` for artifact checksums.

The artifact was generated from clean revision `0ad4e962f81d69e87bf7fd4987b8a84d4b545453`. Its manifest verification passed. The relevant evaluation, feature, deterministic-check, adapter, and independent-generator files are unchanged between that revision and the reviewed revision, and their SHA-256 hashes match `metadata.json`.

## Methodology

1. Verified the artifact manifest, recorded source revision, source hashes, clean-generation flag, development purpose, and `holdout_accessed: false` using `scripts/audit_tdk_protocol_artifact.py`.
2. Ignored aggregate summaries initially and grouped `record_predictions.csv` by scenario and representation.
3. Recomputed AP with `sklearn.metrics.average_precision_score` from each scenario's stored binary labels and continuous scores.
4. Computed the unweighted arithmetic mean of the twelve scenario AP values, matching the implementation's scenario-mean aggregation.
5. Computed policy-minus-raw AP within each paired scenario and reproduced the percentile bootstrap using 10,000 resamples and the implementation's stable SHA-256-derived seed.
6. Recomputed deterministic-policy-rule rare counts directly from per-record labels and predictions.
7. Traced the residual filter, feature definitions, adapter, rare-case generator, aggregation code, auditor, and tests. A deterministic in-memory development regeneration was used only to test source-level implications that are not recorded in the artifact. No holdout path or seed exists or was invoked.
8. Ran `python -m unittest tests.test_independent_scenarios tests.test_tdk_protocol_v2 tests.test_protocol_artifact_audit`; all 30 tests passed.

Core recomputation logic:

```python
rows = read_csv("record_predictions.csv")
rows = [r for r in rows
        if r["method"] == "rule_negative_isolation_forest"
        and r["operating_point"] == "fixed_review_budget"
        and r["representation"] in {"raw_matched", "policy_matched"}]

ap[scenario, representation] = average_precision_score(
    stored_ground_truth, stored_continuous_score
)
deltas = [ap[s, "policy_matched"] - ap[s, "raw_matched"] for s in scenarios]
reported_means = mean(ap[s, representation] for s in all_12_scenarios)
reported_ci = quantile(
    mean(resample_with_replacement(deltas, size=12)) for _ in range(10_000),
    [0.025, 0.975],
)
```

The exact bootstrap seed was `156174388`, derived from SHA-256 of `rule_negative_isolation_forest:fixed_review_budget:average_precision`.

## Independent Recomputation

### Residual AP

**Verified result.** The reported values are unweighted means of twelve scenario-level AP values, not pooled-record AP values.

| Scenario | Residual records | Residual positives | Raw AP | Policy AP | Policy - raw |
| --- | ---: | ---: | ---: | ---: | ---: |
| ind-dev-01 | 66 | 9 | 0.801099 | 0.759432 | -0.041667 |
| ind-dev-02 | 68 | 9 | 0.765226 | 0.258744 | -0.506481 |
| ind-dev-03 | 63 | 0 | 0.000000 | 0.000000 | 0.000000 |
| ind-dev-04 | 57 | 0 | 0.000000 | 0.000000 | 0.000000 |
| ind-dev-05 | 62 | 5 | 0.828571 | 1.000000 | +0.171429 |
| ind-dev-06 | 67 | 4 | 0.383333 | 0.783333 | +0.400000 |
| ind-dev-07 | 60 | 0 | 0.000000 | 0.000000 | 0.000000 |
| ind-dev-08 | 58 | 0 | 0.000000 | 0.000000 | 0.000000 |
| ind-dev-09 | 71 | 8 | 0.918750 | 0.975000 | +0.056250 |
| ind-dev-10 | 66 | 7 | 0.642502 | 0.568880 | -0.073623 |
| ind-dev-11 | 58 | 0 | 0.000000 | 0.000000 | 0.000000 |
| ind-dev-12 | 63 | 0 | 0.000000 | 0.000000 | 0.000000 |

Aggregation and denominators:

- 12 scenario units, each weighted equally;
- 759 residual test records total: 42 positives and 717 negatives;
- 81 fixed-budget alerts for raw and 81 for policy-aware;
- raw scenario-mean AP: `0.36162347225246466`, reported as `0.3616`;
- policy scenario-mean AP: `0.3621157737314858`, reported as `0.3621`;
- paired mean difference: `+0.0004923014790211011`, reported as `+0.0005`.

AP has no count numerator analogous to a proportion. Its relevant denominators are the records and positives entering each scenario ranking. The pooled-record APs, which are not the reported estimand and should not replace it, are raw `0.3716747605` and policy `0.3621105441`. This difference confirms that the documentation must continue to call the reported numbers scenario means, not pooled AP.

### Paired Confidence Interval

**Verified result under the implemented, but methodologically disputed, convention.** The twelve policy-minus-raw deltas were resampled as paired scenario units. The implementation drew 10,000 bootstrap samples of size 12 with replacement, calculated each sample mean, and used the 2.5th and 97.5th percentiles.

- recomputed exact interval: `[-0.11725459577768009, 0.10791823939856704]`;
- report rounding: `[-0.1173, 0.1079]`;
- stored value in `paired_comparisons.csv`: exact match;
- paired delta standard deviation: `0.20365495422245652`;
- median paired delta: `0.0`;
- exact sign-flip result stored and reproduced by the same deltas: `p = 1.0`.

**Discrepancy:** six zero-positive scenarios contribute structural zero deltas. Under `docs/TDK_PROTOCOL_CHANGE_PROPOSALS.md`, their AP is undefined and they must not contribute as zero. Restricting to the six eligible scenarios gives 400 records, 42 positives, raw mean AP `0.7232469445`, policy mean AP `0.7242315475`, mean delta `+0.0009846030`, and the same bootstrap algorithm gives `[-0.23855815, 0.20935650]`. This alternative is still underpowered and does not establish an advantage.

### Policy-Transition False Alerts

**Verified artifact count.** Filtering `record_predictions.csv` to `deterministic_policy_rules / true_policy_checks / rules_fixed` gives:

- 864 test histories total;
- 108 labelled anomalies and 756 non-anomalies;
- 72 rare-legitimate histories;
- 105 total rule alerts: 66 true positives and 39 false positives;
- all 39 false positives are rare-legitimate histories;
- rare-legitimate false-alert proportion: `39/72 = 54.17%`.

Scenario-level rare-pattern totals are 24 grandfathered-policy, 24 recognized-prior-service, and 24 delayed-bulk-recording histories. The stored predictions give 19/24, 20/24, and 0/24 alerts respectively. Thus the report's 39/72 arithmetic is correct.

**Denominator qualification:** the generator applies grandfathering or recognized-service transitions only to progression-track employees; non-progression employees assigned those scenario patterns fall through to delayed bulk recording. Source-level deterministic regeneration shows 39 actual policy-transition histories, all 39 flagged. Therefore three distinct statements must not be conflated:

- 39/72 of all rare-legitimate histories were flagged;
- 39/48 histories in scenarios nominally assigned a transition rare pattern were flagged;
- 39/39 actually instantiated policy-transition histories were flagged.

The artifact does not store the per-record truth evidence or actual rare mechanism, so the last attribution cannot be reconstructed from the artifact alone; it requires the recorded source revision and deterministic regeneration.

## Verified Findings

### Critical: Policy-aware residual features are deterministically erased

`protocol_evaluation.py` defines `policy_matched` as the six common features plus `policy_service_deficit_months`, `policy_service_deficit_ratio`, and `policy_unexplained_short_promotion`. It then constructs the residual population by retaining only records for which `validate_record_with_policy` returns no finding. That validator uses the same promotion-history assessment and emits a finding whenever service deficit is positive.

Consequently, every retained residual record has all three policy-specific matched features equal to zero. Replaying the recorded development generator and filter produced 3,827 residual records across train, validation, and test, with unique values `{0.0}` for each of the three policy-specific columns. Relevant implementation locations are `src/services/anomaly_detection/protocol_evaluation.py:30-35,280-345`, `src/services/anomaly_detection/features.py:85-128`, and `src/services/anomaly_detection/deterministic_checks.py:107-131`.

The alleged nine-dimensional policy-aware model therefore has only six effective varying features, while `raw_matched` retains three additional varying raw features. This is not an equal-information or effective-dimension comparison, and it cannot estimate incremental value from policy context beyond deterministic rules. Differences in AP are differences between a six-variable common-core model and a nine-variable raw model, not evidence for or against policy-aware residual features.

This directly contradicts the proposed primary hypothesis and the reports' causal wording that policy-aware features help one residual mechanism and hurt another. The implementation may produce different rankings, but those differences cannot be attributed to policy-specific features because those features are constant.

### High: Undefined AP values are silently encoded as zero and enter inference

`protocol_evaluation.py:726-731` returns `0.0` when a scenario has no positive labels. Six of twelve independent scenarios have zero rule-negative positives because approval-bypass and batch-retry cases are entirely removed by deterministic checks. Those six zeros enter both representation means and the paired bootstrap.

This conflicts explicitly with `docs/TDK_PROTOCOL_CHANGE_PROPOSALS.md`, which states that scenarios with no residual positives cannot contribute a defined scenario-level AP and must not be silently counted as zero. It also halves both reported AP means and makes the interval substantially narrower than the eligibility-consistent calculation.

The test `tests/test_independent_scenarios.py:78-92` requires only that some residual errors exist across selected scenarios. It does not require positive residual cases in every primary-eligible scenario and therefore does not detect this failure.

### High: The transition false-alert result is constructed from a guaranteed policy mismatch

The independent generator creates grandfathered promotions at 30 months and recognized-service promotions at 24 months. The adapter discards historical policy choice as a detector input and exposes the current 36-month policy. The same current-policy arithmetic then deterministically flags those histories. This is useful as a designed counterexample demonstrating a missing policy-version contract, but it is not an empirical estimate of how often such false alerts occur in realistic organizations.

Because all 39 actually instantiated transition histories are flagged, the observed count is guaranteed by construction once track assignment is known. Statements that the result "demonstrates" unreliability should be limited to existence of a specification failure, not its prevalence, operational frequency, or external reliability.

### High: The independent residual scenarios do not test the stated policy-value mechanism

Code-level independence is verified: `src/research/independent_scenarios.py` imports no MyHR detector or original generator modules. Conceptual independence is not sufficient for the proposed question. Wrong-employee linkage injects five sanctions, and missing-increment import changes increment counts/intervals. These mechanisms are represented in the six common features available to both models; neither requires policy context. Approval bypass is a direct policy violation and batch retry a direct interval violation, so deterministic rules remove both from residual evaluation.

The independent artifact is therefore a useful stress test of common administrative features, but it contains no varying policy-specific residual signal under the current filter. It cannot validate the claimed incremental policy-aware mechanism.

### Medium: Scenario-level uncertainty lacks replication and exchangeability support

Only six scenarios are informative for residual AP. Each population-by-mechanism cell appears once, with one dataset seed and one model seed. Mechanism, population, rare pattern, and random realization cannot be separated cleanly, and there are only three informative scenarios per surviving mechanism.

The percentile bootstrap treats the included scenarios as exchangeable draws from an implicit scenario population that is not defined. This violates the draft protocol's expectation of at least 30 independent scenario seeds per primary condition and makes mechanism claims particularly unstable. The reports appropriately call the run development-only and inconclusive; any stronger use would be unsupported.

### Medium: Stored artifacts cannot audit the causal rare-case attribution

`record_predictions.csv` stores the broad label `policy_legitimate_rare_case` and a scenario-level `rare_pattern`, but not the per-record truth mechanism, evidence, track, policy epoch, or fallback branch. Non-progression employees assigned a transition pattern are actually transformed into delayed-recording cases while retaining the scenario's nominal pattern.

As a result, 39/72 rare false alerts are directly auditable, but "39 policy-transition false alerts" is not independently auditable from stored rows. This falls short of the provenance needed for mechanism-specific conclusions.

### Medium: The artifact auditor does not verify AP or paired inference

`scripts/audit_tdk_protocol_artifact.py` verifies checksums, source hashes, confusion counts, selected rates, aggregate counts, and aggregate means copied from scenario metrics. It does not recompute AP from stored scores, verify score-to-prediction threshold logic, recompute paired deltas, confidence intervals, sign-flip tests, or Holm adjustments. Its selected output reads the stored AP mean without independently validating it.

The supervisor package's broad statement that the auditor "recomputes saved results" is overstated. The requested AP and confidence interval required separate recomputation in this review. Passing auditor tests should not be interpreted as statistical-result verification.

### Low: The proposed primary endpoint was selected after inspecting this development artifact

Repository chronology shows the independent artifact was generated after revision `0ad4e96` and before revision `697344a`, which added the proposed primary hypothesis and endpoint documents. This is acceptable for hypothesis development only because the repository consistently labels the run as development evidence. The endpoint, eligibility rule, feature representation, and scenario family must be frozen before any confirmatory data exist; this artifact cannot later be reclassified as confirmatory support.

## Reviewer Interpretations

The following are interpretations, not arithmetic facts:

1. The close AP means are scientifically uninformative about policy-aware residual value because the policy-specific features are constant after filtering.
2. The broad 39/72 transition wording understates the constructed failure rate among actual transition histories while simultaneously risking overstatement of real-world prevalence.
3. Passing tests and checksum audits establish reproducibility of the implemented computation, not validity of the estimand.
4. The independent generator successfully breaks source-code coupling with the original generator, but it does not break the evaluator's shared conceptual dependence on current-policy service deficit.
5. The present negative/inconclusive result must be preserved. It should not be repaired by selecting favorable mechanisms, dropping adverse seeds, or redesigning scenarios after seeing scores and then treating them as untouched evidence.

## Contradictions To Prior Conclusions

- The development report's `0.3621` versus `0.3616` and interval are numerically correct only under an AP-zero convention that the pending protocol proposal explicitly rejects.
- The phrase "dimension-matched policy-aware versus raw" is nominally true by column count but false by effective varying dimension in the residual population.
- Claims that policy-aware features help wrong-employee sanction links are unsupported: the three policy-specific features are all zero, so no observed improvement can be attributed to policy context.
- The claim that 39 rare-legitimate transition cases were falsely alerted is source-consistent, but the stored artifact alone supports only 39 false alerts among 72 broadly labelled rare histories.
- The artifact auditor's successful status does not verify the AP or confidence interval that are central to the proposed endpoint.

## Limitations Of This Review

- No external or private employee data were available or used, so domain realism and external validity cannot be assessed.
- No supervisor decision, frozen protocol, or expert-adjudicated scenario set exists.
- The source-level 39/39 transition attribution required deterministic regeneration because the artifact omits per-record rare mechanisms and evidence.
- The alternative six-scenario interval is a diagnostic correction of eligibility handling, not a recommended confirmatory analysis; six units remain inadequate.
- Runtime reproducibility was checked in the current recorded dependency environment only through tests and deterministic recomputation, not a clean-room installation from the lock file.

## Final Assessment

The implementation is reproducible enough to expose its own failure modes, and the documentation commendably preserves an inconclusive result. Nevertheless, the proposed primary analysis is not methodologically ready. Before any freeze, the research design must use policy-aware residual features that can vary after deterministic-rule exclusion, define eligible scenarios before results exist, preserve per-record causal truth needed for audit, supply replicated scenario seeds, and make the artifact auditor recompute the primary statistic and inference from scores.

No decision is approved by this review. The final holdout must remain locked.
