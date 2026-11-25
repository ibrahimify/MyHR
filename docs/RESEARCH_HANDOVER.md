# MyHR Research Handover

Status date: 2026-11-25

## Purpose

MyHR studies whether workforce-progression policy context improves anomaly
ranking over matched raw administrative features at the same human-review
capacity. The system combines deterministic evidence checks with statistical
ranking. It never makes automatic personnel decisions.

## Final Evaluation State

Protocol v2 was frozen and evaluated once. The protected artifact contains 36
conditions, 30 seeds per condition, 1,080 scenarios, and 25,920 eligible
evaluation histories. The artifact, authorization evidence, and consumed ledger
are stored outside Git; compact tables, figures, checksums, and interpretation
are stored in this repository.

The independent artifact audit verified the frozen source revision, matrix,
dependencies, manifest, scenario coverage, prediction membership, temporal
policy links, arithmetic, paired comparisons, and controls. The holdout was not
rerun and no post-hoc model or seed selection was performed.

## Research Answers

1. Policy-aware Isolation Forest improved scenario-mean recall from 34.17% to
   40.97% at equal review capacity. The paired difference was +6.81 percentage
   points, with a 95% interval from +3.54 to +10.23.
2. The recall difference was positive in all 19 predeclared descriptive slices,
   but the slices reuse scenarios and are not independent confirmatory tests.
3. Rare-legitimate alerts were 229/2,160 for policy-aware ML and 248/2,160 for
   raw ML. The paired interval crossed zero, so the proposed rare-case benefit
   was not established.

Average precision and the ordinary-clean flagged rate improved after Holm
adjustment. Exploratory model sensitivity ranged from almost no effect for IQR
to larger effects for Isolation Forest and Local Outlier Factor. This variation
must remain visible.

## Interpretation Boundary

- The result applies to the frozen synthetic design, not real organizations.
- Correct-policy controls support attribution but do not prove a causal
  mechanism.
- Qualitative academic feedback supported continued study, but no case-level
  realism ratings or agreement statistic were collected.
- Duplicate detection is a separate entity-resolution task.
- The optional explanation usability study was not conducted.
- The v2 holdout attempt is consumed and must never be rerun or tuned against.

## Implementation Map

| Area | Location |
| --- | --- |
| Policy and anomaly services | `src/services/anomaly_detection/` |
| Independent simulator | `src/research/` |
| Desktop review workflow | `src/ui/pages/anomaly_review.py` |
| Frozen protocol | `docs/TDK_EXPERIMENT_PROTOCOL.md` |
| Final result report | `docs/results/TDK_HOLDOUT_RESULTS.md` |
| Derived result tables | `docs/tables/holdout_*.csv` |
| Publication figures | `docs/figures/holdout_*` |
| Editable manuscript | `docs/TDK_PAPER_DRAFT.md` |
| Revised manuscript | `docs/paper/MyHR_TDK_Paper_Revised_2026-11-25.pdf` |

## Reproduction

```powershell
pip install -r requirements.txt -r requirements-research-lock.txt
python -m pytest tests
python scripts/verify_tdk_citations.py --require-local-artifact
python scripts/audit_tdk_protocol_artifact.py <artifact-directory> `
  --repo-root <frozen-worktree> `
  --holdout-authorization <external-authorization> `
  --holdout-ledger <external-ledger>
python scripts/build_tdk_holdout_report.py <artifact-directory>
```

The report builder derives all committed tables and figures from the verified
artifact. `docs/results/holdout_report_manifest.json` records source and output
checksums.

## Reading Order

1. `TDK_CURRENT_RESEARCH_STATUS.md`
2. `results/TDK_HOLDOUT_RESULTS.md`
3. `TDK_PAPER_DRAFT.md`, especially Sections 4, 6, and 7
4. `TDK_EXPERIMENT_PROTOCOL.md`
5. `TDK_LITERATURE_REVIEW.md`
6. `TDK_RESEARCH_ROADMAP.md` only for detailed development history

Historical diagnostics and failed designs remain in Git history and the
roadmap. They are not current findings.
