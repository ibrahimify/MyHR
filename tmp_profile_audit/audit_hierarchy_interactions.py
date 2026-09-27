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
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme, theme_manager, THEME_LIGHT


def pump(app, count=8):
    for _ in range(count):
        app.processEvents()


def save(window, name):
    path = ROOT / "tmp_profile_audit" / name
    window.grab().save(str(path))
    print(path)


def main():
    init_db()
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    theme_manager.set_theme(THEME_LIGHT, persist=False)
    apply_theme(app)
    user = SimpleNamespace(id=1, username="admin", role="admin", full_name="Perf Admin")
    window = MainWindow(user)
    window.showNormal()
    window.resize(1366, 768)
    window._navigate("hierarchy", animate=False)
    pump(app, 16)
    page = window._pages_cache["hierarchy"]
    save(window, "hierarchy_audit_01_initial.png")
    initial_nodes = len(page.node_items)

    child_keys = [key for key in page.node_items.keys() if key != ("unit", page.selected_node["id"])]
    if child_keys:
        item = page.node_items[child_keys[0]]
        page._select_node(item.data)
        pump(app)
        save(window, "hierarchy_audit_01b_select_child.png")
        if item.data.get("has_children"):
            page._toggle_node(item.data["id"], item.data.get("kind", "unit"))
            pump(app)
            save(window, "hierarchy_audit_01c_expand_child.png")

    page._zoom(1.15)
    pump(app)
    save(window, "hierarchy_audit_02_zoom_in.png")

    page._zoom(0.85)
    page._fit_canvas()
    pump(app)
    save(window, "hierarchy_audit_03_fit_view.png")

    page._export_canvas_snapshot()
    pump(app)
    print(ROOT / "tmp_profile_audit" / "org_hierarchy_export.png")

    page.search.setText("admin")
    page._run_search()
    pump(app)
    save(window, "hierarchy_audit_04_search.png")

    page.search.clear()
    pump(app)
    if page.division_filter.count() > 1:
        page.division_filter.setCurrentIndex(1)
        pump(app)
        save(window, "hierarchy_audit_05_division_filter.png")
        page.division_filter.setCurrentIndex(0)
        pump(app)

    page._view_selected_profile()
    pump(app)
    save(window, "hierarchy_audit_06_view_profile.png")

    print(f"initial_nodes={initial_nodes} final_nodes={len(page.node_items)} edges={len(page.edge_items)}")
    window.close()


if __name__ == "__main__":
    main()
