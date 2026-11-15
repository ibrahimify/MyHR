# MyHR Web Port — Handover

Working notes for continuing the web port. Read this, then continue from "Next up".
This file is safe to commit (no secrets). Delete it when the web port is done.

## Goal

Add a web version of the existing MyHR desktop app (PySide6 + SQLite) without
touching the desktop. End deliverables:

1. A live web app URL (Vercel) that works like the desktop app.
2. A downloadable Windows setup.exe for the desktop app.
3. A minimalist public landing page offering both ("Use web version" /
   "Download for Windows").
4. A platform (MASTER) admin panel for managing organizations.

Architecture (Path A): one FastAPI backend reuses the existing Python
`src/services` and `src/database` layers; a Next.js frontend talks to it; the
PySide6 desktop stays as-is on local SQLite.

## Decisions (locked)

- Repo layout: monorepo on branch `web`, with `backend/` (FastAPI) and
  `frontend/` (Next.js) alongside the existing `src/` desktop code.
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + Framer Motion.
  Follow the Google style guide for frontend source.
- Backend: FastAPI + SQLAlchemy, engine switched by env var
  `MYHR_DATABASE_URL` (defaults to the existing SQLite for desktop/local).
- Database: Supabase Postgres. Project ref `cqyrkbpuaclhrphpezka`.
- Multi-tenancy: option C, "tenant-ready". Add one `organization` table and an
  `organization_id` FK on 11 business tables, seed one default org, enforce with
  a tenant-scoping dependency and Supabase RLS. Single-org behavior for now.
- Roles: keep `admin` and `hr_officer`; reserve a new `superadmin` for the
  platform MASTER panel. Web auth via Supabase Auth; `SystemUser` becomes a
  role/profile table. Do NOT ship the desktop seed passwords to the cloud.
- UI fidelity: feature-identical to the desktop, but a clean modern web look
  (not a pixel copy of the Qt UI).
- Desktop: local SQLite, untouched. Cloud is optional for desktop, later.
- Landing page: product name "MyHR", no tagline, brutally minimalist
  (Linear/Vercel/Resend style). Footer has the author name plus
  https://linkedin.com/in/ibrahimify and https://github.com/ibrahimify.

## Branch / commit / safety rules

- All web work on branch `web` (already created off `research`).
- Never touch `master`, `thesis`, `research`, or the tag `tdk-2026-submission`.
- Never force-push, reset --hard, or `git clean`.
- Commit messages: plain, imperative, no em dashes, no emojis, no AI phrasing,
  no words like "comprehensive"/"robust", nothing that reveals AI authorship.
- `.gitignore` already excludes `.agents/`, `.scratch/`, `*.plan.md`,
  `.kiro/settings/mcp.json`, `.env`, `.env.*`. Keep it that way. No planning or
  AI-authored scratch files in the committed tree.
- The existing desktop test suite (329 tests) must stay green after every phase
  (`python -m pytest tests` from repo root). Record the result in the commit.
- Tag milestones: `web-v0.1` (done, scaffold), `web-v0.2` (on Supabase),
  `web-v1.0` (parity + landing page).

## Status so far

- Phase 0 (done): read-only API contract written to
  `.agents/tasks/web-port-api-contract.md` (git-ignored). It maps every table,
  the 10 feature areas to REST endpoints, the auth model, SQLite coupling to
  fix, and the tenancy-C FK plan. READ THIS FIRST — it is the implementation
  map. (If missing because `.agents/` was cleaned, regenerate by re-reading
  `src/database/models.py`, `src/database/connection.py`, `src/services/*`, and
  `src/ui/pages/*`.)
- Phase 1 (done): branch `web` + tag `web-v0.1`, pushed. Monorepo scaffold:
  `backend/` FastAPI with `/health` and env-switchable engine, reusing
  `src.database` and `src.services` (no duplication); `frontend/` Next.js +
  Tailwind + Framer Motion placeholder; `.github/workflows/web-ci.yml` runs
  backend pytest + frontend build. Desktop suite still 329 passing.
- Phase 2 (in progress): the shared models now include the default organization,
  tenant FKs and scoped uniqueness; Alembic owns the web schema; reference IDs
  use atomic tenant-scoped counters. Migration and compatibility tests run on
  SQLite, and the migration compiles as PostgreSQL SQL. Applying it to a
  Supabase database branch and adding auth-backed RLS remain pending because no
  Supabase token or database URL is configured locally.

## Key facts from the API contract (summary)

- 12 tables, integer autoincrement PKs, named enums (Postgres-friendly).
- Pure/reusable now: `src/services/promotion_policy.py`,
  `src/services/reporting_service.py`, and the read/compute helpers in
  `connection.py` (promotion race, scoring, evidence).
- Biggest job: CRUD for employees/org-units/commendations/sanctions/titles/users
  lives inside the Qt pages, not in a reusable layer. Extract it into a shared
  service module both the API and desktop can call. Keep `log_action` as the
  single audit entry behind every mutating endpoint; preserve the existing
  audit-action vocabulary.
- Auth today: two roles, unsalted SHA-256, seed accounts admin/admin123 and
  hr_officer/hr123. Only gate: settings is admin-only. For web, use Supabase
  Auth and a salted KDF; never ship those seed passwords to the cloud.
- SQLite coupling to replace for Postgres: engine URL, PRAGMA-based migrations
  (use Alembic instead), and the settings file-copy backup + integrity check
  (drop/replace; Supabase handles backups).
- Concurrency bug to fix: ID generators (EMP-XXXX, COM-, SAN-) use max(id)+1 and
  per-day row counts — racy under a multi-worker web server. Use DB sequences or
  transactional retries.
- Background jobs needed: anomaly-detection demo (sklearn, already out-of-process
  on desktop) and bulk import. Return a job id and poll; never run synchronously.
- Anomaly scores are human-review-only. The API must never wire them into any
  write/personnel path. (Project rule.)

## Tenancy C — add organization_id FK to these 11 tables

employee, org_unit, title, promotion_rule, commendation, sanction,
promotion_history, salary_increment_history, performance_score, audit_log,
system_user. Seed one default `organization` row in the init/seed path and
backfill existing rows to it. Leave `commendation_employee` (junction)
unscoped. When tenancy is enabled, `username` is unique per org (not global),
and the ref/ID generators scope their counters per org.

## Supabase access (for the new agent)

- Preferred: use the Supabase MCP server (project ref `cqyrkbpuaclhrphpezka`),
  so no password is in code. The hosted/npx server needs a
  `SUPABASE_ACCESS_TOKEN` env var; create a token in Supabase under
  Account -> Access Tokens with Database = Read-write, Migrations = Read-write,
  everything else Read. Put the token in an env var, never in a committed file.
  MCP tools include apply_migration, execute_sql, list_tables, list_migrations,
  list_branches, get_project_url, get_advisors.
- Alternative: a Postgres connection string from Supabase
  (Project Settings -> Database -> Connection string, Session pooler), placed in
  `backend/.env` as `MYHR_DATABASE_URL` (that file is git-ignored).
- Recommended workflow: build and test migrations on a Supabase DATABASE BRANCH
  first, review, then merge to production. Do not run untested DDL against the
  production database.

## Next up (Phase 2 — database to Supabase)

1. Apply the tested Alembic migration to a Supabase database branch.
2. Add auth-backed RLS policies after the Supabase user-to-organization profile
   mapping is available; do not trust client-supplied organization IDs.
3. Point the backend at Supabase via `MYHR_DATABASE_URL` / MCP; confirm models
   create and services run on Postgres. Prefer a DB branch first.
4. Run the PostgreSQL integration checks, keep the desktop suite green, and tag
   `web-v0.2` only after the live branch verification succeeds.

Then: Phase 3 backend endpoints (+ extract CRUD into services), Phase 4 frontend
core, Phase 5 the 10 feature pages, Phase 6 landing page, Phase 7 Windows
installer (PyInstaller), Phase 8 deploy (backend to Render free, frontend to
Vercel), Phase 8.5 MASTER admin panel, Phase 9 parity check + polish, tag
`web-v1.0`.

## Security note

A Supabase access token was shared in an earlier chat and must be regenerated
after Phase 2. Do not paste tokens into chat or commit them. Secrets live only
in env vars or git-ignored `.env` files.
