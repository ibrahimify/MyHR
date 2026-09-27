import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from src.database.connection import get_session, init_db
from src.database.models import Employee
from src.ui.main_window import MainWindow
from src.ui.theme import THEME_DARK, THEME_LIGHT, apply_theme, theme_manager


def profile_employee_id():
    session = get_session()
    try:
        employee = (
            session.query(Employee)
            .filter(Employee.first_name == "Michael", Employee.last_name == "Brown")
            .first()
        )
        if employee is None:
            employee = session.query(Employee).order_by(Employee.id).first()
        return employee.id
    finally:
        session.close()


def capture(theme, width, height, employee_id):
    theme_manager.set_theme(theme, persist=False)
    app = QApplication.instance()
    apply_theme(app)
    user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Orban Viktor")
    window = MainWindow(user)
    window.showNormal()
    window.resize(width, height)
    window._navigate("employees", animate=False)
    page = window._pages_cache["employees"]
    page.profile_page.editing = False
    page.profile_page.load(employee_id)
    page.stack.setCurrentWidget(page.profile_page)
    window.stack.setCurrentWidget(page)
    for _ in range(12):
        app.processEvents()
    path = ROOT / "tmp_profile_audit" / f"employee_profile_refined_{theme}_{width}x{height}.png"
    window.grab().save(str(path))
    window.close()
    app.processEvents()
    print(path)


def main():
    init_db()
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    employee_id = profile_employee_id()
    for theme in (THEME_LIGHT, THEME_DARK):
        for width, height in ((1366, 768), (1920, 1080)):
            capture(theme, width, height, employee_id)


if __name__ == "__main__":
    main()
