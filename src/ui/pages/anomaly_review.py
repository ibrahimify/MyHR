"""Interactive, synthetic-only demonstration of the research pipeline."""

from __future__ import annotations

import multiprocessing
from queue import Empty

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import t
from src.services.anomaly_detection import (
    DemoEmployeeEvidence,
    DemoRunResult,
    demo_scenario_options,
    run_demo_scenario,
)
from src.ui.components.app_select import AppSelect
from src.ui.icons import app_icon, app_pixmap
from src.ui.styles import (
    alert_ss,
    btn_outline,
    btn_primary,
    card_ss,
    enable_table_row_selection,
    pill_tab_ss,
    semantic_badge_ss,
    sync_table_widget_cells,
    table_style,
)
from src.ui.theme import tokens


_DEMO_EMPLOYEE_COUNT = 120


def _demo_process_entry(option_index: int, output_queue) -> None:
    """Run native ML outside Qt's process and return presentation-safe data."""
    try:
        result = run_demo_scenario(
            option_index,
            employee_count=_DEMO_EMPLOYEE_COUNT,
            progress=lambda value, stage: output_queue.put(("progress", value, stage)),
        )
        output_queue.put(("completed", result))
    except Exception as exc:
        output_queue.put(("failed", f"{type(exc).__name__}: {exc}"))


class AnomalyReviewPage(QWidget):
    """Human-review UI over development-only synthetic histories."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.result: DemoRunResult | None = None
        self._visible_queue = ()
        self._process = None
        self._process_queue = None
        self._process_terminal_message = False
        self._process_timer = QTimer(self)
        self._process_timer.setInterval(75)
        self._process_timer.timeout.connect(self._poll_process)
        self.setObjectName("AnomalyReviewPage")
        self.setStyleSheet(
            f"QWidget#AnomalyReviewPage {{ background: {tokens().canvas}; }}"
        )
        self._build()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._wait_for_worker)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 32, 36, 36)
        layout.setSpacing(18)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel(t("anomaly_demo_title"))
        title.setStyleSheet(
            f"font-size: 30px; font-weight: 800; color: {tokens().text};"
        )
        subtitle = QLabel(t("anomaly_demo_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setMinimumWidth(0)
        subtitle.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        subtitle.setStyleSheet(
            f"font-size: 15px; color: {tokens().text_muted};"
        )
        heading.addWidget(title)
        heading.addWidget(subtitle)
        badge = QLabel(t("anomaly_demo_badge"))
        badge.setStyleSheet(semantic_badge_ss("info"))
        header.addLayout(heading, 1)
        header.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(header)

        layout.addWidget(self._build_run_card())
        layout.addLayout(self._build_stat_row())

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(pill_tab_ss())
        self.tabs.addTab(self._build_queue_tab(), t("anomaly_demo_tab_queue"))
        self.tabs.addTab(self._build_evidence_tab(), t("anomaly_demo_tab_evidence"))
        self.tabs.addTab(self._build_comparison_tab(), t("anomaly_demo_tab_comparison"))
        self.tabs.addTab(self._build_evaluation_tab(), t("anomaly_demo_tab_evaluation"))
        layout.addWidget(self.tabs)

        governance = QLabel(t("anomaly_demo_governance"))
        governance.setWordWrap(True)
        governance.setStyleSheet(alert_ss("info"))
        governance.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(governance)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_run_card(self):
        card = self._card()
        box = QGridLayout(card)
        box.setContentsMargins(20, 18, 20, 18)
        box.setHorizontalSpacing(14)
        box.setVerticalSpacing(10)
        label = QLabel(t("anomaly_demo_scenario"))
        label.setStyleSheet(self._label_style(bold=True))
        self.scenario_select = AppSelect(height=44)
        self.scenario_select.setMinimumWidth(220)
        self.scenario_select.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.scenario_select.label.setMinimumWidth(0)
        self.scenario_select.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        for option in demo_scenario_options(employee_count=_DEMO_EMPLOYEE_COUNT):
            description = t("anomaly_demo_scenario_name").format(number=option.index + 1)
            self.scenario_select.addItem(description, option.index)
        self.run_button = QPushButton(t("anomaly_demo_run"))
        self.run_button.setIcon(app_icon("fa5s.play", color="#ffffff", size=15))
        self.run_button.setStyleSheet(btn_primary(44))
        self.run_button.setCursor(Qt.PointingHandCursor)
        self.run_button.clicked.connect(self._start_run)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        self.status = QLabel(t("anomaly_demo_ready"))
        self.status.setWordWrap(True)
        self.status.setStyleSheet(self._label_style())
        box.addWidget(label, 0, 0)
        box.addWidget(self.scenario_select, 0, 1)
        box.addWidget(self.run_button, 0, 2)
        box.addWidget(self.progress, 1, 0, 1, 3)
        box.addWidget(self.status, 2, 0, 1, 3)
        box.setColumnStretch(1, 1)
        return card

    def _build_stat_row(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        self.stat_values = {}
        for key, label, icon in (
            ("train", t("anomaly_demo_train"), "fa5s.brain"),
            ("validation", t("anomaly_demo_validation"), "fa5s.check-circle"),
            ("test", t("anomaly_demo_test"), "fa5s.flask"),
            ("queue", t("anomaly_demo_queue_count"), "fa5s.list"),
        ):
            card = self._card()
            card.setMinimumHeight(86)
            box = QHBoxLayout(card)
            box.setContentsMargins(18, 12, 18, 12)
            icon_label = QLabel()
            icon_label.setFixedSize(38, 38)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setPixmap(app_pixmap(icon, color=tokens().brand, size=18))
            text = QVBoxLayout()
            value = QLabel("-")
            value.setStyleSheet(
                f"font-size: 21px; font-weight: 800; color: {tokens().text};"
            )
            caption = QLabel(label)
            caption.setWordWrap(True)
            caption.setStyleSheet(self._label_style())
            text.addWidget(value)
            text.addWidget(caption)
            box.addWidget(icon_label)
            box.addLayout(text, 1)
            row.addWidget(card, 1)
            self.stat_values[key] = value
        return row

    def _build_queue_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        filter_label = QLabel(t("anomaly_demo_filter"))
        filter_label.setStyleSheet(self._label_style(bold=True))
        self.queue_filter = AppSelect(height=40)
        self.queue_filter.addItem(t("anomaly_demo_all_items"), None)
        self.queue_filter.addItem(t("anomaly_demo_rules_only"), "deterministic")
        self.queue_filter.addItem(t("anomaly_demo_ml_only"), "statistical")
        self.queue_filter.currentIndexChanged.connect(self._apply_queue_filter)
        self.queue_count = QLabel(t("anomaly_demo_select_item"))
        self.queue_count.setStyleSheet(self._label_style())
        controls.addWidget(filter_label)
        controls.addWidget(self.queue_filter)
        controls.addSpacing(10)
        controls.addWidget(self.queue_count, 1)
        layout.addLayout(controls)
        self.queue_table = self._table(5)
        self.queue_table.setHorizontalHeaderLabels([
            t("anomaly_demo_employee"), t("anomaly_demo_signal"),
            t("anomaly_demo_track"), t("anomaly_demo_reason"),
            t("anomaly_demo_score"),
        ])
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for column, width in ((0, 115), (1, 150), (2, 115), (4, 100)):
            self.queue_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            self.queue_table.setColumnWidth(column, width)
        self.queue_table.cellDoubleClicked.connect(lambda row, _column: self._inspect_queue_row(row))
        layout.addWidget(self.queue_table)
        self.inspect_button = QPushButton(t("anomaly_demo_tab_evidence"))
        self.inspect_button.setIcon(app_icon("fa5s.search", color=tokens().text, size=14))
        self.inspect_button.setStyleSheet(btn_outline(40))
        self.inspect_button.clicked.connect(self._inspect_selected_row)
        self.inspect_button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.inspect_button)
        layout.addLayout(buttons)
        return page

    def _build_evidence_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.evidence_prompt = QLabel(t("anomaly_demo_select_item"))
        self.evidence_prompt.setWordWrap(True)
        self.evidence_prompt.setStyleSheet(alert_ss("info"))
        self.evidence_prompt.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.evidence_prompt)
        self.profile_card = self._card()
        self.profile_layout = QGridLayout(self.profile_card)
        self.profile_layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(self.profile_card)
        section = QLabel(t("anomaly_demo_policy_calculation"))
        section.setStyleSheet(self._section_style())
        layout.addWidget(section)
        self.calculation_table = self._table(7)
        self.calculation_table.setHorizontalHeaderLabels([
            t("anomaly_demo_policy_short"), t("anomaly_demo_observed_short"),
            t("anomaly_demo_required_short"), t("anomaly_demo_credit_short"),
            t("anomaly_demo_delay_short"), t("anomaly_demo_adjusted_short"),
            t("anomaly_demo_deficit"),
        ])
        self.calculation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calculation_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.calculation_table.setColumnWidth(0, 210)
        self.calculation_table.horizontalHeader().setFixedHeight(52)
        self.calculation_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.calculation_table.setMaximumHeight(150)
        layout.addWidget(self.calculation_table)
        self.calculation_evidence = QLabel("")
        self.calculation_evidence.setWordWrap(True)
        self.calculation_evidence.setStyleSheet(self._label_style())
        self.calculation_evidence.hide()
        layout.addWidget(self.calculation_evidence)
        section = QLabel(t("anomaly_demo_events"))
        section.setStyleSheet(self._section_style())
        layout.addWidget(section)
        self.events_table = self._table(5)
        self.events_table.setHorizontalHeaderLabels([
            t("anomaly_demo_effective_date"), t("anomaly_demo_recorded_date"),
            t("anomaly_demo_event"), t("anomaly_demo_detail"),
            t("anomaly_demo_policy"),
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for column in (0, 1, 2, 4):
            self.events_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        layout.addWidget(self.events_table)
        self.limitations = QLabel("")
        self.limitations.setWordWrap(True)
        self.limitations.setStyleSheet(alert_ss("warning"))
        self.limitations.setContentsMargins(16, 12, 16, 12)
        self.limitations.hide()
        layout.addWidget(self.limitations)
        return page

    def _build_comparison_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(t("anomaly_demo_comparison_title"))
        title.setStyleSheet(self._section_style())
        self.comparison_help = QLabel(t("anomaly_demo_comparison_help"))
        self.comparison_help.setWordWrap(True)
        self.comparison_help.setStyleSheet(self._label_style())
        layout.addWidget(title)
        layout.addWidget(self.comparison_help)
        self.comparison_table = self._table(8)
        self.comparison_table.setHorizontalHeaderLabels([
            t("anomaly_demo_method"), t("anomaly_demo_population_short"),
            t("anomaly_demo_reviews_short"), t("anomaly_demo_found_short"),
            t("anomaly_demo_false_alerts_short"), t("anomaly_demo_recall"),
            t("anomaly_demo_precision"), t("anomaly_demo_rare_alerts_short"),
        ])
        self.comparison_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column, width in ((1, 105), (2, 90), (3, 60), (4, 60), (5, 110), (6, 125), (7, 145)):
            self.comparison_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            self.comparison_table.setColumnWidth(column, width)
        layout.addWidget(self.comparison_table)
        warning = QLabel(t("anomaly_demo_control_warning"))
        warning.setWordWrap(True)
        warning.setStyleSheet(alert_ss("warning"))
        warning.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(warning)
        return page

    def _build_evaluation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(t("anomaly_demo_truth_title"))
        title.setStyleSheet(self._section_style())
        help_text = QLabel(t("anomaly_demo_truth_help"))
        help_text.setWordWrap(True)
        help_text.setStyleSheet(self._label_style())
        layout.addWidget(title)
        layout.addWidget(help_text)
        grid = QGridLayout()
        self.evaluation_values = {}
        labels = (
            ("positive", t("anomaly_demo_positive")),
            ("tp", t("anomaly_demo_true_positive")),
            ("fp", t("anomaly_demo_false_positive")),
            ("fn", t("anomaly_demo_false_negative")),
            ("recall", t("anomaly_demo_recall")),
            ("precision", t("anomaly_demo_precision")),
        )
        for index, (key, label) in enumerate(labels):
            card = self._card()
            box = QVBoxLayout(card)
            box.setContentsMargins(18, 16, 18, 16)
            value = QLabel("-")
            value.setStyleSheet(
                f"font-size: 26px; font-weight: 800; color: {tokens().text};"
            )
            caption = QLabel(label)
            caption.setStyleSheet(self._label_style())
            box.addWidget(value)
            box.addWidget(caption)
            grid.addWidget(card, index // 3, index % 3)
            self.evaluation_values[key] = value
        layout.addLayout(grid)
        layout.addStretch()
        return page

    @Slot()
    def _start_run(self):
        if self._process is not None:
            return
        self._clear_results()
        self._set_running(True)
        self.progress.setValue(2)
        self.status.setText(t("anomaly_demo_running"))
        option_index = int(self.scenario_select.currentData() or 0)
        context = multiprocessing.get_context("spawn")
        self._process_queue = context.Queue()
        self._process_terminal_message = False
        self._process = context.Process(
            target=_demo_process_entry,
            args=(option_index, self._process_queue),
            daemon=True,
        )
        self._process.start()
        self._process_timer.start()

    @Slot()
    def _poll_process(self):
        if self._process is None or self._process_queue is None:
            return
        try:
            while True:
                message = self._process_queue.get_nowait()
                kind = message[0]
                if kind == "progress":
                    self._on_progress(int(message[1]), str(message[2]))
                elif kind == "completed":
                    self._process_terminal_message = True
                    self._on_completed(message[1])
                elif kind == "failed":
                    self._process_terminal_message = True
                    self._on_failed(str(message[1]))
        except Empty:
            pass
        if self._process is not None and not self._process.is_alive():
            if not self._process_terminal_message:
                # The result queue can lag process exit by one timer cycle.
                try:
                    message = self._process_queue.get(timeout=0.2)
                    if message[0] == "completed":
                        self._process_terminal_message = True
                        self._on_completed(message[1])
                    elif message[0] == "failed":
                        self._process_terminal_message = True
                        self._on_failed(str(message[1]))
                except Empty:
                    self._on_failed(
                        f"Worker process exited with code {self._process.exitcode}"
                    )
            self._clear_worker()

    @Slot(int, str)
    def _on_progress(self, value: int, message: str):
        self.progress.setValue(value)
        self.status.setText(t(f"anomaly_demo_progress_{message}"))

    @Slot(object)
    def _on_completed(self, result: DemoRunResult):
        self.result = result
        self.progress.setValue(100)
        self.status.setText(t("anomaly_demo_complete"))
        self.stat_values["train"].setText(str(result.model_fit_count))
        self.stat_values["validation"].setText(str(result.validation_count))
        self.stat_values["test"].setText(str(result.eligible_test_count))
        self.stat_values["queue"].setText(str(len(result.queue)))
        self._apply_queue_filter()
        self._populate_comparison()
        self.comparison_help.setText(
            f"{t('anomaly_demo_comparison_help')} "
            + t("anomaly_demo_model_config").format(
                trees=result.model_estimators,
                budget=int(result.review_budget_fraction * 100),
            )
        )
        self._populate_evaluation()
        preferred = next(
            (item for item in result.queue if result.evidence_by_employee_id[item.employee_id].calculations),
            result.queue[0] if result.queue else None,
        )
        if preferred is not None:
            self._show_employee(preferred.employee_id)

    @Slot(str)
    def _on_failed(self, error: str):
        self._clear_results()
        self.progress.setValue(0)
        self.status.setText(f"{t('anomaly_demo_failed')}: {error}")
        self.status.setStyleSheet(alert_ss("danger"))
        self.status.setContentsMargins(12, 8, 12, 8)

    @Slot()
    def _clear_worker(self):
        process = self._process
        queue = self._process_queue
        self._process_timer.stop()
        self._process = None
        self._process_queue = None
        self._set_running(False)
        if process is not None:
            process.join(timeout=1)
            process.close()
        if queue is not None:
            queue.cancel_join_thread()
            queue.close()

    def _set_running(self, running: bool):
        self.run_button.setEnabled(not running)
        self.scenario_select.setEnabled(not running)
        if not running and not self.status.text().startswith(t("anomaly_demo_failed")):
            self.status.setStyleSheet(self._label_style())

    def _apply_queue_filter(self, *_args):
        if self.result is None:
            self._visible_queue = ()
        else:
            selected = self.queue_filter.currentData()
            self._visible_queue = tuple(
                item for item in self.result.queue
                if selected is None or item.source == selected
            )
        self.queue_table.setRowCount(len(self._visible_queue))
        for row, item in enumerate(self._visible_queue):
            values = (
                item.employee_id,
                t("anomaly_demo_rule") if item.source == "deterministic" else t("anomaly_demo_statistical"),
                self._track_label(item.employment_track),
                self._reason_label(item),
                "-" if item.anomaly_score is None else f"{item.anomaly_score:.3f}",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                if column == 3:
                    cell.setToolTip(value)
                self.queue_table.setItem(row, column, cell)
            self.queue_table.setRowHeight(row, 48)
        sync_table_widget_cells(self.queue_table)
        self.queue_count.setText(
            f"{len(self._visible_queue)} / {len(self.result.queue) if self.result else 0}"
        )
        self.inspect_button.setEnabled(bool(self._visible_queue))

    def _inspect_selected_row(self):
        row = self.queue_table.currentRow()
        self._inspect_queue_row(0 if row < 0 else row)

    def _inspect_queue_row(self, row: int):
        if 0 <= row < len(self._visible_queue):
            self._show_employee(self._visible_queue[row].employee_id)
            self.tabs.setCurrentIndex(1)

    def _show_employee(self, employee_id: str):
        if self.result is None:
            return
        evidence = self.result.evidence_by_employee_id[employee_id]
        self._clear_layout(self.profile_layout)
        profile = (
            (t("anomaly_demo_employee"), f"{evidence.full_name} ({evidence.employee_id})"),
            (t("anomaly_demo_track"), self._track_label(evidence.employment_track)),
            (t("anomaly_demo_hired"), evidence.hire_date.isoformat()),
            (t("anomaly_demo_current_level"), evidence.current_level),
        )
        for index, (label, value) in enumerate(profile):
            label_widget = QLabel(label)
            label_widget.setStyleSheet(self._label_style())
            value_widget = QLabel(value)
            value_widget.setStyleSheet(self._label_style(bold=True))
            self.profile_layout.addWidget(label_widget, index // 2 * 2, index % 2)
            self.profile_layout.addWidget(value_widget, index // 2 * 2 + 1, index % 2)
        self.evidence_prompt.setText(f"{t('anomaly_demo_profile')}: {evidence.employee_id}")
        self._populate_calculations(evidence)
        self._populate_events(evidence)
        if evidence.limitations:
            self.limitations.setText(
                f"{t('anomaly_demo_limitations')}: "
                + " ".join(t(f"anomaly_demo_limitation_{code}") for code in evidence.limitations)
            )
            self.limitations.show()
        else:
            self.limitations.hide()

    def _populate_calculations(self, evidence: DemoEmployeeEvidence):
        self.calculation_table.setRowCount(max(1, len(evidence.calculations)))
        if not evidence.calculations:
            cell = QTableWidgetItem(t("anomaly_demo_no_calculation"))
            self.calculation_table.setItem(0, 0, cell)
            self.calculation_table.setSpan(0, 0, 1, 7)
            self.calculation_evidence.hide()
            return
        trace_lines = []
        for row, calculation in enumerate(evidence.calculations):
            values = (
                f"{calculation.policy_id} / {calculation.policy_version}",
                self._months(calculation.observed_service_months),
                self._months(calculation.required_service_months),
                self._months(calculation.commendation_credit_months),
                self._months(calculation.sanction_delay_months),
                self._months(calculation.adjusted_service_months),
                self._months(calculation.service_deficit_months),
            )
            for column, value in enumerate(values):
                self.calculation_table.setItem(row, column, QTableWidgetItem(value))
            self.calculation_table.setRowHeight(row, 48)
            references = ", ".join(calculation.evidence_references) or t("anomaly_demo_none")
            trace_lines.append(
                t("anomaly_demo_calculation_trace").format(
                    number=row + 1,
                    event_id=calculation.event_source_id,
                    evidence=references,
                )
            )
        sync_table_widget_cells(self.calculation_table)
        self.calculation_evidence.setText("\n".join(trace_lines))
        self.calculation_evidence.show()

    def _populate_events(self, evidence: DemoEmployeeEvidence):
        self.events_table.setRowCount(len(evidence.events))
        for row, event in enumerate(evidence.events):
            detail = self._event_detail(event)
            values = (
                event.effective_date.isoformat(),
                event.recorded_date.isoformat(),
                t(f"anomaly_demo_event_{event.event_type}"),
                detail,
                " / ".join(part for part in (event.policy_id, event.policy_version) if part) or "-",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 3:
                    cell.setToolTip(value)
                self.events_table.setItem(row, column, cell)
            self.events_table.setRowHeight(row, 46)
        sync_table_widget_cells(self.events_table)

    def _populate_comparison(self):
        if self.result is None:
            return
        self.comparison_table.setRowCount(len(self.result.comparisons))
        for row, item in enumerate(self.result.comparisons):
            values = (
                t(f"anomaly_demo_method_{item.representation}"),
                str(item.evaluation_count), str(item.review_count),
                str(item.true_positives), str(item.false_positives),
                self._ratio(item.recall), self._ratio(item.precision),
                f"{item.rare_legitimate_flagged}/{item.rare_legitimate_count}",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0 and item.representation == "policy_matched":
                    cell.setForeground(QColor(tokens().brand))
                self.comparison_table.setItem(row, column, cell)
            self.comparison_table.setRowHeight(row, 48)
        sync_table_widget_cells(self.comparison_table)

    def _populate_evaluation(self):
        if self.result is None:
            return
        summary = self.result.evaluation
        values = {
            "positive": str(summary.positive_count),
            "tp": str(summary.true_positives),
            "fp": str(summary.false_positives),
            "fn": str(summary.false_negatives),
            "recall": self._ratio(summary.recall),
            "precision": self._ratio(summary.precision),
        }
        for key, value in values.items():
            self.evaluation_values[key].setText(value)

    def _wait_for_worker(self):
        if self._process is not None:
            self._process_timer.stop()
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=10)
            self._clear_worker()

    def prepare_for_disposal(self) -> bool:
        """Cancel a run and keep Qt objects alive until its process exits."""
        self._wait_for_worker()
        return self._process is None

    def refresh(self):
        """The demonstration runs only after an explicit reviewer action."""

    @staticmethod
    def _event_detail(event):
        if event.level_before or event.level_after:
            return f"{event.level_before or '-'} -> {event.level_after or '-'}"
        if event.category is not None:
            return t("anomaly_demo_category").format(value=event.category)
        if event.recognized_service_months:
            return t("anomaly_demo_recognized_service").format(
                count=event.recognized_service_months
            )
        if event.correction_of_event_id:
            return t("anomaly_demo_correction_of").format(
                event_id=event.correction_of_event_id
            )
        return "-"

    @staticmethod
    def _months(value: int):
        return t("anomaly_demo_months").format(count=value)

    @staticmethod
    def _ratio(value: float | None):
        return t("anomaly_demo_undefined") if value is None else f"{value:.1%}"

    def _clear_results(self):
        self.result = None
        self._visible_queue = ()
        for value in self.stat_values.values():
            value.setText("-")
        for table in (
            self.queue_table,
            self.calculation_table,
            self.events_table,
            self.comparison_table,
        ):
            table.clearContents()
            table.setRowCount(0)
        for value in self.evaluation_values.values():
            value.setText("-")
        self.queue_count.setText(t("anomaly_demo_select_item"))
        self.evidence_prompt.setText(t("anomaly_demo_select_item"))
        self.calculation_evidence.clear()
        self.calculation_evidence.hide()
        self.limitations.clear()
        self.limitations.hide()
        self.inspect_button.setEnabled(False)

    @staticmethod
    def _track_label(track: str):
        key = "anomaly_demo_track_promotion" if track == "promotion" else "anomaly_demo_track_other"
        return t(key)

    @staticmethod
    def _reason_label(item):
        key = f"anomaly_demo_reason_{item.reason_code}"
        translated = t(key)
        return item.reason if translated == key else translated

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("AnomalyCard")
        card.setStyleSheet(card_ss("QFrame#AnomalyCard"))
        return card

    @staticmethod
    def _table(columns: int):
        table = QTableWidget()
        table.setColumnCount(columns)
        table.setStyleSheet(table_style())
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setMinimumHeight(260)
        enable_table_row_selection(table)
        return table

    @staticmethod
    def _label_style(*, bold=False):
        weight = 700 if bold else 400
        return f"font-size: 14px; font-weight: {weight}; color: {tokens().text_muted};"

    @staticmethod
    def _section_style():
        return f"font-size: 17px; font-weight: 800; color: {tokens().text};"
