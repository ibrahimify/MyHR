# MyHR Research Handover

Research title: **MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

Status date: 2026-10-18

Status: development research only. The experiment protocol is draft, all existing results are development or validation diagnostics, the research pull request is unmerged, and the final holdout remains undefined and locked.

## 1. Executive Summary

MyHR is a standalone PySide6, SQLite, and SQLAlchemy employee-management application. Its TDK research asks whether explicit workforce-progression policy context can make anomaly triage more useful than policy-agnostic methods, especially by reducing false alerts for unusual but lawful histories without missing genuine administrative errors.

The implementation now includes formal policy calculations, deterministic validation, synthetic generators, statistical baselines, raw and policy-aware Isolation Forest representations, duplicate-record detection, reproducible artifacts, checksums, statistical comparisons, literature tooling, and independent artifact auditing.

The main scientific result so far is a limitation, not a victory claim. In the current independent rules-first experiment, deterministic filtering makes all three policy-specific residual features constant zero. The remaining raw-versus-policy-aware AP comparison therefore cannot test the central hypothesis. The values `0.3621` and `0.3616` are arithmetically reproducible but scientifically vacuous as evidence about policy context.

A second important finding is actionable: deterministic current-policy checks flagged 39 of 72 broadly labelled rare-legitimate histories. Source regeneration found that all 39 realised policy-transition histories were flagged, but the old stored artifact cannot prove that per-record mechanism attribution. This motivates a historical, bitemporal policy model while also showing why provenance must be stored in future artifacts.

## 2. Problem And Motivation

Administrative histories contain promotions, salary increments, commendations, sanctions, performance reviews, approvals, and corrections. A short promotion interval can mean either an error or a lawful exception caused by commendation credit, recognised prior service, grandfathering, or a historical policy version. A policy-agnostic detector sees only unusual numbers. A policy-aware system should be able to distinguish unusual-but-explained behavior from inconsistent behavior.

The intended operational use is decision support. Deterministic checks identify explicit contradictions, ML ranks unresolved cases for review, and a human makes every personnel decision. An anomaly score must never automatically promote, sanction, change salary, or merge employee records.

## 3. Research Questions

The central question is:

> Under equal human-review capacity, does adding explicit policy context improve anomaly ranking and reduce unnecessary alerts for legitimate exceptional histories without materially reducing detection of genuine administrative errors?

Supporting questions are:

1. Are gains caused by useful policy context or by circularity between the synthetic generator and detector?
2. Do results persist across policies, populations, anomaly mechanisms, rare-legitimate mechanisms, and random seeds?
3. Is any reduction in rare-legitimate false alerts operationally valuable, or does it merely move false alerts to ordinary-clean records?
4. Can current-policy replay correctly evaluate records created under earlier policies?
5. Can duplicate detection identify suspicious pairs while keeping its task, labels, and metrics separate from progression anomalies?

## 4. Research Background

- **Isolation Forest:** random partitioning tends to isolate unusual observations with shorter paths. It supplies a ranking score, not a policy judgement or calibrated probability. See `isolation_forest.py` and the Liu et al. references in `TDK_REFERENCES.bib`.
- **Contextual anomalies:** the same observation can be normal in one context and anomalous in another. Policy version, service requirement, employee track, and recorded evidence are the MyHR context.
- **Rules plus ML:** exact contradictions belong in deterministic validation. ML is reserved for ranking cases not fully decided by explicit rules.
- **Imbalanced evaluation:** anomalies are rare, so accuracy and ROC summaries can conceal poor positive-class behavior. Average precision, precision, recall, false-positive rates, counts, and denominators are reported together.
- **Synthetic validity:** synthetic labels provide known ground truth but can accidentally encode the detector's answer. Source-code separation is not enough; causal mechanisms and decisive features must also be conceptually independent.
- **Temporal policy:** valid time says when a policy or event applies; recorded time says when the database learned it. Historical reconstruction needs both.
- **Human review:** domain experts must assess realism and ambiguous ground truth independently of model scores.

The searched literature supports these methodological principles. It does not prove that MyHR's policy-aware model works or that the claimed combination is globally novel. See `TDK_LITERATURE_REVIEW.md` and `TDK_REFERENCES.bib`.

## 5. Mathematical Foundations

### 5.1 Promotion race arithmetic

For elapsed service months `M`, commendation credit `C`, sanction delay `S`, and base requirement `B`, MyHR uses:

```text
adjusted_service = A = M + C - S
remaining_service = R = max(0, B - A)
eligible = (R = 0)
progress_pct = clamp(int(100 * A / B), 0, 100)
```

The application implementation is `calculate_promotion_race()` in `src/services/promotion_policy.py`. Research history evaluation is `assess_promotion_history()` in `src/services/anomaly_detection/policy_history.py`. Parity tests are essential because the research must not silently use different policy mathematics from the application.

Example: if `B=48`, `M=45`, `C=6`, and `S=3`, then `A=48`, `R=0`, and the employee is service-eligible. This is evidence for review, not automatic approval.

### 5.2 Policy-aware residual features

`extract_policy_aware_features()` computes policy-conditioned quantities such as remaining service deficit, deficit ratio, and unexplained short-promotion indicators. A conceptual deficit is:

```text
deficit = max(0, required_months - elapsed_months - credits + delays)
deficit_ratio = deficit / required_months
```

The current residual filter removes every history with a positive policy deficit. Consequently these policy-specific values become zero for every retained record. That structural collapse is why the current residual comparison cannot answer the research question.

### 5.3 Classification metrics

From true positives `TP`, false positives `FP`, false negatives `FN`, and true negatives `TN`:

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)
F1 = 2 * precision * recall / (precision + recall)
false_positive_rate = FP / (FP + TN)
```

These are implemented in `src/services/anomaly_detection/metrics.py`. Every reported rate needs its count and denominator.

Average precision summarizes the precision-recall ranking over score thresholds. It is prevalence-sensitive. In the current code, `_average_precision()` in `protocol_evaluation.py` returns zero when no positives exist. Six independent scenarios have no residual positives, so treating their AP as zero is methodologically disputed and must not silently define the final estimand.

### 5.4 Paired comparisons

Raw and policy-aware methods are evaluated on the same scenario seed. For scenario `i`:

```text
delta_i = metric(policy_i) - metric(raw_i)
```

The current tooling reports the mean paired difference, a scenario bootstrap interval, a sign-flip test, and Holm-adjusted exploratory p-values. Scenario seeds, not individual employees, are the intended independent units. With only six informative residual scenarios, current uncertainty estimates are weak and do not support a superiority claim.

### 5.5 Duplicate similarity

`find_similarity_duplicate_candidates()` keeps duplicate detection separate and scores field evidence with the implemented weighting:

```text
similarity = 0.35 * name
           + 0.30 * date_of_birth
           + 0.25 * identifier
           + 0.10 * email
```

The current default threshold is `0.86`. This is a review suggestion, never an automatic merge.

### 5.6 Operational utility

The development utility analysis makes assumptions explicit:

```text
total_cost = alerts * review_cost
           + false_negatives * missed_error_cost
           + rare_legitimate_alerts * rare_escalation_cost
```

These costs are sensitivity parameters, not measured organizational costs. A favorable result under one assumed cost ratio is not a universal business benefit.

## 6. Implemented Research Architecture

| Concern | Implementation evidence |
| --- | --- |
| Research records and labels | `src/services/anomaly_detection/synthetic_data.py` |
| Original scenario matrix | `scenario_generation.py:scenario_matrix()` and `generate_scenario_dataset()` |
| Independent development simulator | `src/research/independent_scenarios.py` |
| Application promotion arithmetic | `src/services/promotion_policy.py:calculate_promotion_race()` |
| Research policy history | `policy_history.py:assess_promotion_history()` |
| Deterministic checks | `deterministic_checks.py:validate_record_with_policy()` |
| Raw and policy-aware features | `features.py:extract_raw_features()` and `extract_policy_aware_features()` |
| Transparent baselines | `statistical_baselines.py` |
| Isolation Forest | `isolation_forest.py:score_isolation_forest()` |
| Scenario evaluation and thresholds | `protocol_evaluation.py:evaluate_scenario()` |
| Duplicate detection | `duplicate_detection.py` |
| Artifact generation | `scripts/run_tdk_protocol_experiment.py` and `scripts/run_tdk_independent_development.py` |
| Artifact verification | `scripts/audit_tdk_protocol_artifact.py` |
| Automated tests | `tests/test_tdk_protocol_v2.py`, `test_independent_scenarios.py`, and `test_protocol_artifact_audit.py` |

Research dependencies are isolated in `requirements-research.txt`, so the desktop package is not forced to ship scikit-learn, pandas, or research tooling.

## 7. Methodology And Safeguards

1. Generate fictional histories with train, validation, and test partitions.
2. Fit models only on permitted training records.
3. Select thresholds on validation data, never on inspected test outcomes.
4. Compare representations at equal review budgets.
5. Evaluate deterministic rules alone, rules plus ML, rule-negative residual ML, wrong-policy controls, shuffled-policy controls, and feature ablations.
6. Aggregate paired differences by scenario seed and preserve negative results.
7. Write artifacts once with configuration, revision, dependencies, seeds, source hashes, checksums, and `holdout_accessed: false`.
8. Audit stored predictions and metrics independently.
9. Keep duplicate detection as a separate experiment.
10. Require human approval before protocol changes or holdout access.

## 8. Experiments And Results So Far

### 8.1 Early development seeds

Seeds `2026-2030` were inspected during feature development and are permanently development-only. Each seed had 10 rare-legitimate test records. Policy-aware features flagged a mean `0.4` per seed (`2/50` pooled), while raw features flagged a mean `2.6` per seed (`13/50` pooled). These values are descriptive development evidence, not confirmatory evidence, and their interpretation was superseded by stronger auditing.

### 8.2 Corrected protocol v2 scenarios

Across 30 validation scenarios and 3,600 test records, deterministic rules found `351/360` labelled anomalies. This high recall is partly caused by generator interaction: injected sanction histories also become explicit service-policy violations. It must not be generalized to real organizations.

The rules-plus-ML cascades both raised 408 alerts. Raw IF produced `357 TP, 51 FP, 3 FN`; policy-aware IF produced `358 TP, 50 FP, 2 FN`. The paired AP difference was small and not persuasive. After removing deterministic findings, only 9 anomalies remained among 3,249 records. Both residual models raised 340 alerts and 331 false positives. Policy-aware features reduced rare-legitimate alerts from `59/200` to `27/200`, but moved the same 32 false alerts to ordinary-clean records. Total precision and workload did not improve.

### 8.3 Independent development stress test

Twelve independent development scenarios contain 864 test histories, 108 labelled anomalies, and 72 broadly labelled rare-legitimate histories. Deterministic checks raised 105 alerts, with 66 true positives and 39 false positives. The directly reproducible rare-legitimate rate is `39/72 = 54.17%`.

After deterministic filtering, 759 histories and 42 anomalies remained. At equal budget, raw IF raised 81 alerts with `26 TP, 55 FP, 16 FN`; policy-aware IF raised 81 alerts with `25 TP, 56 FP, 17 FN`. Scenario-mean AP was `0.3616` and `0.3621`, respectively, with paired difference `+0.0005` and stored interval `[-0.1173, 0.1079]`.

These AP values must not be interpreted. All policy-specific residual features are zero, six scenarios have no residual positives, and the two models do not receive a meaningful raw-versus-policy comparison. The independent simulator remains valuable because it exposed this failure and the historical-policy problem.

## 9. What Is Verified, Inferred, Or Pending

### Verified from stored artifacts and code

- Artifact checksums and recorded source hashes pass the auditor.
- The independent artifact contains 864 test histories, 108 anomalies, 72 rare-legitimate histories, and 759 rule-negative histories with 42 residual anomalies.
- Stored residual AP values and paired statistics can be recomputed.
- The policy-specific residual features are constant zero.
- Deterministic rules flag 39 of 72 rare-legitimate histories in the stored artifact.
- No holdout has been generated or accessed.

### Qualified inference

- Deterministic source regeneration finds 39 realised transition histories and flags all 39. The original artifact does not preserve enough per-record mechanism evidence to reproduce this statement without regeneration.
- Historical-policy modelling is strongly motivated, but the exact bitemporal schema and HR semantics require domain approval.

### Pending human decisions

- Primary hypothesis and residual design.
- Primary endpoint and handling of zero-positive scenarios.
- Review-capacity rule.
- Historical policy and evidence schema.
- Expert-review protocol.
- Holdout scenario design and protocol freeze.

See `TDK_SUPERVISOR_DECISION_SHEET.md`. Nothing there is approved until a human records a decision.

## 10. Limitations And Risks

- All evaluation data are synthetic; external validity is unproven.
- Original generator and detector share policy concepts, creating circularity risk.
- The independent residual experiment erased its policy signal.
- Current-policy replay cannot faithfully reconstruct historical policy decisions.
- Six of twelve scenarios have undefined residual AP under a conventional interpretation.
- Existing independent scenarios have one realization per population-mechanism cell and weak inferential power.
- Threshold calibration for deployment is unresolved.
- Cost parameters are assumptions.
- Expert realism review has not begun.
- Duplicate detection and explanation usability are not evidence for the central anomaly-detection hypothesis.

## 11. Key Decisions And Reasoning

- **Rules first, ML second:** exact violations should not be rediscovered by an opaque model.
- **Human in the loop:** personnel decisions carry consequences and anomaly scores are uncertain.
- **Equal review budgets:** comparing models at different alert volumes confounds quality with workload.
- **Scenario seeds as units:** employees within one generated scenario share assumptions and are not independent experimental replications.
- **Wrong/shuffled policy controls:** a genuine policy signal should degrade when policy context is wrong or destroyed.
- **Write-once artifacts:** results must be reconstructable without silently changing old evidence.
- **Locked holdout:** inspected outputs cannot serve as final confirmation.
- **Preserve unfavorable results:** scientific value depends on diagnosing failure, not manufacturing a win.

These are current engineering and methodological boundaries. The specific redesign options remain pending human approval.

## 12. Unresolved Issues And Next Steps

1. Obtain human answers on `TDK_SUPERVISOR_DECISION_SHEET.md`.
2. Preserve per-record realised mechanism and causal evidence in future development artifacts.
3. After approval, implement a historical policy model with effective time, recorded time, policy version, recognised service, and correction provenance.
4. Redesign the residual task so policy-aware features vary after deterministic filtering without encoding the answer by construction.
5. Define primary-eligible scenarios and zero-positive handling before running them.
6. Conduct the blinded expert realism review without exposing model scores or generator labels.
7. Freeze exact dependencies, hypotheses, endpoints, scenario matrix, seeds, and analysis.
8. Only then generate and evaluate the final holdout once.
9. Keep duplicate detection and an optional explanation usability study as secondary work.

## 13. Reproduction And Verification

```bash
pip install -r requirements.txt -r requirements-research.txt
python -m unittest discover tests
python scripts/audit_tdk_protocol_artifact.py research_outputs/independent_development/independent_development_e342bd4acf39b06b
```

Do not run any holdout command. The exact artifact location may be local or intentionally archived outside Git; consult `TDK_RESEARCH_VERIFICATION.md` before interpreting a missing path.

## 14. Recommended Reading Order For Ibrahim

### Tomorrow morning, about 60 to 90 minutes

1. Read this document through Section 3 to understand the problem and questions.
2. Work through Section 5 with a calculator and reproduce the promotion example and confusion-metric formulas.
3. Read Sections 8 and 9, then inspect the tables in `TDK_INDEPENDENT_REVIEW_2026-10-17.md`.
4. Read `TDK_SUPERVISOR_DECISION_SHEET.md` and write one question beside each undecided item.
5. Open `CHATGPT_RESEARCH_TUTOR_PROMPT.md`, paste it into ChatGPT with the repository link, and begin Lesson 1 only.

### Deeper sequence

1. `TDK_LITERATURE_REVIEW.md` and `TDK_REFERENCES.bib`.
2. `TDK_SYNTHETIC_DATA_CONTRACT.md` and `TDK_INDEPENDENT_SCENARIO_SPEC.md`.
3. `promotion_policy.py`, `policy_history.py`, and their tests.
4. `deterministic_checks.py`, `features.py`, and `protocol_evaluation.py`.
5. `TDK_PROTOCOL_V2_DEVELOPMENT_VALIDATION_REPORT.md`.
6. `TDK_INDEPENDENT_REVIEW_2026-10-17.md`.
7. `TDK_PROTOCOL_CHANGE_PROPOSALS.md` and `TDK_EXPERIMENT_PROTOCOL.md` last, so proposals are not confused with implemented facts.

The goal is to be able to explain each claim by pointing to code, a test, an artifact, or a verified source, and to say "unknown" when none exists.
