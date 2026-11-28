"""Smoke test for the health endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_plain_postgres_url_selects_psycopg_driver():
    settings = Settings(database_url="postgresql://user:pass@example.test/myhr")
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_default_database_is_isolated_from_desktop(monkeypatch):
    monkeypatch.delenv("MYHR_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    normalized = settings.database_url.replace("\\", "/")
    assert normalized.endswith("/.scratch/web-local.db")
    assert not normalized.endswith("/myhr.db")


def test_local_frontend_origin_is_allowed():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
