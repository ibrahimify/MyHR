# MyHR TDK Supervisor Brief

Review date: 30 October 2026

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status: **Supervisor review draft. Development evidence only. Draft protocol. Final holdout locked.**

## Five-Minute Summary

MyHR is an offline employee-management and decision-support application with formal promotion, commendation, sanction, annual-increment, performance-review, reporting, and audit workflows. The TDK research asks whether adding explicit progression-policy context to anomaly-detection features reduces unnecessary alerts on legitimate exceptional histories without hiding genuine administrative errors.

The research infrastructure is substantially implemented and tested: deterministic validation, raw and policy-aware features, IQR and z-score baselines, Isolation Forest, validation-only thresholds, equal-review-budget comparisons, wrong-policy and shuffled-policy controls, feature ablations, synthetic and independent scenario generators, duplicate-candidate detection, write-once artifacts, checksum manifests, citation provenance, and independent audits.

The current experiment does **not** establish that policy-aware Isolation Forest is better. This is not being hidden or repaired through favorable tuning. The independent review found that the deterministic filter removes every case with a positive policy deficit, leaving all three policy-specific residual features constant zero. The residual comparison therefore has no policy signal and cannot test the central hypothesis.

The strongest current engineering finding is historical-policy handling. Deterministic current-policy replay flagged `39/72` constructed rare-legitimate histories. Source regeneration associates the flagged histories with realized policy transitions, but the immutable artifact does not preserve that per-record mechanism. The directly auditable claim remains `39/72`; the result demonstrates a specification failure, not real-world prevalence.

## Research Questions

1. Does explicit policy context improve anomaly ranking beyond raw administrative features and deterministic checks?
2. Does any advantage remain across populations, anomaly mechanisms, policies, prevalence levels, and seeds?
3. At equal review capacity, can policy context reduce false alerts on legitimate exceptional histories without missing genuine errors or moving false alerts elsewhere?

## Implemented Work

- Formal progression arithmetic shared with the application.
- Policy-engine parity and golden-history tests.
- Deterministic checks with explainable findings.
- Raw, policy-aware, wrong-policy, shuffled-policy, and ablation representations.
- IQR, z-score, and Isolation Forest comparisons.
- Validation-selected thresholds and fixed-capacity evaluation.
- Original and independently implemented synthetic scenario families.
- Paired scenario analysis, intervals, sign-flip tests, workload measures, and sensitivity analysis.
- Separate duplicate-record candidate experiment.
- Write-once artifacts containing revision, dependencies, seeds, predictions, metrics, and checksums.
- Independent result and citation audits.
- GitHub Actions regression CI and secret scanning.

## Verified Development Findings

| Finding | Verified evidence | Correct interpretation |
| --- | --- | --- |
| Validation rules found `351/360` generated anomalies | 30-scenario validation artifact | Strong generator interaction; not general real-world recall |
| Independent residual set contains 759 histories and 42 anomalies | Stored predictions and independent audit | Correct denominator for residual comparison |
| Raw IF: 81 alerts, 26 TP, 55 FP, 16 FN | Stored predictions | Development diagnostic only |
| Policy-labelled IF: 81 alerts, 25 TP, 56 FP, 17 FN | Stored predictions | Development diagnostic only |
| AP `0.3616` versus `0.3621` | Independently recomputed | Scientifically vacuous because policy features are constant |
| Six of twelve scenarios have no residual positives | Scenario metrics | Approved future rule marks recall and AP undefined and excludes those scenarios from paired inference for those metrics; implementation and freeze remain pending |
| Deterministic checks flagged `39/72` rare-legitimate histories | Stored predictions | Constructed historical-policy failure, not prevalence |

## What Must Not Be Concluded

- Policy-aware Isolation Forest does not currently outperform, tie, or underperform raw Isolation Forest in a scientifically interpretable comparison.
- The current AP difference is not a meaningful null result.
- The synthetic rates do not estimate organizational prevalence.
- The preliminary duplicate experiment is not a validated entity-resolution benchmark.
- No holdout or confirmatory result exists.
- No anomaly score may trigger an automatic personnel decision or record merge.

## Decisions Recorded

The supervisor answers relayed on 29 October 2026 record these choices:

1. primary estimand and residual redesign;
2. primary endpoint and zero-positive scenarios;
3. deterministic-rule and equal-ML review capacity;
4. effective-time and recorded-time historical policy model;
5. blinded expert-realism review;
6. conceptually independent holdout design.

The approved choices are documented in `TDK_SUPERVISOR_DECISIONS_2026-10-29.md`. Implementation, protocol freeze, and holdout access remain pending and cannot be approved by an AI agent.

## Paper Status

An English supervisor-review manuscript has been prepared using the official 30-35-page main-text requirements. Introduction, related work, formal model, methods, implementation, development results, limitations, conclusion, references, and appendices are drafted. The methodology is approved for implementation, but confirmatory wording and any final result remain blocked until the implementation is verified and the protocol is separately frozen.

## Verification

```powershell
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python scripts/audit_tdk_protocol_artifact.py research_outputs/protocol_v2_verified/validation_c5878ca7b927ccd2
python scripts/audit_tdk_protocol_artifact.py research_outputs/independent_development/independent_development_e342bd4acf39b06b
```

Do not run a holdout command. The implementation intentionally refuses that run purpose.

## Next Review Outcome

Implement only the six recorded methodology decisions, rerun development and validation, and present the verified redesign for a separate protocol-freeze decision. Execute the final holdout exactly once only after that dated freeze approval. Until then, retain the current work as development evidence and do not claim confirmatory superiority.

