# MyHR Backend

FastAPI backend for the MyHR web platform. The health endpoint, configurable
database engine, tenant-ready schema, employee endpoints, Supabase JWT
verification and transaction-scoped RLS context are implemented.

The backend reuses the existing desktop Python packages (`src/database`,
`src/services`) from the repository root rather than duplicating them.

## Layout

```
backend/
  app/
    __init__.py
    main.py         FastAPI app factory and /health endpoint
    config.py       Settings loaded from environment
    db.py           Configurable SQLAlchemy engine
  alembic/          Versioned database migrations
  alembic.ini       Alembic configuration
  tests/            Health, configuration and migration tests
  requirements.txt
  pytest.ini
```

## Database engine

The engine is selected through `MYHR_DATABASE_URL`. When unset, application
configuration points to an isolated SQLite database under `.scratch`. It never
selects the desktop database implicitly.

For local migration work, use a separate ignored database:

```powershell
cd backend
$env:MYHR_DATABASE_URL = "sqlite:///../.scratch/web-local.db"
$env:MYHR_AUTH_MODE = "local"
alembic upgrade head
```

Never run the web migration against the repository `myhr.db`. For Supabase,
set the variable in an untracked `backend/.env` file using a Postgres URL:

```dotenv
MYHR_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
MYHR_AUTH_MODE=supabase
MYHR_SUPABASE_URL=https://your-project.supabase.co
```

Do not commit `.env` files, passwords, access tokens or service-role keys.

After creating a user in Supabase Auth, link it to the default organization:

```powershell
python -m scripts.link_supabase_user `
  --auth-user-id USER_UUID `
  --email user@example.com `
  --full-name "Organization Administrator"
```

The command validates the Auth user in Supabase and stores only its UUID,
email, display name, organization and application role. It never handles the
user's Supabase password.

## Local development

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health`.

## Tests

```powershell
cd backend
python -m pytest -q
```

See the repository [README](../README.md) and
[Web Port Handover](../docs/WEB_PORT_HANDOVER.md) for the verified checkpoint,
security boundaries and next milestone.
