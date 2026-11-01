"""End-to-end smoke checks for the interactive anomaly demonstration."""

import os
from queue import Queue
import time
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.services.anomaly_detection import run_demo_scenario
from src.ui.pages.anomaly_review import AnomalyReviewPage, _demo_process_entry


def _wait_until(app, predicate, timeout_ms=90_000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(25)
    raise AssertionError("asynchronous demonstration did not finish in time")


class AnomalyDemoUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.completed_result = run_demo_scenario(0, employee_count=120)

    def test_demo_runs_and_drills_into_same_synthetic_employee(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._start_run()
            _wait_until(self.app, lambda: page._process is None)
            self.assertIsNotNone(page.result)
            self.assertEqual(page.progress.value(), 100)
            self.assertEqual(page.queue_table.rowCount(), len(page.result.queue))
            self.assertEqual(page.comparison_table.rowCount(), 4)
            self.assertGreater(page.events_table.rowCount(), 0)
            evidence_id = page.evidence_prompt.text().split(": ")[-1]
            self.assertIn(evidence_id, page.result.evidence_by_employee_id)
            self.assertTrue(page.run_button.isEnabled())
        finally:
            page.close()

    def test_model_failure_is_visible_and_not_reported_as_success(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_failed("RuntimeError: model unavailable")
            self.assertIsNone(page.result)
            self.assertIn("model unavailable", page.status.text())
            self.assertEqual(page.progress.value(), 0)
            self.assertTrue(page.run_button.isEnabled())
        finally:
            page.close()

    def test_process_boundary_reports_service_failure(self):
        output = Queue()
        _demo_process_entry(99, output)
        kind, message = output.get_nowait()
        self.assertEqual(kind, "failed")
        self.assertIn("unknown demonstration scenario", message)

    def test_failed_rerun_clears_previous_results(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            self.assertGreater(page.queue_table.rowCount(), 0)
            page._on_failed("RuntimeError: second run failed")
            self.assertIsNone(page.result)
            self.assertEqual(page.queue_table.rowCount(), 0)
            self.assertEqual(page.comparison_table.rowCount(), 0)
            self.assertIn("second run failed", page.status.text())
        finally:
            page.close()

    def test_grandfathering_evidence_is_linked_to_source_event(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            employee = next(
                evidence
                for evidence in self.completed_result.evidence_by_employee_id.values()
                if any(item.evidence_references for item in evidence.calculations)
            )
            calculation = next(
                item for item in employee.calculations if item.evidence_references
            )
            page._show_employee(employee.employee_id)
            trace = page.calculation_evidence.text()
            self.assertIn(calculation.event_source_id, trace)
            self.assertIn(calculation.evidence_references[0], trace)
            self.assertTrue(
                any(
                    event.source_id == calculation.event_source_id
                    for event in employee.events
                )
            )
        finally:
            page.close()

    def test_demo_constructs_in_all_languages_and_themes(self):
        from src.core.i18n import get_language, set_language
        from src.ui.theme import apply_theme, theme_manager

        original_language = get_language()
        original_theme = theme_manager.theme
        try:
            for language in ("en", "hu", "ar"):
                set_language(language)
                for theme in ("light", "dark"):
                    theme_manager.set_theme(theme, persist=False)
                    apply_theme(self.app)
                    page = AnomalyReviewPage(SimpleNamespace(role="admin"))
                    page.resize(1024, 720)
                    page.show()
                    self.app.processEvents()
                    self.assertNotIn("anomaly_demo_", page.run_button.text())
                    self.assertEqual(page.tabs.count(), 4)
                    self.assertEqual(page.scenario_select.count(), 3)
                    self.assertFalse(page.grab().isNull())
                    page.close()
        finally:
            set_language(original_language)
            theme_manager.set_theme(original_theme, persist=False)
            apply_theme(self.app)

    def test_completed_dynamic_content_is_localized(self):
        from src.core.i18n import get_language, set_language, t

        original_language = get_language()
        try:
            for language in ("en", "hu", "ar"):
                set_language(language)
                page = AnomalyReviewPage(SimpleNamespace(role="admin"))
                try:
                    page._on_completed(self.completed_result)
                    self.assertEqual(
                        page.scenario_select.label.text(),
                        t("anomaly_demo_scenario_name").format(number=1),
                    )
                    self.assertEqual(
                        page.comparison_table.item(0, 0).text(),
                        t("anomaly_demo_method_raw_matched"),
                    )
                    self.assertEqual(
                        page.queue_table.item(0, 3).text(),
                        page._reason_label(self.completed_result.queue[0]),
                    )
                    self.assertNotEqual(
                        page.events_table.item(0, 2).text().lower(),
                        "anomaly_demo_event_hire",
                    )
                    self.assertNotIn("anomaly_demo_", page.limitations.text())
                finally:
                    page.close()
        finally:
            set_language(original_language)


if __name__ == "__main__":
    unittest.main()
