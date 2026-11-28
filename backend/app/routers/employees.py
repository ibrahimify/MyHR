"""Tenant-scoped employee endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.context import (
    OrganizationContext,
    get_authorized_session,
    get_organization_context,
)
from app.schemas.employees import (
    EmployeeAdminDetail,
    EmployeeCreate,
    EmployeeListPage,
    EmployeeOptions,
    EmployeeSummary,
    EmployeeUpdate,
    EmployeeWorkDetail,
)
from src.services.employee_service import (
    EmployeeActor,
    EmployeeConflictError,
    EmployeeNotFoundError,
    EmployeePermissionError,
    EmployeeValidationError,
    create_employee,
    get_employee_options,
    get_employee,
    list_employees,
    update_employee,
)


router = APIRouter(prefix="/api/employees", tags=["employees"])


def _actor(context: OrganizationContext) -> EmployeeActor:
    return EmployeeActor(context.organization_id, context.user_id, context.role)


def _detail(employee, context: OrganizationContext) -> dict:
    schema = EmployeeAdminDetail if context.role == "admin" else EmployeeWorkDetail
    detail = schema.model_validate(employee).model_dump(mode="json")
    detail.update(
        title_name=f"{employee.title.name} - {employee.title.label}",
        title_currency=employee.title.currency,
        org_unit_name=employee.org_unit.name if employee.org_unit else None,
        reports_to_name=employee.reports_to.full_name if employee.reports_to else None,
    )
    return detail


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, EmployeeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EmployeeConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, EmployeePermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, EmployeeValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=EmployeeListPage)
def employee_list(
    search: str | None = Query(default=None, max_length=100),
    employee_status: Literal["active", "inactive", "on_leave", "terminated"] | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_authorized_session),
    context: OrganizationContext = Depends(get_organization_context),
):
    rows, total = list_employees(
        session,
        context.organization_id,
        search=search,
        status=employee_status,
        page=page,
        page_size=page_size,
    )
    return EmployeeListPage(
        page=page,
        page_size=page_size,
        total=total,
        items=[EmployeeSummary.model_validate(row) for row in rows],
    )


@router.get("/options", response_model=EmployeeOptions)
def employee_options(
    session: Session = Depends(get_authorized_session),
    context: OrganizationContext = Depends(get_organization_context),
):
    return get_employee_options(session, context.organization_id)


@router.get("/{employee_id}", response_model=EmployeeAdminDetail | EmployeeWorkDetail)
def employee_detail(
    employee_id: int,
    session: Session = Depends(get_authorized_session),
    context: OrganizationContext = Depends(get_organization_context),
):
    try:
        return _detail(get_employee(session, context.organization_id, employee_id), context)
    except (
        EmployeeNotFoundError,
        EmployeePermissionError,
        EmployeeValidationError,
        EmployeeConflictError,
    ) as exc:
        _raise_http_error(exc)


@router.post("", response_model=EmployeeAdminDetail | EmployeeWorkDetail, status_code=status.HTTP_201_CREATED)
def employee_create(
    payload: EmployeeCreate,
    session: Session = Depends(get_authorized_session),
    context: OrganizationContext = Depends(get_organization_context),
):
    try:
        employee = create_employee(
            session,
            _actor(context),
            payload.model_dump(mode="python"),
        )
        return _detail(employee, context)
    except (
        EmployeeNotFoundError,
        EmployeePermissionError,
        EmployeeValidationError,
        EmployeeConflictError,
    ) as exc:
        _raise_http_error(exc)


@router.patch("/{employee_id}", response_model=EmployeeAdminDetail | EmployeeWorkDetail)
def employee_update(
    employee_id: int,
    payload: EmployeeUpdate,
    session: Session = Depends(get_authorized_session),
    context: OrganizationContext = Depends(get_organization_context),
):
    try:
        employee = update_employee(
            session,
            _actor(context),
            employee_id,
            payload.model_dump(mode="python", exclude_unset=True),
        )
        return _detail(employee, context)
    except (
        EmployeeNotFoundError,
        EmployeePermissionError,
        EmployeeValidationError,
        EmployeeConflictError,
    ) as exc:
        _raise_http_error(exc)
