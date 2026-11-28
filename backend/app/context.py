"""Verified identity, organization context, and tenant-restricted sessions."""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

import app._paths  # noqa: F401
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_identity_session
from src.database.connection import DEFAULT_ORGANIZATION_ID
from src.database.models import SystemUser


@dataclass(frozen=True)
class OrganizationContext:
    organization_id: int
    user_id: int | None = None
    role: Literal["admin", "hr_officer"] = "admin"
    auth_user_id: str | None = None


_bearer = HTTPBearer(auto_error=False)
_jwks_clients: dict[str, PyJWKClient] = {}


def _unauthorized(detail: str = "Authentication is required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any] | None:
    """Verify a Supabase access token with the project's public signing keys."""
    settings = get_settings()
    if settings.auth_mode == "local":
        return None
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    jwks_url = f"{issuer}/.well-known/jwks.json"
    client = _jwks_clients.setdefault(jwks_url, PyJWKClient(jwks_url, cache_keys=True))
    try:
        signing_key = client.get_signing_key_from_jwt(credentials.credentials)
        return jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("The access token is invalid or expired.") from exc


def get_organization_context(
    claims: Annotated[dict[str, Any] | None, Depends(verify_access_token)],
    session: Annotated[Session, Depends(get_identity_session)],
) -> OrganizationContext:
    """Resolve tenant and role from a verified identity and server-owned profile."""
    if claims is None:
        return OrganizationContext(organization_id=DEFAULT_ORGANIZATION_ID, role="admin")

    profile = session.scalar(
        select(SystemUser).where(
            SystemUser.auth_user_id == str(claims["sub"]),
            SystemUser.is_active.is_(True),
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not assigned to an active MyHR profile.",
        )
    if profile.role not in {"admin", "hr_officer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account cannot access an organization workspace.",
        )
    return OrganizationContext(
        organization_id=profile.organization_id,
        user_id=profile.id,
        role=profile.role,
        auth_user_id=profile.auth_user_id,
    )


def get_authorized_session(
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
):
    """Yield a session that reapplies tenant RLS identity after every commit."""
    session = SessionLocal()
    if get_settings().auth_mode == "supabase":
        session.info["rls_claims"] = {
            "sub": context.auth_user_id,
            "organization_id": context.organization_id,
            "app_role": context.role,
        }
    try:
        yield session
    finally:
        session.close()
