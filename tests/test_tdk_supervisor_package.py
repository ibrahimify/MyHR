import re
import tempfile
import unittest
from pathlib import Path

from docx import Document

from scripts.generate_tdk_supervisor_package import TITLE, build_decision_sheet


REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER_SOURCE = REPO_ROOT / "docs" / "TDK_PAPER_DRAFT.md"
PACKAGE_SCRIPT = REPO_ROOT / "scripts" / "generate_tdk_supervisor_package.py"


class TdkSupervisorPackageTests(unittest.TestCase):
    def test_manuscript_source_has_stable_title_and_complete_figures(self):
        text = PAPER_SOURCE.read_text(encoding="utf-8")

        self.assertEqual(
            TITLE,
            "MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression",
        )
        self.assertTrue(text.startswith(f"# {TITLE}\n"))
        figures = re.findall(r"\[\[FIGURE:([^|]+)\|([^\]]+)\]\]", text)
        self.assertEqual(11, len(figures))
        self.assertEqual(len(figures), len({name for name, _ in figures}))
        self.assertNotIn("**Keywords:**", text)
        for marker in ("TODO", "TBD", "PLACEHOLDER"):
            self.assertNotIn(marker, text)

    def test_manuscript_preserves_scientific_and_holdout_boundaries(self):
        text = PAPER_SOURCE.read_text(encoding="utf-8")

        required_statements = (
            "No policy-aware advantage was demonstrated in this exploratory development run",
            "b866ae2aa1b4b479",
            "does not establish equivalence",
            "The final holdout has not been generated or accessed.",
        )
        for statement in required_statements:
            self.assertIn(statement, text)
        self.assertIn("0 of 72", text)
        self.assertIn("Only that `8/72` false-positive interpretation is invalidated", text)
        self.assertIn("designed specification counterexample", text)
        self.assertIn("`deterministic_rules` result is `0/72`", text)
        self.assertIn("does not preserve employee-specific entitlement evidence", text)
        self.assertNotIn("Both interpretations are invalidated", text)
        self.assertIn("explicit evaluation universe", text)
        self.assertIn("this is a design inference applied to the present experiment", text)
        self.assertNotRegex(text, r"(?i)policy-aware (?:isolation forest )?(?:outperforms|is superior)")
        self.assertNotRegex(text, r"(?i)run[_ -]purpose\s*[=:]\s*holdout")
        package_script = PACKAGE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("39/72 is a constructed specification counterexample", package_script)
        self.assertIn("8/72 was invalidated", package_script)

    def test_decision_sheet_is_one_landscape_page_source_with_pending_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "decision.docx"
            build_decision_sheet(output)
            document = Document(output)

        section = document.sections[0]
        self.assertGreater(section.page_width, section.page_height)
        self.assertEqual(1, len(document.tables))
        self.assertEqual(8, len(document.tables[0].rows))
        all_text = "\n".join(
            cell.text for row in document.tables[0].rows for cell in row.cells
        )
        self.assertIn("Scenario proposals", all_text)
        self.assertIn("Freeze and holdout", all_text)
        self.assertIn("[ ] Approve", all_text)


if __name__ == "__main__":
    unittest.main()
