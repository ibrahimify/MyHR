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
3. Implement deterministic checks.
4. Implement raw and policy-aware feature extraction.
5. Add statistical baselines.
6. Add Isolation Forest experiments.
7. Add duplicate detection experiment.
8. Generate result tables and plots.
9. Draft methodology and results sections from actual outputs.
