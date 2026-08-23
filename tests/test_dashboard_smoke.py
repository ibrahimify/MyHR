import os
import tempfile
import unittest
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
