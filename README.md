# MyHR - Employee Management System

A standalone desktop application for managing employee records in government-like organizations.

**Supervisor:** Dr. Husam Al-Maghoosi  
**Developer:** Muhammad Ibrahim Shoeb  
**Status:** Project Lab - In Progress (core logic complete, UI polish pending)

---

## Running the MockUI

The MockUI is a React-based interactive prototype of the application interface built with Vite, TypeScript, and Tailwind CSS.

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

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| UI Framework | PySide6 (Qt6) |
| Database | SQLite (local, offline) |
| ORM | SQLAlchemy 2.0 |
| Version Control | GitHub |
| UI Mockup | Figma / Draw.io |

---

## Project Structure

```
MyHR/
├── main.py                  # Entry point
├── requirements.txt
├── docs/                    # Presentations, analysis documents
├── MockUI/                  # Figma UI mockup (reference only)
└── src/
    ├── core/
    │   └── i18n.py          # Internationalization (EN / HU / AR)
    ├── database/
    │   ├── models.py        # All 10 SQLAlchemy models
    │   └── connection.py    # DB init, business logic, helpers
    └── ui/
        ├── login_window.py  # Login screen with language selector
        ├── main_window.py   # Main shell + sidebar navigation
        └── pages/
            ├── dashboard.py
            ├── employees.py
            ├── hierarchy.py
            ├── promotions.py
            ├── commendations.py
            ├── sanctions.py
            ├── audit_log.py
            ├── import_data.py
            └── settings.py
```

---

## Features (Semester 1 - Project Lab)

### Core
- **Employee Management** - Add, edit, view employees with unique IDs (EMP-XXXX). Degree-based level auto-assignment: BSc → L7, MSc → L6, PhD → L5
- **Organizational Hierarchy** - Unlimited depth tree (Organization → Division → Department → Unit → Team). Self-referencing structure with head/in-charge assignment
- **Promotion Race Engine** - Live calculation (never stored). Base track duration per level transition. Commendations reduce months, sanctions add months. Clock resets after promotion
- **Commendations** - 3 categories: Cat1 (−1mo), Cat2 (−3mo), Cat3 (−6mo). Max 3 per employee per role enforced. Bulk team awards supported. Unique COM-YYYY-MMDD-NNN IDs
- **Sanctions** - 1–12 month promotion delay. Unique SAN-YYYY-MMDD-NNN IDs. Active/resolved tracking
- **CSV Import** - Upload, validate, preview, import. Template download included
- **Audit Log** - Immutable record of every action. Searchable, filterable, with full tooltip descriptions
- **Settings** - Configurable salary ranges, annual increment rules, password change, DB backup, employee export

### Multi-language
Login screen supports English, Hungarian, and Arabic (RTL layout via Qt)

### Two Actors
- **Admin** - Full access to all modules
- **HR Officer** - Manage employees, commendations, sanctions except settings

---

## Database Schema

10 tables: `system_user`, `org_unit`, `employee`, `title`, `promotion_rule`, `promotion_history`, `commendation`, `commendation_employee`, `sanction`, `salary_increment_history`, `audit_log`

---

## Running the App

```bash
pip install -r requirements.txt
python main.py
```

**Default credentials:**
- Admin: `admin` / `admin123`
- HR Officer: `hr_officer` / `hr123`

---


## Thesis Extension (Semester 2 - Planned)

- Configurable promotion rule management via UI
- Advanced audit history with before/after diff view
- Yearly reporting summaries (PDF export)
- Improved input validation and error handling
- Email reminder for salary increments
- Dark mode + UI polish
- Multi-language expansion

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Promotion months remaining | Calculated live | Avoids stale data, fully auditable |
| Annual salary increment | Manual with dashboard prompt | Simpler for offline desktop app |
| Language preference | Per session | No DB overhead, suitable for 1-2 users |
| Employee access | None (data subjects only) | Per project requirement |