"""Interactive, synthetic-only demonstration of the research pipeline."""

from __future__ import annotations

import csv
from html import escape
import multiprocessing
import os
from queue import Empty

from PySide6.QtCore import QMarginsF, QRectF, QTimer, Qt, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QIcon,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
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
    menu_ss,
    primary_button_fg,
    semantic_badge_ss,
    sync_table_widget_cells,
    table_style,
)
from src.ui.theme import tokens


_DEMO_EMPLOYEE_COUNT = 120
_WORKER_THREAD_ENV = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def _stateful_icon(name: str, color: str, size: int) -> QIcon:
    """Icon whose disabled state matches the disabled button text colour."""
    icon = QIcon()
    icon.addPixmap(app_pixmap(name, color=color, size=size), QIcon.Normal)
    icon.addPixmap(app_pixmap(name, color=tokens().text_soft, size=size), QIcon.Disabled)
    return icon


class ReviewPriorityIndicator(QWidget):
    """Compact relative queue priority, deliberately not a probability gauge."""

    def __init__(self, priority: str, label: str, parent=None):
        super().__init__(parent)
        self.priority = priority
        self.label = label
        self.setFixedWidth(130)
        self.setMinimumHeight(34)
        self.setToolTip(t("anomaly_demo_priority_tooltip"))

    def paintEvent(self, _event):
        palette = {
            "rule": tokens().brand,
            "high": "#c98200",
            "medium": "#d8a323",
            "low": tokens().text_soft,
        }
        extent = {"rule": 300, "high": 270, "medium": 190, "low": 110}
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        ring = QRectF(3, (self.height() - 20) / 2, 20, 20)
        painter.setPen(QPen(QColor(tokens().border), 4))
        painter.drawArc(ring, 0, 360 * 16)
        painter.setPen(QPen(QColor(palette.get(self.priority, tokens().text_soft)), 4))
        painter.drawArc(ring, 90 * 16, -extent.get(self.priority, 110) * 16)
        painter.setPen(QColor(tokens().text))
        painter.drawText(QRectF(31, 0, 96, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.label)


class ComparisonOutcomeChart(QWidget):
    """Recall/precision overview supporting the exact comparison table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._comparisons = ()
        self.setMinimumHeight(235)

    def set_comparisons(self, comparisons):
        self._comparisons = tuple(comparisons)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(tokens().surface))
        if not self._comparisons:
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(self.rect(), Qt.AlignCenter, t("anomaly_demo_chart_waiting"))
            return

        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        left, top, right, bottom = 48, 50, 18, 52
        chart_width = max(1, self.width() - left - right)
        chart_height = max(1, self.height() - top - bottom)
        for tick in (0, 25, 50, 75, 100):
            y = top + chart_height * (1 - tick / 100)
            painter.setPen(QPen(QColor(tokens().border), 1))
            painter.drawLine(left, y, left + chart_width, y)
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(QRectF(0, y - 9, left - 8, 18), Qt.AlignRight | Qt.AlignVCenter, f"{tick}%")

        group_width = chart_width / len(self._comparisons)
        bar_width = min(34.0, group_width * 0.25)
        # Dark/light green pair in both themes: recall is always the darker
        # bar in light mode and the lighter bar in dark mode, with a clear
        # luminance gap so the two series are distinguishable.
        recall_color = tokens().brand
        precision_color = (
            tokens().brand_accent
            if tokens().name != "dark"
            else "#2f7a46"
        )
        for index, item in enumerate(self._comparisons):
            center = left + index * group_width + group_width / 2
            base_y = top + chart_height
            metrics = (
                (item.recall, recall_color),
                (item.precision, precision_color),
            )
            for offset, (value, color) in zip((-bar_width, 0), metrics):
                painter.setPen(QColor(tokens().text))
                if value is None:
                    painter.drawText(
                        QRectF(center + offset - 10, base_y - 20, bar_width + 20, 18),
                        Qt.AlignCenter,
                        t("anomaly_demo_undefined"),
                    )
                    continue
                height = chart_height * value
                bar = QRectF(center + offset, base_y - height, bar_width, height)
                painter.fillRect(bar, QColor(color))
                # A dark edge keeps the light-green precision bar visible
                # against the white card (non-text contrast).
                painter.setPen(QPen(QColor(tokens().brand if tokens().name != "dark" else tokens().border_strong), 1))
                painter.drawRect(bar)
                painter.setPen(QColor(tokens().text))
                value_font = painter.font()
                value_font.setPointSize(8)
                painter.setFont(value_font)
                label = f"{value:.0%}"
                if painter.fontMetrics().horizontalAdvance(label) + 2 <= bar_width:
                    painter.drawText(
                        QRectF(center + offset, base_y - height - 18, bar_width, 16),
                        Qt.AlignCenter,
                        label,
                    )
                else:
                    # Narrow bars: print the value inside the bar, rotated,
                    # so adjacent recall/precision labels never overlap.
                    painter.save()
                    inside = height >= painter.fontMetrics().horizontalAdvance(label) + 6
                    painter.setPen(QColor(
                        ("#ffffff" if QColor(color).lightness() < 128 else "#062f28")
                        if inside else tokens().text
                    ))
                    anchor_y = base_y - 4 if inside else base_y - height - 4
                    painter.translate(center + offset + bar_width / 2, anchor_y)
                    painter.rotate(-90)
                    painter.drawText(QRectF(0, -8, 60, 16), Qt.AlignVCenter | Qt.AlignLeft, label)
                    painter.restore()
                painter.setFont(font)
            label = t(f"anomaly_demo_method_short_{item.representation}")
            painter.drawText(
                QRectF(left + index * group_width, base_y + 8, group_width, 34),
                Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                label,
            )

        painter.fillRect(QRectF(left, 14, 10, 10), QColor(recall_color))
        painter.setPen(QColor(tokens().text))
        painter.drawText(
            QRectF(left + 16, 7, 160, 24),
            Qt.AlignVCenter | Qt.AlignLeft,
            t("anomaly_demo_recall"),
        )
        painter.fillRect(QRectF(left + 190, 14, 10, 10), QColor(precision_color))
        painter.drawText(
            QRectF(left + 206, 7, 180, 24),
            Qt.AlignVCenter | Qt.AlignLeft,
            t("anomaly_demo_precision"),
        )


class OutcomeCountChart(QWidget):
    """Stacked true/false-positive counts per method at equal review capacity.

    Counts come from the same completed comparison objects as the exact table.
    False positives use a colour-blind-safe vermilion plus diagonal hatching so
    the two segments stay distinguishable without relying on colour alone.
    """

    TP_COLOR_LIGHT = "#1f7a4d"
    TP_COLOR_DARK = "#7fd49a"
    FP_COLOR = "#d55e00"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._comparisons = ()
        self.setMinimumHeight(235)

    def set_comparisons(self, comparisons):
        self._comparisons = tuple(comparisons)
        self.update()

    def _tp_color(self):
        return self.TP_COLOR_DARK if tokens().name == "dark" else self.TP_COLOR_LIGHT

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(tokens().surface))
        if not self._comparisons:
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(self.rect(), Qt.AlignCenter, t("anomaly_demo_chart_waiting"))
            return
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        left, top, right, bottom = 40, 62, 14, 52
        chart_width = max(1, self.width() - left - right)
        chart_height = max(1, self.height() - top - bottom)
        maximum = max(
            1,
            max(item.true_positives + item.false_positives for item in self._comparisons),
        )
        for tick in range(maximum + 1):
            y = top + chart_height * (1 - tick / maximum)
            painter.setPen(QPen(QColor(tokens().border), 1))
            painter.drawLine(left, y, left + chart_width, y)
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(QRectF(0, y - 9, left - 8, 18), Qt.AlignRight | Qt.AlignVCenter, str(tick))

        tp_color = QColor(self._tp_color())
        fp_color = QColor(self.FP_COLOR)
        group_width = chart_width / len(self._comparisons)
        bar_width = min(46.0, group_width * 0.42)
        base_y = top + chart_height
        for index, item in enumerate(self._comparisons):
            x = left + index * group_width + (group_width - bar_width) / 2
            tp_height = chart_height * item.true_positives / maximum
            fp_height = chart_height * item.false_positives / maximum
            tp_rect = QRectF(x, base_y - tp_height, bar_width, tp_height)
            fp_rect = QRectF(x, base_y - tp_height - fp_height, bar_width, fp_height)
            painter.fillRect(tp_rect, tp_color)
            if fp_height:
                painter.fillRect(fp_rect, fp_color)
                painter.fillRect(fp_rect, QBrush(QColor("#ffffff"), Qt.BDiagPattern))
            painter.setPen(QPen(QColor(tokens().text), 1))
            painter.drawRect(QRectF(x, base_y - tp_height - fp_height, bar_width, tp_height + fp_height))
            for rect, value, color in ((tp_rect, item.true_positives, "#ffffff"), (fp_rect, item.false_positives, "#111311")):
                if value and rect.height() >= 16:
                    painter.setPen(QColor(color if tokens().name != "dark" or rect is fp_rect else "#062f28"))
                    painter.drawText(rect, Qt.AlignCenter, str(value))
            painter.setPen(QColor(tokens().text))
            painter.drawText(
                QRectF(left + index * group_width, base_y + 8, group_width, 34),
                Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                t(f"anomaly_demo_method_short_{item.representation}"),
            )

        # Legend: one row when it fits, otherwise two rows (never clipped).
        metrics = painter.fontMetrics()
        tp_text = t("anomaly_demo_tp_legend")
        fp_text = t("anomaly_demo_fp_legend")
        tp_width = 18 + metrics.horizontalAdvance(tp_text)
        fp_width = 18 + metrics.horizontalAdvance(fp_text)
        one_row = left + tp_width + 24 + fp_width <= self.width() - right
        painter.setPen(QColor(tokens().text))
        painter.fillRect(QRectF(left, 12, 12, 12), tp_color)
        painter.drawText(QRectF(left + 18, 6, tp_width, 24), Qt.AlignVCenter | Qt.AlignLeft, tp_text)
        fp_x, fp_y = (left + tp_width + 24, 12) if one_row else (left, 32)
        legend = QRectF(fp_x, fp_y, 12, 12)
        painter.fillRect(legend, fp_color)
        painter.fillRect(legend, QBrush(QColor("#ffffff"), Qt.BDiagPattern))
        painter.drawRect(legend)
        painter.drawText(QRectF(fp_x + 18, fp_y - 6, fp_width, 24), Qt.AlignVCenter | Qt.AlignLeft, fp_text)


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
        self._compact_layout = None
        self._process_timer = QTimer(self)
        self._process_timer.setInterval(75)
        self._process_timer.timeout.connect(self._poll_process)
        self.setObjectName("AnomalyReviewPage")
        self.setStyleSheet(
            f"QWidget#AnomalyReviewPage {{ background: {tokens().canvas}; }}"
        )
        self._build()
        self._clear_results()
        QTimer.singleShot(0, self._apply_responsive_layout)
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
        self.demo_badge = QLabel(t("anomaly_demo_badge"))
        self.demo_badge.setStyleSheet(semantic_badge_ss("info"))
        self.help_button = QPushButton(t("anomaly_demo_help"))
        self.help_button.setIcon(app_icon("fa5s.question-circle", color=tokens().text, size=14))
        self.help_button.setCheckable(True)
        self.help_button.setStyleSheet(btn_outline(38))
        self.help_button.setToolTip(t("anomaly_demo_help_tooltip"))
        self.help_button.clicked.connect(self._toggle_help)
        self.export_button = QPushButton(t("anomaly_demo_export_report"))
        self.export_button.setIcon(_stateful_icon("fa5s.download", primary_button_fg(), 14))
        self.export_button.setStyleSheet(btn_primary(38))
        self.export_button.setToolTip(t("anomaly_demo_export_tooltip"))
        self.export_button.setEnabled(False)
        self.export_menu = QMenu(self.export_button)
        self.export_menu.setStyleSheet(menu_ss())
        self.export_csv_action = QAction(
            app_icon("fa5s.file-csv", color=tokens().text_muted, size=14),
            t("anomaly_demo_export_csv"),
            self,
        )
        self.export_pdf_action = QAction(
            app_icon("fa5s.file-pdf", color=tokens().text_muted, size=14),
            t("anomaly_demo_export_pdf"),
            self,
        )
        self.export_csv_action.triggered.connect(self._export_csv)
        self.export_pdf_action.triggered.connect(self._export_pdf)
        self.export_menu.addAction(self.export_csv_action)
        self.export_menu.addAction(self.export_pdf_action)
        self.export_button.setMenu(self.export_menu)
        header.addLayout(heading, 1)
        header.addWidget(self.help_button, 0, Qt.AlignTop)
        header.addWidget(self.export_button, 0, Qt.AlignTop)
        header.addWidget(self.demo_badge, 0, Qt.AlignTop)
        layout.addLayout(header)

        workspace = QGridLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setHorizontalSpacing(16)
        workspace.setVerticalSpacing(16)
        main = QWidget()
        main.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(18)
        main_layout.addWidget(self._build_run_card())
        main_layout.addLayout(self._build_stat_row())
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._anomaly_tab_style())
        self.tabs.addTab(self._build_queue_tab(), t("anomaly_demo_tab_queue"))
        self.tabs.addTab(self._build_evidence_tab(), t("anomaly_demo_tab_evidence"))
        self.tabs.addTab(self._build_comparison_tab(), t("anomaly_demo_tab_comparison"))
        self.tabs.addTab(self._build_evaluation_tab(), t("anomaly_demo_tab_evaluation"))
        self.tabs.currentChanged.connect(self._update_guide)
        self.tabs.currentChanged.connect(self._fit_tabs_to_current)
        main_layout.addWidget(self.tabs)
        self._fit_tabs_to_current(0)

        governance = QLabel(t("anomaly_demo_governance"))
        governance.setWordWrap(True)
        governance.setStyleSheet(alert_ss("info", "QLabel"))
        governance.setContentsMargins(16, 12, 16, 12)
        governance.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        main_layout.addWidget(governance)
        main_layout.addStretch(1)
        self.main_workspace = main
        workspace.addWidget(main, 0, 0)
        self.guide_panel = self._build_guide_panel()
        self.guide_panel.hide()
        workspace.addWidget(self.guide_panel, 0, 1)
        workspace.setColumnStretch(0, 1)
        self.workspace_layout = workspace
        layout.addLayout(workspace)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_guide_panel(self):
        panel = self._card()
        panel.setMinimumWidth(250)
        panel.setMaximumWidth(300)
        box = QVBoxLayout(panel)
        box.setContentsMargins(18, 18, 18, 18)
        box.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel(t("anomaly_demo_help_title"))
        title.setStyleSheet(self._section_style())
        self.guide_close_button = QPushButton()
        self.guide_close_button.setIcon(
            app_icon("fa5s.chevron-up", color=tokens().text_muted, size=12)
        )
        self.guide_close_button.setToolTip(t("anomaly_demo_hide_help"))
        self.guide_close_button.setFixedSize(30, 30)
        self.guide_close_button.setStyleSheet(btn_outline(30))
        self.guide_close_button.clicked.connect(self._close_guide)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.guide_close_button)
        box.addLayout(header)

        terms = QLabel(t("anomaly_demo_guide_terms"))
        terms.setStyleSheet(self._label_style(bold=True))
        box.addWidget(terms)
        self.guide_terms_widget = QWidget()
        self.guide_terms_layout = QVBoxLayout(self.guide_terms_widget)
        self.guide_terms_layout.setContentsMargins(0, 0, 0, 0)
        self.guide_terms_layout.setSpacing(10)
        box.addWidget(self.guide_terms_widget)
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {tokens().border};")
        box.addWidget(divider)

        path_title = QLabel(t("anomaly_demo_demo_path"))
        path_title.setStyleSheet(self._label_style(bold=True))
        box.addWidget(path_title)
        self.guide_step_numbers = []
        self.guide_step_labels = []
        for step_index in range(4):
            row = QHBoxLayout()
            row.setSpacing(9)
            number = QLabel(str(step_index + 1))
            number.setAlignment(Qt.AlignCenter)
            number.setFixedSize(24, 24)
            label = QLabel(self._guide_step_text(step_index))
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            row.addWidget(number, 0, Qt.AlignTop)
            row.addWidget(label, 1)
            box.addLayout(row)
            self.guide_step_numbers.append(number)
            self.guide_step_labels.append(label)
        box.addStretch()
        return panel

    def _update_guide(self, index: int = 0):
        if not hasattr(self, "guide_terms_layout"):
            return
        self._clear_layout(self.guide_terms_layout)
        terms = t(f"anomaly_demo_guide_terms_{index}").split("\n\n")
        for block in terms:
            term, separator, definition = block.partition(": ")
            row = QLabel()
            row.setWordWrap(True)
            row.setTextFormat(Qt.RichText)
            if separator:
                row.setText(
                    f"<b>{escape(term)}:</b> {escape(definition)}"
                )
            else:
                row.setText(escape(block))
            row.setStyleSheet(
                f"font-size: 13px; color: {tokens().text_muted};"
            )
            self.guide_terms_layout.addWidget(row)

        for step_index, (number, label) in enumerate(
            zip(self.guide_step_numbers, self.guide_step_labels)
        ):
            active = step_index == index
            number.setStyleSheet(
                "border-radius: 12px; font-size: 12px; font-weight: 800; "
                f"background: {tokens().brand if active else tokens().surface_muted}; "
                f"color: {'#062f28' if active and tokens().name == 'dark' else '#ffffff' if active else tokens().text_muted};"
            )
            label.setStyleSheet(
                f"font-size: 12px; font-weight: {700 if active else 400}; "
                f"color: {tokens().text if active else tokens().text_muted};"
            )

    @staticmethod
    def _guide_step_text(index: int):
        text = t(f"anomaly_demo_guide_step_{index}")
        prefix = f"{index + 1}. "
        return text[len(prefix):] if text.startswith(prefix) else text

    def _fit_tabs_to_current(self, index: int):
        """Size the tab widget to the visible page, not the tallest page.

        Without this, short tabs inherit the height of the longest tab and
        leave a large empty gap above the governance note.
        """
        current = self.tabs.widget(index if index is not None else self.tabs.currentIndex())
        if current is None:
            return
        page_layout = current.layout()
        page_layout.activate()
        width = max(1, self.tabs.width())
        # Word-wrapped labels report their height for an arbitrary narrow
        # width in sizeHint(); measure at the real pane width instead.
        if page_layout.hasHeightForWidth():
            page_height = page_layout.totalHeightForWidth(width)
        else:
            page_height = page_layout.totalSizeHint().height()
        # 26 px matches the QTabWidget::pane margin-top in _anomaly_tab_style.
        self.tabs.setFixedHeight(
            page_height + self.tabs.tabBar().sizeHint().height() + 26 + 4
        )

    def _refit_tabs(self, *_args):
        """Re-measure after content or disclosure changes on the current tab."""
        QTimer.singleShot(0, lambda: self._fit_tabs_to_current(self.tabs.currentIndex()))

    def _close_guide(self):
        self.help_button.setChecked(False)
        self._toggle_help(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()
        if hasattr(self, "tabs"):
            self._refit_tabs()

    def _apply_responsive_layout(self):
        if not hasattr(self, "run_layout"):
            return
        # This widget receives the content width after the persistent sidebar.
        # A standard 1488 px laptop window leaves roughly 1150 px here, which
        # is wide enough for the approved desktop workspace and side guide.
        compact = self.width() < 1120
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        self.demo_badge.setVisible(not compact)
        self.workspace_layout.removeWidget(self.guide_panel)
        self.workspace_layout.removeWidget(self.main_workspace)
        if compact:
            self.guide_panel.setMinimumWidth(0)
            self.guide_panel.setMaximumWidth(16777215)
            self.workspace_layout.addWidget(self.guide_panel, 0, 0, 1, 2)
            self.workspace_layout.addWidget(self.main_workspace, 1, 0, 1, 2)
        else:
            self.guide_panel.setMinimumWidth(250)
            self.guide_panel.setMaximumWidth(300)
            self.workspace_layout.addWidget(self.main_workspace, 0, 0)
            self.workspace_layout.addWidget(self.guide_panel, 0, 1)

        for widget in (
            self.scenario_select,
            self.scenario_details_button,
            self.run_button,
            self.progress,
            self.status,
            self.scenario_details,
        ):
            self.run_layout.removeWidget(widget)
        if compact:
            self.run_layout.addWidget(self.scenario_select, 1, 0, 1, 2)
            self.run_layout.addWidget(self.scenario_details_button, 2, 0)
            self.run_layout.addWidget(self.run_button, 2, 1)
            self.run_layout.addWidget(self.progress, 3, 0, 1, 2)
            self.run_layout.addWidget(self.status, 4, 0, 1, 2)
            self.run_layout.addWidget(self.scenario_details, 5, 0, 1, 2)
        else:
            self.run_layout.addWidget(self.scenario_select, 1, 0)
            self.run_layout.addWidget(self.scenario_details_button, 1, 1)
            self.run_layout.addWidget(self.run_button, 1, 2)
            self.run_layout.addWidget(self.progress, 2, 0, 1, 3)
            self.run_layout.addWidget(self.status, 3, 0, 1, 3)
            self.run_layout.addWidget(self.scenario_details, 4, 0, 1, 3)

        for index, card in enumerate(self.stat_cards):
            self.stat_grid.removeWidget(card)
            row, column = (divmod(index, 2) if compact else (0, index))
            self.stat_grid.addWidget(card, row, column)
        for index, card in enumerate(self.evaluation_cards):
            self.evaluation_grid.removeWidget(card)
            row, column = (divmod(index, 2) if compact else (0, index))
            self.evaluation_grid.addWidget(card, row, column)

        tab_keys = (
            "anomaly_demo_tab_queue",
            "anomaly_demo_tab_evidence",
            "anomaly_demo_tab_comparison",
            "anomaly_demo_tab_evaluation",
        )
        if compact:
            tab_keys = tuple(f"{key}_short" for key in tab_keys)
        for index, key in enumerate(tab_keys):
            self.tabs.setTabText(index, t(key))
        self.queue_table.setColumnHidden(1, compact)
        self.queue_table.setColumnHidden(2, compact)

    def _toggle_help(self, checked: bool):
        self.guide_panel.setVisible(checked)
        self._update_guide(self.tabs.currentIndex())
        self.help_button.setText(
            t("anomaly_demo_hide_help") if checked else t("anomaly_demo_help")
        )

    def _build_run_card(self):
        card = self._card()
        box = QGridLayout(card)
        self.run_layout = box
        box.setContentsMargins(20, 18, 20, 18)
        box.setHorizontalSpacing(14)
        box.setVerticalSpacing(10)
        self.scenario_label = QLabel(t("anomaly_demo_scenario"))
        self.scenario_label.setStyleSheet(self._label_style(bold=True))
        box.addWidget(self.scenario_label, 0, 0, 1, 3)
        self.scenario_select = AppSelect(height=44)
        self.scenario_select.setMinimumWidth(220)
        self.scenario_select.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.scenario_select.label.setMinimumWidth(0)
        self.scenario_select.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.scenario_options = demo_scenario_options(
            employee_count=_DEMO_EMPLOYEE_COUNT
        )
        for option in self.scenario_options:
            description = t(f"anomaly_demo_population_{option.population}")
            self.scenario_select.addItem(description, option.index)
        self.scenario_details_button = QPushButton(t("anomaly_demo_scenario_details"))
        self.scenario_details_button.setCheckable(True)
        self.scenario_details_button.setIcon(
            app_icon("fa5s.info-circle", color=tokens().text, size=14)
        )
        self.scenario_details_button.setStyleSheet(btn_outline(44))
        self.scenario_details_button.clicked.connect(
            lambda checked: self.scenario_details.setVisible(checked)
        )
        self.run_button = QPushButton(t("anomaly_demo_run"))
        self.run_button.setIcon(_stateful_icon("fa5s.play", primary_button_fg(), 15))
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
        box.addWidget(self.scenario_select, 1, 0)
        box.addWidget(self.scenario_details_button, 1, 1)
        box.addWidget(self.run_button, 1, 2)
        box.addWidget(self.progress, 2, 0, 1, 3)
        box.addWidget(self.status, 3, 0, 1, 3)
        self.scenario_details = self._card()
        details_layout = QGridLayout(self.scenario_details)
        details_layout.setContentsMargins(14, 12, 14, 12)
        details_layout.setHorizontalSpacing(24)
        details_layout.setVerticalSpacing(5)
        self.scenario_detail_values = {}
        detail_keys = (
            ("population", "anomaly_demo_population_short"),
            ("mechanism", "anomaly_demo_generated_label"),
            ("rare", "anomaly_demo_lawful_rare"),
            ("split", "anomaly_demo_dataset_split"),
            ("seeds", "anomaly_demo_seeds"),
            ("model", "anomaly_demo_model_configuration"),
        )
        for index, (key, label_key) in enumerate(detail_keys):
            label = QLabel(t(label_key))
            label.setStyleSheet(self._label_style())
            value = QLabel("-")
            value.setWordWrap(True)
            value.setStyleSheet(self._label_style(bold=True))
            row, column = divmod(index, 3)
            details_layout.addWidget(label, row * 2, column)
            details_layout.addWidget(value, row * 2 + 1, column)
            self.scenario_detail_values[key] = value
        self.scenario_details.hide()
        box.addWidget(self.scenario_details, 4, 0, 1, 3)
        box.setColumnStretch(0, 1)
        self.scenario_select.currentIndexChanged.connect(
            self._update_scenario_details
        )
        self._update_scenario_details()
        return card

    def _update_scenario_details(self, *_args):
        index = self.scenario_select.currentIndex()
        if index < 0 or index >= len(self.scenario_options):
            return
        option = self.scenario_options[index]
        values = {
            "population": t(f"anomaly_demo_population_{option.population}"),
            "mechanism": t(f"anomaly_demo_mechanism_{option.mechanism}"),
            "rare": t(f"anomaly_demo_rare_{option.rare_pattern}"),
            "split": t("anomaly_demo_split_value").format(employees=option.employee_count),
            "seeds": f"{option.dataset_seed} / {option.split_seed} / {option.model_seed}",
            "model": t("anomaly_demo_model_value"),
        }
        for key, value in values.items():
            self.scenario_detail_values[key].setText(value)

    def _build_stat_row(self):
        row = QGridLayout()
        row.setSpacing(14)
        self.stat_grid = row
        self.stat_cards = []
        self.stat_values = {}
        for index, (key, label, icon) in enumerate((
            ("train", t("anomaly_demo_train"), "fa5s.brain"),
            ("validation", t("anomaly_demo_validation"), "fa5s.check-circle"),
            ("test", t("anomaly_demo_test"), "fa5s.flask"),
            ("queue", t("anomaly_demo_queue_count"), "fa5s.list"),
        )):
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
            row.addWidget(card, 0, index)
            self.stat_cards.append(card)
            self.stat_values[key] = value
        return row

    def _build_queue_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(12)
        layout.addWidget(
            self._tab_intro(
                "anomaly_demo_queue_title",
                "anomaly_demo_queue_description",
            )
        )
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        controls = QHBoxLayout(toolbar)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(10)
        filter_label = QLabel(t("anomaly_demo_filter"))
        filter_label.setStyleSheet(self._label_style(bold=True))
        self.queue_filter = AppSelect(height=40)
        self.queue_filter.addItem(t("anomaly_demo_all_items"), None)
        self.queue_filter.addItem(t("anomaly_demo_rules_only"), "deterministic")
        self.queue_filter.addItem(t("anomaly_demo_ml_only"), "statistical")
        self.queue_filter.currentIndexChanged.connect(self._apply_queue_filter)
        self.queue_search = QLineEdit()
        self.queue_search.setPlaceholderText(t("anomaly_demo_search_placeholder"))
        self.queue_search.setClearButtonEnabled(True)
        self.queue_search.setFixedHeight(40)
        self.queue_search.setStyleSheet(self._input_style())
        self.queue_search.textChanged.connect(self._apply_queue_filter)
        self.queue_count = QLabel(t("anomaly_demo_select_item"))
        self.queue_count.setStyleSheet(self._label_style())
        controls.addWidget(filter_label)
        controls.addWidget(self.queue_filter)
        controls.addSpacing(10)
        controls.addWidget(self.queue_search, 1)
        controls.addWidget(self.queue_count, 1)
        layout.addWidget(toolbar)
        self.queue_table = self._table(6)
        self.queue_table.setHorizontalHeaderLabels([
            t("anomaly_demo_employee"), t("anomaly_demo_signal"),
            t("anomaly_demo_track"), t("anomaly_demo_reason"),
            t("anomaly_demo_score"), t("anomaly_demo_priority_short"),
        ])
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for column, width in ((0, 110), (1, 170), (2, 110), (4, 90), (5, 150)):
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
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(12)
        layout.addWidget(
            self._tab_intro(
                "anomaly_demo_evidence_title",
                "anomaly_demo_evidence_description",
            )
        )
        evidence_header = QHBoxLayout()
        employee_label = QLabel(t("anomaly_demo_employee"))
        employee_label.setStyleSheet(self._label_style(bold=True))
        self.employee_select = AppSelect(height=40)
        self.employee_select.setMinimumWidth(220)
        self.employee_select.currentIndexChanged.connect(self._employee_selected)
        self.previous_employee_button = QPushButton(t("anomaly_demo_previous"))
        self.previous_employee_button.setStyleSheet(btn_outline(40))
        self.previous_employee_button.clicked.connect(lambda: self._move_employee(-1))
        self.next_employee_button = QPushButton(t("anomaly_demo_next"))
        self.next_employee_button.setStyleSheet(btn_outline(40))
        self.next_employee_button.clicked.connect(lambda: self._move_employee(1))
        self.employee_position = QLabel("-")
        self.employee_position.setAlignment(Qt.AlignCenter)
        self.employee_position.setMinimumWidth(64)
        self.employee_position.setStyleSheet(self._label_style(bold=True))
        evidence_header.addWidget(employee_label)
        evidence_header.addWidget(self.employee_select, 1)
        evidence_header.addWidget(self.previous_employee_button)
        evidence_header.addWidget(self.employee_position)
        evidence_header.addWidget(self.next_employee_button)
        layout.addLayout(evidence_header)
        self.evidence_prompt = QLabel(t("anomaly_demo_select_item"))
        self.evidence_prompt.setWordWrap(True)
        self.evidence_prompt.setStyleSheet(alert_ss("info", "QLabel"))
        self.evidence_prompt.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.evidence_prompt)
        self.profile_card = self._card()
        self.profile_layout = QGridLayout(self.profile_card)
        self.profile_layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(self.profile_card)
        section = QLabel(t("anomaly_demo_policy_calculation"))
        section.setStyleSheet(self._section_style())
        layout.addWidget(section)
        self.service_arithmetic = self._card()
        arithmetic_layout = QGridLayout(self.service_arithmetic)
        arithmetic_layout.setContentsMargins(16, 12, 16, 12)
        arithmetic_layout.setHorizontalSpacing(10)
        self.arithmetic_values = {}
        arithmetic_items = (
            ("observed", "anomaly_demo_observed_short", "+"),
            ("credit", "anomaly_demo_credit_short", "-"),
            ("delay", "anomaly_demo_delay_short", "="),
            ("adjusted", "anomaly_demo_adjusted_short", ""),
            ("deficit", "anomaly_demo_deficit", ""),
        )
        for column, (key, label_key, operator) in enumerate(arithmetic_items):
            label = QLabel(t(label_key))
            label.setStyleSheet(self._label_style())
            value = QLabel("-")
            value.setStyleSheet(self._label_style(bold=True))
            arithmetic_layout.addWidget(label, 0, column * 2)
            arithmetic_layout.addWidget(value, 1, column * 2)
            self.arithmetic_values[key] = value
            if operator:
                op = QLabel(operator)
                op.setStyleSheet(self._section_style())
                arithmetic_layout.addWidget(op, 1, column * 2 + 1)
        self.service_arithmetic.hide()
        layout.addWidget(self.service_arithmetic)
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
        self.calculation_table.setFixedHeight(104)
        layout.addWidget(self.calculation_table)
        self.no_calculation_label = QLabel(t("anomaly_demo_no_calculation"))
        self.no_calculation_label.setWordWrap(True)
        self.no_calculation_label.setStyleSheet(alert_ss("info", "QLabel"))
        self.no_calculation_label.setContentsMargins(16, 12, 16, 12)
        self.no_calculation_label.hide()
        layout.addWidget(self.no_calculation_label)
        self.calculation_evidence = QLabel("")
        self.calculation_evidence.setWordWrap(True)
        self.calculation_evidence.setStyleSheet(self._label_style())
        self.calculation_evidence.hide()
        layout.addWidget(self.calculation_evidence)
        self.limitations = QLabel("")
        self.limitations.setWordWrap(True)
        self.limitations.setStyleSheet(alert_ss("warning", "QLabel"))
        self.limitations.setContentsMargins(16, 12, 16, 12)
        self.limitations.hide()
        layout.addWidget(self.limitations)

        self.history_button = QPushButton(t("anomaly_demo_show_history"))
        self.history_button.setCheckable(True)
        self.history_button.setIcon(
            app_icon("fa5s.history", color=tokens().text, size=14)
        )
        self.history_button.setStyleSheet(btn_outline(40))
        self.history_button.clicked.connect(self._toggle_history)
        history_controls = QHBoxLayout()
        history_controls.addWidget(self.history_button)
        history_controls.addStretch()
        layout.addLayout(history_controls)

        self.history_panel = QWidget()
        history_layout = QVBoxLayout(self.history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)
        section = QLabel(t("anomaly_demo_events"))
        section.setStyleSheet(self._section_style())
        history_layout.addWidget(section)
        self.events_table = self._table(5)
        self.events_table.setHorizontalHeaderLabels([
            t("anomaly_demo_effective_date"), t("anomaly_demo_recorded_date"),
            t("anomaly_demo_event"), t("anomaly_demo_detail"),
            t("anomaly_demo_policy"),
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for column in (0, 1, 2, 4):
            self.events_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        history_layout.addWidget(self.events_table)
        self.history_panel.hide()
        layout.addWidget(self.history_panel)
        return page

    def _toggle_history(self, checked: bool):
        self.history_panel.setVisible(checked)
        self._refit_tabs()
        self.history_button.setText(
            t("anomaly_demo_hide_history")
            if checked
            else t("anomaly_demo_show_history")
        )

    def _build_comparison_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(12)
        layout.addWidget(
            self._tab_intro(
                "anomaly_demo_comparison_title",
                "anomaly_demo_comparison_description",
            )
        )
        self.comparison_help = QLabel(t("anomaly_demo_comparison_help"))
        self.comparison_help.setWordWrap(True)
        self.comparison_help.setStyleSheet(alert_ss("info", "QLabel"))
        self.comparison_help.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.comparison_help)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)
        chart_card = self._card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 14, 16, 12)
        chart_title = QLabel(t("anomaly_demo_outcome_chart"))
        chart_title.setWordWrap(True)
        chart_title.setStyleSheet(self._label_style(bold=True))
        self.comparison_chart = ComparisonOutcomeChart()
        self.comparison_chart.setToolTip(
            t("anomaly_demo_comparison_chart_tooltip")
        )
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(self.comparison_chart)
        charts_row.addWidget(chart_card, 1)
        count_card = self._card()
        count_layout = QVBoxLayout(count_card)
        count_layout.setContentsMargins(16, 14, 16, 12)
        count_title = QLabel(t("anomaly_demo_count_chart"))
        count_title.setWordWrap(True)
        count_title.setStyleSheet(self._label_style(bold=True))
        self.outcome_count_chart = OutcomeCountChart()
        self.outcome_count_chart.setToolTip(t("anomaly_demo_count_chart_tooltip"))
        count_layout.addWidget(count_title)
        count_layout.addWidget(self.outcome_count_chart)
        charts_row.addWidget(count_card, 1)
        layout.addLayout(charts_row)

        interpretation_title = QLabel(t("anomaly_demo_interpretation_title"))
        interpretation_title.setStyleSheet(self._label_style(bold=True))
        layout.addWidget(interpretation_title)
        self.comparison_interpretation = QLabel(t("anomaly_demo_interpretation_waiting"))
        self.comparison_interpretation.setWordWrap(True)
        self.comparison_interpretation.setStyleSheet(
            alert_ss("success", "QLabel")
        )
        self.comparison_interpretation.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.comparison_interpretation)

        exact_values = QLabel(t("anomaly_demo_exact_values"))
        exact_values.setStyleSheet(self._section_style())
        self.comparison_details_button = QPushButton(t("anomaly_demo_model_details"))
        self.comparison_details_button.setCheckable(True)
        self.comparison_details_button.setIcon(
            app_icon("fa5s.info-circle", color=tokens().text, size=13)
        )
        self.comparison_details_button.setStyleSheet(btn_outline(38))
        self.comparison_details_button.clicked.connect(
            lambda checked: (self.comparison_config.setVisible(checked), self._refit_tabs())
        )
        self.comparison_config = QLabel("")
        self.comparison_config.setWordWrap(True)
        self.comparison_config.setStyleSheet(alert_ss("info", "QLabel"))
        self.comparison_config.setContentsMargins(14, 10, 14, 10)
        self.comparison_config.hide()
        details_row = QHBoxLayout()
        details_row.addWidget(exact_values)
        details_row.addStretch()
        details_row.addWidget(self.comparison_details_button)
        layout.addLayout(details_row)
        layout.addWidget(self.comparison_config)

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
        self.comparison_table.setMinimumHeight(245)
        layout.addWidget(self.comparison_table)
        warning = QLabel(t("anomaly_demo_control_warning"))
        warning.setWordWrap(True)
        warning.setStyleSheet(alert_ss("warning", "QLabel"))
        warning.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(warning)
        return page

    def _build_evaluation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(12)
        layout.addWidget(
            self._tab_intro(
                "anomaly_demo_truth_title",
                "anomaly_demo_truth_description",
            )
        )
        help_text = QLabel(t("anomaly_demo_truth_help"))
        help_text.setWordWrap(True)
        help_text.setStyleSheet(alert_ss("danger", "QLabel"))
        help_text.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(help_text)
        grid = QGridLayout()
        self.evaluation_grid = grid
        self.evaluation_cards = []
        self.evaluation_values = {}
        labels = (
            ("positive", t("anomaly_demo_positive")),
            ("rare", t("anomaly_demo_lawful_rare")),
            ("evaluation", t("anomaly_demo_test")),
            ("reviews", t("anomaly_demo_records_per_method")),
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
            grid.addWidget(card, 0, index)
            self.evaluation_cards.append(card)
            self.evaluation_values[key] = value
        layout.addLayout(grid)

        method_title = QLabel(t("anomaly_demo_method_outcomes"))
        method_title.setStyleSheet(self._section_style())
        layout.addWidget(method_title)
        self.evaluation_method_table = self._table(5)
        self.evaluation_method_table.setHorizontalHeaderLabels([
            t("anomaly_demo_method"),
            t("anomaly_demo_found_short"),
            t("anomaly_demo_missed_short"),
            t("anomaly_demo_false_alerts_short"),
            t("anomaly_demo_reviews_short"),
        ])
        self.evaluation_method_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for column in (1, 2, 3, 4):
            self.evaluation_method_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Fixed
            )
            self.evaluation_method_table.setColumnWidth(column, 115)
        self.evaluation_method_table.setFixedHeight(238)
        layout.addWidget(self.evaluation_method_table)

        matrix_title = QLabel(t("anomaly_demo_policy_matrix_title"))
        matrix_title.setStyleSheet(self._section_style())
        layout.addWidget(matrix_title)
        self.outcome_matrix = self._table(4)
        self.outcome_matrix.setHorizontalHeaderLabels([
            t("anomaly_demo_truth_category"),
            t("anomaly_demo_total"),
            t("anomaly_demo_flagged"),
            t("anomaly_demo_not_flagged"),
        ])
        self.outcome_matrix.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            self.outcome_matrix.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Stretch
            )
        self.outcome_matrix.setMinimumHeight(175)
        self.outcome_matrix.setMaximumHeight(190)
        layout.addWidget(self.outcome_matrix)

        self.truth_cases_button = QPushButton(t("anomaly_demo_show_truth_cases"))
        self.truth_cases_button.setCheckable(True)
        self.truth_cases_button.setStyleSheet(btn_outline(38))
        self.truth_cases_button.clicked.connect(self._toggle_truth_cases)
        layout.addWidget(self.truth_cases_button, 0, Qt.AlignLeft)
        self.truth_cases_table = self._table(4)
        self.truth_cases_table.setHorizontalHeaderLabels([
            t("anomaly_demo_employee"),
            t("anomaly_demo_truth_category"),
            t("anomaly_demo_generated_label"),
            t("anomaly_demo_policy_outcome"),
        ])
        self.truth_cases_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for column in (0, 1, 3):
            self.truth_cases_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )
        self.truth_cases_table.hide()
        layout.addWidget(self.truth_cases_table)
        layout.addStretch()
        return page

    def _toggle_truth_cases(self, checked: bool):
        self.truth_cases_table.setVisible(checked)
        self._refit_tabs()
        self.truth_cases_button.setText(
            t("anomaly_demo_hide_truth_cases")
            if checked
            else t("anomaly_demo_show_truth_cases")
        )

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
        # The small demo model gains nothing from BLAS threading, and per-thread
        # buffers made the worker fail with "OpenBLAS ... Memory allocation" on
        # memory-constrained laptops. Thread count does not change the results.
        saved_env = {key: os.environ.get(key) for key in _WORKER_THREAD_ENV}
        os.environ.update({key: "1" for key in _WORKER_THREAD_ENV})
        try:
            self._process.start()
        finally:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
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
        self.scenario_detail_values["split"].setText(
            f"{result.train_count} / {result.validation_count} / {result.test_count}"
        )
        self.scenario_detail_values["model"].setText(
            t("anomaly_demo_model_config_short").format(trees=result.model_estimators)
        )
        self.progress.setValue(100)
        self.status.setText(t("anomaly_demo_complete"))
        self.stat_values["train"].setText(str(result.model_fit_count))
        self.stat_values["validation"].setText(str(result.validation_count))
        self.stat_values["test"].setText(str(result.eligible_test_count))
        self.stat_values["queue"].setText(str(len(result.queue)))
        self._apply_queue_filter()
        self.employee_select.clear()
        for item in result.queue:
            evidence = result.evidence_by_employee_id[item.employee_id]
            self.employee_select.addItem(
                f"{item.employee_id}  |  {self._track_label(evidence.employment_track)}",
                item.employee_id,
            )
        self._populate_comparison()
        comparison = result.comparisons[0]
        realized_capacity = (
            comparison.review_count / comparison.evaluation_count
            if comparison.evaluation_count
            else 0.0
        )
        self.comparison_help.setText(
            t("anomaly_demo_equal_capacity").format(
                reviews=comparison.review_count,
                records=comparison.evaluation_count,
                nominal=result.review_budget_fraction,
                realized=realized_capacity,
            )
        )
        self.comparison_config.setText(
            t("anomaly_demo_model_config_details").format(
                trees=result.model_estimators,
                dataset_seed=result.scenario.dataset_seed,
                split_seed=result.scenario.split_seed,
                model_seed=result.scenario.model_seed,
            )
        )
        self._populate_evaluation()
        self.export_button.setEnabled(True)
        preferred = next(
            (item for item in result.queue if result.evidence_by_employee_id[item.employee_id].calculations),
            result.queue[0] if result.queue else None,
        )
        if preferred is not None:
            self._show_employee(preferred.employee_id)
        self._refit_tabs()

    @Slot(str)
    def _on_failed(self, error: str):
        self._clear_results()
        self.progress.setValue(0)
        self.status.setText(f"{t('anomaly_demo_failed')}: {error}")
        self.status.setStyleSheet(alert_ss("danger", "QLabel"))
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
        self.scenario_details_button.setEnabled(not running)
        self.export_button.setEnabled(not running and self.result is not None)
        if not running and not self.status.text().startswith(t("anomaly_demo_failed")):
            self.status.setStyleSheet(self._label_style())

    def _apply_queue_filter(self, *_args):
        if self.result is None:
            self._visible_queue = ()
        else:
            selected = self.queue_filter.currentData()
            query = self.queue_search.text().strip().casefold()
            self._visible_queue = tuple(
                item for item in self.result.queue
                if (selected is None or item.source == selected)
                and (
                    not query
                    or query in item.employee_id.casefold()
                    or query in self._reason_label(item).casefold()
                    or query in self._track_label(item.employment_track).casefold()
                )
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
            self.queue_table.setCellWidget(
                row,
                5,
                ReviewPriorityIndicator(
                    item.priority,
                    t(f"anomaly_demo_priority_{item.priority}"),
                ),
            )
            self.queue_table.setRowHeight(row, 48)
        sync_table_widget_cells(self.queue_table)
        self.queue_table.setFixedHeight(
            self.queue_table.horizontalHeader().height()
            + sum(self.queue_table.rowHeight(row) for row in range(self.queue_table.rowCount()))
            + 4
        )
        self.queue_count.setText(
            f"{len(self._visible_queue)} / {len(self.result.queue) if self.result else 0}"
        )
        self.inspect_button.setEnabled(bool(self._visible_queue))
        self._refit_tabs()

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
        index = self.employee_select.findData(employee_id)
        if index >= 0 and index != self.employee_select.currentIndex():
            self.employee_select.setCurrentIndex(index)
        current_index = self.employee_select.currentIndex()
        self.employee_position.setText(
            t("anomaly_demo_employee_position").format(
                current=current_index + 1,
                total=self.employee_select.count(),
            )
            if current_index >= 0
            else "-"
        )
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
            value_widget = QLabel(value or "-")
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
        self._refit_tabs()

    def _employee_selected(self, _index: int):
        employee_id = self.employee_select.currentData()
        if employee_id and self.result is not None:
            self._show_employee(employee_id)

    def _move_employee(self, offset: int):
        count = self.employee_select.count()
        if count:
            index = (self.employee_select.currentIndex() + offset) % count
            self.employee_select.setCurrentIndex(index)

    def _populate_calculations(self, evidence: DemoEmployeeEvidence):
        self.calculation_table.clearContents()
        self.calculation_table.clearSpans()
        self.calculation_table.setRowCount(len(evidence.calculations))
        if not evidence.calculations:
            self.calculation_table.hide()
            self.service_arithmetic.hide()
            self.no_calculation_label.show()
            self.calculation_evidence.hide()
            return
        self.no_calculation_label.hide()
        self.calculation_table.show()
        self.service_arithmetic.show()
        latest = evidence.calculations[-1]
        arithmetic = {
            "observed": latest.observed_service_months,
            "credit": latest.commendation_credit_months,
            "delay": latest.sanction_delay_months,
            "adjusted": latest.adjusted_service_months,
            "deficit": latest.service_deficit_months,
        }
        for key, value in arithmetic.items():
            self.arithmetic_values[key].setText(self._months(value))
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
        self.calculation_table.setFixedHeight(
            self.calculation_table.horizontalHeader().height()
            + sum(self.calculation_table.rowHeight(row) for row in range(self.calculation_table.rowCount()))
            + 4
        )
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
        self._fit_table_height(self.events_table, max_rows=12)

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
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if column == 0 and item.representation == "policy_matched":
                    cell.setForeground(QColor(tokens().brand))
                    cell.setIcon(
                        app_icon("fa5s.check-circle", color=tokens().brand, size=13)
                    )
                self.comparison_table.setItem(row, column, cell)
            self.comparison_table.setRowHeight(row, 48)
        sync_table_widget_cells(self.comparison_table)
        self._fit_table_height(self.comparison_table)
        self.comparison_chart.set_comparisons(self.result.comparisons)
        self.outcome_count_chart.set_comparisons(self.result.comparisons)
        policy = next(
            item for item in self.result.comparisons
            if item.representation == "policy_matched"
        )
        wrong = next(
            item for item in self.result.comparisons
            if item.representation == "wrong_policy_control"
        )
        if self.result.evaluation.positive_count == 0:
            key = "anomaly_demo_interpretation_no_positives"
        elif policy.true_positives == 0:
            key = "anomaly_demo_interpretation_zero"
        elif (
            policy.true_positives == wrong.true_positives
            and policy.false_positives == wrong.false_positives
        ):
            key = "anomaly_demo_interpretation_no_attribution"
        else:
            key = "anomaly_demo_interpretation_exploratory"
        self.comparison_interpretation.setText(t(key))

    def _populate_evaluation(self):
        if self.result is None:
            return
        summary = self.result.evaluation
        category_counts = {
            category: sum(
                case.category == category for case in self.result.truth_cases
            )
            for category in ("injected_error", "lawful_rare", "ordinary")
        }
        values = {
            "positive": str(summary.positive_count),
            "rare": str(category_counts["lawful_rare"]),
            "evaluation": str(summary.evaluation_count),
            "reviews": str(summary.ml_review_count),
        }
        for key, value in values.items():
            self.evaluation_values[key].setText(value)

        self.evaluation_method_table.setRowCount(len(self.result.comparisons))
        for row, comparison in enumerate(self.result.comparisons):
            row_values = (
                t(f"anomaly_demo_method_{comparison.representation}"),
                str(comparison.true_positives),
                str(comparison.false_negatives),
                str(comparison.false_positives),
                str(comparison.review_count),
            )
            for column, value in enumerate(row_values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.evaluation_method_table.setItem(row, column, cell)
            self.evaluation_method_table.setRowHeight(row, 46)
        self._fit_table_height(self.evaluation_method_table)

        self.outcome_matrix.setRowCount(3)
        for row, category in enumerate(
            ("injected_error", "lawful_rare", "ordinary")
        ):
            cases = [
                case for case in self.result.truth_cases
                if case.category == category
            ]
            flagged = sum(case.policy_matched_flagged for case in cases)
            row_values = (
                t(f"anomaly_demo_truth_{category}"),
                str(len(cases)),
                str(flagged),
                str(len(cases) - flagged),
            )
            for column, value in enumerate(row_values):
                cell = QTableWidgetItem(value)
                if column == 2 and flagged:
                    cell.setBackground(
                        QColor("#d9f4e4" if category == "injected_error" else "#fff0c2")
                    )
                if column == 3 and category == "injected_error" and len(cases) - flagged:
                    cell.setBackground(QColor("#fde2e2"))
                self.outcome_matrix.setItem(row, column, cell)
            self.outcome_matrix.setRowHeight(row, 42)
        sync_table_widget_cells(self.outcome_matrix)
        self._fit_table_height(self.outcome_matrix)

        visible_cases = [
            case for case in self.result.truth_cases
            if case.category != "ordinary"
        ]
        self.truth_cases_table.setRowCount(len(visible_cases))
        for row, case in enumerate(visible_cases):
            labels = ", ".join(
                self._truth_label(label) for label in case.labels
            )
            row_values = (
                case.employee_id,
                t(f"anomaly_demo_truth_{case.category}"),
                labels,
                t("anomaly_demo_flagged_for_review")
                if case.policy_matched_flagged
                else t("anomaly_demo_not_flagged"),
            )
            for column, value in enumerate(row_values):
                cell = QTableWidgetItem(value)
                if column == 2:
                    cell.setToolTip(value)
                self.truth_cases_table.setItem(row, column, cell)
            self.truth_cases_table.setRowHeight(row, 42)
        sync_table_widget_cells(self.truth_cases_table)
        self._fit_table_height(self.truth_cases_table)

    @Slot()
    def _export_csv(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("anomaly_demo_export_report"),
            "myhr_anomaly_review.csv",
            t("csv_files_filter"),
        )
        if not path:
            return
        try:
            self._write_csv_report(path)
        except OSError as exc:
            QMessageBox.critical(self, t("error"), str(exc))
            return
        QMessageBox.information(
            self,
            t("success"),
            t("anomaly_demo_exported_to").format(path=path),
        )

    def _write_csv_report(self, path: str):
        result = self.result
        if result is None:
            raise RuntimeError("analysis result is required")
        comparison = result.comparisons[0]
        realized = (
            comparison.review_count / comparison.evaluation_count
            if comparison.evaluation_count
            else 0.0
        )
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["MyHR synthetic anomaly-review report"])
            writer.writerow(["Scenario", result.scenario.scenario_id])
            writer.writerow(["Population", result.scenario.population])
            writer.writerow(["Injected mechanism", result.scenario.mechanism])
            writer.writerow(["Lawful rare pattern", result.scenario.rare_pattern])
            writer.writerow(["Dataset seed", result.scenario.dataset_seed])
            writer.writerow(["Split seed", result.scenario.split_seed])
            writer.writerow(["Model seed", result.scenario.model_seed])
            writer.writerow(["Model trees", result.model_estimators])
            writer.writerow(["Nominal review capacity", result.review_budget_fraction])
            writer.writerow(["Realized review capacity", realized])
            writer.writerow([])
            writer.writerow(["METHOD COMPARISON"])
            writer.writerow([
                "representation", "evaluation_records", "reviewed", "tp", "fp",
                "fn", "recall", "precision", "rare_legitimate_flagged",
                "rare_legitimate_total",
            ])
            for item in result.comparisons:
                writer.writerow([
                    item.representation,
                    item.evaluation_count,
                    item.review_count,
                    item.true_positives,
                    item.false_positives,
                    item.false_negatives,
                    item.recall,
                    item.precision,
                    item.rare_legitimate_flagged,
                    item.rare_legitimate_count,
                ])
            writer.writerow([])
            writer.writerow(["REVIEW QUEUE"])
            writer.writerow([
                "employee_id", "signal", "track", "reason", "score",
                "review_priority",
            ])
            for item in result.queue:
                writer.writerow([
                    item.employee_id,
                    item.source,
                    item.employment_track,
                    item.reason_code,
                    item.anomaly_score,
                    item.priority,
                ])
            writer.writerow([])
            writer.writerow(["SYNTHETIC EVALUATION ONLY"])
            writer.writerow([
                "employee_id", "truth_category", "generated_labels",
                "policy_matched_flagged",
            ])
            for case in result.truth_cases:
                writer.writerow([
                    case.employee_id,
                    case.category,
                    "|".join(case.labels),
                    case.policy_matched_flagged,
                ])

    @Slot()
    def _export_pdf(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("anomaly_demo_export_report"),
            "myhr_anomaly_review.pdf",
            t("pdf_files_filter"),
        )
        if not path:
            return
        try:
            self._write_pdf_report(path)
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, t("error"), str(exc))
            return
        QMessageBox.information(
            self,
            t("success"),
            t("anomaly_demo_exported_to").format(path=path),
        )

    def _write_pdf_report(self, path: str):
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setPageMargins(
            QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter
        )
        document = QTextDocument()
        document.setHtml(self._report_html())
        document.print_(writer)

    def _report_html(self) -> str:
        result = self.result
        if result is None:
            raise RuntimeError("analysis result is required")
        comparison_rows = "".join(
            "<tr>"
            f"<td>{escape(t(f'anomaly_demo_method_{item.representation}'))}</td>"
            f"<td>{item.evaluation_count}</td><td>{item.review_count}</td>"
            f"<td>{item.true_positives}</td><td>{item.false_positives}</td>"
            f"<td>{escape(self._ratio(item.recall))}</td>"
            f"<td>{escape(self._ratio(item.precision))}</td>"
            "</tr>"
            for item in result.comparisons
        )
        truth_rows = "".join(
            "<tr>"
            f"<td>{escape(case.employee_id)}</td>"
            f"<td>{escape(t(f'anomaly_demo_truth_{case.category}'))}</td>"
            f"<td>{escape(', '.join(self._truth_label(label) for label in case.labels))}</td>"
            f"<td>{escape(t('anomaly_demo_flagged_for_review') if case.policy_matched_flagged else t('anomaly_demo_not_flagged'))}</td>"
            "</tr>"
            for case in result.truth_cases
            if case.category != "ordinary"
        )
        option = result.scenario
        return f"""
        <html><head><style>
        body {{ font-family: Arial, sans-serif; color: #17211f; font-size: 10pt; }}
        h1 {{ color: #063b32; }} h2 {{ color: #184f45; margin-top: 18px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
        th {{ background: #0b5b4d; color: white; padding: 6px; text-align: left; }}
        td {{ border: 1px solid #d8dfdc; padding: 6px; }}
        .notice {{ background: #eef7f2; padding: 10px; border: 1px solid #bcd8ca; }}
        .warning {{ background: #fff3d6; padding: 10px; border: 1px solid #e4c774; }}
        </style></head><body>
        <h1>{escape(t('anomaly_demo_title'))}</h1>
        <p class="notice">{escape(t('anomaly_demo_governance'))}</p>
        <h2>{escape(t('anomaly_demo_scenario_details'))}</h2>
        <p><b>{escape(t('anomaly_demo_scenario'))}:</b>
        {escape(t(f'anomaly_demo_population_{option.population}'))}<br>
        <b>{escape(t('anomaly_demo_generated_label'))}:</b>
        {escape(t(f'anomaly_demo_mechanism_{option.mechanism}'))}<br>
        <b>{escape(t('anomaly_demo_lawful_rare'))}:</b>
        {escape(t(f'anomaly_demo_rare_{option.rare_pattern}'))}</p>
        <h2>{escape(t('anomaly_demo_tab_comparison'))}</h2>
        <table><tr><th>{escape(t('anomaly_demo_method'))}</th>
        <th>{escape(t('anomaly_demo_population_short'))}</th>
        <th>{escape(t('anomaly_demo_reviews_short'))}</th><th>TP</th><th>FP</th>
        <th>{escape(t('anomaly_demo_recall'))}</th><th>{escape(t('anomaly_demo_precision'))}</th></tr>
        {comparison_rows}</table>
        <p class="warning">{escape(t('anomaly_demo_control_warning'))}</p>
        <h2>{escape(t('anomaly_demo_truth_title'))}</h2>
        <p>{escape(t('anomaly_demo_truth_help'))}</p>
        <table><tr><th>{escape(t('anomaly_demo_employee'))}</th>
        <th>{escape(t('anomaly_demo_truth_category'))}</th>
        <th>{escape(t('anomaly_demo_generated_label'))}</th>
        <th>{escape(t('anomaly_demo_policy_outcome'))}</th></tr>{truth_rows}</table>
        </body></html>
        """

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
            self.evaluation_method_table,
            self.outcome_matrix,
            self.truth_cases_table,
        ):
            table.clearContents()
            table.setRowCount(0)
        for value in self.evaluation_values.values():
            value.setText("-")
        self.queue_count.setText(t("anomaly_demo_select_item"))
        self.evidence_prompt.setText(t("anomaly_demo_select_item"))
        self.employee_select.clear()
        self.calculation_evidence.clear()
        self.calculation_evidence.hide()
        self.calculation_table.hide()
        self.no_calculation_label.hide()
        self.service_arithmetic.hide()
        self.limitations.clear()
        self.limitations.hide()
        self.inspect_button.setEnabled(False)
        self.export_button.setEnabled(False)
        # Empty tables show only their header instead of a blank block.
        for table in (
            self.queue_table,
            self.comparison_table,
            self.evaluation_method_table,
            self.outcome_matrix,
            self.truth_cases_table,
            self.events_table,
        ):
            self._fit_table_height(table)
        self.comparison_chart.set_comparisons(())
        self.outcome_count_chart.set_comparisons(())
        self.comparison_interpretation.setText(
            t("anomaly_demo_interpretation_waiting")
        )
        self._refit_tabs()

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
    def _truth_label(label: str):
        key = f"anomaly_demo_truth_label_{label}"
        translated = t(key)
        return label.replace("_", " ").title() if translated == key else translated

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
    def _fit_table_height(table, max_rows: int | None = None):
        """Size a table to its header and rows so no blank band remains."""
        rows = table.rowCount()
        shown = rows if max_rows is None else min(rows, max_rows)
        height = table.horizontalHeader().height() + sum(
            table.rowHeight(row) for row in range(shown)
        ) + 4
        table.setMinimumHeight(0)
        table.setMaximumHeight(16777215)
        table.setFixedHeight(height)

    @staticmethod
    def _table(columns: int):
        table = QTableWidget()
        table.setColumnCount(columns)
        table.setStyleSheet(
            table_style(
                header_bg=tokens().surface_muted,
                header_color=tokens().text_muted,
                header_font_size=12,
                header_weight=700,
                header_height=44,
                row_font_size=13,
                item_padding=10,
            )
        )
        table.verticalHeader().setVisible(False)
        # Consistent left alignment for headers and contents in every table.
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
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

    @staticmethod
    def _tab_intro(title_key: str, description_key: str):
        intro = QWidget()
        intro.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        box = QVBoxLayout(intro)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(3)
        title = QLabel(t(title_key))
        title.setStyleSheet(
            f"font-size: 19px; font-weight: 800; color: {tokens().text};"
        )
        description = QLabel(t(description_key))
        description.setWordWrap(True)
        description.setStyleSheet(
            f"font-size: 13px; color: {tokens().text_muted};"
        )
        box.addWidget(title)
        box.addWidget(description)
        return intro

    @staticmethod
    def _anomaly_tab_style():
        tkn = tokens()
        selected_text = "#062f28" if tkn.name == "dark" else "#ffffff"
        # Opaque, visibly tinted hover: the generic hover token is almost
        # identical to the tab-bar background and read as transparent.
        hover_bg = "#203a31" if tkn.name == "dark" else "#dcefe2"
        hover_border = tkn.brand if tkn.name == "dark" else "#9cc9ad"
        return f"""
            QTabWidget::pane {{
                border: none;
                background: {tkn.canvas};
                margin-top: 26px;
            }}
            QTabBar {{
                background: {tkn.surface_muted};
                border: 1px solid {tkn.border};
                border-radius: 18px;
                padding: 4px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {tkn.text};
                border: none;
                border-radius: 12px;
                padding: 8px 16px;
                margin: 2px;
                min-height: 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            QTabBar::tab:selected {{
                background: {tkn.brand};
                color: {selected_text};
            }}
            QTabBar::tab:selected:hover {{
                background: {tkn.brand_hover};
                color: {selected_text};
            }}
            QTabBar::tab:!selected:hover {{
                background: {hover_bg};
                color: {tkn.text};
                border: 1px solid {hover_border};
            }}
        """

    @staticmethod
    def _input_style():
        tkn = tokens()
        return f"""
            QLineEdit {{
                background: {tkn.input};
                color: {tkn.text};
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {tkn.brand}; }}
        """
