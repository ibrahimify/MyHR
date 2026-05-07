"""
Reset myhr.db and seed a realistic 300-person software company dataset.

Run from the repository root:
    python scripts/seed_demo_company.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from random import Random
import re
import sys
import warnings


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.connection import (  # noqa: E402
    SessionLocal, engine, _seed_defaults, generate_commendation_ref,
    generate_sanction_ref, log_action
)
from src.database.models import (  # noqa: E402
    Base, AuditLog, Commendation, CommendationEmployee, Employee,
    OrgUnit, PromotionHistory, SalaryIncrementHistory, Sanction,
    SystemUser, Title
)
from sqlalchemy.exc import SAWarning  # noqa: E402


warnings.filterwarnings(
    "ignore",
    message="Can't sort tables for DROP.*",
    category=SAWarning,
)


TODAY = datetime(2026, 5, 8, 9, 0, 0)
RNG = Random(8808)

FIRST_NAMES = [
    "Adam", "Aisha", "Alex", "Amelia", "Andrew", "Anna", "Arjun", "Bianca",
    "Bence", "Carlos", "Chloe", "Daniel", "David", "Diana", "Elena", "Emily",
    "Eva", "Fatima", "Gabriel", "Grace", "Hanna", "Hiro", "Ibrahim", "Iris",
    "James", "Jana", "Jonas", "Julia", "Katalin", "Kevin", "Laura", "Leila",
    "Lena", "Liam", "Luca", "Maja", "Maria", "Mark", "Mate", "Maya",
    "Michael", "Mina", "Nadia", "Nora", "Oliver", "Omar", "Peter", "Priya",
    "Robert", "Sara", "Sofia", "Tamas", "Tom", "Victor", "Yasmin", "Zoe",
]

LAST_NAMES = [
    "Ahmed", "Anderson", "Balogh", "Brown", "Chen", "Davis", "Farkas",
    "Garcia", "Hassan", "Honti", "Horvath", "Ibrahim", "Johnson", "Khan",
    "Kiss", "Kovac", "Kovacs", "Lee", "Martinez", "Miller", "Nagy",
    "Nemeth", "Novak", "Patel", "Pop", "Rossi", "Schmidt", "Smith",
    "Szabo", "Toth", "Varga", "Wilson", "Yilmaz", "Zhang",
]

ORG_TREE = {
    "Engineering": {
        "Backend Department": {
            "API Unit": ["Payments Team", "Auth Team"],
            "Platform Unit": ["Microservices Team", "Integration Team"],
        },
        "Frontend Department": {
            "Web Unit": ["Dashboard Team", "Client Portal Team"],
            "Mobile Unit": ["Android Team", "iOS Team"],
        },
        "DevOps Department": {
            "Cloud Operations Unit": ["AWS Team", "Monitoring Team"],
            "Release Engineering Unit": ["CI CD Team", "Build Tools Team"],
        },
    },
    "Product and Design": {
        "Product Management Department": {
            "SaaS Product Unit": ["Core Platform PM Team", "Growth PM Team"],
            "Enterprise Solutions Unit": ["Enterprise PM Team", "Partner PM Team"],
        },
        "UX UI Department": {
            "Research Unit": ["User Research Team"],
            "Design System Unit": ["Design System Team", "Product Design Team"],
        },
    },
    "Quality Assurance": {
        "Manual QA Department": {
            "Functional QA Unit": ["Web QA Team", "Mobile QA Team"],
        },
        "Automation QA Department": {
            "Automation Unit": ["Regression Team", "E2E Testing Team"],
            "Performance Unit": ["Load Testing Team"],
        },
    },
    "IT and Infrastructure": {
        "Corporate IT Department": {
            "Workplace Services Unit": ["Helpdesk Team", "Device Management Team"],
            "Systems Unit": ["Identity Team", "Network Team"],
        },
    },
    "Cybersecurity and Compliance": {
        "Security Operations Department": {
            "SOC Unit": ["Security Operations Team", "Incident Response Team"],
        },
        "Compliance Department": {
            "GRC Unit": ["Governance Risk Compliance Team"],
            "Privacy Unit": ["Data Protection Team"],
        },
    },
    "Data and AI": {
        "Data Engineering Department": {
            "Data Platform Unit": ["Pipelines Team", "Warehouse Team"],
        },
        "AI Department": {
            "Machine Learning Unit": ["ML Engineering Team", "Applied AI Team"],
            "Analytics Unit": ["BI Analytics Team"],
        },
    },
    "Sales and Marketing": {
        "Sales Department": {
            "Enterprise Sales Unit": ["Enterprise Account Team", "Sales Engineering Team"],
            "SMB Sales Unit": ["Inside Sales Team"],
        },
        "Marketing Department": {
            "Demand Generation Unit": ["Campaigns Team", "Content Team"],
        },
    },
    "Customer Success and Support": {
        "Customer Success Department": {
            "Account Management Unit": ["Customer Success Managers", "Renewals Team"],
        },
        "Support Department": {
            "Technical Support Unit": ["Tier 1 Support Team", "Tier 2 Support Team"],
        },
    },
    "Finance and Procurement": {
        "Finance Department": {
            "Accounting Unit": ["Accounting Team"],
            "Planning Unit": ["FP and A Team"],
        },
        "Procurement Department": {
            "Vendor Management Unit": ["Procurement Team"],
        },
    },
    "Human Resources": {
        "People Operations Department": {
            "Recruitment Unit": ["Recruitment Team"],
            "Payroll Unit": ["Payroll and Benefits Team"],
        },
        "Learning Department": {
            "Development Unit": ["Learning and Development Team"],
        },
    },
    "Legal and Administration": {
        "Legal Department": {
            "Contracts Unit": ["Commercial Legal Team"],
            "Administration Unit": ["Office Administration Team"],
        },
    },
    "Executive Office": {
        "Executive Office Department": {
            "Leadership Unit": ["Executive Leadership Team"],
            "Operations Unit": ["Executive Operations Team"],
        },
    },
}

DIVISION_HEAD_ROLES = {
    "Engineering": ("VP Engineering", "L3"),
    "Product and Design": ("VP Product", "L3"),
    "Quality Assurance": ("Director of Quality", "L3"),
    "IT and Infrastructure": ("Director of IT", "L3"),
    "Cybersecurity and Compliance": ("Director of Security", "L3"),
    "Data and AI": ("Director of Data and AI", "L3"),
    "Sales and Marketing": ("VP Sales and Marketing", "L3"),
    "Customer Success and Support": ("Director of Customer Success", "L3"),
    "Finance and Procurement": ("Finance Director", "L3"),
    "Human Resources": ("Director of HR", "L3"),
    "Legal and Administration": ("Legal and Administration Director", "L3"),
}

DEPARTMENT_MANAGER_ROLES = {
    "Engineering": "Engineering Manager",
    "Product and Design": "Product Manager",
    "Quality Assurance": "QA Manager",
    "IT and Infrastructure": "IT Manager",
    "Cybersecurity and Compliance": "Security Manager",
    "Data and AI": "Data Engineering Manager",
    "Sales and Marketing": "Sales Manager",
    "Customer Success and Support": "Customer Success Manager",
    "Finance and Procurement": "Finance Manager",
    "Human Resources": "HR Manager",
    "Legal and Administration": "Operations Manager",
    "Executive Office": "Executive Operations Manager",
}

ROLE_POOLS = {
    "Engineering": [
        ("Senior Software Engineer", "L5"), ("Software Engineer II", "L6"),
        ("Software Engineer I", "L7"), ("Junior Developer", "L7"),
        ("Principal Engineer", "L5"), ("Scrum Master", "L5"),
    ],
    "Product and Design": [
        ("Product Manager", "L5"), ("Associate Product Manager", "L7"),
        ("UI UX Designer", "L6"), ("Senior UI UX Designer", "L5"),
        ("Product Analyst", "L6"),
    ],
    "Quality Assurance": [
        ("QA Engineer", "L6"), ("Senior QA Engineer", "L5"),
        ("Automation QA Engineer", "L6"), ("Associate QA Engineer", "L7"),
    ],
    "IT and Infrastructure": [
        ("System Administrator", "L6"), ("IT Support Technician", "L7"),
        ("Senior DevOps Engineer", "L5"), ("Network Administrator", "L6"),
    ],
    "Cybersecurity and Compliance": [
        ("Security Analyst", "L6"), ("Senior Security Analyst", "L5"),
        ("Compliance Specialist", "L6"), ("GRC Analyst", "L6"),
    ],
    "Data and AI": [
        ("Data Engineer", "L6"), ("Senior Data Engineer", "L5"),
        ("Machine Learning Engineer", "L6"), ("Data Analyst", "L6"),
        ("BI Analyst", "L7"),
    ],
    "Sales and Marketing": [
        ("Account Executive", "L6"), ("Sales Development Representative", "L7"),
        ("Marketing Specialist", "L7"), ("Content Strategist", "L6"),
        ("Sales Engineer", "L5"),
    ],
    "Customer Success and Support": [
        ("Customer Success Manager", "L6"), ("Support Associate", "L7"),
        ("Technical Support Engineer", "L6"), ("Renewals Specialist", "L6"),
    ],
    "Finance and Procurement": [
        ("Financial Analyst", "L6"), ("Accountant", "L6"),
        ("Procurement Specialist", "L6"), ("Finance Coordinator", "L7"),
    ],
    "Human Resources": [
        ("HR Business Partner", "L6"), ("Recruiter", "L6"),
        ("HR Coordinator", "L7"), ("Learning Specialist", "L6"),
    ],
    "Legal and Administration": [
        ("Legal Counsel", "L5"), ("Contract Specialist", "L6"),
        ("Office Administrator", "L7"), ("Administrative Coordinator", "L7"),
    ],
    "Executive Office": [
        ("Executive Assistant", "L6"), ("Business Operations Analyst", "L6"),
        ("Office Assistant", "L7"),
    ],
}

SANCTION_REASON_BY_TYPE = {
    "verbal_warning": [
        "Repeated missed standup attendance",
        "Late submission of internal documentation",
        "Minor breach of ticket update procedure",
    ],
    "written_warning": [
        "Repeated late delivery of assigned sprint work",
        "Unprofessional conduct during project handover",
        "Ignored documented change management process",
    ],
    "suspension": [
        "Serious violation of security handling procedure",
        "Unauthorized access attempt on a restricted system",
    ],
    "final_warning": [
        "Severe repeated misconduct after prior warnings",
        "Critical breach of company policy",
    ],
}

AWARD_TITLES = [
    "Project Excellence Award",
    "Customer Impact Award",
    "Innovation Award",
    "Reliability Champion",
    "Security Mindset Award",
    "Team Collaboration Award",
    "Mentorship Recognition",
    "Operational Excellence Award",
]


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        _seed_defaults(session)
        titles = {title.name: title for title in session.query(Title).all()}
        admin = session.query(SystemUser).filter_by(username="admin").first()
        hr = session.query(SystemUser).filter_by(username="hr_officer").first()

        units = seed_org_units(session)
        employees = seed_employees(session, titles, units)
        seed_promotions(session, employees, titles, admin.id)
        seed_salary_increments(session, employees, admin.id)
        seed_commendations(session, employees, admin.id, hr.id)
        seed_sanctions(session, employees, admin.id, hr.id)
        seed_audit_log(session, employees, admin.id, hr.id)

        session.commit()

        print("Demo database seeded successfully.")
        print(f"Employees: {session.query(Employee).count()}")
        print(f"Org units: {session.query(OrgUnit).count()}")
        print(f"Promotions: {session.query(PromotionHistory).count()}")
        print(f"Commendations: {session.query(Commendation).count()}")
        print(f"Sanctions: {session.query(Sanction).count()}")
        print(f"Audit logs: {session.query(AuditLog).count()}")


def seed_org_units(session):
    company = OrgUnit(name="NexaSoft Technologies", unit_type="organization")
    session.add(company)
    session.flush()

    units = {
        "company": company,
        "divisions": {},
        "departments": {},
        "units": {},
        "teams": {},
        "leaves": [],
    }

    for division_name, departments in ORG_TREE.items():
        division = OrgUnit(name=division_name, unit_type="division", parent_id=company.id)
        session.add(division)
        session.flush()
        units["divisions"][division_name] = division

        for department_name, unit_map in departments.items():
            department = OrgUnit(
                name=department_name,
                unit_type="department",
                parent_id=division.id,
            )
            session.add(department)
            session.flush()
            units["departments"][(division_name, department_name)] = department

            for unit_name, team_names in unit_map.items():
                unit = OrgUnit(name=unit_name, unit_type="unit", parent_id=department.id)
                session.add(unit)
                session.flush()
                units["units"][(division_name, department_name, unit_name)] = unit

                for team_name in team_names:
                    team = OrgUnit(name=team_name, unit_type="team", parent_id=unit.id)
                    session.add(team)
                    session.flush()
                    units["teams"][(division_name, department_name, unit_name, team_name)] = team
                    units["leaves"].append({
                        "division": division_name,
                        "department": department_name,
                        "unit": unit_name,
                        "team": team_name,
                        "org": team,
                    })

    return units


def seed_employees(session, titles, units):
    employees = []
    employee_by_division = {}
    division_heads = {}
    department_heads = {}
    team_heads = {}

    def add_employee(position, title_name, org, manager=None, division=None,
                     first_name=None, last_name=None, join_date=None):
        index = len(employees) + 1
        first, last = (first_name, last_name) if first_name else next_name(index)
        title = titles[title_name]
        degree = degree_for_title(title_name)
        salary = salary_for_title(title)
        join = join_date or join_date_for_title(title_name)
        employee = Employee(
            employee_id=f"EMP-{index:04d}",
            first_name=first,
            last_name=last,
            degree=degree,
            phone=f"+36 30 {100 + index:03d} {200 + index:03d}",
            personal_email=f"{slug(first)}.{slug(last)}.{index}@personal.example",
            address=RNG.choice(["Budapest", "Szeged", "Debrecen", "Gyor", "Pecs"]),
            work_email=f"{slug(first)}.{slug(last)}.{index}@nexasoft.example",
            work_phone=f"+36 20 {300 + index:03d} {400 + index:03d}",
            position=position,
            join_date=join,
            base_salary=salary,
            status="active" if RNG.random() > 0.04 else "on_leave",
            title_id=title.id,
            org_unit_id=org.id,
            reports_to_id=manager.id if manager else None,
        )
        session.add(employee)
        session.flush()
        employees.append(employee)
        if division:
            employee_by_division.setdefault(division, []).append(employee)
        return employee

    executive_team = units["teams"][(
        "Executive Office", "Executive Office Department",
        "Leadership Unit", "Executive Leadership Team"
    )]
    ceo = add_employee("CEO", "L1", executive_team, first_name="Anna", last_name="Kovacs",
                       join_date=TODAY - timedelta(days=365 * 10))
    executive_team.head_employee_id = ceo.id
    units["company"].head_employee_id = ceo.id

    exec_roles = [
        ("CTO", "L2", "Peter", "Nagy"),
        ("COO", "L2", "Sarah", "Johnson"),
        ("CFO", "L2", "Michael", "Brown"),
        ("CHRO", "L2", "Nora", "Szabo"),
    ]
    executives = {"CEO": ceo}
    for role, title_name, first, last in exec_roles:
        executives[role] = add_employee(
            role, title_name, executive_team, manager=ceo,
            first_name=first, last_name=last,
            join_date=TODAY - timedelta(days=RNG.randint(365 * 5, 365 * 9))
        )

    for division_name, division in units["divisions"].items():
        if division_name == "Executive Office":
            continue
        role, title_name = DIVISION_HEAD_ROLES[division_name]
        manager = executives["CTO"] if division_name in {
            "Engineering", "Product and Design", "Quality Assurance",
            "IT and Infrastructure", "Cybersecurity and Compliance", "Data and AI"
        } else executives["COO"]
        if division_name in {"Finance and Procurement"}:
            manager = executives["CFO"]
        if division_name in {"Human Resources"}:
            manager = executives["CHRO"]
        head = add_employee(
            role, title_name, division, manager=manager, division=division_name,
            join_date=TODAY - timedelta(days=RNG.randint(365 * 4, 365 * 8))
        )
        division.head_employee_id = head.id
        division_heads[division_name] = head

    for (division_name, department_name), department in units["departments"].items():
        if division_name == "Executive Office":
            manager = executives["COO"]
        else:
            manager = division_heads.get(division_name)
        role = DEPARTMENT_MANAGER_ROLES.get(division_name, "Department Manager")
        head = add_employee(
            role, "L4", department, manager=manager, division=division_name,
            join_date=TODAY - timedelta(days=RNG.randint(365 * 3, 365 * 7))
        )
        department.head_employee_id = head.id
        department_heads[(division_name, department_name)] = head

    for leaf in units["leaves"]:
        division_name = leaf["division"]
        department_name = leaf["department"]
        team = leaf["org"]
        manager = department_heads[(division_name, department_name)]
        role = "Team Lead" if division_name in {"Engineering", "Quality Assurance", "Data and AI"} else "Lead Specialist"
        head = add_employee(
            role, "L5", team, manager=manager, division=division_name,
            join_date=TODAY - timedelta(days=RNG.randint(365 * 2, 365 * 6))
        )
        team.head_employee_id = head.id
        team_heads[team.id] = head

    weighted_leaves = []
    for leaf in units["leaves"]:
        weight = {
            "Engineering": 5,
            "Product and Design": 2,
            "Quality Assurance": 3,
            "Data and AI": 3,
            "Customer Success and Support": 3,
            "Sales and Marketing": 3,
        }.get(leaf["division"], 1)
        weighted_leaves.extend([leaf] * weight)

    while len(employees) < 300:
        leaf = RNG.choice(weighted_leaves)
        position, title_name = RNG.choice(ROLE_POOLS.get(leaf["division"], ROLE_POOLS["Engineering"]))
        manager = team_heads.get(leaf["org"].id) or department_heads[(leaf["division"], leaf["department"])]
        add_employee(
            position, title_name, leaf["org"], manager=manager,
            division=leaf["division"]
        )

    return employees


def seed_promotions(session, employees, titles, admin_id):
    level_order = ["L7", "L6", "L5", "L4", "L3", "L2", "L1"]
    candidates = [
        employee for employee in employees
        if employee.title.name in {"L6", "L5", "L4", "L3", "L2"}
        and employee.join_date < TODAY - timedelta(days=365 * 3)
    ]
    RNG.shuffle(candidates)

    for employee in candidates[:78]:
        current = employee.title.name
        previous = level_order[level_order.index(current) - 1]
        earliest = employee.join_date + timedelta(days=365)
        latest = TODAY - timedelta(days=120)
        if earliest >= latest:
            continue
        promoted_at = earliest + timedelta(days=RNG.randint(120, max(121, (latest - earliest).days)))
        session.add(PromotionHistory(
            employee_id=employee.id,
            from_title_id=titles[previous].id,
            to_title_id=titles[current].id,
            approved_by_id=admin_id,
            basis=RNG.choice(["time_based", "accelerated", "admin_override"]),
            months_taken=months_between(employee.join_date, promoted_at),
            notes="Seeded prior promotion record.",
            promoted_at=promoted_at,
        ))
    session.flush()


def seed_salary_increments(session, employees, admin_id):
    eligible = [employee for employee in employees if employee.join_date < TODAY - timedelta(days=390)]
    RNG.shuffle(eligible)
    for employee in eligible[:165]:
        applied_at = TODAY - timedelta(days=RNG.randint(30, 520))
        title = employee.title
        salary_before = employee.base_salary
        salary_after = round(salary_before * (1 + title.annual_increment_value / 100), 2)
        employee.base_salary = salary_after
        employee.annual_increment_last_applied = applied_at
        session.add(SalaryIncrementHistory(
            employee_id=employee.id,
            approved_by_id=admin_id,
            salary_before=salary_before,
            salary_after=salary_after,
            increment_type="percentage",
            increment_value=title.annual_increment_value,
            applied_at=applied_at,
            notes="Annual merit increment from seeded demo data.",
        ))
    session.flush()


def seed_commendations(session, employees, admin_id, hr_id):
    counts = {employee.id: 0 for employee in employees}
    non_exec = [employee for employee in employees if employee.title.name not in {"L1", "L2"}]
    RNG.shuffle(non_exec)

    maxed = non_exec[:12]
    for employee in maxed:
        for category in [1, 2, 1]:
            add_commendation(session, [employee], category, admin_id if RNG.random() > 0.4 else hr_id)
            counts[employee.id] += 1

    for employee in non_exec[12:120]:
        award_count = RNG.choice([1, 1, 1, 2])
        for _ in range(award_count):
            if counts[employee.id] >= 3:
                continue
            category = RNG.choice([1, 1, 2, 2, 3])
            add_commendation(session, [employee], category, admin_id if RNG.random() > 0.5 else hr_id)
            counts[employee.id] += 1

    employees_by_team = {}
    for employee in non_exec:
        employees_by_team.setdefault(employee.org_unit_id, []).append(employee)
    team_groups = [group for group in employees_by_team.values() if len(group) >= 4]
    RNG.shuffle(team_groups)

    for group in team_groups[:10]:
        recipients = [employee for employee in group[:6] if counts[employee.id] < 3]
        if len(recipients) < 2:
            continue
        add_commendation(session, recipients, RNG.choice([2, 3]), admin_id)
        for employee in recipients:
            counts[employee.id] += 1

    session.flush()


def add_commendation(session, recipients, category, issued_by_id):
    months = {1: -1, 2: -3, 3: -6}[category]
    first_employee = recipients[0]
    issued_at = random_event_date(race_start_for(session, first_employee))
    comm = Commendation(
        commendation_ref=generate_commendation_ref(session),
        title=RNG.choice(AWARD_TITLES),
        description="Recognition for measurable contribution to delivery, quality, or team outcomes.",
        category=category,
        months_impact=months,
        is_team_award=len(recipients) > 1,
        issued_by_id=issued_by_id,
        issued_at=issued_at,
    )
    session.add(comm)
    session.flush()
    for employee in recipients:
        session.add(CommendationEmployee(commendation_id=comm.id, employee_id=employee.id))


def seed_sanctions(session, employees, admin_id, hr_id):
    candidates = [employee for employee in employees if employee.title.name not in {"L1", "L2"}]
    RNG.shuffle(candidates)

    for employee in candidates[:30]:
        stype = RNG.choice(["verbal_warning", "written_warning", "written_warning", "suspension"])
        add_sanction(session, employee, stype, False, admin_id if RNG.random() > 0.45 else hr_id)

    for employee in candidates[30:68]:
        stype = RNG.choice(["verbal_warning", "written_warning", "suspension", "final_warning"])
        add_sanction(session, employee, stype, True, admin_id if RNG.random() > 0.45 else hr_id)

    session.flush()


def add_sanction(session, employee, sanction_type, resolved, issued_by_id):
    issued_at = random_event_date(race_start_for(session, employee))
    delay = delay_for_sanction_type(sanction_type)
    resolved_at = issued_at + timedelta(days=RNG.randint(14, 90)) if resolved else None
    session.add(Sanction(
        sanction_ref=generate_sanction_ref(session),
        employee_id=employee.id,
        sanction_type=sanction_type,
        reason=RNG.choice(SANCTION_REASON_BY_TYPE[sanction_type]),
        delay_months=delay,
        issued_by_id=issued_by_id,
        issued_at=issued_at,
        resolved_at=resolved_at,
        is_resolved=resolved,
    ))


def seed_audit_log(session, employees, admin_id, hr_id):
    log_action(
        session,
        action="import.bulk_employees",
        performed_by_id=admin_id,
        target_table="employee",
        target_id=None,
        description="Demo software company dataset seeded with 300 employees",
    )

    recent_employees = sorted(employees, key=lambda item: item.created_at or TODAY)[:30]
    for employee in recent_employees:
        add_audit(
            session, "employee.create", admin_id, "employee", employee.id,
            f"New employee added: {employee.full_name} ({employee.employee_id})",
            random_recent_date(2, 22)
        )

    for promotion in session.query(PromotionHistory).limit(45).all():
        add_audit(
            session, "promotion.approve", admin_id, "promotion_history", promotion.id,
            f"Promotion approved for employee #{promotion.employee_id}",
            promotion.promoted_at
        )

    for comm in session.query(Commendation).limit(55).all():
        add_audit(
            session, "commendation.issue", comm.issued_by_id, "commendation", comm.id,
            f"Commendation issued [{comm.commendation_ref}]: {comm.title}",
            comm.issued_at
        )

    for sanction in session.query(Sanction).limit(55).all():
        action = "sanction.resolve" if sanction.is_resolved else "sanction.issue"
        when = sanction.resolved_at if sanction.is_resolved else sanction.issued_at
        add_audit(
            session, action, sanction.issued_by_id, "sanction", sanction.id,
            f"Sanction record [{sanction.sanction_ref}] for {sanction.employee.full_name}",
            when
        )

    for increment in session.query(SalaryIncrementHistory).limit(35).all():
        add_audit(
            session, "salary_increment.apply", hr_id, "employee", increment.employee_id,
            f"Annual salary increment applied: {increment.salary_before} to {increment.salary_after}",
            increment.applied_at
        )


def add_audit(session, action, performed_by_id, target_table, target_id, description, performed_at):
    session.add(AuditLog(
        performed_by_id=performed_by_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        description=description,
        performed_at=performed_at or random_recent_date(1, 30),
    ))


def next_name(index):
    first = FIRST_NAMES[(index * 3) % len(FIRST_NAMES)]
    last = LAST_NAMES[(index * 7) % len(LAST_NAMES)]
    return first, last


def slug(value):
    return re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")


def degree_for_title(title_name):
    if title_name in {"L1", "L2", "L3", "L4"}:
        return RNG.choice(["MSc", "PhD", "Other"])
    if title_name == "L5":
        return RNG.choice(["MSc", "PhD"])
    if title_name == "L6":
        return RNG.choice(["BSc", "MSc"])
    return "BSc"


def salary_for_title(title):
    step = 50
    raw = RNG.uniform(title.base_salary_min, title.base_salary_max)
    return round(raw / step) * step


def join_date_for_title(title_name):
    ranges = {
        "L1": (8, 13),
        "L2": (6, 11),
        "L3": (4, 9),
        "L4": (3, 8),
        "L5": (2, 7),
        "L6": (1, 6),
        "L7": (0, 5),
    }
    min_years, max_years = ranges[title_name]
    days = RNG.randint(min_years * 365 + 60, max_years * 365 + 120)
    return TODAY - timedelta(days=days)


def months_between(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month)


def race_start_for(session, employee):
    last = (
        session.query(PromotionHistory)
        .filter_by(employee_id=employee.id)
        .order_by(PromotionHistory.promoted_at.desc())
        .first()
    )
    return last.promoted_at if last else employee.join_date


def random_event_date(start):
    start = start or TODAY - timedelta(days=365)
    earliest = max(start + timedelta(days=30), TODAY - timedelta(days=900))
    latest = TODAY - timedelta(days=7)
    if earliest >= latest:
        return latest
    return earliest + timedelta(days=RNG.randint(0, (latest - earliest).days))


def random_recent_date(min_days, max_days):
    return TODAY - timedelta(days=RNG.randint(min_days, max_days), hours=RNG.randint(0, 8))


def delay_for_sanction_type(sanction_type):
    if sanction_type == "verbal_warning":
        return RNG.randint(1, 2)
    if sanction_type == "written_warning":
        return RNG.randint(3, 6)
    if sanction_type == "suspension":
        return RNG.randint(6, 9)
    return RNG.randint(9, 12)


if __name__ == "__main__":
    main()
