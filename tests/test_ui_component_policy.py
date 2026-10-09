import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOTS = [
    ROOT / "src" / "ui" / "components",
    ROOT / "src" / "ui" / "pages",
    ROOT / "src" / "ui" / "login_window.py",
    ROOT / "src" / "ui" / "main_window.py",
]


class UIComponentPolicyTests(unittest.TestCase):
    def _ui_files(self):
        files = []
        for root in UI_ROOTS:
            if root.is_file():
                files.append(root)
            else:
                files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
        return files

    def test_application_dropdowns_use_app_select(self):
        offenders = []
        for path in self._ui_files():
            text = path.read_text(encoding="utf-8")
            if "QComboBox(" in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(
            offenders,
            [],
            "Use src.ui.components.app_select.AppSelect for dropdowns, not QComboBox.",
        )

    def test_pages_do_not_define_standalone_dropdown_widgets(self):
        offenders = []
        allowed = {
            Path("src/ui/components/app_select.py"),
            Path("src/ui/login_window.py"),
        }
        for path in self._ui_files():
            rel = path.relative_to(ROOT)
            if rel in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"class\s+\w*Select\s*\(\s*QWidget\s*\)", text):
                offenders.append(str(rel))
            if "QListWidget::item:selected" in text:
                offenders.append(str(rel))
        self.assertEqual(
            sorted(set(offenders)),
            [],
            "Do not build page-local dropdowns. Use AppSelect or subclass AppSelect.",
        )


if __name__ == "__main__":
    unittest.main()
