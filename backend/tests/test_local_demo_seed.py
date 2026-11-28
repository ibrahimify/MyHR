"""Safety and repeatability checks for the local demonstration seed command."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scripts.seed_local_demo import (
    DemoSeedError,
    REPOSITORY_DATABASE,
    seed_local_demo,
    sqlite_database_path,
)
from src.database.models import Employee, OrgUnit, SystemUser, Title


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_seed_refuses_non_sqlite_memory_and_repository_database():
    with pytest.raises(DemoSeedError, match="only be seeded into SQLite"):
        sqlite_database_path("postgresql://user:pass@example.test/myhr")
    with pytest.raises(DemoSeedError, match="file-backed SQLite"):
        sqlite_database_path("sqlite:///:memory:")
    with pytest.raises(DemoSeedError, match="repository myhr.db is protected"):
        sqlite_database_path(f"sqlite:///{REPOSITORY_DATABASE.as_posix()}")


def test_seed_requires_existing_alembic_schema(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'empty.db').as_posix()}"
    with pytest.raises(DemoSeedError, match="Apply the Alembic schema"):
        seed_local_demo(database_url)


def test_seed_is_idempotent_and_marks_actor_login_inactive(tmp_path, monkeypatch):
    database_path = tmp_path / "local-demo.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("MYHR_DATABASE_URL", database_url)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    first = seed_local_demo(database_url)
    second = seed_local_demo(database_url)

    assert first.titles == 2
    assert first.org_units == 2
    assert first.users == 1
    assert first.employees == 3
    assert second.titles == 0
    assert second.org_units == 0
    assert second.users == 0
    assert second.employees == 0

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.query(Title).filter(Title.name.like("DEMO-%")).count() == 2
        assert session.query(OrgUnit).filter(OrgUnit.name.like("Local Demo %")).count() == 2
        employees = session.query(Employee).filter(
            Employee.employee_id.like("DEMO-EMP-%")
        ).order_by(Employee.employee_id).all()
        assert len(employees) == 3
        assert employees[1].reports_to_id == employees[0].id
        assert employees[2].reports_to_id == employees[0].id
        actor = session.query(SystemUser).filter_by(username="local-demo-actor").one()
        assert actor.is_active is False
        assert actor.password_hash == "!local-demo-login-disabled"
    engine.dispose()
