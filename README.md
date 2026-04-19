# MyHR - Employee Management System

A standalone desktop application for managing employee records in government-like organizations.

**Supervisor:** Dr. Husam Al-Maghoosi  
**Developer:** Muhammad Ibrahim Shoeb  
**Status:** Active Development — Semester 1 complete, UI polish complete, Thesis extension starting

---

## Running the MockUI

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

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| UI Framework | PySide6 6.11.0 (Qt6) |
| Database | SQLite (local, offline) |
| ORM | SQLAlchemy 2.0 |
| Icons | qtawesome 1.4.2 (Font Awesome 5) |
| Version Control | GitHub |
| UI Reference | Figma MockUI (React + Tailwind, in `MockUI/` folder) |

---

## Project Structure

```
MyHR/
├── main.py                  # Entry point — app init, global stylesheet, Fusion style
├── requirement.txt          # Python dependencies
├── myhr.db                  # SQLite database (auto-created on first run)
├── docs/                    # Presentations, analysis documents
├── MockUI/                  # React+Tailwind design reference (not the actual app)
└── src/
    ├── core/
    │   └── i18n.py          # Internationalization (EN / HU / AR)
    ├── database/
    │   ├── models.py        # All 10 SQLAlchemy models
    │   └── connection.py    # DB init, business logic, helpers
    └── ui/
        ├── assets/
        │   └── chevron_down.svg   # Global dropdown arrow icon
        ├── styles.py              # Shared style constants & helpers
        ├── login_window.py        # Login screen with language selector
        ├── main_window.py         # Main shell + white sidebar navigation
        └── pages/
            ├── dashboard.py       # Live stats + salary increment approval
            ├── employees.py       # Employee list, add form, profile view
            ├── hierarchy.py       # Org tree (unlimited depth)
            ├── promotions.py      # Race tracker, approvals, history
            ├── commendations.py   # Single + team awards (3 categories)
            ├── sanctions.py       # 1–12 month promotion delays
            ├── audit_log.py       # Immutable action log
            ├── import_data.py     # CSV bulk import
            └── settings.py        # Salary ranges, increment rules, security
```

---

## Features (Semester 1 - Project Lab)

### Core
- **Employee Management** — Add, edit, view employees with unique IDs (EMP-XXXX). Degree-based level auto-assignment: BSc → L7, MSc → L6, PhD → L5
- **Organizational Hierarchy** — Unlimited depth tree (Organization → Division → Department → Unit → Team). Self-referencing structure with head/in-charge assignment
- **Promotion Race Engine** — Live calculation (never stored). Base track duration per level transition. Commendations reduce months, sanctions add months. Clock resets after promotion
- **Commendations** — 3 categories: Cat1 (−1mo), Cat2 (−3mo), Cat3 (−6mo). Max 3 per employee per role enforced. Bulk team awards supported. Unique COM-YYYY-MMDD-NNN IDs
- **Sanctions** — 1–12 month promotion delay. Unique SAN-YYYY-MMDD-NNN IDs. Active/resolved tracking
- **Salary Increment** — Dashboard alert when employees are due. Admin reviews and approves per employee via dialog
- **CSV Import** — Upload, validate, preview, import. Template download included
- **Audit Log** — Immutable record of every action. Searchable, filterable, with full tooltip descriptions
- **Settings** — Configurable salary ranges per level (with live currency badge), annual increment rules, password change, DB backup, employee export

### UI
- White sidebar with blue active state, Font Awesome 5 icons throughout (qtawesome)
- Login page opens maximized with blue gradient background, real user/lock field icons
- All dropdown menus show chevron arrow indicators
- Page background `#f9fafb`, card `white` with `border: 1px solid #e5e7eb`
- Matches the Figma MockUI design tokens

### Multi-language
Login screen supports English, Hungarian, and Arabic (RTL layout via Qt)

### Two Actors
- **Admin** — Full access to all modules including Settings
- **HR Officer** — Manage employees, commendations, sanctions; no access to Settings

---

## Database Schema

10 tables: `system_user`, `org_unit`, `employee`, `title`, `promotion_rule`, `promotion_history`, `commendation`, `commendation_employee`, `sanction`, `salary_increment_history`, `audit_log`

---

## Running the App

```bash
# Install dependencies
py -3.12 -m pip install pyside6 sqlalchemy qtawesome

# Run
py -3.12 main.py
```

**Default credentials:**
- Admin: `admin` / `admin123`
- HR Officer: `hr_officer` / `hr123`

---

## Progress Log

### Session 2 — UI Overhaul + Functional Fixes
- Fixed: Sidebar dark background → white with `border-right: 1px solid #e5e7eb`
- Fixed: Login opens maximized with blue gradient background
- Fixed: Login form shows real user/lock icons (qtawesome) instead of "U"/"P" text
- Fixed: All dropdown arrows restored across all pages (were hidden by bad CSS rule)
- Fixed: Grey borders everywhere — caused by overly broad `QWidget { }` global stylesheet rule
- Fixed: Promotions "View" button now navigates to employee profile tab
- Fixed: Dashboard "Review Increments" banner opens salary approval dialog with per-row approve
- Added: `src/ui/styles.py` shared style module
- Added: `src/ui/assets/chevron_down.svg` for consistent dropdown arrows
- Added: qtawesome 1.4.2 dependency (Font Awesome 5 icons throughout)
- Improved: Settings salary tab — currency field highlighted in blue, live-updating currency badge between Min/Max

### Session 1 — Core Implementation (Semester 1)
- All 10 pages scaffolded and fully functional
- Business logic: promotion race engine, commendation cap enforcement, sanction delay
- Multi-language login (EN/HU/AR) with RTL layout for Arabic
- CSV import with validation and preview
- Audit log (immutable, searchable, filterable)
- Admin vs HR Officer access control enforced throughout
- Default credentials: admin/admin123 and hr_officer/hr123

---

## Thesis Extension (Semester 2 — In Progress)

- Promotion rule management editor via UI (rules tab exists, full editor TBD)
- Before/after diff view in audit log
- Yearly reporting summaries (PDF export)
- Improved input validation and error UX
- Email reminder for salary increment due dates
- Multi-language expansion (post-login translation for all pages)

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Promotion months remaining | Calculated live | Avoids stale data, fully auditable |
| Annual salary increment | Manual with dashboard prompt | Simpler for offline desktop app |
| Language preference | Per session | No DB overhead, suitable for 1–2 users |
| Employee access | None (data subjects only) | Per project requirement |
| Dashboard/Employees/Promotions pages | Recreated on every visit | Ensures live data without manual refresh |
