# MyHR TDK Supervisor Review Package

## Methodological Correction - 2026-10-18

The independent hostile review supersedes the earlier interpretation of the residual experiment. After deterministic policy findings are removed, all three policy-specific residual features are constant zero. The reported residual comparison therefore cannot test whether policy context improves anomaly ranking. It is a design failure, not evidence that policy-aware and raw models perform similarly.

## Proposed Research Claim

MyHR investigates whether explicit workforce-progression policy context improves unsupervised ranking of administrative anomalies that remain after deterministic validation. The system supports human review and does not automate personnel decisions.

## Implemented Research Infrastructure

- policy-aware and raw feature representations;
- deterministic administrative and policy checks;
- Isolation Forest, IQR, and z-score baselines;
- rule-negative and rules-plus-ML evaluations;
- wrong-policy, shuffled-policy, and ablation controls;
- validation-only thresholds and equal-capacity comparisons;
- paired intervals, permutation tests, Holm correction, and cost sensitivity;
- write-once artifacts with revisions, dependencies, seeds, source hashes, and checksums;
- an independent two-world simulator and separate truth ledger;
- an artifact auditor that independently recomputes counts, rates, average precision, paired differences, bootstrap intervals, sign-flip tests, and Holm adjustments from stored evidence.

## Established Development Findings

1. The original generator strongly favors policy-aware representations, but corrected rules explain 351/360 validation anomalies, leaving insufficient residual evidence.
2. The independent residual experiment cannot evaluate incremental policy value because deterministic filtering removes all variation from the policy-specific residual features.
3. The stored values, policy AP `0.3621` and raw AP `0.3616`, are reproducible under the implemented convention but have no valid policy-aware interpretation. Six of twelve scenarios have no residual positives and were assigned AP zero.
4. The deterministic checker flagged `39/72` rare-legitimate histories. Source regeneration attributes `39/39` realized policy-transition histories to this failure, but the existing stored artifact does not preserve per-record realized mechanisms.
5. Applying one current policy across history creates a reproducible specification failure for lawful grandfathering and recognized prior service. It does not estimate real-world prevalence.

These are development observations, not final claims.

## Approved Confirmatory Design - Implementation Pending

The research question is retained. The primary comparison is raw versus policy-aware residual ML after filtering only invariant contradictions. Both representations receive the same additional fixed review capacity over the same remaining records. The complete rules-plus-ML workflow is secondary.

Recall at fixed review capacity is primary. Precision, total false alerts, and rare-legitimate false-alert rates accompany it. AP is secondary. Zero-positive scenarios remain reported, are marked undefined for recall and AP, and are excluded from paired inference for those metrics under the frozen predeclared rule.

The approved design also requires bitemporal policy and fact history, two blinded complementary reviewers, and an independently specified repeated-seed holdout matrix with causal truth outside model inputs.

## Decisions Recorded And Remaining Work

- Implement and test the invariant-contradiction boundary.
- Implement equal fixed additional ML capacity and recall-primary analysis.
- Implement and test the bitemporal policy and evidence contract.
- Freeze the independent scenario matrix and zero-positive handling.
- Record the two reviewers, qualifications, sampling, agreement measure, and adjudication process.
- Freeze dependencies, analysis, source revision, and write-once configuration before requesting holdout authorization.

## Reproduction

```powershell
python scripts/run_tdk_protocol_experiment.py --run-purpose development --scenario-count 30 --employee-count 600
python scripts/run_tdk_protocol_experiment.py --run-purpose validation --scenario-count 30 --employee-count 600
python scripts/run_tdk_independent_development.py --employee-count 360
python scripts/audit_tdk_protocol_artifact.py <artifact-directory>
```

The `holdout` run purpose fails by design. No holdout scenario or seed range exists.

## Current Readiness

- Implementation mechanics: high confidence within automated coverage.
- Internal validity of the central residual comparison: insufficient because the policy-specific signal is structurally absent.
- Statistical confidence in policy-aware superiority: not estimable from the current residual experiment.
- External generalization: not established.
- Protocol freeze: not ready until the approved design is implemented and independently verified.
- Publication claim: not ready.
