"""Link an existing Supabase Auth user to a MyHR organization profile."""

import argparse
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from src.database.models import Organization, SystemUser


def link_user(
    session: Session,
    *,
    auth_user_id: str,
    email: str,
    full_name: str,
    role: str = "admin",
    organization_id: int = 1,
) -> SystemUser:
    normalized_id = str(UUID(auth_user_id))
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()
    if role not in {"admin", "hr_officer"}:
        raise ValueError("Role must be admin or hr_officer.")
    if not normalized_email or not normalized_name:
        raise ValueError("Email and full name are required.")
    if session.get(Organization, organization_id) is None:
        raise ValueError("Organization does not exist.")

    existing = session.scalar(
        select(SystemUser).where(SystemUser.auth_user_id == normalized_id)
    )
    if existing is None:
        existing = session.scalar(
            select(SystemUser).where(
                SystemUser.organization_id == organization_id,
                SystemUser.username == normalized_email,
            )
        )
    if existing is None:
        existing = SystemUser(
            organization_id=organization_id,
            username=normalized_email,
            password_hash="supabase-auth-only",
            role=role,
            full_name=normalized_name,
            is_active=True,
        )
        session.add(existing)
    elif existing.organization_id != organization_id:
        raise ValueError("The existing profile belongs to another organization.")

    existing.auth_user_id = normalized_id
    existing.username = normalized_email
    existing.full_name = normalized_name
    existing.role = role
    existing.is_active = True
    session.commit()
    session.refresh(existing)
    return existing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-user-id", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", choices=("admin", "hr_officer"), default="admin")
    parser.add_argument("--organization-id", type=int, default=1)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.database_url.startswith("postgresql+"):
        parser.error("This command requires the configured Supabase Postgres database.")
    with SessionLocal() as session:
        auth_email = session.execute(
            text("SELECT email FROM auth.users WHERE id = CAST(:id AS uuid)"),
            {"id": str(UUID(args.auth_user_id))},
        ).scalar_one_or_none()
        if auth_email is None:
            parser.error("The Supabase Auth user does not exist.")
        if auth_email.lower() != args.email.strip().lower():
            parser.error("The supplied email does not match the Auth user.")
        profile = link_user(
            session,
            auth_user_id=args.auth_user_id,
            email=args.email,
            full_name=args.full_name,
            role=args.role,
            organization_id=args.organization_id,
        )
    print(f"Linked profile {profile.id} to organization {profile.organization_id}.")


if __name__ == "__main__":
    main()
