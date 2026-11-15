# MyHR Backend

FastAPI backend for the MyHR web platform. The health endpoint, configurable
database engine, tenant-ready SQLAlchemy schema and initial Alembic migration
are implemented. Business endpoints and web authentication are not yet built.

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
configuration points to the existing desktop SQLite database at the repository
root. That fallback supports shared-model inspection, but it is not a safe
migration target.

For local migration work, use a separate ignored database:

```powershell
cd backend
$env:MYHR_DATABASE_URL = "sqlite:///../.scratch/web-local.db"
alembic upgrade head
```

Never run the web migration against the repository `myhr.db`. For Supabase,
set the variable in an untracked `backend/.env` file using a Postgres URL:

```dotenv
MYHR_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
```

Do not commit `.env` files, passwords, access tokens or service-role keys.

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
