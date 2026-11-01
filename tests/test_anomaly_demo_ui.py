"""End-to-end smoke checks for the interactive anomaly demonstration."""

import os
from dataclasses import replace
from pathlib import Path
from queue import Queue
import tempfile
import time
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

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

    def test_progressive_disclosure_and_truth_boundary(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            self.assertFalse(page.guide_panel.isVisible())
            self.assertFalse(page.scenario_details.isVisible())
            self.assertFalse(page.events_table.isVisible())
            self.assertFalse(page.truth_cases_table.isVisible())
            self.assertFalse(page.export_button.isEnabled())
            page.help_button.click()
            self.assertFalse(page.guide_panel.isHidden())
            guide_text = " ".join(
                label.text()
                for label in page.guide_terms_widget.findChildren(QLabel)
            )
            self.assertIn("Review priority", guide_text)
            page.tabs.setCurrentIndex(2)
            guide_text = " ".join(
                label.text()
                for label in page.guide_terms_widget.findChildren(QLabel)
            )
            self.assertIn("Equal capacity", guide_text)
            page.guide_close_button.click()
            self.assertTrue(page.guide_panel.isHidden())
            self.assertFalse(page.help_button.isChecked())
            page._on_completed(self.completed_result)
            self.assertTrue(page.export_button.isEnabled())
            self.assertEqual(
                page.outcome_matrix.rowCount(),
                3,
            )
            self.assertEqual(
                page.truth_cases_table.rowCount(),
                sum(
                    case.category != "ordinary"
                    for case in self.completed_result.truth_cases
                ),
            )
        finally:
            page.close()

    def test_queue_search_and_evidence_empty_state_are_semantic(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            employee_id = self.completed_result.queue[0].employee_id
            page.queue_search.setText(employee_id)
            self.app.processEvents()
            self.assertEqual(page.queue_table.rowCount(), 1)
            self.assertEqual(page.queue_table.item(0, 0).text(), employee_id)

            without_calculation = next(
                evidence
                for evidence in self.completed_result.evidence_by_employee_id.values()
                if not evidence.calculations
            )
            page._show_employee(without_calculation.employee_id)
            self.assertFalse(page.no_calculation_label.isHidden())
            self.assertTrue(page.calculation_table.isHidden())
            self.assertTrue(page.service_arithmetic.isHidden())
        finally:
            page.close()

    def test_comparison_copy_is_derived_from_live_outcomes(self):
        from src.core.i18n import t

        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            policy = next(
                item
                for item in self.completed_result.comparisons
                if item.representation == "policy_matched"
            )
            wrong = next(
                item
                for item in self.completed_result.comparisons
                if item.representation == "wrong_policy_control"
            )
            if policy.true_positives == 0:
                expected = t("anomaly_demo_interpretation_zero")
            elif (
                policy.true_positives == wrong.true_positives
                and policy.false_positives == wrong.false_positives
            ):
                expected = t("anomaly_demo_interpretation_no_attribution")
            else:
                expected = t("anomaly_demo_interpretation_exploratory")
            self.assertEqual(page.comparison_interpretation.text(), expected)
            self.assertIn(
                str(self.completed_result.model_estimators),
                page.scenario_detail_values["model"].text(),
            )
        finally:
            page.close()

    def test_comparison_visuals_and_evaluation_table_match_live_results(self):
        from src.ui.theme import apply_theme, theme_manager, tokens

        original_theme = theme_manager.theme
        try:
            theme_manager.set_theme("light", persist=False)
            apply_theme(self.app)
            page = AnomalyReviewPage(SimpleNamespace(role="admin"))
            page._on_completed(self.completed_result)
            page.resize(1500, 900)
            page.show()
            page.tabs.setCurrentIndex(2)
            self.app.processEvents()

            chart_image = page.comparison_chart.grab().toImage()
            chart_colors = {
                chart_image.pixelColor(x, y).name()
                for x in range(chart_image.width())
                for y in range(chart_image.height())
            }
            self.assertIn(tokens().brand.lower(), chart_colors)
            self.assertIn(tokens().brand_accent.lower(), chart_colors)
            self.assertNotIn("#2f80ed", chart_colors)
            self.assertIn(tokens().surface_muted, page.comparison_table.styleSheet())
            self.assertIn(
                f"background: {tokens().brand}",
                page.tabs.styleSheet(),
            )

            self.assertEqual(
                page.evaluation_method_table.rowCount(),
                len(self.completed_result.comparisons),
            )
            for row, comparison in enumerate(self.completed_result.comparisons):
                self.assertEqual(
                    page.evaluation_method_table.item(row, 1).text(),
                    str(comparison.true_positives),
                )
                self.assertEqual(
                    page.evaluation_method_table.item(row, 2).text(),
                    str(comparison.false_negatives),
                )
                self.assertEqual(
                    page.evaluation_method_table.item(row, 3).text(),
                    str(comparison.false_positives),
                )
                self.assertEqual(
                    page.evaluation_method_table.item(row, 4).text(),
                    str(comparison.review_count),
                )
            self.assertIn(
                str(page.employee_select.count()),
                page.employee_position.text(),
            )
            page.close()
        finally:
            theme_manager.set_theme(original_theme, persist=False)
            apply_theme(self.app)

    def test_undefined_recall_is_reported_not_drawn_as_zero(self):
        from src.core.i18n import t

        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            comparisons = tuple(
                replace(item, recall=None, true_positives=0, false_negatives=0)
                for item in self.completed_result.comparisons
            )
            result = replace(
                self.completed_result,
                comparisons=comparisons,
                evaluation=replace(
                    self.completed_result.evaluation,
                    positive_count=0,
                    true_positives=0,
                    false_negatives=0,
                    recall=None,
                ),
            )
            page._on_completed(result)
            self.assertEqual(page.comparison_table.item(0, 5).text(), t("anomaly_demo_undefined"))
            self.assertEqual(
                page.comparison_interpretation.text(),
                t("anomaly_demo_interpretation_no_positives"),
            )
            self.assertFalse(page.comparison_chart.grab().isNull())
        finally:
            page.close()

    def test_minimum_window_content_uses_compact_layout(self):
        from src.core.i18n import t

        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page.resize(760, 660)
            page.show()
            self.app.processEvents()
            self.assertTrue(page.queue_table.isColumnHidden(1))
            self.assertTrue(page.queue_table.isColumnHidden(2))
            self.assertEqual(
                page.tabs.tabText(2),
                t("anomaly_demo_tab_comparison_short"),
            )
            self.assertFalse(page.demo_badge.isVisible())
            page.help_button.click()
            self.app.processEvents()
            self.assertFalse(page.guide_panel.isHidden())
            self.assertLess(
                page.guide_panel.geometry().y(),
                page.main_workspace.geometry().y(),
            )
            self.assertEqual(
                page.stat_grid.getItemPosition(
                    page.stat_grid.indexOf(page.stat_cards[2])
                )[:2],
                (1, 0),
            )
        finally:
            page.close()

    def test_csv_report_contains_exact_configuration_and_separate_truth(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.csv"
                page._write_csv_report(str(path))
                report = path.read_text(encoding="utf-8-sig")
            self.assertIn("Nominal review capacity,0.1", report)
            self.assertIn("Realized review capacity,0.125", report)
            self.assertIn("Model trees,", report)
            self.assertIn("SYNTHETIC EVALUATION ONLY", report)
            self.assertIn("policy_matched_flagged", report)
        finally:
            page.close()

    def test_pdf_report_is_written_from_the_same_verified_result(self):
        page = AnomalyReviewPage(SimpleNamespace(role="admin"))
        try:
            page._on_completed(self.completed_result)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.pdf"
                page._write_pdf_report(str(path))
                payload = path.read_bytes()
            self.assertTrue(payload.startswith(b"%PDF"))
            self.assertGreater(len(payload), 1_000)
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
        from src.ui.theme import apply_theme, theme_manager, tokens

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
                    self.assertIn(tokens().surface, page.export_menu.styleSheet())
                    self.assertIn(tokens().text, page.export_menu.styleSheet())
                    self.assertEqual(len(page.export_menu.actions()), 2)
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
                        t("anomaly_demo_population_stable_administration"),
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
