# MyHR Scope Audit

Last updated: 2026-10-11

This document separates thesis scope, TDK research scope, and future work. It is intended for review before packaging, thesis defense preparation, and TDK paper writing.

## Thesis Scope

Official thesis topic:

**Design and Implementation of a Standalone Employee Management System**

| Thesis requirement | Status | Evidence |
|---|---|---|
| Employee database | Complete | SQLAlchemy and SQLite data model. |
| Organizational database | Complete | Organization hierarchy entities and hierarchy workflows. |
| Employee management functions | Complete | Employee CRUD, profile pages, import/export, search, filters. |
| Department and organization management | Complete | Organization -> Division -> Department -> Unit -> Team -> Position hierarchy. |
| Performance evaluation records | Complete | Rubric-based performance reviews on employee profiles. |
| Commendations | Complete | Commendation workflows and history. |
| Disciplinary actions | Complete | Sanctions, active/resolved status, delay months, history. |
| Rule-based promotion eligibility | Complete | Promotion race engine with service, commendations, sanctions, and manual approval. |
| Annual allowance / salary increment eligibility | Complete | Annual increment queue, approval, salary history, audit trail. |
| Desktop GUI | Complete | PySide6 desktop interface with light/dark theme. |
| Local database | Complete | SQLite local-first workflow. |
| Configurable policies | Complete | Level, promotion, increment, salary, and policy settings. |
| Audit logging | Complete | Immutable audit records with before/after snapshots and exports. |
| Reporting | Complete | Yearly reports, PDF export, dashboard summaries. |
| Improved validation | Mostly complete | Import validation, policy validation, dialog validation, and deterministic research validation. |
| Reliability features | Partial | Backup, health checks, tests, CI. Packaging smoke test still needed. |

## TDK Research Scope

Submitted title:

**MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression**

| Research component | Status | Evidence |
|---|---|---|
| Formal policy representation | Implemented | `src/services/anomaly_detection/policy_model.py` |
| Synthetic data contract | Implemented | `docs/TDK_SYNTHETIC_DATA_CONTRACT.md` |
| Reproducible synthetic generator | Implemented | `generate_synthetic_dataset()` |
| Injected anomaly labels | Implemented | `AnomalyType` taxonomy |
| Rare legitimate policy cases | Implemented | `policy_legitimate_rare_case` label |
| Deterministic validation baseline | Implemented | `validate_record()`, `validate_dataset()` |
| Raw feature extraction | Implemented | `extract_raw_features()` |
| Policy-aware feature extraction | Implemented | `extract_policy_aware_features()` |
| Statistical baselines | Implemented | z-score and IQR baselines |
| Isolation Forest boundary | Implemented | scikit-learn research dependency and wrapper |
| Duplicate-record detection | Implemented | exact, normalized exact, and similarity methods |
| Experiment artifacts | Implemented | `scripts/run_tdk_research_experiment.py` |
| Paper-ready final results | Not final | Requires reviewed full experiment runs and analysis. |
| User study | Optional | Not required unless time remains. |

## Verification Commands

Desktop app test path:

```bash
pip install -r requirements.txt
python -m unittest discover tests
python main.py
```

Research verification path:

```bash
pip install -r requirements.txt -r requirements-research.txt
python scripts/run_tdk_research_smoke.py --seed 2026 --employee-count 300
python scripts/run_tdk_research_experiment.py --seed 2026 --employee-count 1000
```

## Before Packaging

- Run full tests in a clean environment.
- Verify no local database, demo export, temporary output, or private research note is committed.
- Perform manual smoke test from `docs/QA_CHECKLIST.md`.
- Decide whether the packaged app ships empty, with seed data, or with a separate demo database.
- Confirm licensing/IP direction from `docs/LICENSING_AND_IP.md`.

## Before TDK Paper Writing

- Run final experiments with fixed seeds and documented configuration.
- Save or archive selected `research_outputs/<run_id>/` folders.
- Generate result tables only from CSV/JSON artifacts.
- Document limitations clearly, especially synthetic data assumptions.
- Keep user study as optional unless there is enough time for ethical and meaningful evaluation.

## Current Recommendation

Keep the research PR as draft until final experiment settings are reviewed. Do not merge research code into the thesis packaging branch until the thesis app package is stable.
