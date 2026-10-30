# MyHR TDK Supervisor Brief

Review date: 30 October 2026

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status: **Supervisor-review draft. Development evidence only. Draft protocol. Final holdout locked.**

## Five-Minute Summary

MyHR is an offline employee-management and decision-support application. The TDK study asks whether explicit progression-policy context improves anomaly ranking at the same human review capacity, without increasing false alerts on legitimate exceptional histories.

The repository implements deterministic validation, statistical baselines, raw and policy-aware Isolation Forest representations, wrong- and shuffled-policy controls, feature ablations, synthetic generators, duplicate-candidate detection, write-once artifacts, checksum auditing, and paired scenario-level analysis. An external audit exposed invalid scenario semantics and an incorrect duplicate-pair universe. Those defects were repaired with regression tests before generating the current artifact.

The current corrected exploratory artifact is `4feea4508de1bb05`, generated from clean commit `56597d3`. Its audit status is verified and `holdout_accessed` is `false`. Across 12 scenarios it contains 864 eligible test histories, 108 anomalies, and 72 generated rare-legitimate labels. Deterministic policy checks produced 63 TP, 0 FP, and 45 FN, with 0/72 generated rare labels flagged. That denominator includes 24 grandfathering labels without independently established employee-specific entitlement.

At identical additional review capacity, the scenario-level recall difference for policy-aware minus raw Isolation Forest was +0.0278, 95% CI [-0.0278, +0.1019], paired sign-flip p=0.6875. The nominal top-10% rule uses ceiling rounding, so each model reviewed 8/72 records per scenario, or 96/864 (11.11%) overall. **No policy-aware advantage was demonstrated in this exploratory run.** The interval does not establish equivalence. The secondary AP difference was +0.0738 with unadjusted p=0.0122, but the all-comparison Holm-adjusted p was 1.0; it is not confirmatory.

The adverse controls are more restrictive than the headline comparison: wrong-policy context selected exactly the same 96 records as policy-matched context and produced the same 39 TP/57 FP. Each of three single-policy-feature ablations produced 42 TP/54 FP. The observed difference from raw features therefore cannot be attributed to correct policy knowledge, and the full policy representation underperformed its ablations in this inspected run.

## What The Audit Changed

- Historical `39/72` and intermediate `8/72` have different status. In artifact `e342bd4acf39b06b`, `deterministic_policy_rules` flagged 39/72 broadly labelled rare-legitimate test histories while `deterministic_rules` flagged 0/72. The old source constructs 30-month grandfathered and 24-month recognized-service promotions with narrative evidence, but the stored artifact omits employee-specific entitlement evidence and per-record realized mechanisms; `39/72` is therefore a constructed current-policy replay counterexample, not a prevalence estimate or artifact-supported mechanism-specific rate. The `8/72` false-positive interpretation is invalidated because that later generator created genuine contradictions.
- Those historical artifacts predate the strengthened provenance schema and do not pass the current auditor. The supervisor package includes immutable metadata and metric extracts for the audit-history figures, while only the repaired current artifact is described as currently verified.
- Duplicate metrics now use explicit pair-set membership. Exact methods use the complete partition-local pair universe; similarity evaluation uses its declared blocking universe. True negatives are no longer repaired by capping a wrong count.
- Correction histories reject duplicate identifiers, branched corrections, cross-type corrections, self-corrections, and cycles.
- Provenance covers the effective-state resolver, and runtime measurement no longer resets a caller-owned memory trace.
- Duplicate source and variant records share the same latent-person history. All three synthetic generators now enforce and test a minimum generated hire age of 18 years.

## Decisions Recorded On 30 October

- Lawful correction and transition cases are accepted only when explicit
  employee and population eligibility checks pass. Stable-administration and
  merger/migration populations may host all five rare patterns; rapid expansion
  excludes legacy policy transition under the current hire window. The exact
  balanced protocol-scale cell allocation is not frozen.
- Grandfathering requires entitlement evidence linked to employee, policy
  ID/version, relevant event, evidence reference, and knowledge time.
- `known_then` and `later_review` are separate required temporal views.
- Protocol-scale included conditions use 30 independent seeds unless a written
  pre-run justification approves another count. Zero-positive scenarios remain
  reported; recall and AP are undefined for their metric-specific inference.
- Fixed-capacity recall is primary. Holm adjustment covers the three secondary
  paired comparisons: AP, rare-legitimate false-alert rate, and
  ordinary-legitimate false-alert rate.
- The realism-review procedure is fixed at 48 stratified cases and two blinded
  complementary reviewers, with raw agreement, unweighted Cohen's kappa, and
  evidence-based adjudication. The two actual reviewers are not yet nominated.
- Protocol freeze and one holdout run are explicitly withheld.

## Scientific Boundaries

- The 12 scenarios are inspected development units. Their lawful compatibility
  rules are approved, but their frequency allocation is not the frozen
  protocol-scale matrix.
- Employee-linked entitlement and explicit decision-time/later-review views now
  exist in development code and tests. They have not yet been exercised and
  independently verified in a protocol-scale artifact.
- All data are synthetic. Expert realism review has not begun.
- Duplicate detection is a separate task and current repaired code does not yet provide a protocol-scale benchmark result.
- No holdout has been generated, inspected, scored, or unlocked.
- No anomaly score may make a personnel decision automatically.

## Human Inputs Still Required

1. Nominate the HR-policy reviewer and information-systems reviewer and record
   their qualifications.
2. Review concrete generated examples and the proposed balanced compatible-cell
   matrix before it is frozen.
3. After protocol-scale development, validation, expert review, dependency lock,
   and independent audit, sign or reject the separate protocol-freeze request.

No current decision authorizes holdout generation or evaluation.

## Reproduce The Current Evidence

```powershell
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_4feea4508de1bb05
```

## Recommended Supervisor Outcome

Nominate the two reviewers and review the concrete scenario examples. Do not
authorize the final holdout yet. After the approved semantics are verified in
protocol-scale development and validation, the expert review is complete, and
dependencies, analysis, and source revision are frozen and independently
audited, a separate human decision may authorize one holdout run only.
