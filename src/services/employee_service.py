"""Tenant-scoped employee operations shared by application frontends."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Literal, Mapping

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.database.connection import generate_employee_id, validate_salary_for_title
from src.database.models import AuditLog, Employee, OrgUnit, Organization, SystemUser, Title


class EmployeeServiceError(Exception):
    """Base class for expected employee operation failures."""


class EmployeeNotFoundError(EmployeeServiceError):
    pass


class EmployeeValidationError(EmployeeServiceError):
    pass


class EmployeeConflictError(EmployeeServiceError):
    pass


class EmployeePermissionError(EmployeeServiceError):
    pass


@dataclass(frozen=True)
class EmployeeActor:
    """Identity already resolved by the calling application."""

    organization_id: int
    user_id: int | None = None
    role: Literal["admin", "hr_officer"] = "admin"


def list_employees(
    session: Session,
    organization_id: int,
    *,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Employee], int]:
    query = _employee_query(session, organization_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(
            Employee.employee_id.ilike(pattern),
            Employee.first_name.ilike(pattern),
            Employee.last_name.ilike(pattern),
            Employee.position.ilike(pattern),
        ))
    if status:
        query = query.filter(Employee.status == status)
    total = query.count()
    rows = (
        query.order_by(Employee.last_name.asc(), Employee.first_name.asc(), Employee.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_employee(session: Session, organization_id: int, employee_id: int) -> Employee:
    employee = _employee_query(session, organization_id).filter(Employee.id == employee_id).first()
    if employee is None:
        raise EmployeeNotFoundError("Employee not found.")
    return employee


def get_employee_options(session: Session, organization_id: int) -> dict[str, list[dict[str, Any]]]:
    """Return tenant-owned records used by employee forms."""
    titles = session.query(Title).filter(
        Title.organization_id == organization_id
    ).order_by(Title.name.asc(), Title.id.asc()).all()
    org_units = session.query(OrgUnit).filter(
        OrgUnit.organization_id == organization_id
    ).order_by(OrgUnit.name.asc(), OrgUnit.id.asc()).all()
    managers = session.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.status == "active",
    ).order_by(Employee.last_name.asc(), Employee.first_name.asc(), Employee.id.asc()).all()
    return {
        "titles": [
            {"id": title.id, "label": f"{title.name} - {title.label}"}
            for title in titles
        ],
        "org_units": [
            {"id": unit.id, "label": f"{unit.name} ({unit.unit_type})"}
            for unit in org_units
        ],
        "managers": [
            {"id": manager.id, "label": f"{manager.full_name} ({manager.employee_id})"}
            for manager in managers
        ],
    }


def create_employee(
    session: Session,
    actor: EmployeeActor,
    values: Mapping[str, Any],
) -> Employee:
    try:
        return _create_employee(session, actor, values)
    except EmployeeServiceError:
        session.rollback()
        raise


def _create_employee(
    session: Session,
    actor: EmployeeActor,
    values: Mapping[str, Any],
) -> Employee:
    _require_organization(session, actor.organization_id)
    data = dict(values)
    _validate_actor(session, actor)
    if actor.role == "hr_officer":
        private_fields = {"date_of_birth", "phone", "personal_email", "address"}
        if any(data.get(field) is not None for field in private_fields):
            raise EmployeePermissionError(
                "This role cannot create private employee fields."
            )
    title = _tenant_record(session, Title, actor.organization_id, data.get("title_id"), "Title")
    org_unit = _optional_tenant_record(
        session, OrgUnit, actor.organization_id, data.get("org_unit_id"), "Organization unit"
    )
    manager = _optional_manager(
        session, actor.organization_id, data.get("reports_to_id")
    )
    _validate_salary(title, data["base_salary"])
    _validate_dates(data.get("date_of_birth"), data["join_date"])

    employee = Employee(
        organization_id=actor.organization_id,
        employee_id=generate_employee_id(session, actor.organization_id),
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=_as_datetime(data.get("date_of_birth")),
        phone=data.get("phone"),
        personal_email=data.get("personal_email"),
        address=data.get("address"),
        degree=data["degree"],
        work_email=data.get("work_email"),
        work_phone=data.get("work_phone"),
        position=data["position"],
        join_date=_as_datetime(data["join_date"]),
        base_salary=data["base_salary"],
        status=data.get("status", "active"),
        profile_picture=data.get("profile_picture"),
        linkedin_url=_as_optional_string(data.get("linkedin_url")),
        title_id=title.id,
        org_unit_id=org_unit.id if org_unit else None,
        reports_to_id=manager.id if manager else None,
    )
    session.add(employee)
    try:
        session.flush()
        _add_audit_entry(
            session,
            actor,
            action="employee.create",
            employee=employee,
            after=_audit_snapshot(employee),
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmployeeConflictError("The employee could not be created because a value conflicts.") from exc
    except Exception:
        session.rollback()
        raise
    return get_employee(session, actor.organization_id, employee.id)


def update_employee(
    session: Session,
    actor: EmployeeActor,
    employee_id: int,
    values: Mapping[str, Any],
) -> Employee:
    try:
        return _update_employee(session, actor, employee_id, values)
    except EmployeeServiceError:
        session.rollback()
        raise


def _update_employee(
    session: Session,
    actor: EmployeeActor,
    employee_id: int,
    values: Mapping[str, Any],
) -> Employee:
    employee = get_employee(session, actor.organization_id, employee_id)
    data = dict(values)
    _validate_actor(session, actor)
    if actor.role == "hr_officer":
        protected = {
            "first_name", "last_name", "date_of_birth", "phone", "personal_email",
            "address", "degree", "title_id", "base_salary",
        }
        if protected.intersection(data):
            raise EmployeePermissionError(
                "This role cannot update personal or administrative fields."
            )
    before = _audit_snapshot(employee)

    title = employee.title
    if "title_id" in data:
        title = _tenant_record(session, Title, actor.organization_id, data["title_id"], "Title")
    if "org_unit_id" in data:
        org_unit = _optional_tenant_record(
            session, OrgUnit, actor.organization_id, data["org_unit_id"], "Organization unit"
        )
        employee.org_unit_id = org_unit.id if org_unit else None
    if "reports_to_id" in data:
        manager = _optional_manager(
            session, actor.organization_id, data["reports_to_id"]
        )
        if manager and _would_create_manager_cycle(
            session, actor.organization_id, employee.id, manager.id
        ):
            raise EmployeeValidationError("The manager assignment would create a reporting cycle.")
        employee.reports_to_id = manager.id if manager else None

    salary = data.get("base_salary", employee.base_salary)
    _validate_salary(title, salary)
    date_of_birth = data.get("date_of_birth", employee.date_of_birth)
    join_date = data.get("join_date", employee.join_date)
    _validate_dates(date_of_birth, join_date)

    editable_fields = (
        "first_name",
        "last_name",
        "phone",
        "personal_email",
        "address",
        "degree",
        "work_email",
        "work_phone",
        "position",
        "base_salary",
        "status",
        "profile_picture",
        "linkedin_url",
    )
    for field in editable_fields:
        if field in data:
            value = _as_optional_string(data[field]) if field == "linkedin_url" else data[field]
            setattr(employee, field, value)
    if "date_of_birth" in data:
        employee.date_of_birth = _as_datetime(data["date_of_birth"])
    if "join_date" in data:
        employee.join_date = _as_datetime(data["join_date"])
    if "title_id" in data:
        employee.title_id = title.id

    try:
        session.flush()
        _add_audit_entry(
            session,
            actor,
            action="employee.update",
            employee=employee,
            before=before,
            after=_audit_snapshot(employee),
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmployeeConflictError("The employee could not be updated because a value conflicts.") from exc
    except Exception:
        session.rollback()
        raise
    return get_employee(session, actor.organization_id, employee.id)


def _employee_query(session: Session, organization_id: int):
    return session.query(Employee).options(
        joinedload(Employee.title),
        joinedload(Employee.org_unit),
        joinedload(Employee.reports_to),
    ).filter(Employee.organization_id == organization_id)


def _require_organization(session: Session, organization_id: int) -> None:
    if session.query(Organization.id).filter(Organization.id == organization_id).first() is None:
        raise EmployeeValidationError("Organization context is not valid.")


def _tenant_record(session: Session, model, organization_id: int, record_id: int | None, label: str):
    if record_id is None:
        raise EmployeeValidationError(f"{label} is required.")
    record = session.query(model).filter(
        model.id == record_id, model.organization_id == organization_id
    ).first()
    if record is None:
        raise EmployeeValidationError(f"{label} is not available in this organization.")
    return record


def _optional_tenant_record(
    session: Session, model, organization_id: int, record_id: int | None, label: str
):
    if record_id is None:
        return None
    return _tenant_record(session, model, organization_id, record_id, label)


def _optional_manager(
    session: Session, organization_id: int, employee_id: int | None
) -> Employee | None:
    manager = _optional_tenant_record(
        session, Employee, organization_id, employee_id, "Manager"
    )
    if manager is not None and manager.status != "active":
        raise EmployeeValidationError("Manager must be active.")
    return manager


def _validate_salary(title: Title, salary: float) -> None:
    valid, message = validate_salary_for_title(title, salary)
    if not valid:
        raise EmployeeValidationError(message)


def _validate_dates(date_of_birth: date | datetime | None, join_date: date | datetime) -> None:
    if date_of_birth and _as_date(date_of_birth) >= _as_date(join_date):
        raise EmployeeValidationError("Date of birth must be earlier than the join date.")


def _would_create_manager_cycle(
    session: Session,
    organization_id: int,
    employee_id: int,
    manager_id: int,
) -> bool:
    current_id: int | None = manager_id
    visited: set[int] = set()
    while current_id is not None:
        if current_id == employee_id or current_id in visited:
            return True
        visited.add(current_id)
        manager = session.query(Employee).filter(
            Employee.id == current_id,
            Employee.organization_id == organization_id,
        ).first()
        current_id = manager.reports_to_id if manager else None
    return False


def _add_audit_entry(
    session: Session,
    actor: EmployeeActor,
    *,
    action: str,
    employee: Employee,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    user = _validate_actor(session, actor)
    session.add(AuditLog(
        organization_id=actor.organization_id,
        performed_by_id=user.id if user else None,
        performed_by_username=user.username if user else None,
        performed_by_name=user.full_name if user else None,
        action=action,
        target_table="employee",
        target_id=employee.id,
        description=f"Employee {'added' if action == 'employee.create' else 'updated'}: "
        f"{employee.full_name} ({employee.employee_id})",
        before_value=json.dumps(before, sort_keys=True) if before is not None else None,
        after_value=json.dumps(after, sort_keys=True) if after is not None else None,
    ))


def _validate_actor(session: Session, actor: EmployeeActor) -> SystemUser | None:
    if actor.user_id is None:
        return None
    user = session.query(SystemUser).filter(
        SystemUser.id == actor.user_id,
        SystemUser.organization_id == actor.organization_id,
        SystemUser.role == actor.role,
        SystemUser.is_active.is_(True),
    ).first()
    if user is None:
        raise EmployeeValidationError("The acting user is not valid for this organization.")
    return user


def _audit_snapshot(employee: Employee) -> dict[str, Any]:
    return {
        "employee_id": employee.employee_id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "date_of_birth": employee.date_of_birth.isoformat() if employee.date_of_birth else None,
        "phone": employee.phone,
        "personal_email": employee.personal_email,
        "address": employee.address,
        "degree": employee.degree,
        "work_email": employee.work_email,
        "work_phone": employee.work_phone,
        "position": employee.position,
        "join_date": employee.join_date.isoformat(),
        "status": employee.status,
        "base_salary": employee.base_salary,
        "profile_picture": employee.profile_picture,
        "linkedin_url": employee.linkedin_url,
        "title_id": employee.title_id,
        "org_unit_id": employee.org_unit_id,
        "reports_to_id": employee.reports_to_id,
    }


def _as_datetime(value: date | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def _as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def _as_optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
