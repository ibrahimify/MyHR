# MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression

**Author:** Muhammad Ibrahim Shoeb

**Supervisor:** Dr. Husam Al-Magsoosi

**Institution:** Budapest University of Technology and Economics, Faculty of Electrical Engineering and Informatics

**Paper language:** English

## Abstract

Workforce progression systems apply promotion, commendation, sanction, and salary-increment policies to complex administrative records. Detecting erroneous records is challenging because unusual histories may be legitimate under the applicable policy. A short promotion interval, for example, may reflect a recorded commendation rather than an error. This research investigates whether incorporating explicit progression-policy context into machine-learning features can reduce false anomaly alerts while preserving detection of actual errors, thereby reducing manual HR review workload by prioritising records for evidence-based attention.

The study uses MyHR, an offline HR decision-support application, as the experimental platform. A formal progression model specifies service requirements, commendation credits, sanction delays, and annual increments. Deterministic validation addresses explicit contradictions, and Isolation Forest models rank the remaining histories using raw or policy-conditioned features at equal review capacity. Alerts support human review and never trigger personnel decisions.

Evaluation uses reproducible synthetic histories with injected administrative errors and rare legitimate cases, separate fitting, validation, and evaluation partitions, and wrong-policy, shuffled-policy, ablation, and alternative-model controls. In the frozen one-time synthetic holdout, policy-aware Isolation Forest increased scenario-mean recall from 34.2% to 41.0% at the same review capacity, a paired difference of 6.81 percentage points (95% interval 3.54 to 10.23). Average precision and the ordinary-clean false-alert rate also improved after multiplicity adjustment. The rare-legitimate false-alert difference was favorable but inconclusive. Policy-aware recall was higher in all 19 predeclared descriptive condition slices, while alternative scorers showed effects from near zero to 6.83 percentage points. These findings support policy-conditioned features within the synthetic design but do not establish performance on real organizational data or justify automatic personnel decisions. Duplicate detection remains a separate task, and the optional usability study was not conducted.

Keywords: machine learning, anomaly detection, Isolation Forest, workforce progression, rule-based decision support, synthetic data, duplicate detection, explainability

## 1 Introduction

### 1.1 Context and Problem

Employee progression decisions are built from administrative facts that accumulate over time. Service duration, role level, performance evidence, commendations, sanctions, policy versions, and recorded approvals all affect eligibility for promotion or an annual salary increment. Executing explicit eligibility rules is straightforward; reviewing data quality is harder. Some errors are direct contradictions, such as an end date before a start date. Other histories are suspicious only in context: a promotion after a short interval may be an error, or it may be lawful because a commendation shortened the required service.

A detector that flags every unusual history creates unnecessary review work and may escalate legitimate exceptional cases, while one that suppresses too many alerts misses real errors. The goal is therefore a review queue, not automated personnel decisions. Explicit violations are explained deterministically, and less direct patterns are ranked for an authorized person. The scientific question is whether representing the applicable policy improves that ranking beyond raw event counts and intervals.

MyHR, a standalone Python and PySide6 desktop application backed by SQLite and SQLAlchemy, already contains an auditable progression model. It manages employee and organization data, performance reviews, promotions, commendations, sanctions, annual increments, imports, reports, and an application audit trail. Progression is calculated from source records rather than stored as an edited percentage, which gives research features and explanations a defined policy boundary.

**Problem statement.**

The research problem has three parts. Explicit contradictions should be detected reliably and explained with their evidence. Histories that are not explicit violations may still deserve review because their event patterns are unusual. Legitimate policy-dependent histories should not be treated as errors only because they are rare. No single accuracy score captures all three, so the problem needs separate deterministic and statistical components, comparisons at fixed review capacity, complete denominators, and a protected evaluation design.

Unsupervised anomaly detection is attractive when labelled errors are scarce, but it has no notion of what an organization considers lawful. Isolation Forest scores observations by how quickly random recursive partitions isolate them [1,2]. Its score measures statistical isolation, not administrative invalidity, and the same history can be anomalous under one policy and legitimate under another. This motivates policy-conditioned features, together with controls that test whether the supplied policy information is actually used.

### 1.2 Research Questions

The study is organized around three questions:

1. Does explicit policy context improve progression-anomaly ranking beyond raw administrative features and deterministic validation?
2. Does any observed advantage remain across employee populations, anomaly mechanisms, policy configurations, prevalence levels, and random seeds?
3. At equal review capacity, can policy context reduce false alerts on rare but legitimate histories without missing genuine administrative errors or merely moving false alerts to ordinary clean records?

Duplicate-record detection is a pairwise entity-resolution problem, not an employee-level progression anomaly, and is evaluated separately. Mixing it with progression labels would obscure both tasks and distort denominators.

### 1.3 Research Approach and Contributions

The architecture applies rules first and machine learning (ML) second (Figure 1). Deterministic checks identify explicit date, event, and policy contradictions, and statistical baselines and Isolation Forest rank the remaining records. Raw and policy-aware representations share scenario, split, and model seeds, are compared at equal review budgets, and are accompanied by wrong-policy, shuffled-policy, and ablation controls that are reported even when unfavorable. Every alert is a recommendation to a human reviewer.

Synthetic histories provide known ground truth without private data, but a generator can encode the same rule the detector uses, so that the method succeeds by construction. The study therefore adds an independently implemented administrative-world simulator to the original policy-shaped generator and records causal truth separately from observed records. Independence of the generator is necessary but not sufficient; realism still requires human review.

[[FIGURE:architecture.png|Figure 1. Rules-first, ML-second decision-support architecture. Histories without an invariant finding receive matched raw or policy-aware features, an Isolation Forest score, and a position within a fixed additional review budget. The dashed boundary marks the only decision point, an authorized human reviewer; scores never change personnel records.]]

**Contributions and limits.**

The implemented work contributes a formal progression model shared with the application; evidence-rich deterministic validation; raw and policy-aware feature families with statistical and Isolation Forest baselines; validation-only thresholds and equal-budget comparisons; wrong-policy, shuffled-policy, and ablation controls; an independent development simulator; write-once, checksummed artifacts with independent recomputation of metrics; and a separate duplicate-candidate experiment.

The development evidence also yields a negative methodological result. In an early residual design, deterministic filtering consumed the policy signal and held all three policy-specific features at zero (Section 6.7). A later diagnostic showed that apparent false alerts on policy-transition cases were responses to genuine contradictions created by the generator (Section 6.7). Both failures were preserved and led to the corrected design and stronger provenance checks.

The paper does not claim that policy-aware ML is generally better, that synthetic rates transfer to real organizations, or that the system should automate promotion, sanction, salary, or record-merging decisions. The frozen holdout was evaluated once at the preregistered revision; no post-hoc tuning or rerun was performed.

Section 2 reviews related work. Section 3 describes MyHR and its progression model, and Section 4 the research methodology. Section 5 covers implementation, reproducibility, and the in-app demonstration. Section 6 reports the development experiments, Section 7 discusses their validity, and Section 8 concludes.

## 2 Background and Related Work

### 2.1 Isolation-Based Anomaly Detection

Isolation Forest rests on the observation that anomalies are often easier to isolate than ordinary points. Isolation trees are built by repeatedly choosing a random feature and split value, and the expected path length across trees becomes the anomaly score [1]. The later isolation-based formulation analyses the method more broadly and explains its computational behavior [2]. The method suits MyHR because it produces a continuous ranking, handles several numeric features, and needs no labelled anomalies during fitting.

A high score means that a feature vector is isolated relative to the fitted population, not that the record is invalid, unlawful, or harmful. MyHR therefore keeps deterministic policy evidence, model score, threshold, and human decision separate.

ADBench shows that anomaly-detection performance varies substantially with dataset, supervision assumptions, and method family [3], which argues for comparing any model against transparent baselines. The aim here is to measure what the policy representation contributes under matched conditions, not to find a universally best detector.

### 2.2 Policy Context and Explainability

Context-dependent anomaly detection concerns observations that are unusual only in a particular situation, and knowledge-based context can change how an observation should be interpreted [4]. Workforce progression is a clear case: the same elapsed service can comply with one policy version and violate another. Commendation credits, sanction delays, employee track, recognized prior service, and the effective policy period all change the expected progression path.

Policy-aware features are therefore transformations relative to an explicit rule set, such as a service deficit relative to the applicable requirement. They can align the model with administrative meaning, but they can also leak the answer if the generator uses the same residual to define anomalies. A genuine policy signal should weaken when the policy identity is wrong or shuffled, which is what the controls test.

**Review evidence.**

Explainable anomaly-detection research separates global understanding of a detector from local evidence for a specific alert [5], and DIFFI derives feature importance for Isolation Forest from tree depth and feature use [6]. Feature importance can describe a model score, but an HR reviewer also needs administrative evidence: policy version, required and observed service, adjustments, source records, and deterministic findings.

MyHR gives priority to this administrative evidence; a model attribution, if added later, would be labelled as model evidence rather than a policy fact. Explanation quality is a separate evaluation problem. The registered abstract makes a user study optional, and this paper claims no usability results.

### 2.3 Evaluation Under Class Imbalance

Administrative anomalies are expected to be rare. Under severe class imbalance, receiver-operating-characteristic summaries can look favorable while the precision of the review queue is poor, and precision-recall analysis is often more informative [7]. Average precision (AP) summarizes a ranking without a test-selected threshold, but it depends on prevalence, so every AP value needs the number of ranked records and positive cases.

Threshold metrics are still needed because HR teams review a finite number of cases; Section 4.4 defines the operating points and measures used here. Metric choice follows the review task because anomaly-detection metrics encode different assumptions, a point made for time-series detection in [8].

The evaluation protocol can itself inflate results. Train-test partitioning choices, thresholds tuned on the test set, and contamination rates taken from the test data can all inflate F1 and average precision [9], and conclusions may depend on a narrow evaluation pipeline [10]. Selecting favorable seeds is a related risk, which MyHR addresses by fixing and reporting all seeds. MyHR records separate dataset, split, and model seeds, selects thresholds on validation data, retains negative results, and evaluated the frozen holdout once without post-hoc tuning.

### 2.4 Synthetic Data and Circularity

Synthetic data allows controlled injection of known errors and rare legitimate histories, but realistic evaluation requires more than plausible-looking rows. Steinbuss and Böhm show the importance of varying synthetic outlier characteristics and data domains [11]. MyHR additionally treats defining anomalies through the detector's own decisive feature as a circularity risk; this is a design inference applied to the present experiment, not a prescription attributed to that paper. Data-centric work on synthetic tabular data likewise emphasizes downstream behavior and multiple profiles over a single similarity score [12].

The original MyHR generator and the policy-aware detector share policy concepts, so results on that generator are useful for engineering but vulnerable to circularity. The independent simulator (Section 4.2) avoids shared code, but source-code separation does not ensure conceptual separation, as the historical residual design showed (Section 6.7).

### 2.5 Temporal Policy and Human Review

Administrative systems must distinguish when a fact or policy is effective in the modeled world from when it is recorded in the database; bitemporal research calls these valid time and transaction time [13]. The distinction supports historical reconstruction, corrections, and auditability, and applies directly to promotions decided under an earlier policy, recognized service recorded later, and corrections entered after an event. A preserved MyHR artifact shows the failure caused by replaying current policy over constructed histories intended to represent lawful historical exceptions (Section 6.7), and the corrected research adapter replays the applicable historical policy (Section 3.3).

**Human review and duplicate detection.**

Human-in-the-loop anomaly detection treats expert validation as part of the workflow instead of assuming that model output is true [14]. MyHR keeps the same boundary, and its proposed realism review is blinded to model scores and generated labels so that reviewers judge plausibility rather than confirm the detector.

Duplicate detection is evaluated as entity resolution. Candidate generation and pair scoring must be separated, because scoring every possible pair makes false-positive rates look deceptively small, and dense-blocking research stresses candidate workload and blocking recall [15]. This secondary task provides no evidence for the progression-anomaly hypothesis.

### 2.6 Research Gap

The reviewed literature covers Isolation Forest, contextual anomaly detection, imbalanced evaluation, the limits of synthetic data, bitemporal history, explanation, and entity resolution. It does not provide a standard benchmark for policy-aware workforce progression. The contribution is therefore bounded: formalize one progression domain, build reproducible controls, test whether policy context changes ranking at matched workload, and document when the experiment cannot answer that question. The performed search does not support a claim that no prior system combines these elements.

## 3 MyHR and the Formal Progression Model

### 3.1 Application Boundary

MyHR is a local-first desktop system with a PySide6 interface and SQLite persistence through SQLAlchemy. Research dependencies are kept out of the packaged application. The operational modules (Section 1.1) form the context for the research package, which reads structured representations and cannot change personnel data.

[[FIGURE:myhr_ui.png|Figure 2. MyHR employee-management interface used as the application context for policy evidence and human review.]]

### 3.2 Progression Rules and Evidence

Let B denote the base number of service months required for the next level, M the completed months since the last promotion or recognized start point, C the months of valid commendation credit, and S the months of active sanction delay. Adjusted service A and remaining service R are defined as:

```text
A = M + C - S
R = max(0, B - A)
```

Service-requirement status and bounded progress are:

```text
service_requirement_met = (R = 0)
progress = clamp(floor(100 A / B), 0, 100)
```

The form makes the sign of each adjustment explicit: a commendation brings the employee closer to the requirement, and a sanction delays eligibility. The implementation records the source events and policy configuration used in each calculation. Promotions remain manual decisions even when the service requirement is met.

**Promotion, sub-race, and annual increment.**

A promotion race represents service toward the next level. Sub-race checkpoints track annual progress and salary-increment timing but are not promotions. Employees in the `Other` track have no degree-based promotion race, although they receive annual increments, commendations, sanctions, and performance reviews, so the system does not invent a promotion path for roles governed by different rules.

Annual salary increments are independent of promotion: completing a yearly interval can make an increment due when the employee is not eligible for a new level, whereas a promotion changes level and salary through an explicit approval workflow.

**Performance and manual approval.**

Performance reviews use a weighted rubric covering goal delivery, role competencies, conduct and reliability, and teamwork and leadership. The score is evidence shown during promotion review and does not replace policy eligibility, since a candidate may complete a race with no recent review or with poor performance. The confirmation dialog shows policy status, latest performance, active sanctions, commendations, salary change, warnings, and a link to the employee profile; the authorized reviewer approves or cancels, and every outcome is audited.

**Administrative evidence.**

The research representation separates employee facts, administrative events, policy epochs, generated truth, and observed records. This matters when an observation is incomplete or late: a missing increment import may be a data error although the underlying event occurred, and a sanction linked to the wrong employee changes the observation ledger but not the generated world. The independent generator records these distinctions for new artifacts; the original immutable artifact retains only its historical schema.

[[FIGURE:policy_timeline.png|Figure 3. Example progression timeline showing base service, commendation credit, sanction delay, and the need to retain the policy effective at the decision date.]]

### 3.3 Policy-Engine Parity and Temporal Replay

Research calculations must agree with the application on shared histories. The application calls a pure promotion-race calculation shared with research code, and policy-parity tests (Section 5.1) cover clean progression, commendation credit, sanction delay, promotion reset, completed service, and non-progression tracks. Passing these tests shows implementation agreement on the tested histories, not that the policy itself is organizationally correct.

**Temporal representation.**

Replaying the current policy is insufficient for historical decisions. The research record therefore retains policy identity and version, valid and recorded times, jurisdiction, recognized service, approval and entitlement evidence, and correction or retry provenance. The implementation links grandfathering evidence to the employee, policy version, and event, and provides two temporal views. The `known_then` view restricts effective facts, recorded facts, and policy knowledge to the decision date. The `later_review` view keeps the same effective decision horizon but admits evidence and amendments recorded by the review date. These semantics were frozen under protocol v2 and tested in the research implementation; they are not presented as a migrated production database schema.

## 4 Research Methodology

### 4.1 Tasks and Data Contract

The primary task ranks employee histories for progression-related review. Positive classes are inconsistent dates, unexplained frequent promotions, excessive sanctions, and unusual administrative intervals. A broadly labelled rare-legitimate class contains histories that are unusual but intended to be lawful under the generated policy context, and clean records include both ordinary and exceptional non-error histories.

Duplicate detection is a separate pairwise task whose positive unit is a pair or entity cluster and whose identity attributes do not belong in progression features. Reporting it separately keeps the many easy non-duplicate pairs from diluting progression metrics and keeps duplicate labels from changing anomaly prevalence.

**Synthetic record contract.**

Each synthetic history contains an employee identifier, track, service and role dates, promotions, commendations, sanctions, annual increments, performance evidence, and the administrative timestamps the scenario needs. Generated labels and causal truth are excluded from prediction features. Dataset, split, and model seeds are recorded separately, and all records of one latent person stay in one partition for duplicate detection.

The taxonomy (table below) distinguishes the nominal scenario pattern from the mechanism realized in each record. Generation applies explicit compatibility and record-level eligibility checks instead of silently replacing an infeasible pattern. Stable-administration and merger/migration populations may host all five rare patterns; rapid expansion excludes legacy policy transitions because of its hire window. Future artifacts preserve nominal and realized values, complete event fields, entitlement evidence, policy epochs, and whether the causal event was observed or omitted; existing artifacts are not rewritten.

| Category | Example mechanism | Expected evidence | Evaluation role |
| --- | --- | --- | --- |
| Inconsistent dates | Event before employment start | Direct chronological contradiction | Deterministic baseline and anomaly label |
| Frequent promotion | Promotion before adjusted service requirement | Promotion interval and applicable policy | Policy check and anomaly ranking |
| Excessive sanctions | Dense or repeated sanction history | Event count, timing, resolution, service delay | Statistical and policy context |
| Unusual interval | Abnormally short administrative gap | Event intervals and process context | Statistical ranking |
| Wrong employee link | Sanctions attached to another employee | Observation ledger differs from generated world | Independent residual mechanism |
| Missing import | Increment event omitted from observation | World event exists but record is absent | Independent residual mechanism |
| Approval bypass | Promotion without required approval evidence | Explicit workflow violation | Deterministic check |
| Batch retry | Duplicate or repeated administrative events | Repeated event references and intervals | Deterministic check |
| Rare legitimate | Previous policy, recognized service, or delayed recording | Temporal policy and evidence context | False-alert analysis |

### 4.2 Scenario Design and Evaluation Boundary

Seeds 2026 to 2030 were inspected during early feature development and are permanently development-only. Protocol-development scenarios were used to diagnose implementation and design failures, while validation scenarios informed threshold selection and feature-family decisions. The final matrix, feature families, thresholds, analysis, dependencies, and source revision were frozen before any holdout records were generated.

The holdout was generated and evaluated once from the frozen revision. Its configuration, seeds, source hashes, dependency lock, and file checksums are preserved in a write-once artifact. Any future change requires a separately versioned protocol and a new holdout family; the reported result remains unchanged.

[[FIGURE:experiment_flow.png|Figure 4. Evaluation lifecycle. Within each scenario, models are fitted on fitting histories, operating decisions are made on validation histories, and metrics are computed on evaluation histories. The final holdout used a separately frozen scenario matrix and was run once without post-hoc tuning.]]

**Original scenario matrix.**

The protocol-v2 generator varies policy profile, population profile, anomaly mechanism, rare-legitimate pattern, prevalence, and seeds, and produces matched raw and policy-aware representations of the same records. Thirty development and thirty validation scenarios were generated with 600 employees and 120 test records per scenario, giving 3,600 validation test histories.

This generator is useful for testing pipeline mechanics, but it is conceptually close to the detector: several injected anomaly mechanisms become direct policy deficits, so the policy-aware representation can mirror the generator's construction. Its results are development diagnostics, not transferable evidence.

**Independent administrative-world simulator.**

The independent simulator uses only the Python standard library and does not import detector features, deterministic checks, the application policy engine, or the original generator. It first constructs an administrative world and then derives an observation ledger that can contain omissions, wrong links, or retries. This separation follows the broader synthetic-data requirement that utility claims be tested alongside fidelity and failure modes rather than inferred from realism alone [11,12]. The frozen matrix combines three population families, four causal error mechanisms, five rare legitimate patterns, three policy profiles, and two levels each of anomaly and rare-case prevalence. Lawful cases have explicit compatibility requirements: late corrections require an existing progression event and valid supersession; policy transitions require service under the applicable historical policy; and grandfathering requires entitlement evidence linked to the employee, policy version, and event. The source-code boundary reduces direct generator-detector coupling, while controls and alternative models test whether the result depends only on the matched policy representation.

The matrix is a balanced fractional design rather than the full Cartesian product. Every level appears repeatedly across other factors, and each selected condition has 30 independent seeds. This gives paired comparisons variation in policy, workforce composition, error mechanism, lawful exception, and prevalence without making a single favorable scenario dominate the result.

| Design dimension | Frozen levels | Purpose |
| --- | --- | --- |
| Policy profile | Conservative, standard, accelerated | Changes service requirements, credits, and delays |
| Population profile | Stable administration, rapid expansion, merger migration | Changes career-stage and administrative-event distributions |
| Error mechanism | Approval bypass, missing increment import, batch retry, wrong employee link | Represents distinct causal administrative failures |
| Rare legitimate pattern | Recognized prior service, grandfathered policy, policy transition, delayed bulk recording, late correction | Tests unusual but lawful histories |
| Anomaly prevalence | 8%, 16% | Tests performance under different error frequencies |
| Rare-case prevalence | 4%, 10% | Tests changing exposure to lawful exceptions |

Generation proceeds in two layers. The latent administrative world contains employees, policy epochs, entitlements, and intended events. The observation ledger then represents what the information system recorded, including effective and recorded dates. Error interventions change the ledger through an explicit causal mechanism; rare legitimate interventions change the lawful world or its documented evidence. The model receives only the observed administrative fields. The causal mechanism, generated class, accepted generation attempt, and evaluation labels remain outside all feature matrices.

Exact disjoint allocation prevents one record from being assigned incompatible truth roles. Scenario construction rejects an attempted world when it cannot allocate the required ordinary, anomalous, and rare legitimate histories without overlap. The accepted generation-attempt number is stored, and the process is deterministic from the scenario seeds. This matters because silently lowering a requested class count would change denominators, while relabelling an incompatible record as clean would corrupt ground truth.

### 4.3 Deterministic Checks and Feature Representations

Deterministic validation returns findings with their evidence rather than a single boolean. Policy-agnostic checks cover date contradictions and duplicate event references, and flag unusually dense administrative activity for review, since a busy period is not by itself invalid; policy checks compare progression service with the supplied policy. Rules are reported both as a standalone baseline and as the first stage of a rules-plus-ML queue.

Explicit findings are never dropped to meet a nominal capacity. The original cascade uses a 10% capacity floor in which all deterministic findings are mandatory and ML fills any unused capacity, which complicates equal-budget comparison when rules alone exceed the floor. The primary design applies identical invariant checks to both pipelines and gives each an equal, fixed additional ML budget over the same invariant-negative histories. The complete policy-rules queue is reported as a secondary result.

**Feature representations.**

Raw features describe recorded activity without evaluating it against a policy: event counts, sanction and commendation counts, promotion and increment intervals, and administrative density. The policy-aware representation adds to a matched common core quantities such as service deficit, deficit ratio, and an unexplained-short-promotion indicator.

For a completed promotion with required service B, elapsed service M, commendation credit C, and sanction delay S, a conceptual policy deficit D is:

```text
D = max(0, B - M - C + S)
deficit_ratio = D / B
```

The sign convention matches the progression equation: credits reduce remaining service and sanctions increase it. The implementation evaluates this expression over the recorded history and event evidence rather than in isolation.

Consider an illustrative promotion requiring 36 months of service. The recorded history shows 34 elapsed months, a documented two-month commendation credit, and no sanction delay. Adjusted service is therefore 36 months and the deficit is zero. A raw model sees a short 34-month interval and may rank it as unusual; the policy-aware representation records that the interval is explained by valid evidence. If the same commendation is missing its employee or event link, the system does not silently grant the credit. It records missing evidence, computes the standard-policy view, and presents the uncertainty to the reviewer. This example explains the intended representational difference; it is not an experimental result.

The opposite case is also important. Suppose 40 months elapsed but an active six-month sanction delay applied before the promotion. Adjusted service is 34 months, leaving a two-month deficit. A raw interval alone looks ordinary because 40 exceeds the base requirement, while policy context exposes the unresolved delay. Thus policy awareness is not designed only to forgive unusual records. It can also make apparently ordinary timing suspicious when relevant restrictions are present.

Historical replay adds a second dimension. If a policy changed from 30 to 36 required months, a promotion effective under the earlier version must be assessed with the 30-month rule even when reviewed later. The event's effective date selects the applicable policy; its recorded date determines what was known to the system at a particular review time. A correction recorded later can change the present-review interpretation without rewriting what an administrator could have known earlier. These two views apply the valid-time and transaction-time distinction used in bitemporal databases [13], preventing current policy from being projected backwards and late information from being treated as if it had always been available.

| Illustrative history | Raw timing view | Policy-aware evidence view | Correct reviewer response |
| --- | --- | --- | --- |
| 34 months plus valid two-month credit | Unusually short | Requirement satisfied | Verify evidence; do not treat as an error |
| 40 months plus active six-month delay | Apparently sufficient | Two-month deficit | Review promotion and sanction evidence |
| Promotion under an earlier 30-month policy | Short under current rule | Sufficient under effective policy version | Apply historical policy |
| Credit mentioned but not linked to employee and event | Potentially short | Evidence insufficient | Request evidence; do not infer entitlement |

The matched representations use the same row population and the same number of columns. The distinction is what the final three columns express.

| Feature group | Examples | Interpretation |
| --- | --- | --- |
| Shared common core | Administrative-event count, sanction count, commendation count, event density, missing-field count, recorded-time lag | Information available to both methods |
| Raw additions | Promotion interval, increment interval, activity-timing summary | Observed timing without policy interpretation |
| Policy-aware additions | Service deficit, deficit ratio, unexplained short-promotion indicator | Timing expressed relative to applicable policy and evidence |
| Excluded truth fields | Generated class, intervention mechanism, latent identity, evaluation label | Preserved only for synthetic evaluation |

Policy features are calculated using the policy version effective for the event and the facts visible at the selected review time. Effective time answers when a policy or event applied; recorded time answers when the system learned it. Employee-specific entitlement is accepted only when the evidence links the employee, policy version, and relevant event. Missing entitlement or ambiguous history is represented as missing evidence rather than converted into a violation.

Controls (Figure 5) include raw features without the commendation-count shortcut, single-feature representations that add only one policy feature (or only the raw promotion interval) to the common core, wrong-policy context, and shuffled-policy context. They are needed because extra columns can improve a model through added information without correct use of the policy.

[[FIGURE:feature_design.png|Figure 5. Matched feature representations and controls as defined in the research code. Raw and policy-aware representations share a six-feature common core and add three features each. Single-feature representations keep the core plus one feature; the wrong-policy and shuffled-policy controls use the policy-aware columns with altered policy input.]]

### 4.4 Models, Thresholds, and Metrics

Interquartile-range and z-score methods are the transparent statistical baselines. Isolation Forest is fitted with continuous scores and `contamination="auto"`, so configured test prevalence is never passed in as a threshold. Within a scenario, every representation receives the same training records and seed budget.

Larger scores mean higher review priority. Predictions are produced at predefined operating points, AP is recomputed from the stored continuous scores, and runtime is recorded for every method.

The frozen evaluation keeps Isolation Forest as the primary scorer because it was specified before holdout inspection. Four alternatives test whether the feature effect is specific to that model. IQR and robust z-score use univariate robust deviation summaries; Local Outlier Factor measures local density; One-Class SVM learns a boundary around common observations. Their results are exploratory and cannot replace the primary model after the holdout has been seen.

| Comparison | Question addressed | Interpretation limit |
| --- | --- | --- |
| Raw versus policy-aware | Does policy-conditioned representation improve ranking at equal capacity? | Primary test only for Isolation Forest |
| Wrong-policy control | Does mismatched policy context reproduce the gain? | A weaker result for wrong policy supports attribution but does not prove causality |
| Shuffled-policy control | Does destroying the policy-record association remove the gain? | Shuffling may also change feature distributions |
| Single-feature ablations | Is the result dependent on one policy feature? | Similar performance does not identify a necessary cause |
| Alternative scorers | Does the direction persist under different ranking rules? | Exploratory sensitivity, not model selection |

**Thresholds and review budgets.**

Four views are retained. Average precision evaluates ranking without a test-selected threshold, while fixed-capacity recall reflects the bounded review task; this distinction matters because metrics encode different assumptions under severe class imbalance [7,8]. A fixed nominal top-10% operating point compares methods at equal review capacity; the queue size is `ceil(0.10 n)`, so with 72 test records per scenario it is 8 records (a realized 11.11%), or 96 alerts across 12 scenarios. A target false-positive-rate threshold is selected only on validation data. A validation-maximized F1 threshold is secondary and gets the same search budget for every representation, avoiding the test-set tuning and protocol bias documented in anomaly-detection evaluations [9,10].

Alongside the percentage, the paper reports alert counts, true and false positives, missed anomalies, and rare-legitimate and ordinary-clean alerts, which shows whether an improvement for one group only moves false alerts to another.

**Metrics.**

For true positives TP, false positives FP, false negatives FN, and true negatives TN:

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)
F1 = 2 * precision * recall / (precision + recall)
false_positive_rate = FP / (FP + TN)
```

Recall and AP are undefined for a scenario with no positive cases. Such scenarios remain in design and denominator tables and are excluded only from paired inference for those metrics, under a predeclared eligibility indicator. Older immutable artifacts that stored zero keep that historical convention, which cannot define the confirmatory endpoint.

Operational measures are anomalies found per 100 reviews, rare-legitimate reviews per 1,000 employees, missed anomalies per 1,000 employees, runtime, and total workload. Review cost, missed-error cost, and rare-escalation cost are sensitivity assumptions, not measured organizational values.

### 4.5 Paired Analysis and Experimental Estimands

Raw and policy-aware methods are paired within each scenario seed. For metric m and scenario i:

```text
delta_i = m(policy-aware_i) - m(raw_i)
```

Scenario seeds, not employees, are the independent units, because employees generated in one scenario share policy and population assumptions. Every included protocol-scale condition uses 30 independent seeds unless a written power or feasibility justification approves another count before the run. Development tooling reports mean and median paired differences, scenario bootstrap intervals, and paired sign-flip tests. Fixed-capacity recall is the single primary endpoint. The confirmatory secondary family contains AP, rare-legitimate false-alert rate, and ordinary-legitimate false-alert rate for the policy-aware versus raw comparison, with Holm's step-down adjustment [16,17] across these three two-sided tests. Precision and total false alerts are descriptive companions at fixed capacity. Controls, ablations, threshold analyses, per-class results, and utility sensitivity are exploratory.

The hierarchical interval resamples conditions and then seed-level paired differences within conditions. This retains the matrix structure instead of treating all employee rows as independent observations. The paired sign-flip test changes the direction of each scenario-level difference under the null and compares the observed mean with the resulting distribution. A fixed Monte Carlo seed makes the reported approximation reproducible. The exact pooled confusion counts remain useful for workload interpretation, but they are not substituted for scenario-level inference.

The secondary family is adjusted because testing several favorable-looking outcomes independently would inflate the chance of a false claim. Holm's procedure orders the three unadjusted p-values and compares them with progressively less stringent thresholds. The rare-legitimate endpoint remains reported even though it is unfavorable to the stronger hypothesis. Robustness slices and alternative models are clearly separated from this family because they reuse scenarios and serve as diagnostics rather than additional confirmatory tests.

### 4.6 Duplicate Detection

The duplicate experiment generates latent people and derives noisy records from them. It compares exact matching, normalized exact matching, and weighted similarity; candidate generation and pair scoring are evaluated separately because blocking can otherwise hide missed true pairs [15]. The similarity score is:

```text
similarity = 0.35 name + 0.30 date_of_birth
           + 0.25 identifier + 0.10 email
```

The score proposes candidate pairs for review and never merges records. A defensible final benchmark must separate blocking recall from pair scoring, use entity-disjoint partitions, include hard non-duplicates, and select its threshold on validation data. The existing run is preliminary secondary evidence only.

**Formal experimental estimands.**

Let s identify a generated scenario (its profiles, mechanisms, prevalence, and seeds), E_s the histories remaining after identical invariant checks, and Y_s their binary anomaly labels. A representation r and method m produce continuous scores a_{s,r,m} over E_s.

At fixed additional review capacity k_s, let A_s,r be the top-k_s alert set. The primary scenario-level recall difference is:

```text
delta_recall_s = recall(Y_s, A_s,policy) - recall(Y_s, A_s,raw)
```

Equal capacity requires |A_s,raw| = |A_s,policy| over the same E_s, and the complete rules queue is kept separate from this budget, so a representation cannot look better by raising more alerts. AP(Y_s, a_s,r,m) is a secondary ranking metric. Scenarios with no positive Y_s follow the eligibility rule of Section 4.4 and are never assigned zero or removed after score inspection.

With L_s the set of legitimate exceptional histories, the rare-legitimate flagged rate is |A_s,r intersect L_s| / |L_s|. It does not replace total false positives, because a method can reduce alerts in L_s while increasing them among ordinary-clean histories, as Section 6.3 shows.

The frozen implementation applies this estimand. An earlier development artifact, whose policy-specific features were constant after filtering, could not test it and remains excluded from the final result. The repaired design was verified in development and validation before the protocol and source revision were frozen.

### 4.7 Reproducibility, Domain Review, and Safety

Every experiment directory records the protocol status, full configuration, command line, Git revision, dirty-state flag, source hashes, Python and dependency versions, seeds, policy configuration, record-level predictions, scenario and aggregate metrics, and a SHA-256 manifest. Artifact directories are write-once and are published atomically from a staging directory only after successful completion (Figure 9).

The independent verification checks manifests, source hashes, confusion counts, rates, AP recomputed from stored scores, aggregate consistency, paired differences, bootstrap intervals, sign-flip results, and correction fields. Passing these checks shows that the arithmetic is reproducible, not that the estimand, scenario population, or policy assumptions are valid (Section 7.3).

**Domain review.**

Two academic reviewers with complementary policy and information-systems experience examined the research direction and advised continued development. Their feedback was qualitative rather than a blinded case-rating experiment: it did not produce record-level labels, agreement statistics, or an external estimate of realism. This distinction follows human-in-the-loop anomaly detection, where expert validation is part of the workflow but does not automatically create ground truth [14]. The synthetic holdout therefore remains an internally controlled evaluation, and external validity remains a limitation.

**Safety and decision boundary.**

The anomaly pipeline ends at a review recommendation. A high score does not establish misconduct, poor performance, ineligibility, or duplicate identity, and deterministic findings can be wrong if the supplied policy or history is incomplete. The interface must therefore show the applicable rule, source events, calculation, model signal, uncertainty, and reviewer action separately. Promotion approval, sanction and salary changes, user management, imports, and record edits are transactional and audited with before-and-after evidence, and duplicate candidates are never merged automatically. The evaluation measures prioritization quality, not autonomous personnel outcomes.

## 5 Implementation and Reproducibility

### 5.1 Architecture and Regression Tests

Research services live under `src/services/anomaly_detection`, and the independent scenario code under `src/research`. Synthetic data structures, feature extraction, deterministic checks, statistical baselines, Isolation Forest scoring, duplicate detection, metrics, and protocol evaluation are separate modules. The desktop application does not inherit scikit-learn, pandas, or plotting dependencies.

The separation reduces packaging risk, lets policy logic be tested without research models, and allows adapters to be inspected for leakage and the independent generator to be checked for prohibited imports.

**Policy-engine parity.**

Golden-history tests run the same progression cases through the pure policy arithmetic and the SQL-backed application, which also verifies adapter behavior. Further tests cover deterministic checks, generator determinism, feature values, threshold selection, wrong-policy and shuffled-policy controls, write-once artifacts, manifest tampering, source-hash mismatches, citation governance, and holdout refusal.

Regression tests cover previously observed defects, including incomplete causal event joins, truth-only prediction columns, unmanifested citation artifacts, evidence bound to the wrong paper, and overwrite attempts. A successful happy-path run alone cannot establish these boundaries.

### 5.2 Reproducibility and Continuous Integration

The literature review combines foundational work on Isolation Forest with recent studies of anomaly-detection evaluation, contextual features, synthetic-data validation, temporal information, explainability, and entity resolution. References were checked against publisher metadata or scholarly indexes, and legally accessible full texts were used where available. The review informed the paired-seed design, equal-capacity endpoint, validation-only operating decisions, temporal policy representation, and the separation of duplicate detection from progression anomalies.
**Continuous integration.**

GitHub Actions runs the Python test suite on pushes and pull requests, GitGuardian checks for exposed secrets, and citation schema and governance checks run without private credentials. Large research artifacts that do not suit every hosted CI run are verified locally.

CI shows only that the checked code and tests pass; it cannot approve a hypothesis, interpret a negative result, or authorize a holdout run.

### 5.3 Working Demonstration in MyHR

The desktop application includes a synthetic-only Anomaly Review workflow, so the pipeline can be inspected without reading source code or JSON artifacts. A reviewer selects a labelled development scenario and starts the analysis; the interface reports model-fitting, reserved validation, eligible evaluation, and review-queue counts separately. The run calls the same adapter, invariant checks, policy-history assessment, feature representations, Isolation Forest scorer, and fixed-capacity evaluation functions as the research services; the interface contains no second detector.

The review queue (Figure 6) separates deterministic contradictions from statistical suspicion and hides generated truth. Selecting an item opens the employee's evidence (Figure 7): source events, effective and recorded dates, policy ID and version, elapsed and required service, commendation credit, sanction delay, adjusted service, deficit, and evidence limitations. Generated labels appear only in a separate Synthetic Evaluation view, which reports injected-error, lawful-rare, and ordinary counts with a per-case list hidden by default.

The live comparison (Figure 8) gives the raw, policy-aware, wrong-policy, and shuffled-policy representations the same eligible residual records and additional review capacity, and charts recall, precision, and queue composition from the same result object used for the tables and the CSV and PDF exports. A model exception is shown as a failed run instead of silently returning a rules-only queue. Leaving the page during a run terminates the worker and discards the partial result; there is no separate cancel button. The workflow performs no database write or personnel action.

The demonstration is not a research experiment. It runs three fixed development scenarios with 120 synthetic employees each (72 fitting, 24 validation, and 24 evaluation histories), a 25-tree Isolation Forest, and a review capacity of 3 of 24 records (nominal 10%, realized 12.5% after rounding). The table below lists the outcomes produced by `scripts/verify_anomaly_demo.py` and the demonstration service at the reviewed revision.

| Scenario | Population | Raw TP/FP | Policy-aware TP/FP | Wrong-policy TP/FP | Shuffled-policy TP/FP | Rare legitimate alerted (each method) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ind-dev-01` | Stable administration | 2/1 | 3/0 | 2/1 | 2/1 | 0/2 |
| `ind-dev-07` | Rapid expansion | 0/3 | 0/3 | 0/3 | 0/3 | 0/2 |
| `ind-dev-12` | Merger and migration | 0/3 | 0/3 | 0/3 | 0/3 | 0/2 |

In-app demonstration outcomes at equal review capacity (24 evaluation records, 3 reviews per method). Each scenario has 3 injected errors among its evaluation records.

The first scenario is shown by default and in the figures. Its policy-aware queue finds all three injected errors, but this is a single realization of 24 records. In the other two scenarios no representation, including the controls, finds any injected error within three reviews. The demonstration shows that the pipeline runs end to end and that its outputs are traceable. These are inspected development observations that help to debug and demonstrate the pipeline. They are too few to support any conclusion about the research hypothesis.

[[FIGURE:anomaly_queue_light.png|Figure 6. Synthetic Anomaly Review queue after running the shared rule and Isolation Forest services. Generated truth is not shown in this operational view.]]

[[FIGURE:anomaly_evidence_light.png|Figure 7. Employee Evidence view for queue item I-00102, showing the profile and the service-adjustment arithmetic; the source events with effective and recorded dates are in the expandable history below.]]

[[FIGURE:anomaly_comparison_light.png|Figure 8. Method Comparison view for demonstration scenario ind-dev-01 (24 evaluation records, 3 reviews per method). Both charts and the exact table come from the same completed run. The wrong-policy and shuffled-policy controls are always shown; one 24-record scenario is not evidence of a policy effect (Section 6.4).]]

[[FIGURE:artifact_lifecycle.png|Figure 9. Write-once artifact lifecycle. Runs record provenance and a SHA-256 manifest before atomic publication; automated verification recomputes checksums and statistics, and failed artifacts are preserved with the defect recorded. Verification establishes reproducible arithmetic, not scientific validity.]]

## 6 Frozen Evaluation and Results

### 6.1 Evaluation Execution

The final evaluation used the frozen 36-condition matrix with 30 independent seeds per condition. Each scenario contained 120 synthetic employee histories divided into training, validation, and evaluation partitions. The one-time run produced 1,080 scenarios and 25,920 eligible evaluation histories. The artifact preserved scenario configuration, accepted generation attempt, source revision, dependency versions, seeds, event histories, policy epochs, entitlement evidence, predictions, metrics, and checksums.

The run was not repeated. Separate verification code checked manifest hashes, frozen source revision, matrix identity, scenario coverage, prediction membership, bitemporal event-policy links, stored arithmetic, paired comparisons, and control outputs before the results were interpreted. The earlier v1 attempt is not part of the result: it failed during scenario construction before publishing an artifact or exposing model outcomes.

### 6.2 Primary Endpoint: Recall at Fixed Review Capacity

The primary comparison asks how many injected errors are found when raw and policy-aware Isolation Forest receive the same eligible histories and the same additional review capacity after invariant deterministic checks. Both methods reviewed 3,240 residual records across the 1,080 scenarios.

| Primary residual comparison | Raw | Policy-aware |
| --- | ---: | ---: |
| Evaluation histories | 25,920 | 25,920 |
| Injected errors | 3,240 | 3,240 |
| Records reviewed | 3,240 | 3,240 |
| True positives | 1,058 | 1,282 |
| False positives | 2,182 | 1,958 |
| False negatives | 2,182 | 1,958 |
| Scenario-mean recall | 34.17% | 40.97% |
| Scenario-mean precision | 32.65% | 39.57% |

Policy-aware minus raw scenario-mean recall was +6.81 percentage points. The paired 95% interval was +3.54 to +10.23 percentage points, and the predeclared paired sign-flip test gave p approximately 0.000010. The interval excludes zero in the favorable direction. This supports the primary hypothesis within the frozen synthetic design.

[[FIGURE:holdout_primary_comparison.png|Figure 10. Frozen holdout comparison at equal review capacity. The left panel shows scenario-mean recall; the right panel shows pooled true and false positives within the identical 3,240-record review queues. Statistical inference uses paired scenario seeds rather than the pooled records.]]

### 6.3 Secondary Endpoints and Complete Workflow

Three secondary endpoints were declared as one Holm-adjusted family.

| Endpoint | Policy-aware minus raw | 95% paired interval | Holm-adjusted p |
| --- | ---: | ---: | ---: |
| Average precision | +6.64 pp | +3.57 to +9.73 pp | 0.00003 |
| Rare-legitimate flagged rate | -0.88 pp | -3.33 to +1.53 pp | 0.199 |
| Ordinary-clean flagged rate | -1.02 pp | -1.57 to -0.48 pp | 0.00003 |

Average precision and the ordinary-clean flagged rate support the policy-aware representation after multiplicity adjustment. The rare-legitimate result does not. Policy-aware ML flagged 229 of 2,160 generated rare-legitimate histories and raw ML flagged 248 of 2,160, but the paired interval crosses zero. The observed direction is favorable, yet the study cannot conclude that policy awareness reliably protects rare lawful behavior.

**Complete rules-plus-ML workflow.**

The residual comparison isolates the incremental contribution of ML. A secondary workflow comparison measures what an HR team would receive after combining invariant rules with each model.

| Workflow | Reviewed | True positives | False positives | False negatives | Rare-legitimate alerts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic rules only | 4,899 | 2,023 | 2,876 | 1,217 | 347/2,160 |
| Rules plus raw ML | 6,010 | 2,334 | 3,676 | 906 | 449/2,160 |
| Rules plus policy-aware ML | 6,010 | 2,402 | 3,608 | 838 | 431/2,160 |

Rules identify explicit contradictions with evidence; ML adds a fixed number of statistical review candidates. At the same complete queue size, policy-aware ML found 68 more errors than raw ML and produced 68 fewer false positives. The complete workflow should not be confused with the primary residual estimand because deterministic findings are shared by both pipelines.

### 6.4 Policy Controls, Ablations, and Alternative Models

The correct-policy representation found 1,282 residual anomalies. The wrong-policy control found 1,158, the shuffled-policy control 1,042, and the raw representation 1,058. In the separately stored Isolation Forest control contrasts, correct policy exceeded wrong policy by 4.31 recall percentage points (95% interval +1.83 to +7.13) and exceeded shuffled policy by 6.83 points (95% interval +3.63 to +10.32). These controls make a simple column-count explanation less plausible than in the earlier development experiments.

The result still does not prove that the entire gain is caused by correct organizational policy knowledge. Some policy-derived features can encode useful structure even when individual policy identities are imperfect, and the simulator and detector share domain concepts despite separate implementations. The ablations are therefore reported as attribution evidence, not as a causal decomposition.

**Alternative detection methods.**

The primary hypothesis concerns Isolation Forest. Four additional scorers were predeclared as exploratory sensitivity analyses and were not used to choose a replacement after the holdout was inspected.

| Scorer | Raw recall | Policy-aware recall | Difference |
| --- | ---: | ---: | ---: |
| IQR | 39.05% | 39.24% | +0.19 pp |
| Isolation Forest | 33.73% | 40.46% | +6.74 pp |
| Local Outlier Factor | 37.82% | 44.65% | +6.83 pp |
| One-Class SVM | 29.56% | 32.18% | +2.62 pp |
| Robust z-score | 36.94% | 37.85% | +0.90 pp |

[[FIGURE:holdout_model_sensitivity.png|Figure 11. Exploratory model sensitivity at the same fixed review capacity. Policy-aware features improve recall for all five scorers, but the effect size varies substantially and no post-hoc model selection is made.]]

The variation matters. It shows that the representation is not equally valuable to every anomaly-scoring rule and that the favorable primary result is partly model-dependent. Local Outlier Factor has the highest descriptive recall in this table, but selecting it after seeing the holdout would invalidate the protected comparison.

### 6.5 Robustness Across Conditions

Policy-aware minus raw recall was positive in all 19 predeclared descriptive slices: three policy profiles, three population profiles, four anomaly mechanisms, five rare-legitimate patterns, two anomaly rates, and two rare-pattern rates. Differences ranged from +0.83 percentage points for approval-bypass scenarios to +17.41 points for wrong-employee-link scenarios.

[[FIGURE:holdout_robustness.png|Figure 12. Descriptive policy-aware minus raw recall across the 19 predeclared condition slices. Every difference is positive, but the slices reuse scenario histories and are not separate multiplicity-adjusted hypotheses.]]

This consistency answers the robustness question more strongly than a single pooled average, but it has limits. Slice estimates share data, have different numbers of scenarios, and were not assigned individual confirmatory tests. The study therefore reports them as evidence that the primary effect is not confined to one configured condition, not as 19 independent replications.

### 6.6 Duplicate Detection and Explanations

Duplicate detection remains a separate entity-resolution task. Its candidate generation, pair universe, similarity threshold, blocking recall, workload, runtime, and memory are evaluated independently from progression anomalies. These results do not contribute to RQ1-RQ3 and are not combined with employee-level anomaly metrics.

MyHR also displays an evidence-oriented review workflow: source events, policy version, elapsed service, commendation credit, sanction delay, adjusted service, deficit, and missing evidence. This demonstrates the software integration requested for the project. The optional usability study was not conducted, so the paper makes no claim that the explanation improves interpretation accuracy or task completion time.

### 6.7 Development Lessons

Two earlier failures materially shaped the final experiment. First, a rules-first design removed every record carrying policy variation before ML, leaving the policy features constant and making the comparison unable to test the hypothesis. Second, malformed historical-transition cases produced apparent false alerts that were actually responses to impossible event sequences. These findings led to an invariant-only primary rule boundary, linked entitlement evidence, bitemporal event-policy replay, exact disjoint label allocation, and stronger artifact validation.

The failures are methodological history, not final results. Their value is that they were detected before the frozen evaluation and were not silently discarded or reinterpreted as evidence for the hypothesis.

## 7 Discussion

### 7.1 Answers to the Research Questions

**RQ1:** Policy-aware Isolation Forest improved progression-anomaly ranking over matched raw features at the same review capacity in the frozen synthetic holdout. The +6.81-point scenario-mean recall difference, its paired interval, and the average-precision result support this conclusion within the experiment.

**RQ2:** The advantage remained descriptively positive across every predeclared policy, population, mechanism, rare-pattern, and prevalence slice. This is evidence of robustness within the matrix, not proof of transfer to other organizations, policy systems, or data-generating processes.

**RQ3:** The proposed reduction in rare-legitimate false alerts was not established. The pooled count was lower for policy-aware ML, but the paired interval crossed zero and the Holm-adjusted test was not significant. A benefit to ordinary clean records was supported, so the policy-aware queue was more precise overall without demonstrating the specific rare-case protection originally expected.

### 7.2 Interpretation of the Policy-Conditioned Signal

Raw features describe counts and intervals. Policy-aware features express those observations relative to the policy that applied at the event time, including required service, credits, delays, recognized service, and evidence-backed exceptions. This can place two numerically similar histories in different administrative contexts. The control results are consistent with the model using that context because correct policy outperformed wrong and shuffled policy.

This explanation remains an inference from the design and controls. It is not a feature-level causal proof. The generator and detector use separate code paths, but both represent the same domain concepts; synthetic truth can therefore still favor the feature vocabulary chosen for the detector.

### 7.3 Validity and Generalization

The strongest internal-validity protections are fixed hypotheses, equal review budgets, validation-only threshold decisions, paired seeds, a separate simulator, causal truth excluded from model inputs, wrong-policy and shuffled-policy controls, ablations, and a one-time verified holdout. These controls reduce leakage and selective reporting but do not make the synthetic histories equivalent to organizational data.

External validity is the main limitation. No private employee data were used, which protects privacy but prevents direct estimates of real error prevalence, policy complexity, missingness, reviewer behavior, or operational cost. Two complementary academic experts gave qualitative feedback supporting continued work, but no case-level ratings, blinded agreement measurement, or adjudication dataset was collected. The study therefore cannot quantify scenario realism or inter-reviewer agreement.

The experiment also evaluates one policy formalization and a bounded set of populations and error mechanisms. New organizations would need their own policy history, import mapping, evidence rules, and validation data. A policy-aware model is only as reliable as that information.

A real-world follow-up should begin with a retrospective, read-only sample rather than a live personnel workflow. The organization would first map each historical policy version and its effective dates, then extract only the fields required by the frozen feature definitions. Two qualified reviewers should independently examine a stratified sample containing model alerts, rule findings, and unflagged controls without seeing model scores. Their initial judgements, evidence used, disagreements, and adjudication should be retained. This would estimate both data quality and reviewer uncertainty instead of treating either reviewer as an infallible label source. The frozen synthetic result could then be tested without changing features or thresholds; any later redesign would require a separate evaluation cohort.

Several shifts could reduce performance. A new HR system may record events in batches, omit policy-version links, use different commendation categories, or contain business units with distinct progression tracks. Error prevalence may also be lower than in the synthetic matrix, which would reduce precision even if ranking quality were unchanged. These are not edge conditions to hide through preprocessing. They are deployment conditions that should be measured, reported by subgroup and time period, and shown as missing evidence when the policy reconstruction is incomplete.

### 7.4 Statistical Interpretation

Scenario seeds, not individual employee rows, are the independent paired units. Pooled counts are included to explain operational workload, while inference uses scenario-level differences stratified by condition. Zero-positive scenarios remain in the artifact and have undefined recall and average precision for those endpoints rather than being assigned favorable values.

The primary endpoint was tested once. The three secondary endpoints form one Holm-adjusted family. Alternative scorers, controls, ablations, and robustness slices are supporting analyses. Their results should guide future hypotheses, not create new confirmatory claims from the already inspected holdout.

### 7.5 Human Review, Privacy, and Fairness

An anomaly score is a review priority, not an error probability or personnel judgement. The interface keeps deterministic evidence, statistical suspicion, generated truth, and reviewer action separate. A reviewer can inspect source history and missing evidence before deciding whether correction or escalation is appropriate.

The experiments use fictional records and run locally. This avoids exposing employee data to cloud services, but production deployment would still require device security, access control, encrypted backups, retention policy, and audit protection. The study makes no demographic fairness claim. Such an analysis requires lawful protected-attribute handling, a defined harm model, adequate representation, and organizational oversight.

### 7.6 Practical Implications

The result supports further evaluation of policy-aware ranking as a decision-support feature, accompanied by the raw model and controls in research evaluation. Historical policy versions and effective versus recorded time are product requirements, not optional research metadata. When policy or entitlement evidence is missing, MyHR should show uncertainty and request review rather than assert a violation.

The finding also supports a modest engineering principle: deterministic checks should handle explicit contradictions, while ML should prioritize the remaining ambiguous workload. Combining both without reporting their separate contributions can make a model appear effective merely because rules found the easy cases.

The operational decision remains whether the extra anomalies found justify the review burden and maintenance of historical policy data. In the protected evaluation both methods reviewed the same number of records, so the comparison isolates prioritization rather than staffing. A deployment study would additionally measure review time, correction yield, unresolved cases, and whether alerts are concentrated on particular roles or periods. It should compare these quantities with the existing manual process, not only with another model. If reviewers cannot verify an alert from source evidence, the item should remain unresolved rather than being counted as a confirmed error.

Duplicate detection should follow the same restraint. Similar names or identifiers are evidence for comparison, not permission to merge records. A production benchmark would preserve entity-disjoint partitions, measure blocking misses separately from pair-scoring errors, and include difficult non-duplicate pairs such as family members or transliteration variants [15]. The current duplicate module demonstrates the engineering path but does not contribute evidence to the progression-anomaly hypothesis.

## 8 Conclusion

This research implemented and evaluated a policy-aware anomaly-detection workflow for workforce progression. The final frozen synthetic holdout shows that policy-aware Isolation Forest improved scenario-mean recall by 6.81 percentage points over matched raw features at the same review capacity. Average precision and ordinary-clean false-alert rates also improved after multiplicity adjustment, and the recall advantage was positive across all predeclared descriptive slices.

The third research question has a less favorable answer: rare-legitimate false alerts were lower in pooled counts, but the paired evidence was inconclusive. The study therefore supports policy-aware ranking within the tested synthetic domain while rejecting a stronger claim that it has proven protection for rare lawful behavior or real-world deployment value.

The main contributions are the formal policy representation, rules-first and ML-second architecture, independent scenario simulator, equal-capacity evaluation, falsification controls, bitemporal evidence model, reproducible artifact pipeline, and working in-application review interface. Future work should evaluate the frozen method on organization-specific historical data where lawful, conduct a case-level blinded realism review, study reviewer comprehension, and assess demographic and operational consequences before deployment.

## References

[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in 2008 Eighth IEEE International Conference on Data Mining, 2008, pp. 413–422. DOI: 10.1109/ICDM.2008.17.

[2] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation-Based Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, vol. 6, no. 1, pp. 1–39, 2012. DOI: 10.1145/2133360.2133363.

[3] S. Han, X. Hu, H. Huang, M. Jiang, and Y. Zhao, “ADBench: Anomaly Detection Benchmark,” in Advances in Neural Information Processing Systems 35, 2022, pp. 32142–32159. DOI: 10.52202/068431-2329.

[4] N. Vaska, K. Leahy, and V. Helus, “Context-Dependent Anomaly Detection with Knowledge Graph Embedding Models,” in 2022 IEEE 18th International Conference on Automation Science and Engineering (CASE), 2022, pp. 2020–2027. DOI: 10.1109/CASE49997.2022.9926631.

[5] Z. Li, Y. Zhu, and M. van Leeuwen, “A Survey on Explainable Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, vol. 18, no. 1, pp. 1–54, 2024. DOI: 10.1145/3609333.

[6] M. Carletti, M. Terzi, and G. A. Susto, “Interpretable Anomaly Detection with DIFFI: Depth-Based Feature Importance of Isolation Forest,” Engineering Applications of Artificial Intelligence, vol. 119, art. 105730, 2023. DOI: 10.1016/j.engappai.2022.105730.

[7] T. Saito and M. Rehmsmeier, “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets,” PLOS ONE, vol. 10, no. 3, e0118432, 2015. DOI: 10.1371/journal.pone.0118432.

[8] S. Sørbø and M. Ruocco, “Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection in Time Series,” Data Mining and Knowledge Discovery, vol. 38, no. 3, pp. 1027–1068, 2024. DOI: 10.1007/s10618-023-00988-8.

[9] D. Fourure, M. U. Javaid, N. Posocco, and S. Tihon, “Anomaly Detection: How to Artificially Increase Your F1-Score with a Biased Evaluation Protocol,” in Machine Learning and Knowledge Discovery in Databases. Applied Data Science Track, Lecture Notes in Computer Science, Springer, 2021, pp. 3–18. DOI: 10.1007/978-3-030-86514-6_1.

[10] P. Röchner, S. Klüttermann, K. Kammler, F. Rothlauf, E. Müller, and D. Schlör, “We Need to Rethink Benchmarking in Anomaly Detection,” arXiv preprint arXiv:2507.15584, 2025. DOI: 10.48550/arXiv.2507.15584.

[11] G. Steinbuss and K. Böhm, “Benchmarking Unsupervised Outlier Detection with Realistic Synthetic Data,” ACM Transactions on Knowledge Discovery from Data, vol. 15, no. 4, pp. 1–20, 2021. DOI: 10.1145/3441453.

[12] L. Hansen, N. Seedat, M. van der Schaar, and A. Petrovic, “Reimagining Synthetic Tabular Data Generation through Data-Centric AI: A Comprehensive Benchmark,” in Advances in Neural Information Processing Systems 36, 2023, pp. 33781–33823. DOI: 10.52202/075280-1466.

[13] G. Neelamegam, J. Bhogal, P. Samimi, and Ö. Öztürkoğlu, “Comprehensive Insights into Bitemporal Databases: A PRISMA-Guided Systematic Literature Review,” Journal of Data, Information and Management, vol. 8, no. 2, pp. 71–96, 2026. DOI: 10.1007/s42488-026-00162-x.

[14] Z. Deng, X. Xuan, K.-L. Ma, and Z. Kong, “A Reliable Framework for Human-in-the-Loop Anomaly Detection in Time Series,” ACM Transactions on Interactive Intelligent Systems, vol. 16, no. 2, pp. 1–23, 2026. DOI: 10.1145/3778167.

[15] T. Wang, H. Lin, X. Han, X. Chen, B. Cao, and L. Sun, “Towards Universal Dense Blocking for Entity Resolution,” arXiv preprint arXiv:2404.14831, 2024. DOI: 10.48550/arXiv.2404.14831.

[16] J. Demšar, “Statistical Comparisons of Classifiers over Multiple Data Sets,” Journal of Machine Learning Research, vol. 7, pp. 1–30, 2006. Available: https://www.jmlr.org/papers/v7/demsar06a.html (accessed 1 November 2026).

[17] S. Holm, “A Simple Sequentially Rejective Multiple Test Procedure,” Scandinavian Journal of Statistics, vol. 6, no. 2, pp. 65–70, 1979. Available: https://www.jstor.org/stable/4615733 (accessed 1 November 2026).

[18] K. Krippendorff, “Reliability in Content Analysis: Some Common Misconceptions and Recommendations,” Human Communication Research, vol. 30, no. 3, pp. 411–433, 2004. DOI: 10.1111/j.1468-2958.2004.tb00738.x.

## Appendix: Reproduction

Code availability. The source code, tests, figure scripts, and documentation are in the repository https://github.com/ibrahimify/MyHR. The tag `tdk-2026-revised-results` identifies this revised report, while `tdk-2026-submission` preserves the original submission. The large record-level evaluation artifact is stored separately; its repository manifest records the frozen source revision, configuration, dependencies, seeds, source hashes, and output checksums.

Settings. Isolation Forest is fitted with `contamination="auto"` and a recorded model seed per scenario. The primary review budget is 10% of the residual evaluation histories, rounded up, for every representation. Dataset, split, and model seeds, scenario configurations, and exact package versions are stored in `metadata.json`, `scenario_configs.csv`, and the dependency declaration. Scenario seeds are the resampling unit for all intervals and tests. The in-app demonstration uses 25 trees and is not the holdout evaluation.

Commands, run from the repository root in PowerShell:

```text
pip install -r requirements.txt -r requirements-research-lock.txt
python -m pytest tests
python scripts/verify_tdk_citations.py --require-local-artifact
$d = "<path-to-verified-holdout-artifact>"
python -m scripts.audit_tdk_protocol_artifact $d
python scripts/build_tdk_holdout_report.py $d
python scripts/verify_anomaly_demo.py
```
