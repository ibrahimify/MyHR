"""First-user profile linking tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scripts.link_supabase_user import link_user
from src.database.models import Base, Organization, SystemUser


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        database_session.add_all(
            [
                Organization(id=1, name="First", slug="first"),
                Organization(id=2, name="Second", slug="second"),
            ]
        )
        database_session.commit()
        yield database_session
    engine.dispose()


def test_link_user_is_idempotent_and_never_stores_a_web_password(session):
    auth_id = "11111111-1111-1111-1111-111111111111"
    first = link_user(
        session,
        auth_user_id=auth_id,
        email="Admin@Example.test",
        full_name="First Admin",
    )
    second = link_user(
        session,
        auth_user_id=auth_id,
        email="admin@example.test",
        full_name="Updated Admin",
    )

    assert first.id == second.id
    assert second.username == "admin@example.test"
    assert second.full_name == "Updated Admin"
    assert second.password_hash == "supabase-auth-only"
    assert session.query(SystemUser).count() == 1


def test_link_user_rejects_invalid_role_and_cross_tenant_reassignment(session):
    auth_id = "11111111-1111-1111-1111-111111111111"
    link_user(
        session,
        auth_user_id=auth_id,
        email="admin@example.test",
        full_name="First Admin",
    )

    with pytest.raises(ValueError, match="another organization"):
        link_user(
            session,
            auth_user_id=auth_id,
            email="admin@example.test",
            full_name="First Admin",
            organization_id=2,
        )
    with pytest.raises(ValueError, match="Role must"):
        link_user(
            session,
            auth_user_id="22222222-2222-2222-2222-222222222222",
            email="user@example.test",
            full_name="User",
            role="superadmin",
        )
