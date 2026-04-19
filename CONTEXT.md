**Claude Code** is better for this job — it runs in your terminal, reads all your actual files directly, fixes code and runs it immediately, and keeps full context of your project. 

That said, here's the full project summary:

---

## MyHR — Full Project Summary

### Project Requirements (Semester 1 — Project Lab)

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

### Project Requirements (Semester 2 — Thesis Extension)

- Configurable rule management via UI
- Advanced audit history with before/after diff
- Yearly reporting and PDF export
- Improved input validation and error handling
- Email reminder for salary increments
- Dark mode + full UI polish
- Multi-language expansion

---

### What We Learned from Professor Meetings

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

### Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Promotion months remaining | Calculated live, never stored | Avoids stale data, fully auditable |
| Annual salary increment | Manual with dashboard prompt | Simpler for offline desktop app |
| Language | Per session | No DB overhead |
| Employee access | None | Per professor requirement |
| Commendation query | Two-step subquery | SQLite JOIN reliability |

---

### What We Built

**Tech stack:** Python 3.12 + PySide6 + SQLite + SQLAlchemy 2.0

**10 DB tables:** `system_user`, `org_unit`, `employee`, `title`, `promotion_rule`, `promotion_history`, `commendation`, `commendation_employee`, `sanction`, `salary_increment_history`, `audit_log`

**Pages built:**
- Login — language switcher (EN/HU/AR), RTL support for Arabic
- Dashboard — live stats, salary increment alert banner, recent activity
- Employees — list with search/filter, add form with degree→level auto-assign, profile with live promotion race status
- Org Hierarchy — unlimited depth tree, add/edit/delete units with dependency checks
- Promotions — live race tracker, approve promotion, history, configurable base months
- Commendations — single + team award, 3 categories, max 3 cap enforced, unique COM- IDs
- Sanctions — 1–12 month delay, unique SAN- IDs, active/resolved tracking
- Audit Log — immutable, searchable, filterable, hover tooltips
- Import Data — CSV upload, validate, preview, import with template download
- Settings — salary ranges, annual increment config, password change, DB backup, CSV export

**Access control:**
- Admin: full access to all pages
- HR Officer: everything except Settings

**Known issues to fix:**
- UI needs full styling pass (white text on white backgrounds in some areas)
- Promotion tracker "View" button not wired to employee profile yet
- Annual salary increment approval flow on dashboard not fully wired
- Language switching doesn't translate all labels after login (only login screen translates)

---

For the next session — whether Claude Code or here — share the full `src/` folder and this summary and they'll have everything needed to fix the UI and remaining logic gaps.