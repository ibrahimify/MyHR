# TDK Literature Review

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Review date: 2026-11-26

Status: literature synthesis supporting the completed v2 evaluation. This update changed no experiment protocol and did not generate, inspect, or rerun any experimental data.

**Historical evidence boundary:** An early residual experiment could not test whether policy-aware features added value because its three policy-specific features became constant after deterministic filtering. That failed design is retained as research history. The later v2 protocol and one-time protected evaluation are described in the current research-status and results documents; literature cannot substitute for their empirical evidence.

## Review Method

Thirteen predefined searches cover recent work from 2022-2026 plus essential foundations. A 2026-11-26 refresh through the repository clients queried OpenAlex, Crossref, and arXiv and returned 298 source records and 282 deduplicated discovery records. Nine papers were added only after title, author, year, venue, identifier, full-text availability, and claim relevance were checked. The bibliography now contains 27 sources: 19 published from 2022 through 2026 and eight retained foundations or pre-2022 methodological sources. Semantic Scholar is optional because its anonymous quota is not reliable; no paid service or credential was introduced.

Discovery was intentionally broad, while inclusion required direct methodological relevance to at least one MyHR research component. Citation counts supported discovery only and were not treated as evidence of correctness.

## Core Evidence

| Theme | Full-text evidence | Relevance to MyHR |
| --- | --- | --- |
| Isolation Forest | Liu et al. (2008, 2012) | Supports efficient unsupervised scoring, but not policy interpretation or automatic HR decisions |
| Broad anomaly benchmarks | Han et al. (2022), ADBench | No unsupervised method is universally dominant; method comparisons must span anomaly types, corruptions, and independent trials |
| Recent tabular detector comparisons | Bouman et al. (2024) | Local and global anomaly structures favor different algorithms; a structurally different baseline is more informative than additional Isolation Forest variants alone |
| Temporal shift | Dragoi et al. (2022); Tschalzev et al. (2024) | Time and data preparation can change model rankings, supporting explicit policy-period and population-shift checks |
| Context-dependent anomalies | Vaska et al. (2022) | An observation can be abnormal only relative to context, supporting policy-conditioned residuals rather than raw intervals alone |
| Explainable anomaly detection | Li et al. (2024); Carletti et al. (2023) | Explanations need explicit evaluation; DIFFI is a possible model-level explanation for Isolation Forest, not a substitute for policy evidence |
| Synthetic validation | Steinbuss and Boehm (2021); Hansen et al. (2023); Van Breugel et al. (2023) | Synthetic realism needs explicit anomaly characteristics and downstream checks; synthetic-only performance can misstate real-world utility, particularly in sparse regions |
| Evaluation bias | Fourure et al. (2021); Saito and Rehmsmeier (2015) | F1 and average precision depend on prevalence and threshold choices; PR analysis remains useful under imbalance when prevalence and denominators are explicit |
| Benchmark reliability | Liu and Paparrizos (2024) | Dataset integrity, measure choice, and consistent tuning are distinct requirements for reliable comparisons |
| Statistical comparison | Demsar (2006) | Compare methods on independent units with paired nonparametric procedures; control multiplicity when making many comparisons |
| Duplicate detection | Binette and Steorts (2022); Wang et al. (2024); Binette et al. (2024); Nanayakkara et al. (2025) | Blocking, pair scoring, cluster evaluation, and the candidate universe are separate concerns; representative error analysis needs explicit denominators |
| Responsible AI in HR | Bujold et al. (2024) | AI used in HR is socio-technical and risk-bearing, supporting human review and explicit limits on automated personnel action |

Full citations and persistent identifiers are in `docs/TDK_REFERENCES.bib`.

## Citation Governance Audit

The 2026-10-29 audit covered the original 18 entries and remains preserved in the archive. The 2026-11-26 update adds nine directly relevant sources. Crossref and OpenAlex verified DOI metadata, arXiv or publisher records covered papers without Crossref DOIs, and legally accessible full text was inspected before any scientific claim was recorded. No duplicate identities were found. The centralized provenance registry records online-first versus issue years and distinguishes peer-reviewed articles from preprints.

The Holm multiple-testing claim is supported through Demsar's preserved secondary account of the procedure. The Krippendorff paper is now preserved and supports independent coding under common instructions and agreement assessment. It does not directly establish MyHR's disagreement-retention or adjudication procedure; those remain explicit study-design choices. The ledger also labels the application of contextual-anomaly research to MyHR policy residuals and the protected-evaluation recommendation as inferences rather than direct findings of the cited papers.

Author-year prose alone is insufficient provenance. New literature-supported claims must update the bibliography, provenance registry, and claim ledger and pass `scripts/verify_tdk_citations.py`. An independent recheck on 2026-11-26 verified the nine additions and narrowed claims drawn from adjacent domains before manuscript integration.

## 2026-11-26 Recency And Coverage Update

The expanded evidence changes the emphasis of the review in five useful ways:

1. **Model choice:** Bouman et al. (2024) found different leading methods for local and global anomalies across 52 real-world tabular datasets. MyHR should therefore retain Isolation Forest as a transparent baseline and compare it with at least one structurally different method; the literature does not identify a universally best detector.
2. **Temporal robustness:** AnoShift shows degradation between contemporaneous and later test periods, while Tschalzev et al. show that preprocessing and temporal adaptation can change tabular-model rankings. MyHR's policy versions and population periods should therefore be analyzed explicitly rather than pooled into one timeless distribution.
3. **Benchmark discipline:** Liu and Paparrizos separate dataset integrity, metric reliability, and consistent model comparison. Their time-series benchmark is adjacent rather than directly equivalent to workforce histories, but its evaluation warnings apply to MyHR's experimental design.
4. **Synthetic evidence:** Van Breugel et al. show that treating synthetic data as observed real data can overstate downstream performance, especially for minority classes and low-density regions. This supports explicit limits on external-validity claims from MyHR's synthetic evaluation.
5. **Duplicate detection and HR responsibility:** Recent entity-resolution work makes the all-pairs universe, blocking losses, cluster-level errors, and representative labeling explicit. Bujold et al. place AI in HR within a responsible socio-technical setting. Together these sources support separate duplicate evaluation and human review, not automatic personnel action.

These sources strengthen methodological justification but do not retroactively change results, establish generalization to real organizations, or prove that policy-aware features caused any observed difference.

## Findings

### 1. Isolation Forest Is A Baseline, Not The Contribution

Isolation Forest isolates points through random partitioning and yields continuous anomaly scores efficiently. Its original motivation does not incorporate organizational policy. ADBench's 30-algorithm, 57-dataset study found no universally superior unsupervised detector. Therefore the defensible MyHR contribution is not “using Isolation Forest.” It is the controlled integration and evaluation of explicit policy context around a transparent baseline.

The current plan is appropriate: preserve continuous scores, compare multiple baselines, and avoid claiming that one model is intrinsically correct.

### 2. Context Can Distinguish Errors From Legitimate Exceptions

Context-dependent anomaly research formalizes the general problem that the same observation may be normal or abnormal under different relationships or states. MyHR has a concrete form of context: service requirements, commendation credits, sanction delays, policy versions, employee track, and race start date.

This supports the main hypothesis: a short promotion interval should not be interpreted identically when a valid policy adjustment explains it. The important scientific boundary is that policy residuals must be tested under wrong policies, shuffled policies, ablations, and independently designed scenarios. Otherwise the detector may simply reproduce the generator's construction logic.

No strong directly comparable paper was found that combines formal workforce-progression rules, policy-aware Isolation Forest features, rare legitimate administrative histories, and a rules-first review pipeline. This is a plausible research gap, not proof of worldwide novelty. The paper should say that prior work was not found in the searched sources and dates, not that no such work exists.

### 3. Deterministic Rules And ML Have Different Jobs

Explicit inconsistencies should be found by deterministic checks. Unsupervised ML is more defensible as a residual ranking layer for unusual but not explicitly forbidden histories. The Issue #10 cascade confirms that policy rules already explain most detectable policy violations. It does not establish added ranking value from policy-aware ML because the current policy-specific residual features are constant after filtering.

The primary experiment should use this order:

1. validate and preserve invariant contradictions common to both pipelines;
2. compare raw and policy-aware ranking over the same invariant-negative records at equal additional review capacity;
3. report configurable policy checks and the complete rules-plus-ML queue secondarily;
4. show evidence to an HR reviewer;
5. never promote, sanction, or change salary automatically from an anomaly score.

### 4. Evaluation Must Separate Ranking From Operating Decisions

The literature exposes two complementary facts. Precision-recall analysis is informative for rare positive classes, while F1 and average precision can shift with class prevalence and evaluation construction. MyHR should therefore report average precision but never without anomaly prevalence, denominators, and paired scenario context.

Issue #10 correctly adds continuous-score average precision, validation-only thresholds, equal top-10% review budgets, target-FPR analysis, and explicit counts. It also avoids passing known test contamination to Isolation Forest. These choices directly address the documented evaluation risks.

The later independent methodology audit showed that rare-legitimate reduction alone can move false alerts to ordinary-clean records without improving total precision. The supervisor decision recorded on 29 October 2026 therefore defines the primary estimand as:

> Paired scenario-level difference in recall at identical fixed additional review capacity between policy-aware and raw Isolation Forest among invariant-negative records from independently generated residual-error scenarios.

Precision, total false alerts, and rare-legitimate false-alert rates accompany the primary endpoint. Average Precision, ordinary-clean flag rates, F1, per-class recall, and cost sensitivity remain secondary. The exact multiplicity procedure for inferential secondary tests remains a draft freeze decision rather than part of the six approved choices.

### 5. Synthetic Ground Truth Is Necessary But Not Sufficient

Synthetic data provides known labels for errors that are rare and sensitive in real HR systems. The reviewed synthetic-data work also shows the central weakness: matching marginal statistics does not establish realistic relationships or downstream validity.

The original scenario matrix was a useful development instrument but arose from one conceptual design. A separately implemented stress-test family exposed constant residual policy features and partly constructed historical-policy counterexamples. Source-code independence alone therefore did not establish a valid central comparison. For any future protected evaluation, reviewers should examine:

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
| Independently designed generator family | Implemented as a development stress test | Keep as development evidence; redesign is still required because the residual policy signal collapsed to constants |
| Synthetic realism/external calibration | Limited | Seek supervisor or HR-domain review and aggregate real-world ranges |
| Explanation evaluation | Not implemented | Optional after core validity; policy evidence first |
| Duplicate entity-resolution experiment | Protocol specified, not part of v2 result | Secondary, time permitting |
| Protected v2 evaluation | Completed once under the frozen v2 protocol | Preserve the result; never rerun or tune against it |

## Evidence-Based Recommendations

### Historical Pre-Freeze Recommendations

1. Implement the approved recall-at-fixed-capacity estimand and independent holdout-generation specification without opening the holdout.
2. Add a documented multiple-comparison rule for secondary inferential tests.
3. Add an independently implemented scenario family or an expert-reviewed history set that does not call detector policy-residual code.
4. Freeze prevalence levels, review budgets, anomaly mechanisms, rare-legitimate mechanisms, and utility-cost sensitivity ranges.
5. Preserve all current negative findings, including raw ablations that outperform the complete raw representation.

These recommendations were recorded before protocol v2 was frozen. The frozen
design subsequently specified the primary endpoint, multiplicity rule, scenario
matrix, and one-time protected evaluation. Current results are summarized in
`TDK_CURRENT_RESEARCH_STATUS.md`.

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

## Targeted Decision Review - 2026-10-17

This update addresses only the open supervisor decisions. It does not approve or alter the protocol. Full text was reviewed for Saito and Rehmsmeier, Demsar, Steinbuss and Boehm, Hansen et al., Sorbo and Ruocco, Rochner et al., Neelamegam et al., and Deng et al. DOI metadata was independently resolved through OpenAlex; arXiv identifiers were resolved through the arXiv API.

| Decision | Established by the reviewed evidence | Still uncertain for MyHR |
| --- | --- | --- |
| Primary endpoint | Precision-recall measures are more informative than ROC summaries under severe imbalance, and continuous-score metrics avoid choosing a test threshold. Average precision remains prevalence-sensitive, so each value needs its positive count and scenario context. | Literature does not designate AP as universally optimal. Whether scenario-mean AP is the correct primary estimand is a domain decision. The current residual AP comparison is invalid because policy features are constant after filtering. |
| Paired inference and multiplicity | Methods should be paired on the same independent experimental units. One predeclared primary test avoids a multiplicity family. Demsar's preserved account describes Holm's step-down control of family-wise error for secondary comparisons. | A sign-flip test requires an exchangeable or sign-symmetric null interpretation. A scenario bootstrap requires a defensible scenario population. With only six informative development scenarios, neither procedure supplies strong evidence. Exploratory outcomes may be better reported with intervals and explicit labels rather than inferential claims. |
| Synthetic validation and circularity | Synthetic evaluation should test downstream utility, multiple data profiles, and detector behavior across scenarios. Recent anomaly-benchmarking work directly warns about single-pipeline overfitting and supports scenario-specific objectives. Repeated random factors, intervals, and protected evaluation data are MyHR design inferences, not direct prescriptions from that paper. | Source-code separation alone does not establish conceptual independence. Domain experts must assess scenario realism, and the generator must not encode the detector's decisive residual by construction. No literature result can certify the current generator as realistic. |
| Policy versions over time | Bitemporal research distinguishes valid time, when a fact or rule applies in the modeled world, from transaction time, when it is stored. Preserving both supports historical reconstruction, corrections, and auditability. | The exact MyHR schema, policy epochs, jurisdictions, recognized-service rules, and migration behavior require human domain approval. The literature supports the temporal distinction, not a particular HR policy. |
| Expert review of anomaly ground truth | Human-in-the-loop anomaly work treats expert validation as a separate workflow rather than automatic truth. The preserved reliability paper supports independently working coders applying common instructions and measuring agreement. | Disagreement retention and adjudication are MyHR protocol choices rather than direct findings from that paper. No universal reviewer count or agreement threshold applies to workforce progression. Reviewer qualifications, sample size, acceptable agreement, and adjudication rules must be chosen before cases are reviewed. |
| Holdout generation | The reviewed benchmark critique supports concern about overfitting to a single evaluation pipeline. Protected data, frozen choices, repeated random realizations, and scenario diversity informed the MyHR design. | This row records the pre-freeze concern. Protocol v2 later replaced the defective residual design and was evaluated once; external validity remains unresolved. |

### Supervisor Decision Outcome - 2026-10-29

The supervisor selected recall at identical fixed additional review capacity as the primary endpoint for raw versus policy-aware residual ML after invariant-only filtering. Pair methods within the same independently generated scenario seed and report scenario-level and pooled denominators separately. Average Precision is secondary. Zero-positive scenarios remain reported, are marked undefined for recall and AP, and do not enter paired inference for those metrics under the predeclared rule.

For historical policy, the implementation contract stores effective and
recorded times, policy versions, recognized service, and correction provenance.
The proposed case-level review uses two complementary reviewers and blinded
histories. That review was not completed; the final study therefore reports
qualitative expert feedback without agreement statistics or external realism
estimates.

## Recorded Supervisor Answers

1. Recall at fixed review capacity is primary; AP is secondary.
2. Deterministic filtering for the primary residual comparison is restricted to invariant contradictions.
3. Both ML representations receive the same additional review budget on the same remaining records.
4. Historical reconstruction uses a bitemporal contract with policy versions and correction provenance.
5. Two complementary blinded reviewers assess synthetic realism and preserve ambiguity.
6. The final holdout uses an independently specified repeated-seed matrix with detector-inaccessible causal truth.

The secondary multiplicity procedure, exact scenario matrix, exact reviewers and sample, external calibration, and protocol freeze were not resolved by these six answers.

## Bottom Line

The literature supports the research question and most of the Issue #10 protocol, but it does not justify claiming that policy-aware ML is universally better. A defensible contribution is narrower and stronger: evaluate whether explicit policy context changes anomaly ranking and reduces unnecessary review of legitimate exceptional histories, after deterministic rules are handled, under matched workload and independently varied scenarios.
