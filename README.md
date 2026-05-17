# MyHR - Employee Management System

MyHR is a standalone offline desktop HRMS built with Python, PySide6, SQLite, and SQLAlchemy. It is designed for a small HR department or government-style organization where administrators and HR officers manage employee records, organization structure, promotion eligibility, commendations, sanctions, salary increments, imports, exports, and audit logs from one local application.

Supervisor: Dr. Husam Al-Maghoosi  
Developer: Muhammad Ibrahim Shoeb  
Project stage: Project Lab semester implementation with thesis-extension features in progress

## Highlights

- Full PySide6 desktop application, not a web wrapper.
- Local SQLite database with SQLAlchemy models and relationships.
- Admin and HR Officer actor model with Settings restricted to Admin.
- Real HR workflows: onboarding, hierarchy assignment, promotion race tracking, commendations, sanctions, salary increments, data import/export, backup, and audit.
- MyHR visual system: `#f9fafb` page background, white cards, `#e5e7eb` borders, 8px radius, consistent tabs, tables, buttons, dropdowns, dialogs, and qtawesome Font Awesome 5 icons.
- Login language selector for English, Hungarian, and Arabic. Arabic uses right-to-left session layout. Internal enum values, audit action codes, and import/export headers stay stable so logic and contracts do not break.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Desktop UI | PySide6 6.11.0 / Qt 6 |
| Database | SQLite |
| ORM | SQLAlchemy 2.0.49 |
| Icons | qtawesome 1.4.2, Font Awesome 5 |
| Excel import | openpyxl 3.1.5, with XLSX XML fallback |
| Settings storage | Qt `QSettings` |
| Prototype reference | `MockUI/` React + Tailwind mockup |

## Project Structure

```text
MyHR/
  main.py                         Application entry point and global Qt styling
  requirements.txt                Python dependencies
  demo_import_10_employees.xlsx   Sample import file
  README.md                       Main project documentation
  docs/                           Presentation and analysis artifacts
  MockUI/                         React prototype used as visual reference
  scripts/
    seed_demo_company.py          Optional realistic demo-data seed script
  src/
    core/
      app_settings.py             Company branding and persisted app settings
      i18n.py                     Session-level translations
    database/
      connection.py               DB init, ID generation, business helpers
      models.py                   SQLAlchemy schema
    ui/
      login_window.py             Login and language selector
      main_window.py              Main shell, sidebar, navigation, refresh
      styles.py                   Shared UI style helpers
      assets/chevron_down.svg     Dropdown arrow asset
      pages/
        dashboard.py              Live stats and salary increment review
        employees.py              Employee list, add/edit, profile
        hierarchy.py              Organization tree and unit employee drill-down
        promotions.py             Eligibility tracker, history, rule editor
        commendations.py          Awards and team commendations
        sanctions.py              Disciplinary actions and resolution
        audit_log.py              Immutable action log
        import_data.py            CSV/XLSX validation and import
        settings.py               Branding, salary, rules, security, backup/export
```

## Actors and Roles

| Actor | Login? | Role in System | Access |
|---|---:|---|---|
| Admin | Yes | System owner and HR administrator | All pages including Settings, salary ranges, database backup, export, and password management |
| HR Officer | Yes | Operational HR user | Dashboard, Employees, Hierarchy, Promotions, Commendations, Sanctions, Audit Log, Import Data |
| Employee | No | Data subject only | No login; employees are managed records |

Default credentials:

| User | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

## Running the App

1. Create or activate a Python 3.12+ environment.

```bash
python -m pip install -r requirements.txt
```

2. Start the app.

```bash
python main.py
```

The SQLite database is created automatically on first run. The app seeds default users, titles, promotion rules, and a base organization if they do not already exist.

Optional demo company seed:

```bash
python scripts/seed_demo_company.py
```

The seed script resets and creates a larger demo company dataset for presentations. Use it only when you intentionally want demo data.

## Feature Set

### Semester Project Features

| Area | What It Does |
|---|---|
| Authentication | Admin and HR Officer login, role-aware navigation, styled login screen, language selector |
| Employee Management | Add, edit, view, delete employees; employee IDs; profile tabs; manager assignment; org-unit assignment |
| Organization Hierarchy | Organization, division, department, unit, and team tree; add/edit/delete units; assign heads; click a unit/team to view employees inside it and child units |
| Promotion Race | Live eligibility calculation based on current level, promotion rule, time elapsed, commendations, and active sanctions |
| Promotion Approval | Admin/HR can approve eligible promotions; salary is updated; promotion history is recorded; audit log is written |
| Commendations | Single or team awards, three categories, maximum three commendations per employee per current role |
| Sanctions | Issue 1-12 month disciplinary delays, active/resolved tracking, resolved sanctions stop affecting active promotion delay |
| Dashboard | Live totals, recent audit activity, upcoming promotion eligibility, salary increment prompt and approval dialog |
| Import Data | CSV/XLSX upload, header aliases, required-column validation, duplicate-email prevention, org-unit creation, manager wiring, optional history import |
| Audit Log | Immutable searchable/filterable activity log for important changes |
| Settings | Company branding, salary ranges, promotion rules, annual increment settings, password changes, employee export, database backup |

### Thesis Extension / Advanced Features Already Started

| Area | Status |
|---|---|
| Company branding | Settings updates login title, sidebar brand, and main window title |
| L2/L1 executive levels | Promotion path continues above director level |
| Salary increment workflow | Dashboard review dialog approves annual increments and records history |
| Bulk onboarding | Import supports departments, teams, managers, commendations, and active sanctions |
| I18n coverage | Login, navigation, page titles, tabs, key tables, dialogs, filters, profile views, and core messages support English, Hungarian, and Arabic with English fallback for untranslated edge strings |
| UI hardening | Fake emoji/symbol icons replaced with qtawesome icons or plain text in active PySide6 source |

## Database Schema

| Table | Purpose | Key Relationships |
|---|---|---|
| `system_user` | Admin/HR login accounts | Referenced by audit logs, issued commendations, issued sanctions, promotions |
| `org_unit` | Organization tree | Self-referencing parent/children, optional head employee |
| `title` | Level and salary configuration | Referenced by employees and promotion rules |
| `employee` | Employee master record | Belongs to org unit and title; optional manager; referenced by history, awards, sanctions |
| `promotion_rule` | Level-to-level promotion rules | Maps from title to next title with base months and salary increase |
| `promotion_history` | Completed promotions | Employee, from title, to title, approver, salary before/after |
| `commendation` | Award record | Issued by user, linked to employees through join table |
| `commendation_employee` | Team/single award recipients | Joins commendations and employees |
| `sanction` | Disciplinary record | Employee, issuer, delay months, active/resolved state |
| `salary_increment_history` | Annual salary increment approvals | Employee, approver, old/new salary |
| `audit_log` | Immutable activity stream | User, action code, target table/id, description |

## Business Logic Rules

| Scenario | Rule | Result |
|---|---|---|
| New employee is added with degree `BSc` | Degree maps to starting title | Employee starts at L7 |
| New employee is added with degree `MSc` | Degree maps to starting title | Employee starts at L6 |
| New employee is added with degree `PhD` | Degree maps to starting title | Employee starts at L5 |
| Employee joins an org unit | `employee.org_unit_id` references `org_unit.id` | Hierarchy and employee list show connected data |
| Employee has a manager | `reports_to_id` references another employee | Profile and org data can show reporting line |
| Promotion eligibility is shown | Calculation is live, not stored | Dashboard, profile, and promotions page avoid stale months remaining |
| Commendation is issued | Category months are negative modifiers | Promotion race becomes shorter by 1, 3, or 6 months |
| Employee already has 3 commendations in current role | Cap is enforced | More commendations for that role are blocked or skipped in team mode |
| Active sanction is issued | Delay months are added | Promotion race becomes longer while sanction is active |
| Sanction is resolved | `is_resolved=True` and `resolved_at` is set | It stops contributing active delay |
| Promotion is approved | Current title changes to next title | Promotion history is created, salary can change, audit log records action |
| Promotion is completed | Race start becomes promotion date | Next promotion race starts from month 0 |
| Salary increment is approved | Manual admin workflow | Salary history is created and employee base salary is updated |
| Employee import has duplicate work email | Existing and in-file duplicates are checked | Row is rejected before database write |
| Import row includes division/unit/team | Missing org units are created | Employee is assigned to the deepest provided unit |
| Import row includes manager email | Manager lookup checks imported and existing employees | Reporting line is wired when found |
| Critical write happens | `log_action(...)` is called | Audit log receives a human-readable record |
| Settings company name changes | `QSettings` is updated | Login screen, sidebar branding, and window title refresh |

## Import and Export Contracts

Required import headers stay stable because they are part of the file contract:

```text
first_name,last_name,department,degree,position,join_date,base_salary
```

Optional import headers:

```text
division,unit,team,work_email,work_phone,personal_email,phone,address,status,
manager_work_email,commendation_months,active_sanction_months,sanction_type
```

The UI may be translated, but internal enum values, audit action codes, and import/export column names are intentionally not translated unless the importer explicitly supports aliases.

## UI Design System

| Element | Standard |
|---|---|
| Page background | `#f9fafb` |
| Page margins | 40px |
| Page title | 30px, bold |
| Page subtitle | 16px, muted `#4b5563` |
| Cards | White, `#e5e7eb` border, 8px radius |
| Forms | 30px card padding, 14px bold labels, 44px inputs/dropdowns |
| Inputs | `#f3f3f5` background, 8px radius, blue focus border |
| Tabs | Light gray pill container, white active tab, 14px bold text |
| Tables | Bold left-aligned headers, left-aligned content, clean row borders |
| Tooltips | Dark background, white text |
| Icons | qtawesome Font Awesome 5 only |
| Primary buttons | Black background, white text |
| Secondary buttons | White background, border, dark text |

## UI and Translation Rules

| Rule | Implementation |
|---|---|
| No fake symbols in production UI | Active PySide6 source uses qtawesome icons or plain text only |
| No logic-coupled translation | Database enums, audit action codes, and import/export headers stay stable |
| Login language changes session language | The selected language is applied before authentication and carried into the main app |
| Arabic support | Arabic is available in the login selector and enables right-to-left layout direction |
| Page consistency | The same title scale, card style, table style, button style, and form sizing are used across pages |
| Tooltips | Dark background, white text, used for truncated table content |
| Dialog readability | Message boxes use white background, dark text, and explicit button styling |

## Operational Rules

| Topic | Rule |
|---|---|
| Audit logging | Important create, update, delete, promotion, sanction, commendation, import, and settings actions must call `log_action(...)` before commit |
| Audit ordering | Audit feeds sort by `performed_at DESC, id DESC` so same-second actions still appear in the correct order |
| Future-dated audit rows | Dashboard and audit feeds hide future timestamps from demo seed artifacts so current user actions appear first |
| Refresh behavior | Main navigation recreates or refreshes data-heavy pages so the user does not need to restart the app to see changes |
| Promotion math | Promotion progress is calculated live from race start, commendations, sanctions, and the active rule |
| Sanction effect | Only unresolved sanctions contribute active delay |
| Commendation cap | Maximum three commendations per employee in the current role |
| Hierarchy drill-down | Teams and higher units can open an employee list dialog for that scope |
| Branding updates | Saving company settings updates sidebar branding, login brand text, and main window title |
| Import stability | User-facing UI can translate, but import file structure remains stable for onboarding and batch upload compatibility |

## Architecture

| Layer | Responsibility |
|---|---|
| `main.py` | Starts QApplication, initializes DB, applies global styling, opens login |
| `src/core` | Session language and persistent application/company settings |
| `src/database/models.py` | SQLAlchemy table definitions and relationships |
| `src/database/connection.py` | Engine/session setup, seeding, IDs, promotion math helpers, audit helper |
| `src/ui/login_window.py` | Authentication, language selection, login-specific branding |
| `src/ui/main_window.py` | Main layout, sidebar, role-based page access, page refresh/rebuild |
| `src/ui/pages` | Feature pages that render data and call database helpers |

Design principle: the UI should display and trigger workflows, while reusable calculations and database helpers remain centralized. Promotion months remaining should be calculated from source data every time rather than stored as a denormalized value.

## Verification

Current cleanup verification:

```bash
python -m compileall main.py src scripts
```

An offscreen PySide6 smoke test instantiates login, main window, dashboard, employees, hierarchy, promotions, commendations, sanctions, audit log, import data, and settings pages in English, Hungarian, and Arabic.

## Notes for Future Work

- Continue expanding translation coverage for deeper form help text and validation messages.
- Consider moving more business calculations from UI pages into a dedicated service module if the project grows.
- Keep demo/prototype artifacts in `MockUI/` separate from the production PySide6 app.
- Keep `scripts/seed_demo_company.py` because it is useful for demos, presentations, and testing realistic data density.
