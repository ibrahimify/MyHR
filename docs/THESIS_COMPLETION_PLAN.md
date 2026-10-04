# MyHR thesis completion plan

This plan tracks the thesis implementation scope from the official task description. It is safe to keep in the public project documentation because it describes implementation status, not the detailed TDK research strategy.

## Submitted thesis topic

**Design and Implementation of a Standalone Employee Management System**

The project aims to design and implement a standalone desktop application for managing employee records in a government-like organization. The system supports employee and organizational data management, performance evaluation records, commendation and disciplinary actions, and rule-based determination of promotion and annual allowance eligibility. A local database stores employee and administrative data, while a graphical user interface provides administrative workflows. The second phase may extend the system with configurable policies, audit logging, reporting, improved validation, and additional reliability features.

## Requirement traceability

| Requirement | Current status | Evidence / next action |
|---|---|---|
| Design and implement the employee database | Done | SQLAlchemy/SQLite models and database connection layer. |
| Design and implement organizational database | Done | Organization hierarchy model and hierarchy page. |
| Employee management functions | Done | Add, edit, list, profile, import, export, search, filters. |
| Department and organization management functions | Done | Organization -> Division -> Department -> Unit -> Team -> Position hierarchy. |
| Performance evaluation records | Planned small addition | Add lightweight performance score/history records connected to promotion eligibility and anomaly detection examples. Avoid a large full performance-management module. |
| Commendation actions | Done | Issue and history workflows. |
| Disciplinary actions | Done | Sanction issue, active/history, resolution, delay months. |
| Rule-based promotion eligibility checks | Done | Promotion race engine with service time, commendation credits, sanction delay, and promotion history. |
| Annual allowance / salary increment eligibility checks | Done | Annual increment rules, due queue, approval, and salary history. |
| Desktop graphical user interface | Done | PySide6 desktop app with admin workflows and light/dark themes. |
| Configurable policies | Done | Promotion, level, salary, and increment settings. |
| Audit logging | Done | Audit log with before/after values, snapshots, filters, and exports. |
| Reporting | Done | Yearly reports, preview, PDF export, dashboard indicators. |
| Improved validation | Mostly done | Import validation, salary range validation, policy input validation. Needs final regression run. |
| Reliability features | Partial | Backup/export/database health checks exist. Needs final packaging and smoke testing. |

## Remaining thesis implementation work

1. Add lightweight performance score/history support:
   - score value, evaluation date, evaluator/admin, optional note;
   - latest score visible on employee profile;
   - create/edit/delete or append-only decision to be finalized;
   - audit log for performance score changes;
   - optional required performance score setting for research/anomaly examples.
2. Run and record the full test suite in the intended virtual environment.
3. Build/package the desktop app for Windows.
4. Smoke test the packaged app:
   - login;
   - dashboard;
   - employee CRUD;
   - employee profile;
   - org hierarchy pan/zoom/select/export;
   - promotion and annual increment workflows;
   - commendation and sanction workflows;
   - import validation;
   - yearly report export;
   - audit export;
   - settings save/load;
   - light and dark mode.
5. Update user and developer guides after the performance score feature and packaging are stable.
6. Prepare thesis evidence:
   - requirement traceability table;
   - screenshots;
   - architecture diagram;
   - database schema figure;
   - promotion/increment rule examples;
   - audit/reporting examples;
   - final test results;
   - known limitations and future work.

## Suggested implementation order

1. Finish thesis-critical feature gap: performance score/history.
2. Run regression tests and fix failures.
3. Package the app.
4. Perform packaged-app smoke test.
5. Freeze a thesis demo database.
6. Update documentation and screenshots.
7. Start the detailed TDK research implementation on a separate branch.

## Git workflow recommendation

Use separate branches so thesis packaging and TDK research do not interfere:

- `thesis/final-polish`: performance score, tests, packaging, docs.
- `research/policy-aware-anomaly`: formal model, synthetic benchmark, Isolation Forest, duplicate detection, experiments.

Finish and tag a stable thesis build before heavy research changes:

```bash
git switch -c thesis/final-polish
python -m unittest discover tests
git add .
git commit -m "Complete thesis implementation plan and docs"
```

After packaging is stable:

```bash
git tag thesis-demo-stable
git switch -c research/policy-aware-anomaly
```

Avoid committing `docs/research/` until the content is cleaned and safe for public release.
