# MyHR TDK Supervisor Review Package

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
- an artifact auditor that recomputes saved results.

## Established Development Findings

1. The original generator strongly favors policy-aware representations, but corrected rules explain 351/360 validation anomalies, leaving insufficient residual evidence.
2. In the independent 12-scenario test, policy-aware residual AP is `0.3621` and raw residual AP is `0.3616`; the paired interval includes advantage and disadvantage.
3. Policy context helps some mechanisms and hurts others.
4. Rare-legitimate alert reduction can be offset by ordinary-clean false alerts.
5. Applying one current policy across history creates false findings for lawful grandfathering and recognized prior service.

These are development observations, not final claims.

## Proposed Confirmatory Design

Primary hypothesis: among rule-negative histories in independently generated residual-error scenarios, policy-aware Isolation Forest ranks true errors better than dimension-matched raw Isolation Forest.

Primary endpoint: paired scenario-level average-precision difference, with a two-sided paired permutation test and 95% scenario-clustered bootstrap interval. Success requires a lower confidence bound above zero.

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
- Internal validity: moderate; key defects are corrected, but synthetic assumptions remain.
- Statistical confidence in policy-aware superiority: low; independent evidence is inconclusive.
- External generalization: not established.
- Protocol freeze: not ready until the decisions above are resolved.
- Publication claim: not ready.
