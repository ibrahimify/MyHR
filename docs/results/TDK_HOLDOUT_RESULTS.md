# Frozen Holdout Results

Status: independently audited frozen holdout. No post-hoc tuning or rerun was performed.

## Research Questions

**RQ1: Did policy-aware Isolation Forest improve detection at equal review capacity?**

Yes within this synthetic holdout. Scenario-mean recall increased from 34.2% to 41.0%; the paired difference was +6.8 percentage points (95% CI +3.5 to +10.2, sign-flip p approximately 0.000010). Both methods reviewed 3,240 residual records. Policy-aware ML found 1,282 anomalies and raw ML found 1,058.

**RQ2: Did the advantage persist across changed conditions?**

Descriptively, yes: policy-aware recall was higher in all 19 predeclared policy, population, anomaly-mechanism, rare-pattern, and rate slices. The slice differences ranged from +0.8% to +17.4%. These slice summaries are robustness diagnostics, not separately multiplicity-adjusted confirmatory tests. The exploratory effect also varied by scorer, from nearly zero for IQR to larger differences for Isolation Forest and Local Outlier Factor.

**RQ3: Did policy awareness reduce false alerts on rare legitimate behavior?**

Not conclusively. The scenario-mean rare-legitimate flagged-rate difference was -0.9% (95% CI -3.3% to +1.5%, Holm-adjusted p=0.199). The pooled counts were 229/2160 for policy-aware ML and 248/2160 for raw ML. The direction was favorable, but the evidence does not establish a rare-case benefit.

## Secondary Results

- Average precision improved by +6.6 percentage points (95% CI +3.6 to +9.7, Holm-adjusted p=0.00003).
- The ordinary-clean flagged rate decreased by -1.0 percentage points (95% CI -1.6 to -0.5, Holm-adjusted p=0.00003).
- The complete workflow found 2402 anomalies with policy-aware ML and 2334 with raw ML, from equal 6010-record queues containing policy-rule findings plus ML queue filling.
- Exploratory results for five scorers are reported without selecting a winner after holdout inspection.

## Interpretation Boundary

The result supports the value of policy-conditioned features within the frozen synthetic design. It does not prove performance on real employee data, establish that every gain is caused by correct policy knowledge, or justify automatic personnel decisions. Wrong-policy, shuffled-policy, ablation, and multi-model results remain necessary context. The expert review supplied qualitative support for continuing the study but did not produce case-level ratings or an agreement statistic.

## Evidence

- Artifact: verified v2 protected evaluation; exact identifier is recorded in `holdout_report_manifest.json`
- Frozen source revision: repository tag `tdk-2026-revised-results`
- Scenarios: 1,080 (36 conditions x 30 seeds)
- Evaluation histories: 25,920
- Manifest and authorization were independently verified before interpretation.
