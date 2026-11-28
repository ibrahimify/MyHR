"""Authentication boundary and profile-mapping tests."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.context import (
    _jwks_clients,
    get_authorized_session,
    get_organization_context,
    verify_access_token,
)
from app.db import get_identity_session
from app.main import create_app
from src.database.models import Base, Organization, SystemUser


@pytest.fixture()
def auth_api(monkeypatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv("MYHR_AUTH_MODE", "supabase")
    monkeypatch.setenv("MYHR_SUPABASE_URL", "https://example.supabase.co")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add_all(
            [
                Organization(id=1, name="First", slug="first"),
                Organization(id=2, name="Second", slug="second"),
                SystemUser(
                    id=1,
                    organization_id=1,
                    auth_user_id="11111111-1111-1111-1111-111111111111",
                    username="admin@example.test",
                    password_hash="supabase-auth",
                    role="admin",
                    full_name="First Admin",
                    is_active=True,
                ),
                SystemUser(
                    id=2,
                    organization_id=2,
                    auth_user_id="22222222-2222-2222-2222-222222222222",
                    username="disabled@example.test",
                    password_hash="supabase-auth",
                    role="admin",
                    full_name="Disabled Admin",
                    is_active=False,
                ),
            ]
        )
        session.commit()

    app = create_app()

    def session_override():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_identity_session] = session_override
    app.dependency_overrides[get_authorized_session] = session_override
    with TestClient(app) as client:
        yield client, session_factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_supabase_mode_requires_bearer_token(auth_api):
    client, _ = auth_api

    response = client.get("/api/employees")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}


def test_verified_subject_resolves_server_owned_tenant(auth_api):
    client, _ = auth_api
    client.app.dependency_overrides[verify_access_token] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111"
    }

    response = client.get(
        "/api/employees",
        headers={"X-Organization-ID": "2"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.parametrize(
    "subject",
    [
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    ],
)
def test_inactive_or_unmapped_subject_is_forbidden(auth_api, subject):
    client, _ = auth_api
    client.app.dependency_overrides[verify_access_token] = lambda: {"sub": subject}

    response = client.get("/api/employees")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "This account is not assigned to an active MyHR profile."
    }


def test_local_mode_keeps_disposable_development_context(monkeypatch):
    monkeypatch.setenv("MYHR_AUTH_MODE", "local")
    context = get_organization_context(None, None)
    assert context.organization_id == 1
    assert context.role == "admin"


def test_access_token_signature_issuer_and_audience_are_verified(monkeypatch):
    monkeypatch.setenv("MYHR_AUTH_MODE", "supabase")
    monkeypatch.setenv("MYHR_SUPABASE_URL", "https://example.supabase.co")
    private_key = ec.generate_private_key(ec.SECP256R1())

    class SigningKey:
        key = private_key.public_key()

    class JwksClient:
        def get_signing_key_from_jwt(self, token):
            return SigningKey()

    jwks_url = "https://example.supabase.co/auth/v1/.well-known/jwks.json"
    monkeypatch.setitem(_jwks_clients, jwks_url, JwksClient())
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(claims, private_key, algorithm="ES256")

    verified = verify_access_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert verified["sub"] == claims["sub"]

    wrong_issuer = jwt.encode(
        {**claims, "iss": "https://other.example/auth/v1"},
        private_key,
        algorithm="ES256",
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=wrong_issuer)
        )
    assert exc_info.value.status_code == 401
