"""Seed repeatable demonstration records into a disposable local SQLite database."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.database.models import Employee, Organization, OrgUnit, SystemUser, Title  # noqa: E402


REPOSITORY_DATABASE = (REPO_ROOT / "myhr.db").resolve()
REQUIRED_TABLES = {
    "alembic_version",
    "organization",
    "org_unit",
    "title",
    "employee",
    "system_user",
}


class DemoSeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedResult:
    titles: int = 0
    org_units: int = 0
    users: int = 0
    employees: int = 0


def sqlite_database_path(database_url: str) -> Path:
    try:
        url = make_url(database_url)
    except Exception as exc:
        raise DemoSeedError("A valid SQLAlchemy database URL is required.") from exc
    if url.get_backend_name() != "sqlite":
        raise DemoSeedError("Local demonstration data can only be seeded into SQLite.")
    if not url.database or url.database == ":memory:" or url.database.startswith("file:"):
        raise DemoSeedError("A file-backed SQLite database is required.")
    database_path = Path(url.database).expanduser().resolve()
    if database_path == REPOSITORY_DATABASE:
        raise DemoSeedError("The repository myhr.db is protected and cannot be seeded.")
    return database_path


def seed_local_demo(database_url: str, organization_id: int = 1) -> SeedResult:
    sqlite_database_path(database_url)
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise DemoSeedError(
                "Apply the Alembic schema before seeding. Missing tables: " + ", ".join(missing)
            )
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if not revision:
            raise DemoSeedError("Apply the Alembic schema before seeding. No migration revision was found.")
        session_factory = sessionmaker(bind=engine)
        with session_factory() as session, session.begin():
            return _seed(session, organization_id)
    finally:
        engine.dispose()


def _seed(session: Session, organization_id: int) -> SeedResult:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise DemoSeedError(f"Organization {organization_id} does not exist.")

    counts = {"titles": 0, "org_units": 0, "users": 0, "employees": 0}
    titles: dict[str, Title] = {}
    for values in (
        {
            "name": "DEMO-L1",
            "label": "Local Demo Associate",
            "degree_requirement": "any",
            "base_salary_min": 2000,
            "base_salary_max": 3500,
        },
        {
            "name": "DEMO-L2",
            "label": "Local Demo Specialist",
            "degree_requirement": "any",
            "base_salary_min": 3000,
            "base_salary_max": 5000,
        },
    ):
        title = session.query(Title).filter_by(
            organization_id=organization_id, name=values["name"]
        ).first()
        if title is None:
            title = Title(organization_id=organization_id, **values)
            session.add(title)
            session.flush()
            counts["titles"] += 1
        titles[title.name] = title

    units: dict[str, OrgUnit] = {}
    for name in ("Local Demo Engineering", "Local Demo Operations"):
        unit = session.query(OrgUnit).filter_by(
            organization_id=organization_id, name=name
        ).first()
        if unit is None:
            unit = OrgUnit(
                organization_id=organization_id,
                name=name,
                unit_type="department",
            )
            session.add(unit)
            session.flush()
            counts["org_units"] += 1
        units[name] = unit

    actor = session.query(SystemUser).filter_by(
        organization_id=organization_id, username="local-demo-actor"
    ).first()
    if actor is None:
        session.add(SystemUser(
            organization_id=organization_id,
            username="local-demo-actor",
            password_hash="!local-demo-login-disabled",
            role="admin",
            full_name="Local Demo Actor",
            is_active=False,
        ))
        counts["users"] += 1

    employees: dict[str, Employee] = {}
    employee_rows = (
        ("DEMO-EMP-0001", "Ada", "Lovelace", "Software Engineer", "DEMO-L2", "Local Demo Engineering", None),
        ("DEMO-EMP-0002", "Grace", "Hopper", "Systems Analyst", "DEMO-L1", "Local Demo Engineering", "DEMO-EMP-0001"),
        ("DEMO-EMP-0003", "Alan", "Turing", "Operations Analyst", "DEMO-L1", "Local Demo Operations", "DEMO-EMP-0001"),
    )
    for employee_id, first_name, last_name, position, title_name, unit_name, manager_ref in employee_rows:
        employee = session.query(Employee).filter_by(
            organization_id=organization_id, employee_id=employee_id
        ).first()
        if employee is None:
            manager = employees.get(manager_ref) if manager_ref else None
            employee = Employee(
                organization_id=organization_id,
                employee_id=employee_id,
                first_name=first_name,
                last_name=last_name,
                degree="BSc",
                position=position,
                join_date=datetime(2024, 1, 15),
                base_salary=3200 if title_name == "DEMO-L2" else 2600,
                status="active",
                title_id=titles[title_name].id,
                org_unit_id=units[unit_name].id,
                reports_to_id=manager.id if manager else None,
            )
            session.add(employee)
            session.flush()
            counts["employees"] += 1
        employees[employee_id] = employee

    return SeedResult(**counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("MYHR_DATABASE_URL"),
        help="Disposable SQLite SQLAlchemy URL. Defaults to MYHR_DATABASE_URL.",
    )
    parser.add_argument("--organization-id", type=int, default=1)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or MYHR_DATABASE_URL is required")
    try:
        result = seed_local_demo(args.database_url, args.organization_id)
    except DemoSeedError as exc:
        parser.error(str(exc))
    print(
        "Local demo seed complete: "
        f"{result.titles} titles, {result.org_units} units, "
        f"{result.users} actor profiles, {result.employees} employees created."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
