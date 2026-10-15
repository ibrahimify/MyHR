# Independent Methodology Review - 2026-10-16

## Review Question

What could make the present conclusion wrong, and what is the strongest permissible test before holdout access?

## Confirmed Corrections

1. The old fixed-budget cascade dropped mandatory deterministic findings in 10/30 validation scenarios. The corrected cascade keeps all rules and uses ML only to fill remaining nominal capacity.
2. The reported PR-AUC was `average_precision_score`. Current artifacts label it average precision (AP).
3. Policy checks previously evaluated only the latest promotion. All completed promotions are now assessed.
4. Fixed-budget score ties previously fell back to row order. Current selection uses a stable, label-independent employee-ID hash.
5. Operational review cost is now charged to every alert rather than only false alerts.
6. Exploratory sign-flip tests now include Holm correction across the complete generated comparison family.
7. A target-FPR point that cannot be achieved without discarding mandatory rules is reported as infeasible.

## Main Threats To Validity

- **Conceptual circularity:** the original generator creates promotion cases from the same service-credit-delay concepts reconstructed by policy features.
- **Generator side effects:** injected sanctions can make otherwise separate histories violate promotion policy.
- **Sparse residual signal:** after corrected rules, the original validation set has 9 rule-negative anomalies across 30 scenarios.
- **Policy-version omission:** current detection applies one policy to a whole history and can falsely flag lawful grandfathering or recognized service.
- **Threshold realism:** per-scenario threshold selection assumes labelled local anomalies and can overfit small validation partitions.
- **Factor confounding:** most original policy, population, mechanism, and seed combinations occur once.
- **Synthetic-only evidence:** no authorized real or expert-adjudicated external dataset is available.

## Proposed Primary Hypothesis

> Among employee histories not flagged by deterministic policy checks, policy-aware Isolation Forest provides better anomaly ranking than a dimension-matched policy-agnostic Isolation Forest on independently generated, locked scenarios containing predeclared residual administrative-error mechanisms.

## Proposed Primary Endpoint

Paired scenario-level difference in average precision:

`AP(policy-aware, rule-negative records) - AP(raw, rule-negative records)`

Use one two-sided paired permutation test and a 95% scenario-clustered bootstrap interval. A positive conclusion requires the interval's lower bound to exceed zero. The primary scenario family must contain independently specified residual mechanisms with positive cases in every scenario; explicit rule-violation families remain secondary.

This hypothesis and endpoint are proposals only. Supervisor approval is required before protocol freeze.

## Secondary Outcomes

- recall and precision at a fixed residual review budget;
- rare-legitimate and ordinary-clean flag rates, always together;
- total alerts, false alerts, and missed anomalies with denominators;
- per-mechanism recall and AP;
- rules-only and rules-plus-ML cost sensitivity;
- wrong-policy, shuffled-policy, and feature-ablation controls.

All secondary significance tests remain exploratory and receive Holm correction.

## Independent Review Roles

- Methodology review found cascade truncation, AP mislabelling, multiplicity, and threshold-validity risks.
- ML/statistics review found latest-promotion-only validation, residual-isolation weakness, tied baselines, and sparse residual positives.
- Scenario-design review specified a latent administrative world, observation failures, separate truth ledger, policy transitions, and blinded expert review.
- Replication review verified historical artifacts, denominators, checksums, source hashes, holdout absence, and corrected cascade arithmetic.

No reviewer accessed a holdout or modified evidence.
