# TDK Literature Review

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Review date: 2026-10-15

Status: development literature synthesis for supervisor review. No holdout data was generated or inspected, and no experiment protocol was silently changed.

## Review Method

Eight predeclared searches covered recent work from 2022-2026 plus foundational papers. OpenAlex and arXiv returned 174 source records and 170 merged discovery records. The full-text synthesis used a curated set of 12 legally accessible papers totaling 336 pages. PDF headers, extracted text, identifiers, titles, and SHA-256 checksums were verified. DOI papers were resolved through OpenAlex; arXiv-only papers were resolved through the arXiv API.

Discovery was intentionally broad, while inclusion required direct methodological relevance to at least one MyHR research component. Citation counts supported discovery only and were not treated as evidence of correctness.

## Core Evidence

| Theme | Full-text evidence | Relevance to MyHR |
| --- | --- | --- |
| Isolation Forest | Liu et al. (2008, 2012) | Supports efficient unsupervised scoring, but not policy interpretation or automatic HR decisions |
| Broad anomaly benchmarks | Han et al. (2022), ADBench | No unsupervised method is universally dominant; method comparisons must span anomaly types, corruptions, and independent trials |
| Context-dependent anomalies | Vaska et al. (2022) | An observation can be abnormal only relative to context, supporting policy-conditioned residuals rather than raw intervals alone |
| Explainable anomaly detection | Li et al. (2024); Carletti et al. (2023) | Explanations need explicit evaluation; DIFFI is a possible model-level explanation for Isolation Forest, not a substitute for policy evidence |
| Synthetic validation | Steinbuss and Boehm (2021); Hansen et al. (2023) | Synthetic realism needs explicit anomaly characteristics, data profiles, and downstream utility; statistical resemblance alone is insufficient |
| Evaluation bias | Fourure et al. (2021); Saito and Rehmsmeier (2015) | F1 and average precision depend on prevalence and threshold choices; PR analysis remains useful under imbalance when prevalence and denominators are explicit |
| Statistical comparison | Demsar (2006) | Compare methods on independent units with paired nonparametric procedures; control multiplicity when making many comparisons |
| Duplicate detection | Wang et al. (2024) | Blocking and pair scoring are separate stages and need separate workload, recall, and ranking metrics |

Full citations and persistent identifiers are in `docs/TDK_REFERENCES.bib`.

## Findings

### 1. Isolation Forest Is A Baseline, Not The Contribution

Isolation Forest isolates points through random partitioning and yields continuous anomaly scores efficiently. Its original motivation does not incorporate organizational policy. ADBench's 30-algorithm, 57-dataset study found no universally superior unsupervised detector. Therefore the defensible MyHR contribution is not “using Isolation Forest.” It is the controlled integration and evaluation of explicit policy context around a transparent baseline.

The current plan is appropriate: preserve continuous scores, compare multiple baselines, and avoid claiming that one model is intrinsically correct.

### 2. Context Can Distinguish Errors From Legitimate Exceptions

Context-dependent anomaly research formalizes the general problem that the same observation may be normal or abnormal under different relationships or states. MyHR has a concrete form of context: service requirements, commendation credits, sanction delays, policy versions, employee track, and race start date.

This supports the main hypothesis: a short promotion interval should not be interpreted identically when a valid policy adjustment explains it. The important scientific boundary is that policy residuals must be tested under wrong policies, shuffled policies, ablations, and independently designed scenarios. Otherwise the detector may simply reproduce the generator's construction logic.

No strong directly comparable paper was found that combines formal workforce-progression rules, policy-aware Isolation Forest features, rare legitimate administrative histories, and a rules-first review pipeline. This is a plausible research gap, not proof of worldwide novelty. The paper should say that prior work was not found in the searched sources and dates, not that no such work exists.

### 3. Deterministic Rules And ML Have Different Jobs

Explicit inconsistencies should be found by deterministic checks. Unsupervised ML is more defensible as a residual ranking layer for unusual but not explicitly forbidden histories. This interpretation matches the Issue #10 cascade results: policy rules already explain most detectable policy violations, while policy-aware ML adds a smaller amount of ranking value for remaining cases.

The final system should retain this order:

1. validate explicit contradictions and policy violations;
2. remove or mark rule-confirmed cases;
3. rank residual cases with raw and policy-aware statistical models;
4. show evidence to an HR reviewer;
5. never promote, sanction, or change salary automatically from an anomaly score.

### 4. Evaluation Must Separate Ranking From Operating Decisions

The literature exposes two complementary facts. Precision-recall analysis is informative for rare positive classes, while F1 and average precision can shift with class prevalence and evaluation construction. MyHR should therefore report average precision but never without anomaly prevalence, denominators, and paired scenario context.

Issue #10 correctly adds continuous-score average precision, validation-only thresholds, equal top-10% review budgets, target-FPR analysis, and explicit counts. It also avoids passing known test contamination to Isolation Forest. These choices directly address the documented evaluation risks.

The later independent methodology audit showed that rare-legitimate reduction alone can move false alerts to ordinary-clean records without improving total precision. The current proposed primary estimand is therefore:

> Paired scenario-level difference in average precision between policy-aware and raw Isolation Forest among rule-negative records from independently generated residual-error scenarios.

Rare-legitimate and ordinary-clean flag rates, F1, anomaly-class recall, total false positives, and cost sensitivity remain important secondary outcomes. Secondary hypothesis tests should be labelled exploratory and adjusted with Holm's procedure. The proposal remains subject to supervisor approval.

### 5. Synthetic Ground Truth Is Necessary But Not Sufficient

Synthetic data provides known labels for errors that are rare and sensitive in real HR systems. The reviewed synthetic-data work also shows the central weakness: matching marginal statistics does not establish realistic relationships or downstream validity.

The current scenario matrix is a strong development instrument, but all scenarios still arise from one conceptual design. Before holdout execution, the supervisor should review:

- the causal story behind each anomaly mechanism;
- whether clean, rare-legitimate, and anomalous cases overlap realistically;
- whether policy-aware features can access a shortcut used by generation;
- whether at least one scenario family can be implemented independently from detector code;
- whether anonymized aggregate distributions or expert judgement can calibrate plausible ranges.

The independently implemented family should not reuse detector residual functions or labels. Its specification can be written as business histories first and translated to records by separate code. This is more valuable than adding another sophisticated detector.

### 6. Explanations Need Their Own Evaluation

The explainable-anomaly literature distinguishes global model interpretation from local case explanations. DIFFI can attribute Isolation Forest decisions to features efficiently, but feature importance alone does not answer the administrative question “what record and policy caused this review?”

MyHR should prioritize evidence-rich local explanations:

- applicable policy version and employee track;
- required and observed service duration;
- commendation and sanction adjustments with source records;
- deterministic validation findings;
- anomaly score and review threshold;
- the most influential residual signals, clearly labelled as model evidence rather than policy facts.

If DIFFI or another explainer is added, test explanation stability and correctness separately. The optional user study can compare interpretation accuracy and completion time against a binary flag, but it should not block the core experiment.

### 7. Duplicate Detection Must Remain A Separate Experiment

Entity-resolution literature treats candidate generation, or blocking, separately from pair scoring. Measuring all possible pairs can make false-positive rates look artificially small because most pairs are easy nonmatches.

The existing protocol is correct to require entity-disjoint splits, hard nonduplicates, corruption families, validation-selected thresholds, blocking recall, reduction ratio, candidate workload, average precision, runtime, and memory. Duplicate detection is useful product functionality and a secondary TDK experiment; it should not be mixed into progression-anomaly labels or the main title claim.

## Comparison With Existing MyHR Research Work

| Requirement from evidence | Existing status | Action |
| --- | --- | --- |
| Validation-only thresholds | Implemented in Issue #10 | Keep |
| Equal review-budget comparison | Implemented at top 10% | Keep as primary operating point |
| Average precision plus explicit prevalence | Implemented with denominators | Keep; avoid cross-prevalence interpretation |
| Rules-only and rules-plus-ML baselines | Implemented | Keep; center the paper on incremental value |
| Wrong-policy, shuffled-policy, and ablation controls | Implemented | Keep all unfavorable results |
| Independent scenario units and paired uncertainty | Implemented across 30 scenarios | Keep; scenario, not employee, is the independent unit |
| Multiple-comparison policy | Not explicitly predeclared | Propose one primary estimand and Holm-adjust secondary tests before freeze |
| Independently designed generator family | Not yet complete | Required before holdout unlock |
| Synthetic realism/external calibration | Limited | Seek supervisor or HR-domain review and aggregate real-world ranges |
| Explanation evaluation | Not implemented | Optional after core validity; policy evidence first |
| Duplicate entity-resolution experiment | Protocol specified, not part of v2 result | Secondary, time permitting |
| Locked final holdout | Correctly untouched | Do not unlock |

## Evidence-Based Recommendations

### Required Before Protocol Freeze

1. Ask the supervisor to approve one primary estimand and the independent holdout-generation specification.
2. Add a documented multiple-comparison rule for secondary inferential tests.
3. Add an independently implemented scenario family or an expert-reviewed history set that does not call detector policy-residual code.
4. Freeze prevalence levels, review budgets, anomaly mechanisms, rare-legitimate mechanisms, and utility-cost sensitivity ranges.
5. Preserve all current negative findings, including raw ablations that outperform the complete raw representation.

These are proposals from the review. They have not changed `docs/TDK_EXPERIMENT_PROTOCOL.md`.

### Keep For The Main Paper

- Rules-first, ML-second architecture.
- Raw versus policy-aware Isolation Forest at equal review capacity.
- Rules-only, statistical, wrong-policy, shuffled-policy, and ablation controls.
- Average precision, fixed-budget precision/recall, explicit denominators, and per-class recall.
- Paired uncertainty across independent scenarios.
- Operational utility expressed as reviews and false escalations, not only model scores.
- Human review for every personnel-relevant finding.

### Optional If Time Allows

- DIFFI-style local feature evidence, after correctness and stability tests.
- A small explanation-usability study.
- Full duplicate-detection benchmark with blocking and scoring phases.
- A real or anonymized external dataset, only with lawful access and a documented data-protection plan.

## Main Remaining Weaknesses

- The current empirical result is entirely synthetic.
- Generator and detector remain conceptually related even when code paths are separate.
- Workforce-progression anomaly research appears sparse, so adjacent evidence comes from general anomaly detection, contextual detection, HR analytics, and entity resolution.
- Utility costs are sensitivity assumptions rather than observed organizational costs.
- A 30-scenario matrix supports paired internal inference but does not prove generalization to arbitrary organizations.

## Supervisor Review Questions

1. Is rule-negative average precision an acceptable primary endpoint, with rare-legitimate and ordinary-clean flag rates as paired secondary outcomes?
2. Which policy profiles and administrative histories are realistic enough to include in the independently designed scenario family?
3. Can the supervisor or another domain expert review a blinded sample of generated histories before protocol freeze?
4. Should secondary p-values use Holm adjustment, or should they remain descriptive with confidence intervals only?
5. Is there any lawful anonymized or aggregate organizational data that can calibrate feature ranges without exposing personal data?

## Bottom Line

The literature supports the research question and most of the Issue #10 protocol, but it does not justify claiming that policy-aware ML is universally better. A defensible contribution is narrower and stronger: evaluate whether explicit policy context changes anomaly ranking and reduces unnecessary review of legitimate exceptional histories, after deterministic rules are handled, under matched workload and independently varied scenarios.
