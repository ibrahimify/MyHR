# MyHR QA Checklist

This checklist is the go/no-go gate before packaging or demoing MyHR.

It adapts the useful parts of a SaaS pre-launch audit to this project. MyHR is currently an offline desktop HR system, so web-only items such as CDN, SEO, browser compatibility, payment gateways, and Product Hunt launch planning are not core release gates yet. They become relevant later if a public website, cloud edition, or paid licensing flow is added.

Reference reviewed: https://saaslaunchlab.com/blog/saas-audit-checklist-before-launch/#saas-growth-formula

## 1. Product Clarity

- [ ] One-sentence explanation is clear: MyHR is an offline desktop HR system for employee records, hierarchy, promotion/increment eligibility, audit, import/export, and reports.
- [ ] Target user is clear: HR/admin staff in local-first or government-like organizations.
- [ ] Main pain point is clear: structured HR administration without cloud dependency or spreadsheet fragility.
- [ ] Demo script proves the value in less than 5 minutes.

## 2. First-Run And Onboarding

- [ ] Login screen opens in light mode by default.
- [ ] Admin and HR Officer default credentials work.
- [ ] Language selector works.
- [ ] Theme toggle works and does not break login UI.
- [ ] After login, the dashboard loads without empty or broken states.
- [ ] User can understand primary navigation without training.

## 3. UI Consistency

- [ ] All dropdowns use `AppSelect` behavior and styling.
- [ ] No page-specific custom dropdowns are introduced.
- [ ] Dialogs do not touch screen edges on 1080p displays.
- [ ] Dialogs have consistent title, icon, content spacing, and button layout.
- [ ] Tables have aligned headers and readable row spacing.
- [ ] Light and dark modes both have enough contrast.
- [ ] No text overlaps or clips in common window sizes.

## 4. Critical Workflows

### Dashboard

- [ ] KPIs load.
- [ ] Promotion trend filters work.
- [ ] Custom date range dialog is readable and not cramped.
- [ ] Increment queue/action cards work.
- [ ] Empty states are understandable.

### Employees

- [ ] Employee list search works.
- [ ] Department/status filters work.
- [ ] Add employee works for BSc/MSc/PhD.
- [ ] Add employee works for `Other`.
- [ ] Edit employee profile works.
- [ ] Inline edit works.
- [ ] Employee profile tabs load.
- [ ] Performance review add/edit flow works.
- [ ] Performance radar/trend/table update correctly.

### Organization Hierarchy

- [ ] Canvas loads.
- [ ] Pan, zoom, and fit view work.
- [ ] Selecting a node updates the side panel.
- [ ] Add child unit works.
- [ ] Edit unit works.
- [ ] Delete unit respects dependency rules.
- [ ] Export asks for save location.

### Promotions

- [ ] Eligible employees appear correctly.
- [ ] Ineligible employees show understandable reasons.
- [ ] Promotion approval dialog shows policy evidence.
- [ ] Bad/no performance review triggers manual review warning.
- [ ] Active sanctions and commendations are explained clearly.
- [ ] Approval writes promotion history and audit log.

### Salary Increments

- [ ] Due increments appear.
- [ ] Approval updates salary correctly.
- [ ] Approval writes salary history and audit log.
- [ ] `Other` employees follow increment-only path.

### Commendations

- [ ] Single commendation works.
- [ ] Team/bulk commendation works.
- [ ] Category dropdown works.
- [ ] Max commendation rules work.
- [ ] Audit record is created.

### Sanctions

- [ ] Sanction issue works.
- [ ] Category dropdown works.
- [ ] Promotion delay month dropdown works.
- [ ] Active/resolved status works.
- [ ] Resolution creates audit record.

### Import Data

- [ ] Template download works.
- [ ] Required columns are documented.
- [ ] Valid file preview works.
- [ ] Invalid file shows clear errors.
- [ ] Duplicate or suspicious rows are handled.
- [ ] Import writes audit record.

### Audit Log

- [ ] Search works.
- [ ] Filters work.
- [ ] Row detail dialog opens from action button/double click.
- [ ] Before/after snapshots are readable.
- [ ] CSV export works.
- [ ] PDF export works.

### Settings

- [ ] General company settings save/load.
- [ ] Level settings save/load.
- [ ] Promotion rules save/load.
- [ ] Increment settings save/load.
- [ ] User management works.
- [ ] Database health check dialog explains what it checks.
- [ ] Yearly report filters are readable in light and dark mode.
- [ ] Yearly report preview/PDF export works.

## 5. Technical Reliability

- [ ] `python -m unittest discover tests` passes or known Qt offscreen hang is documented.
- [ ] `python -m unittest tests.test_ui_component_policy` passes.
- [ ] `python -m py_compile main.py` passes.
- [ ] App starts from a clean checkout.
- [ ] App starts with a fresh local database.
- [ ] App starts with seeded demo database.
- [ ] Backup/export produces a valid file.
- [ ] No local `.db`, `.log`, build, or temporary files are committed.

## 6. Security And Compliance Readiness

- [ ] Admin/HR role permissions are correct.
- [ ] HR Officer cannot access Settings/User Management.
- [ ] Password change works.
- [ ] Audit log captures sensitive administrative actions.
- [ ] Employee data stays local unless explicitly exported.
- [ ] Exports are user-initiated and location is chosen by the user.
- [ ] Documentation explains local-first data storage.

## 7. Performance Readiness

- [ ] Dashboard loads quickly with demo data.
- [ ] Employee list remains usable with large test data.
- [ ] Org hierarchy remains usable after expanding realistic branches.
- [ ] Audit log pagination remains responsive.
- [ ] Report generation completes within acceptable time.

## 8. Evidence For Thesis And TDK

- [ ] Screenshot set is prepared.
- [ ] Requirement traceability table is updated.
- [ ] Database schema figure is prepared.
- [ ] Promotion/increment examples are documented.
- [ ] Performance review examples are documented.
- [ ] Audit/report examples are documented.
- [ ] Known limitations are written honestly.

## 9. Feedback Loop

- [ ] Supervisor has seen the thesis scope.
- [ ] At least one user-like reviewer tests the app.
- [ ] Bugs found during manual testing are logged.
- [ ] Fixes are committed with clear messages.
- [ ] Release decision is made from checklist evidence, not memory.

