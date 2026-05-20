# MyHR

![Status](https://img.shields.io/badge/status-In%20Progress%20%7C%20Project%20Lab-2563eb)

Offline desktop HR management system for employee records, hierarchy, promotions, salary increments, commendations, sanctions, imports, exports, backups, audit logs, and admin-managed HR accounts.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3 | Main application language |
| UI | PySide6 / Qt | Native desktop screens, dialogs, tables, and RTL support |
| Database | SQLite | Offline single-file database |
| ORM | SQLAlchemy | Models, relationships, indexes, and business queries |
| Icons | qtawesome / Font Awesome 5 | Consistent icon buttons |
| Import | openpyxl | XLSX employee import support |
| Settings | Qt QSettings | Local company branding settings |
| Docs | python-docx | Word guide generation |

## Features

- Admin and HR Officer login with role-aware navigation.
- English, Hungarian, and Arabic UI, with Arabic right-to-left layout.
- Employee add, edit, view, delete, search, filters, generated employee IDs, and paginated lists.
- BSc, MSc, PhD level assignment plus Other/Misc employee handling.
- OTHERS hierarchy branch for janitors, cleaners, guards, painters, and similar employees.
- Salary range validation against admin-defined level ranges.
- Organization hierarchy rules with one organization root and ordered parent levels.
- Live promotion race and sub-race tracking.
- Promotion approvals with salary updates and promotion history.
- Annual salary increment review from the dashboard.
- Single and team commendations with promotion-month reduction.
- Active and resolved sanctions with promotion delay.
- CSV/XLSX employee import with validation and manager wiring.
- Employee CSV export and SQLite database backup.
- Admin user management for HR accounts with soft deactivation.
- Immutable audit log with `username: full name` identity snapshots.
- Performance-focused list loading with database indexes and bounded table rendering.

## Project Structure

```text
MyHR/
|-- main.py                         # App entry point
|-- requirements.txt                # Python dependencies
|-- README.md                       # Project overview
|-- myhr.db                         # Local SQLite database
|-- assets/                         # Project-level assets
|-- docs/                           # Generated guides and project documents
|   |-- MyHR_User_Guide.docx
|   `-- MyHR_Developer_Guide.docx
|-- scripts/
|   |-- generate_docs.py            # Regenerates Word documentation
|   `-- seed_demo_company.py        # Resets and seeds demo company data
`-- src/
    |-- core/
    |   |-- app_settings.py         # Company branding settings
    |   `-- i18n.py                 # EN, HU, AR translations and RTL flag
    |-- database/
    |   |-- models.py               # SQLAlchemy schema
    |   `-- connection.py           # Sessions, seed defaults, business logic
    `-- ui/
        |-- login_window.py         # Authentication screen
        |-- main_window.py          # Sidebar, routing, role access
        |-- styles.py               # Shared UI styles
        `-- pages/
            |-- dashboard.py        # Metrics and annual increment review
            |-- employees.py        # Employee list, forms, profile, race view
            |-- hierarchy.py        # Organization hierarchy builder
            |-- promotions.py       # Eligibility tracker and history
            |-- commendations.py    # Commendation issuance and history
            |-- sanctions.py        # Sanction issuance, resolution, history
            |-- audit_log.py        # Immutable audit viewer
            |-- import_data.py      # CSV/XLSX import workflow
            `-- settings.py         # Admin configuration and user management
```

## Install and Run

```bash
python -m pip install -r requirements.txt
python main.py
```

The SQLite database is created and seeded automatically on first run.

Optional demo data reset:

```bash
python scripts/seed_demo_company.py
```

## Default Credentials

| Role | Username | Password |
|---|---|---|
| admin | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

## Demo Data

The demo seed includes a normal company hierarchy plus an `OTHERS` branch:

- Other Employees Head reports to the CEO.
- Janitor, Cleaner, Window Cleaner, Security Guard, and Painter report to the Other Employees Head.
- Other/Misc employees receive annual increments and sub-race milestones.
- Other/Misc employees do not use the standard L7 to L1 promotion race and are excluded from commendations and sanctions.

## Screenshots

- `[Screenshot placeholder: Login screen]`
- `[Screenshot placeholder: Dashboard]`
- `[Screenshot placeholder: Employee profile with race and sub-race]`
- `[Screenshot placeholder: Organization hierarchy with OTHERS branch]`
- `[Screenshot placeholder: User management and audit log]`

## Architecture Decisions

| Decision | Reason |
|---|---|
| Desktop app instead of web app | Fits offline Project Lab scope and avoids server deployment. |
| SQLite local database | Simple backup, single-file storage, and no external DB service. |
| SQLAlchemy ORM | Keeps relationships explicit and business queries readable. |
| Database indexes | Keeps employee, audit, race, sanction, and history queries responsive as data grows. |
| Paginated table rendering | Prevents large employee and history lists from creating thousands of widgets at once. |
| Live promotion calculation | Prevents stale stored eligibility values. |
| Batch race calculation for lists | Preserves the existing formula while avoiding repeated per-employee queries. |
| Audit identity snapshots | Old logs keep the original username and full name after account changes. |
| Soft-delete HR users | Preserves audit references and prevents orphaned user history. |
| Dictionary i18n | Simple EN/HU/AR translation layer for a desktop prototype. |
| Stable internal values | User data, enums, audit codes, and import/export headers are not translated. |

## Access Control

| Page / Capability | admin | HR Officer |
|---|---:|---:|
| Dashboard | Yes | Yes |
| Employees | Yes | Yes |
| Organization Hierarchy | Yes | Yes |
| Promotions | Yes | Yes |
| Commendations | Yes | Yes |
| Sanctions | Yes | Yes |
| Audit Log | Yes | Yes |
| Import Data | Yes | Yes |
| Settings | Yes | No |
| User Management | Yes | No |
| Salary and Promotion Configuration | Yes | No |
| Export and Backup | Yes | No |

## Documentation

- `docs/MyHR_User_Guide.docx`
- `docs/MyHR_Developer_Guide.docx`

Regenerate the Word guides:

```bash
python scripts/generate_docs.py
```

## Future Scope

- Package the desktop app as an installer.
- Add automated tests for promotion math, imports, audit snapshots, access control, and performance-sensitive list pages.
- Add richer reports for yearly promotions, salary budget impact, sanctions, and commendations.
- Add scheduled backup reminders and backup health checks.
- Add a formal migration tool if schema changes continue.
- Consider encrypted backups or protected local storage for sensitive HR data.

## Author and Supervisor

| Role | Name |
|---|---|
| Developer | Muhammad Ibrahim Shoeb |
| Supervisor | Dr. Husam Al-Maghoosi |
| Program | BME Project Lab, Semester 8 |
