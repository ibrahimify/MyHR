# MyHR Architecture Roadmap

This is a controlled improvement plan. It is not a request to add random features before packaging.

The goal is to keep MyHR stable while making the codebase easier to defend in a thesis, extend for TDK research, and package as a serious desktop product.

## Principles

- Keep the thesis app stable before heavy research changes.
- Prefer shared components over page-local UI implementations.
- Put business rules in service/helper layers, not directly inside UI event handlers.
- Every destructive or important administrative action should be auditable.
- Add tests for rules that are easy to regress.
- Avoid cosmetic changes that do not improve clarity or workflow.

## Add

### Shared UI Components

Current status:

- `AppSelect` exists and is now the required dropdown component.
- `tests/test_ui_component_policy.py` protects this rule.

Next useful components:

- `AppDialog`: shared title/icon area, max height, scroll behavior, footer buttons.
- `AppTable`: consistent headers, row height, empty state, action column.
- `AppDateInput`: consistent date picker field styling.
- `AppEmptyState`: reusable no-data states.
- `AppActionButton`: consistent icon, loading, destructive, and primary variants.

Priority: medium. Add only when touching related screens.

### Validation Service Layer

Move or centralize validation that currently lives in UI pages:

- Employee import validation.
- Salary range validation.
- Hierarchy delete/dependency validation.
- Promotion approval warnings.
- Performance review duplicate/period validation.

Priority: high before packaging if a bug appears; otherwise do gradually.

### QA Checklist

Use `docs/QA_CHECKLIST.md` before packaging or demoing.

Priority: high.

### Research Module Boundary

Current status: implemented separately from the core UI under:

```text
src/services/anomaly_detection/
```

Current structure includes:

```text
src/services/anomaly_detection/
|-- features.py
|-- synthetic_data.py
|-- isolation_forest.py
|-- duplicate_detection.py
|-- metrics.py
|-- protocol_evaluation.py
```

Independent scenario generation is in `src/research/independent_scenarios.py`.
Artifact verification is in `scripts/audit_tdk_protocol_artifact.py`.

Priority: maintain this boundary. Research dependencies remain separate in `requirements-research.txt`.

### Database Versioning

Add a simple schema/version record before packaging if database changes continue.

Possible minimal design:

- `schema_version` table.
- Migration functions in order.
- Startup check that applies missing migrations.

Priority: medium-high before shipping to external users.

## Alter

### Reduce Large UI Files

Some pages are large and mix UI, validation, data loading, and dialogs. Split gradually:

```text
src/ui/pages/employees.py
src/ui/pages/employees/
|-- profile.py
|-- edit_dialogs.py
|-- performance_widgets.py
|-- list_view.py
```

Do not do a risky big-bang refactor before packaging.

Priority: low-medium, gradual.

### Standardize Dialogs

All dialogs should share:

- Header icon/title/subtitle pattern.
- Content max-height with scroll when needed.
- Footer with cancel on left/secondary, primary action on right.
- Warning/info states with consistent colors.

Priority: medium.

### Audit Logging

Move audit helpers toward one service-level API:

```python
record_audit(action, target, before=None, after=None, description=None)
```

This reduces the chance that future CRUD actions miss audit history.

Priority: medium-high.

### Import/Export UX

Improve toward enterprise onboarding:

- Template.
- Required-column guide.
- Preview.
- Dry run.
- Error export.
- Duplicate/suspicious-row warnings.
- Final import audit.

Priority: high if a client/demo user must onboard real data.

## Delete Or Avoid

- Do not add another custom dropdown.
- Do not add raw `QComboBox` widgets.
- Do not create one-off dialog styling for each page.
- Do not add decorative animation unless it helps usability.
- Do not package the installer while core data models are still changing heavily.
- Do not commit private TDK research notes from `docs/research/`.

## Suggested Order

1. Keep the draft research PR unmerged until the approved methodology is implemented, verified, and separately frozen.
2. Use `docs/QA_CHECKLIST.md` for thesis and packaging QA.
3. Use `TDK_SUPERVISOR_DECISIONS_2026-10-29.md` as the authority for the six approved methodology choices.
4. Implement only those approved protocol changes, with tests and development-only artifacts.
5. Freeze the protocol and exact environment before any holdout generation.
6. Package after thesis and research-critical logic stop moving.

