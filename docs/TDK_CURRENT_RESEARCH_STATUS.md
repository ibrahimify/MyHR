# Current Research Status

Status date: 2026-11-25

The frozen v2 holdout was evaluated once at the revision identified by
repository tag `tdk-2026-revised-results`. The published artifact passed the
standalone manifest, authorization, provenance, bitemporal-evidence, metric,
and prediction audit. No seed was selected and the holdout was not rerun.

## Research Question

Under equal human-review capacity, does adding explicit workforce-policy
context improve the ranking of administrative errors over raw features without
increasing unnecessary alerts for unusual but lawful histories?

## Final Evaluation

The artifact contains 36 conditions with 30 seeds each, for 1,080 scenarios and
25,920 eligible evaluation histories.

| Primary residual comparison | Raw | Policy-aware |
| --- | ---: | ---: |
| Records reviewed | 3,240 | 3,240 |
| Injected errors found | 1,058/3,240 | 1,282/3,240 |
| False alerts among non-anomalies | 2,182/22,680 | 1,958/22,680 |
| Scenario-mean recall | 34.17% | 40.97% |
| Scenario-mean precision | 32.65% | 39.57% |
| Average precision | 46.08% | 52.72% |
| Rare-legitimate alerts | 248/2,160 | 229/2,160 |
| Ordinary-clean alerts | 1,934/20,520 | 1,729/20,520 |

Policy-aware minus raw scenario-mean recall was **+6.81 percentage points**
(95% CI +3.54 to +10.23, paired sign-flip `p approximately 0.000010`). This is the
predeclared primary endpoint.

The three predeclared secondary endpoints were:

| Endpoint | Difference | 95% CI | Holm-adjusted p | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Average precision | +6.64 pp | +3.57 to +9.73 pp | 0.00003 | Supported improvement |
| Rare-legitimate flagged rate | -0.88 pp | -3.33 to +1.53 pp | 0.199 | Benefit not established |
| Ordinary-clean flagged rate | -1.02 pp | -1.57 to -0.48 pp | 0.00003 | Supported reduction |

The complete rules-plus-ML workflow reviewed 6,010 records per method. The
policy-aware workflow found 2,402 anomalies and the raw workflow found 2,334;
rules alone found 2,023 while reviewing 4,899 records.

## Research Questions Answered

1. **Useful policy signal:** policy-aware Isolation Forest improved recall at
   equal capacity in the frozen synthetic holdout. Correct-policy features also
   outperformed wrong-policy and shuffled-policy controls, although synthetic
   construction still limits causal interpretation.
2. **Robustness:** the descriptive recall difference was positive in all 19
   predeclared policy, population, anomaly-mechanism, rare-pattern, and rate
   slices. These slice results do not replace the single confirmatory primary
   test.
3. **Rare lawful behavior:** pooled alerts were lower for policy-aware ML, but
   the paired confidence interval crossed zero and the adjusted test was not
   significant. The study therefore does not establish this proposed benefit.

## Interpretation Boundary

- Results apply to the frozen synthetic design, not real organizations or private employee data.
- Qualitative expert feedback supported continuing the study, but no case-level ratings or agreement statistic were collected.
- The five alternative scorers are exploratory sensitivity analyses; none was selected after holdout inspection.
- Anomaly scores support human review and never authorize automatic personnel action.
- The v1 attempt failed during scenario construction before artifact publication; its failed ledger remains preserved and v1 was never rerun.

## Evidence Map

| Need | Source |
| --- | --- |
| Final answers, counts, and limitations | [Frozen holdout results](results/TDK_HOLDOUT_RESULTS.md) |
| Reproducible result tables | [tables](tables/README.md) |
| Publication figures and checksums | [figures](figures/README.md), [result manifest](results/holdout_report_manifest.json) |
| Frozen analysis design | [Experiment protocol](TDK_EXPERIMENT_PROTOCOL.md) |
| Detailed chronology and preserved negative findings | [Archived research roadmap](archive/research-history/TDK_RESEARCH_ROADMAP_2026-11-25.md) |
| Literature and claim provenance | [Literature review](TDK_LITERATURE_REVIEW.md), [bibliography](TDK_REFERENCES.bib), [claim ledger](TDK_CLAIM_EVIDENCE_LEDGER.json) |
| Historical submitted manuscript | Tag `tdk-2026-submission` |

The submitted 2026 manuscript and dated audits are historical records. The
revised manuscript reports the later frozen holdout result.
