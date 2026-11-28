# MyHR Web Platform

[![Web CI](https://github.com/ibrahimify/MyHR/actions/workflows/web-ci.yml/badge.svg?branch=web)](https://github.com/ibrahimify/MyHR/actions/workflows/web-ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)

This is the `web` development branch of MyHR. It is extending the verified
PySide6 desktop application into a tenant-ready web platform without replacing
or weakening the existing desktop product.

The web platform uses a Next.js frontend, a FastAPI backend, shared SQLAlchemy
models and business services, and Supabase Postgres. The desktop application
continues to use local SQLite and remains independently runnable.

> **Current checkpoint:** the employee workflow and Supabase security boundary
> are implemented. The hosted schema is migrated, 14 tenant policies are active,
> FastAPI verifies Supabase access tokens, and the Next.js client has a sign-in
> flow. First-user onboarding and an authenticated end-to-end run remain. Resume from
> [Web Port Handover](docs/WEB_PORT_HANDOVER.md).

## Project status

| Area | Status | Evidence |
| --- | --- | --- |
| Desktop application | Working baseline | `python main.py` and the desktop test suite |
| FastAPI backend | Local employee workflow complete | Tenant-scoped employee API, validation, audit logging and tests |
| Next.js frontend | Local employee workflow complete | Responsive employee directory, details and create/edit forms |
| Tenant-ready schema | Deployed | Organization scope, tenant uniqueness and hosted PostgreSQL migration head verified |
| Database migrations | Verified | SQLite migration tests, PostgreSQL rendering and hosted migration completed |
| Supabase deployment | Database connected | Hosted schema and rollback-only isolation probe verified |
| Web authentication and RLS | Implemented, onboarding pending | JWT verification, profile mapping, login UI and 14 RLS policies |
| Production deployment | Not started | Vercel and backend hosting are deliberately deferred |

No hosted web application or production authentication is claimed at this stage.

## Architecture

```text
                         MyHR monorepo

  Desktop client                               Web client
  PySide6                                      Next.js + TypeScript
      |                                              |
      |                                              v
      |                                        FastAPI backend
      |                                              |
      +---------- shared models and services --------+
                         |
              +----------+----------+
              |                     |
          SQLite local         Supabase Postgres
          desktop data         tenant-ready web data
```

The web backend imports the existing `src/database` and `src/services`
packages. Business rules are not being copied into a second implementation.
Desktop UI code under `src/ui` remains separate from the Next.js frontend.

## Repository layout

```text
backend/                  FastAPI application, Alembic and backend tests
frontend/                 Next.js App Router application
src/database/             Shared SQLAlchemy models and desktop database logic
src/services/             Shared policy, reporting and research services
src/ui/                   Existing PySide6 desktop interface
tests/                    Desktop and shared-service regression tests
docs/WEB_PORT_HANDOVER.md Current engineering checkpoint and roadmap
```

## Quick start

### Desktop application

```powershell
python -m pip install -r requirements.txt
python main.py
```

The local demonstration accounts are only for the offline SQLite application:

- Admin: `admin` / `admin123`
- HR officer: `hr_officer` / `hr123`

These credentials must never be deployed to the web platform.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MYHR_DATABASE_URL = "sqlite:///../.scratch/web-local.db"
$env:MYHR_AUTH_MODE = "local"
alembic upgrade head
python -m scripts.seed_local_demo --database-url sqlite:///../.scratch/web-local.db
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health`. The isolated `.scratch/web-local.db`
database keeps web migration work away from the desktop application's data.
Do not run Alembic against the repository `myhr.db`.

For Postgres, create an untracked `backend/.env` file:

```dotenv
MYHR_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
MYHR_AUTH_MODE=supabase
MYHR_SUPABASE_URL=https://your-project.supabase.co
```

Never commit that file or paste credentials into issues or pull requests.

### Frontend

```powershell
cd frontend
npm ci
$env:NEXT_PUBLIC_AUTH_MODE = "local"
npm run dev
```

Copy `frontend/.env.example` to an untracked `.env.local` and set the project
URL and publishable key. Local mode remains available for disposable browser
tests; hosted mode requires an Auth user linked to an active MyHR profile.

## Verification

Run checks from their documented working directories:

```powershell
# Repository root: desktop and shared services
python -m pytest tests -q

# Backend
cd backend
python -m pytest -q

# Frontend
cd ..\frontend
npm run build
npm run test:e2e
```

Verified on the local employee workflow branch:

- Desktop and shared suite: 332 tests passed, plus 17 subtests.
- Backend suite: 34 tests passed.
- Frontend lint and production build: passed.
- Browser suite: 4 tests passed, covering list, detail, search, filtering,
  create/update, loading, empty and failure states, request races and mobile
  layout against a disposable migrated database.
- GitHub Web CI: pending the feature-branch push.

## Tenancy and security

- Every tenant-owned business table has an `organization_id` foreign key.
- Human-readable employee, commendation and sanction references use atomic,
  organization-scoped counters.
- Usernames and configurable titles are unique within an organization.
- `superadmin` is reserved for the future platform administration surface.
- Supabase Auth owns web identity; desktop SHA-256 seed credentials are not
  valid web authentication.
- FastAPI resolves organization and role from a server-owned profile after JWT
  verification. Client-supplied tenant identifiers are ignored.
- Tenant transactions assume a restricted PostgreSQL role. Fourteen RLS
  policies were verified with a rollback-only cross-tenant probe.
- Anomaly results remain advisory and cannot trigger personnel changes.
- The research holdout remains locked and is outside the web-port workflow.

See [SECURITY.md](SECURITY.md) for reporting guidance. No open-source license
has been selected; see [Licensing and IP](docs/LICENSING_AND_IP.md).

## Roadmap

1. Create and link the first Supabase Auth administrator, then run the hosted
   employee workflow end to end.
2. Extend shared services and API endpoints to organization units, titles,
   commendations and sanctions.
3. Add the remaining authenticated feature pages.
4. Add the public product page and deployment configuration.
5. Package the desktop application as a Windows installer.
6. Complete parity, security and accessibility verification.

Milestones:

- `web-v0.1`: monorepo and CI scaffold, complete.
- `web-v0.2`: verified Supabase schema and security boundary, pending the first
  authenticated end-to-end run.
- `web-v1.0`: feature parity, public entry point and deployable releases.

## Branches

| Branch | Purpose |
| --- | --- |
| `master` | Preserved Project Laboratory submission |
| `thesis` | Verified standalone desktop application |
| `research` | TDK research implementation and submitted evidence |
| `web` | Web platform development, this branch |

The research manuscript and evidence remain available on `research` and at the
immutable `tdk-2026-submission` tag. Web work must not rewrite those records.

## Contribution boundaries

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change. Keep commits
small, preserve the desktop test suite, add migration tests for schema changes,
and never commit environment files, local planning files, generated databases
or credentials.

MyHR is an academic software project by Muhammad Ibrahim Shoeb at the Budapest
University of Technology and Economics.
