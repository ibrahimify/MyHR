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

## Candidate Confirmatory Design - Pending Human Approval

The research question may be retained, but the current residual representation and scenarios must not be reused as a confirmatory design. The supervisor must choose whether to redesign the residual task, adopt non-overlapping policy-context features, or make an end-to-end rules-plus-ML workflow the primary estimand.

If AP remains primary, eligible scenario families must be defined before generation and must contain residual positives by construction. Zero-positive scenarios must never be selected or removed after results are inspected. Fixed-capacity outcomes remain operational secondary evidence with complete denominators.

Secondary outcomes include fixed-budget recall, precision, rare-legitimate and ordinary-clean flag rates, workload, per-mechanism behavior, and cost sensitivity with Holm correction.

## Decisions Requested

- Approve or revise the primary hypothesis and endpoint.
- Approve mandatory rules with a nominal 10% capacity floor.
- Review independent scenarios for organizational realism.
- Approve policy version, jurisdiction, recognized service, and effective-versus-recorded dates.
- Nominate two reviewers for blinded scenario plausibility assessment, if feasible.
- Confirm whether authorized aggregate ranges or anonymized external data can be used.

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
- Protocol freeze: not ready until the decisions above are resolved.
- Publication claim: not ready.
