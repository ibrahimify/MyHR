# TDK Protocol V2 Development and Validation Report

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status: **Development and validation diagnostics only. The holdout remains locked.**

## Purpose

This report checks whether the draft v2 protocol is implemented correctly and whether its assumptions are reasonable enough for supervisor review. It does not provide final paper evidence. No result below was used to unlock, generate, inspect, or evaluate a holdout scenario.

## Verified Runs

| Purpose | Artifact | Scenarios | Employees per scenario | Source revision |
| --- | --- | ---: | ---: | --- |
| Development | `development_df2b4d0905d31a33` | 30 | 600 | `20c21dc80aa80011a02fd0e29d23b8bb67f189d4` |
| Validation | `validation_7e1336910c16aea8` | 30 | 600 | `20c21dc80aa80011a02fd0e29d23b8bb67f189d4` |

Both runs recorded a clean Git worktree, `holdout_accessed: false`, exact commands, package versions, source hashes, and separate dataset, split, and model seeds. All nine recorded file hashes in each manifest were independently recomputed and matched.

The development and validation seed ranges are disjoint. Each run includes three policy profiles, three population profiles, three anomaly mechanisms, three rare-legitimate patterns, three anomaly rates, and three rare-legitimate rates. The first 27 scenarios cover every policy, population, and anomaly-mechanism combination; the remaining three are predeclared repeats.

## Evaluation Denominators

Each run evaluates 3,600 test records across 30 scenarios:

- 360 genuine anomalies;
- 3,240 non-anomalies;
- 200 rare but legitimate histories;
- 3,040 ordinary clean histories.

At the fixed 10% review budget, every Isolation Forest and rules-plus-Isolation-Forest representation raises exactly 12 alerts per scenario, or 360 alerts per run. This makes their fixed-budget comparisons directly comparable.

## Main Results

The table reports mean scenario metrics at the fixed 10% review budget. Brackets are 95% bootstrap confidence intervals over scenario means.

| Run | Method | F1 | PR-AUC | Rare legitimate flagged | Ordinary clean flagged |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | Raw Isolation Forest | 0.510 [0.474, 0.547] | 0.565 [0.529, 0.600] | 30/200 | 142/3,040 |
| Development | Policy-aware Isolation Forest | 0.715 [0.674, 0.757] | 0.830 [0.809, 0.853] | 4/200 | 93/3,040 |
| Development | Rules + raw Isolation Forest | 0.835 [0.804, 0.868] | 0.984 [0.976, 0.991] | 8/200 | 49/3,040 |
| Development | Rules + policy-aware Isolation Forest | 0.852 [0.814, 0.890] | 0.997 [0.994, 0.999] | 0/200 | 51/3,040 |
| Validation | Raw Isolation Forest | 0.481 [0.433, 0.527] | 0.546 [0.498, 0.594] | 42/200 | 140/3,040 |
| Validation | Policy-aware Isolation Forest | 0.717 [0.675, 0.759] | 0.838 [0.810, 0.867] | 8/200 | 89/3,040 |
| Validation | Rules + raw Isolation Forest | 0.814 [0.781, 0.845] | 0.975 [0.959, 0.987] | 13/200 | 51/3,040 |
| Validation | Rules + policy-aware Isolation Forest | 0.840 [0.804, 0.878] | 0.990 [0.980, 0.997] | 5/200 | 50/3,040 |

The exact policy-rules-only baseline achieved validation precision 1.000, recall 0.789, and F1 0.880, with no false positives. This is a strong baseline and prevents attributing deterministic policy violations to machine learning.

At equal review budget on validation scenarios, policy-aware versus raw Isolation Forest produced:

- mean F1 difference `+0.236`, 95% paired bootstrap CI `[+0.206, +0.267]`, sign-flip `p = 0.00001`;
- mean PR-AUC difference `+0.292`, 95% CI `[+0.260, +0.323]`, sign-flip `p = 0.00001`;
- mean rare-legitimate flag-rate difference `-0.186`.

After exact policy rules were applied first, policy-aware versus raw Isolation Forest produced a smaller validation gain:

- mean F1 difference `+0.026`, 95% CI `[+0.009, +0.045]`, sign-flip `p = 0.01562`;
- mean PR-AUC difference `+0.015`, 95% CI `[+0.008, +0.023]`, sign-flip `p = 0.00011`;
- mean rare-legitimate flag-rate difference `-0.044`.

This smaller cascade result is the relevant evidence against the claim that the model merely rediscovers explicit rules. It suggests some incremental ranking value, but most detectable policy violations are already handled well by deterministic checks.

## Controls and Ablations

On validation scenarios at equal review budget:

| Representation | F1 | PR-AUC | Rare legitimate flag rate |
| --- | ---: | ---: | ---: |
| Raw matched | 0.481 | 0.546 | 0.219 |
| Raw without commendation count | 0.515 | 0.595 | 0.129 |
| Raw interval ablation | 0.527 | 0.608 | 0.114 |
| Policy matched | 0.717 | 0.838 | 0.034 |
| Policy deficit-months ablation | 0.658 | 0.784 | 0.032 |
| Policy unexplained-signal ablation | 0.704 | 0.823 | 0.029 |
| Wrong-policy control | 0.687 | 0.800 | 0.064 |
| Shuffled-policy control | 0.660 | 0.746 | 0.142 |

Correct policy assignment outperformed wrong and shuffled policy controls. Removing key policy residuals reduced performance. Raw ablations improving over the full raw representation is a useful negative finding: some raw variables expose legitimate exceptional behavior as statistical outliers and harm the raw detector.

## Robustness

For fixed-budget policy-minus-raw comparisons, all 18 reported slices had non-negative F1 and PR-AUC differences in both development and validation. Slices cover policy profile, population profile, anomaly mechanism, rare pattern, anomaly prevalence, and rare-legitimate prevalence.

This is evidence of stability within the declared synthetic matrix, not proof of external validity. The scenario families remain finite and are produced by one synthetic generator design.

Per-class results also show why a hybrid system is necessary. On validation scenarios, policy-aware Isolation Forest recalled all injected unexplained frequent-promotion cases on average, while raw Isolation Forest recalled 0.064. Exact policy rules recalled those cases perfectly but detected only 0.178 of excessive-sanction anomalies. The policy-aware cascade increased excessive-sanction recall from 0.542 for the raw cascade to 0.647, while deterministic checks retained their strength on date and interval errors.

## Operational Utility

The value conclusion depends on the cost assumptions. On validation scenarios, the policy-aware cascade had lower estimated cost than the raw cascade under all three declared cost profiles. Compared with exact policy rules alone, the policy-aware cascade was better when missed-error cost was medium or high, but worse under the lowest missed-error cost profile because additional reviews were not worth their smaller recall gain.

Therefore the experiment does not support a universal claim that more ML alerts are always valuable. It supports presenting a configurable review budget and measuring the tradeoff for the intended organization.

## Answers to the Three Audit Questions

1. **Is the model learning more than the construction rules?** Tentatively yes within this synthetic matrix. Exact policy rules are already strong, but the policy-aware cascade still improves paired F1 and PR-AUC and detects more non-policy anomalies. The gain is modest after rules, so the paper must describe ML as supplementary ranking, not a replacement for deterministic validation.
2. **Does the advantage survive changed data and policies?** It survives the independent development and validation seed ranges and every reported slice in the current matrix. It has not yet been shown on a separately implemented generator, real organizational data, or the locked holdout.
3. **Is reducing rare-legitimate false positives worth the tradeoff?** It clearly reduces unnecessary escalation at an equal review budget. Whether this justifies additional ML reviews depends on the missed-error and review-cost ratio, as shown by the sensitivity analysis.

## Remaining Weaknesses

- All current evidence is synthetic.
- Generator and detector implementations are separate, but they describe the same domain and may still share conceptual assumptions.
- A holdout generator implemented independently from the current detector is not yet defined or reviewed.
- The scenario matrix does not represent every organization, data-quality failure, or policy change.
- The utility costs are sensitivity assumptions, not measured organizational costs.
- Duplicate detection is a separate research task and is not part of these progression results.
- The optional explanation usability study has not been performed.

## Readiness Decision

The implementation is ready for **supervisor protocol review**. It is not ready for a final research claim, protocol freeze, or holdout execution. Supervisor review should focus on the scenario assumptions, the independent holdout-generation plan, acceptable operational cost profiles, and whether an anonymized or expert-reviewed external dataset can be added.

