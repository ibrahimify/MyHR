# MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression

**Author:** Muhammad Ibrahim Shoeb

**Supervisor:** Dr. Husam Al-Magsoosi

**Institution:** Budapest University of Technology and Economics, Faculty of Electrical Engineering and Informatics

**Paper language:** English
**Status:** Supervisor review draft, 30 October 2026

## Abstract

Workforce progression systems apply promotion, commendation, sanction, and salary-increment policies to complex administrative records. Detecting erroneous records is challenging because unusual histories may be legitimate under the applicable policy. A short promotion interval, for example, may reflect a recorded commendation rather than an error. This research investigates whether incorporating explicit progression-policy context into machine-learning features can reduce false anomaly alerts while preserving detection of actual errors, thereby reducing manual HR review workload by prioritising records for evidence-based attention.

The study uses MyHR, an offline HR decision-support application, as the experimental platform. A formal progression model specifies service requirements, commendation credits, sanction delays, policy changes, and annual increments independent of promotion. Isolation Forest models analyse sanction frequencies, promotion intervals, and administrative-event patterns using raw and policy-conditioned features. Deterministic validation addresses explicit inconsistencies, while eligibility explanations present the applicable rules, adjustments, and supporting records. A separate similarity-based matching component identifies potential duplicate employee records. Anomaly and duplicate alerts support human review rather than automatic personnel decisions or record merging.

Evaluation uses reproducible synthetic histories containing documented injected errors and rare legitimate cases, with separate training, validation, and test partitions. Comparisons include rule checks, contextual statistical baselines, and Isolation Forest models with and without policy-conditioned features. Measures include precision, recall, F1 score, false-positive rate, review workload, and runtime. Duplicate detection is evaluated separately. Successive audits exposed and repaired defects in synthetic truth, temporal replay, pairwise evaluation, and provenance. In the latest clean exploratory progression artifact, deterministic rules flagged 0 of 72 test-split rare-legitimate histories. Policy-aware minus raw recall at equal review capacity was +0.0278 with a 95% paired bootstrap interval from -0.0278 to +0.1019 and sign-flip p=0.6875. No advantage was demonstrated, and the interval does not establish equivalence. Employee-specific grandfathering, distinct knowledge-time replay, expert realism review, exact scenario approval, and confirmatory holdout evaluation remain incomplete.

Keywords: machine learning, anomaly detection, Isolation Forest, workforce progression, rule-based decision support, synthetic data, duplicate detection, explainability

## 1 Introduction

### 1.1 Motivation

Employee progression decisions are assembled from administrative facts that develop over time. Service duration, role level, performance evidence, commendations, disciplinary sanctions, policy versions, and recorded approvals can all influence whether an employee is eligible for promotion or an annual salary increment. A conventional information system can store these events and implement explicit eligibility rules, but data-quality review is harder than rule execution. Some errors are direct contradictions, such as an end date before a start date. Other suspicious histories are only unusual in context. A promotion after a short interval may be erroneous, or it may be lawful because a commendation reduced the required service period. A delayed administrative action may indicate missing data, or it may reflect a legitimate batch-recording process.

This distinction matters operationally. A detector that flags every unusual history creates unnecessary review work and may unfairly escalate legitimate exceptional cases. A detector that suppresses too many alerts can miss real administrative errors. The practical goal is not autonomous personnel decision-making. It is a review queue in which explicit violations are explained deterministically and less direct patterns are ranked for an authorized human. The scientific question is whether representing the applicable policy helps that ranking beyond raw event counts and intervals.

MyHR provides a suitable experimental platform because it already contains an auditable workforce-progression model. It is a standalone Python and PySide6 desktop application backed by SQLite and SQLAlchemy. It manages employee and organization data, performance reviews, promotions, commendations, sanctions, annual increments, imports, reports, and immutable audit records. The application calculates progression from source records rather than storing a manually edited percentage. This creates a defined policy boundary against which research features and explanations can be checked.

### 1.2 Problem Statement

The research problem has three parts. First, explicit policy and data contradictions should be detected reliably and explained with their evidence. Second, residual histories that are not explicit violations may still deserve review because their event patterns are unusual. Third, legitimate policy-dependent histories must not be treated as errors merely because they are rare. These parts cannot be collapsed into a single accuracy score. They require separate deterministic and statistical components, explicit review-capacity comparisons, complete denominators, and a protected evaluation design.

Unsupervised anomaly detection is attractive when labelled errors are scarce, but it does not know what an organization considers lawful. Isolation Forest isolates points through random recursive partitions and assigns higher anomaly scores to observations requiring shorter paths [1,2]. It can rank unusual event vectors without a large labelled training set. The score, however, describes statistical isolation rather than administrative invalidity. The same employee history can be anomalous under one policy and legitimate under another. This motivates policy-conditioned features and controls that test whether the supplied policy information is genuinely useful.

### 1.3 Research Questions

The study is organized around three questions:

1. Does explicit policy context improve progression-anomaly ranking beyond raw administrative features and deterministic validation?
2. Does any observed advantage remain across employee populations, anomaly mechanisms, policy configurations, prevalence levels, and random seeds?
3. At equal review capacity, can policy context reduce false alerts on rare but legitimate histories without missing genuine administrative errors or merely moving false alerts to ordinary clean records?

Duplicate-record detection is evaluated separately. It is a pairwise entity-resolution problem rather than an employee-level progression anomaly. Combining it with progression labels would obscure both tasks and create misleading denominators.

### 1.4 Research Approach

The proposed architecture is rules first and machine learning second. Deterministic checks identify explicit date, event, and policy contradictions. Statistical baselines and Isolation Forest rank records that remain candidates for contextual review. Raw and policy-aware representations are evaluated on the same scenario, split, and model seeds. Wrong-policy, shuffled-policy, and feature-ablation controls are retained even when unfavorable. Methods are compared at equal review budgets, and every alert remains a recommendation to a human reviewer.

Synthetic histories provide known ground truth without exposing private employee data. This choice also creates a serious methodological risk: a generator can encode the same rule used by the detector and make the proposed method appear successful by construction. The study therefore separates the original policy-shaped generator from an independently implemented administrative-world simulator, records causal truth and observation ledgers, and treats generator independence as necessary but not sufficient. Scenario realism and conceptual independence still require human review.

[[FIGURE:architecture.png|Figure 1. Rules-first MyHR research architecture. Deterministic findings and anomaly scores support a human review queue; neither component automatically changes personnel records.]]

### 1.5 Contributions and Non-Claims

The implemented work contributes: a formal progression model shared with the application; deterministic validation with evidence-rich findings; raw and policy-aware feature families; statistical and Isolation Forest baselines; validation-only thresholds; equal-budget comparisons; wrong-policy, shuffled-policy, and ablation controls; an independent development simulator; write-once experiment artifacts with checksums; independent re-computation of stored metrics; and a separate duplicate-candidate experiment.

The development evidence contributes an important negative methodological result. In an early residual design, deterministic filtering consumed the policy signal and forced all three policy-specific features to constant zero. That comparison was structurally unable to test the hypothesis and was preserved rather than presented as a null result. A later audit also invalidated apparent transition false alerts because the generator had created genuine contradictions. Both failures motivated the corrected design and stronger provenance checks.

The paper makes no claim that policy-aware machine learning is universally better, that current synthetic rates generalize to organizations, or that the system should automate promotion, sanction, salary, or record-merging decisions. The final holdout has not been generated or accessed.

## 2 Background and Related Work

### 2.1 Isolation-Based Anomaly Detection

Isolation Forest is based on the observation that anomalies are often easier to isolate than ordinary points. Randomly selecting a feature and split value creates isolation trees; the expected path length across trees becomes an anomaly score [1]. The later isolation-based formulation analyses the method more broadly and explains its computational behavior [2]. The method is attractive for MyHR because it produces a continuous ranking, handles multiple numeric event features, and does not require labelled anomalies during fitting.

The method does not provide a policy judgement. A high score means that a feature vector is isolated relative to the fitted population. It does not establish that the record is invalid, unlawful, or harmful. This is why the MyHR workflow keeps deterministic policy evidence, model score, threshold, and human decision separate. The model is fitted only on permitted training records; test prevalence is not supplied as a threshold shortcut.

ADBench demonstrates that anomaly-detection performance varies substantially by dataset, supervision assumptions, and method family [3]. This supports evaluating transparent baselines rather than presenting a single model in isolation. MyHR includes deterministic checks, interquartile-range and z-score baselines, raw Isolation Forest, policy-aware Isolation Forest, controls, and ablations. The purpose is not to find a universally winning detector but to determine what the policy representation contributes under matched conditions.

### 2.2 Context and Policy Awareness

Context-dependent anomaly detection distinguishes observations that are unusual only under a particular situation. Knowledge-based context can change how an observation should be interpreted [6]. Workforce progression is a strong example: identical elapsed service can be compliant under one policy version and non-compliant under another. Commendation credits, sanction delays, employee track, recognized prior service, and effective policy period can alter the expected progression path.

Policy-aware features are therefore not simply extra event counts. They are transformations relative to an explicit rule set. A service deficit, for example, compares adjusted completed service with the requirement applicable to the employee and decision. This can make the model more aligned with administrative meaning, but it can also leak the answer if the synthetic generator uses exactly the same residual to define anomalies. The study uses wrong-policy and shuffled-policy controls because a genuine policy signal should weaken when policy identity is incorrect or destroyed.

### 2.3 Explainability and Review Evidence

Explainable anomaly-detection research distinguishes global understanding of a detector from local evidence for a specific alert [4]. DIFFI provides feature-importance information for Isolation Forest by analysing tree depth and feature use [5]. Feature importance can help describe a model score, but an HR reviewer also needs administrative evidence: the policy version, required and observed service, commendation and sanction adjustments, source records, and deterministic findings.

MyHR prioritizes this evidence-rich explanation. A model feature attribution, if later added, would be clearly labelled as model evidence rather than a policy fact. Explanation quality is a separate evaluation problem. The submitted abstract makes a user study optional, and the current paper does not claim usability results that were not collected.

### 2.4 Evaluation Under Class Imbalance

Administrative anomalies are expected to be rare. Under severe class imbalance, receiver-operating-characteristic summaries can appear favorable even when the precision of the review queue is poor. Precision-recall analysis is often more informative in such settings [10]. Average precision summarizes a ranking without selecting a test threshold, but it remains sensitive to prevalence. Every AP value therefore needs the number of records and positive cases entering the ranking.

Operational threshold metrics remain necessary because HR teams review a finite number of cases. MyHR reports precision, recall, F1 score, false-positive rate, alert count, alert rate, anomalies found per 100 reviews, and rare-legitimate reviews per 1,000 employees. Methods are compared at the same nominal review capacity. Scenario-level means and pooled numerators and denominators are kept separate.

Evaluation protocol can itself create inflated results. Biased partitioning, threshold selection on test labels, favorable seed selection, and contamination settings derived from known test prevalence can all make anomaly detection appear stronger than it is [9]. Recent benchmark criticism also emphasizes that conclusions may depend on a narrow evaluation pipeline [14]. MyHR records separate dataset, split, and model seeds; selects thresholds on validation data; retains negative results; and locks the final holdout until the protocol is frozen.

### 2.5 Synthetic Data and Circularity

Synthetic data allows controlled injection of known administrative errors and rare legitimate histories. Realistic synthetic evaluation, however, requires more than plausible-looking rows. Steinbuss and Bohm show the importance of varying synthetic outlier characteristics and data domains [7]. MyHR additionally treats defining anomalies through the detector's own decisive feature as a circularity risk; this is a design inference applied to the present experiment, not a prescription attributed to that paper. Data-centric synthetic evaluation similarly emphasizes downstream behavior and multiple profiles rather than one visual or distributional similarity score [8].

The original MyHR generator and policy-aware detector share policy concepts. This makes the original validation results useful for engineering but vulnerable to circularity. The independent simulator avoids imports from the detector, feature extractor, application policy engine, and original generator. It constructs an administrative world and a separate observation ledger. Nevertheless, source-code separation does not ensure conceptual separation. The current residual experiment proves this point: deterministic filtering removes the cases for which the policy residual varies, leaving no policy-specific signal for the model.

### 2.6 Historical Policy and Bitemporal Representation

Administrative systems must distinguish when a fact or policy is effective in the modeled world from when it is recorded in the database. Bitemporal research calls these valid time and transaction time [15]. The distinction supports historical reconstruction, corrections, and auditability. It is directly relevant to promotions decided under an earlier policy, recognized service recorded later, and administrative corrections entered after an event.

The preserved development artifact predates the approved temporal contract and intentionally exposes the failure created by replaying current policy over lawful historical decisions. This is a constructed counterexample, not a prevalence estimate. The corrected research adapter now carries policy versions, jurisdiction, effective and recorded dates, recognized-service evidence, and correction or retry provenance, and replays the applicable historical policy. Production database migration and final protocol freeze remain pending.

### 2.7 Human Review and Duplicate Detection

Human-in-the-loop anomaly detection treats expert validation as part of the workflow rather than assuming model output is truth [16]. MyHR follows the same boundary: findings are prioritized for review, and consequential actions require an authorized person. The proposed expert-realism review is blinded to model scores and generated labels so that reviewers judge history plausibility and evidence sufficiency rather than confirm the detector.

Duplicate detection is evaluated as entity resolution. Candidate generation and pair scoring must be separated because evaluating every possible pair can make false-positive rates look deceptively small. Dense-blocking research reinforces the importance of candidate workload and blocking recall [12]. The MyHR experiment compares exact matching, normalized exact matching, and weighted similarity, while keeping each latent person inside one partition. This secondary task does not supply evidence for the progression-anomaly hypothesis.

### 2.8 Research Gap

The audited literature supports Isolation Forest, contextual anomaly detection, imbalanced evaluation, synthetic-data caution, bitemporal history, explanation, and entity resolution. It does not establish a standard policy-aware workforce-progression benchmark. The contribution is therefore deliberately bounded: formalize one progression domain, build reproducible controls, test whether policy context changes ranking under matched workload, and document when the experiment cannot answer that question. A claim that no prior system combines these elements everywhere would exceed the evidence from the performed search.

## 3 MyHR and the Formal Progression Model

### 3.1 Application Boundary

MyHR is a local-first desktop system. The graphical interface is implemented in PySide6, persistent records use SQLite through SQLAlchemy, and research dependencies are isolated from the packaged application. Employee management, organization hierarchy, performance reviews, promotions, commendations, sanctions, annual increments, imports, reports, and audit records form the operational context. The research package reads structured representations and does not authorize changes to personnel data.

[[FIGURE:myhr_ui.png|Figure 2. MyHR employee-management interface used as the application context for policy evidence and human review.]]

### 3.2 Progression Arithmetic

Let B denote the base number of service months required for the next level, M the completed months since the last promotion or recognized start point, C the months of valid commendation credit, and S the months of active sanction delay. Adjusted service A and remaining service R are defined as:

```text
A = M + C - S
R = max(0, B - A)
```

Eligibility and bounded progress are:

```text
eligible = (R = 0)
progress = clamp(floor(100 A / B), 0, 100)
```

This form makes the sign of each policy adjustment explicit. A commendation brings the employee closer to the requirement; a sanction delays eligibility. The implementation also records the source events and policy configuration used in the calculation. Promotions remain manual decisions even when service requirements are complete.

### 3.3 Promotion, Sub-Race, and Annual Increment

A promotion race represents service toward the next level. Sub-race checkpoints provide annual progress and salary-increment timing without being independent promotions. Employees in the `Other` track do not have a degree-based promotion race, but they can receive annual increments, commendations, sanctions, and performance reviews. This separation prevents the system from inventing a promotion path for roles governed by different progression rules.

Annual salary increments are independent of promotion. Finishing a yearly interval can make an increment due even when the employee is not eligible for a new level. Conversely, promotion changes level and salary under an explicit approval workflow. This distinction is preserved in both application logic and audit records.

### 3.4 Performance and Manual Approval

Performance reviews contain a weighted rubric for goal delivery, role competencies, conduct and reliability, and teamwork and leadership. The score is evidence shown during promotion review, not an automatic replacement for policy eligibility. A candidate may complete a race while having no recent review or poor performance. The confirmation dialog therefore displays policy status, latest performance, active sanctions, commendations, salary change, warnings, and a direct route to the employee profile. The authorized reviewer approves or cancels the action, and every result is audited.

### 3.5 Administrative Evidence

The research representation distinguishes employee facts, administrative events, policy epochs, generated truth, and observed records. This separation matters when the observation is incomplete or recorded late. A missing increment import may be a data error even when the underlying organizational event occurred. A wrong-employee sanction link changes the observation ledger without changing the intended world. The independent generator preserves these causal distinctions for future artifacts, while the original immutable artifact retains only its historical schema.

[[FIGURE:policy_timeline.png|Figure 3. Example progression timeline showing base service, commendation credit, sanction delay, and the need to retain the policy effective at the decision date.]]

### 3.6 Policy-Engine Parity

Research calculations must agree with the actual application on shared histories. Golden-history tests cover clean progression, commendation credit, sanction delay, promotion reset, completed service, and non-progression tracks. The application calls a pure promotion-race calculation shared with research-facing code, while SQL-backed tests verify adapter behavior. Passing parity tests establishes implementation agreement for the tested histories; it does not prove that the policy itself is organizationally correct.

### 3.7 Temporal Limitation

Current-policy replay is insufficient for historical decisions. The research record retains policy identity and version, valid and recorded times, jurisdiction, recognized service, approval evidence, and correction or retry provenance. Version matching and future-effective exclusion are implemented, but employee-level grandfathering entitlement and separate decision-time versus later-review knowledge views are not. The bitemporal contract is therefore partial, research-only, and neither a migrated production schema nor a frozen confirmatory protocol.

## 4 Research Methodology

### 4.1 Task Separation

The primary task ranks employee histories for progression-related administrative review. Positive classes include inconsistent dates, unexplained frequent promotions, excessive sanctions, and unusual administrative intervals. A broadly labelled rare-legitimate class represents histories that are unusual but intended to be lawful under the generated policy context. Clean records include both ordinary and exceptional non-error histories.

Duplicate detection is a separate pairwise task. Its positive unit is a pair or entity cluster rather than one employee history. It uses identity attributes and corruption mechanisms that do not belong in progression anomaly features. Reporting the tasks separately prevents the enormous number of easy nonduplicate pairs from diluting progression metrics and prevents duplicate labels from changing employee-level anomaly prevalence.

### 4.2 Synthetic Record Contract

Each synthetic history contains an employee identifier, employee track, service and role dates, promotion events, commendations, sanctions, annual increments, performance evidence, and administrative timestamps needed by the selected scenario. Generated labels and causal truth are excluded from prediction features. Dataset, split, and model seeds are recorded separately. Records belonging to the same latent person remain within one partition for duplicate detection.

The taxonomy distinguishes the nominal scenario pattern from the realized per-record mechanism. This distinction became important in the independent stress test: non-progression employees assigned to a transition-pattern scenario can realize a delayed-recording mechanism instead. Future development artifacts preserve both values, complete event fields, policy epochs, and whether the causal event was observed or intentionally omitted. Existing artifacts are immutable and are not retroactively rewritten.

| Category | Example mechanism | Expected evidence | Evaluation role |
| --- | --- | --- | --- |
| Inconsistent dates | Event before employment start | Direct chronological contradiction | Deterministic baseline and anomaly label |
| Frequent promotion | Promotion before adjusted service requirement | Promotion interval and applicable policy | Policy check and anomaly ranking |
| Excessive sanctions | Dense or repeated sanction history | Event count, timing, resolution, service delay | Statistical and policy context |
| Unusual interval | Abnormally short administrative gap | Event intervals and process context | Statistical ranking |
| Wrong employee link | Sanctions attached to another employee | Observation ledger differs from generated world | Independent residual mechanism |
| Missing import | Increment event omitted from observation | World event exists but record is absent | Independent residual mechanism |
| Approval bypass | Promotion without required approval evidence | Explicit workflow violation | Deterministic check |
| Batch retry | Duplicate or dense administrative events | Repeated event references and intervals | Deterministic check |
| Rare legitimate | Previous policy, recognized service, or delayed recording | Temporal policy and evidence context | False-alert analysis |

### 4.3 Data Partitions and Holdout Boundary

Seeds 2026 to 2030 were inspected during early feature development and are permanently development-only. Protocol-development scenarios may be generated and inspected while diagnosing implementation and design failures. Validation scenarios may support threshold selection and feature-family decisions. The final holdout is not defined, generated, inspected, or scored until the protocol, scenario matrix, feature families, thresholds, and analysis are frozen with human approval.

This boundary is enforced in code. The protocol runner refuses a holdout run purpose, and existing metadata records `holdout_accessed: false`. A future one-time holdout must use a frozen source revision and complete manifest. Any later change would require a new protocol version and a new holdout family while preserving the original result.

[[FIGURE:experiment_flow.png|Figure 4. Evaluation lifecycle. Development and validation remain inspectable; the final holdout is unavailable until a human-approved protocol freeze.]]

### 4.4 Original Scenario Matrix

The protocol-v2 generator varies policy profile, population profile, anomaly mechanism, rare-legitimate pattern, prevalence, and independent seeds. It produces matched raw and policy-aware representations on the same records. Thirty development and thirty validation scenarios were generated with 600 employees per scenario and 120 test records per scenario, giving 3,600 validation test histories.

The original generator is useful for testing pipeline mechanics and known policy interactions, but it is conceptually close to the detector. Several injected anomaly mechanisms become direct policy deficits, and the policy-aware representation can mirror the generator's construction. Results from this family are therefore development diagnostics, not transferable evidence.

### 4.5 Independent Administrative-World Simulator

The independent simulator is implemented in the standard library and does not import detector features, deterministic checks, the application policy engine, or the original generator. It first constructs an administrative world and then derives an observation ledger that can contain omissions, wrong links, or retries. Twelve development scenarios combine three population families with four causal error mechanisms and rare patterns.

This source-code boundary reduces one form of leakage but does not guarantee a valid experiment. Conceptual dependence can remain if deterministic filtering and feature construction erase the policy information the comparison is intended to test. The independent run is explicitly a stress test, not a holdout.

### 4.6 Deterministic Checks

Deterministic validation returns evidence-rich findings rather than a single boolean. Policy-agnostic checks address date contradictions, duplicate event references, and dense administrative activity. Policy checks assess progression service against the supplied policy. Rules are reported both as a standalone baseline and as the first stage of a rules-plus-ML queue.

Explicit findings are not silently discarded to satisfy a nominal capacity. The original cascade uses a 10% capacity floor: all deterministic findings remain mandatory, and ML fills any unused nominal capacity. This is operationally conservative but complicates equal-budget interpretation when rules alone exceed the floor. The approved primary redesign instead applies identical invariant checks to both pipelines and allocates an equal, fixed additional ML budget among the same invariant-negative histories. The complete policy-rules queue is reported secondarily.

### 4.7 Feature Representations

Raw features describe recorded activity without evaluating it against a policy. They include event counts, sanction and commendation counts, promotion intervals, increment intervals, and administrative density. The policy-aware representation augments a matched common core with quantities such as service deficit, deficit ratio, and an unexplained-short-promotion indicator.

For a completed promotion with required service B, elapsed service M, commendation credit C, and sanction delay S, a conceptual policy deficit D is:

```text
D = max(0, B - M - C + S)
deficit_ratio = D / B
```

The sign convention is consistent with the progression equation: credits reduce remaining service and sanctions increase it. The actual implementation handles history and event evidence rather than applying this isolated expression blindly.

Controls include raw features without the commendation-count shortcut, one policy-residual feature at a time, a complete matched policy representation, wrong-policy context, and shuffled-policy context. These controls are needed because adding columns can improve a model through information volume without demonstrating correct policy use.

[[FIGURE:feature_design.png|Figure 5. Matched raw and policy-aware representations with wrong-policy, shuffled-policy, and ablation controls.]]

### 4.8 Models and Statistical Baselines

Interquartile-range and z-score methods provide transparent statistical baselines. Isolation Forest is fitted with continuous scores and `contamination="auto"`; configured test prevalence is never passed as a known threshold. Every representation receives the same training records and seed budget within a scenario.

The model score is oriented so that larger values indicate higher review priority. Predictions are produced for predefined operating points, but average precision is recomputed from stored continuous scores. Runtime is recorded for every method. No model output changes an employee record or triggers an automatic personnel action.

### 4.9 Thresholds and Review Budgets

Four views are retained. Average precision evaluates ranking without a test-selected threshold. A fixed top-10% operating point compares methods at equal nominal review capacity. A target false-positive-rate threshold is selected only from validation data. A validation-maximized F1 threshold is secondary and receives the same search budget for all representations.

The fixed budget is operationally interpretable, but a percentage alone is not sufficient. The paper reports alert counts, true and false positives, missed anomalies, rare-legitimate alerts, and ordinary-clean alerts. This reveals whether an apparent fairness improvement merely moves false alerts between clean subgroups.

### 4.10 Metrics

For true positives TP, false positives FP, false negatives FN, and true negatives TN:

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)
F1 = 2 * precision * recall / (precision + recall)
false_positive_rate = FP / (FP + TN)
```

Average precision summarizes the precision-recall ranking. It is undefined for a scenario with no positive cases under the intended primary interpretation. The current implementation historically stored zero for such scenarios. That convention is preserved in the development artifact but is explicitly disputed and cannot silently define a confirmatory endpoint.

Operational measures include anomalies found per 100 reviews, rare-legitimate reviews per 1,000 employees, missed anomalies per 1,000 employees, runtime, and total workload. Cost sensitivity treats review cost, missed-error cost, and rare-escalation cost as assumptions rather than measured organizational values.

### 4.11 Paired Scenario Analysis

Raw and policy-aware methods are paired within each scenario seed. For metric m and scenario i:

```text
delta_i = m(policy-aware_i) - m(raw_i)
```

Scenario seeds, not individual employees, are the intended independent units because employees generated under one scenario share policy and population assumptions. Development tooling reports mean and median paired differences, scenario bootstrap intervals, and paired sign-flip tests. Exploratory families can receive Holm adjustment, but the repository has not preserved the full text of the original Holm paper; the current paper therefore describes the implemented correction without presenting that reference as independently verified evidence.

### 4.12 Duplicate Detection

The duplicate experiment generates latent people and derives noisy records. Three methods are compared: exact matching, normalized exact matching, and weighted similarity. The implemented similarity score is:

```text
similarity = 0.35 name + 0.30 date_of_birth
           + 0.25 identifier + 0.10 email
```

The score suggests candidate pairs for review and never merges records automatically. A defensible final benchmark must separate blocking recall from pair scoring, use entity-disjoint partitions, include hard nonduplicates, and select its threshold on validation data. The existing run is retained as preliminary secondary evidence only.

### 4.13 Formal Experimental Estimands

The employee record is not the independent experimental unit. Let s identify a generated scenario, containing a policy profile, population profile, anomaly mechanism, rare-legitimate mechanism, prevalence, dataset seed, split seed, and model seed. Let E_s be the histories remaining after identical invariant checks, and let Y_s be their binary anomaly labels. A representation r and method m produce continuous scores a_{s,r,m} over E_s.

At fixed additional review capacity k_s, let A_s,r be the top-k_s alert set. The primary scenario-level recall difference is:

```text
delta_recall_s = recall(Y_s, A_s,policy) - recall(Y_s, A_s,raw)
```

Equal capacity requires |A_s,raw| = |A_s,policy| over the same E_s. The primary summary is the paired scenario-level recall difference across the frozen scenario population. Precision, total false alerts, and rare-legitimate false-alert rates accompany it. Average precision AP(Y_s, a_s,r,m) is a secondary ranking metric.

Scenarios with no positive Y_s remain in denominator tables, while recall and AP are marked undefined and excluded from paired inference for those metrics under the predeclared eligibility rule. They are never assigned zero or removed after score inspection. The complete rules queue remains separate from the identical additional ML budget so a representation cannot appear better merely by raising more alerts.

Rare-legitimate workload is reported with its own denominator. Let L_s be the set of legitimate exceptional histories. The rare-legitimate flagged rate is |A_s,r intersect L_s| / |L_s|. This rate does not replace total false positives. A method can reduce alerts in L_s while increasing alerts among ordinary-clean histories. The original validation residual experiment demonstrates exactly this transfer.

The estimand is implemented in the development code with invariant-only filtering, identical residual populations, and equal additional review capacity. The historical artifact still has constant policy-specific features and remains invalid for this estimand. The formulas above do not convert that artifact into confirmatory evidence; a clean-revision development and validation run, independent audit, and protocol freeze remain required.

### 4.14 Reproducibility and Artifact Audit

Every experiment directory records the protocol status, complete configuration, command line, Git revision, dirty-state flag, source hashes, Python and dependency versions, seeds, policy configuration, record-level predictions, scenario metrics, aggregate metrics, and SHA-256 manifest. Artifact directories are write-once. Process-owned staging directories are atomically published only after successful completion.

The independent auditor verifies manifests, source hashes, confusion counts, rates, average precision from stored scores, aggregate consistency, paired differences, bootstrap intervals, sign-flip results, and correction fields. Passing this audit establishes reproducibility of implemented arithmetic. It does not establish that the estimand, scenario population, or policy assumptions are scientifically valid.

### 4.15 Approved Blinded Realism-Review Method

Synthetic correctness is assessed by code and invariant tests; organizational realism requires a different review. The prepared expert packet contains fictional histories without model scores, generated labels, or method names. Reviewers would assess whether the history is plausible, whether it appears ordinary, legitimately exceptional, erroneous, or indeterminate, whether the evidence is sufficient, how confident they are, and whether escalation is appropriate.

Two independent reviewers with complementary HR-policy and information-systems expertise make disagreement observable rather than silently resolving it through one opinion. Their original ratings and reasons are retained before evidence-based adjudication, and genuinely ambiguous cases remain ambiguous. The review does not allow cases to be rewritten to improve model metrics. Exact reviewer identities, sample size, agreement statistic, acceptance criterion, sampling seed, and operational form remain pending. The prepared packet has not been distributed.

### 4.16 Safety and Decision Boundary

The anomaly pipeline ends at a review recommendation. A high score does not establish misconduct, poor performance, ineligibility, or duplicate identity. Deterministic findings can also be wrong if the supplied policy or historical evidence is incomplete. The interface must show the applicable rule, source events, calculation, model signal, uncertainty, and reviewer action separately.

Important operations remain transactional and audited. Promotion approval, sanction changes, salary changes, user management, import, and record edits produce before-and-after evidence. Duplicate candidates require explicit review and are never automatically merged. This boundary is a product requirement and a research assumption: evaluation measures prioritization quality, not autonomous personnel outcomes.

## 5 Implementation and Reproducibility

### 5.1 Module Boundaries

Research services are isolated under `src/services/anomaly_detection`, with independent scenario code under `src/research`. Synthetic data structures, feature extraction, deterministic checks, statistical baselines, Isolation Forest scoring, duplicate detection, metrics, and protocol evaluation have separate modules. The desktop application does not automatically inherit scikit-learn, pandas, or plotting dependencies.

The separation reduces packaging risk and clarifies ownership. Application policy logic remains testable without loading research models. Research adapters can be audited for information leakage. The independent generator can be checked for prohibited imports. These boundaries support reproducibility but do not replace conceptual review.

### 5.2 Golden Histories and Tests

Golden-history tests run the same progression cases through pure policy arithmetic and SQL-backed application behavior. Additional tests cover deterministic checks, generator determinism, feature values, threshold selection, wrong-policy and shuffled-policy controls, artifact write-once behavior, manifest tampering, source-hash mismatches, citation governance, and holdout refusal.

Adversarial tests were added when audits found gaps. Examples include rejecting incomplete causal event joins, truth-only prediction columns, unmanifested citation artifacts, wrong-paper evidence binding, and overwrite attempts. This practice matters because a successful happy-path experiment does not prove that the audit boundary works.

### 5.3 Literature and Claim Governance

Literature discovery uses free direct clients for OpenAlex, arXiv, Crossref, and Semantic Scholar. Optional API keys remain outside Git. Each reference is deduplicated, its identifiers and retrieval provenance are recorded, and each scientific claim is linked to an evidence locator. The independent citation audit currently validates 18 references and 15 claim records. Sixteen legally accessible full texts are preserved locally.

Two references remain metadata-only: Holm's multiple-comparison paper and Krippendorff's reliability paper. Claims that depend on their full text remain explicitly unverified. The paper does not hide that limitation or convert metadata verification into scientific evidence.

### 5.4 Continuous Integration

GitHub Actions runs the Python test suite on pushes and pull requests. GitGuardian checks for exposed secrets. Citation schema and governance checks run without requiring private credentials. Local verification additionally audits large research artifacts that are not suitable for every hosted CI run.

CI answers whether the checked code and tests pass in the configured environment. It does not approve a research hypothesis, interpret a negative result, or authorize a holdout. Those decisions remain human responsibilities.

### 5.5 Traceability

| Paper statement | Primary evidence |
| --- | --- |
| Progression arithmetic | `src/services/promotion_policy.py` and business-logic tests |
| Research policy history | `policy_history.py` and golden-history tests |
| Raw and policy features | `features.py` and protocol tests |
| Independent generator boundary | `src/research/independent_scenarios.py` |
| Validation results | `validation_c5878ca7b927ccd2` artifact and audit |
| Independent results (pre-fix development) | `independent_development_e342bd4acf39b06b` artifact and audit |
| Current repaired independent results | `independent_development_b866ae2aa1b4b479` artifact and audit (commit `1942718`, status: verified) |
| Structural feature collapse | Independent hostile review and source trace |
| Citation claims | Bibliography, provenance registry, and evidence ledger |
| Holdout status | Protocol, artifact metadata, runner refusal, and roadmap |

[[FIGURE:artifact_lifecycle.png|Figure 6. Write-once artifact lifecycle and independent verification boundary.]]

## 6 Development Experiments and Results

### 6.1 Interpretation Boundary

All results in this section are development or validation diagnostics. They were inspected during feature and protocol work and are permanently ineligible for final confirmatory claims. The results are valuable because they reveal generator coupling, feature collapse, and temporal-policy failure. They do not establish deployment accuracy or policy-aware superiority.

### 6.2 Protocol-V2 Validation Family

The corrected validation artifact contains 30 scenarios and 3,600 test histories: 360 labelled anomalies, 3,240 non-anomalies, 200 rare-legitimate histories, and 3,040 ordinary-clean histories. Deterministic policy rules found 351 of 360 anomalies with no false positive in this scenario family. This high recall is partly caused by generator interaction: several injected excessive-sanction histories also become explicit service-policy violations. It must not be generalized to real organizations.

| Validation method | Alerts | TP | FP | FN | Scenario-mean F1 | Scenario-mean AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic policy rules | 351 | 351 | 0 | 9 | 0.986 | 0.977 |
| Rules plus raw Isolation Forest | 408 | 357 | 51 | 3 | 0.907 | 0.998 |
| Rules plus policy-aware Isolation Forest | 408 | 358 | 50 | 2 | 0.910 | 1.000 |

The policy-aware cascade finds one additional anomaly and produces one fewer false alert at the same total alert count. The paired mean AP difference is +0.0016 with a stored 95% bootstrap interval from 0.0000 to 0.0041, sign-flip p = 0.25, and exploratory adjusted p = 1.0. This does not establish a meaningful advantage. The near-perfect AP also reflects the original generator's close relationship to policy features.

[[FIGURE:validation_counts.png|Figure 7. Corrected validation alert outcomes. Counts are pooled across 30 scenarios; the high rules performance is partly a generator interaction.]]

### 6.3 Original Rule-Negative Validation

Removing every deterministic policy finding leaves only 9 labelled anomalies among 3,249 histories. At the nominal 10% budget, both residual models raise 340 alerts, find all 9 anomalies, and produce 331 false positives.

| Residual validation method | Alerts | TP | FP | FN | Mean F1 | Mean AP | Rare-legitimate alerts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw Isolation Forest | 340 | 9 | 331 | 0 | 0.047 | 0.161 | 59/200 |
| Policy-aware Isolation Forest | 340 | 9 | 331 | 0 | 0.047 | 0.181 | 27/200 |

Policy-aware features avoid 32 alerts among rare-legitimate histories, but the same 32 false alerts move to ordinary-clean histories. Total precision, anomaly recall, and review workload do not improve. This result directly answers why subgroup false-alert counts cannot be interpreted without total false positives and capacity.

The paired AP difference is +0.0194 with a stored interval from -0.0417 to 0.0889. Twenty-four of the thirty rule-negative validation scenarios contain no residual positive case and historically store AP as zero. The reported scenario means and interval therefore depend on this disputed convention. The original generator leaves too few informative residual scenarios to estimate incremental ML value convincingly; no alternative scenario-eligibility rule is selected after inspection.

### 6.4 Historical Independent Stress Test Invalidated

The first independent simulator run produced 12 test scenarios with 864 histories, 108 labelled anomalies, and 72 broadly labelled rare-legitimate histories. It recorded 39 apparent false alerts among those rare histories. Later semantic audits showed that this generator produced contradictory transition histories and invalid duplicate truth. The following numbers are retained solely to explain why the design was rejected; they are not current performance evidence.

After deterministic filtering, 759 histories remain, including 42 labelled anomalies and 717 negatives. At equal nominal budget, both models raise 81 alerts.

| Independent residual method | Alerts | TP | FP | FN | Mean F1 | Scenario-mean AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw Isolation Forest | 81 | 26 | 55 | 16 | 0.304 | 0.3616 |
| Policy-aware Isolation Forest | 81 | 25 | 56 | 17 | 0.298 | 0.3621 |

The stored paired AP difference is +0.0005 with interval [-0.1173, 0.1079], sign-flip p = 1.0, and adjusted exploratory p = 1.0. These values are arithmetically reproducible under the implemented convention. They are not evidence of equivalence or a policy effect.

[[FIGURE:independent_ap.png|Figure 8. Primary exploratory recall comparison in repaired artifact b866ae2aa1b4b479. The interval crosses zero; the result does not demonstrate superiority or equivalence.]]

### 6.5 Historical Structural Failure of the Central Comparison

In the historical residual design, the policy-aware representation contained a six-feature common core plus policy service deficit, policy deficit ratio, and an unexplained-short-promotion indicator. The full-policy residual filter kept only records with no policy finding. The same policy assessment emitted a finding whenever service deficit was positive. Consequently, every retained record had zero for all three policy-specific features.

The policy-aware model therefore has no varying policy signal. Its effective varying dimension is the six-feature common core, whereas the matched raw model retains three additional varying raw features. Differences in ranking cannot be attributed to policy context. The experiment as designed could not test the primary hypothesis.

This is stronger and more precise than describing the result as merely inconclusive. An inconclusive estimate would arise from valid but uncertain evidence. Here the intended explanatory variable is structurally absent after filtering. The correct response is to preserve the run, diagnose the design, and seek approval for a new estimand rather than tune features against inspected outcomes.

[[FIGURE:feature_collapse.png|Figure 9. Historical design failure and corrected architecture. The original rule gate consumed the signal intended for ML; the repaired design limits the primary gate to invariant contradictions and assigns equal additional ML review capacity.]]

Six of the twelve scenarios also contain no residual positive case. The implementation stores AP as zero for these scenarios, while the approved future design treats recall and AP as undefined and excludes those scenarios from paired inference for those metrics under a predeclared eligibility rule. Including structural zeros halves both reported AP means and changes uncertainty. Restricting the development calculation to the six informative scenarios still yields a very wide interval and does not establish an advantage. The approved rule must be implemented and frozen before generating any confirmatory scenario.

### 6.6 Invalidated Historical-Policy Interpretation

The preserved `39/72` and later `8/72` readings do not estimate false alerts on lawful transition histories. The second audit showed that the corresponding generators created genuine contradictions, including promotions before hire and insufficient service. Those alerts were therefore responses to defective records, not evidence that current-policy replay rejected lawful decisions. Both interpretations are invalidated.

[[FIGURE:policy_alerts.png|Figure 10. Audit history of the transition scenario. Earlier apparent false-alert readings were invalidated; the repaired exploratory run records 0/72 deterministic alerts among test-split rare-legitimate histories.]]

The audit still motivates temporal modeling as a requirements issue, but the current experiments do not quantify its real-world frequency or benefit. Policy identity, version, effective time, recorded time, recognized service, and correction provenance are represented in research records. Employee-specific grandfathering and separate decision-time versus later-review replay remain incomplete.

### 6.7 Corrected Exploratory Development Artifact

Artifact `b866ae2aa1b4b479` was generated from clean commit `1942718` after the second-audit repairs. The strengthened artifact audit reports `verified`, 12 scenarios, 864 test histories, 108 anomalies, 72 rare-legitimate histories, and `holdout_accessed: false`. Deterministic policy checks produced 63 true positives, no false positives, and 45 false negatives; none of the 72 rare-legitimate histories was flagged.

At the primary equal review capacity, policy-aware minus raw residual recall was +0.0278 across 12 paired scenarios. The paired 95% bootstrap interval was [-0.0278, +0.1019], and the sign-flip p-value was 0.6875. Precision difference was +0.0313 with interval [-0.0313, +0.1042]. Average precision favored the policy representation in this inspected development run, but AP is secondary, multiplicity-adjusted p-values are 1.0, and the scenario definitions remain pending approval. No superiority, inferiority, or equivalence claim follows.

The corrected duplicate evaluation uses an explicit evaluation universe and set membership for every TP, FP, FN, and TN. Exact methods use the complete partition-local pair universe, while similarity methods report blocking recall and metrics within their declared candidate universe separately.

[[FIGURE:duplicate_results.png|Figure 11. Duplicate-evaluation contract after repair. Pair ground truth is entity-contained; blocking recall, candidate-universe classification, end-to-end matching, workload, runtime, and memory are reported separately. No final duplicate-performance claim is made.]]

### 6.8 Result Summary

The historical runs demonstrate why passing tests and reproducible arithmetic are insufficient when labels or evaluation universes are wrong. The corrected exploratory artifact demonstrates that the repaired pipeline executes reproducibly, but its 12 inspected scenarios are below protocol scale and use scenario definitions pending approval. Its primary interval crosses zero. The current evidence therefore supports the framework and its auditability, not a performance or product-effectiveness claim.

### 6.9 Robustness Slices and What They Can Show

The stored artifacts include slices by policy profile, population profile, anomaly mechanism, rare pattern, prevalence, and operating point. These tables are useful for diagnosing whether a method's behavior is concentrated in one constructed condition. They are not independent experiments when several slices reuse the same scenario histories. Consequently, the paper does not count every slice as a new sample or select the slice with the most favorable difference.

Mechanism-specific residual comparisons describe the surviving rule-negative task rather than the full anomaly taxonomy. The repaired artifact preserves per-mechanism counts and feature-variation checks, but twelve inspected scenarios are too few to separate population, mechanism, rare pattern, and random realization. These slices remain diagnostics rather than confirmatory subgroup effects.

Population slices similarly combine organizational assumptions with one random realization per population-mechanism cell. A merger-migration scenario may contain more delayed records than a stable-administration scenario, but one realization cannot establish a general population effect. A redesigned validation matrix needs repeated seeds within each cell, preserving scenario seed as the unit while allowing variability to be estimated separately from configured factors.

### 6.10 Utility Sensitivity

The pipeline stores a transparent cost model rather than one claimed business value:

```text
total cost = review_count * review_cost
           + false_negatives * missed_error_cost
           + rare_legitimate_alerts * rare_escalation_cost
```

Each cost is a sensitivity parameter. Review time can be estimated operationally; the cost of missing an error or escalating a legitimate exception depends on organizational context and cannot be inferred from synthetic labels. The paper therefore reports how conclusions change across cost ratios rather than choosing one ratio that favors a method.

The current residual comparison does not justify a utility advantage. Although both representations receive the same review budget, the primary recall interval crosses zero and operational costs remain assumptions. Any favorable utility result can depend on the relative cost assigned to missed anomalies, rare-legitimate reviews, and ordinary false alerts. Those weights must be declared and reviewed rather than hidden inside a score.

## 7 Discussion and Threats to Validity

### 7.1 Answer to the Research Questions Today

The corrected exploratory run did not demonstrate that policy context improves residual anomaly ranking. Its primary recall difference was positive but imprecise, with a paired interval crossing zero. The original generator remains conceptually coupled to the policy representation, and the repaired independent scenarios remain inspected and pending approval. No superiority, inferiority, or equivalence conclusion follows.

Robustness across changed policies and populations cannot yet be established because the repaired comparison contains only twelve inspected scenario units and its scenario definitions remain pending approval. Development infrastructure varies these factors, but protocol-scale repeated seeds and independent validation are still required.

The rare-legitimate objective remains operationally important. The original validation run shows that reducing alerts in one legitimate subgroup can merely move the same number of false alerts elsewhere. The invalidated transition scenarios show why generated lawful status must be checked semantically before interpreting subgroup metrics. A valid future experiment must therefore report both subgroup and total false alerts at equal workload.

### 7.2 Rules First, ML Second

Direct contradictions should not be rediscovered by an opaque model. Deterministic checks provide stable evidence, while ML is better suited to ranking residual patterns that are unusual without being explicit violations. The division also supports explanation: a reviewer can distinguish a factual policy conflict from a statistical suggestion.

The boundary must be designed carefully. If deterministic rules remove every history for which policy residuals vary, a residual model cannot test the value of those residuals. On 29 October 2026, the methodology was approved (per Ibrahim, relaying supervisor-aligned decisions; see the authorship note below) as a redesign that restricts the primary residual filter to invariant contradictions, compares raw and policy-aware ML at equal additional review capacity, and reports the complete rules-plus-ML queue secondarily. This design is implemented in the development code and exercised by the current development artifacts, but it is not frozen: the exact scenario definitions remain pending human approval (see `TDK_PROTOCOL_CHANGE_PROPOSALS.md`), and protocol freeze plus holdout access require a separate dated approval.

### 7.3 Internal Validity

The strongest internal-validity threat is generator-detector circularity. Original anomaly labels and detector features share progression concepts. Wrong-policy, shuffled-policy, and ablation controls help, but they do not certify independence. The separate simulator reduces code reuse, while a blinded expert review is intended to assess realism. A future holdout should be specified as business histories first and translated to records by an implementation isolated from detector code.

Threshold leakage is controlled by validation-only selection, and test prevalence is not passed to Isolation Forest. Seed and scenario selection remain visible. Negative and adverse results are retained. The final protocol must predeclare primary-eligible scenarios and zero-positive handling before any protected data are generated.

### 7.4 Statistical Validity

The independent stress test has only twelve scenario units, six of which contain residual positives. Population, mechanism, rare pattern, and random realization cannot be separated cleanly. Bootstrap intervals assume an implicit exchangeable scenario population that is not yet defined. The current interval is descriptive development output.

The draft protocol expects at least 30 independent scenario seeds per primary condition unless a power analysis supports another number. Repeated seeds within population-mechanism cells are needed to separate scenario factors from random realization. One predeclared primary endpoint avoids interpreting a large family of exploratory tests as independent discoveries.

### 7.5 Construct and External Validity

Synthetic labels establish correctness relative to the generator, not organizational truth. No private employee data were used, which is a privacy strength but an external-validity limitation. Feature ranges, policy transitions, missing-data mechanisms, and utility costs require domain calibration. A blinded review by qualified domain reviewers can test plausibility and evidence sufficiency, but reviewer qualifications, sample size, agreement measure, and adjudication rule remain pending.

The repaired policy-transition scenario is a proposed contract test, not a rate estimate, and still requires human approval. Likewise, high deterministic recall in a synthetic generator does not imply that rules will find nearly every real administrative error.

### 7.6 Temporal Validity

Policy-aware analysis is only as correct as the supplied policy history. Applying today's rule to yesterday's decision can create false violations. A robust design needs policy identity, valid time, transaction time, jurisdiction, recognized-service evidence, and corrections. Bitemporal storage supports reconstruction, but it does not decide the organization's substantive policy. Those semantics require human approval and migration planning.

### 7.7 Explanation and Human Factors

The application presents evidence and keeps authorization with HR. This reduces the risk of an anomaly score becoming an automatic employment decision. It does not remove automation bias: reviewers may over-trust a numerical score or a polished explanation. The interface should distinguish facts, rules, model signals, uncertainty, and the final human action.

The optional usability study could compare binary eligibility indicators with evidence-rich explanations using interpretation accuracy, completion time, and usability ratings. It is omitted from the current empirical claims because no participants were recruited and no approved protocol was run.

### 7.8 Privacy, Security, and Fairness

The experiments use fictional records and do not require cloud processing. Local-first deployment can support data sovereignty, but offline storage is not automatically secure. Access control, backups, audit integrity, device protection, and organizational procedure still matter.

The current study does not make a fairness claim across protected demographic groups. Synthetic subgroup behavior and rare-legitimate false alerts are useful diagnostics, but demographic fairness requires lawful attributes, a defined harm model, adequate representation, and separate analysis. The system must not infer sensitive traits or use anomaly ranking as a proxy for disciplinary action.

### 7.9 Reproducibility Versus Validity

Checksums, manifests, source hashes, CI, and independent arithmetic audits make the work reproducible. They cannot make an invalid estimand valid. The most important outcome of the infrastructure is that it exposes exactly what was calculated and why the central comparison failed. This distinction is central to the paper's scientific contribution.

### 7.10 Approved Redesign and Remaining Freeze Gate

The approved primary design retains a residual task after removing only invariant contradictions. It introduces policy context that is not consumed by that gate, including historical policy identity, effective-versus-recorded timing, recognized-service evidence, jurisdiction, and correction provenance. Raw and policy-aware Isolation Forest receive the same additional review capacity over the same remaining records, with recall at that capacity as the primary endpoint. The residual boundary and endpoint are implemented; the temporal model remains partial as described in Section 3.7.

The end-to-end rules-plus-ML review queue remains a secondary operational analysis. It measures the system a client would use, but it is reported separately because rules can dominate the queue and obscure the incremental contribution of the ML representation.

The invariant rule boundary, research bitemporal schema, equal-capacity primary endpoint, and zero-positive treatment are implemented and covered by regression tests. The scenario matrix, explicit correction cases, duplicate latent-person design, exact secondary analysis family, dependencies, source revision, expert review, and protocol still require independent verification and freeze before protected generation.

The approval refines the hypothesis after inspecting development diagnostics; it does not convert those diagnostics into confirmatory evidence. New development and validation runs must test the redesigned pipeline. The scenario specification, feature family, endpoint, capacity, seeds, and analysis must then be frozen before protected generation.

### 7.11 Practical Implications for MyHR

Historical-policy handling remains a product requirement even though the earlier false-alert quantification was invalidated. A client importing old promotion records needs the system to distinguish the policy effective at the decision date from the policy active today. Without that evidence, MyHR should display an indeterminate status and request review rather than assert a violation. Import templates and migration tools would need policy identifiers, effective dates, recorded dates, and evidence for recognized service or corrections.

The same principle applies to explanations. A reviewer should see which facts are present, which assumptions were inferred, and which evidence is missing. A model score can prioritize the record, but an incomplete history should not be converted into a confident personnel judgement. These requirements make the application safer and also create better research data because future labels can distinguish missing evidence from confirmed error.

| Threat | Current mitigation | Remaining weakness |
| --- | --- | --- |
| Generator-detector circularity | Independent simulator, controls, preserved negative findings | Approved review method not yet executed; conceptual realism unverified |
| Test-threshold leakage | Validation-only thresholds | Deployment calibration unresolved |
| Favorable seed selection | Recorded seed matrix and write-once artifacts | More replicated scenario seeds needed |
| Missing denominators | Counts and pooled/scenario metrics stored; undefined recall/AP eligibility implemented | Repaired artifact `b866ae2aa1b4b479` certified at commit `1942718`; protocol-scale development and validation remain needed |
| Historical policy replay | Research bitemporal contract and golden replay tests implemented | Production temporal schema and correction-case matrix not frozen |
| Citation overstatement | Provenance registry and claim ledger | Two references remain metadata-only |
| External validity | Fictional data protect privacy | No organizational validation |
| Human over-trust | Review-only design and evidence display | Usability and automation-bias study not conducted |

## 8 Conclusion and Future Work

This study set out to test whether explicit workforce-progression policy context improves anomaly detection beyond raw administrative features and deterministic validation. MyHR now contains the technical foundation required for a defensible investigation: a formal progression model, application-research parity tests, synthetic data contracts, deterministic and statistical baselines, Isolation Forest comparisons, policy controls, equal-budget reporting, write-once artifacts, citation provenance, and independent auditing.

The development experiments do not establish the expected advantage. They first revealed why a superficially reasonable comparison can fail: the original generator was closely aligned with the policy representation, and the historical residual design removed all variation from its policy-specific features. The repaired experiment restores a testable residual comparison, but its primary recall interval crosses zero and its twelve inspected scenarios are below protocol scale. Preserving both failures and uncertain results prevents a false claim of success or equivalence.

The historical-policy direction remains the most actionable, but its earlier quantification must be read with care. A preserved older artifact recorded that deterministic validation flagged 39 of 72 constructed rare-legitimate histories; that figure comes from an earlier generator and is retained only as historical development evidence. A second external audit (30 October 2026) later found that the policy-transition generator used to produce the 2026-10-30 artifacts constructed genuinely contradictory histories (promotions before hire, insufficient service), so an intermediate "8 of 72" reading was INVALIDATED: those alerts were responses to real contradictions, not false positives on lawful histories. The generator was repaired so transition cases are lawful by construction; see `TDK_SECOND_EXTERNAL_AUDIT_2026-10-30.md` and the roadmap repairs (R1–R10). No current figure should be presented as a historical-policy false-positive rate on lawful histories until the repaired scenarios are approved and re-evaluated.

After the repairs, artifact `b866ae2aa1b4b479` was generated from clean commit `1942718` and passed the strengthened repository audit with `holdout_accessed: false`. Deterministic rules flagged 0 of 72 test-split rare-legitimate cases. The primary residual recall difference was +0.0278, 95% CI [-0.0278, +0.1019], sign-flip p=0.6875. No policy-aware advantage was demonstrated in this exploratory development run; the interval neither proves equivalence nor excludes a potentially useful effect. Scenario definitions remain pending human approval, the temporal model is partial, and the experiment contains only 12 inspected scenario units. Remaining work includes blinded realism review, protocol-scale development and validation, and an independently specified holdout matrix. After those checks, dependencies, analysis, and source revision require a separate dated freeze approval. Only then may the locked holdout run once.

Duplicate detection remains a useful secondary experiment, and evidence-rich explanation remains a product contribution. Neither substitutes for a valid central anomaly-detection experiment. The present paper therefore offers a reproducible research platform, an honest diagnosis of a failed comparison, and a concrete path to a stronger confirmatory study.

## References

[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in Proceedings of the 2008 IEEE International Conference on Data Mining, 2008. DOI: 10.1109/ICDM.2008.17.

[2] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation-Based Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, 2012. DOI: 10.1145/2133360.2133363.

[3] S. Han, X. Hu, H. Huang, M. Jiang, and Y. Zhao, “ADBench: Anomaly Detection Benchmark,” Advances in Neural Information Processing Systems, 2022. DOI: 10.52202/068431-2329.

[4] Z. Li, Y. Zhu, and M. van Leeuwen, “A Survey on Explainable Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, 2024. DOI: 10.1145/3609333.

[5] M. Carletti, M. Terzi, and G. A. Susto, “Interpretable Anomaly Detection with DIFFI: Depth-Based Feature Importance of Isolation Forest,” Engineering Applications of Artificial Intelligence, 2023. DOI: 10.1016/j.engappai.2022.105730.

[6] N. Vaska, K. Leahy, and V. Helus, “Context-Dependent Anomaly Detection with Knowledge Graph Embedding Models,” 2022. DOI: 10.1109/CASE49997.2022.9926631.

[7] G. Steinbuss and K. Böhm, “Benchmarking Unsupervised Outlier Detection with Realistic Synthetic Data,” ACM Transactions on Knowledge Discovery from Data, 2021. DOI: 10.1145/3441453.

[8] L. Hansen, N. Seedat, M. van der Schaar, and A. Petrovic, “Reimagining Synthetic Tabular Data Generation through Data-Centric AI: A Comprehensive Benchmark,” 2023. DOI: 10.52202/075280-1466.

[9] D. Fourure, M. U. Javaid, N. Posocco, and S. Tihon, “Anomaly Detection: How to Artificially Increase Your F1-Score with a Biased Evaluation Protocol,” in Machine Learning and Knowledge Discovery in Databases, 2021. DOI: 10.1007/978-3-030-86514-6_1.

[10] T. Saito and M. Rehmsmeier, “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets,” PLOS ONE, 2015. DOI: 10.1371/journal.pone.0118432.

[11] J. Demšar, “Statistical Comparisons of Classifiers over Multiple Data Sets,” Journal of Machine Learning Research, 2006.

[12] T. Wang et al., “Towards Universal Dense Blocking for Entity Resolution,” 2024. DOI: 10.48550/arXiv.2404.14831.

[13] S. Sørbø and M. Ruocco, “Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection in Time Series,” Data Mining and Knowledge Discovery, 2024. DOI: 10.1007/s10618-023-00988-8.

[14] P. Röchner et al., “We Need to Rethink Benchmarking in Anomaly Detection,” 2025. DOI: 10.48550/arXiv.2507.15584.

[15] G. Neelamegam, J. Bhogal, P. Samimi, and Ö. Öztürkoğlu, “Comprehensive Insights into Bitemporal Databases: A PRISMA-Guided Systematic Literature Review,” 2026. DOI: 10.1007/s42488-026-00162-x.

[16] Z. Deng, X. Xuan, K.-L. Ma, and Z. Kong, “A Reliable Framework for Human-in-the-Loop Anomaly Detection in Time Series,” 2026. DOI: 10.1145/3778167.

## Appendix A Reproduction Commands

```text
pip install -r requirements.txt -r requirements-research.txt
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_e342bd4acf39b06b
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_b866ae2aa1b4b479
```

No holdout command is included. The holdout runner remains unavailable until the protocol is frozen and approved.

## Appendix B Recorded Decisions and Pending Freeze Work

1. Implement invariant-only filtering for the primary residual comparison and report the complete workflow secondarily.
2. Independently verify recall at fixed equal additional review capacity as primary, with AP secondary and predeclared zero-positive handling.
3. Independently verify the research bitemporal policy and evidence contract, then freeze explicit correction scenarios and the production-migration boundary.
4. Nominate the two complementary reviewers and freeze the sample, agreement statistic, and adjudication form.
5. Freeze the independently specified holdout matrix with repeated seeds and detector-inaccessible causal truth.
6. Freeze exact dependencies, analysis code, configuration, and source revision after independent verification.

Authorship and approval note: the methodology direction was authorized for implementation on 29 October 2026 by the project author (Muhammad Ibrahim Shoeb). A separately documented independent supervisor endorsement is not on record; earlier wording that implied "relayed supervisor answers" overstated this and has been corrected across the decision records. Implementation completeness, protocol freeze, and holdout access still require separate recorded human approval and cannot be granted by an AI agent.

