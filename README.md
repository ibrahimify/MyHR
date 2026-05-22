
# MyHR -  Employee Management System



A standalone, offline desktop application for managing employee records, organizational hierarchy, promotions, commendations, and sanctions in government like organizations.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/PySide6-Qt6-41CD52?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white) <br/>
![Status](https://img.shields.io/badge/Status-Semester%201%20Complete-brightgreen)


<p align="center">
  <img src="docs/media/demo.gif" alt="MyHR Demo" width="800"/>
</p>

---

**Supervisor:** Dr. Husam Al-Maghoosi   
**Developer:** Muhammad Ibrahim Shoeb  
**Institution:** Budapest University of Technology and Economics   
**Status:** <br/>Semester 1 (Project Lab) -  Complete <br/>Semester 2 (Thesis) -  In Progress

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| UI Framework | PySide6 6.11.0 (Qt6) |
| Database | SQLite (local, offline -  no networking required) |
| ORM | SQLAlchemy 2.0 |
| Icons | qtawesome 1.4.2 (Font Awesome 5) |
| Spreadsheet Support | openpyxl (XLSX import) |
| Version Control | GitHub |
| UI Reference | Figma MockUI (React + Tailwind, in `MockUI/` folder) |

---

## Getting Started

## 1. Running the MockUI

The MockUI is a React-based interactive prototype of the application interface built with Vite, TypeScript, and Tailwind CSS. It was used as the design reference for the desktop app's UI.

### Prerequisites
- Node.js 16+ and npm/pnpm installed

### Setup & Run

1. Navigate to the MockUI directory:
```bash
cd MockUI
```

2. Install dependencies:
```bash
npm install
# or if using pnpm:
pnpm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and navigate to `http://localhost:5173` (or the port shown in terminal)

### Build for Production
```bash
npm run build
npm run preview
```

---
## 2. Running the Desktop Appication

## Install & Run

```bash
pip install -r requirements.txt
python main.py
```

### Default Credentials

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

---

## Project Structure

```
MyHR/
├── main.py                        # Entry point
├── requirements.txt               # Python dependencies
├── myhr.db                        # SQLite database (auto-created on first run)
├── docs/
│   ├── media/
│   │   ├── demo.gif              # App walkthrough GIF
│   │   └── screenshots/
│   │       ├── login.png
│   │       ├── dashboard.png
│   │       ├── employees.png
│   │       └── ...etc
├── guides/
│   │   ├── MyHR_User_Guide.docx        # End-user manual
│   │   └── MyHR_Developer_Guide.docx   # Technical handover guide
├── scripts/
│   ├── seed_demo_company.py       # Generates a 300-person demo dataset
│   └── generate_docs.py           # Rebuilds documentation
├── MockUI/                        # React + Tailwind design reference (not the actual app)
└── src/
    ├── core/
    │   ├── i18n.py                # Internationalization (EN / HU / AR)
    │   └── app_settings.py        # Company branding via QSettings
    ├── database/
    │   ├── models.py              # 10 SQLAlchemy models + 1 junction table
    │   └── connection.py          # DB init, business logic, audit helpers
    └── ui/
        ├── styles.py              # Shared style constants
        ├── login_window.py        # Login with language selector
        ├── main_window.py         # Sidebar navigation shell
        ├── assets/
        │   └── chevron_down.svg   # Dropdown arrow icon
        └── pages/
            ├── dashboard.py       # Stats, salary increment approval, activity feed
            ├── employees.py       # List, add, edit, profile, delete
            ├── hierarchy.py       # Org tree (unlimited depth)
            ├── promotions.py      # Race tracker, approvals, rules, history
            ├── commendations.py   # Single + team awards (3 categories)
            ├── sanctions.py       # Disciplinary actions (1–12 month delays)
            ├── audit_log.py       # Immutable activity log
            ├── import_data.py     # CSV/XLSX bulk import with validation
            └── settings.py        # Salary, increments, users, security, backup
```

---

## Features

### Employee Management
- Add, edit, view, and delete employees with auto-generated unique IDs (EMP-XXXX)
- Degree-based level auto-assignment on hire: BSc → L7, MSc → L6, PhD → L5
- Other/Miscellaneous employee track for non-standard roles (janitors, guards, etc.)
- Employee profile with promotion race status, commendation and sanction history
- Search, filter, and paginated employee list

### Organizational Hierarchy
- Unlimited depth tree: Organization → Division → Department → Unit → Team → Position
- Self-referencing structure with head/in-charge assignment per node
- Inline add, edit, and delete with dependency checks
- Dedicated OTHERS branch for miscellaneous employees

### Promotion Race Engine
- Each level is a race track with a configurable base duration in months
- Employees advance 1 checkpoint per month automatically
- Commendations speed up the race (−1, −3, or −6 months)
- Sanctions delay the race (+1 to +12 months)
- Months remaining calculated live -  never stored in the database
- Clock resets to zero after each promotion
- Sub-race milestones (L7.1, L7.2, etc.) tracked for annual checkpoints
- Promotion levels: L7 → L6 → L5 → L4 → L3 → L2 (Board) → L1 (CEO)

### Commendations
- Three categories: Category 1 (−1 month), Category 2 (−3 months), Category 3 (−6 months)
- Maximum 3 commendations per employee per role -  enforced in backend
- Single employee or bulk team awards
- Team awards skip employees at max limit with warning instead of blocking
- Unique auto-generated IDs: COM-YYYY-MMDD-NNN

### Sanctions
- Disciplinary actions with 1–12 month promotion delay
- Types: verbal warning, written warning, suspension, final warning
- Active/resolved tracking -  only unresolved sanctions affect the promotion race
- Unique auto-generated IDs: SAN-YYYY-MMDD-NNN

### Annual Salary Increment
- Separate from promotion -  every employee's salary increases on their anniversary date
- Dashboard alert banner when employees are due for increment
- Admin reviews and approves individually or in bulk
- Configurable per level: percentage or fixed amount
- Full before/after salary audit trail

### Data Import & Export
- CSV and XLSX bulk import with validation and preview
- Error rows highlighted before import -  only valid rows are written
- Downloadable CSV template with sample data
- Employee data export to CSV
- SQLite database backup to any location

### Audit Log
- Immutable record of every admin and HR action
- Stores username snapshot at time of action -  survives account renames
- Searchable by action, description, user, and category
- Filterable with full-text tooltips for long descriptions

### User Management (Admin Only)
- Create, edit, and deactivate HR Officer accounts
- Each HR account has its own username and password
- Soft delete: deactivated accounts cannot log in but remain in audit history
- Admin can edit their own username and password for handover scenarios
- Audit logs preserve the original username even after account changes

### Settings (Admin Only)
- Company name and subtitle (reflected on login screen and sidebar)
- Salary ranges per level with live currency badge
- Annual increment rules per level (percentage or fixed)
- Promotion track base duration configuration
- Password management
- Database backup and export

### Multi-language Support
- Language selector on login: English, Hungarian, Arabic
- Arabic applies right-to-left layout automatically via Qt
- Per-session language selection -  resets on logout

### Access Control

| Capability | Admin | HR Officer |
|---|:---:|:---:|
| Dashboard | ✓ | ✓ |
| Employee Management | ✓ | ✓ |
| Organization Hierarchy | ✓ | ✓ |
| Promotions | ✓ | ✓ |
| Commendations | ✓ | ✓ |
| Sanctions | ✓ | ✓ |
| Audit Log | ✓ | ✓ |
| Import Data | ✓ | ✓ |
| Settings & Configuration | ✓ | X |
| User Management | ✓ | X |
| Export & Backup | ✓ | X |

---

## Database Schema

| Table | Purpose |
|---|---|
| `system_user` | Admin and HR Officer accounts (employees never log in) |
| `org_unit` | Self-referencing organizational hierarchy |
| `employee` | Core employee records with personal and work-facing data |
| `title` | Salary levels L1–L7 + Other, with ranges and increment config |
| `promotion_rule` | Base months per level transition (configurable) |
| `promotion_history` | Every promotion applied (immutable) |
| `commendation` | Awards with category and month impact |
| `commendation_employee` | Junction -  one commendation to many employees |
| `sanction` | Disciplinary actions with delay months and resolution tracking |
| `salary_increment_history` | Annual increment records with before/after values |
| `audit_log` | Immutable activity trail with username snapshots |

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Promotion months remaining | Calculated live, never stored | Avoids stale data, fully auditable from raw records |
| Annual salary increment | Manual approval via dashboard | Appropriate for offline app without background services |
| Language preference | Per session, not stored in DB | Minimal overhead for 1–2 concurrent users |
| Employee system access | None -  data subjects only | Per professor requirement |
| Audit log identity | Username snapshot at write time | Survives account renames, ensures accountability |
| HR account deletion | Soft delete (is_active=False) | Preserves audit log references |
| Page data freshness | Recreated per visit | Ensures live data without manual refresh |
| List page performance | Batched race calculation | Same formula, fewer DB queries |

---

## Documentation

| Document | Location |
|---|---|
| User Guide | `docs/MyHR_User_Guide.docx` |
| Developer Guide | `docs/MyHR_Developer_Guide.docx` |
| UI Mockup | `MockUI/` -  run with `cd MockUI && npm install && npm run dev` |
| Demo Dataset | `scripts/seed_demo_company.py` -  generates 300 employees |

---

## Thesis Extension (Semester 2 -  Planned)

- Configurable promotion and allowance policies via dedicated UI editor
- Audit log before/after diff view for change comparison
- Yearly reporting summaries with PDF export
- Improved input validation and error handling
- Email reminders for salary increment due dates
- Dark mode and extended multi-language support
- Desktop app packaging as a standalone installer
- Automated test suite for promotion math, imports, and access control
- Encrypted backups for sensitive HR data
- Formal database migration tooling

---

## License

Academic project -  Budapest University of Technology and Economics (BME), 2025–2026.
