"""Config-switchable SQLAlchemy engine for the backend.

Defaults to an isolated SQLite database under ``.scratch`` and can point at
Postgres by setting ``MYHR_DATABASE_URL``. The ORM models are reused from the
existing desktop package ``src.database.models``; they are not duplicated.
"""

import json
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

_connect_args = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    sqlite_path = make_url(_settings.database_url).database
    if sqlite_path and sqlite_path != ":memory:":
        Path(sqlite_path).expanduser().resolve().parent.mkdir(
            parents=True, exist_ok=True
        )

engine = create_engine(_settings.database_url, echo=False, connect_args=_connect_args)


class BackendSession(Session):
    """Backend session with optional transaction-scoped RLS identity."""


SessionLocal = sessionmaker(
    bind=engine,
    class_=BackendSession,
    autoflush=False,
    autocommit=False,
)


@event.listens_for(BackendSession, "after_begin")
def _apply_rls_context(session, transaction, connection) -> None:
    claims = session.info.get("rls_claims")
    if not claims or connection.dialect.name != "postgresql":
        return
    connection.exec_driver_sql("SET LOCAL ROLE myhr_api")
    connection.execute(
        text("SELECT set_config('request.jwt.claims', :claims, true)"),
        {"claims": json.dumps(claims, separators=(",", ":"))},
    )


def get_session():
    """FastAPI dependency that yields a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_identity_session():
    """Yield a privileged session used only to map verified auth identities."""
    yield from get_session()
