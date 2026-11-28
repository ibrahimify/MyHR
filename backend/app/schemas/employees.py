"""Employee API schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


Degree = Literal["BSc", "MSc", "PhD", "Other"]
EmployeeStatus = Literal["active", "inactive", "on_leave", "terminated"]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmployeeCreate(StrictRequest):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=50)
    personal_email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    degree: Degree
    work_email: str | None = Field(default=None, max_length=255)
    work_phone: str | None = Field(default=None, max_length=50)
    position: str = Field(min_length=1, max_length=255)
    join_date: date
    base_salary: float = Field(ge=0)
    status: EmployeeStatus = "active"
    profile_picture: str | None = Field(default=None, max_length=500)
    linkedin_url: HttpUrl | None = None
    title_id: int = Field(gt=0)
    org_unit_id: int | None = Field(default=None, gt=0)
    reports_to_id: int | None = Field(default=None, gt=0)


class EmployeeUpdate(StrictRequest):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=50)
    personal_email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    degree: Degree | None = None
    work_email: str | None = Field(default=None, max_length=255)
    work_phone: str | None = Field(default=None, max_length=50)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    join_date: date | None = None
    base_salary: float | None = Field(default=None, ge=0)
    status: EmployeeStatus | None = None
    profile_picture: str | None = Field(default=None, max_length=500)
    linkedin_url: HttpUrl | None = None
    title_id: int | None = Field(default=None, gt=0)
    org_unit_id: int | None = Field(default=None, gt=0)
    reports_to_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one employee field is required.")
        non_nullable = {
            "first_name", "last_name", "degree", "position", "join_date",
            "base_salary", "status", "title_id",
        }
        if any(getattr(self, field) is None for field in non_nullable.intersection(self.model_fields_set)):
            raise ValueError("Required employee fields cannot be null.")
        return self


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    first_name: str
    last_name: str
    position: str
    status: EmployeeStatus
    title_id: int
    org_unit_id: int | None


class EmployeeWorkDetail(EmployeeSummary):
    organization_id: int
    work_email: str | None
    work_phone: str | None
    join_date: datetime
    base_salary: float
    profile_picture: str | None
    linkedin_url: str | None
    reports_to_id: int | None
    title_name: str | None = None
    title_currency: str | None = None
    org_unit_name: str | None = None
    reports_to_name: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeAdminDetail(EmployeeWorkDetail):
    date_of_birth: datetime | None
    phone: str | None
    personal_email: str | None
    address: str | None
    degree: Degree


class EmployeeListPage(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[EmployeeSummary]


class EmployeeOption(BaseModel):
    id: int
    label: str


class EmployeeOptions(BaseModel):
    titles: list[EmployeeOption]
    org_units: list[EmployeeOption]
    managers: list[EmployeeOption]
