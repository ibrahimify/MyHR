# MyHR - Employee Management System

MyHR is a standalone offline desktop application for managing employee records,
organization hierarchy, promotions, commendations, sanctions, salary increments,
audit logs, imports, exports, and yearly HR reports.

It is built for a local-first HR workflow: no server is required, data is stored
in SQLite, and the desktop UI is implemented with PySide6.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/PySide6-Qt6-41CD52?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)

---

## Project Status

Current checkpoint: pre-packaging polish complete.

Completed:
- Core desktop app workflow
- Employee CRUD and profile pages
- Organization hierarchy canvas
- Promotion race and annual increment logic
- Commendations, sanctions, audit log, import/export
- Yearly PDF reports
- Light/dark themes
- Multi-language support
- Dashboard density polish for laptop and desktop layouts
- Application icon asset ready for packaging

Remaining:
- Build/package the desktop app as a standalone Windows application or installer

---

## Supervisor And Developer

| Role | Name |
|---|---|
| Supervisor | Dr. Husam Al-Magsoosi |
| Developer | Muhammad Ibrahim Shoeb |
| Institution | Budapest University of Technology and Economics |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| UI Framework | PySide6 6.11.0 / Qt6 |
| Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Icons | Local Lucide SVG icons with QtAwesome fallback |
| Spreadsheet Import | openpyxl |
| PDF/Document Support | PySide6 printing, pypdf, python-docx |
| Mock UI Reference | `MockUI/` React + Vite prototype |

---

## Run The Desktop App

Create and activate a virtual environment first if desired, then install:

```bash
pip install -r requirements.txt
python main.py
```

Default credentials:

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

---

## Run Tests

```bash
python -m unittest discover tests
```

Before pushing or packaging, this should pass:

```bash
python -m py_compile main.py src/ui/icons.py src/ui/pages/dashboard.py
python -m unittest discover tests
```

UI rule: new dropdowns must use `src.ui.components.app_select.AppSelect`.
Do not add new `QComboBox` widgets or page-local custom dropdowns. This is
documented in `docs/UI_RULES.md` and guarded by `tests/test_ui_component_policy.py`.

Before packaging or a formal demo, use `docs/QA_CHECKLIST.md` as the manual
go/no-go checklist. Architectural follow-up items are tracked in
`docs/ARCHITECTURE_ROADMAP.md`. SaaS launch-audit insights are converted into
project-specific actions in `docs/LAUNCH_AUDIT_ACTIONS.md`.

Latest verification before this README update:

```text
Ran 42 tests in 70.647s
OK
```

---

## Demo Data

To reset the local database and populate a realistic demo company dataset:

```bash
python scripts/seed_demo_company.py
```

This creates employees, org units, promotion records, commendations, sanctions,
salary increment data, and audit activity for testing.

---

## MockUI Prototype

The `MockUI/` folder contains the original React/Vite design reference.
It is not required to run the desktop app.

```bash
cd MockUI
npm install
npm run dev
```

Open the local URL shown by Vite, usually:

```text
http://localhost:5173
```

---

## Main Features

### Employee Management

- Add, edit, view, and delete employee records
- Auto-generated employee IDs
- Degree-based level assignment for BSc, MSc, and PhD employees
- `Other` employee track for increment-only roles
- Professional employee profile with employment, personal, promotion, commendation, and sanction records
- Rubric-based performance review history on employee profiles
- Search, filtering, and pagination

### Organization Hierarchy

- Hierarchy model: Organization -> Division -> Department -> Unit -> Team -> Position
- Premium canvas view with pan, zoom, fit view, search, and lazy expansion
- Selected employee/unit inspector panel
- Add, edit, and delete unit actions with hierarchy dependency checks
- Export current hierarchy canvas as PNG through a save dialog

### Promotion Race

- Promotion race is calculated live from raw records
- Commendations reduce race months
- Sanctions add delay months
- Promotions reset the race clock
- Sub-race checkpoints show annual progress
- `Other` employees do not get promotion races; they keep annual increment timelines only

### Annual Salary Increment

- Annual increments are separate from promotion
- Dashboard alert when increments are due
- Admin review and approval workflow
- Per-level increment settings
- Full before/after salary audit trail

### Commendations And Sanctions

- Commendations can be issued to one employee or bulk teams
- Sanctions track disciplinary delay months
- Active and resolved sanctions are separated
- Commendations and sanctions remain available for `Other` employees

### Dashboard

- KPI overview
- Increment queue
- Promotion pipeline
- Priority signals
- Workforce charts
- Recent activity
- Responsive density for laptop and desktop screens

### Import, Export, And Reports

- CSV/XLSX employee import with validation preview
- Downloadable import template
- Employee CSV export
- Yearly PDF report with Full, Executive, and Audit-only modes
- Report preview before PDF generation
- Export history via immutable audit records
- SQLite backup to a chosen location

### Audit Log

- Immutable audit trail for admin and HR actions
- Username snapshots survive account renames
- Search, filters, tooltips, and readable before/after diffs
- CSV and PDF audit export

### Access Control

| Capability | Admin | HR Officer |
|---|:---:|:---:|
| Dashboard | Yes | Yes |
| Employee Management | Yes | Yes |
| Organization Hierarchy | Yes | Yes |
| Promotions | Yes | Yes |
| Commendations | Yes | Yes |
| Sanctions | Yes | Yes |
| Audit Log | Yes | Yes |
| Import Data | Yes | Yes |
| Settings | Yes | No |
| User Management | Yes | No |
| Export And Backup | Yes | No |

---

## Project Structure

```text
MyHR/
|-- main.py
|-- requirements.txt
|-- README.md
|-- docs/
|   |-- guides/
|   |-- media/
|-- scripts/
|   |-- seed_demo_company.py
|   |-- generate_docs.py
|-- MockUI/
|-- src/
|   |-- core/
|   |   |-- i18n.py
|   |   |-- app_settings.py
|   |-- database/
|   |   |-- models.py
|   |   |-- connection.py
|   |-- services/
|   |   |-- reporting_service.py
|   |-- ui/
|       |-- assets/
|       |   |-- myhr.ico
|       |   |-- icons/lucide/
|       |-- icons.py
|       |-- styles.py
|       |-- theme.py
|       |-- login_window.py
|       |-- main_window.py
|       |-- pages/
|           |-- dashboard.py
|           |-- employees.py
|           |-- hierarchy.py
|           |-- promotions.py
|           |-- commendations.py
|           |-- sanctions.py
|           |-- audit_log.py
|           |-- import_data.py
|           |-- settings.py
|-- tests/
```

---

## Packaging Notes

Packaging is intentionally not done yet.

Before building the standalone app:

1. Make sure tests pass.
2. Make sure temporary folders are not included:
   - `tmp_*/`
   - `build/`
   - `dist/`
   - `MockUI/node_modules/`
   - local `*.db` files
3. Use `src/ui/assets/myhr.ico` as the Windows executable icon.
4. Include `src/ui/assets/icons/lucide/` with the package so SVG icons load correctly.
5. Decide whether the packaged app should create a fresh local database or ship with a demo database.

Suggested packaging tool for the next step:

```bash
pyinstaller --noconfirm --windowed --name MyHR --icon src/ui/assets/myhr.ico main.py
```

That command may need additional data-file options for assets. Do not treat it as final until the packaged app is tested.

---

## Safe Push And Rollback

Before pushing:

```bash
git status
python -m unittest discover tests
git add .
git commit -m "Pre-package polish"
git push
```

If something goes wrong after pushing, first find the last good commit:

```bash
git log --oneline -5
```

To temporarily go back and inspect an older version:

```bash
git switch --detach <commit-hash>
```

To return to your working branch:

```bash
git switch <branch-name>
```

To undo the latest commit safely with a new revert commit:

```bash
git revert HEAD
```

Avoid `git reset --hard` unless you are completely sure you want to discard local changes.

---

## Documentation

| Document | Location |
|---|---|
| User Guide | `docs/guides/MyHR_User_Guide.docx` |
| Developer Guide | `docs/guides/MyHR_Developer_Guide.docx` |
| UI Rules | `docs/UI_RULES.md` |
| QA Checklist | `docs/QA_CHECKLIST.md` |
| Architecture Roadmap | `docs/ARCHITECTURE_ROADMAP.md` |
| Launch Audit Actions | `docs/LAUNCH_AUDIT_ACTIONS.md` |
| Thesis Completion Plan | `docs/THESIS_COMPLETION_PLAN.md` |
| TDK Synthetic Data Contract | `docs/TDK_SYNTHETIC_DATA_CONTRACT.md` |
| UI Mockup | `MockUI/` |
| Demo Dataset Script | `scripts/seed_demo_company.py` |

Private TDK research planning notes are kept locally under `docs/research/` and
are intentionally ignored by Git until they are cleaned for public release.

---

## License

Academic project for Budapest University of Technology and Economics, 2025-2026.
