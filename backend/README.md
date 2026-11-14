# MyHR Backend

FastAPI backend for the MyHR web port. Phase 1 is engineering scaffolding only:
no business endpoints are implemented yet.

The backend reuses the existing desktop Python packages (`src/database`,
`src/services`) from the repository root rather than duplicating them.

## Layout

```
backend/
  app/
    __init__.py
    main.py         FastAPI app factory and /health endpoint
    config.py       Settings loaded from environment
    db.py           Config-switchable SQLAlchemy engine (SQLite by default)
  tests/
    test_health.py  Health endpoint test
  requirements.txt
  pytest.ini
```

## Database engine

The engine is config-switchable through `MYHR_DATABASE_URL`. When unset it
defaults to the existing desktop SQLite database (`myhr.db` at the repository
root), so local development matches the desktop app. Set
`MYHR_DATABASE_URL=postgresql+psycopg://...` to point at Postgres later.

## Local development

```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests

```
cd backend
pytest
```
