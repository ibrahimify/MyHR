"""
MyHR Database Models
All 9 tables + junction table for commendation-employee relationship.

Key design decisions:
- Promotion months remaining is CALCULATED LIVE, never stored
- Annual salary increment is separate from promotion entirely
- Language is per-session only, not stored per user
- Org hierarchy is self-referencing (unlimited depth)
- Employees are data subjects only — no login
- Only Admin and HR Officer can log in
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# 1. OrgUnit — self-referencing hierarchy
# ─────────────────────────────────────────────
class OrgUnit(Base):
    """
    Unlimited depth hierarchy: Organization → Division → Department → Unit → Team
    Self-referencing via parent_id.
    head_employee_id points to whoever leads this node (CEO, HOD, Unit In-Charge, etc.)
    """
    __tablename__ = "org_unit"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(255), nullable=False)
    unit_type        = Column(
        Enum("organization", "division", "department", "unit", "team", name="unit_type_enum"),
        nullable=False
    )
    parent_id        = Column(Integer, ForeignKey("org_unit.id"), nullable=True)
    head_employee_id = Column(Integer, ForeignKey("employee.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent    = relationship("OrgUnit", remote_side=[id], back_populates="children")
    children  = relationship("OrgUnit", back_populates="parent")
    employees = relationship("Employee", foreign_keys="Employee.org_unit_id", back_populates="org_unit")
    head      = relationship("Employee", foreign_keys=[head_employee_id])

    def __repr__(self):
        return f"<OrgUnit {self.name} ({self.unit_type})>"


# ─────────────────────────────────────────────
# 2. Title — salary levels (L3 → L7)
# ─────────────────────────────────────────────
class Title(Base):
    """
    Salary levels. BSc → L7, MSc → L6, PhD → L5 on hire.
    Admin configures salary ranges and annual increment rate per level.
    annual_increment_type: 'percentage' or 'fixed'
    annual_increment_value: % or EUR amount
    promotion_salary_increase_pct: salary bump % when promoted to this level
    """
    __tablename__ = "title"

    id                           = Column(Integer, primary_key=True, autoincrement=True)
    name                         = Column(String(50), nullable=False, unique=True)   # "L7", "L6"...
    label                        = Column(String(100), nullable=False)               # "Entry Level"
    degree_requirement           = Column(
        Enum("BSc", "MSc", "PhD", "any", name="degree_enum"),
        nullable=False, default="any"
    )
    base_salary_min              = Column(Float, nullable=False, default=2000.0)
    base_salary_max              = Column(Float, nullable=False, default=3000.0)
    currency                     = Column(String(10), nullable=False, default="EUR")
    annual_increment_type        = Column(
        Enum("percentage", "fixed", name="increment_type_enum"),
        nullable=False, default="percentage"
    )
    annual_increment_value       = Column(Float, nullable=False, default=3.0)  # 3% or 150 EUR
    promotion_salary_increase_pct = Column(Float, nullable=False, default=15.0)  # % on promotion
    created_at                   = Column(DateTime, default=datetime.utcnow)
    updated_at                   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employees              = relationship("Employee", back_populates="title")
    promotion_rules_from   = relationship("PromotionRule", foreign_keys="PromotionRule.from_title_id", back_populates="from_title")
    promotion_rules_to     = relationship("PromotionRule", foreign_keys="PromotionRule.to_title_id", back_populates="to_title")

    def __repr__(self):
        return f"<Title {self.name}>"


# ─────────────────────────────────────────────
# 3. Employee — core record
# ─────────────────────────────────────────────
class Employee(Base):
    """
    Core employee record. Employees are DATA SUBJECTS only — no login.
    Two layers of visibility:
      - Admin sees everything
      - HR Officer sees work-facing fields only
    Employee can only edit: profile_picture, linkedin_url, status
    Everything else requires admin action.
    
    annual_increment_last_applied: date of last approved salary increment
    salary_increment_approved: whether current year's increment has been applied
    """
    __tablename__ = "employee"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    employee_id     = Column(String(20), nullable=False, unique=True)  # "EMP-1001"

    # Personal — Admin only
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    date_of_birth   = Column(DateTime, nullable=True)
    phone           = Column(String(50), nullable=True)
    personal_email  = Column(String(255), nullable=True)
    address         = Column(Text, nullable=True)
    degree          = Column(
        Enum("BSc", "MSc", "PhD", "Other", name="emp_degree_enum"),
        nullable=False
    )

    # Work-facing — HR Officer can see
    work_email      = Column(String(255), nullable=True)
    work_phone      = Column(String(50), nullable=True)
    position        = Column(String(255), nullable=False)
    join_date       = Column(DateTime, nullable=False)
    base_salary     = Column(Float, nullable=False)
    status          = Column(
        Enum("active", "inactive", "on_leave", name="emp_status_enum"),
        nullable=False, default="active"
    )

    # Annual increment tracking
    annual_increment_last_applied = Column(DateTime, nullable=True)

    # Employee-editable
    profile_picture = Column(String(500), nullable=True)
    linkedin_url    = Column(String(500), nullable=True)

    # FK relationships
    org_unit_id     = Column(Integer, ForeignKey("org_unit.id"), nullable=True)
    title_id        = Column(Integer, ForeignKey("title.id"), nullable=False)
    reports_to_id   = Column(Integer, ForeignKey("employee.id"), nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org_unit     = relationship("OrgUnit", foreign_keys=[org_unit_id], back_populates="employees")
    title        = relationship("Title", back_populates="employees")
    reports_to   = relationship("Employee", remote_side=[id])
    promotions   = relationship("PromotionHistory", back_populates="employee", order_by="PromotionHistory.promoted_at")
    commendations = relationship("Commendation", secondary="commendation_employee", back_populates="employees")
    sanctions    = relationship("Sanction", back_populates="employee")
    salary_increments = relationship("SalaryIncrementHistory", back_populates="employee")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee {self.employee_id} — {self.full_name}>"


# ─────────────────────────────────────────────
# 4. PromotionRule — configurable race track
# ─────────────────────────────────────────────
class PromotionRule(Base):
    """
    One row per level transition (e.g. L7→L6).
    base_months: starting point for the promotion race
    Commendations and sanctions are OPTIONAL modifiers applied on top.
    After promotion, the clock resets — no carryover.
    """
    __tablename__ = "promotion_rule"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    from_title_id  = Column(Integer, ForeignKey("title.id"), nullable=False)
    to_title_id    = Column(Integer, ForeignKey("title.id"), nullable=False)
    base_months    = Column(Integer, nullable=False, default=36)  # base race duration
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    from_title = relationship("Title", foreign_keys=[from_title_id], back_populates="promotion_rules_from")
    to_title   = relationship("Title", foreign_keys=[to_title_id], back_populates="promotion_rules_to")

    def __repr__(self):
        return f"<PromotionRule {self.from_title_id}→{self.to_title_id} base={self.base_months}mo>"


# ─────────────────────────────────────────────
# 5. PromotionHistory — every promotion ever
# ─────────────────────────────────────────────
class PromotionHistory(Base):
    """
    Every promotion applied. Immutable after creation.
    basis: time_based (hit base_months), accelerated (commendations reduced timeline), 
           or admin_override.
    months_at_promotion: actual months taken (for audit/analytics)
    """
    __tablename__ = "promotion_history"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    employee_id     = Column(Integer, ForeignKey("employee.id"), nullable=False)
    from_title_id   = Column(Integer, ForeignKey("title.id"), nullable=False)
    to_title_id     = Column(Integer, ForeignKey("title.id"), nullable=False)
    approved_by_id  = Column(Integer, ForeignKey("system_user.id"), nullable=False)
    basis           = Column(
        Enum("time_based", "accelerated", "admin_override", name="promo_basis_enum"),
        nullable=False
    )
    months_taken    = Column(Integer, nullable=True)  # actual months in role before promotion
    notes           = Column(Text, nullable=True)
    promoted_at     = Column(DateTime, default=datetime.utcnow)

    employee    = relationship("Employee", back_populates="promotions")
    from_title  = relationship("Title", foreign_keys=[from_title_id])
    to_title    = relationship("Title", foreign_keys=[to_title_id])
    approved_by = relationship("SystemUser")

    def __repr__(self):
        return f"<PromotionHistory emp={self.employee_id} {self.from_title_id}→{self.to_title_id}>"


# ─────────────────────────────────────────────
# 6. Commendation — team or individual award
# ─────────────────────────────────────────────
class Commendation(Base):
    """
    One commendation can apply to multiple employees (bulk team award).
    category: 1, 2, or 3 — maps to -1, -3, -6 months off the promotion race.
    Max 3 commendations per employee per role — enforced in business logic layer.
    commendation_ref: unique human-readable ID e.g. "COM-2026-0418-001"
    """
    __tablename__ = "commendation"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    commendation_ref = Column(String(30), nullable=False, unique=True)  # "COM-2026-0418-001"
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    category        = Column(Integer, nullable=False)  # 1, 2, or 3
    months_impact   = Column(Integer, nullable=False)  # -1, -3, or -6
    is_team_award   = Column(Boolean, default=False)
    issued_by_id    = Column(Integer, ForeignKey("system_user.id"), nullable=False)
    issued_at       = Column(DateTime, default=datetime.utcnow)

    issued_by = relationship("SystemUser")
    employees = relationship("Employee", secondary="commendation_employee", back_populates="commendations")

    def __repr__(self):
        return f"<Commendation {self.commendation_ref} Cat{self.category}>"


# ─────────────────────────────────────────────
# Junction: commendation ↔ employee
# ─────────────────────────────────────────────
class CommendationEmployee(Base):
    """One commendation → many employees."""
    __tablename__ = "commendation_employee"

    commendation_id = Column(Integer, ForeignKey("commendation.id"), primary_key=True)
    employee_id     = Column(Integer, ForeignKey("employee.id"), primary_key=True)


# ─────────────────────────────────────────────
# 7. Sanction — disciplinary action
# ─────────────────────────────────────────────
class Sanction(Base):
    """
    Disciplinary sanction. Duration is in MONTHS (1-12), not days.
    sanction_ref: unique human-readable ID e.g. "SAN-2026-0418-001"
    delay_months: how many months this adds to the employee's promotion race.
    is_resolved: when marked resolved by admin.
    """
    __tablename__ = "sanction"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    sanction_ref = Column(String(30), nullable=False, unique=True)  # "SAN-2026-0418-001"
    employee_id  = Column(Integer, ForeignKey("employee.id"), nullable=False)
    sanction_type = Column(
        Enum("verbal_warning", "written_warning", "suspension", "final_warning", name="sanction_type_enum"),
        nullable=False
    )
    reason        = Column(Text, nullable=False)
    delay_months  = Column(Integer, nullable=False)  # 1-12 months added to promotion race
    issued_by_id  = Column(Integer, ForeignKey("system_user.id"), nullable=False)
    issued_at     = Column(DateTime, default=datetime.utcnow)
    resolved_at   = Column(DateTime, nullable=True)
    is_resolved   = Column(Boolean, default=False)

    employee  = relationship("Employee", back_populates="sanctions")
    issued_by = relationship("SystemUser")

    def __repr__(self):
        return f"<Sanction {self.sanction_ref} +{self.delay_months}mo>"


# ─────────────────────────────────────────────
# 8. SalaryIncrementHistory — annual increments
# ─────────────────────────────────────────────
class SalaryIncrementHistory(Base):
    """
    Records every manual annual salary increment approved by admin.
    Separate from promotion entirely.
    salary_before / salary_after: for audit trail.
    increment_type: 'percentage' or 'fixed' — copied from Title config at time of approval.
    increment_value: the actual % or amount applied.
    """
    __tablename__ = "salary_increment_history"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    employee_id     = Column(Integer, ForeignKey("employee.id"), nullable=False)
    approved_by_id  = Column(Integer, ForeignKey("system_user.id"), nullable=False)
    salary_before   = Column(Float, nullable=False)
    salary_after    = Column(Float, nullable=False)
    increment_type  = Column(
        Enum("percentage", "fixed", name="salary_inc_type_enum"),
        nullable=False
    )
    increment_value = Column(Float, nullable=False)
    applied_at      = Column(DateTime, default=datetime.utcnow)
    notes           = Column(Text, nullable=True)

    employee    = relationship("Employee", back_populates="salary_increments")
    approved_by = relationship("SystemUser")

    def __repr__(self):
        return f"<SalaryIncrement emp={self.employee_id} {self.salary_before}→{self.salary_after}>"


# ─────────────────────────────────────────────
# 9. AuditLog — immutable activity trail
# ─────────────────────────────────────────────
class AuditLog(Base):
    """
    Every admin/HR action is logged automatically.
    Covers: who, what, when, before/after values (JSON snapshots).
    Logs cannot be deleted or modified.
    action examples: "employee.create", "promotion.approve", "sanction.issue"
    """
    __tablename__ = "audit_log"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    performed_by_id = Column(Integer, ForeignKey("system_user.id"), nullable=True)
    action          = Column(String(100), nullable=False)
    target_table    = Column(String(100), nullable=True)
    target_id       = Column(Integer, nullable=True)
    description     = Column(Text, nullable=True)
    before_value    = Column(Text, nullable=True)  # JSON
    after_value     = Column(Text, nullable=True)  # JSON
    performed_at    = Column(DateTime, default=datetime.utcnow)

    performed_by = relationship("SystemUser")

    def __repr__(self):
        return f"<AuditLog {self.action} at {self.performed_at}>"


# ─────────────────────────────────────────────
# 10. SystemUser — Admin and HR Officer only
# ─────────────────────────────────────────────
class SystemUser(Base):
    """
    Only two roles: admin and hr_officer.
    Employees do NOT have system accounts — they are data subjects only.
    language preference is per-session, not stored here.
    """
    __tablename__ = "system_user"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(
        Enum("admin", "hr_officer", name="role_enum"),
        nullable=False
    )
    full_name     = Column(String(255), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<SystemUser {self.username} ({self.role})>"