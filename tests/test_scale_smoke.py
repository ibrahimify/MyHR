import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.database.connection as db
from src.database.models import (
    AuditLog,
    Base,
    Commendation,
    CommendationEmployee,
    Employee,
    OrgUnit,
    PromotionHistory,
    SalaryIncrementHistory,
    Sanction,
    SystemUser,
)


class ScaleSmokeTests(unittest.TestCase):
    EMPLOYEE_COUNT = 5000

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._old_engine = db.engine
        cls._old_session_local = db.SessionLocal
        cls._tmp = tempfile.NamedTemporaryFile(prefix="myhr_scale_test_", suffix=".db", delete=False)
        cls._tmp.close()
        cls.engine = create_engine(f"sqlite:///{cls._tmp.name}", echo=False)
        db.engine = cls.engine
        db.SessionLocal = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(cls.engine)
        db._migrate_schema()

        with db.SessionLocal() as session:
            db._seed_defaults(session)
            cls._seed_large_company(session, cls.EMPLOYEE_COUNT)
            cls._seed_active_sanctions(session, 37)
            cls._seed_scale_activity(session)

        from PySide6.QtWidgets import QApplication
        from src.ui.theme import apply_theme

        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        apply_theme(cls.app)

    @classmethod
    def tearDownClass(cls):
        db.SessionLocal = cls._old_session_local
        db.engine = cls._old_engine
        cls.engine.dispose()
        try:
            os.remove(cls._tmp.name)
        except OSError:
            pass

    @classmethod
    def _seed_large_company(cls, session, employee_count):
        titles = session.query(db.Title).all()
        root = OrgUnit(name="Scale Test Organization", unit_type="organization")
        session.add(root)
        session.flush()

        units = []
        for index in range(50):
            unit = OrgUnit(
                name=f"Scale Division {index + 1}",
                unit_type="division",
                parent_id=root.id,
            )
            session.add(unit)
            units.append(unit)
        session.flush()

        now = datetime.utcnow()
        employees = []
        for index in range(employee_count):
            employee_number = index + 1
            title = titles[index % len(titles)]
            employees.append(Employee(
                employee_id=f"EMP-S{employee_number:05d}",
                first_name=f"Employee{employee_number}",
                last_name="Scale",
                degree=("BSc", "MSc", "PhD")[index % 3],
                work_email=f"employee{employee_number}@scale.test",
                position="Staff",
                join_date=db._add_months(now, -(index % 108)),
                base_salary=2500 + (index % 1000),
                status="active",
                title_id=title.id,
                org_unit_id=units[index % len(units)].id,
            ))

        session.bulk_save_objects(employees)
        session.commit()

    @classmethod
    def _seed_active_sanctions(cls, session, sanction_count):
        employees = (
            session.query(Employee)
            .filter_by(status="active")
            .order_by(Employee.id.asc())
            .limit(sanction_count)
            .all()
        )
        sanctions = []
        for index, employee in enumerate(employees):
            sanctions.append(Sanction(
                sanction_ref=f"SAN-SCALE-{index + 1:03d}",
                employee_id=employee.id,
                sanction_type=("verbal_warning", "written_warning", "suspension")[index % 3],
                reason="Scale smoke sanction",
                delay_months=(index % 12) + 1,
                issued_by_id=1,
                issued_at=datetime.utcnow(),
                is_resolved=False,
            ))
        session.bulk_save_objects(sanctions)
        session.commit()

    @classmethod
    def _seed_scale_activity(cls, session):
        employees = (
            session.query(Employee)
            .filter_by(status="active")
            .order_by(Employee.id.asc())
            .limit(240)
            .all()
        )
        titles = {title.name: title for title in session.query(db.Title).all()}
        admin = session.query(SystemUser).filter_by(username="admin").first()
        admin_id = admin.id if admin else 1
        now = datetime.utcnow()

        commendations = []
        links = []
        for index, employee in enumerate(employees[:120]):
            commendation = Commendation(
                commendation_ref=f"COM-SCALE-{index + 1:03d}",
                title=f"Scale Commendation {index + 1}",
                description="Scale smoke commendation",
                category=(index % 3) + 1,
                months_impact=(-1, -3, -6)[index % 3],
                is_team_award=False,
                issued_by_id=admin_id,
                issued_at=now - timedelta(days=index % 90),
            )
            session.add(commendation)
            session.flush()
            links.append(CommendationEmployee(commendation_id=commendation.id, employee_id=employee.id))
            commendations.append(commendation)

        promo_from = titles.get("L7") or next(iter(titles.values()))
        promo_to = titles.get("L6") or promo_from
        histories = []
        increments = []
        resolved_sanctions = []
        for index, employee in enumerate(employees[120:200]):
            histories.append(PromotionHistory(
                employee_id=employee.id,
                from_title_id=promo_from.id,
                to_title_id=promo_to.id,
                approved_by_id=admin_id,
                basis="time_based",
                months_taken=36,
                notes="Scale smoke promotion",
                promoted_at=now - timedelta(days=index % 120),
            ))
            increments.append(SalaryIncrementHistory(
                employee_id=employee.id,
                approved_by_id=admin_id,
                salary_before=employee.base_salary,
                salary_after=employee.base_salary * 1.03,
                increment_type="percentage",
                increment_value=3.0,
                applied_at=now - timedelta(days=index % 120),
                notes="Scale smoke increment",
            ))

        for index, employee in enumerate(employees[:120]):
            resolved_sanctions.append(Sanction(
                sanction_ref=f"SAN-HIST-SCALE-{index + 1:03d}",
                employee_id=employee.id,
                sanction_type=("verbal_warning", "written_warning", "suspension", "final_warning")[index % 4],
                reason="Scale smoke resolved sanction",
                delay_months=(index % 12) + 1,
                issued_by_id=admin_id,
                issued_at=now - timedelta(days=180 + index),
                resolved_at=now - timedelta(days=90 + index),
                is_resolved=True,
            ))

        logs = []
        targets = ["employee", "promotion", "commendation", "sanction", "hierarchy"]
        actions = [
            "employee.create",
            "promotion.approve",
            "commendation.issue",
            "sanction.issue",
            "org_unit.update",
        ]
        for index in range(300):
            logs.append(AuditLog(
                performed_by_id=admin_id,
                performed_by_username="admin",
                performed_by_name="Scale Admin",
                action=actions[index % len(actions)],
                target_table=targets[index % len(targets)],
                target_id=(index % max(len(employees), 1)) + 1,
                description=f"Scale audit event {index + 1}",
                performed_at=now - timedelta(minutes=index),
            ))

        session.bulk_save_objects(links)
        session.bulk_save_objects(histories)
        session.bulk_save_objects(increments)
        session.bulk_save_objects(resolved_sanctions)
        session.bulk_save_objects(logs)
        session.commit()

    def _admin_user(self):
        return SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")

    def _assert_under(self, label, started, seconds=8.0):
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, seconds, f"{label} took {elapsed:.2f}s")
        return elapsed

    def _assert_eager_picker_cache(self, options):
        self.assertGreater(len(options), self.EMPLOYEE_COUNT * 0.75)

    def test_dashboard_and_employee_list_handle_5000_employees(self):
        from src.ui.pages.dashboard import DashboardPage
        from src.ui.pages.employees import EmployeesPage

        user = self._admin_user()

        started = time.perf_counter()
        dashboard = DashboardPage(user, lambda key: None)
        dashboard_seconds = self._assert_under("DashboardPage", started)
        try:
            self.assertEqual(dashboard.emp_count, self.EMPLOYEE_COUNT)
            self.assertLess(dashboard_seconds, 8.0)
        finally:
            dashboard.close()

        started = time.perf_counter()
        employees = EmployeesPage(user)
        employees_seconds = self._assert_under("EmployeesPage", started)
        try:
            self.assertEqual(employees.list_page.total_count, self.EMPLOYEE_COUNT)
            self.assertEqual(employees.list_page.table.rowCount(), employees.list_page.page_size)
            self.assertEqual(employees.list_page.total_pages, 100)
            self.assertLess(employees_seconds, 8.0)
        finally:
            employees.close()

    def test_main_window_dashboard_has_no_stylesheet_parse_warnings(self):
        from PySide6.QtCore import qInstallMessageHandler
        from src.ui.main_window import MainWindow

        messages = []

        def handler(_mode, _context, message):
            messages.append(message)

        previous = qInstallMessageHandler(handler)
        try:
            admin = SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")
            window = MainWindow(admin)
            try:
                self.app.processEvents()
            finally:
                window.close()
        finally:
            qInstallMessageHandler(previous)

        parse_warnings = [
            message for message in messages
            if "Could not parse stylesheet" in message
        ]
        self.assertEqual(parse_warnings, [])

    def test_active_sanctions_are_paginated_at_scale(self):
        from src.ui.pages.sanctions import ActiveSanctionsTab

        user = self._admin_user()
        tab = ActiveSanctionsTab(user)
        try:
            tab.refresh()
            self.assertEqual(tab.total_pages, 4)
            self.assertEqual(tab.table.rowCount(), tab.page_size)
            self.assertEqual(tab.page_lbl.text(), "Page 1 of 4")
        finally:
            tab.close()

    def test_hierarchy_promotions_commendations_sanctions_and_audit_handle_scale(self):
        from src.ui.pages.audit_log import AuditLogPage
        from src.ui.pages.commendations import CommendationsPage
        from src.ui.pages.hierarchy import HierarchyPage
        from src.ui.pages.promotions import PromotionsPage
        from src.ui.pages.sanctions import SanctionsPage

        user = self._admin_user()

        started = time.perf_counter()
        hierarchy = HierarchyPage(user)
        self._assert_under("HierarchyPage", started)
        try:
            self.assertGreaterEqual(len(hierarchy.node_items), 1)
            self.assertLess(len(hierarchy.node_items), self.EMPLOYEE_COUNT)
        finally:
            hierarchy.close()

        started = time.perf_counter()
        promotions = PromotionsPage(user)
        promotions.eligible_tab.refresh()
        self._assert_under("PromotionsPage eligible refresh", started, seconds=12.0)
        try:
            self.assertLessEqual(promotions.eligible_tab.table.rowCount(), promotions.eligible_tab.page_size)
            self.assertGreater(promotions.eligible_tab.total_pages, 1)
            promotions.history_tab.refresh()
            self.assertEqual(promotions.history_tab.table.rowCount(), promotions.history_tab.page_size)
        finally:
            promotions.close()

        started = time.perf_counter()
        commendations = CommendationsPage(user)
        commendations.issue_tab.refresh_employees()
        self._assert_under("CommendationsPage", started, seconds=10.0)
        try:
            self._assert_eager_picker_cache(commendations.issue_tab.employee_options)
            self.assertLessEqual(commendations.issue_tab.single_list.count(), 150)
            commendations.tabs.setCurrentIndex(1)
            commendations.history_tab.refresh()
            self.assertEqual(commendations.history_tab.table.rowCount(), commendations.history_tab.page_size)
            self.assertGreater(commendations.history_tab.total_pages, 1)
        finally:
            commendations.close()

        started = time.perf_counter()
        sanctions = SanctionsPage(user)
        self._assert_under("SanctionsPage", started, seconds=10.0)
        try:
            self._assert_eager_picker_cache(sanctions.issue_tab.employee_options)
            self.assertLessEqual(sanctions.issue_tab.emp_list.count(), 150)
            sanctions.history_tab.refresh()
            self.assertEqual(sanctions.history_tab.table.rowCount(), sanctions.history_tab.page_size)
            self.assertGreater(sanctions.history_tab.total_pages, 1)
            sanctions.active_tab.refresh()
            self.assertLessEqual(sanctions.active_tab.table.rowCount(), sanctions.active_tab.page_size)
        finally:
            sanctions.close()

        started = time.perf_counter()
        audit = AuditLogPage(user)
        self._assert_under("AuditLogPage", started, seconds=10.0)
        try:
            self.assertEqual(audit.table.rowCount(), audit.page_size)
            self.assertGreater(audit.total_pages, 1)
            self.assertFalse(hasattr(audit, "all_logs") and audit.all_logs)
            self.assertFalse(hasattr(audit, "filtered_logs") and audit.filtered_logs)
        finally:
            audit.close()

    def test_sidebar_selected_item_keeps_left_rail(self):
        from src.ui.main_window import Sidebar

        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")
        sidebar = Sidebar(user, on_navigate=lambda _key: None, on_logout=lambda: None)
        try:
            dashboard_btn, _ = sidebar.nav_buttons["dashboard"]
            employees_btn, _ = sidebar.nav_buttons["employees"]

            self.assertIn("border-left: 3px solid", dashboard_btn.styleSheet())
            self.assertIn("border-left: 3px solid transparent", employees_btn.styleSheet())

            sidebar._set_active("employees")
            self.assertIn("border-left: 3px solid", employees_btn.styleSheet())
            self.assertIn("border-left: 3px solid transparent", dashboard_btn.styleSheet())
        finally:
            sidebar.close()

    def test_theme_switch_rebuilds_cached_pages_to_avoid_stale_styles(self):
        from src.ui.main_window import MainWindow
        from src.ui.theme import THEME_DARK, THEME_LIGHT, theme_manager

        original_theme = theme_manager.theme
        target_theme = THEME_DARK if original_theme != THEME_DARK else THEME_LIGHT
        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")
        window = MainWindow(user)
        try:
            window._navigate("employees", animate=False)
            old_employees_page = window._pages_cache["employees"]
            window._navigate("hierarchy", animate=False)
            self.assertNotIn("employees", window._pages_cache)

            theme_manager.set_theme(target_theme, persist=False)
            self.app.processEvents()

            self.assertNotIn("employees", window._pages_cache)
            window._navigate("employees", animate=False)
            self.assertIsNot(window._pages_cache["employees"], old_employees_page)
        finally:
            window.close()
            theme_manager.set_theme(original_theme, persist=False)

    def test_theme_switch_keeps_settings_subpage(self):
        from src.ui.main_window import MainWindow
        from src.ui.theme import THEME_DARK, THEME_LIGHT, theme_manager

        original_theme = theme_manager.theme
        target_theme = THEME_DARK if original_theme != THEME_DARK else THEME_LIGHT
        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")
        window = MainWindow(user)
        try:
            window._navigate("settings", animate=False)
            page = window.stack.currentWidget()
            database_index = page.tabs.count() - 1
            page.tabs.setCurrentIndex(database_index)
            self.assertEqual(page.tabs.currentIndex(), database_index)

            theme_manager.set_theme(target_theme, persist=False)
            self.app.processEvents()

            page = window.stack.currentWidget()
            self.assertEqual(page.tabs.currentIndex(), database_index)
        finally:
            window.close()
            theme_manager.set_theme(original_theme, persist=False)
