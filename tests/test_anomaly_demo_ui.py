"""End-to-end smoke checks for the interactive anomaly demonstration."""

import os
from queue import Queue
import time
from types import SimpleNamespace
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.ui.pages.anomaly_review import AnomalyReviewPage, _demo_process_entry
from src.services.anomaly_detection import run_demo_scenario


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def completed_result():
    return run_demo_scenario(0, employee_count=120)


def _wait_until(app, predicate, timeout_ms=90_000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(25)
    raise AssertionError("asynchronous demonstration did not finish in time")


def test_demo_runs_and_drills_into_same_synthetic_employee(app):
    page = AnomalyReviewPage(SimpleNamespace(role="admin"))
    try:
        page._start_run()
        _wait_until(app, lambda: page._process is None)
        assert page.result is not None
        assert page.progress.value() == 100
        assert page.queue_table.rowCount() == len(page.result.queue)
        assert page.comparison_table.rowCount() == 4
        assert page.events_table.rowCount() > 0
        evidence_id = page.evidence_prompt.text().split(": ")[-1]
        assert evidence_id in page.result.evidence_by_employee_id
        assert page.run_button.isEnabled()
    finally:
        page.close()


def test_model_failure_is_visible_and_not_reported_as_success(app):
    page = AnomalyReviewPage(SimpleNamespace(role="admin"))
    try:
        page._on_failed("RuntimeError: model unavailable")
        assert page.result is None
        assert "model unavailable" in page.status.text()
        assert page.progress.value() == 0
        assert page.run_button.isEnabled()
    finally:
        page.close()


def test_process_boundary_reports_service_failure():
    output = Queue()
    _demo_process_entry(99, output)
    kind, message = output.get_nowait()
    assert kind == "failed"
    assert "unknown demonstration scenario" in message


def test_failed_rerun_clears_previous_results(app, completed_result):
    page = AnomalyReviewPage(SimpleNamespace(role="admin"))
    try:
        page._on_completed(completed_result)
        assert page.queue_table.rowCount() > 0
        page._on_failed("RuntimeError: second run failed")
        assert page.result is None
        assert page.queue_table.rowCount() == 0
        assert page.comparison_table.rowCount() == 0
        assert "second run failed" in page.status.text()
    finally:
        page.close()


def test_grandfathering_evidence_is_linked_to_source_event(app, completed_result):
    page = AnomalyReviewPage(SimpleNamespace(role="admin"))
    try:
        page._on_completed(completed_result)
        employee = next(
            evidence
            for evidence in completed_result.evidence_by_employee_id.values()
            if any(item.evidence_references for item in evidence.calculations)
        )
        calculation = next(
            item for item in employee.calculations if item.evidence_references
        )
        page._show_employee(employee.employee_id)
        trace = page.calculation_evidence.text()
        assert calculation.event_source_id in trace
        assert calculation.evidence_references[0] in trace
        assert any(
            event.source_id == calculation.event_source_id
            for event in employee.events
        )
    finally:
        page.close()


def test_demo_constructs_in_all_languages_and_themes(app):
    from src.core.i18n import get_language, set_language
    from src.ui.theme import apply_theme, theme_manager

    original_language = get_language()
    original_theme = theme_manager.theme
    try:
        for language in ("en", "hu", "ar"):
            set_language(language)
            for theme in ("light", "dark"):
                theme_manager.set_theme(theme, persist=False)
                apply_theme(app)
                page = AnomalyReviewPage(SimpleNamespace(role="admin"))
                page.resize(1024, 720)
                page.show()
                app.processEvents()
                assert "anomaly_demo_" not in page.run_button.text()
                assert page.tabs.count() == 4
                assert page.scenario_select.count() == 3
                assert not page.grab().isNull()
                page.close()
    finally:
        set_language(original_language)
        theme_manager.set_theme(original_theme, persist=False)
        apply_theme(app)


def test_completed_dynamic_content_is_localized(app, completed_result):
    from src.core.i18n import get_language, set_language, t

    original_language = get_language()
    try:
        for language in ("en", "hu", "ar"):
            set_language(language)
            page = AnomalyReviewPage(SimpleNamespace(role="admin"))
            try:
                page._on_completed(completed_result)
                assert page.scenario_select.label.text() == t("anomaly_demo_scenario_name").format(number=1)
                assert page.comparison_table.item(0, 0).text() == t("anomaly_demo_method_raw_matched")
                assert page.queue_table.item(0, 3).text() == page._reason_label(completed_result.queue[0])
                assert page.events_table.item(0, 2).text().lower() != "anomaly_demo_event_hire"
                assert "anomaly_demo_" not in page.limitations.text()
            finally:
                page.close()
    finally:
        set_language(original_language)
