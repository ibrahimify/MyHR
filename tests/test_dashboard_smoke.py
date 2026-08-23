import os
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
        combo.setCurrentIndex(combo.findData("percentage"))
        spin.setValue(4.5)

        with patch("src.ui.pages.settings._information", return_value=None):
            salary_tab._save()
            increment_tab._save()

        with db.SessionLocal() as session:
            updated = session.query(db.Title).filter_by(id=title_id).one()
            self.assertEqual(updated.name, "Entry Track")
            self.assertEqual(updated.base_salary_min, 2200)
            self.assertEqual(updated.base_salary_max, 2900)
            self.assertEqual(updated.currency, "HUF")
            self.assertEqual(updated.annual_increment_type, "percentage")
            self.assertEqual(updated.annual_increment_value, 4.5)
            updated.name = "L7"
            updated.label = "Entry Level"
            updated.base_salary_min = 2000
            updated.base_salary_max = 2800
            updated.currency = "EUR"
            updated.annual_increment_type = "percentage"
            updated.annual_increment_value = 3.0
            session.commit()

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
