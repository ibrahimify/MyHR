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
