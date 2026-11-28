# MyHR Web Port Handover

Engineering checkpoint for continuing the web port. It contains no credentials.

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
  `MYHR_DATABASE_URL` (defaults to an isolated `.scratch/web-local.db`; the
  desktop database is never selected implicitly).
- Database: Supabase Postgres. Project ref `wqtrnxljvpvudhdblsrf`.
- Multi-tenancy: option C, "tenant-ready". Add one `organization` table and an
  `organization_id` FK on 11 business tables, seed one default org, enforce with
  a tenant-scoping dependency and Supabase RLS. Single-org behavior for now.
- Roles: keep `admin` and `hr_officer`; reserve a new `superadmin` for the
  platform MASTER panel. Web auth via Supabase Auth; `SystemUser` becomes a
  role/profile table. Do NOT ship the desktop seed passwords to the cloud.
- UI fidelity: feature-identical to the desktop, but a clean modern web look
  (not a pixel copy of the Qt UI).
- Desktop: local SQLite, untouched. Cloud is optional for desktop, later.
- Landing page: product name "MyHR", no tagline, restrained minimalist design
  (Linear/Vercel/Resend style). Footer has the author name plus
  https://linkedin.com/in/ibrahimify and https://github.com/ibrahimify.

## Branch / commit / safety rules

- Integrate web work through short feature branches targeting `web`.
- Never touch `master`, `thesis`, `research`, or the tag `tdk-2026-submission`.
- Never force-push, reset --hard, or `git clean`.
- Commit messages are plain, imperative and specific to the change.
- `.gitignore` excludes local planning, temporary configuration and environment
  files. Keep those files and generated outputs out of the committed tree.
- The existing desktop test suite (332 tests plus 17 subtests) must stay green
  after every phase (`python -m pytest tests` from repo root). Record the result
  in the commit.
- Tag milestones: `web-v0.1` (done, scaffold), `web-v0.2` (on Supabase),
  `web-v1.0` (parity + landing page).

## Status so far

- Phase 0 (done): a local API contract maps every table, the 10 feature areas
  to REST endpoints, the auth model, SQLite coupling to fix and the tenancy-C
  foreign-key plan. It is the implementation map. If the ignored local copy is
  unavailable, regenerate it by reading `src/database/models.py`,
  `src/database/connection.py`, `src/services/*` and `src/ui/pages/*`.
- Phase 1 (done): branch `web` + tag `web-v0.1`, pushed. Monorepo scaffold:
  `backend/` FastAPI with `/health` and env-switchable engine, reusing
  `src.database` and `src.services` (no duplication); `frontend/` Next.js +
  Tailwind + Framer Motion placeholder; `.github/workflows/web-ci.yml` runs
  backend pytest + frontend build. Desktop suite now has 332 tests plus 17
  subtests passing.
- Phase 2 (hosted schema complete): the shared models now include the default organization,
  tenant FKs and scoped uniqueness; Alembic owns the web schema; reference IDs
  use atomic tenant-scoped counters. Migration and compatibility tests run on
  SQLite, and the migration compiles as PostgreSQL SQL. Applying it to a
  The migrations are applied to Supabase and 14 RLS policies passed a
  rollback-only cross-tenant probe. The hosted database is at Alembic head.
- Local employee milestone (implemented and verified): `EmployeeService`
  provides tenant-scoped list, detail, create and update operations with
  relationship validation, manager-cycle prevention, atomic reference IDs and
  audit entries. FastAPI exposes the service under `/api/employees`. The
  responsive Next.js directory supports search, status filters, details and
  create/edit forms. A guarded seed command creates isolated SQLite demo data.
  Backend tests, frontend lint/build and four reproducible browser tests pass.
  The browser suite covers the real create/edit workflow on a disposable
  database plus failure states, request races and mobile layout. Production
  identity is not implemented; the UI labels its current server-owned context
  as local development.
- Authentication milestone (implementation complete, onboarding pending): the
  Next.js client provides sign-in, session tracking and sign-out. FastAPI
  verifies ES256 Supabase JWTs, maps the subject to an active `SystemUser`, and
  reapplies a restricted `myhr_api` role plus tenant claims after every
  transaction. The first Auth user still needs to be created and linked before
  the hosted end-to-end workflow can be run.

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
- Remaining concurrency work: employee references now use atomic tenant
  counters. Apply the same service pattern to commendation and sanction
  references before exposing their write endpoints.
- Background jobs needed: anomaly-detection demo (sklearn, already out-of-process
  on desktop) and bulk import. Return a job id and poll; never run synchronously.
- Anomaly scores are human-review-only. The API must never wire them into any
  write/personnel path. (Project rule.)

## Tenancy C

employee, org_unit, title, promotion_rule, commendation, sanction,
promotion_history, salary_increment_history, performance_score, audit_log,
system_user. Seed one default `organization` row in the init/seed path and
backfill existing rows to it. Leave `commendation_employee` (junction)
unscoped. When tenancy is enabled, `username` is unique per org (not global),
and the ref/ID generators scope their counters per org.

## Supabase access

- Preferred: use the Supabase MCP server (project ref `wqtrnxljvpvudhdblsrf`),
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

## Next up

1. Create the first Supabase Auth administrator and link its UUID to an active
   `SystemUser` in the default organization.
2. Configure untracked backend and frontend environment files, then run the
   authenticated employee workflow against hosted Postgres.
3. Run the full regression suite and CI, then tag `web-v0.2` after the live
   authenticated workflow succeeds.

Then extend the shared-service pattern to organization units, titles,
commendations and sanctions before expanding the remaining feature pages.
Landing, desktop packaging, deployment, platform administration and final
parity verification follow after the authenticated boundary is proven.

## Security note

Keep credentials in environment variables or git-ignored `.env` files. Rotate
any credential that may have been exposed; never place secrets in source,
issues, pull requests or documentation.
