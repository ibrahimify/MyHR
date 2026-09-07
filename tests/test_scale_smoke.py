import os
import tempfile
import time
import unittest
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.database.connection as db
from src.database.models import Base, Employee, OrgUnit, SystemUser


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

    def test_dashboard_and_employee_list_handle_5000_employees(self):
        from src.ui.pages.dashboard import DashboardPage
        from src.ui.pages.employees import EmployeesPage

        user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Scale Admin")

        started = time.perf_counter()
        dashboard = DashboardPage(user, lambda key: None)
        dashboard_seconds = time.perf_counter() - started
        try:
            self.assertEqual(dashboard.emp_count, self.EMPLOYEE_COUNT)
            self.assertLess(dashboard_seconds, 8.0)
        finally:
            dashboard.close()

        started = time.perf_counter()
        employees = EmployeesPage(user)
        employees_seconds = time.perf_counter() - started
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
