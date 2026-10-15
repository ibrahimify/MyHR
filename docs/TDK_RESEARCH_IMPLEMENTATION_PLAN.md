# TDK Research Implementation Plan

Research title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

This document tracks implementation work only. Experimental results must be added only after reproducible scripts produce them.

## Existing Functionality Used By The Research

- Employee, organization, promotion, commendation, sanction, salary increment, performance review, and audit models.
- Rule-based promotion race logic.
- Annual increment logic.
- Performance review history.
- Audit trail and reporting foundations.

## Planned Research Components

1. Formal policy representation.
2. Reproducible synthetic workforce-history generator.
3. Injected anomaly labels and rare legitimate cases.
4. Deterministic validation checks.
5. Statistical baselines.
6. Raw feature representation.
7. Policy-aware feature representation.
8. Raw Isolation Forest.
9. Policy-aware Isolation Forest.
10. Duplicate-record detection.
11. Metrics and experiment artifacts.
12. Explainability examples for human review.

## Scientific Rule

No research claim may be written into the paper unless it is supported by a reproducible experiment output committed or archived with:

- configuration;
- random seed;
- dataset generation parameters;
- method name;
- metrics;
- timestamp or run identifier.

The scientific audit dated 2026-10-15 supersedes any interpretation of the first five-seed outputs as final evidence. Seeds `2026-2030` are development-only. The untouched holdout remains locked under `docs/TDK_EXPERIMENT_PROTOCOL.md`.

## Evaluation Metrics

- Precision.
- Recall.
- F1 score.
- False-positive rate.
- False-negative rate.
- Review workload.
- Runtime.
- Separate false-positive analysis for rare legitimate policy cases.

## TDK Paper Format Reminder

- Main text length: 30-35 pages.
- Excluded from page count: cover page, optional assignment, table of contents, bibliography, abstract, and appendices.
- Included in page count: figures and tables.
- A4 page size.
- Single-column text.
- 12 pt Times New Roman or another readable serif font.
- Single line spacing.
- Margins between 1.5 cm and 3.5 cm.
- Figures and tables must be readable in print; avoid labels below 10 pt.
- Presentation: 15 minutes plus 5 minutes questions.

## Implementation Order

1. Add CI and research package skeleton.
2. Define synthetic data contract and anomaly taxonomy. See `docs/TDK_SYNTHETIC_DATA_CONTRACT.md`.
3. Implement the reproducible synthetic dataset generator.
4. Implement deterministic checks. These provide the non-ML baseline for explicit administrative inconsistencies.
5. Implement raw and policy-aware feature extraction. This is the central representation comparison for the TDK research question.
6. Add statistical baselines and evaluation reporting.
7. Add Isolation Forest experiments after approving the research dependency boundary.
8. Add duplicate detection experiment as a secondary comparison with exact, normalized exact, and similarity methods.
9. Generate reproducible result artifacts for paper tables and later plots.
10. Run multi-seed stability checks and aggregate mean/std results.
11. Draft methodology and results sections from actual outputs.

## Issue 10 Milestone

The draft v2 framework adds independent scenario families, shared policy arithmetic, golden-history parity tests, validation-selected thresholds, equal-budget comparisons, PR-AUC, feature ablations, negative policy controls, deterministic rules-only comparisons, paired uncertainty, utility sensitivity, and checksummed write-once artifacts.

The remaining gate is methodological review, not metric optimization. Development and validation matrices must be examined in full, including negative findings, before asking the supervisor to approve a frozen protocol. Holdout generation remains prohibited.
