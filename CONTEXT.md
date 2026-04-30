# MyHR — Project Context for Claude

**Read this file before making ANY change.**

Also read: [ui_redesign.md](ui_redesign.md)

---

## Quick Start

```bash
py -3.12 main.py
```

**Tech Stack:**
- Python 3.12 + PySide6 6.11.0
- SQLite + SQLAlchemy 2.0.49
- qtawesome 1.4.2

---

## Project Overview

**MyHR** is a professional, offline desktop HR management system.

**Type:** Admin + HR Officer only (employees are data only, never login)

**Core Features:**
- Employee CRUD + Organizational hierarchy
- Promotion race tracking (live calculation)
- Commendations + Sanctions
- Salary increment review
- Audit logging
- CSV import/export
- Production-quality UI

---

## User Roles & Access

| Role | Access |
|------|--------|
| **Admin** | All pages: Dashboard, Employees, Organization Hierarchy, Promotions, Commendations, Sanctions, Audit Log, Import Data, Settings |
| **HR Officer** | Operational pages only (no Settings) |
| **Employees** | Data subjects only (NO login) |

**Default Credentials:**
- Admin: `admin` / `admin123`
- HR Officer: `hr_officer` / `hr123`

---

## Core Business Logic

### Employee IDs
- Format: `EMP-XXXX` (unique)

### Degree → Starting Level
- BSc → Level 7
- MSc → Level 6
- PhD → Level 5

### Promotion System (🔴 CRITICAL)

**Key Rule:** Promotion is a **LIVE CALCULATION**. Never store "months remaining" or computed status.

**Promotion depends on:**
- Base track duration (months)
- Time in current level
- Commendations (reduce time)
- Sanctions (delay time)
- Promotion history

**Metaphor:** Race track where commendations accelerate, sanctions delay.

**⚠️ IMPORTANT:** All pages (Dashboard, Promotions page) **must use the SAME promotion logic**. If they differ → it's a bug.

### Commendations

**ID Format:** `COM-XXXX`

**Categories & Impact:**
- Category 1 → -1 month
- Category 2 → -3 months
- Category 3 → -6 months

**Rules:**
- Max 3 commendations per employee per role/level
- **Single award:** Show error if maxed: `"This employee has reached the maximum 3 commendations for this role."`
- **Team award:** Must NOT block entire team if one employee is maxed. Instead:
  - Skip capped employees
  - Award others
  - Show warning to user

### Sanctions

**ID Format:** `SAN-XXXX`

**Rules:**
- Delay promotion by 1–12 months
- Store: issue date + resolved date
- Can be active or resolved
- **Show resolved date everywhere** (employee profile, audit log, etc.)

### Salary Increment

- **Separate from promotion** (not linked)
- Manual review/approval flow via `SalaryIncrementReviewDialog`
- After approval: Dashboard must refresh or rebuild

---

## Database Schema

**Current tables:**
```
system_user
org_unit
employee
title
promotion_rule
promotion_history
commendation
commendation_employee
sanction
salary_increment_history
audit_log
```

**If schema changes:** Update this file before making large changes.

---

## Current Status

### ✅ Working Features
- Employee edit + View/Edit buttons
- Team commendation skip logic (doesn't block team)
- Sanction resolved date display
- Dashboard rebuilds on navigation
- Promotion View → navigate to employee profile

### ❌ Active Issues

| Issue | Required Fix |
|-------|--------------|
| **Audit Log** | Some actions show raw values (e.g., "1") → must be human-readable |
| **Dashboard** | "Upcoming Eligible Promotions" uses different logic than Promotions page → must use same calculation |
| **Commendation UX** | Error message for maxed employee not consistent |
| **CSV Import** | Employees missing org assignment → weak hierarchy logic |
| **Organization Design** | Only uses position text; real systems need dept, position, reporting structure |
| **Language** | Only switches at login, not globally |
| **Dialog Styling** | Some dialogs unreadable (white on white) |
| **Currency Input** | Must auto-uppercase and max 3 characters |
| **Employee Delete** | Missing delete action + confirmation dialog |
| **Navigation** | Back buttons need consistent breadcrumb style |

---

## Engineering Rules

### Before Writing Code

1. **Check if logic exists** → Don't duplicate
2. **Verify feature wiring** → Is it actually connected?
3. **Identify root cause** → Not just symptoms
4. **Reuse services/helpers** → Don't reinvent
5. **Don't invent business rules silently** → Ask if unclear

### Anti-Patterns (DO NOT DO)

❌ Rewrite promotion logic in multiple files
❌ Hardcode UI values instead of using real data
❌ Patch UI without fixing underlying logic
❌ Make silent assumptions about business rules
❌ Ignore existing functions/services
❌ Store computed values in database

### When to Stop & Ask

If something feels:
- Inconsistent
- Hacky
- Unrealistic in real HR systems

→ STOP and ask before proceeding.

---

## Reference Files

- **Database:** `src/database/models.py` (SQLAlchemy schema)
- **UI Pages:** `src/ui/pages/` (all page implementations)
- **Styles:** `src/ui/styles.py` (shared styling)
- **Main Window:** `src/ui/main_window.py` (page lifecycle)
- **UI Design Rules:** Read `ui_redesign.md` before UI changes


### 🔴 Promotion Logic Location (Single Source of Truth)

Promotion calculation MUST be implemented in ONE place only.

Example:
- `services/promotion_service.py` or equivalent

All pages must call this function:
- Dashboard
- Promotions page
- Employee profile

❌ DO NOT duplicate logic in UI files
❌ DO NOT calculate separately per page

## Data Integrity Rules

- Every employee MUST belong to an organization unit
- Every employee MUST have a valid level based on degree
- Promotion levels now continue beyond director: L7, L6, L5, L4, L3, L2 Board Member, L1 CEO / Executive.
- Admin can manually change an employee's current level/role in Employee Edit when real-world promotion paths do not follow only the default race track.
- Promotion must always be:
  - from lower level → higher level
- Commendations and sanctions must always be linked to an existing employee
- Deleting entities must not break relationships (use checks or constraints)

## Audit Log Rules

- Every critical action must be logged:
  - Employee create/edit/delete
  - Commendations issued
  - Sanctions issued/resolved
  - Promotions approved
- Logs must be human-readable (no numeric codes)
- Logs are immutable (never edited or deleted)

## Consistency Rule

If two pages show the same concept (e.g., promotions):

→ They MUST use the same data source and logic

If they differ:
→ It is ALWAYS a bug

## When Refactoring

- Prefer moving logic into services layer
- Keep UI thin (UI = display + interaction only)
- Business logic must NOT live inside UI files

## Latest UI/Wiring Notes

- Company name/subtitle are stored in `QSettings` via `src/core/app_settings.py`.
- Login and sidebar read company name/subtitle from those settings.
- Settings salary cards must stay white/subtle; no bright colored card backgrounds.
- Global stylesheet hides ugly spinbox arrow buttons and styles combo popups/calendar widgets.
- Organization hierarchy is now a Figma-style card tree using qtawesome icons and inline add/edit/delete actions.
- Login screen was rebuilt to match the Figma card layout: large centered logo, title/subtitle, language selector below, integrated icon inputs, and clean role indicators.
- Login translation refresh owns every visible login label, including Admin/HR Officer role indicators, so switching Arabic/English/Hungarian no longer leaves stale role text.
- Login preserves the current session language when returning after logout; Arabic returns to the Arabic selector and RTL layout, English/Hungarian return to LTR.
