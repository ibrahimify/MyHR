# Contributing To MyHR

Thank you for considering a contribution. MyHR is both a desktop HR application and a BSc/TDK research platform, so changes must keep product behavior and research validity separate.

## Branches

- `master`: stable public branch.
- `thesis-final-polish`: thesis-focused application work.
- `research/policy-aware-anomaly`: TDK research pipeline.

Use pull requests for meaningful changes. Avoid direct commits to protected branches.

## Development Setup

Runtime app dependencies:

```bash
pip install -r requirements.txt
```

Research dependencies:

```bash
pip install -r requirements.txt -r requirements-research.txt
```

Run the app:

```bash
python main.py
```

Run tests:

```bash
python -m unittest discover tests
```

## Code Rules

- Keep UI changes consistent with `docs/UI_RULES.md`.
- New dropdowns must use `src.ui.components.app_select.AppSelect`.
- Do not introduce `QComboBox` or page-local dropdown implementations.
- Keep research code under `src/services/anomaly_detection/` unless there is a clear reason.
- Do not mix unreviewed research outputs into production UI claims.

## Research Rules

No paper claim should be written unless it is backed by a reproducible artifact containing:

- configuration;
- random seed;
- dataset generation parameters;
- method name;
- metrics;
- run ID or timestamp.

Generated outputs under `research_outputs/` are ignored by default. Commit only intentionally reviewed outputs.

## Pull Request Checklist

Before opening a PR:

- run relevant tests;
- update docs if behavior changes;
- avoid committing real data, local databases, generated reports, or credentials;
- explain whether the change affects thesis functionality, research functionality, or both.
