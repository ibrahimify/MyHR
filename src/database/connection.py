"""
Database connection, session management, seeding, and core business logic.

Business logic included here:
- verify_login
- generate_employee_id
- generate_commendation_ref
- generate_sanction_ref
- calculate_promotion_months_remaining (LIVE calculation — never stored)
- get_salary_increment_due_employees
- log_action (audit trail)
"""

import os
import json
from datetime import datetime, date
from hashlib import sha256
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import (
    Base, SystemUser, Title, PromotionRule, Employee,
    Commendation, CommendationEmployee, Sanction,
    PromotionHistory, SalaryIncrementHistory, AuditLog
)

# ── DB path ──────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_PATH   = os.path.join(_BASE_DIR, "myhr.db")
DB_URL    = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine       = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


# ── Init + seed ───────────────────────────────────────────────────────────────
def init_db():
    """Create all tables and seed default data on first run."""
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        _seed_defaults(session)


def _seed_defaults(session: Session):
    """Seed default admin, HR officer, salary levels, and promotion rules."""

    # Default users
    if not session.query(SystemUser).filter_by(username="admin").first():
        session.add(SystemUser(
            username="admin",
            password_hash=_hash("admin123"),
            role="admin",
            full_name="System Administrator",
        ))
    if not session.query(SystemUser).filter_by(username="hr_officer").first():
        session.add(SystemUser(
            username="hr_officer",
            password_hash=_hash("hr123"),
            role="hr_officer",
            full_name="HR Officer",
        ))
    session.flush()

    # Default salary levels
    defaults = [
        {"name": "L7", "label": "Entry Level",      "degree_requirement": "BSc", "base_salary_min": 2000, "base_salary_max": 2800, "annual_increment_value": 3.0,  "promotion_salary_increase_pct": 15.0},
        {"name": "L6", "label": "Mid Level",        "degree_requirement": "MSc", "base_salary_min": 2800, "base_salary_max": 3500, "annual_increment_value": 3.0,  "promotion_salary_increase_pct": 20.0},
        {"name": "L5", "label": "Senior Level",     "degree_requirement": "PhD", "base_salary_min": 3500, "base_salary_max": 4500, "annual_increment_value": 3.5,  "promotion_salary_increase_pct": 25.0},
        {"name": "L4", "label": "Management Level", "degree_requirement": "any", "base_salary_min": 4500, "base_salary_max": 6000, "annual_increment_value": 4.0,  "promotion_salary_increase_pct": 25.0},
        {"name": "L3", "label": "Director Level",   "degree_requirement": "any", "base_salary_min": 6000, "base_salary_max": 9000, "annual_increment_value": 4.0,  "promotion_salary_increase_pct": 30.0},
    ]
    titles = {}
    for d in defaults:
        existing = session.query(Title).filter_by(name=d["name"]).first()
        if not existing:
            obj = Title(**d)
            session.add(obj)
            session.flush()
            titles[d["name"]] = obj
        else:
            titles[d["name"]] = existing

    # Default promotion rules (base_months = race track duration)
    rules = [
        {"from": "L7", "to": "L6", "base_months": 36},
        {"from": "L6", "to": "L5", "base_months": 48},
        {"from": "L5", "to": "L4", "base_months": 60},
        {"from": "L4", "to": "L3", "base_months": 60},
    ]
    for r in rules:
        ft = titles.get(r["from"])
        tt = titles.get(r["to"])
        if ft and tt:
            exists = session.query(PromotionRule).filter_by(
                from_title_id=ft.id, to_title_id=tt.id
            ).first()
            if not exists:
                session.add(PromotionRule(
                    from_title_id=ft.id,
                    to_title_id=tt.id,
                    base_months=r["base_months"],
                ))

    session.commit()


def get_session() -> Session:
    return SessionLocal()


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserSession:
    """
    Plain Python object holding logged-in user data.
    Avoids SQLAlchemy DetachedInstanceError — no session dependency.
    """
    def __init__(self, id, username, full_name, role):
        self.id        = id
        self.username  = username
        self.full_name = full_name
        self.role      = role


def verify_login(username: str, password: str):
    """Returns UserSession if valid credentials, else None."""
    hashed = _hash(password)
    with SessionLocal() as session:
        user = session.query(SystemUser).filter_by(
            username=username,
            password_hash=hashed,
            is_active=True
        ).first()
        if user:
            user.last_login = datetime.utcnow()
            session.commit()
            return UserSession(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
            )
        return None


# ── ID generators ─────────────────────────────────────────────────────────────
def generate_employee_id(session: Session) -> str:
    """Generates next sequential EMP-XXXX ID."""
    last = session.query(Employee).order_by(Employee.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    return f"EMP-{next_num:04d}"


def generate_commendation_ref(session: Session) -> str:
    """Generates COM-YYYY-MMDD-NNN format."""
    today = datetime.utcnow()
    prefix = f"COM-{today.year}-{today.month:02d}{today.day:02d}"
    count = session.query(Commendation).filter(
        Commendation.commendation_ref.like(f"{prefix}%")
    ).count()
    return f"{prefix}-{count + 1:03d}"


def generate_sanction_ref(session: Session) -> str:
    """Generates SAN-YYYY-MMDD-NNN format."""
    today = datetime.utcnow()
    prefix = f"SAN-{today.year}-{today.month:02d}{today.day:02d}"
    count = session.query(Sanction).filter(
        Sanction.sanction_ref.like(f"{prefix}%")
    ).count()
    return f"{prefix}-{count + 1:03d}"


# ── Promotion race calculation (LIVE — never stored) ──────────────────────────
def calculate_months_remaining(employee: Employee, session: Session) -> dict:
    """
    Calculates the employee's current position in the promotion race.
    
    Formula:
      months_elapsed = months since last promotion (or join date)
      commendation_reduction = sum of months_impact for all commendations in current role
      sanction_addition = sum of delay_months for all active sanctions
      months_remaining = base_months - months_elapsed - commendation_reduction + sanction_addition
      floor at 0.
    
    Returns dict with full breakdown for UI display.
    """
    # Get promotion rule for current title
    rule = session.query(PromotionRule).filter_by(
        from_title_id=employee.title_id,
        is_active=True
    ).first()

    if not rule:
        return {
            "has_next_level": False,
            "months_remaining": None,
            "base_months": None,
            "months_elapsed": None,
            "commendation_reduction": 0,
            "sanction_addition": 0,
            "eligible": False,
            "next_title_id": None,
        }

    # Start date = last promotion date or join date
    last_promo = session.query(PromotionHistory).filter_by(
        employee_id=employee.id
    ).order_by(PromotionHistory.promoted_at.desc()).first()

    race_start = last_promo.promoted_at if last_promo else employee.join_date
    now = datetime.utcnow()

    # Months elapsed since race start
    months_elapsed = (
        (now.year - race_start.year) * 12 +
        (now.month - race_start.month)
    )

    # Commendation reduction — commendations since race start
    # Using simpler subquery approach to avoid JOIN issues
    comm_links = session.query(CommendationEmployee).filter_by(
        employee_id=employee.id
    ).all()
    comm_ids = [cl.commendation_id for cl in comm_links]

    commendations = []
    if comm_ids:
        commendations = session.query(Commendation).filter(
            Commendation.id.in_(comm_ids),
            Commendation.issued_at >= race_start
        ).all()

    commendation_reduction = sum(abs(c.months_impact) for c in commendations)

    # Sanction addition — active sanctions since race start
    sanctions = session.query(Sanction).filter(
        Sanction.employee_id == employee.id,
        Sanction.is_resolved == False,
        Sanction.issued_at >= race_start
    ).all()

    sanction_addition = sum(s.delay_months for s in sanctions)

    # Final calculation
    raw_remaining = rule.base_months - months_elapsed - commendation_reduction + sanction_addition
    months_remaining = max(0, raw_remaining)  # floor at 0

    return {
        "has_next_level": True,
        "months_remaining": months_remaining,
        "base_months": rule.base_months,
        "months_elapsed": months_elapsed,
        "commendation_reduction": commendation_reduction,
        "sanction_addition": sanction_addition,
        "eligible": months_remaining == 0,
        "next_title_id": rule.to_title_id,
        "progress_pct": min(100, int((months_elapsed + commendation_reduction - sanction_addition) / rule.base_months * 100)),
    }


# ── Commendation cap check ─────────────────────────────────────────────────────
def count_commendations_in_current_role(employee: Employee, session: Session) -> int:
    """
    Returns count of commendations for this employee since their last promotion.
    Used to enforce max 3 per role.
    """
    last_promo = session.query(PromotionHistory).filter_by(
        employee_id=employee.id
    ).order_by(PromotionHistory.promoted_at.desc()).first()

    race_start = last_promo.promoted_at if last_promo else employee.join_date

    comm_links = session.query(CommendationEmployee).filter_by(
        employee_id=employee.id
    ).all()
    comm_ids = [cl.commendation_id for cl in comm_links]
    if not comm_ids:
        return 0
    return session.query(Commendation).filter(
        Commendation.id.in_(comm_ids),
        Commendation.issued_at >= race_start
    ).count()


def can_receive_commendation(employee: Employee, session: Session) -> bool:
    """Returns True if employee has fewer than 3 commendations in current role."""
    return count_commendations_in_current_role(employee, session) < 3


# ── Annual salary increment ────────────────────────────────────────────────────
def get_increment_due_employees(session: Session) -> list:
    """
    Returns list of employees due for annual salary increment.
    Eligibility: employee's join anniversary has passed and no increment
    was applied in the current anniversary year.
    """
    today = datetime.utcnow()
    due = []

    employees = session.query(Employee).filter_by(status="active").all()
    for emp in employees:
        if not emp.join_date:
            continue

        # Check if anniversary has passed this year
        try:
            anniversary_this_year = emp.join_date.replace(year=today.year)
        except ValueError:
            # Feb 29 edge case
            anniversary_this_year = emp.join_date.replace(year=today.year, day=28)

        if anniversary_this_year > today:
            continue  # anniversary not yet reached this year

        # Check if increment already applied this anniversary year
        last_applied = emp.annual_increment_last_applied
        if last_applied and last_applied.year == today.year and last_applied >= anniversary_this_year:
            continue  # already done this year

        due.append(emp)

    return due


def apply_salary_increment(employee_id: int, approved_by_id: int, session: Session, notes: str = "") -> dict:
    """
    Applies the annual salary increment for one employee.
    Reads increment config from the employee's current Title.
    Returns result dict with before/after salary.
    """
    employee = session.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        return {"success": False, "error": "Employee not found"}

    title = session.query(Title).filter_by(id=employee.title_id).first()
    if not title:
        return {"success": False, "error": "Title not found"}

    salary_before = employee.base_salary

    if title.annual_increment_type == "percentage":
        salary_after = round(salary_before * (1 + title.annual_increment_value / 100), 2)
    else:
        salary_after = round(salary_before + title.annual_increment_value, 2)

    employee.base_salary = salary_after
    employee.annual_increment_last_applied = datetime.utcnow()

    record = SalaryIncrementHistory(
        employee_id=employee_id,
        approved_by_id=approved_by_id,
        salary_before=salary_before,
        salary_after=salary_after,
        increment_type=title.annual_increment_type,
        increment_value=title.annual_increment_value,
        notes=notes,
    )
    session.add(record)

    log_action(
        session=session,
        performed_by_id=approved_by_id,
        action="salary_increment.apply",
        target_table="employee",
        target_id=employee_id,
        description=f"Annual salary increment applied: {salary_before} → {salary_after}",
        before_value=json.dumps({"base_salary": salary_before}),
        after_value=json.dumps({"base_salary": salary_after}),
    )

    session.commit()
    return {"success": True, "salary_before": salary_before, "salary_after": salary_after}


# ── Audit log helper ──────────────────────────────────────────────────────────
def log_action(
    session: Session,
    action: str,
    performed_by_id: int = None,
    target_table: str = None,
    target_id: int = None,
    description: str = None,
    before_value: str = None,
    after_value: str = None,
):
    """Call this whenever any admin/HR action happens."""
    entry = AuditLog(
        performed_by_id=performed_by_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        description=description,
        before_value=before_value,
        after_value=after_value,
    )
    session.add(entry)


# ── Utility ───────────────────────────────────────────────────────────────────
def _hash(password: str) -> str:
    return sha256(password.encode()).hexdigest()


def degree_to_title_name(degree: str) -> str:
    """Maps employee degree to starting title."""
    return {"PhD": "L5", "MSc": "L6", "BSc": "L7"}.get(degree, "L7")