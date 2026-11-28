"""Employee API tenant isolation and mutation tests."""

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.context import (
    OrganizationContext,
    get_authorized_session,
    get_organization_context,
)
from app.main import create_app
from src.database.models import (
    AuditLog, Base, Employee, Organization, OrgUnit, ReferenceCounter, SystemUser, Title
)
from src.services.employee_service import list_employees


@pytest.fixture()
def api() -> Iterator[tuple[TestClient, sessionmaker]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add_all([
            Organization(id=1, name="First Organization", slug="first"),
            Organization(id=2, name="Second Organization", slug="second"),
            Title(
                id=1,
                organization_id=1,
                name="L7",
                label="Entry Level",
                degree_requirement="BSc",
                base_salary_min=2000,
                base_salary_max=3000,
            ),
            OrgUnit(id=1, organization_id=1, name="Engineering", unit_type="department"),
            OrgUnit(id=2, organization_id=2, name="Foreign Unit", unit_type="department"),
            Title(
                id=2,
                organization_id=2,
                name="L7",
                label="Entry Level",
                degree_requirement="BSc",
                base_salary_min=2000,
                base_salary_max=3000,
            ),
            SystemUser(
                id=1,
                organization_id=1,
                username="local-admin",
                password_hash="not-used-by-api-tests",
                role="admin",
                full_name="Local Administrator",
            ),
            SystemUser(
                id=2,
                organization_id=2,
                username="foreign-admin",
                password_hash="not-used-by-api-tests",
                role="admin",
                full_name="Foreign Administrator",
            ),
            Employee(
                id=20,
                organization_id=2,
                employee_id="EMP-0001",
                first_name="Other",
                last_name="Tenant",
                degree="BSc",
                position="Analyst",
                join_date=datetime(2024, 1, 1),
                base_salary=2500,
                status="active",
                title_id=2,
            ),
        ])
        session.commit()

    app = create_app()

    def session_override():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_authorized_session] = session_override
    app.dependency_overrides[get_organization_context] = lambda: OrganizationContext(1, 1, "admin")
    with TestClient(app) as client:
        yield client, session_factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def employee_payload(**overrides):
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "degree": "BSc",
        "position": "Software Engineer",
        "join_date": "2024-02-01",
        "base_salary": 2600,
        "status": "active",
        "title_id": 1,
    }
    payload.update(overrides)
    return payload


def test_create_list_and_detail_are_scoped_to_server_context(api):
    client, _ = api

    created = client.post("/api/employees", json=employee_payload())
    assert created.status_code == 201
    employee = created.json()
    assert employee["organization_id"] == 1
    assert employee["employee_id"] == "EMP-0001"
    assert employee["title_name"] == "L7 - Entry Level"
    assert employee["title_currency"] == "EUR"
    assert employee["org_unit_name"] is None
    assert employee["reports_to_name"] is None

    listed = client.get("/api/employees")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert [row["id"] for row in listed.json()["items"]] == [employee["id"]]

    hidden = client.get("/api/employees/20")
    assert hidden.status_code == 404
    assert hidden.json() == {"detail": "Employee not found."}


def test_service_list_enforces_tenant_scope(api):
    _, session_factory = api
    with session_factory() as session:
        first_tenant, total = list_employees(session, 1)
        second_tenant, other_total = list_employees(session, 2)
    assert first_tenant == []
    assert total == 0
    assert [employee.id for employee in second_tenant] == [20]
    assert other_total == 1


def test_options_include_only_current_tenant_records(api):
    client, _ = api
    created = client.post("/api/employees", json=employee_payload()).json()

    response = client.get("/api/employees/options")
    assert response.status_code == 200
    options = response.json()
    assert options["titles"] == [{"id": 1, "label": "L7 - Entry Level"}]
    assert options["org_units"] == [{"id": 1, "label": "Engineering (department)"}]
    assert options["managers"] == [
        {"id": created["id"], "label": "Ada Lovelace (EMP-0001)"}
    ]
    serialized = str(options)
    assert "Foreign Unit" not in serialized
    assert "Other Tenant" not in serialized


def test_create_records_actor_and_tenant_in_audit_log(api):
    client, session_factory = api
    response = client.post("/api/employees", json=employee_payload())
    assert response.status_code == 201

    with session_factory() as session:
        audit = session.query(AuditLog).one()
        assert audit.organization_id == 1
        assert audit.performed_by_id == 1
        assert audit.performed_by_username == "local-admin"
        assert audit.action == "employee.create"
        assert audit.target_id == response.json()["id"]
        assert '"employee_id": "EMP-0001"' in audit.after_value
        assert '"first_name": "Ada"' in audit.after_value
        assert '"work_email": null' in audit.after_value


def test_create_rejects_foreign_tenant_title(api):
    client, session_factory = api
    response = client.post("/api/employees", json=employee_payload(title_id=2))

    assert response.status_code == 422
    assert response.json() == {"detail": "Title is not available in this organization."}
    with session_factory() as session:
        assert session.query(Employee).filter(Employee.organization_id == 1).count() == 0
        assert session.query(AuditLog).count() == 0


def test_create_rejects_foreign_tenant_org_unit(api):
    client, _ = api
    response = client.post("/api/employees", json=employee_payload(org_unit_id=2))
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Organization unit is not available in this organization."
    }


def test_request_cannot_supply_organization_context(api):
    client, _ = api
    response = client.post(
        "/api/employees",
        json=employee_payload(organization_id=2),
    )
    assert response.status_code == 422


def test_update_rejects_foreign_manager_and_preserves_employee(api):
    client, _ = api
    created = client.post("/api/employees", json=employee_payload()).json()

    response = client.patch(
        f"/api/employees/{created['id']}",
        json={"reports_to_id": 20},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Manager is not available in this organization."}
    unchanged = client.get(f"/api/employees/{created['id']}").json()
    assert unchanged["reports_to_id"] is None


def test_failed_update_rolls_back_earlier_field_changes(api):
    client, session_factory = api
    created = client.post("/api/employees", json=employee_payload()).json()

    response = client.patch(
        f"/api/employees/{created['id']}",
        json={"org_unit_id": 1, "base_salary": 9000},
    )
    assert response.status_code == 422
    with session_factory() as session:
        employee = session.get(Employee, created["id"])
        assert employee.org_unit_id is None
        assert employee.base_salary == 2600
        assert session.query(AuditLog).filter_by(action="employee.update").count() == 0


def test_update_rejects_reporting_cycle_and_audits_valid_change(api):
    client, session_factory = api
    first = client.post("/api/employees", json=employee_payload()).json()
    second = client.post(
        "/api/employees",
        json=employee_payload(first_name="Grace", last_name="Hopper", reports_to_id=first["id"]),
    ).json()

    cycle = client.patch(
        f"/api/employees/{first['id']}",
        json={"reports_to_id": second["id"]},
    )
    assert cycle.status_code == 422
    assert cycle.json() == {"detail": "The manager assignment would create a reporting cycle."}

    updated = client.patch(
        f"/api/employees/{first['id']}",
        json={"position": "Senior Software Engineer", "base_salary": 2800},
    )
    assert updated.status_code == 200
    assert updated.json()["position"] == "Senior Software Engineer"
    with session_factory() as session:
        update_audits = session.query(AuditLog).filter_by(action="employee.update").all()
        assert len(update_audits) == 1
        assert '"position": "Software Engineer"' in update_audits[0].before_value
        assert '"position": "Senior Software Engineer"' in update_audits[0].after_value


def test_payload_and_business_validation_return_clear_errors(api):
    client, _ = api
    empty_update = client.patch("/api/employees/1", json={})
    assert empty_update.status_code == 422

    invalid_salary = client.post("/api/employees", json=employee_payload(base_salary=9000))
    assert invalid_salary.status_code == 422

    invalid_dates = client.post(
        "/api/employees",
        json=employee_payload(date_of_birth="2025-01-01", join_date="2024-01-01"),
    )
    assert invalid_dates.status_code == 422

    null_required_field = client.patch("/api/employees/1", json={"base_salary": None})
    assert null_required_field.status_code == 422


def test_list_search_status_pagination_and_ordering(api):
    client, _ = api
    client.post("/api/employees", json=employee_payload(first_name="Zoe", last_name="Alpha"))
    client.post(
        "/api/employees",
        json=employee_payload(first_name="Amy", last_name="Zulu", status="inactive"),
    )
    client.post("/api/employees", json=employee_payload(first_name="Ada", last_name="Alpha"))

    first_page = client.get("/api/employees?page=1&page_size=1").json()
    second_page = client.get("/api/employees?page=2&page_size=1").json()
    assert first_page["total"] == 3
    assert first_page["items"][0]["first_name"] == "Ada"
    assert second_page["items"][0]["first_name"] == "Zoe"

    searched = client.get("/api/employees?search=Zulu&status=inactive").json()
    assert searched["total"] == 1
    assert searched["items"][0]["first_name"] == "Amy"


def test_hr_detail_hides_personal_fields_and_restricts_updates(api):
    client, _ = api
    created = client.post(
        "/api/employees",
        json=employee_payload(
            date_of_birth="1990-01-01",
            personal_email="ada@example.test",
            linkedin_url="https://example.test/ada",
        ),
    ).json()
    app = client.app
    app.dependency_overrides[get_organization_context] = lambda: OrganizationContext(
        1, None, "hr_officer"
    )

    detail = client.get(f"/api/employees/{created['id']}")
    assert detail.status_code == 200
    assert "date_of_birth" not in detail.json()
    assert "personal_email" not in detail.json()
    assert "degree" not in detail.json()
    assert detail.json()["linkedin_url"] == "https://example.test/ada"

    forbidden = client.patch(
        f"/api/employees/{created['id']}", json={"base_salary": 2700}
    )
    assert forbidden.status_code == 403

    private_create = client.post(
        "/api/employees",
        json=employee_payload(
            first_name="Grace",
            last_name="Hopper",
            personal_email="grace@example.test",
        ),
    )
    assert private_create.status_code == 403


def test_audit_snapshot_records_work_field_changes(api):
    client, session_factory = api
    created = client.post("/api/employees", json=employee_payload()).json()

    response = client.patch(
        f"/api/employees/{created['id']}",
        json={"work_email": "ada@work.example", "position": "Senior Engineer"},
    )
    assert response.status_code == 200

    with session_factory() as session:
        audit = session.query(AuditLog).filter_by(action="employee.update").one()
        assert '"work_email": null' in audit.before_value
        assert '"work_email": "ada@work.example"' in audit.after_value
        assert '"position": "Software Engineer"' in audit.before_value
        assert '"position": "Senior Engineer"' in audit.after_value


def test_inactive_employee_cannot_be_assigned_as_manager(api):
    client, _ = api
    inactive = client.post(
        "/api/employees",
        json=employee_payload(
            first_name="Inactive", last_name="Manager", status="inactive"
        ),
    ).json()

    response = client.post(
        "/api/employees",
        json=employee_payload(
            first_name="New", last_name="Employee", reports_to_id=inactive["id"]
        ),
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Manager must be active."}


def test_foreign_actor_rolls_back_employee_counter_and_audit(api):
    client, session_factory = api
    client.app.dependency_overrides[get_organization_context] = lambda: OrganizationContext(
        1, 2, "admin"
    )

    response = client.post("/api/employees", json=employee_payload())
    assert response.status_code == 422
    assert response.json() == {"detail": "The acting user is not valid for this organization."}

    with session_factory() as session:
        assert session.query(Employee).filter_by(organization_id=1).count() == 0
        assert session.query(ReferenceCounter).filter_by(organization_id=1).count() == 0
        assert session.query(AuditLog).filter_by(organization_id=1).count() == 0
