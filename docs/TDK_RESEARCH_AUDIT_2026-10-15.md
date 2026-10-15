# TDK Research Audit - 2026-10-15

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

## Verdict

The current implementation is a reproducible research prototype, not yet evidence that policy-aware Isolation Forest is generally superior. Seeds `2026-2030` influenced feature development and are now permanently classified as development-only. Their results must not be presented as an untouched holdout.

The strongest existing observation is narrower: on one generator, one policy, and five reused seeds, policy-aware features changed which legitimate records were flagged. This may be useful, but it may also reflect the same rules and templates used to generate those records.

## Exact Interpretation Of 0.4 Versus 2.6

The saved result at commit `267aa6f` averaged counts across five seeds. Each seed contained 10 rare-legitimate records in its test split.

| Representation | Per-seed false-positive counts | Total | Denominator | Rate |
| --- | --- | ---: | ---: | ---: |
| Raw | 1, 3, 3, 5, 1 | 13 | 50 | 26% |
| Policy-aware | 0, 1, 1, 0, 0 | 2 | 50 | 4% |

Therefore, `2.6` and `0.4` mean average flagged rare-legitimate records per seed, not percentages. The observed absolute difference is 22 percentage points. A paired exact sign-flip test on the five seed-level differences gives `p = 0.0625`; this is descriptive development evidence, not a final significance claim.

The same saved run produced a less favorable overall workload result:

| Measure | Raw | Policy-aware |
| --- | ---: | ---: |
| Total alerts | 86/1000 | 103/1000 |
| True positives | 62 | 68 |
| False positives | 24 | 35 |
| Ordinary clean false positives | 11/850 (1.29%) | 33/850 (3.88%) |
| Overall false-positive rate | 24/900 (2.67%) | 35/900 (3.89%) |

The rare-case reduction was accompanied by more false alerts elsewhere. The available evidence therefore does not yet show lower total review workload.

## Scientifically Reliable Today

- Fixed configurations generate deterministic datasets.
- Train, validation, and test record partitions are deterministic and disjoint by record.
- Confusion-matrix arithmetic is correct under the supplied labels.
- Model runs and multi-seed CSV artifacts are reproducible.
- Candidate duplicate pairs include field-level evidence for human review.
- Tests and CI verify implementation behavior, although they do not establish methodological validity.

## Critical Risks

### Circularity And Shortcut Learning

The rare-legitimate template uses a 24-month promotion plus two six-month commendation credits. Policy features calculate the same policy adjustment. Normal records receive a narrower commendation pattern. The current experiment can therefore rediscover generator structure without demonstrating generalization.

Required response: matched feature ablations, wrong-policy and shuffled-policy controls, overlapping commendation distributions, and holdout anomaly mechanisms not used during feature design.

### No Untouched Holdout

Validation records were generated but unused. Seeds `2026-2030` were inspected while features were changed. Contamination was fixed at `0.10`, equal to the configured anomaly rate.

Required response: tune only on validation scenarios, compare thresholds at matched alert budgets, and open a separately registered holdout once after the protocol is frozen.

### Mixed Research Tasks

Identity duplicates were counted as progression anomalies even though progression features contain no identity similarity. This imposed an artificial recall penalty and mixed two different problems.

Correction: progression evaluation now excludes duplicate-labelled records. Duplicate detection remains a separate experiment.

### Contradictory Synthetic Ground Truth

Some rare-legitimate promotions were assigned to employees outside the promotion track. Random sanctions could also make records labelled clean or legitimate invalid under the encoded policy.

Corrections:

- rare-legitimate promotions are now restricted to promotion-track employees;
- base sanctions are generated after completed promotions;
- rare-legitimate templates remove unrelated base sanctions;
- property tests require clean and rare-legitimate records to have no policy service deficit.

### Feature Leakage

`duplicate_of_employee_id` is synthetic ground truth unavailable during inference. A derived `has_duplicate_source` feature exposed it in the raw feature dictionary, although it was not selected by the default experiment.

Correction: the ground-truth-derived feature was removed.

### Unfair Threshold Comparison

Raw and policy-aware models used their own Isolation Forest decision thresholds and produced different alert volumes. No validation-selected threshold, matched alert budget, matched false-positive rate, or continuous-score average precision was reported.

Required response: implement the comparison modes specified in `TDK_EXPERIMENT_PROTOCOL.md`.

### Policy Engine Mismatch

The research extractor considers historical events differently from the application. MyHR applies commendations and active sanctions since the current race start. The research extractor currently evaluates the latest completed promotion and lacks sanction resolution state.

Required response: define shared golden histories and verify equivalent outputs between the application policy engine and research representation at an explicit date.

### Duplicate Evaluation Bias

Synthetic duplicates preserve date of birth and use identifier transformations that the matcher explicitly reverses. Similarity threshold `0.70` was not selected on validation data. Pairwise false-positive rates are diluted by roughly 499,500 mostly easy pairs at 1,000 records.

Corrections already made:

- exact matching now means raw exact matching rather than case/whitespace normalization;
- ground truth now includes every within-entity cluster pair, not only direct source links.

Remaining response: entity-disjoint splits, independent corruption families, hard nonduplicates, validation-selected thresholds, blocking recall, candidate workload, and runtime reporting.

### Artifact Traceability

Current run IDs identify generator configuration but not source revision, dirty state, protocol version, dependencies, or feature definition. Old and new implementations can therefore share a run ID.

Required response: write-once artifact directories with Git revision, source hashes, package versions, command line, protocol version, and checksums.

## Answers To The Three Research Questions

1. **Is policy awareness learning something genuinely useful?** Not established. Current results are compatible with rediscovering generator rules and template-specific shortcuts.
2. **Will advantages remain under changed data, policies, anomalies, and seeds?** Unknown. No independent policy or scenario family has been tested.
3. **Is reducing rare-legitimate false positives worth the precision tradeoff?** Not established. In the saved exploratory run, rare false positives fell while total false positives and alert workload increased.

## Required Next Step

Freeze and implement the non-circular experimental protocol before changing another model feature. In particular, create independent scenario generation, validation-based thresholding, matched-budget comparisons, and an untouched holdout. Until then, all numerical results are development diagnostics.

## Implementation Follow-Up

Issue #10 implements the draft v2 framework described in `TDK_EXPERIMENT_PROTOCOL.md`. This addresses the mechanical gaps identified here, but it does not retroactively validate old outputs and does not establish external validity. The protocol remains draft and the holdout remains locked pending full development/validation review and supervisor approval.
