"""Config-switchable SQLAlchemy engine for the backend.

Defaults to the existing desktop SQLite database for local development and
can point at Postgres by setting ``MYHR_DATABASE_URL``. The ORM models are
reused from the existing desktop package ``src.database.models``; they are
not duplicated here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

_settings = get_settings()

_connect_args = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(_settings.database_url, echo=False, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """FastAPI dependency that yields a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
