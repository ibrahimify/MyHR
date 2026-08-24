"""Reporting data service for yearly workforce reports."""

from __future__ import annotations

from calendar import month_abbr
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from sqlalchemy import func

from src.core.app_settings import company_name, company_subtitle
from src.core.i18n import t
from src.database.connection import get_session, OTHER_TITLE_NAME
from src.database.models import (
    AuditLog,
    Commendation,
    Employee,
    OrgUnit,
    PromotionHistory,
    SalaryIncrementHistory,
    Sanction,
    Title,
)


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: str
    detail: str = ""


@dataclass(frozen=True)
class YearlyReport:
    company: str
    subtitle: str
    year: int
    generated_at: datetime
    executive_summary: str
    metrics: list[ReportMetric]
    department_rows: list[list[str]]
    level_rows: list[list[str]]
    monthly_rows: list[list[str]]
    audit_rows: list[list[str]]
    salary_summary: list[ReportMetric] = field(default_factory=list)


def available_report_years() -> list[int]:
    """Return years that have useful workforce activity."""
    session = get_session()
    try:
        years = set()
        date_columns = [
            Employee.join_date,
            PromotionHistory.promoted_at,
            SalaryIncrementHistory.applied_at,
            Commendation.issued_at,
            Sanction.issued_at,
            AuditLog.performed_at,
        ]
        for column in date_columns:
            for (value,) in session.query(column).filter(column.isnot(None)).all():
                if value:
                    years.add(value.year)
        years.add(datetime.utcnow().year)
        return sorted(years, reverse=True)
    finally:
        session.close()


def build_yearly_report(year: int) -> YearlyReport:
    """Build a complete yearly report DTO from live database data."""
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    session = get_session()
    try:
        employees = session.query(Employee).all()
        active_employees = [employee for employee in employees if employee.status == "active"]
        other_employees = [
            employee for employee in employees
            if employee.title and employee.title.name == OTHER_TITLE_NAME
        ]

        promotions = (
            session.query(PromotionHistory)
            .filter(PromotionHistory.promoted_at >= start, PromotionHistory.promoted_at < end)
            .all()
        )
        increments = (
            session.query(SalaryIncrementHistory)
            .filter(SalaryIncrementHistory.applied_at >= start, SalaryIncrementHistory.applied_at < end)
            .all()
        )
        commendations = (
            session.query(Commendation)
            .filter(Commendation.issued_at >= start, Commendation.issued_at < end)
            .all()
        )
        sanctions = (
            session.query(Sanction)
            .filter(Sanction.issued_at >= start, Sanction.issued_at < end)
            .all()
        )
        audit_logs = (
            session.query(AuditLog)
            .filter(AuditLog.performed_at >= start, AuditLog.performed_at < end)
            .all()
        )

        hires = [employee for employee in employees if employee.join_date and start <= employee.join_date < end]
        active_sanctions = [sanction for sanction in session.query(Sanction).all() if not sanction.is_resolved]
        payroll = sum(float(employee.base_salary or 0) for employee in active_employees)
        average_salary = payroll / len(active_employees) if active_employees else 0
        increment_spend = sum(
            max(0, float(item.salary_after or 0) - float(item.salary_before or 0))
            for item in increments
        )
        currency = _primary_currency(active_employees)

        metrics = [
            ReportMetric(t("report_metric_headcount"), str(len(active_employees)), t("active_employees")),
            ReportMetric(t("report_metric_hires"), str(len(hires)), t("joined_during_year")),
            ReportMetric(t("report_metric_promotions"), str(len(promotions)), t("approved_in_year")),
            ReportMetric(t("report_metric_increments"), str(len(increments)), t("approved_in_year")),
            ReportMetric(t("report_metric_commendations"), str(len(commendations)), t("issued_in_year")),
            ReportMetric(t("report_metric_sanctions"), str(len(sanctions)), t("issued_in_year")),
            ReportMetric(t("report_metric_other_track"), str(len(other_employees)), t("annual_increment_only")),
            ReportMetric(t("report_metric_audit_events"), str(len(audit_logs)), t("immutable_activity_records")),
        ]
        salary_summary = [
            ReportMetric(t("report_metric_payroll"), _money(payroll, currency), t("active_base_salary_total")),
            ReportMetric(t("report_metric_average_salary"), _money(average_salary, currency), t("active_employee_average")),
            ReportMetric(t("report_metric_increment_spend"), _money(increment_spend, currency), t("yearly_increment_delta")),
            ReportMetric(t("report_metric_active_sanctions"), str(len(active_sanctions)), t("open_disciplinary_actions")),
        ]

        department_rows = _department_rows(employees)
        level_rows = _level_rows(session)
        monthly_rows = _monthly_activity_rows(promotions, increments, commendations, sanctions)
        audit_rows = _audit_rows(audit_logs)

        summary = t(
            "yearly_report_summary_text",
            company=company_name("MyHR"),
            year=year,
            headcount=len(active_employees),
            promotions=len(promotions),
            increments=len(increments),
            sanctions=len(sanctions),
        )
        return YearlyReport(
            company=company_name("MyHR"),
            subtitle=company_subtitle("Employee Management"),
            year=year,
            generated_at=datetime.utcnow(),
            executive_summary=summary,
            metrics=metrics,
            salary_summary=salary_summary,
            department_rows=department_rows,
            level_rows=level_rows,
            monthly_rows=monthly_rows,
            audit_rows=audit_rows,
        )
    finally:
        session.close()


def build_yearly_report_html(report: YearlyReport) -> str:
    """Render the yearly report as print-ready HTML for Qt PDF export."""
    generated = report.generated_at.strftime("%Y-%m-%d %H:%M")
    title = t("yearly_workforce_report")
    metric_cards = "".join(_metric_card(metric) for metric in report.metrics)
    salary_cards = "".join(_metric_card(metric) for metric in report.salary_summary)
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    color: #111827;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
}}
h1 {{
    color: #030213;
    font-size: 28pt;
    margin: 0;
}}
h2 {{
    color: #030213;
    font-size: 16pt;
    margin: 22px 0 10px;
}}
h3 {{
    color: #111827;
    font-size: 12pt;
    margin: 0 0 6px;
}}
p {{
    margin: 0 0 8px;
}}
.cover {{
    border-bottom: 3px solid #2563eb;
    padding-bottom: 18px;
    margin-bottom: 24px;
}}
.company {{
    color: #2563eb;
    font-size: 13pt;
    font-weight: 700;
    margin-bottom: 8px;
}}
.meta {{
    color: #4b5563;
    font-size: 9pt;
    margin-top: 12px;
}}
.summary {{
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 14px 0 18px;
}}
.cards {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 8px;
    margin: 8px 0 12px;
}}
.card {{
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px;
    width: 25%;
    vertical-align: top;
}}
.label {{
    color: #4b5563;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}
.value {{
    color: #030213;
    font-size: 19pt;
    font-weight: 800;
    margin-top: 4px;
}}
.detail {{
    color: #2563eb;
    font-size: 8.5pt;
    margin-top: 2px;
}}
table.data {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
}}
table.data th {{
    background: #f3f4f6;
    color: #111827;
    border-bottom: 1px solid #d1d5db;
    font-weight: 700;
    padding: 7px 8px;
    text-align: left;
}}
table.data td {{
    border-bottom: 1px solid #e5e7eb;
    padding: 7px 8px;
    color: #111827;
}}
.footer {{
    color: #6b7280;
    border-top: 1px solid #e5e7eb;
    margin-top: 28px;
    padding-top: 10px;
    font-size: 8.5pt;
}}
</style>
</head>
<body>
    <div class="cover">
        <div class="company">{escape(report.company)}</div>
        <h1>{escape(title)}</h1>
        <p class="meta">{escape(report.subtitle)} | {escape(t("report_period", year=report.year))} | {escape(t("generated_on", value=generated))}</p>
    </div>
    <h2>{escape(t("executive_summary"))}</h2>
    <div class="summary">{escape(report.executive_summary)}</div>
    <h2>{escape(t("workforce_highlights"))}</h2>
    {_cards_table(metric_cards)}
    <h2>{escape(t("salary_and_compliance"))}</h2>
    {_cards_table(salary_cards)}
    {_data_table(t("department_breakdown"), [t("department"), t("employees"), t("active"), t("average_salary")], report.department_rows)}
    {_data_table(t("level_breakdown"), [t("level"), t("name"), t("employees"), t("salary_range")], report.level_rows)}
    {_data_table(t("monthly_activity"), [t("month"), t("promotions"), t("increments"), t("commendations"), t("sanctions")], report.monthly_rows)}
    {_data_table(t("audit_summary"), [t("category"), t("events"), t("most_recent_action")], report.audit_rows)}
    <div class="footer">
        {escape(t("report_footer_note"))}
    </div>
</body>
</html>
"""


def _department_rows(employees: list[Employee]) -> list[list[str]]:
    grouped = defaultdict(list)
    for employee in employees:
        name = employee.org_unit.name if employee.org_unit else t("unassigned")
        grouped[name].append(employee)

    rows = []
    for name, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        active = [employee for employee in items if employee.status == "active"]
        average_salary = (
            sum(float(employee.base_salary or 0) for employee in active) / len(active)
            if active else 0
        )
        rows.append([name, str(len(items)), str(len(active)), _money(average_salary, _primary_currency(active))])
    return rows or [[t("no_data"), "0", "0", _money(0, "EUR")]]


def _level_rows(session) -> list[list[str]]:
    rows = []
    counts = dict(
        session.query(Employee.title_id, func.count(Employee.id))
        .group_by(Employee.title_id)
        .all()
    )
    titles = session.query(Title).all()
    titles.sort(key=lambda title: _level_sort_key(title.name))
    for title in titles:
        salary = f"{title.base_salary_min:,.0f}-{title.base_salary_max:,.0f} {title.currency or 'EUR'}"
        rows.append([title.name, title.label, str(counts.get(title.id, 0)), salary])
    return rows


def _monthly_activity_rows(promotions, increments, commendations, sanctions) -> list[list[str]]:
    buckets = {
        "promotions": Counter(item.promoted_at.month for item in promotions if item.promoted_at),
        "increments": Counter(item.applied_at.month for item in increments if item.applied_at),
        "commendations": Counter(item.issued_at.month for item in commendations if item.issued_at),
        "sanctions": Counter(item.issued_at.month for item in sanctions if item.issued_at),
    }
    return [
        [
            month_abbr[month],
            str(buckets["promotions"].get(month, 0)),
            str(buckets["increments"].get(month, 0)),
            str(buckets["commendations"].get(month, 0)),
            str(buckets["sanctions"].get(month, 0)),
        ]
        for month in range(1, 13)
    ]


def _audit_rows(audit_logs: list[AuditLog]) -> list[list[str]]:
    grouped = defaultdict(list)
    for log in audit_logs:
        category = (log.action or "other").split(".")[0].replace("_", " ").title()
        grouped[category].append(log)
    rows = []
    for category, logs in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        latest = max(logs, key=lambda log: log.performed_at or datetime.min)
        rows.append([category, str(len(logs)), latest.description or latest.action or "-"])
    return rows or [[t("no_data"), "0", "-"]]


def _metric_card(metric: ReportMetric) -> str:
    return (
        "<td class=\"card\">"
        f"<div class=\"label\">{escape(metric.label)}</div>"
        f"<div class=\"value\">{escape(metric.value)}</div>"
        f"<div class=\"detail\">{escape(metric.detail)}</div>"
        "</td>"
    )


def _cards_table(cards: str) -> str:
    cells = cards.split("</td>")
    cells = [cell + "</td>" for cell in cells if cell.strip()]
    rows = []
    for index in range(0, len(cells), 4):
        rows.append("<tr>" + "".join(cells[index:index + 4]) + "</tr>")
    return "<table class=\"cards\">" + "".join(rows) + "</table>"


def _data_table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<h2>{escape(title)}</h2><table class=\"data\"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency or 'EUR'}"


def _primary_currency(employees: list[Employee]) -> str:
    currencies = {employee.title.currency for employee in employees if employee.title and employee.title.currency}
    if not currencies:
        return "EUR"
    if len(currencies) == 1:
        return next(iter(currencies))
    return t("mixed_currency")


def _level_sort_key(name: str):
    if name == OTHER_TITLE_NAME:
        return (2, 0)
    if name.startswith("L") and name[1:].isdigit():
        return (0, -int(name[1:]))
    return (1, name)
