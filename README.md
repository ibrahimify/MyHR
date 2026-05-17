# MyHR

![Status](https://img.shields.io/badge/status-In%20Progress%20-%20Project%20Lab-2563eb)

Offline desktop HR management system for employees, hierarchy, promotions, commendations, sanctions, salary increments, imports, exports, backups, audit logs, and admin user management.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3 | Main application language |
| UI | PySide6 / Qt | Native desktop UI, dialogs, tables, RTL support |
| Database | SQLite | Local offline database file |
| ORM | SQLAlchemy | Models, relationships, and queries |
| Icons | qtawesome / Font Awesome 5 | Consistent professional icon buttons |
| Excel import | openpyxl | XLSX onboarding import |
| Settings | Qt QSettings | Company name and subtitle |
| Docs | python-docx | Word guide generation |

## Features

- Admin and HR Officer login with role-aware navigation.
- English, Hungarian, and Arabic UI; Arabic uses right-to-left layout.
- Employee add, edit, view, delete, search, filters, profile history, and generated employee IDs.
- BSc/MSc/PhD level assignment plus Other/Misc employee track.
- Salary range validation based on admin-defined levels.
- Rule-based organization hierarchy with one organization root and an OTHERS branch.
- Live promotion race and sub-race tracking.
- Promotion approvals with salary update and promotion history.
- Single and team commendations with promotion-month reduction.
- Active and resolved sanctions with promotion delay.
- Annual salary increment review from the dashboard.
- CSV/XLSX employee import with validation and manager wiring.
- Employee CSV export and SQLite database backup.
- Admin user management for HR accounts with soft deactivation.
- Immutable audit log with `username: full name` identity snapshots.

## Project Structure

```text
MyHR/
  main.py
  requirements.txt
  README.md
  myhr.db
  docs/
    MyHR_User_Guide.docx
    MyHR_Developer_Guide.docx
  scripts/
    seed_demo_company.py
    generate_docs.py
  src/
    core/
      app_settings.py
      i18n.py
    database/
      connection.py
      models.py
    ui/
      login_window.py
      main_window.py
      styles.py
      pages/
        dashboard.py
        employees.py
        hierarchy.py
        promotions.py
        commendations.py
        sanctions.py
        audit_log.py
        import_data.py
        settings.py
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
| Administrator | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

## Screenshots

- `[Screenshot placeholder: Login screen]`
- `[Screenshot placeholder: Dashboard]`
- `[Screenshot placeholder: Employee profile with race and sub-race]`
- `[Screenshot placeholder: Organization hierarchy]`
- `[Screenshot placeholder: User management and audit log]`

## Architecture Decisions

| Decision | Reason |
|---|---|
| Desktop app instead of web app | Fits offline Project Lab scope and avoids server deployment. |
| SQLite local database | Simple backup, single-file storage, and no external DB service. |
| SQLAlchemy ORM | Keeps relationships explicit and business queries readable. |
| Live promotion calculation | Prevents stale stored eligibility values. |
| Audit identity snapshots | Old logs keep the original username and full name after account changes. |
| Soft-delete HR users | Preserves audit references and prevents orphaned user history. |
| Dictionary i18n | Simple EN/HU/AR translation layer for a desktop prototype. |
| Stable internal values | User data, enums, audit codes, and import/export headers are not translated. |

## Access Control

| Page / Capability | Admin | HR Officer |
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
- Add automated tests for promotion math, imports, audit snapshots, and access control.
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
