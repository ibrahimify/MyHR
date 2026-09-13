import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from src.database.connection import init_db
from src.ui.pages.dashboard import DashboardPage
from src.ui.theme import THEME_DARK, THEME_LIGHT, apply_theme, theme_manager


def capture(theme, width, height):
    theme_manager.set_theme(theme, persist=False)
    app = QApplication.instance()
    apply_theme(app)
    user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Admin")
    window = DashboardPage(user, lambda _key: None)
    window.resize(width, height)
    window.show()
    for _ in range(8):
        app.processEvents()
    path = ROOT / "tmp_audit" / f"dashboard_{theme}_{width}x{height}.png"
    pixmap = window.grab()
    pixmap.save(str(path))
    window.close()
    app.processEvents()
    print(path)


def main():
    init_db()
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    for theme in (THEME_LIGHT, THEME_DARK):
        for width, height in ((1366, 768), (1920, 1080)):
            capture(theme, width, height)


if __name__ == "__main__":
    main()
