# Current Research Status

## Holdout v1 failure and v2 repair - 24 November 2026

Protocol v1 was frozen at revision `dda874e` and its one authorized attempt began
on 24 November. It stopped at scenario 43 before artifact publication because
truth-label allocation selected overlapping error candidates before reserving
the constrained rare-case candidates. The external ledger records `failed`; no
v1 result artifact exists and no model outcome was inspected.

The v2 repair allocates exact disjoint candidate sets independent of category
order and uses a new seed family and ledger. The factor matrix, features,
endpoints, thresholds, review capacity, models, and analysis remain unchanged.
V2 is a freeze candidate and has not been generated or scored. See
`TDK_HOLDOUT_V1_FAILURE_2026-11-24.md`.

Status date: 2026-11-23

Research question: under equal human-review capacity, does adding explicit
workforce-policy context improve the ranking of administrative errors over raw
features without increasing unnecessary alerts for lawful unusual histories?

## Current Evidence

The current claim-bearing evidence is independent synthetic validation artifact
`c5b0723409c2394e`. It contains 36 conditions, 30 seeds per condition, and 1,080
scenarios. Raw and policy-aware Isolation Forest scored the same 77,760
invariant-negative evaluation histories and each received 8,640 review slots.
The artifact was generated from revision `dc055c3`, passed its 20-file manifest
and standalone audit, and records `holdout_accessed: false`.

| Fixed-capacity result | Raw | Policy-aware |
| --- | ---: | ---: |
| Injected errors found | 3,348/9,720 | 3,800/9,720 |
| False alerts | 5,292/68,040 | 4,840/68,040 |
| Rare-legitimate alerts | 607/5,400 | 513/5,400 |
| Ordinary-clean alerts | 4,685/62,640 | 4,327/62,640 |

The condition-balanced mean recall difference is +0.0438, with a 95%
hierarchical interval [+0.0177, +0.0698] and Monte Carlo sign-flip
`p approximately 0.000010`. Average Precision differs by +0.0487, interval
[+0.0206, +0.0774], with Holm-adjusted
`p approximately 0.000030`.

The rare-legitimate rate difference is -0.0167, but its hierarchical interval
[-0.0431, +0.0090] crosses zero while the adjusted sign-flip p-value is
0.000490. These summaries respond differently to condition heterogeneity. Both
are retained, and the conservative conclusion is that a stable reduction for
rare but lawful cases is not established.

## Supported Conclusion

Within the independent synthetic matrix, policy-aware features improved the
mean ranking recall of the predeclared Isolation Forest comparison over the
tested raw representation at the same review capacity. This does not establish
that the effect will transfer to real organisations, unseen policy systems, or
private employee data. The five-scorer extension remains exploratory, and
wrong-policy controls limit a simple causal interpretation.

## Open Scientific Gates

- The data are synthetic. Two independent academic experts provided a
  qualitative realism review, but no case-level ratings or agreement analysis
  exists; external validity therefore remains unestablished.
- Protocol v1 was consumed by a failed technical attempt without a result.
- Protocol v2 remains locked pending repair verification, freeze, and a new
  exact-revision one-time authorization.
- No result authorizes automatic personnel action or post-validation model
  selection.

## Evidence Map

| Need | Source |
| --- | --- |
| Exact validation counts, intervals, and interpretation | [Development and validation report](TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md) |
| Detailed implementation chronology and negative findings | [Research roadmap](TDK_RESEARCH_ROADMAP.md) |
| Normative design and locked-holdout boundary | [Experiment protocol](TDK_EXPERIMENT_PROTOCOL.md) |
| Independent scenario definitions | [Scenario specification](TDK_INDEPENDENT_SCENARIO_SPEC.md) |
| Literature and claim provenance | [Literature review](TDK_LITERATURE_REVIEW.md), [bibliography](TDK_REFERENCES.bib), and [claim ledger](TDK_CLAIM_EVIDENCE_LEDGER.json) |
| Submitted manuscript | [Submitted paper](paper/MyHR_Policy_Aware_Machine_Learning_for_Anomaly_Detection_in_Workforce_Progression.pdf) |

The submitted manuscript and dated audits are preserved as historical evidence.
They do not contain the later November 23 validation result unless explicitly
stated.
