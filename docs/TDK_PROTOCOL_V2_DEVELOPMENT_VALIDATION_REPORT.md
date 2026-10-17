# TDK Protocol V2 Development And Validation Report

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

## Superseding Methodological Correction - 2026-10-18

The 2026-10-17 independent review found that deterministic filtering forces all three policy-specific residual features to zero. The residual AP comparison below is retained as development history, but it cannot test incremental policy context. Six of twelve independent scenarios also contain no residual positives and were assigned AP zero under the implemented convention. No residual superiority, equivalence, or mechanism-specific policy effect may be inferred from these values.

Status: **Development and validation diagnostics only. The holdout remains locked.**

## Supersession Notice

The v2.1 artifacts and earlier report are superseded. They capped the rules-plus-ML cascade at 10% even when deterministic findings exceeded that capacity, dropping 21 development and 18 validation rule findings. They also labelled average precision as PR-AUC.

The current implementation retains every deterministic finding, uses ML only to fill unused nominal capacity, reports average precision correctly, evaluates all completed promotions, and includes a rule-negative residual experiment.

## Verified Artifacts

| Purpose | Artifact | Scenarios | Test records | Source revision |
| --- | --- | ---: | ---: | --- |
| Development | `development_5f0f99d3ffe8dc9e` | 30 | 3,600 | `31d3e3e` |
| Validation | `validation_c5878ca7b927ccd2` | 30 | 3,600 | `31d3e3e` |
| Independent stress test | `independent_development_e342bd4acf39b06b` | 12 | 864 | `0ad4e96` |

All artifacts report `holdout_accessed: false`. Their manifests, historical source hashes, predictions, confusion counts, rates, and aggregate denominators were independently recomputed by `scripts/audit_tdk_protocol_artifact.py`.

## Corrected Validation Result

The original scenario family contains 360 labelled anomalies, 3,240 non-anomalies, 200 rare-legitimate histories, and 3,040 ordinary-clean histories in the validation test splits.

| Method | Alerts | TP | FP | FN | Mean F1 | Mean AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic policy rules | 351 | 351 | 0 | 9 | 0.986 | 0.977 |
| Rules + raw IF | 408 | 357 | 51 | 3 | 0.907 | 0.998 |
| Rules + policy-aware IF | 408 | 358 | 50 | 2 | 0.910 | 1.000 |

Rules alone now detect 351/360 anomalies because evaluating every promotion reveals that many injected excessive-sanction histories also become policy service violations. This is a generator interaction, not evidence that rules universally achieve 97.5% recall.

The policy-aware cascade finds one more anomaly and one fewer false alert than the raw cascade at the same capacity. The paired mean AP difference is `+0.0016`, 95% bootstrap interval `[0.0000, 0.0041]`, sign-flip `p = 0.25`, and Holm-adjusted exploratory `p = 1.0`. This does not establish a meaningful cascade advantage.

## Rule-Negative Residual Result

Removing every record flagged by deterministic policy checks leaves only 9 anomalies among 3,249 validation records.

| Residual method, 10% budget | Alerts | TP | FP | FN | Mean F1 | Mean AP | Rare legitimate flagged |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw IF | 340 | 9 | 331 | 0 | 0.047 | 0.161 | 59/200 |
| Policy-aware IF | 340 | 9 | 331 | 0 | 0.047 | 0.181 | 27/200 |

The paired AP difference is `+0.0194`, 95% interval `[-0.0417, 0.0889]`, sign-flip `p = 0.75`, and Holm-adjusted `p = 1.0`. Policy context changes which false alerts are raised but does not improve total precision or workload: 32 rare-legitimate flags are avoided while 32 additional ordinary-clean records are flagged.

This original generator contains too few rule-negative anomalies to estimate incremental ML value convincingly.

## Independent Development Stress Test

The independent simulator uses three population families, four causal error mechanisms, policy transitions, separate truth and observation ledgers, and no imports from the MyHR detector, policy engine, features, or original generator.

Across 12 test scenarios it produced 108 anomalies and 72 rare-legitimate histories. Deterministic rules raised 105 alerts, including 39 false alerts on rare legitimate policy-transition cases. This demonstrates that a single-current-policy rule engine is not reliable when grandfathering or recognized prior service applies.

Among the 759 rule-negative records, 42 anomalies remained:

| Residual method, 10% budget | Alerts | TP | FP | FN | Mean F1 | Mean AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw IF | 81 | 26 | 55 | 16 | 0.304 | 0.3616 |
| Policy-aware IF | 81 | 25 | 56 | 17 | 0.298 | 0.3621 |

The stored paired AP difference is `+0.0005`, 95% interval `[-0.1173, 0.1079]`, sign-flip `p = 1.0`, and Holm-adjusted `p = 1.0`. These values are arithmetically reproducible but scientifically vacuous for policy context because the policy-specific features are constant. Apparent mechanism differences cannot be attributed to policy information.

## Conclusions Supported Today

- Deterministic policy checks are valuable for explicit inconsistencies, but they require correct policy-version context.
- Policy-aware features strongly fit the original generator, which is evidence of generator-detector coupling rather than transferable advantage.
- The independent residual design does not contain varying policy-specific signal after rule filtering, so it cannot establish similarity, superiority, or inferiority.
- Reducing rare-legitimate alerts can merely move false alerts to ordinary-clean records when total capacity is fixed.
- Isolation Forest is a supplementary triage method, not a replacement for deterministic validation or human review.

## Remaining Limitations

- All data remain synthetic.
- Independent scenarios are development stress tests, not a locked holdout.
- The independent simulator covers only four causal error mechanisms and three populations.
- Policy version, jurisdiction, transfer, and recognized-service evidence are not first-class detector inputs.
- Current validation thresholds are selected separately within small labelled scenarios; deployment calibration is unresolved.
- Operational costs are sensitivity assumptions rather than measured organizational costs.
- Duplicate detection and explanation usability remain separate, secondary studies.

## Readiness

Implementation confidence is high for the tested mechanics and artifact integrity. Internal validity of the central residual comparison is insufficient because the intended policy signal is absent. The work is ready for supervisor methodological redesign, not protocol freeze, holdout execution, or publication claims.
