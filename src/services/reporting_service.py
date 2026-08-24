"""Reporting data service for yearly workforce reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from sqlalchemy import func

from src.core.app_settings import company_name, company_subtitle
from src.core.i18n import is_rtl, t
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
    direction = "rtl" if is_rtl() else "ltr"
    align = "right" if is_rtl() else "left"
    opposite_align = "left" if is_rtl() else "right"
    section_count = 6
    return f"""
<!doctype html>
<html dir="{direction}">
<head>
<meta charset="utf-8">
<style>
body {{
    color: #1c2430;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    margin: 0;
}}
h1, h2 {{
    color: #16202e;
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 700;
}}
p {{
    margin: 0 0 8px;
}}
.hr {{
    border: none;
    border-top: 1px solid #c7ccd4;
    margin: 14px 0;
}}
.hr-accent {{
    border: none;
    border-top: 2px solid #1f3a5f;
    margin: 8px 0 24px;
}}
.page {{
    background: #ffffff;
    color: #1c2430;
}}
.cover {{
    padding-top: 8px;
}}
.masthead {{
    color: #55606e;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.company {{
    color: #16202e;
    font-size: 13pt;
    font-weight: 700;
    margin-top: 4px;
}}
.subtitle {{
    color: #55606e;
    font-size: 9.5pt;
    margin-top: 2px;
}}
h1.title {{
    font-size: 25pt;
    margin: 30px 0 4px;
}}
.period {{
    color: #1f3a5f;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11pt;
    margin-bottom: 26px;
}}
h2.section-title {{
    font-size: 13pt;
    margin: 0 0 4px;
}}
.section-page {{
    page-break-before: always;
}}
.section-header {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 6px;
}}
.section-header td {{
    border: none;
    padding: 0;
    vertical-align: top;
}}
.section-header .meta {{
    color: #55606e;
    font-size: 8pt;
    text-align: {opposite_align};
}}
.summary {{
    background: #f7f8fa;
    border: 1px solid #c7ccd4;
    border-left: 3px solid #1f3a5f;
    padding: 14px 16px;
    margin: 4px 0 20px;
    page-break-inside: avoid;
}}
table.metrics {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 6px;
}}
table.metrics td {{
    border: 1px solid #d9dee5;
    padding: 10px 12px;
    width: 50%;
    vertical-align: top;
    page-break-inside: avoid;
}}
table.metrics .m-label {{
    color: #55606e;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}
table.metrics .m-value {{
    color: #16202e;
    font-size: 14pt;
    font-weight: 700;
    margin-top: 3px;
}}
table.metrics .m-detail {{
    color: #55606e;
    font-size: 8pt;
    margin-top: 2px;
}}
table.data {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 6px;
    font-size: 9pt;
    table-layout: fixed;
}}
table.data th {{
    background: #f1f2f4;
    color: #16202e;
    border-bottom: 1px solid #1f3a5f;
    font-weight: 700;
    padding: 7px 9px;
    text-align: {align};
    word-wrap: break-word;
}}
table.data td {{
    border-bottom: 1px solid #e2e5ea;
    padding: 7px 9px;
    color: #1c2430;
    vertical-align: top;
    word-wrap: break-word;
}}
table.data tr:nth-child(even) td {{
    background: #fafafb;
}}
.page-footer {{
    color: #8a93a1;
    border-top: 1px solid #d9dee5;
    margin-top: 28px;
    padding-top: 8px;
    font-size: 7.5pt;
}}
.page-footer table {{
    width: 100%;
    border-collapse: collapse;
}}
.page-footer td {{
    border: none;
    padding: 0;
    vertical-align: top;
}}
.page-footer .right {{
    text-align: {opposite_align};
    white-space: nowrap;
}}
</style>
</head>
<body>
    <div class="page cover">
        <div class="masthead">{escape(t("report_period", year=report.year))}</div>
        <div class="company">{escape(report.company)}</div>
        <div class="subtitle">{escape(report.subtitle)}</div>
        <h1 class="title">{escape(title)}</h1>
        <div class="period">{escape(t("report_period", year=report.year))} &middot; {escape(t("generated_on", value=generated))}</div>
        <hr class="hr-accent">
        <h2 class="section-title">{escape(t("executive_summary"))}</h2>
        <div class="summary">{escape(report.executive_summary)}</div>
        {_report_footer(report, t("executive_summary"), 0, section_count)}
    </div>
    {_report_section(report, t("workforce_highlights"), _metric_table(report.metrics), 1, section_count)}
    {_report_section(report, t("salary_and_compliance"), _metric_table(report.salary_summary), 2, section_count)}
    {_report_section(report, t("department_breakdown"), _data_table([t("department"), t("report_header_employees"), t("active"), t("report_metric_average_salary")], report.department_rows), 3, section_count)}
    {_report_section(report, t("level_breakdown"), _data_table([t("level"), t("name"), t("report_header_employees"), t("salary_range")], report.level_rows), 4, section_count)}
    {_report_section(report, t("monthly_activity"), _data_table([t("filter_month"), t("promotions"), t("report_metric_increments"), t("report_metric_commendations"), t("report_metric_sanctions")], report.monthly_rows), 5, section_count)}
    {_report_section(report, t("audit_summary"), _data_table([t("category"), t("events"), t("most_recent_action")], report.audit_rows), 6, section_count)}
</body>
</html>
"""


def _department_rows(employees: list[Employee]) -> list[list[str]]:
    grouped = defaultdict(list)
    for employee in employees:
        name = employee.org_unit.name if employee.org_unit else t("unassigned")
        grouped[name].append(employee)

    summary = []
    for name, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        active = [employee for employee in items if employee.status == "active"]
        average_salary = (
            sum(float(employee.base_salary or 0) for employee in active) / len(active)
            if active else 0
        )
        summary.append((name, items, active, average_salary))
    if not summary:
        return [[t("no_data"), "0", "0", _money(0, "EUR")]]

    top_rows = summary[:12]
    rows = [
        [name, str(len(items)), str(len(active)), _money(average_salary, _primary_currency(active))]
        for name, items, active, average_salary in top_rows
    ]
    remaining = summary[12:]
    if remaining:
        remaining_items = [employee for _, items, _, _ in remaining for employee in items]
        remaining_active = [employee for _, _, active, _ in remaining for employee in active]
        remaining_average = (
            sum(float(employee.base_salary or 0) for employee in remaining_active) / len(remaining_active)
            if remaining_active else 0
        )
        rows.append([
            t("remaining_units"),
            str(len(remaining_items)),
            str(len(remaining_active)),
            _money(remaining_average, _primary_currency(remaining_active)),
        ])
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
            _report_month(month),
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


def _report_month(month: int) -> str:
    return t(f"report_month_{month:02d}")


def _report_section(report: YearlyReport, title: str, content: str, index: int, total: int) -> str:
    header = (
        "<table class=\"section-header\"><tr>"
        f"<td><div class=\"masthead\">{escape(report.company)} &middot; {escape(t('yearly_workforce_report'))}</div></td>"
        f"<td class=\"meta\">{escape(t('report_period', year=report.year))}</td>"
        "</tr></table>"
    )
    return (
        "<div class=\"page section-page\">"
        f"{header}"
        "<hr class=\"hr\">"
        f"<h2 class=\"section-title\">{escape(title)}</h2>"
        f"{content}"
        f"{_report_footer(report, title, index, total)}"
        "</div>"
    )


def _report_footer(report: YearlyReport, title: str, index: int, total: int) -> str:
    if index:
        page_text = f"{escape(title)} &middot; {index}/{total}"
    else:
        page_text = escape(t("executive_summary"))
    return (
        "<div class=\"page-footer\">"
        "<table><tr>"
        f"<td>{escape(t('report_footer_note'))}</td>"
        f"<td class=\"right\">{page_text}</td>"
        "</tr></table>"
        "</div>"
    )


def _metric_table(metrics: list[ReportMetric]) -> str:
    cells = [_metric_cell(metric) for metric in metrics]
    rows = []
    for index in range(0, len(cells), 2):
        row_cells = cells[index:index + 2]
        if len(row_cells) == 1:
            row_cells.append("<td></td>")
        rows.append("<tr>" + "".join(row_cells) + "</tr>")
    return "<table class=\"metrics\">" + "".join(rows) + "</table>"


def _metric_cell(metric: ReportMetric) -> str:
    return (
        "<td>"
        f"<div class=\"m-label\">{escape(metric.label)}</div>"
        f"<div class=\"m-value\">{escape(metric.value)}</div>"
        f"<div class=\"m-detail\">{escape(metric.detail)}</div>"
        "</td>"
    )


def _data_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table class=\"data\"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


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
