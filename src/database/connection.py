"""
Database connection, session management, seeding, and core business logic.

Business logic included here:
- verify_login
- generate_employee_id
- generate_commendation_ref
- generate_sanction_ref
- calculate_promotion_months_remaining (LIVE calculation - never stored)
- get_salary_increment_due_employees
- log_action (audit trail)
"""

import os
import json
import calendar
from datetime import datetime, date
from hashlib import sha256
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.i18n import t
from src.database.models import (
    Base, SystemUser, Title, PromotionRule, Employee, OrgUnit,
    Commendation, CommendationEmployee, Sanction,
    PromotionHistory, SalaryIncrementHistory, AuditLog
)

# Database path
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_PATH   = os.path.join(_BASE_DIR, "myhr.db")
DB_URL    = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine       = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

OTHER_TITLE_NAME = "Other"
OTHER_ORG_UNIT_NAME = "OTHERS"


# Initialization and seed data
def init_db():
    """Create all tables and seed default data on first run."""
    Base.metadata.create_all(engine)
    _migrate_schema()
    with SessionLocal() as session:
        _seed_defaults(session)


def _migrate_schema():
    """Apply small SQLite migrations that create_all cannot add to existing DBs."""
    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(audit_log)").fetchall()
        }
        if "performed_by_username" not in columns:
            conn.exec_driver_sql("ALTER TABLE audit_log ADD COLUMN performed_by_username VARCHAR(100)")
        if "performed_by_name" not in columns:
            conn.exec_driver_sql("ALTER TABLE audit_log ADD COLUMN performed_by_name VARCHAR(255)")
        conn.exec_driver_sql(
            """
            UPDATE audit_log
            SET performed_by_username = (
                SELECT username FROM system_user WHERE system_user.id = audit_log.performed_by_id
            )
            WHERE performed_by_id IS NOT NULL
              AND (performed_by_username IS NULL OR performed_by_username = '')
            """
        )
        conn.exec_driver_sql(
            """
            UPDATE audit_log
            SET performed_by_name = (
                SELECT full_name FROM system_user WHERE system_user.id = audit_log.performed_by_id
            )
            WHERE performed_by_id IS NOT NULL
              AND (performed_by_name IS NULL OR performed_by_name = '')
            """
        )


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
        {"name": "L2", "label": "Board Member",     "degree_requirement": "any", "base_salary_min": 9000, "base_salary_max": 13000, "annual_increment_value": 4.0,  "promotion_salary_increase_pct": 30.0},
        {"name": "L1", "label": "CEO / Executive",  "degree_requirement": "any", "base_salary_min": 13000, "base_salary_max": 20000, "annual_increment_value": 4.0,  "promotion_salary_increase_pct": 35.0},
        {"name": OTHER_TITLE_NAME, "label": "Miscellaneous Employees", "degree_requirement": "any", "base_salary_min": 2000, "base_salary_max": 2800, "annual_increment_value": 3.0, "promotion_salary_increase_pct": 0.0},
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
        {"from": "L3", "to": "L2", "base_months": 72},
        {"from": "L2", "to": "L1", "base_months": 84},
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


# Authentication
class UserSession:
    """
    Plain Python object holding logged-in user data.
    Avoids SQLAlchemy DetachedInstanceError - no session dependency.
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


# ID generators
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


# Promotion race calculation (LIVE - never stored)
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
    if is_other_employee(employee):
        return {
            "has_next_level": False,
            "months_remaining": None,
            "base_months": None,
            "months_elapsed": _months_between(employee.join_date, datetime.utcnow()) if employee.join_date else 0,
            "commendation_reduction": 0,
            "sanction_addition": 0,
            "eligible": False,
            "next_title_id": None,
            "progress_pct": 0,
        }

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
    months_elapsed = _months_between(race_start, now)

    # Commendation reduction - commendations since race start
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

    # Sanction addition - active sanctions since race start
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
        "progress_pct": max(0, min(100, int((months_elapsed + commendation_reduction - sanction_addition) / rule.base_months * 100))),
    }


def get_race_start(employee: Employee, session: Session) -> datetime:
    """Return the date from which the current role race started."""
    last_promo = session.query(PromotionHistory).filter_by(
        employee_id=employee.id
    ).order_by(PromotionHistory.promoted_at.desc()).first()
    return last_promo.promoted_at if last_promo else employee.join_date


def calculate_sub_race(employee: Employee, session: Session) -> dict:
    """
    Build yearly sub-race milestones for the employee profile.
    Standard employees get L7.1/L7.2 style checkpoints before the next level.
    Other/Misc employees get ongoing Other.1/Other.2 service checkpoints.
    """
    race_start = get_race_start(employee, session)
    today = datetime.utcnow()
    months_elapsed = _months_between(race_start, today) if race_start else 0
    current_title = employee.title.name if employee.title else OTHER_TITLE_NAME
    title = employee.title
    increment_label = _increment_label(title)

    if is_other_employee(employee):
        completed_years = max(0, months_elapsed // 12)
        visible_years = max(1, completed_years + 1)
        steps = []
        for year in range(1, visible_years + 1):
            due_date = _add_months(race_start, year * 12) if race_start else None
            steps.append({
                "label": f"{OTHER_TITLE_NAME}.{year}",
                "kind": "annual_increment",
                "completed": bool(due_date and due_date <= today),
                "due_date": due_date,
                "increment": increment_label,
            })
        return {
            "is_other_track": True,
            "current_title": OTHER_TITLE_NAME,
            "next_title": None,
            "race_start": race_start,
            "expected_promotion_date": None,
            "months_left": None,
            "progress_pct": 0,
            "steps": steps,
            "current_step_label": steps[completed_years - 1]["label"] if completed_years > 0 and completed_years <= len(steps) else OTHER_TITLE_NAME,
        }

    race = calculate_months_remaining(employee, session)
    if not race["has_next_level"]:
        return {
            "is_other_track": False,
            "current_title": current_title,
            "next_title": None,
            "race_start": race_start,
            "expected_promotion_date": None,
            "months_left": None,
            "progress_pct": 0,
            "steps": [],
            "current_step_label": current_title,
        }

    next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
    effective_months = max(1, race["base_months"] - race["commendation_reduction"] + race["sanction_addition"])
    expected_date = _add_months(race_start, effective_months)
    annual_checkpoints = max(0, (effective_months - 1) // 12)
    steps = []
    for year in range(1, annual_checkpoints + 1):
        due_date = _add_months(race_start, year * 12)
        steps.append({
            "label": f"{current_title}.{year}",
            "kind": "annual_increment",
            "completed": due_date <= today,
            "due_date": due_date,
            "increment": increment_label,
        })
    steps.append({
        "label": next_title.name if next_title else "-",
        "kind": "promotion",
        "completed": bool(expected_date and expected_date <= today),
        "due_date": expected_date,
        "increment": f"+{next_title.promotion_salary_increase_pct:.1f}%" if next_title else "",
    })
    completed_regular_steps = [step["label"] for step in steps if step["kind"] == "annual_increment" and step["completed"]]
    return {
        "is_other_track": False,
        "current_title": current_title,
        "next_title": next_title.name if next_title else None,
        "race_start": race_start,
        "expected_promotion_date": expected_date,
        "months_left": race["months_remaining"],
        "progress_pct": race["progress_pct"],
        "steps": steps,
        "current_step_label": completed_regular_steps[-1] if completed_regular_steps else current_title,
    }


# Commendation cap checks
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


# Annual salary increment
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

    sub_race = calculate_sub_race(employee, session)
    milestone_note = f"Sub-race milestone {sub_race['current_step_label']}"
    record = SalaryIncrementHistory(
        employee_id=employee_id,
        approved_by_id=approved_by_id,
        salary_before=salary_before,
        salary_after=salary_after,
        increment_type=title.annual_increment_type,
        increment_value=title.annual_increment_value,
        notes=f"{milestone_note}. {notes}".strip(),
    )
    session.add(record)

    log_action(
        session=session,
        performed_by_id=approved_by_id,
        action="salary_increment.apply",
        target_table="employee",
        target_id=employee_id,
        description=f"Annual salary increment applied: {salary_before} to {salary_after}",
        before_value=json.dumps({"base_salary": salary_before}),
        after_value=json.dumps({"base_salary": salary_after}),
    )

    session.commit()
    return {"success": True, "salary_before": salary_before, "salary_after": salary_after}


# Audit log helper
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
    performed_by_username = None
    performed_by_name = None
    if performed_by_id:
        user = session.query(SystemUser).filter_by(id=performed_by_id).first()
        if user:
            performed_by_username = user.username
            performed_by_name = user.full_name
    entry = AuditLog(
        performed_by_id=performed_by_id,
        performed_by_username=performed_by_username,
        performed_by_name=performed_by_name,
        action=action,
        target_table=target_table,
        target_id=target_id,
        description=description,
        before_value=before_value,
        after_value=after_value,
    )
    session.add(entry)


# Utility
def _hash(password: str) -> str:
    return sha256(password.encode()).hexdigest()


def degree_to_title_name(degree: str) -> str:
    """Maps employee degree to starting title."""
    return {"PhD": "L5", "MSc": "L6", "BSc": "L7", "Other": OTHER_TITLE_NAME}.get(degree, "L7")


def is_other_title(title: Title) -> bool:
    return bool(title and title.name == OTHER_TITLE_NAME)


def is_other_employee(employee: Employee) -> bool:
    return bool(employee and (employee.degree == "Other" or is_other_title(employee.title)))


def display_title_name(title: Title) -> str:
    return OTHER_TITLE_NAME if is_other_title(title) else (title.name if title else "-")


def ensure_others_org_unit(session: Session) -> OrgUnit:
    """Create or return the special OTHERS branch used by Other/Misc employees."""
    unit = session.query(OrgUnit).filter(OrgUnit.name == OTHER_ORG_UNIT_NAME).first()
    organization = session.query(OrgUnit).filter_by(unit_type="organization").first()
    if unit:
        if organization and unit.parent_id != organization.id:
            unit.parent_id = organization.id
        return unit
    unit = OrgUnit(
        name=OTHER_ORG_UNIT_NAME,
        unit_type="division",
        parent_id=organization.id if organization else None,
    )
    session.add(unit)
    session.flush()
    return unit


def valid_other_manager_ids(session: Session) -> set:
    ids = set()
    others = ensure_others_org_unit(session)
    if others.head_employee_id:
        ids.add(others.head_employee_id)
    for organization in session.query(OrgUnit).filter_by(unit_type="organization").all():
        if organization.head_employee_id:
            ids.add(organization.head_employee_id)
    for employee in session.query(Employee).filter(Employee.status == "active").all():
        position = (employee.position or "").lower()
        if "other employees head" in position or "ceo" in position:
            ids.add(employee.id)
    return ids


def validate_salary_for_title(title: Title, salary: float) -> tuple[bool, str]:
    if not title:
        return False, t("title_not_found")
    if salary < title.base_salary_min or salary > title.base_salary_max:
        return (
            False,
            t(
                "salary_range_warning",
                level=display_title_name(title),
                min_salary=f"{title.base_salary_min:,.0f}",
                max_salary=f"{title.base_salary_max:,.0f}",
                currency=title.currency or "EUR",
            )
        )
    return True, ""


def _months_between(start: datetime, end: datetime) -> int:
    if not start or not end:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def _add_months(start: datetime, months: int) -> datetime:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _increment_label(title: Title) -> str:
    if not title:
        return ""
    if title.annual_increment_type == "fixed":
        return f"+{title.annual_increment_value:,.0f} {title.currency or 'EUR'}"
    return f"+{title.annual_increment_value:.1f}%"
