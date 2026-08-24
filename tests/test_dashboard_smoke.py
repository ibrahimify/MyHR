import os
import csv
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.database.connection as db
from src.database.models import Base


class DashboardSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._old_engine = db.engine
        cls._old_session_local = db.SessionLocal
        cls._tmp = tempfile.NamedTemporaryFile(prefix="myhr_ui_test_", suffix=".db", delete=False)
        cls._tmp.close()
        cls.engine = create_engine(f"sqlite:///{cls._tmp.name}", echo=False)
        db.engine = cls.engine
        db.SessionLocal = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(cls.engine)
        with db.SessionLocal() as session:
            db._seed_defaults(session)

        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        db.SessionLocal = cls._old_session_local
        db.engine = cls._old_engine
        cls.engine.dispose()
        try:
            os.remove(cls._tmp.name)
        except OSError:
            pass

    def test_priority_signal_view_buttons_route_to_expected_pages(self):
        from PySide6.QtWidgets import QPushButton

        from src.ui.main_window import MainWindow
        from src.ui.pages.employees import EmployeesPage
        from src.ui.pages.sanctions import SanctionsPage

        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Smoke Test")
        window = MainWindow(user)
        try:
            dashboard = window._pages_cache["dashboard"]
            dashboard._set_workforce_metric("all")
            self.assertEqual(len(dashboard.timeline_series), 3)
            for _, values, _ in dashboard.timeline_series:
                self.assertEqual(len(values), len(dashboard.timeline_labels))

            buttons = [
                button for button in dashboard.findChildren(QPushButton)
                if button.text() == "View"
                and button.parent()
                and button.parent().objectName() == "AttentionRow"
            ]
            self.assertEqual(len(buttons), 3)

            buttons[0].click()
            self.assertIsInstance(window.stack.currentWidget(), SanctionsPage)
            self.assertEqual(window.stack.currentWidget().tabs.currentIndex(), 2)

            window._navigate("dashboard")
            dashboard = window._pages_cache["dashboard"]
            buttons = [
                button for button in dashboard.findChildren(QPushButton)
                if button.text() == "View"
                and button.parent()
                and button.parent().objectName() == "AttentionRow"
            ]
            buttons[1].click()
            self.assertIsInstance(window.stack.currentWidget(), SanctionsPage)
            self.assertEqual(window.stack.currentWidget().tabs.currentIndex(), 2)

            window._navigate("dashboard")
            dashboard = window._pages_cache["dashboard"]
            buttons = [
                button for button in dashboard.findChildren(QPushButton)
                if button.text() == "View"
                and button.parent()
                and button.parent().objectName() == "AttentionRow"
            ]
            buttons[2].click()
            self.assertIsInstance(window.stack.currentWidget(), EmployeesPage)
        finally:
            window.close()

    def test_settings_tabs_save_renamed_levels_by_database_id(self):
        from src.ui.pages.settings import IncrementTab, SalaryTab

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            title = session.query(db.Title).filter_by(name="L7").one()
            title.name = "Entry Track"
            title.label = "Entry Track"
            title.base_salary_min = 2100
            title.base_salary_max = 2800
            title_id = title.id
            session.commit()
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        salary_tab = SalaryTab(user)
        min_spin, max_spin = salary_tab.fields[title_id]
        min_spin.setValue(2200)
        max_spin.setValue(2900)
        salary_tab.currency_input.setText("HUF")

        increment_tab = IncrementTab(user)
        combo, spin = increment_tab.fields[title_id]
        combo.setCurrentIndex(combo.findData("fixed"))
        spin.setValue(250.0)

        with patch("src.ui.pages.settings._information", return_value=None):
            salary_tab._save()
            increment_tab._save()

        with db.SessionLocal() as session:
            updated = session.query(db.Title).filter_by(id=title_id).one()
            self.assertEqual(updated.name, "Entry Track")
            self.assertEqual(updated.base_salary_min, 2200)
            self.assertEqual(updated.base_salary_max, 2900)
            self.assertEqual(updated.currency, "HUF")
            self.assertEqual(updated.annual_increment_type, "fixed")
            self.assertEqual(updated.annual_increment_value, 250.0)
            updated.name = "L7"
            updated.label = "Entry Level"
            updated.base_salary_min = 2000
            updated.base_salary_max = 2800
            updated.currency = "EUR"
            updated.annual_increment_type = "percentage"
            updated.annual_increment_value = 3.0
            session.commit()

    def test_promotion_rules_edit_custom_targets_and_reject_cycles(self):
        from src.ui.pages.settings import SettingsPromotionTab

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            l7 = session.query(db.Title).filter_by(name="L7").one()
            l6 = session.query(db.Title).filter_by(name="L6").one()
            l5 = session.query(db.Title).filter_by(name="L5").one()
            l4 = session.query(db.Title).filter_by(name="L4").one()
            l6.name = "LL6"
            l6.label = "Custom Mid"
            ids = {
                "l7": l7.id,
                "l6": l6.id,
                "l5": l5.id,
                "l4": l4.id,
            }
            session.commit()
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        try:
            tab = SettingsPromotionTab(user)
            l7_target = tab.fields[ids["l7"]]["target"]
            l6_index = l7_target.findData(ids["l6"])
            self.assertGreaterEqual(l6_index, 0)
            self.assertIn("LL6", l7_target.itemText(l6_index))

            tab.fields[ids["l7"]]["months"].setValue(42)
            tab.fields[ids["l7"]]["salary"].setValue(22.0)

            with patch("src.ui.pages.settings._information", return_value=None):
                tab._save()

            with db.SessionLocal() as session:
                rule = session.query(db.PromotionRule).filter_by(from_title_id=ids["l7"]).one()
                target = session.query(db.Title).filter_by(id=ids["l6"]).one()
                self.assertEqual(rule.to_title_id, ids["l6"])
                self.assertEqual(rule.base_months, 42)
                self.assertEqual(target.promotion_salary_increase_pct, 22.0)

            l7_target = tab.fields[ids["l7"]]["target"]
            l5_index = l7_target.findData(ids["l5"])
            self.assertGreaterEqual(l5_index, 0)
            l7_target.setCurrentIndex(l5_index)
            with patch("src.ui.pages.settings._warning", return_value=None) as warning:
                tab._save()
            warning.assert_called_once()

            tab._load()
            l6_target = tab.fields[ids["l6"]]["target"]
            l7_index = l6_target.findData(ids["l7"])
            self.assertGreaterEqual(l7_index, 0)
            l6_target.setCurrentIndex(l7_index)
            with patch("src.ui.pages.settings._warning", return_value=None) as warning:
                tab._save()
            warning.assert_called_once()

            with db.SessionLocal() as session:
                l7_rule = session.query(db.PromotionRule).filter_by(from_title_id=ids["l7"]).one()
                l6_rule = session.query(db.PromotionRule).filter_by(from_title_id=ids["l6"]).one()
                self.assertEqual(l7_rule.to_title_id, ids["l6"])
                self.assertEqual(l6_rule.to_title_id, ids["l5"])
        finally:
            with db.SessionLocal() as session:
                l6 = session.query(db.Title).filter_by(id=ids["l6"]).one()
                l5 = session.query(db.Title).filter_by(id=ids["l5"]).one()
                l6.name = "L6"
                l6.label = "Mid Level"
                l6.promotion_salary_increase_pct = 20.0
                l5.promotion_salary_increase_pct = 25.0
                l7_rule = session.query(db.PromotionRule).filter_by(from_title_id=ids["l7"]).one()
                l7_rule.to_title_id = ids["l6"]
                l7_rule.base_months = 36
                session.commit()

    def test_level_management_rejects_invalid_promotion_targets(self):
        from src.ui.pages.settings import AddLevelDialog

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            l7 = session.query(db.Title).filter_by(name="L7").one()
            l6 = session.query(db.Title).filter_by(name="L6").one()
            l5 = session.query(db.Title).filter_by(name="L5").one()
            ids = {"l7": l7.id, "l6": l6.id, "l5": l5.id}
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        add_dialog = AddLevelDialog(user)
        try:
            add_dialog.level_name.setText("L8")
            add_dialog.level_label.setText("Interns")
            add_dialog.currency.setText("EUR")
            add_dialog.salary_min.setValue(500)
            add_dialog.salary_max.setValue(900)
            l6_index = add_dialog.target_title.findData(ids["l6"])
            self.assertGreaterEqual(l6_index, 0)
            add_dialog.target_title.setCurrentIndex(l6_index)
            with patch("src.ui.pages.settings._warning", return_value=None) as warning:
                add_dialog._save()
            warning.assert_called_once()
            with db.SessionLocal() as session:
                self.assertIsNone(session.query(db.Title).filter_by(name="L8").first())
        finally:
            add_dialog.close()

        edit_dialog = AddLevelDialog(user, title_id=ids["l6"])
        try:
            l7_index = edit_dialog.target_title.findData(ids["l7"])
            self.assertGreaterEqual(l7_index, 0)
            edit_dialog.target_title.setCurrentIndex(l7_index)
            with patch("src.ui.pages.settings._warning", return_value=None) as warning:
                edit_dialog._save()
            warning.assert_called_once()
            with db.SessionLocal() as session:
                l6_rule = session.query(db.PromotionRule).filter_by(from_title_id=ids["l6"]).one()
                self.assertEqual(l6_rule.to_title_id, ids["l5"])
        finally:
            edit_dialog.close()

    def test_level_management_allows_other_policy_edits_without_rename(self):
        from src.ui.pages.settings import AddLevelDialog

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            other = session.query(db.Title).filter_by(name="Other").one()
            title_id = other.id
            original = {
                "label": other.label,
                "min": other.base_salary_min,
                "max": other.base_salary_max,
                "currency": other.currency,
                "increment_type": other.annual_increment_type,
                "increment_value": other.annual_increment_value,
            }
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        dialog = AddLevelDialog(user, title_id=title_id)
        try:
            dialog.level_label.setText("Support Staff")
            dialog.currency.setText("HUF")
            dialog.salary_min.setValue(100)
            dialog.salary_max.setValue(700)
            fixed_index = dialog.increment_type.findData("fixed")
            self.assertGreaterEqual(fixed_index, 0)
            dialog.increment_type.setCurrentIndex(fixed_index)
            dialog.increment_value.setValue(50)
            with patch("src.ui.pages.settings._information", return_value=None):
                dialog._save()
            with db.SessionLocal() as session:
                other = session.query(db.Title).filter_by(id=title_id).one()
                self.assertEqual(other.name, "Other")
                self.assertEqual(other.label, "Support Staff")
                self.assertEqual(other.currency, "HUF")
                self.assertEqual(other.annual_increment_type, "fixed")
                self.assertEqual(other.annual_increment_value, 50)
                other.label = original["label"]
                other.base_salary_min = original["min"]
                other.base_salary_max = original["max"]
                other.currency = original["currency"]
                other.annual_increment_type = original["increment_type"]
                other.annual_increment_value = original["increment_value"]
                session.commit()
        finally:
            dialog.close()

    def test_history_tables_render_only_one_page(self):
        from datetime import datetime

        from src.database.models import (
            AuditLog,
            Commendation,
            CommendationEmployee,
            Employee,
            OrgUnit,
            Sanction,
        )
        from src.ui.pages.audit_log import AuditLogPage
        from src.ui.pages.commendations import CommendationHistoryTab
        from src.ui.pages.sanctions import SanctionHistoryTab

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            title = session.query(db.Title).filter_by(name="L7").one()
            org = OrgUnit(name="Smoke Org", unit_type="organization")
            session.add(org)
            session.flush()
            employees = []
            now = datetime.utcnow()
            for index in range(65):
                employee = Employee(
                    employee_id=f"SMOKE-{index + 1:04d}",
                    first_name="Smoke",
                    last_name=f"Employee{index + 1}",
                    degree="BSc",
                    work_email=f"smoke{index + 1}@example.test",
                    position="Analyst",
                    join_date=now,
                    base_salary=2400,
                    status="active",
                    title_id=title.id,
                    org_unit_id=org.id,
                )
                session.add(employee)
                session.flush()
                employees.append(employee)
                session.add(AuditLog(
                    performed_by_id=admin.id,
                    performed_by_username="admin",
                    performed_by_name="Smoke Admin",
                    action="employee.update",
                    target_table="employee",
                    target_id=employee.id,
                    description="Pagination smoke",
                ))
                commendation = Commendation(
                    commendation_ref=f"COM-SMOKE-{index + 1:03d}",
                    title="Pagination commendation",
                    category=1,
                    months_impact=-1,
                    issued_by_id=admin.id,
                    issued_at=now,
                )
                session.add(commendation)
                session.flush()
                session.add(CommendationEmployee(commendation_id=commendation.id, employee_id=employee.id))
                session.add(Sanction(
                    sanction_ref=f"SAN-SMOKE-{index + 1:03d}",
                    employee_id=employee.id,
                    sanction_type="written_warning",
                    reason="Pagination sanction",
                    delay_months=1,
                    issued_by_id=admin.id,
                    issued_at=now,
                    is_resolved=False,
                ))
            session.commit()

        user = type("User", (), {"id": 1, "username": "admin", "role": "admin", "full_name": "Smoke Admin"})()
        audit = AuditLogPage(user)
        commendations = CommendationHistoryTab(user)
        sanctions = SanctionHistoryTab(user)

        self.assertLessEqual(audit.table.rowCount(), 50)
        self.assertLessEqual(commendations.table.rowCount(), 50)
        self.assertLessEqual(sanctions.table.rowCount(), 50)
        self.assertGreaterEqual(audit.total_pages, 2)
        self.assertGreaterEqual(commendations.total_pages, 2)
        self.assertGreaterEqual(sanctions.total_pages, 2)

    def test_issue_sanction_tab_populates_and_creates_sanction(self):
        from datetime import datetime

        from src.database.models import AuditLog, Sanction
        from src.ui.pages.sanctions import IssueSanctionTab

        issued = []
        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            title = session.query(db.Title).filter_by(name="L7").one()
            employee = db.Employee(
                employee_id="SAN-SMOKE-EMP",
                first_name="Sanction",
                last_name="Smoke",
                degree="BSc",
                position="Analyst",
                join_date=datetime.utcnow(),
                base_salary=2400,
                status="active",
                title_id=title.id,
            )
            session.add(employee)
            session.commit()
            before_count = session.query(Sanction).count()
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        tab = IssueSanctionTab(user, lambda: issued.append(True))
        try:
            self.assertGreater(tab.emp_combo.count(), 1)
            tab.emp_combo.setCurrentIndex(1)
            tab.type_combo.setCurrentIndex(tab.type_combo.findData("written_warning"))
            tab.reason_input.setPlainText("Smoke sanction reason")
            tab.delay_combo.setCurrentIndex(tab.delay_combo.findData(2))

            with patch("src.ui.pages.sanctions._information", return_value=None):
                tab._issue()

            self.assertTrue(issued)
            with db.SessionLocal() as session:
                self.assertEqual(session.query(Sanction).count(), before_count + 1)
                sanction = (
                    session.query(Sanction)
                    .filter_by(reason="Smoke sanction reason", delay_months=2)
                    .order_by(Sanction.id.desc())
                    .first()
                )
                self.assertIsNotNone(sanction)
                self.assertIsNotNone(
                    session.query(AuditLog)
                    .filter_by(action="sanction.issue", target_table="sanction", target_id=sanction.id)
                    .first()
                )
        finally:
            tab.close()

    def test_yearly_report_builds_pdf_without_placeholder_text(self):
        from pathlib import Path

        from src.services.reporting_service import build_yearly_report, build_yearly_report_html
        from src.ui.pages.settings import _write_pdf

        year = 2026
        report = build_yearly_report(year)
        html = build_yearly_report_html(report)

        self.assertEqual(report.year, year)
        self.assertIn("Yearly Workforce Report", html)
        self.assertIn("Executive Summary", html)
        self.assertNotIn("Thesis Extension", html)
        self.assertNotIn("average_salary", html)

        fd, name = tempfile.mkstemp(prefix="myhr_report_", suffix=".pdf")
        os.close(fd)
        target = Path(name)
        try:
            _write_pdf(str(target), html)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 1000)
            from pypdf import PdfReader
            reader = PdfReader(str(target))
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertIn(f"1 / {len(reader.pages)}", extracted)
        finally:
            try:
                target.unlink()
            except OSError:
                pass

    def test_yearly_report_uses_current_company_settings(self):
        from src.services.reporting_service import build_yearly_report, build_yearly_report_html

        with patch("src.services.reporting_service.company_name", return_value="Nexasoft Labs"), \
             patch("src.services.reporting_service.company_subtitle", return_value="People Operations"):
            report = build_yearly_report(2026)
            html = build_yearly_report_html(report)

        self.assertEqual(report.company, "Nexasoft Labs")
        self.assertEqual(report.subtitle, "People Operations")
        self.assertIn("Nexasoft Labs", html)
        self.assertIn("People Operations", html)

    def test_yearly_report_filters_and_report_types(self):
        from src.services.reporting_service import ReportFilters, build_yearly_report, build_yearly_report_html

        with db.SessionLocal() as session:
            title = session.query(db.Title).filter_by(name="L7").one()
            title_id = title.id

        executive = build_yearly_report(2026, ReportFilters(report_type="executive", title_id=title_id, status="active"))
        executive_html = build_yearly_report_html(executive)
        self.assertEqual(executive.report_type, "executive")
        self.assertIn("Executive Workforce Report", executive_html)
        self.assertIn("Level:", executive.filter_summary)
        self.assertIn("Workforce Highlights", executive_html)
        self.assertNotIn("Audit Summary", executive_html)

        audit = build_yearly_report(2026, ReportFilters(report_type="audit"))
        audit_html = build_yearly_report_html(audit)
        self.assertIn("Yearly Audit Report", audit_html)
        self.assertIn("Audit Summary", audit_html)
        self.assertNotIn("Department Breakdown", audit_html)

    def test_database_report_filter_controls_are_wired(self):
        from src.ui.pages.settings import DatabaseTab

        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Smoke Admin")
        tab = DatabaseTab(user)
        try:
            self.assertGreaterEqual(tab.report_type.count(), 3)
            self.assertGreaterEqual(tab.report_year.count(), 1)
            self.assertGreaterEqual(tab.report_department.count(), 1)
            self.assertGreaterEqual(tab.report_level.count(), 1)
            self.assertEqual(tab._report_filters().report_type, "full")
        finally:
            tab.close()

    def test_audit_log_filters_details_and_exports_current_view(self):
        from datetime import datetime, timedelta
        from pathlib import Path

        from src.database.models import AuditLog
        from src.ui.pages.audit_log import AuditLogPage, _format_diff, _format_snapshot

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="employee.update",
                target_table="employee",
                target_id=501,
                description="Audit export current item",
                before_value='{"status": "inactive"}',
                after_value='{"status": "active"}',
                performed_at=datetime.utcnow(),
            ))
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="employee.update",
                target_table="employee",
                target_id=502,
                description="Audit export old item",
                performed_at=datetime.utcnow() - timedelta(days=60),
            ))
            session.commit()
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        page = AuditLogPage(user)
        page.refresh()
        self.assertGreaterEqual(page.search.minimumWidth(), 360)
        self.assertEqual(page.search_btn.text(), "Search")
        page.search.setText("Audit export")
        page.date_filter.setCurrentIndex(page.date_filter.findData("last_30"))
        employee_target_index = page.target_filter.findData("employee")
        self.assertGreaterEqual(employee_target_index, 0)
        page.target_filter.setCurrentIndex(employee_target_index)
        page._filter()
        self.assertEqual(page.table.rowCount(), 1)
        self.assertIn("status", _format_snapshot('{"status": "active"}'))
        self.assertIn("Status: inactive -> active", _format_diff('{"status": "inactive"}', '{"status": "active"}'))

        fd, name = tempfile.mkstemp(prefix="myhr_audit_", suffix=".csv")
        os.close(fd)
        target = Path(name)
        try:
            with patch("src.ui.pages.audit_log.QFileDialog.getSaveFileName", return_value=(str(target), "CSV Files (*.csv)")), \
                 patch("src.ui.pages.audit_log._info", return_value=None):
                page._export_current_view()
            with target.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertGreaterEqual(len(rows), 2)
            self.assertEqual(rows[0][:5], ["Timestamp", "User", "Action", "Action Code", "Target"])
            self.assertIn("Employee Updated", rows[1])
            self.assertIn("employee.update", rows[1])
            self.assertIn("Audit export current item", rows[1])
            self.assertIn("Status: inactive", rows[1])
            self.assertIn("Status: active", rows[1])
        finally:
            try:
                target.unlink()
            except OSError:
                pass

    def test_audit_target_uses_readable_record_names(self):
        from datetime import datetime

        from src.database.models import AuditLog
        from src.ui.pages.audit_log import AuditLogPage

        with db.SessionLocal() as session:
            admin = session.query(db.SystemUser).filter_by(username="admin").one()
            title = session.query(db.Title).filter_by(name="L6").one()
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="settings.level_update",
                target_table="title",
                target_id=title.id,
                description="Level target smoke active",
                after_value=f'{{"name": "{title.name}", "label": "{title.label}"}}',
                performed_at=datetime.utcnow(),
            ))
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="settings.level_delete",
                target_table="title",
                target_id=99001,
                description="Level target smoke deleted",
                before_value='{"name": "S8", "label": "Interns"}',
                performed_at=datetime.utcnow(),
            ))
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="settings.database_health_check",
                description="Level target smoke database check",
                after_value='{"integrity": "ok"}',
                performed_at=datetime.utcnow(),
            ))
            session.add(AuditLog(
                performed_by_id=admin.id,
                performed_by_username="admin",
                performed_by_name="Smoke Admin",
                action="settings.export_yearly_report",
                description="Level target smoke report exported: 2026",
                after_value='{"year": 2026}',
                performed_at=datetime.utcnow(),
            ))
            session.commit()
            user = SimpleNamespace(id=admin.id, username=admin.username, role=admin.role, full_name=admin.full_name)

        page = AuditLogPage(user)
        page.search.setText("Level target smoke")
        page._filter()
        targets = [
            page.table.item(row, 3).text()
            for row in range(page.table.rowCount())
        ]
        actions = [
            page.table.item(row, 2).text()
            for row in range(page.table.rowCount())
        ]

        self.assertIn("L6 - Mid Level", targets)
        self.assertIn("S8 - Interns", targets)
        self.assertIn("Database", targets)
        self.assertIn("Yearly Report 2026", targets)
        self.assertTrue(all("Title #" not in target for target in targets))
        self.assertTrue(all(target != "-" for target in targets))
        self.assertIn("Level Updated", actions)
        self.assertIn("Level Deleted", actions)

    def test_hierarchy_canvas_lazy_expand_and_search_focus(self):
        from datetime import datetime

        from src.database.models import Employee, OrgUnit
        from src.ui.pages.hierarchy import HierarchyPage

        with db.SessionLocal() as session:
            title = session.query(db.Title).filter_by(name="L7").one()
            organization = OrgUnit(name="Canvas Org", unit_type="organization")
            engineering = OrgUnit(name="Canvas Engineering", unit_type="division", parent=organization)
            backend = OrgUnit(name="Canvas Backend", unit_type="department", parent=engineering)
            platform = OrgUnit(name="Canvas Platform", unit_type="unit", parent=backend)
            api_team = OrgUnit(name="Canvas API Team", unit_type="team", parent=platform)
            other_division = OrgUnit(name="Canvas Others", unit_type="division", parent=organization)
            session.add_all([organization, engineering, backend, platform, api_team, other_division])
            session.flush()
            manager = Employee(
                employee_id="CANVAS-0001",
                first_name="Sarah",
                last_name="Canvas",
                degree="BSc",
                work_email="sarah.canvas@example.test",
                position="Backend Lead",
                join_date=datetime.utcnow(),
                base_salary=2400,
                status="active",
                title_id=title.id,
                org_unit_id=api_team.id,
            )
            report = Employee(
                employee_id="CANVAS-0002",
                first_name="Report",
                last_name="Canvas",
                degree="BSc",
                work_email="report.canvas@example.test",
                position="Engineer",
                join_date=datetime.utcnow(),
                base_salary=2400,
                status="active",
                title_id=title.id,
                org_unit_id=api_team.id,
                reports_to=manager,
            )
            other_head = Employee(
                employee_id="CANVAS-0003",
                first_name="Other",
                last_name="Head",
                degree="Other",
                work_email="other.head@example.test",
                position="Other Employees Head",
                join_date=datetime.utcnow(),
                base_salary=2200,
                status="active",
                title_id=title.id,
                org_unit_id=other_division.id,
            )
            janitor = Employee(
                employee_id="CANVAS-0004",
                first_name="Leaf",
                last_name="Janitor",
                degree="Other",
                work_email="leaf.janitor@example.test",
                position="Janitor",
                join_date=datetime.utcnow(),
                base_salary=2000,
                status="active",
                title_id=title.id,
                org_unit_id=other_division.id,
                reports_to=other_head,
            )
            session.add_all([manager, report, other_head, janitor])
            session.flush()
            api_team.head_employee_id = manager.id
            other_division.head_employee_id = other_head.id
            session.commit()
            org_id = organization.id
            engineering_id = engineering.id
            backend_id = backend.id
            platform_id = platform.id
            team_id = api_team.id
            manager_id = manager.id
            report_id = report.id
            other_division_id = other_division.id
            other_head_id = other_head.id
            janitor_id = janitor.id

        user = type("User", (), {"id": 1, "username": "admin", "role": "admin", "full_name": "Smoke Admin"})()
        page = HierarchyPage(user)

        self.assertIn(("unit", org_id), page.node_items)
        self.assertIn(("unit", engineering_id), page.node_items)
        self.assertNotIn(("unit", backend_id), page.node_items)

        page._toggle_node(engineering_id)
        self.assertIn(("unit", backend_id), page.node_items)
        self.assertNotIn(("unit", platform_id), page.node_items)

        page._toggle_node(backend_id)
        self.assertIn(("unit", platform_id), page.node_items)

        page._toggle_node(platform_id)
        self.assertIn(("unit", team_id), page.node_items)
        self.assertNotIn(("employee", manager_id), page.node_items)

        page._toggle_node(team_id)
        self.assertNotIn(("employee", manager_id), page.node_items)
        self.assertIn(("employee", report_id), page.node_items)

        page._toggle_node(other_division_id)
        self.assertNotIn(("employee", other_head_id), page.node_items)
        self.assertIn(("employee", janitor_id), page.node_items)

        page.search.setText("Sarah Canvas")
        page._run_search()
        self.assertIsNotNone(page.selected_node)
        self.assertEqual(page.selected_node["kind"], "employee")
        self.assertEqual(page.selected_node["name"], "Sarah Canvas")


if __name__ == "__main__":
    unittest.main()
