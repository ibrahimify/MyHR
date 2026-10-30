# MyHR TDK Supervisor Brief

Review date: 30 October 2026

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status: **Supervisor-review draft. Development evidence only. Draft protocol. Final holdout locked.**

## Five-Minute Summary

MyHR is an offline employee-management and decision-support application. The TDK study asks whether explicit progression-policy context improves anomaly ranking at the same human review capacity, without increasing false alerts on legitimate exceptional histories.

The repository implements deterministic validation, statistical baselines, raw and policy-aware Isolation Forest representations, wrong- and shuffled-policy controls, feature ablations, synthetic generators, duplicate-candidate detection, write-once artifacts, checksum auditing, and paired scenario-level analysis. An external audit exposed invalid scenario semantics and an incorrect duplicate-pair universe. Those defects were repaired with regression tests before generating the current artifact.

The current corrected exploratory artifact is `4feea4508de1bb05`, generated from clean commit `56597d3`. Its audit status is verified and `holdout_accessed` is `false`. Across 12 scenarios it contains 864 eligible test histories, 108 anomalies, and 72 rare-legitimate histories. Deterministic policy checks produced 63 TP, 0 FP, and 45 FN, with 0/72 rare-legitimate histories flagged.

At identical additional review capacity, the scenario-level recall difference for policy-aware minus raw Isolation Forest was +0.0278, 95% CI [-0.0278, +0.1019], paired sign-flip p=0.6875. **No policy-aware advantage was demonstrated in this exploratory run.** The interval does not establish equivalence. The secondary AP difference was +0.0738 with unadjusted p=0.0122, but the all-comparison Holm-adjusted p was 1.0; it is not confirmatory.

## What The Audit Changed

- Historical `39/72` and intermediate `8/72` have different status. In artifact `e342bd4acf39b06b`, `deterministic_policy_rules` flagged 39/72 broadly labelled rare-legitimate test histories while `deterministic_rules` flagged 0/72. The old source constructs 30-month grandfathered and 24-month recognized-service promotions with narrative evidence, but the stored artifact omits employee-specific entitlement evidence and per-record realized mechanisms; `39/72` is therefore a constructed current-policy replay counterexample, not a prevalence estimate or artifact-supported mechanism-specific rate. The `8/72` false-positive interpretation is invalidated because that later generator created genuine contradictions.
- Duplicate metrics now use explicit pair-set membership. Exact methods use the complete partition-local pair universe; similarity evaluation uses its declared blocking universe. True negatives are no longer repaired by capping a wrong count.
- Correction histories reject duplicate identifiers, branched corrections, cross-type corrections, self-corrections, and cycles.
- Provenance covers the effective-state resolver, and runtime measurement no longer resets a caller-owned memory trace.
- Duplicate source and variant records share the same latent-person history and satisfy an adult-at-hire plausibility check.

## Scientific Boundaries

- The 12 scenarios are inspected development units and their definitions remain pending approval.
- The temporal model is partial. Policy identity and future-effective exclusion are implemented; employee-specific grandfathering and explicit knowledge-time versus review-time views are not frozen.
- All data are synthetic. Expert realism review has not begun.
- Duplicate detection is a separate task and current repaired code does not yet provide a protocol-scale benchmark result.
- No holdout has been generated, inspected, scored, or unlocked.
- No anomaly score may make a personnel decision automatically.

## Human Decisions Required

The attached decision sheet asks for approval, rejection, or modification of repaired scenario proposals, grandfathering semantics, temporal views, expert-review design, protocol-scale matrix, multiplicity family, and eventual freeze conditions. Approval of prior high-level methodology does not automatically approve these concrete definitions.

## Reproduce The Current Evidence

```powershell
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_4feea4508de1bb05
```

## Recommended Supervisor Outcome

Review the decision sheet and concrete scenario examples. Do not authorize the final holdout yet. After pending semantics, expert review, protocol-scale development and validation, dependencies, analysis, and source revision are frozen and independently audited, the holdout may be authorized for one run only.
