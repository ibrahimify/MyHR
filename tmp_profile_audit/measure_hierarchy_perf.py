import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from src.database.connection import init_db
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme


def main(label="MEASURE"):
    init_db()
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    apply_theme(app)
    user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Perf Admin")
    started = time.perf_counter()
    window = MainWindow(user)
    window.showNormal()
    window.resize(1366, 768)
    for _ in range(8):
        app.processEvents()
    nav_started = time.perf_counter()
    window._navigate("hierarchy", animate=False)
    for _ in range(12):
        app.processEvents()
    nav_elapsed = time.perf_counter() - nav_started
    total_elapsed = time.perf_counter() - started
    page = window._pages_cache.get("hierarchy")
    nodes = len(page.node_items) if page else -1
    edges = len(page.edge_items) if page else -1
    print(f"{label} hierarchy_nav_seconds={nav_elapsed:.4f} total_window_seconds={total_elapsed:.4f} nodes={nodes} edges={edges}")
    window.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "MEASURE")
