# MyHR — Project Context for Claude Code

> **For Claude:** Read this file at the start of every session. It contains the full project summary, requirements, architectural rules, and current status. Running `py -3.12 main.py` from the project root launches the app.

---

## Project Requirements (Semester 1 — Project Lab)

- Standalone desktop app, offline, local SQLite DB, no networking
- Two actors: Admin and HR Officer (employees are data subjects only — no login)
- Employee CRUD with unique IDs (EMP-XXXX)
- Organizational hierarchy (unlimited depth, self-referencing)
- Degree-based salary levels: BSc→L7, MSc→L6, PhD→L5
- Configurable promotion rules (time-based race track)
- Commendation and sanction management
- Bulk CSV import
- Audit logging

---

## Project Requirements (Semester 2 — Thesis Extension)

- Configurable rule management via UI
- Advanced audit history with before/after diff
- Yearly reporting and PDF export
- Improved input validation and error handling
- Email reminder for salary increments
- Multi-language expansion (post-login translation)
- Full UI polish (complete as of Session 2)

---

## What We Learned from Professor Meetings

**Meeting 1:**
- Standalone desktop app confirmed
- Two actors: Admin and HR Officer
- Org hierarchy needed (CEO down to individual contributors)
- Employee CRUD, commendations, sanctions, rule-based promotions

**Meeting 2:**
- Employees are data subjects only — no employee login ever
- Unique employee IDs required
- Degree → level mapping: BSc→L7, MSc→L6, PhD→L5
- Salary levels configurable by admin per region
- Bulk commendation for teams (one commendation → multiple employees)
- Two actors confirmed: Admin (system maintainer) + HR Officer (records manager)

**Meeting 3:**
- Language switcher on login: English, Hungarian, Arabic
- Annual salary increment separate from promotion
- Promotion as a "race" metaphor — 1 checkpoint per month
- Commendation categories: Cat1=−1mo, Cat2=−3mo, Cat3=−6mo
- Max 3 commendations per employee per role
- Sanctions in months (1–12), not days
- Sanctions delay promotion race
- Everything must be editable (built for selling to different companies)
- Unique IDs for commendations (COM-) and sanctions (SAN-)

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Promotion months remaining | Calculated live, never stored | Avoids stale data, fully auditable |
| Annual salary increment | Manual with dashboard prompt | Simpler for offline desktop app |
| Language | Per session | No DB overhead |
| Employee access | None | Per professor requirement |
| Commendation query | Two-step subquery | SQLite JOIN reliability |

---

## What We Built

**Tech stack:** Python 3.12 + PySide6 6.11.0 + SQLite + SQLAlchemy 2.0

**Additional dependency:** qtawesome 1.4.2 — Font Awesome 5 icons via `qta.icon("fa5s.*", color="#hex")`
Install: `py -3.12 -m pip install pyside6 sqlalchemy qtawesome`

**10 DB tables:** `system_user`, `org_unit`, `employee`, `title`, `promotion_rule`, `promotion_history`, `commendation`, `commendation_employee`, `sanction`, `salary_increment_history`, `audit_log`

**Pages built:**
- Login — language switcher (EN/HU/AR), RTL support for Arabic, maximized on open, blue gradient bg, qtawesome user/lock icons in form fields
- Dashboard — live stats, salary increment alert banner → opens `SalaryIncrementReviewDialog`, recent activity
- Employees — list with search/filter, add form with degree→level auto-assign, profile with live promotion race status
- Org Hierarchy — unlimited depth tree, add/edit/delete units with dependency checks
- Promotions — live race tracker, approve promotion, history, configurable base months, "View" button navigates to employee profile
- Commendations — single + team award, 3 categories, max 3 cap enforced, unique COM- IDs, qtawesome icons on mode buttons
- Sanctions — 1–12 month delay, unique SAN- IDs, active/resolved tracking
- Audit Log — immutable, searchable, filterable, hover tooltips
- Import Data — CSV upload, validate, preview, import with template download
- Settings — salary ranges (currency badge live-updates), annual increment config, password change, DB backup, CSV export

**Additional source files:**
- `src/ui/styles.py` — shared style constants: `btn_primary()`, `btn_blue()`, `btn_outline()`, `btn_ghost()`, `CARD_SS`, `TABLE_SS`, `TAB_SS`, `INPUT_SS`, `badge_ss()`
- `src/ui/assets/chevron_down.svg` — dropdown arrow SVG referenced globally via `QComboBox::down-arrow`

**Access control:**
- Admin: full access to all pages
- HR Officer: everything except Settings

**Default credentials:**
- Admin: `admin` / `admin123`
- HR Officer: `hr_officer` / `hr123`

---

## UI Architecture — Critical Rules for Future Claude Sessions

### 1. Never use `QWidget { }` in the global stylesheet
Setting `QWidget { color/background/font... }` in `app.setStyleSheet()` disables Fusion native rendering on ALL widgets — causes grey borders and grey backgrounds everywhere. Only target specific widget types: `QLabel`, `QLineEdit`, `QComboBox`, `QTableWidget`, etc.

### 2. Dropdown arrow fix
`QComboBox::drop-down { border: none; }` removes the arrow entirely when combined with a custom QComboBox style. The correct fix lives in `main.py`:
```
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 28px; border: none; background: transparent;
}
QComboBox::down-arrow {
    image: url(src/ui/assets/chevron_down.svg); width: 10px; height: 6px;
}
```
**Never** add `QComboBox::drop-down { border: none; }` in per-page combo styles — it overrides the global arrow. Just set `QComboBox { ... }` without touching `::drop-down`.

### 3. Sidebar background
`background: transparent` on a child QWidget inside the sidebar renders as Fusion grey in CSS mode, NOT the parent's white. Always use explicit `background: white` on nav container widgets inside the sidebar.

### 4. Login window gradient
Use `QWidget#LoginWindow { background: qlineargradient(...) }` with `setObjectName("LoginWindow")` set on the window. Using `QWidget { background: gradient }` applies the gradient to ALL children including cards, inputs, and buttons.

### 5. Design tokens (matches MockUI)

| Token | Value |
|---|---|
| Primary blue | `#2563eb` (hover: `#1d4ed8`) |
| Near-black button | `#030213` |
| Page background | `#f9fafb` |
| Card background | `white`, `border: 1px solid #e5e7eb`, `border-radius: 10–12px` |
| Sidebar | `white`, `border-right: 1px solid #e5e7eb`, `width: 256px` |
| Active nav item | `background: #eff6ff; color: #1d4ed8` |
| Inactive nav item | `color: #6b7280`, hover `background: #f3f4f6` |
| Field label | `font-size: 12px; font-weight: bold; color: #6b7280` |
| Icons | `qtawesome fa5s.*` — nav sidebar, login form, commendations, etc. |

### 6. Pages that recreate on every visit (cache invalidated)
`dashboard`, `employees`, `promotions` — see `_navigate()` in `main_window.py`. These are always freshly instantiated to show up-to-date data. Other pages are cached after first load.

---

## Functional Gap Status

| Gap | Status | Notes |
|---|---|---|
| Promotions "View" button → employee profile | ✅ Fixed | `navigate_to_employee` callback chain in `main_window.py` |
| Dashboard salary increment approval flow | ✅ Fixed | `SalaryIncrementReviewDialog` in `dashboard.py` |
| Full UI styling pass | ✅ Fixed | White sidebar, `#2563eb` accents, dropdown arrows, qtawesome icons |
| Language switching post-login | ❌ Not fixed | Architectural limitation — login screen only. Would require every page to call `t()` on `showEvent`. |

---

## Thesis Extension — Remaining Work

- Promotion rule management editor via UI (rules tab exists, full editor not yet built)
- Before/after diff view in audit log
- Yearly reporting summaries (PDF export)
- Improved input validation and error UX
- Email reminder for salary increment due dates
- Multi-language expansion (more languages, post-login translation)
