"""
Settings Page
- General company branding and organization details
- Salary ranges and annual increment rules
- Promotion race settings
- Security and database utilities
"""

from hashlib import sha256
import csv
import json
import os
import shutil
import sqlite3
from datetime import datetime

import qtawesome as qta
from sqlalchemy import func
from PySide6.QtCore import Qt, QSize, QTimer, QMarginsF
from PySide6.QtGui import QColor, QFont, QTextDocument, QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QMessageBox, QTabWidget,
    QSpinBox, QDoubleSpinBox, QFileDialog, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout
)

from src.core.i18n import t
from src.core.app_settings import app_settings, company_name
from src.ui.animations import install_tab_transition
from src.ui.styles import PILL_TAB_SS, enable_table_row_selection, prepare_table_cell_widget, polish_combo_box, table_style
from src.ui.theme import THEME_DARK, tokens
from src.database.connection import get_session, log_action, DB_PATH
from src.database.models import AuditLog, Title, SystemUser, PromotionRule, Employee, OrgUnit
from src.services.reporting_service import (
    ReportFilters,
    available_report_years,
    build_yearly_report,
    build_yearly_report_html,
    report_section_titles,
)


PAGE_BG = tokens().canvas
TEXT = tokens().text
MUTED = tokens().text_muted
BLACK = tokens().text
BLUE = tokens().brand

LEVEL_META = {
    "L7": ("level_l7_label", "#2563eb", "#dbeafe"),
    "L6": ("level_l6_label", "#16a34a", "#dcfce7"),
    "L5": ("level_l5_label", "#d97706", "#fef3c7"),
    "L4": ("level_l4_label", "#7c3aed", "#ede9fe"),
    "L3": ("level_l3_label", "#db2777", "#fce7f3"),
    "L2": ("level_l2_label", "#0284c7", "#e0f2fe"),
    "L1": ("level_l1_label", "#dc2626", "#fee2e2"),
    "Other": ("level_other_label", "#2563eb", "#dbeafe"),
}
LEVEL_ORDER = {level: index for index, level in enumerate(["L7", "L6", "L5", "L4", "L3", "L2", "L1", "Other"])}

CARD_SS = f"""
QFrame#Card {{
    background: {tokens().surface};
    border: 1px solid {tokens().border};
    border-radius: 8px;
}}
QFrame#Card QLabel {{
    background: transparent;
    border: none;
}}
"""

NOTE_BLUE_SS = f"""
QFrame {{
    background: {tokens().selected};
    border: 1px solid {tokens().brand};
    border-radius: 8px;
}}
QLabel {{
    background: transparent;
    border: none;
}}
"""

NOTE_YELLOW_SS = f"""
QFrame {{
    background: {tokens().warning_soft};
    border: 1px solid {tokens().warning};
    border-radius: 8px;
}}
QLabel {{
    background: transparent;
    border: none;
}}
"""

INPUT_SS = f"""
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {tokens().input};
    color: {tokens().text};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0 12px;
    min-height: 44px;
    font-size: 14px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    background: {tokens().surface};
    border: 1px solid {tokens().brand};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0px;
    border: none;
}}
"""

COMBO_SS = f"""
QComboBox {{
    background: {tokens().input};
    color: {tokens().text};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0 34px 0 12px;
    min-height: 44px;
    font-size: 14px;
}}
QComboBox:focus {{
    background: {tokens().surface};
    border: 1px solid {tokens().brand};
}}
QComboBox::drop-down {{
    width: 30px;
    border: none;
}}
QComboBox::down-arrow {{
    image: url(src/ui/assets/chevron_down.svg);
    width: 13px;
    height: 13px;
}}
QComboBox QAbstractItemView {{
    background: {tokens().surface};
    color: {tokens().text};
    border: 1px solid {tokens().border_strong};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {tokens().selected};
    selection-color: {tokens().text};
    outline: none;
}}
"""

MESSAGE_BOX_SS = f"""
QMessageBox {{ background: {tokens().surface}; color: {tokens().text}; }}
QMessageBox QLabel {{ color: {tokens().text}; background: transparent; font-size: 13px; }}
QPushButton {{
    background: {tokens().surface};
    color: {tokens().text};
    border: 1px solid {tokens().border_strong};
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {tokens().hover}; }}
QPushButton:default {{ background: {tokens().brand}; color: {"#062f28" if tokens().name == THEME_DARK else "#ffffff"}; border: none; }}
"""


class SettingsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setObjectName("SettingsPage")
        self.setStyleSheet(f"QWidget#SettingsPage {{ background: {PAGE_BG}; }}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("settings_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {TEXT}; background: transparent;")
        subtitle = QLabel(t("settings_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {MUTED}; background: transparent;")

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(PILL_TAB_SS)
        self.tabs.addTab(GeneralTab(self.user), t("general"))
        self._add_policy_tabs()
        self.tabs.addTab(UserManagementTab(self.user), t("user_management"))
        self.tabs.addTab(DatabaseTab(self.user), t("database_tab"))
        self.tabs.currentChanged.connect(self._handle_tab_changed)
        install_tab_transition(self.tabs, duration=240, offset=10)
        layout.addWidget(self.tabs, 1)

    def _add_policy_tabs(self, insert_at=None):
        self.summary_tab = PolicySummaryTab(self.user)
        self.level_tab = LevelManagementTab(self.user, on_saved=self._reload_policy_tabs)
        self.salary_tab = SalaryTab(self.user, on_saved=self._refresh_policy_views)
        self.promotion_tab = SettingsPromotionTab(self.user, on_saved=self._refresh_policy_views)
        self.increment_tab = IncrementTab(self.user, on_saved=self._refresh_policy_views)
        tabs = [
            (self.summary_tab, t("policy_summary")),
            (self.level_tab, t("level_management")),
            (self.salary_tab, t("salary_ranges")),
            (self.promotion_tab, t("promotion_rules_tab")),
            (self.increment_tab, t("annual_increment")),
        ]
        if insert_at is None:
            for widget, label in tabs:
                self.tabs.addTab(widget, label)
        else:
            for offset, (widget, label) in enumerate(tabs):
                self.tabs.insertTab(insert_at + offset, widget, label)

    def _reload_policy_tabs(self):
        current_label = self.tabs.tabText(self.tabs.currentIndex())
        start = 1
        for _ in range(5):
            widget = self.tabs.widget(start)
            self.tabs.removeTab(start)
            if widget:
                widget.deleteLater()
        self._add_policy_tabs(start)
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == current_label:
                self.tabs.setCurrentIndex(index)
                break

    def _refresh_policy_views(self):
        for widget in (getattr(self, "summary_tab", None), getattr(self, "level_tab", None)):
            refresh = getattr(widget, "refresh", None)
            if callable(refresh):
                refresh()

    def _refresh_current_tab(self, index):
        widget = self.tabs.widget(index)
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def _handle_tab_changed(self, index):
        self._refresh_current_tab(index)


class PolicySummaryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.content, self.outer = _content()
        _set_page(self, self.content)
        self.refresh()

    def refresh(self):
        _clear_layout(self.outer)

        header, header_layout = _section_card(
            t("policy_summary"),
            t("policy_summary_subtitle"),
            "fa5s.clipboard-list",
            BLUE,
        )
        header_layout.addWidget(_note_card(
            t("policy_summary_note_title"),
            [
                t("policy_summary_note_rules"),
                t("policy_summary_note_readonly"),
                t("policy_summary_note_data"),
            ],
            "fa5s.info-circle",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        self.outer.addWidget(header)

        session = get_session()
        try:
            titles = _ordered_titles(session)
            order_map = _promotion_order_map(session)
            title_counts = {
                title_id: count for title_id, count in
                session.query(Employee.title_id, func.count(Employee.id))
                .filter(Employee.status == "active")
                .group_by(Employee.title_id)
                .all()
            }
            rules = session.query(PromotionRule).all()
            rules.sort(key=lambda rule: order_map.get(rule.from_title_id, _level_sort_key(rule.from_title)))

            currency = titles[0].currency if titles else "EUR"
            currencies = sorted({title.currency for title in titles if title.currency})
            other_title = next((title for title in titles if title.name == "Other"), None)
            metric_grid = QGridLayout()
            metric_grid.setHorizontalSpacing(14)
            metric_grid.setVerticalSpacing(14)
            metrics = [
                self._metric_card(t("configured_levels"), str(len(titles)), "fa5s.layer-group", BLUE, "#dbeafe"),
                self._metric_card(t("active_promotion_tracks"), str(sum(1 for rule in rules if rule.is_active)), "fa5s.route", "#16a34a", "#dcfce7"),
                self._metric_card(t("salary_currency"), ", ".join(currencies) or currency, "fa5s.money-bill-wave", "#7c3aed", "#ede9fe"),
                self._metric_card(t("other_track"), t("configured") if other_title else t("not_configured"), "fa5s.user-cog", "#475569", "#e2e8f0"),
            ]
            for index, metric in enumerate(metrics):
                metric_grid.addWidget(metric, index // 2, index % 2)
            self.outer.addLayout(metric_grid)

            salary_rows = []
            increment_rows = []
            for title in titles:
                salary_rows.append([
                    title.name,
                    title.label,
                    f"{title.base_salary_min:.0f}-{title.base_salary_max:.0f} {title.currency or currency}",
                    str(title_counts.get(title.id, 0)),
                ])
                increment_rows.append([
                    title.name,
                    title.annual_increment_type.title(),
                    _format_increment(title),
                    _format_promotion_bump(title),
                ])

            promotion_rows = [[
                rule.from_title.name,
                rule.to_title.name,
                t("month_count_plain", count=rule.base_months),
                _format_promotion_bump(rule.to_title),
                t("active") if rule.is_active else t("inactive"),
            ] for rule in rules]

        finally:
            session.close()

        summaries = QVBoxLayout()
        summaries.setSpacing(18)
        summaries.addWidget(self._summary_card(
            t("salary_policy_summary"),
            t("salary_policy_summary_subtitle"),
            ["Level", t("name"), t("salary_range"), t("active_employees")],
            salary_rows,
            "fa5s.coins",
            [78, 180, 260, 142],
        ))
        summaries.addWidget(self._summary_card(
            t("promotion_policy_summary"),
            t("promotion_policy_summary_subtitle"),
            [t("from_level"), t("to_level"), t("duration"), t("salary_increase"), t("status")],
            promotion_rows,
            "fa5s.chart-line",
            [106, 98, 124, 150, 98],
        ))
        summaries.addWidget(self._summary_card(
            t("annual_increment_summary"),
            t("annual_increment_summary_subtitle"),
            ["Level", t("increment_type"), t("increment_value"), t("promotion_salary_increase")],
            increment_rows,
            "fa5s.percentage",
            [78, 190, 170, 160],
        ))
        summaries.addWidget(self._summary_card(
            t("modifier_policy_summary"),
            t("modifier_policy_summary_subtitle"),
            [t("type"), t("category"), t("impact"), t("notes")],
            self._modifier_rows(),
            "fa5s.balance-scale",
            [130, 170, 130, 260],
        ))
        self.outer.addLayout(summaries)
        self.outer.addStretch()

    def _metric_card(self, label, value, icon_name, color, bg):
        card = _plain_card()
        card.setFixedHeight(94)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)
        layout.addWidget(_badge_icon(icon_name, color, bg))
        text = QVBoxLayout()
        text.setSpacing(0)
        text.setAlignment(Qt.AlignVCenter)
        title = QLabel(label)
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {MUTED}; background: transparent;")
        number = QLabel(value)
        number.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {TEXT}; background: transparent;")
        text.addWidget(title)
        text.addWidget(number)
        layout.addLayout(text)
        layout.addStretch()
        return card

    def _summary_card(self, title, subtitle, headers, rows, icon_name, column_widths=None):
        card = _plain_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(_badge_icon(icon_name, BLUE, "#dbeafe"))
        text = QVBoxLayout()
        text.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 900; color: {TEXT}; background: transparent;")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {MUTED}; background: transparent;")
        text.addWidget(title_lbl)
        text.addWidget(sub_lbl)
        head.addLayout(text)
        head.addStretch()
        layout.addLayout(head)

        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        table.setStyleSheet(_summary_table_ss())
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.horizontalHeader().setMinimumSectionSize(54)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(table)
        table.setShowGrid(False)
        table.setFocusPolicy(Qt.NoFocus)
        for col in range(table.columnCount()):
            item = table.horizontalHeaderItem(col)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for row_index, row in enumerate(rows):
            table.setRowHeight(row_index, 42)
            for col_index, value in enumerate(row):
                _set_tooltip_item(table, row_index, col_index, value)
        table.setFixedHeight(50 + (42 * max(1, len(rows))) + 4)
        layout.addWidget(table)
        return card

    def _modifier_rows(self):
        rows = [
            [t("commendation"), t("category_1"), t("negative_month_count", count=1), t("commendation_modifier_note")],
            [t("commendation"), t("category_2"), t("negative_month_count", count=3), t("commendation_modifier_note")],
            [t("commendation"), t("category_3"), t("negative_month_count", count=6), t("commendation_modifier_note")],
            [t("sanction"), t("verbal_warning"), t("manual_delay"), t("sanction_modifier_note")],
            [t("sanction"), t("written_warning"), t("manual_delay"), t("sanction_modifier_note")],
            [t("sanction"), t("suspension"), t("manual_delay"), t("sanction_modifier_note")],
            [t("sanction"), t("final_warning"), t("manual_delay"), t("sanction_modifier_note")],
            [t("level_other_label"), t("ongoing_service_track"), t("annual_increment_only"), t("other_track_policy_note")],
        ]
        return rows


class GeneralTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.settings = app_settings()
        self._build()
        self._load()

    def _build(self):
        content, outer = _content()
        row = QHBoxLayout()
        row.setSpacing(30)
        row.setAlignment(Qt.AlignTop)

        form, form_layout = _section_card(t("organization_information"), t("organization_information_subtitle"), "fa5s.building", BLUE)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)

        self.company_name = _line_edit()
        self.company_subtitle = _line_edit()
        self.company_address = _line_edit()
        self.fiscal_start = _line_edit("01-01")
        self.timezone = _line_edit("Europe/Budapest")

        _add_form_field(grid, 0, 0, t("company_name"), self.company_name)
        _add_form_field(grid, 0, 1, t("company_subtitle"), self.company_subtitle)
        _add_form_field(grid, 1, 0, t("company_address"), self.company_address)
        _add_form_field(grid, 1, 1, t("fiscal_year_start"), self.fiscal_start)
        _add_form_field(grid, 2, 0, t("timezone"), self.timezone)
        form_layout.addLayout(grid)
        row.addWidget(form, 3)

        actions, actions_layout = _section_card(t("actions"), None, "fa5s.save", BLACK)
        save = _button(t("save_general_settings"), "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        actions_layout.addWidget(save)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(_note_card(
            t("branding_update"),
            [
                t("branding_note_sidebar"),
                t("branding_note_login"),
                t("branding_note_subtitle"),
            ],
            "fa5s.info-circle",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        actions_layout.addStretch()
        row.addWidget(actions, 1)

        outer.addLayout(row)
        outer.addStretch()
        _set_page(self, content)

    def _load(self):
        self.company_name.setText(self.settings.value("company/name", "MyHR"))
        self.company_subtitle.setText(self.settings.value("company/subtitle", "Employee Management"))
        self.company_address.setText(self.settings.value("company/address", "Budapest, Hungary"))
        self.fiscal_start.setText(self.settings.value("company/fiscal_start", "01-01"))
        self.timezone.setText(self.settings.value("company/timezone", "Europe/Budapest"))

    def _save(self):
        self.settings.setValue("company/name", self.company_name.text().strip() or "MyHR")
        self.settings.setValue("company/subtitle", self.company_subtitle.text().strip() or "Employee Management")
        self.settings.setValue("company/address", self.company_address.text().strip())
        self.settings.setValue("company/fiscal_start", self.fiscal_start.text().strip() or "01-01")
        self.settings.setValue("company/timezone", self.timezone.text().strip() or "Europe/Budapest")
        self.settings.sync()

        session = get_session()
        try:
            log_action(session, action="settings.general", performed_by_id=self.user.id, description="Organization settings updated")
            session.commit()
        finally:
            session.close()

        window = self.window()
        sidebar = getattr(window, "sidebar", None)
        if sidebar and hasattr(sidebar, "refresh_branding"):
            sidebar.refresh_branding()
        if hasattr(window, "setWindowTitle"):
            window.setWindowTitle(f"{company_name('MyHR')} - {t('employee_management_system')}")
        _information(self, t("success"), t("general_settings_saved"))


class LevelManagementTab(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved
        self._build()
        self.refresh()

    def _build(self):
        content, outer = _content()

        header, header_layout = _section_card(
            t("level_management"),
            t("level_management_subtitle"),
            "fa5s.layer-group",
            BLUE,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        if self.user.role == "admin":
            add = _button(t("add_level"), "fa5s.plus", primary=True)
            add.clicked.connect(self._add_level)
            action_row.addWidget(add, alignment=Qt.AlignLeft)
        action_row.addStretch()
        header_layout.addLayout(action_row)
        header_layout.addWidget(_note_card(
            t("level_management_rules"),
            [
                t("level_rule_complete_policy"),
                t("level_rule_salary_required"),
                t("level_rule_existing_tabs"),
            ],
            "fa5s.info-circle",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        outer.addWidget(header)

        card = _plain_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            t("level"), t("name"), t("degree"), t("salary"),
            t("annual_short"), t("target"), t("months"), t("raise"), t("actions")
        ])
        self.table.setStyleSheet(_summary_table_ss())
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        header_view = self.table.horizontalHeader()
        header_view.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_view.setMinimumSectionSize(56)
        for col in range(self.table.columnCount()):
            header_view.setSectionResizeMode(col, QHeaderView.Fixed)
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setTextAlignment((Qt.AlignCenter if col in (0, 2, 4, 5, 6, 7, 8) else Qt.AlignLeft) | Qt.AlignVCenter)
        layout.addWidget(self.table)
        outer.addWidget(card)
        outer.addStretch()
        _set_page(self, content)

    def refresh(self):
        session = get_session()
        try:
            titles = _ordered_titles(session)
            rules_by_from = {rule.from_title_id: rule for rule in session.query(PromotionRule).all()}
            rows = []
            for title in titles:
                rule = rules_by_from.get(title.id)
                rows.append({
                    "id": title.id,
                    "name": title.name,
                    "protected": title.name == "Other",
                    "values": [
                        title.name,
                        title.label,
                        title.degree_requirement,
                        f"{title.base_salary_min:.0f}-{title.base_salary_max:.0f} {title.currency}",
                        _format_increment(title),
                        rule.to_title.name if rule else "-",
                        t("month_count_plain", count=rule.base_months) if rule else "-",
                        _format_promotion_bump(rule.to_title) if rule else _format_promotion_bump(title),
                    ],
                })
        finally:
            session.close()

        _clear_table_widgets(self.table)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        self.table.setFixedHeight(54 + (48 * max(1, len(rows))) + 2)
        for row_index, row in enumerate(rows):
            self.table.setRowHeight(row_index, 48)
            for col_index, value in enumerate(row["values"]):
                _set_tooltip_item(self.table, row_index, col_index, value)
            self._style_policy_row(row_index)
            for badge_col in (0, 4, 5, 7):
                item = self.table.item(row_index, badge_col)
                if item:
                    item.setText("")
            self.table.setCellWidget(row_index, 0, _pill_cell(row["values"][0], "#1d4ed8", "#dbeafe", align=Qt.AlignCenter, min_width=52))
            self.table.setCellWidget(row_index, 4, _pill_cell(row["values"][4], "#047857", "#dcfce7"))
            self.table.setCellWidget(row_index, 5, _pill_cell(row["values"][5], "#1d4ed8", "#dbeafe", align=Qt.AlignCenter))
            self.table.setCellWidget(row_index, 7, _pill_cell(row["values"][7], "#047857", "#dcfce7"))
            self.table.setCellWidget(row_index, 8, self._actions_cell(row))
        self._resize_level_columns()
        QTimer.singleShot(0, self._resize_level_columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self._resize_level_columns()

    def _resize_level_columns(self):
        if not hasattr(self, "table"):
            return
        available = max(860, self.table.viewport().width() - 2)
        action_width = 118
        remaining = max(720, available - action_width)
        weights = {
            0: 0.08,
            1: 0.20,
            2: 0.10,
            3: 0.18,
            4: 0.11,
            5: 0.10,
            6: 0.10,
            7: 0.13,
        }
        widths = {col: int(remaining * weight) for col, weight in weights.items()}
        widths[8] = action_width
        minimums = {0: 86, 1: 140, 2: 76, 3: 130, 4: 90, 5: 86, 6: 100, 7: 96, 8: 118}
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, max(minimums.get(col, 56), widths.get(col, 80)))

    def _style_policy_row(self, row_index):
        level_item = self.table.item(row_index, 0)
        if level_item:
            level_item.setBackground(QColor("#dbeafe"))
            level_item.setForeground(QColor("#1d4ed8"))

        for col in (4, 7):
            item = self.table.item(row_index, col)
            if item:
                item.setBackground(QColor("#ecfdf5"))
                item.setForeground(QColor("#047857"))

        salary_item = self.table.item(row_index, 3)
        if salary_item:
            salary_item.setForeground(QColor("#065f46"))

        for col in (2, 5, 6):
            item = self.table.item(row_index, col)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

    def _actions_cell(self, row):
        cell = prepare_table_cell_widget(QWidget())
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        edit = QPushButton()
        edit.setIcon(qta.icon("fa5s.edit", color="white"))
        edit.setIconSize(QSize(13, 13))
        edit.setFixedSize(36, 34)
        edit.setCursor(Qt.PointingHandCursor)
        edit.setStyleSheet(_primary_button_ss())
        edit.setToolTip(t("edit_level"))
        edit.clicked.connect(lambda _, title_id=row["id"]: self._edit_level(title_id))
        layout.addWidget(edit)

        delete = QPushButton()
        delete.setIcon(qta.icon("fa5s.trash-alt", color="#dc2626"))
        delete.setIconSize(QSize(13, 13))
        delete.setFixedSize(36, 34)
        delete.setCursor(Qt.PointingHandCursor)
        delete.setStyleSheet(_danger_icon_button_ss())
        delete.setToolTip(t("delete_level"))
        delete.setEnabled(not row["protected"])
        if row["protected"]:
            delete.setIcon(qta.icon("fa5s.trash-alt", color="#9ca3af"))
        delete.clicked.connect(lambda _, title_id=row["id"]: self._delete_level(title_id))
        layout.addWidget(delete)
        return cell

    def _add_level(self):
        dialog = AddLevelDialog(self.user, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
            if callable(self.on_saved):
                self.on_saved()

    def _edit_level(self, title_id):
        dialog = AddLevelDialog(self.user, title_id=title_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
            if callable(self.on_saved):
                self.on_saved()

    def _delete_level(self, title_id):
        session = get_session()
        try:
            title = session.query(Title).filter_by(id=title_id).first()
            if not title or title.name == "Other":
                _warning(self, t("warning"), t("level_delete_protected"))
                return
            employee_count = session.query(Employee).filter_by(title_id=title.id).count()
            incoming_rules = session.query(PromotionRule).filter_by(to_title_id=title.id).count()
            if employee_count:
                _warning(self, t("warning"), t("level_delete_has_employees"))
                return
            if incoming_rules:
                _warning(self, t("warning"), t("level_delete_has_rules"))
                return
            if _question(self, t("delete_level"), t("confirm_delete_level", level=title.name)) != QMessageBox.Yes:
                return
            before = (
                f'{{"name": "{title.name}", "label": "{title.label}", '
                f'"salary_min": {title.base_salary_min}, "salary_max": {title.base_salary_max}, '
                f'"currency": "{title.currency}"}}'
            )
            for rule in session.query(PromotionRule).filter_by(from_title_id=title.id).all():
                session.delete(rule)
            log_action(
                session,
                action="settings.level_delete",
                performed_by_id=self.user.id,
                target_table="title",
                target_id=title.id,
                description=f"Level deleted: {title.name} ({title.label})",
                before_value=before,
            )
            session.delete(title)
            session.commit()
            self.refresh()
            if callable(self.on_saved):
                self.on_saved()
            _information(self, t("success"), t("level_deleted_successfully"))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class AddLevelDialog(QDialog):
    def __init__(self, user, title_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.title_id = title_id
        self.is_edit = title_id is not None
        self.setWindowTitle(t("edit_level") if self.is_edit else t("add_level"))
        self.setFixedWidth(620)
        self.setStyleSheet("QDialog { background: white; color: #111827; } QLabel { background: transparent; color: #111827; }")
        self._build()
        if self.is_edit:
            self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(t("edit_level") if self.is_edit else t("add_level"))
        title.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {TEXT}; background: transparent;")
        layout.addWidget(title)

        note = QLabel(t("add_level_note"))
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 13px; color: {MUTED}; background: transparent;")
        layout.addWidget(note)

        self.level_name = _line_edit("Junior Specialist")
        self.level_label = _line_edit()
        self.degree = QComboBox()
        for value in ("any", "BSc", "MSc", "PhD"):
            self.degree.addItem(value, value)
        _style_combo(self.degree)

        self.currency = _line_edit(self._default_currency())
        self.salary_min = _money_spin()
        self.salary_max = _money_spin()
        self.increment_type = QComboBox()
        self.increment_type.addItem(t("increment_percentage"), "percentage")
        self.increment_type.addItem(t("increment_fixed"), "fixed")
        _style_combo(self.increment_type)
        self.increment_value = _increment_value_spin(3.0)
        self.increment_type.currentIndexChanged.connect(lambda *_: self._sync_increment_value_suffix())
        self.currency.textChanged.connect(lambda *_: self._sync_increment_value_suffix())
        self._sync_increment_value_suffix()
        self.target_title = QComboBox()
        if self.is_edit:
            self.target_title.addItem(t("no_promotion_target"), None)
        for title in _titles():
            if title.name != "Other" and title.id != self.title_id:
                self.target_title.addItem(title.name, title.id)
        _style_combo(self.target_title)
        self.track_months = _spin(1, 240, 36)
        self.target_bump = _percent_spin(20.0)
        self.target_title.currentIndexChanged.connect(self._load_target_defaults)
        self._load_target_defaults()

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.addRow(t("level") + " *", self.level_name)
        form.addRow(t("name") + " *", self.level_label)
        form.addRow(t("degree_requirement") + " *", self.degree)
        form.addRow(t("currency") + " *", self.currency)
        form.addRow(t("salary_min") + " *", self.salary_min)
        form.addRow(t("salary_max") + " *", self.salary_max)
        form.addRow(t("increment_type") + " *", self.increment_type)
        form.addRow(t("increment_value") + " *", self.increment_value)
        form.addRow(t("promotion_target") + (" *" if not self.is_edit else ""), self.target_title)
        form.addRow(t("base_track_duration_months") + " *", self.track_months)
        form.addRow(t("promotion_salary_increase"), self.target_bump)
        layout.addLayout(form)

        hint = QLabel(t("target_promotion_bump_note"))
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(_secondary_button_ss())
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setFixedHeight(38)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(_primary_button_ss())
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _default_currency(self):
        session = get_session()
        try:
            title = session.query(Title).first()
            return title.currency if title else "EUR"
        finally:
            session.close()

    def _load(self):
        session = get_session()
        try:
            title = session.query(Title).filter_by(id=self.title_id).first()
            if not title:
                return
            self.level_name.setText(title.name)
            self.level_name.setReadOnly(title.name == "Other")
            self.level_label.setText(title.label)
            degree_index = self.degree.findData(title.degree_requirement)
            if degree_index >= 0:
                self.degree.setCurrentIndex(degree_index)
            increment_index = self.increment_type.findData(title.annual_increment_type)
            if increment_index >= 0:
                self.increment_type.setCurrentIndex(increment_index)
            self.increment_value.setValue(title.annual_increment_value)
            self._sync_increment_value_suffix()
            rule = session.query(PromotionRule).filter_by(from_title_id=title.id).first()
            if rule:
                target_index = self.target_title.findData(rule.to_title_id)
                if target_index >= 0:
                    self.target_title.setCurrentIndex(target_index)
                self.track_months.setValue(rule.base_months)
                self.target_bump.setValue(rule.to_title.promotion_salary_increase_pct)
            else:
                none_index = self.target_title.findData(None)
                if none_index >= 0:
                    self.target_title.setCurrentIndex(none_index)
                self.target_bump.setValue(title.promotion_salary_increase_pct)
            self.currency.setText(title.currency or "EUR")
            self.salary_min.setValue(title.base_salary_min)
            self.salary_max.setValue(title.base_salary_max)
        finally:
            session.close()

    def _load_target_defaults(self):
        title_id = self.target_title.currentData()
        if not title_id:
            return
        session = get_session()
        try:
            title = session.query(Title).filter_by(id=title_id).first()
            if title:
                self.target_bump.setValue(title.promotion_salary_increase_pct)
                target_min = max(0, float(title.base_salary_min or 0))
                default_min = max(1, round(target_min * 0.75))
                default_max = max(default_min + 1, round(target_min - 1))
                self.salary_min.setValue(default_min)
                self.salary_max.setValue(default_max)
                self.currency.setText(title.currency or "EUR")
        finally:
            session.close()

    def _sync_increment_value_suffix(self):
        _sync_increment_spin_suffix(self.increment_type, self.increment_value, self.currency.text().strip() or "EUR")

    def _save(self):
        level = self.level_name.text().strip()
        label = self.level_label.text().strip()
        currency = self.currency.text().strip().upper() or "EUR"
        target_id = self.target_title.currentData()

        if not level or not label:
            _warning(self, t("warning"), t("level_name_label_required"))
            return
        if not _valid_currency_code(currency):
            _warning(self, t("warning"), t("currency_code_warning"))
            return
        if self.salary_max.value() <= 0 or self.salary_min.value() > self.salary_max.value():
            _warning(self, t("warning"), t("salary_min_max_warning"))
            return
        if not target_id and not self.is_edit:
            _warning(self, t("warning"), t("promotion_target_required"))
            return

        session = get_session()
        try:
            duplicate = session.query(Title).filter(func.lower(Title.name) == level.lower()).first()
            if duplicate and duplicate.id != self.title_id:
                _warning(self, t("warning"), t("level_already_exists"))
                return
            duplicate_label = session.query(Title).filter(func.lower(Title.label) == label.lower()).first()
            if duplicate_label and duplicate_label.id != self.title_id:
                _warning(self, t("warning"), t("level_label_already_exists"))
                return
            current_title = session.query(Title).filter_by(id=self.title_id).first() if self.is_edit else None
            editing_other = bool(current_title and current_title.name == "Other")
            if level.lower() == "other" and not editing_other:
                _warning(self, t("warning"), t("level_name_format_warning"))
                return
            target = session.query(Title).filter_by(id=target_id).first() if target_id else None
            if not target and not self.is_edit:
                _warning(self, t("warning"), t("promotion_target_required"))
                return
            if target:
                salary_key = _salary_transition_validation_key(
                    self.salary_min.value(),
                    self.salary_max.value(),
                    currency,
                    target,
                )
                if salary_key:
                    _warning(self, t("warning"), t(salary_key))
                    return
            proposed = {
                rule.from_title_id: rule.to_title_id
                for rule in session.query(PromotionRule).all()
            }
            proposed[self.title_id if self.is_edit else -1] = target_id
            validation_key = _promotion_mapping_validation_key(session, proposed)
            if validation_key:
                _warning(self, t("warning"), t(validation_key))
                return
            if self.is_edit:
                title = current_title
                if not title:
                    _warning(self, t("warning"), t("level_not_found"))
                    return
                before = (
                    f'{{"name": "{title.name}", "label": "{title.label}", '
                    f'"salary_min": {title.base_salary_min}, "salary_max": {title.base_salary_max}, '
                    f'"currency": "{title.currency}"}}'
                )
                if title.name != "Other":
                    title.name = level
                title.label = label
                title.degree_requirement = self.degree.currentData()
                title.base_salary_min = self.salary_min.value()
                title.base_salary_max = self.salary_max.value()
                title.currency = currency
                title.annual_increment_type = self.increment_type.currentData()
                title.annual_increment_value = self.increment_value.value()
                rule = session.query(PromotionRule).filter_by(from_title_id=title.id).first()
                if target:
                    if rule:
                        rule.to_title_id = target.id
                        rule.base_months = self.track_months.value()
                        rule.is_active = True
                    else:
                        session.add(PromotionRule(
                            from_title_id=title.id,
                            to_title_id=target.id,
                            base_months=self.track_months.value(),
                            is_active=True,
                        ))
                    target.promotion_salary_increase_pct = self.target_bump.value()
                elif rule:
                    session.delete(rule)
                action = "settings.level_update"
                description = f"Level updated: {level} ({label})"
                target_table_id = title.id
                message = t("level_updated_successfully")
            else:
                title = Title(
                    name=level,
                    label=label,
                    degree_requirement=self.degree.currentData(),
                    base_salary_min=self.salary_min.value(),
                    base_salary_max=self.salary_max.value(),
                    currency=currency,
                    annual_increment_type=self.increment_type.currentData(),
                    annual_increment_value=self.increment_value.value(),
                    promotion_salary_increase_pct=0.0,
                )
                session.add(title)
                session.flush()
                target.promotion_salary_increase_pct = self.target_bump.value()
                session.add(PromotionRule(
                    from_title_id=title.id,
                    to_title_id=target.id,
                    base_months=self.track_months.value(),
                    is_active=True,
                ))
                before = None
                action = "settings.level_create"
                description = (
                    f"Level created: {level} ({label}) -> {target.name}; "
                    f"salary {self.salary_min.value():.0f}-{self.salary_max.value():.0f} {currency}; "
                    f"track {self.track_months.value()} months"
                )
                target_table_id = title.id
                message = t("level_created_successfully")
            after = (
                f'{{"name": "{level}", "label": "{label}", '
                f'"salary_min": {self.salary_min.value()}, "salary_max": {self.salary_max.value()}, '
                f'"currency": "{currency}"}}'
            )
            log_action(
                session,
                action=action,
                performed_by_id=self.user.id,
                target_table="title",
                target_id=target_table_id,
                description=description,
                before_value=before,
                after_value=after,
            )
            session.commit()
            _information(self, t("success"), message)
            self.accept()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class SalaryTab(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved
        self.fields = {}
        self.currency_badges = []
        self._build()
        self._load()

    def _build(self):
        content, outer = _content()

        top, top_layout = _section_card(t("salary_range_config"), t("salary_range_config_subtitle"), "fa5s.coins", BLUE)
        currency_row = QHBoxLayout()
        currency_row.setSpacing(14)
        currency_row.addWidget(_label(t("currency_code")))
        self.currency_input = _line_edit("EUR")
        self.currency_input.setFixedWidth(130)
        self.currency_input.textChanged.connect(self._on_currency_changed)
        currency_row.addWidget(self.currency_input)
        note = QLabel(t("applies_to_all_levels"))
        note.setStyleSheet(f"font-size: 13px; color: {MUTED}; background: transparent;")
        currency_row.addWidget(note)
        currency_row.addStretch()
        top_layout.addLayout(currency_row)
        outer.addWidget(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        for index, title in enumerate(_titles()):
            card = self._salary_card(title)
            grid.addWidget(card, index // 2, index % 2)
        outer.addLayout(grid)

        save = _button(t("save_salary_ranges"), "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        outer.addWidget(save, alignment=Qt.AlignLeft)
        outer.addStretch()
        _set_page(self, content)

    def _salary_card(self, title):
        label_key, color, bg = LEVEL_META.get(title.name, (None, BLUE, "#dbeafe"))
        label = t(label_key) if label_key else title.label
        card = _plain_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(16)

        head = QHBoxLayout()
        icon = _badge_icon("fa5s.layer-group", color, bg)
        text = QLabel(f"{title.name} - {label}")
        text.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {TEXT}; background: transparent;")
        head.addWidget(icon)
        head.addWidget(text)
        head.addStretch()
        layout.addLayout(head)

        fields = QGridLayout()
        fields.setHorizontalSpacing(16)
        fields.setVerticalSpacing(8)
        min_spin = _money_spin()
        max_spin = _money_spin()
        currency_badge = QLabel("EUR")
        currency_badge.setFixedSize(58, 44)
        currency_badge.setAlignment(Qt.AlignCenter)
        currency_badge.setStyleSheet(f"background: {bg}; color: {color}; border-radius: 8px; font-size: 13px; font-weight: 800;")
        self.currency_badges.append(currency_badge)

        fields.addWidget(_label(t("salary_min")), 0, 0)
        fields.addWidget(_label(t("currency")), 0, 1)
        fields.addWidget(_label(t("salary_max")), 0, 2)
        fields.addWidget(min_spin, 1, 0)
        fields.addWidget(currency_badge, 1, 1)
        fields.addWidget(max_spin, 1, 2)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(2, 1)
        layout.addLayout(fields)
        self.fields[title.id] = (min_spin, max_spin)
        return card

    def _on_currency_changed(self, value):
        clean = value.upper()[:8]
        if clean != value:
            self.currency_input.blockSignals(True)
            self.currency_input.setText(clean)
            self.currency_input.setCursorPosition(len(clean))
            self.currency_input.blockSignals(False)
        self._update_currency_badges(clean)

    def _update_currency_badges(self, value=None):
        code = (value or self.currency_input.text() or "EUR").strip()
        for badge in self.currency_badges:
            badge.setText(code)

    def _load(self):
        session = get_session()
        try:
            for title in session.query(Title).all():
                if title.id in self.fields:
                    min_spin, max_spin = self.fields[title.id]
                    min_spin.setValue(title.base_salary_min)
                    max_spin.setValue(title.base_salary_max)
                    self.currency_input.setText(title.currency or "EUR")
        finally:
            session.close()
        self._update_currency_badges()

    def _save(self):
        session = get_session()
        try:
            currency = (self.currency_input.text().strip() or "EUR").upper()
            if not _valid_currency_code(currency):
                _warning(self, t("warning"), t("currency_code_warning"))
                return
            for title_id, (min_spin, max_spin) in self.fields.items():
                title = session.query(Title).filter_by(id=title_id).first()
                if title:
                    if min_spin.value() > max_spin.value():
                        _warning(self, t("warning"), t("salary_min_max_warning"))
                        return
                    title.base_salary_min = min_spin.value()
                    title.base_salary_max = max_spin.value()
                    title.currency = currency
            validation_key = _salary_policy_validation_key(
                {title.id: title for title in session.query(Title).all()},
                session.query(PromotionRule).all(),
            )
            if validation_key:
                _warning(self, t("warning"), t(validation_key))
                return
            log_action(session, action="settings.salary_ranges", performed_by_id=self.user.id, description="Salary ranges updated")
            session.commit()
            _information(self, t("success"), t("salary_ranges_saved"))
            if callable(self.on_saved):
                self.on_saved()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class SettingsPromotionTab(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved
        self.fields = {}
        self._build()
        self._load()

    def _build(self):
        content, outer = _content()

        card, layout = _section_card(t("promotion_track_config"), t("promotion_track_config_subtitle"), "fa5s.chart-line", BLUE)
        layout.addWidget(_promotion_guide())
        self.rules_list = QVBoxLayout()
        self.rules_list.setSpacing(18)
        layout.addLayout(self.rules_list)
        layout.addWidget(_note_card(
            t("track_modifiers"),
            [
                t("track_modifier_commendations"),
                t("track_modifier_sanctions"),
                t("track_modifier_reset"),
            ],
            "fa5s.clock",
            "#92400e",
            NOTE_YELLOW_SS,
        ))
        save = _button(t("save_promotion_settings"), "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        layout.addWidget(save, alignment=Qt.AlignRight)
        outer.addWidget(card)
        outer.addStretch()
        _set_page(self, content)

    def _load(self):
        _clear_layout(self.rules_list)
        self.fields = {}

        session = get_session()
        try:
            titles = _ordered_titles(session)
            target_titles = [title for title in titles if title.name != "Other"]
            rules_by_from = {
                rule.from_title_id: rule
                for rule in session.query(PromotionRule).all()
            }
            rows = []
            for title in target_titles:
                rule = rules_by_from.get(title.id)
                rows.append({
                    "id": rule.id if rule else None,
                    "from_id": title.id,
                    "from": title.name,
                    "from_label": title.label,
                    "to_id": rule.to_title_id if rule else None,
                    "to": rule.to_title.name if rule else t("no_promotion_target"),
                    "base_months": rule.base_months if rule else 36,
                    "salary_increase": rule.to_title.promotion_salary_increase_pct if rule else 0.0,
                    "target_titles": target_titles,
                })
        finally:
            session.close()

        for row in rows:
            self.rules_list.addWidget(self._rule_card(row))

    def _rule_card(self, row):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }"
            "QLabel { background: transparent; border: none; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.chart-line", color=BLUE).pixmap(17, 17))
        title = QLabel(t("level_to_level", from_level=row["from"], to_level=row["to"]))
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {TEXT}; background: transparent;")
        subtitle = QLabel(row["from_label"])
        subtitle.setStyleSheet(f"font-size: 12px; color: {MUTED}; background: transparent;")
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(title)
        text.addWidget(subtitle)
        title_row.addWidget(icon)
        title_row.addLayout(text)
        title_row.addStretch()
        layout.addLayout(title_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        target_combo = QComboBox()
        target_combo.addItem(t("no_promotion_target"), None)
        for target in row["target_titles"]:
            if target.id != row["from_id"]:
                target_combo.addItem(_level_option_label(target), target.id)
        target_index = target_combo.findData(row["to_id"])
        if target_index >= 0:
            target_combo.setCurrentIndex(target_index)
        _style_combo(target_combo)
        target_combo.setMinimumWidth(360)
        months = _spin(1, 120, row["base_months"])
        salary = _percent_spin(row["salary_increase"])
        months.setMinimumWidth(180)
        salary.setMinimumWidth(180)
        def update_enabled():
            enabled = target_combo.currentData() is not None
            months.setEnabled(enabled)
            salary.setEnabled(enabled)
        target_combo.currentIndexChanged.connect(lambda *_: update_enabled())
        update_enabled()

        grid.addWidget(_label(t("promotion_target")), 0, 0)
        grid.addWidget(_label(t("base_track_duration")), 0, 1)
        grid.addWidget(_label(t("base_salary_increase")), 0, 2)
        grid.addWidget(target_combo, 1, 0)
        grid.addWidget(months, 1, 1)
        grid.addWidget(salary, 1, 2)
        grid.addWidget(_hint(t("promotion_rule_no_target_hint")), 2, 0)
        grid.addWidget(_hint(t("starting_point_for_race")), 2, 1)
        grid.addWidget(_hint(t("upon_promotion_to_next")), 2, 2)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)

        self.fields[row["from_id"]] = {
            "rule_id": row["id"],
            "target": target_combo,
            "months": months,
            "salary": salary,
        }
        return card

    def _save(self):
        session = get_session()
        try:
            titles = {title.id: title for title in session.query(Title).all()}
            proposed = {}
            for from_title_id, controls in self.fields.items():
                target_id = controls["target"].currentData()
                proposed[from_title_id] = target_id

            validation_key = _promotion_mapping_validation_key(session, proposed)
            if validation_key:
                _warning(self, t("warning"), t(validation_key))
                return
            salary_key = _promotion_rules_salary_validation_key(titles, proposed)
            if salary_key:
                _warning(self, t("warning"), t(salary_key))
                return

            for from_title_id, controls in self.fields.items():
                target_id = proposed[from_title_id]
                rule_id = controls["rule_id"]
                rule = session.query(PromotionRule).filter_by(id=rule_id).first() if rule_id else None
                if target_id is None:
                    if rule:
                        session.delete(rule)
                    continue
                if rule:
                    rule.to_title_id = target_id
                    rule.base_months = controls["months"].value()
                    rule.is_active = True
                else:
                    rule = PromotionRule(
                        from_title_id=from_title_id,
                        to_title_id=target_id,
                        base_months=controls["months"].value(),
                        is_active=True,
                    )
                    session.add(rule)
                titles[target_id].promotion_salary_increase_pct = controls["salary"].value()
            log_action(session, action="settings.promotion_rules", performed_by_id=self.user.id, description="Promotion settings updated")
            session.commit()
            _information(self, t("success"), t("promotion_settings_saved"))
            self._load()
            if callable(self.on_saved):
                self.on_saved()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class IncrementTab(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved
        self.fields = {}
        self._build()
        self._load()

    def _build(self):
        content, outer = _content()
        outer.addWidget(_note_card(
            t("annual_increment_rules"),
            [t("increment_note")],
            "fa5s.calendar-check",
            "#92400e",
            NOTE_YELLOW_SS,
        ))

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        for index, title in enumerate(_titles()):
            grid.addWidget(self._increment_card(title), index // 2, index % 2)
        outer.addLayout(grid)

        save = _button(t("save_increment_rules"), "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        outer.addWidget(save, alignment=Qt.AlignLeft)
        outer.addStretch()
        _set_page(self, content)

    def _increment_card(self, title):
        label_key, color, bg = LEVEL_META.get(title.name, (None, BLUE, "#dbeafe"))
        label = t(label_key) if label_key else title.label
        card = _plain_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(16)

        head = QHBoxLayout()
        head.addWidget(_badge_icon("fa5s.percentage", color, bg))
        title_lbl = QLabel(f"{title.name} - {label}")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {TEXT}; background: transparent;")
        head.addWidget(title_lbl)
        head.addStretch()
        layout.addLayout(head)

        fields = QGridLayout()
        fields.setHorizontalSpacing(16)
        type_combo = QComboBox()
        type_combo.addItem(t("increment_percentage"), "percentage")
        type_combo.addItem(t("increment_fixed"), "fixed")
        _style_combo(type_combo)
        value_spin = _increment_value_spin(3.0)
        type_combo.currentIndexChanged.connect(
            lambda *_args, combo=type_combo, spin=value_spin, currency=title.currency or "EUR":
            _sync_increment_spin_suffix(combo, spin, currency)
        )
        _sync_increment_spin_suffix(type_combo, value_spin, title.currency or "EUR")
        fields.addWidget(_label(t("increment_type")), 0, 0)
        fields.addWidget(_label(t("increment_value")), 0, 1)
        fields.addWidget(type_combo, 1, 0)
        fields.addWidget(value_spin, 1, 1)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        layout.addLayout(fields)
        self.fields[title.id] = (type_combo, value_spin)
        return card

    def _load(self):
        session = get_session()
        try:
            for title_id, (combo, spin) in self.fields.items():
                title = session.query(Title).filter_by(id=title_id).first()
                if title:
                    index = combo.findData(title.annual_increment_type)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                    spin.setValue(title.annual_increment_value)
                    _sync_increment_spin_suffix(combo, spin, title.currency or "EUR")
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            for title_id, (combo, spin) in self.fields.items():
                title = session.query(Title).filter_by(id=title_id).first()
                if title:
                    title.annual_increment_type = combo.currentData()
                    title.annual_increment_value = spin.value()
            log_action(session, action="settings.increment_rules", performed_by_id=self.user.id, description="Annual increment rules updated")
            session.commit()
            _information(self, t("success"), t("increment_rules_saved"))
            if callable(self.on_saved):
                self.on_saved()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class UserManagementTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()
        self.refresh()

    def _build(self):
        content, outer = _content()

        header, header_layout = _section_card(
            t("user_management"),
            t("user_management_subtitle"),
            "fa5s.users-cog",
            BLUE,
        )
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        if self.user.role == "admin":
            add = _button(t("add_hr_account"), "fa5s.user-plus", primary=True)
            add.clicked.connect(self._add_hr)
            top_row.addWidget(add, alignment=Qt.AlignLeft)
        top_row.addStretch()
        header_layout.addLayout(top_row)
        header_layout.addWidget(_note_card(
            t("user_management_rules") if self.user.role == "admin" else t("security_information"),
            [
                t("user_rule_admin_single") if self.user.role == "admin" else t("security_note_audit_retained"),
                t("user_rule_hr_soft_delete") if self.user.role == "admin" else t("security_note_identity"),
                t("user_rule_audit_snapshot") if self.user.role == "admin" else t("security_note_hashes"),
            ],
            "fa5s.shield-alt",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        outer.addWidget(header)

        outer.addWidget(self._password_card())

        if self.user.role != "admin":
            outer.addStretch()
            _set_page(self, content)
            return

        card = _plain_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("username"), t("full_name"), t("role"), t("status"), t("last_login"), t("actions")
        ])
        self.table.setStyleSheet(
            """
QTableWidget {
    background: white;
    alternate-background-color: #fcfcfd;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 14px;
    color: #111827;
    outline: none;
}
QTableWidget::item {
    background: white;
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
}
QTableWidget::item:hover { background: #f9fafb; }
QTableWidget::item:selected { background: #eff6ff; color: #111827; }
QHeaderView::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 800;
    color: #030213;
    min-height: 50px;
    text-align: left;
}
QToolTip {
    background-color: #111827;
    color: white;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 6px 8px;
}
"""
        )
        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for col, width in {0: 180, 1: 240, 2: 160, 3: 130, 4: 180, 5: 190}.items():
            self.table.setColumnWidth(col, width)
        for col in (0, 1):
            header_view.setSectionResizeMode(col, QHeaderView.Stretch)
        for col in (2, 3, 4, 5):
            header_view.setSectionResizeMode(col, QHeaderView.Fixed)
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)
        outer.addWidget(card)
        outer.addStretch()
        _set_page(self, content)

    def _password_card(self):
        card, layout = _section_card(t("change_password"), t("change_password_subtitle"), "fa5s.lock", BLUE)
        row = QHBoxLayout()
        row.setSpacing(22)
        form = QGridLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        self.current_pwd = _line_edit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd = _line_edit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd = _line_edit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        _add_form_field(form, 0, 0, t("current_password"), self.current_pwd)
        _add_form_field(form, 0, 1, t("new_password"), self.new_pwd)
        _add_form_field(form, 0, 2, t("confirm_new_password"), self.confirm_pwd)
        row.addLayout(form, 1)
        change = _button(t("change_password"), "fa5s.key", primary=True)
        change.setFixedWidth(190)
        change.clicked.connect(self._change_password)
        row.addWidget(change, alignment=Qt.AlignBottom)
        layout.addLayout(row)
        return card

    def refresh(self):
        session = get_session()
        try:
            users = (
                session.query(SystemUser)
                .filter(
                    (SystemUser.role == "admin") |
                    ((SystemUser.role == "hr_officer") & (SystemUser.is_active == True))
                )
                .order_by(SystemUser.role, SystemUser.username)
                .all()
            )
            rows = [{
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": bool(user.is_active),
                "last_login": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "-",
            } for user in users]
        finally:
            session.close()

        _clear_table_widgets(self.table)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (62 * max(1, len(rows))))
        for row_index, row in enumerate(rows):
            self.table.setRowHeight(row_index, 58)
            _set_tooltip_item(self.table, row_index, 0, row["username"])
            _set_tooltip_item(self.table, row_index, 1, row["full_name"])
            _set_tooltip_item(self.table, row_index, 2, row["username"] if row["role"] == "admin" else t("role_hr"))
            _set_tooltip_item(self.table, row_index, 3, t("active") if row["is_active"] else t("inactive"))
            _set_tooltip_item(self.table, row_index, 4, row["last_login"])
            self.table.setCellWidget(row_index, 5, self._actions_cell(row))

    def _actions_cell(self, row):
        cell = prepare_table_cell_widget(QWidget())
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(10, 8, 18, 8)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        edit = QPushButton("  " + t("edit"))
        edit.setIcon(qta.icon("fa5s.edit", color="white"))
        edit.setIconSize(QSize(13, 13))
        edit.setFixedSize(96, 38)
        edit.setCursor(Qt.PointingHandCursor)
        edit.setStyleSheet(_primary_button_ss())
        edit.setToolTip(t("edit_user_account"))
        edit.clicked.connect(lambda _, uid=row["id"]: self._edit_user(uid))
        layout.addWidget(edit)

        if row["role"] == "hr_officer":
            layout.addSpacing(14)
            delete = QPushButton()
            delete.setIcon(qta.icon("fa5s.trash-alt", color="#dc2626"))
            delete.setIconSize(QSize(13, 13))
            delete.setFixedSize(38, 38)
            delete.setCursor(Qt.PointingHandCursor)
            delete.setStyleSheet(_danger_icon_button_ss())
            delete.setToolTip(t("delete_hr_login"))
            delete.clicked.connect(lambda _, uid=row["id"]: self._delete_hr_login(uid))
            layout.addWidget(delete)
        return cell

    def _change_password(self):
        current = self.current_pwd.text()
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if not current or not new or not confirm:
            _warning(self, t("warning"), t("all_fields_required"))
            return
        if new != confirm:
            _warning(self, t("warning"), t("new_passwords_do_not_match"))
            return
        if len(new) < 6:
            _warning(self, t("warning"), t("password_min_length"))
            return

        session = get_session()
        try:
            user = session.query(SystemUser).filter_by(id=self.user.id).first()
            if not user or user.password_hash != sha256(current.encode()).hexdigest():
                _critical(self, t("error"), t("current_password_incorrect"))
                return
            user.password_hash = sha256(new.encode()).hexdigest()
            log_action(session, action="settings.password_change", performed_by_id=self.user.id, description=f"Password changed for user: {self.user.username}")
            session.commit()
            self.current_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
            _information(self, t("success"), t("password_changed_successfully"))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()

    def _add_hr(self):
        dialog = UserAccountDialog(self.user, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_user(self, user_id):
        session = get_session()
        try:
            account = session.query(SystemUser).filter_by(id=user_id).first()
            if not account or (account.role == "hr_officer" and not account.is_active):
                _warning(self, t("warning"), t("hr_account_not_found"))
                return
        finally:
            session.close()
        dialog = UserAccountDialog(self.user, user_id=user_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _set_active(self, user_id, make_active):
        title = t("reactivate_user_account") if make_active else t("deactivate_user_account")
        body = t("confirm_reactivate_user") if make_active else t("confirm_deactivate_user")
        if _question(self, title, body) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            account = session.query(SystemUser).filter_by(id=user_id, role="hr_officer").first()
            if not account:
                _warning(self, t("warning"), t("hr_account_not_found"))
                return
            account.is_active = make_active
            log_action(
                session,
                action="settings.user_reactivate" if make_active else "settings.user_deactivate",
                performed_by_id=self.user.id,
                target_table="system_user",
                target_id=account.id,
                description=(
                    f"User account {'reactivated' if make_active else 'deactivated'}: "
                    f"{account.username} ({account.full_name})"
                ),
            )
            session.commit()
            self.refresh()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()

    def _delete_hr_login(self, user_id):
        if _question(self, t("delete_hr_login"), t("confirm_delete_hr_login")) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            account = session.query(SystemUser).filter_by(id=user_id, role="hr_officer").first()
            if not account:
                _warning(self, t("warning"), t("hr_account_not_found"))
                return
            before = f'{{"username": "{account.username}", "full_name": "{account.full_name}", "role": "{account.role}", "is_active": {str(bool(account.is_active)).lower()}}}'
            account.is_active = False
            after = f'{{"username": "{account.username}", "full_name": "{account.full_name}", "role": "{account.role}", "is_active": false}}'
            log_action(
                session,
                action="settings.user_delete",
                performed_by_id=self.user.id,
                target_table="system_user",
                target_id=account.id,
                description=f"HR login deleted: {account.username} ({account.full_name})",
                before_value=before,
                after_value=after,
            )
            session.commit()
            self.refresh()
            _information(self, t("success"), t("hr_login_deleted"))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class UserAccountDialog(QDialog):
    def __init__(self, actor, user_id=None, parent=None):
        super().__init__(parent)
        self.actor = actor
        self.user_id = user_id
        self.account_role = "hr_officer"
        self.setWindowTitle(t("edit_user_account") if user_id else t("add_hr_account"))
        self.setFixedWidth(520)
        self.setStyleSheet("QDialog { background: white; color: #111827; } QLabel { background: transparent; color: #111827; }")
        self._build()
        if user_id:
            self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(t("edit_user_account") if self.user_id else t("add_hr_account"))
        title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {TEXT}; background: transparent;")
        layout.addWidget(title)

        self.role_label = QLabel(t("role_hr"))
        self.role_label.setStyleSheet("font-size: 13px; color: #2563eb; font-weight: 700; background: transparent;")
        layout.addWidget(self.role_label)

        self.username = _line_edit()
        self.full_name = _line_edit()
        self.password = _line_edit()
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm = _line_edit()
        self.confirm.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.addRow(t("username") + " *", self.username)
        form.addRow(t("full_name") + " *", self.full_name)
        form.addRow(t("new_password") + (" *" if not self.user_id else ""), self.password)
        form.addRow(t("confirm_new_password") + (" *" if not self.user_id else ""), self.confirm)
        layout.addLayout(form)

        note = QLabel(t("password_optional_edit") if self.user_id else t("password_required_new_user"))
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(_secondary_button_ss())
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setFixedHeight(38)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(_primary_button_ss())
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _load(self):
        session = get_session()
        try:
            account = session.query(SystemUser).filter_by(id=self.user_id).first()
            if not account:
                return
            self.account_role = account.role
            self.username.setText(account.username)
            self.full_name.setText(account.full_name)
            self.role_label.setText(t("role_admin") if account.role == "admin" else t("role_hr"))
        finally:
            session.close()

    def _save(self):
        username = self.username.text().strip()
        full_name = self.full_name.text().strip()
        password = self.password.text()
        confirm = self.confirm.text()

        if not username or not full_name:
            _warning(self, t("warning"), t("username_full_name_required"))
            return
        if not self.user_id and not password:
            _warning(self, t("warning"), t("password_required_new_user"))
            return
        if password or confirm:
            if password != confirm:
                _warning(self, t("warning"), t("new_passwords_do_not_match"))
                return
            if len(password) < 6:
                _warning(self, t("warning"), t("password_min_length"))
                return

        session = get_session()
        try:
            duplicate = session.query(SystemUser).filter(SystemUser.username == username).first()
            if duplicate and duplicate.id != self.user_id:
                _warning(self, t("warning"), t("username_already_exists"))
                return

            if self.user_id:
                account = session.query(SystemUser).filter_by(id=self.user_id).first()
                if not account:
                    _warning(self, t("warning"), t("user_account_not_found"))
                    return
                before = f'{{"username": "{account.username}", "full_name": "{account.full_name}", "role": "{account.role}"}}'
                account.username = username
                account.full_name = full_name
                if password:
                    account.password_hash = sha256(password.encode()).hexdigest()
                action = "settings.user_update"
                description = f"User account updated: {username} ({full_name})"
                target_id = account.id
                if account.id == self.actor.id:
                    self.actor.username = username
                    self.actor.full_name = full_name
            else:
                account = SystemUser(
                    username=username,
                    full_name=full_name,
                    role="hr_officer",
                    password_hash=sha256(password.encode()).hexdigest(),
                    is_active=True,
                )
                session.add(account)
                session.flush()
                before = None
                action = "settings.user_create"
                description = f"HR account created: {username} ({full_name})"
                target_id = account.id

            after = f'{{"username": "{account.username}", "full_name": "{account.full_name}", "role": "{account.role}", "is_active": {str(bool(account.is_active)).lower()}}}'
            log_action(
                session,
                action=action,
                performed_by_id=self.actor.id,
                target_table="system_user",
                target_id=target_id,
                description=description,
                before_value=before,
                after_value=after,
            )
            session.commit()
            self.accept()
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class DatabaseTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()

    def _build(self):
        content, outer = _content()
        row = QHBoxLayout()
        row.setSpacing(30)
        row.setAlignment(Qt.AlignTop)

        left = QVBoxLayout()
        left.setSpacing(20)
        left.setAlignment(Qt.AlignTop)

        backup, backup_layout = _section_card(t("db_backup"), t("db_backup_subtitle"), "fa5s.database", BLUE)
        backup_info = QLabel(t("db_backup_description"))
        backup_info.setWordWrap(True)
        backup_info.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        backup_layout.addWidget(backup_info)
        backup_btn = _button(t("create_backup"), "fa5s.save", primary=True)
        backup_btn.clicked.connect(self._backup)
        backup_layout.addWidget(backup_btn, alignment=Qt.AlignLeft)
        left.addWidget(backup)

        export, export_layout = _section_card(t("export_all"), t("export_all_subtitle"), "fa5s.file-export", BLUE)
        export_info = QLabel(t("export_all_description"))
        export_info.setWordWrap(True)
        export_info.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        export_layout.addWidget(export_info)
        export_btn = _button(t("export_employees_csv"), "fa5s.download", primary=True)
        export_btn.clicked.connect(self._export)
        export_layout.addWidget(export_btn, alignment=Qt.AlignLeft)
        left.addWidget(export)

        report, report_layout = _section_card(t("yearly_reports"), t("yearly_reports_subtitle"), "fa5s.file-pdf", "#dc2626")
        report_info = QLabel(t("yearly_reports_description"))
        report_info.setWordWrap(True)
        report_info.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        report_layout.addWidget(report_info)

        filter_box = QFrame()
        filter_box.setObjectName("ReportFilterBox")
        filter_box.setStyleSheet(
            "QFrame#ReportFilterBox { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }"
            "QFrame#ReportFilterBox QLabel { background: transparent; border: none; color: #374151; "
            "font-size: 12px; font-weight: 800; }"
        )
        filter_layout = QGridLayout(filter_box)
        filter_layout.setContentsMargins(14, 12, 14, 12)
        filter_layout.setHorizontalSpacing(12)
        filter_layout.setVerticalSpacing(8)

        hint = QLabel(t("report_filters_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {MUTED}; background: transparent;")
        filter_layout.addWidget(hint, 0, 0, 1, 3)

        self.report_type = QComboBox()
        self.report_type.setFixedHeight(40)
        _style_combo(self.report_type)
        self.report_type.addItem(t("report_type_full"), "full")
        self.report_type.addItem(t("report_type_executive"), "executive")
        self.report_type.addItem(t("report_type_audit"), "audit")
        filter_layout.addWidget(_field_label(t("report_type")), 1, 0)
        filter_layout.addWidget(self.report_type, 2, 0)

        self.report_year = QComboBox()
        self.report_year.setFixedHeight(40)
        _style_combo(self.report_year)
        for year in available_report_years():
            self.report_year.addItem(str(year), year)
        filter_layout.addWidget(_field_label(t("report_period_label")), 1, 1)
        filter_layout.addWidget(self.report_year, 2, 1)

        self.report_status = QComboBox()
        self.report_status.setFixedHeight(40)
        _style_combo(self.report_status)
        self.report_status.addItem(t("all_statuses"), None)
        for status in ["active", "inactive", "on_leave", "terminated"]:
            self.report_status.addItem(t(status), status)
        filter_layout.addWidget(_field_label(t("status")), 1, 2)
        filter_layout.addWidget(self.report_status, 2, 2)

        self.report_department = QComboBox()
        self.report_department.setFixedHeight(40)
        _style_combo(self.report_department)
        self.report_level = QComboBox()
        self.report_level.setFixedHeight(40)
        _style_combo(self.report_level)
        self._load_report_filter_options()
        filter_layout.addWidget(_field_label(t("department")), 3, 0)
        filter_layout.addWidget(self.report_department, 4, 0, 1, 2)
        filter_layout.addWidget(_field_label(t("level")), 3, 2)
        filter_layout.addWidget(self.report_level, 4, 2)

        report_layout.addWidget(filter_box)

        report_controls = QHBoxLayout()
        report_controls.setSpacing(12)
        report_btn = _button(t("export_yearly_pdf"), "fa5s.file-pdf", primary=True)
        report_btn.clicked.connect(self._export_yearly_report)
        report_controls.addWidget(report_btn)
        report_controls.addStretch()
        report_layout.addLayout(report_controls)

        history_title = QLabel(t("report_history"))
        history_title.setStyleSheet(f"font-size: 14px; font-weight: 900; color: {TEXT}; background: transparent;")
        report_layout.addWidget(history_title)
        self.report_history_table = QTableWidget()
        self.report_history_table.setColumnCount(4)
        self.report_history_table.setHorizontalHeaderLabels([
            f"{t('generated')} / {t('user')}", t("report"), t("scope"), t("path")
        ])
        self.report_history_table.setStyleSheet(_summary_table_ss())
        self.report_history_table.verticalHeader().setVisible(False)
        self.report_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.report_history_table)
        self.report_history_table.setShowGrid(False)
        self.report_history_table.setWordWrap(True)
        self.report_history_table.setMouseTracking(True)
        self.report_history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.report_history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.report_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.report_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.report_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.report_history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.report_history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.report_history_table.setColumnWidth(0, 220)
        self.report_history_table.setColumnWidth(1, 120)
        self.report_history_table.setColumnWidth(3, 180)
        report_layout.addWidget(self.report_history_table)
        self._refresh_report_history()
        left.addWidget(report)
        row.addLayout(left, 3)

        right, right_layout = _section_card(t("reporting_controls"), None, "fa5s.shield-alt", BLACK)
        right_layout.addWidget(_note_card(
            t("reporting_controls_title"),
            [
                t("db_note_manual_backups"),
                t("db_note_pdf_reports"),
                t("db_note_audit_exports"),
                t("db_note_health_check"),
            ],
            "fa5s.check-circle",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        health = _button(t("run_health_check"), "fa5s.heartbeat", primary=False)
        health.clicked.connect(self._health_check)
        right_layout.addWidget(health, alignment=Qt.AlignLeft)
        right_layout.addStretch()
        row.addWidget(right, 1)

        outer.addLayout(row)
        outer.addStretch()
        _set_page(self, content)

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(self, t("save_backup"), "myhr_backup.db", t("sqlite_database_filter"))
        if not path:
            return
        try:
            shutil.copy2(DB_PATH, path)
            _information(self, t("success"), t("backup_saved_to", path=path))
        except Exception as exc:
            _critical(self, t("error"), str(exc))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, t("export_employees"), "employees_export.csv", t("csv_files_filter"))
        if not path:
            return
        session = get_session()
        try:
            employees = session.query(Employee).all()
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "employee_id", "first_name", "last_name", "degree", "position",
                    "level", "department", "base_salary", "status", "join_date",
                    "work_email", "phone"
                ])
                for employee in employees:
                    writer.writerow([
                        employee.employee_id,
                        employee.first_name,
                        employee.last_name,
                        employee.degree,
                        employee.position,
                        employee.title.name if employee.title else "",
                        employee.org_unit.name if employee.org_unit else "",
                        employee.base_salary,
                        employee.status,
                        str(employee.join_date.date()) if employee.join_date else "",
                        employee.work_email or "",
                        employee.phone or "",
                    ])
            log_action(session, action="settings.export_employees", performed_by_id=self.user.id, description=f"Employee data exported to CSV: {len(employees)} records")
            session.commit()
            _information(self, t("success"), t("employees_exported_to", count=len(employees), path=path))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()

    def _load_report_filter_options(self):
        self.report_department.clear()
        self.report_department.addItem(t("all_departments"), None)
        self.report_level.clear()
        self.report_level.addItem(t("all_levels"), None)
        session = get_session()
        try:
            org_units = session.query(OrgUnit).order_by(OrgUnit.unit_type, OrgUnit.name).all()
            for unit in org_units:
                self.report_department.addItem(f"{unit.name} ({unit.unit_type})", unit.id)
            titles = session.query(Title).order_by(Title.id).all()
            for title in titles:
                self.report_level.addItem(f"{title.name} - {title.label}", title.id)
        finally:
            session.close()

    def _report_filters(self):
        return ReportFilters(
            report_type=self.report_type.currentData() or "full",
            org_unit_id=self.report_department.currentData(),
            title_id=self.report_level.currentData(),
            status=self.report_status.currentData(),
        )

    def _export_yearly_report(self):
        year = self.report_year.currentData()
        if not year:
            year = datetime.utcnow().year
        filters = self._report_filters()
        try:
            report = build_yearly_report(int(year), filters)
        except Exception as exc:
            _critical(self, t("error"), str(exc))
            return
        if not self._confirm_yearly_report_export(report):
            return
        type_suffix = (filters.report_type or "full").replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_yearly_report"),
            f"{company_name('MyHR').replace(' ', '_')}_{year}_{type_suffix}_Report.pdf",
            t("pdf_files_filter"),
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        session = get_session()
        try:
            html = build_yearly_report_html(report)
            _write_pdf(path, html)
            log_action(
                session,
                action="settings.export_yearly_report",
                performed_by_id=self.user.id,
                description=f"Yearly workforce report exported to PDF: {year}",
                after_value=json.dumps(
                    {
                        "year": int(year),
                        "path": path,
                        "report_type": filters.report_type,
                        "org_unit_id": filters.org_unit_id,
                        "title_id": filters.title_id,
                        "status": filters.status or "all",
                    },
                    ensure_ascii=False,
                ),
            )
            session.commit()
            self._refresh_report_history()
            _information(self, t("success"), t("yearly_report_exported_to", path=path))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()

    def _confirm_yearly_report_export(self, report):
        return YearlyReportPreviewDialog(report, self).exec() == QDialog.Accepted

    def _refresh_report_history(self):
        if not hasattr(self, "report_history_table"):
            return
        session = get_session()
        try:
            logs = (
                session.query(AuditLog)
                .filter(AuditLog.action == "settings.export_yearly_report")
                .order_by(AuditLog.performed_at.desc(), AuditLog.id.desc())
                .limit(5)
                .all()
            )
            rows = [_report_history_row(log, session) for log in logs]
        finally:
            session.close()

        _clear_table_widgets(self.report_history_table)
        self.report_history_table.clearContents()
        self.report_history_table.clearSpans()
        self.report_history_table.setRowCount(max(1, len(rows)))
        row_height = 64
        self.report_history_table.setFixedHeight(48 + (row_height * max(1, len(rows))) + 2)
        if not rows:
            self.report_history_table.setSpan(0, 0, 1, self.report_history_table.columnCount())
            _set_tooltip_item(self.report_history_table, 0, 0, t("report_history_empty"))
            self.report_history_table.setRowHeight(0, row_height)
            return
        for row_index, row in enumerate(rows):
            self.report_history_table.setRowHeight(row_index, row_height)
            for col_index, value in enumerate(row["values"]):
                _set_tooltip_item(self.report_history_table, row_index, col_index, value)
                item = self.report_history_table.item(row_index, col_index)
                if item:
                    item.setToolTip(row["tooltips"][col_index])

    def _health_check(self):
        session = get_session()
        try:
            with sqlite3.connect(DB_PATH) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            employee_count = session.query(Employee).count()
            user_count = session.query(SystemUser).count()
            title_count = session.query(Title).count()
            log_action(
                session,
                action="settings.database_health_check",
                performed_by_id=self.user.id,
                description=f"Database health check executed: {integrity}",
                after_value=(
                    f'{{"integrity": "{integrity}", "employees": {employee_count}, '
                    f'"users": {user_count}, "levels": {title_count}}}'
                ),
            )
            session.commit()
            if integrity.lower() == "ok":
                _information(
                    self,
                    t("success"),
                    t("database_health_ok", employees=employee_count, users=user_count, levels=title_count),
                )
            else:
                _warning(self, t("warning"), t("database_health_warning", result=integrity))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class YearlyReportPreviewDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.report = report
        self.setWindowTitle(t("report_preview_title"))
        self.setMinimumWidth(620)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(
            "QDialog { background: white; color: #111827; font-family: 'Segoe UI', Arial; } "
            "QLabel { background: transparent; border: none; font-family: 'Segoe UI', Arial; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: #fee2e2; border-radius: 8px;")
        icon.setPixmap(qta.icon("fa5s.file-pdf", color="#dc2626").pixmap(18, 18))
        text_col = QVBoxLayout()
        title = QLabel(t("report_preview_title"))
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #030213;")
        subtitle = QLabel(t("report_preview_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {MUTED};")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        header.addWidget(icon)
        header.addLayout(text_col, 1)
        layout.addLayout(header)

        scope = QFrame()
        scope.setObjectName("Card")
        scope.setStyleSheet(CARD_SS)
        scope_grid = QGridLayout(scope)
        scope_grid.setContentsMargins(18, 16, 18, 16)
        scope_grid.setHorizontalSpacing(18)
        scope_grid.setVerticalSpacing(12)
        for index, (label, value) in enumerate([
            (t("company"), report.company),
            (t("report_type"), t(f"report_type_{report.report_type}")),
            (t("report_period_label"), str(report.year)),
            (t("report_preview_scope"), report.filter_summary),
        ]):
            row = index // 2
            col = (index % 2) * 2
            scope_grid.addWidget(_preview_label(label), row, col)
            scope_grid.addWidget(_preview_value(value), row, col + 1)
        layout.addWidget(scope)

        metrics = QFrame()
        metrics.setObjectName("Card")
        metrics.setStyleSheet(CARD_SS)
        metric_layout = QGridLayout(metrics)
        metric_layout.setContentsMargins(18, 16, 18, 16)
        metric_layout.setHorizontalSpacing(12)
        metric_layout.setVerticalSpacing(12)
        preview_metrics = _report_preview_metrics(report)
        for index, metric in enumerate(preview_metrics):
            metric_layout.addWidget(_metric_chip(metric.label, metric.value, metric.detail), index // 3, index % 3)
        layout.addWidget(metrics)

        sections_title = QLabel(t("report_preview_sections"))
        sections_title.setStyleSheet("font-size: 13px; font-weight: 900; color: #030213;")
        layout.addWidget(sections_title)

        sections = QLabel("  |  ".join(report_section_titles(report)))
        sections.setWordWrap(True)
        sections.setStyleSheet(
            "font-size: 13px; color: #374151; background: #f9fafb; border: 1px solid #e5e7eb; "
            "border-radius: 8px; padding: 10px;"
        )
        layout.addWidget(sections)

        if _report_has_no_activity(report):
            warning = QLabel(t("report_preview_empty_warning"))
            warning.setWordWrap(True)
            warning.setStyleSheet(
                "font-size: 13px; color: #92400e; background: #fffbeb; border: 1px solid #fde68a; "
                "border-radius: 8px; padding: 10px;"
            )
            layout.addWidget(warning)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            "QPushButton { background: white; color: #111827; border: 1px solid #d1d5db; "
            "border-radius: 8px; padding: 0 18px; font-size: 13px; font-weight: 800; }"
            "QPushButton:hover { background: #f9fafb; }"
        )
        cancel.clicked.connect(self.reject)
        export = QPushButton(t("confirm_export_pdf"))
        export.setFixedHeight(38)
        export.setCursor(Qt.PointingHandCursor)
        export.setIcon(qta.icon("fa5s.file-pdf", color="white"))
        export.setStyleSheet(
            "QPushButton { background: #030213; color: white; border: none; border-radius: 8px; "
            "padding: 0 18px; font-size: 13px; font-weight: 800; }"
            "QPushButton:hover { background: #111827; }"
        )
        export.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(export)
        layout.addLayout(buttons)


def _content():
    content = QWidget()
    content.setStyleSheet(f"background: {PAGE_BG};")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(24)
    return content, layout


def _field_label(text):
    label = QLabel(text)
    label.setStyleSheet("font-size: 12px; font-weight: 800; color: #374151; background: transparent;")
    return label


def _preview_label(text):
    label = QLabel(str(text))
    label.setStyleSheet(f"font-size: 12px; font-weight: 900; color: {MUTED};")
    return label


def _preview_value(text):
    value = QLabel(str(text or "-"))
    value.setWordWrap(True)
    value.setStyleSheet("font-size: 13px; font-weight: 800; color: #111827;")
    return value


def _metric_chip(label, value, detail):
    chip = QFrame()
    chip.setObjectName("MetricChip")
    chip.setMinimumHeight(92)
    chip.setStyleSheet(
        "QFrame#MetricChip { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }"
        "QFrame#MetricChip QLabel { background: transparent; border: none; }"
    )
    layout = QVBoxLayout(chip)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)
    title = QLabel(str(label))
    title.setStyleSheet(f"font-size: 11px; font-weight: 900; color: {MUTED};")
    number = QLabel(str(value))
    number.setStyleSheet("font-size: 18px; font-weight: 900; color: #030213;")
    note = QLabel(str(detail or ""))
    note.setWordWrap(True)
    note.setStyleSheet(f"font-size: 11px; color: {MUTED}; line-height: 14px;")
    layout.addWidget(title)
    layout.addWidget(number)
    layout.addWidget(note)
    return chip


def _report_preview_metrics(report):
    wanted = {
        t("report_metric_headcount"),
        t("report_metric_promotions"),
        t("report_metric_increments"),
        t("report_metric_sanctions"),
        t("report_metric_audit_events"),
    }
    metrics = [metric for metric in report.metrics if metric.label in wanted]
    if report.report_type != "audit" and report.salary_summary:
        metrics.append(report.salary_summary[0])
    return metrics[:6]


def _report_has_no_activity(report):
    values = []
    for metric in report.metrics:
        try:
            values.append(int(str(metric.value).replace(",", "")))
        except ValueError:
            pass
    return values and sum(values) == 0


def _report_history_row(log, session=None):
    payload = _json_payload(log.after_value)
    year = payload.get("year") or "-"
    report_type = _export_value(payload.get("report_type") or "full", "report_type")
    scope = _report_history_scope(payload, session)
    path = payload.get("path") or "-"
    generated = log.performed_at.strftime("%Y-%m-%d %H:%M") if log.performed_at else "-"
    user = _user_snapshot(log.performed_by_username, log.performed_by_name)
    visible_user = (log.performed_by_name or log.performed_by_username or "System").strip()
    values = [
        f"{generated}\n{visible_user}",
        f"{report_type}\n{year}",
        scope,
        _history_filename(path),
    ]
    return {"values": values, "tooltips": [f"{generated}\n{user}", f"{year} {report_type}", scope, path]}


def _compact_path(path):
    if not path or path == "-":
        return "-"
    parts = str(path).replace("/", "\\").split("\\")
    parts = [part for part in parts if part]
    if len(parts) <= 2:
        return str(path)
    return f"...\\{parts[-2]}\\{parts[-1]}"


def _history_filename(path):
    if not path or path == "-":
        return "-"
    parts = str(path).replace("/", "\\").split("\\")
    parts = [part for part in parts if part]
    return parts[-1] if parts else str(path)


def _report_history_scope(payload, session=None):
    parts = []
    status = payload.get("status")
    if status and status != "all":
        parts.append(f"{t('status')}: {_export_value(status, 'status')}")
    if payload.get("org_unit_id"):
        parts.append(f"{t('department')}: {_org_unit_history_label(payload['org_unit_id'], session)}")
    if payload.get("title_id"):
        parts.append(f"{t('level')}: {_title_history_label(payload['title_id'], session)}")
    return "; ".join(parts) if parts else t("all_employees")


def _title_history_label(title_id, session=None):
    if not title_id:
        return "-"
    title = None
    if session is not None:
        title = session.query(Title).filter_by(id=title_id).first()
    if title:
        label = title.label or ""
        return f"{title.name} - {label}" if label else title.name
    return f"#{title_id}"


def _org_unit_history_label(org_unit_id, session=None):
    if not org_unit_id:
        return "-"
    unit = None
    if session is not None:
        unit = session.query(OrgUnit).filter_by(id=org_unit_id).first()
    return unit.name if unit else f"#{org_unit_id}"


def _json_payload(value):
    if not value:
        return {}
    try:
        payload = json.loads(value)
        return payload if isinstance(payload, dict) else {}
    except (TypeError, ValueError):
        return {}


def _user_snapshot(username, full_name):
    username = (username or "").strip()
    full_name = (full_name or "").strip()
    if username and full_name:
        return f"{username}: {full_name}"
    return username or full_name or "System"


def _export_value(value, key=None):
    if value is None:
        return ""
    text = str(value)
    if key in {"report_type", "status"}:
        return text.replace("_", " ").title()
    return text


def _write_pdf(path, html):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Millimeter)
    document = QTextDocument()
    document.setDefaultFont(QFont("Segoe UI", 10))
    document.setPageSize(printer.pageLayout().paintRectPoints().size())
    document.setHtml(html)
    document.print_(printer)
    _stamp_pdf_page_numbers(path)


def _stamp_pdf_page_numbers(path):
    """Add real PDF page numbers after Qt renders the document."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
    except Exception:
        return

    tmp_path = f"{path}.tmp"
    try:
        reader = PdfReader(path)
        total = len(reader.pages)
        if total <= 1:
            return

        writer = PdfWriter()
        for index, page in enumerate(reader.pages, start=1):
            _append_page_number_stream(
                writer,
                page,
                f"{index} / {total}",
                DecodedStreamObject,
                DictionaryObject,
                NameObject,
                ArrayObject,
            )
            writer.add_page(page)

        with open(tmp_path, "wb") as handle:
            writer.write(handle)
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def _append_page_number_stream(writer, page, text, stream_cls, dict_cls, name_cls, array_cls):
    resources = page.get("/Resources")
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    if resources is None:
        resources = dict_cls()
        page[name_cls("/Resources")] = resources

    fonts = resources.get("/Font")
    fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
    if fonts is None:
        fonts = dict_cls()
        resources[name_cls("/Font")] = fonts
    fonts[name_cls("/F_PageFooter")] = dict_cls({
        name_cls("/Type"): name_cls("/Font"),
        name_cls("/Subtype"): name_cls("/Type1"),
        name_cls("/BaseFont"): name_cls("/Helvetica"),
    })

    width = float(page.mediabox.width)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    footer_stream = stream_cls()
    footer_stream.set_data(
        (
            "q\n"
            "BT\n"
            "/F_PageFooter 8 Tf\n"
            "0.54 0.58 0.63 rg\n"
            f"1 0 0 1 {width - 72:.2f} 24 Tm\n"
            f"({escaped}) Tj\n"
            "ET\n"
            "Q\n"
        ).encode("latin-1", errors="replace")
    )
    footer_ref = writer._add_object(footer_stream)

    existing = page.get("/Contents")
    if existing is None:
        page[name_cls("/Contents")] = footer_ref
    elif isinstance(existing, array_cls):
        existing.append(footer_ref)
    else:
        page[name_cls("/Contents")] = array_cls([existing, footer_ref])


def _set_page(page, content):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setStyleSheet(f"border: none; background: {PAGE_BG};")
    scroll.setWidget(content)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(scroll)


def _plain_card():
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet(CARD_SS)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return card


def _section_card(title, subtitle=None, icon_name=None, icon_color=BLUE):
    card = _plain_card()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(30, 28, 30, 30)
    layout.setSpacing(22)

    header = QHBoxLayout()
    header.setSpacing(10)
    if icon_name:
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        header.addWidget(icon)
    texts = QVBoxLayout()
    texts.setSpacing(6)
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT}; background: transparent;")
    texts.addWidget(title_lbl)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        texts.addWidget(sub)
    header.addLayout(texts)
    header.addStretch()
    layout.addLayout(header)
    return card, layout


def _note_card(title, lines, icon_name, color, stylesheet):
    card = QFrame()
    card.setStyleSheet(stylesheet)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(8)

    header = QHBoxLayout()
    header.setSpacing(10)
    icon = QLabel()
    icon.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {color}; background: transparent;")
    header.addWidget(icon)
    header.addWidget(title_lbl)
    header.addStretch()
    layout.addLayout(header)

    for line in lines:
        lbl = QLabel("&bull; " + line)
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
        layout.addWidget(lbl)
    return card


def _promotion_guide():
    return _note_card(
        t("how_promotion_race_works"),
        [
            t("race_guide_level_track"),
            t("race_guide_checkpoint"),
            t("race_guide_commendations"),
            t("race_guide_sanctions"),
            t("race_guide_eligible"),
        ],
        "fa5s.chart-line",
        "#1e40af",
        """
        QFrame {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eff6ff,stop:1 #f5f3ff);
            border: 1px solid #bfdbfe;
            border-radius: 8px;
        }
        QLabel { background: transparent; border: none; }
        """,
    )


def _label(text):
    label = QLabel(text)
    label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {TEXT}; background: transparent;")
    return label


def _hint(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("font-size: 13px; color: #64748b; background: transparent;")
    return label


def _line_edit(placeholder=""):
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setStyleSheet(INPUT_SS)
    field.setFixedHeight(44)
    return field


def _spin(minimum, maximum, value):
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setStyleSheet(INPUT_SS)
    spin.setFixedHeight(44)
    return spin


def _money_spin():
    spin = QDoubleSpinBox()
    spin.setRange(0, 9999999)
    spin.setDecimals(0)
    spin.setStyleSheet(INPUT_SS)
    spin.setFixedHeight(44)
    return spin


def _percent_spin(value):
    spin = QDoubleSpinBox()
    spin.setRange(0, 100)
    spin.setDecimals(1)
    spin.setValue(value)
    spin.setStyleSheet(INPUT_SS)
    spin.setFixedHeight(44)
    return spin


def _increment_value_spin(value):
    spin = QDoubleSpinBox()
    spin.setRange(0, 9999999)
    spin.setDecimals(2)
    spin.setValue(value)
    spin.setStyleSheet(INPUT_SS)
    spin.setFixedHeight(44)
    return spin


def _sync_increment_spin_suffix(combo, spin, currency):
    if combo.currentData() == "fixed":
        spin.setRange(0, 9999999)
        spin.setDecimals(2)
        spin.setSuffix(f" {currency or 'EUR'}")
    else:
        spin.setRange(0, 100)
        spin.setDecimals(2)
        spin.setSuffix("%")


def _style_combo(combo):
    combo.setStyleSheet(COMBO_SS)
    combo.setFixedHeight(44)
    polish_combo_box(combo)


def _add_form_field(grid, row, col, label_text, widget):
    wrapper = QVBoxLayout()
    wrapper.setSpacing(8)
    wrapper.addWidget(_label(label_text))
    wrapper.addWidget(widget)
    grid.addLayout(wrapper, row, col)


def _button(text, icon_name, primary=False):
    button = QPushButton("  " + text)
    button.setIcon(qta.icon(icon_name, color="white" if primary else "#111827"))
    button.setIconSize(QSize(15, 15))
    button.setCursor(Qt.PointingHandCursor)
    button.setFixedHeight(50)
    button.setStyleSheet(_primary_button_ss() if primary else _secondary_button_ss())
    return button


def _badge_icon(icon_name, color, background):
    label = QLabel()
    label.setFixedSize(44, 44)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(f"background: {background}; border-radius: 8px;")
    label.setPixmap(qta.icon(icon_name, color=color).pixmap(20, 20))
    return label


def _titles():
    session = get_session()
    try:
        return _ordered_titles(session)
    finally:
        session.close()


def _ordered_titles(session):
    titles = session.query(Title).all()
    order_map = _promotion_order_map(session)
    titles.sort(key=lambda title: order_map.get(title.id, _level_sort_key(title)))
    return titles


def _promotion_order_map(session):
    titles = session.query(Title).all()
    title_by_id = {title.id: title for title in titles}
    non_other_ids = [title.id for title in titles if title.name != "Other"]
    links = {}
    incoming = set()
    for rule in session.query(PromotionRule).all():
        if rule.from_title_id in non_other_ids and rule.to_title_id in non_other_ids:
            links[rule.from_title_id] = rule.to_title_id
            incoming.add(rule.to_title_id)

    starts = [title_id for title_id in non_other_ids if title_id not in incoming]
    starts.sort(key=lambda title_id: _level_sort_key(title_by_id[title_id]))

    order = {}
    visited = set()
    index = 0
    for start in starts:
        current = start
        while current and current not in visited and current in title_by_id:
            order[current] = (0, index)
            visited.add(current)
            index += 1
            current = links.get(current)

    remaining = [title_id for title_id in non_other_ids if title_id not in visited]
    remaining.sort(key=lambda title_id: _level_sort_key(title_by_id[title_id]))
    for title_id in remaining:
        order[title_id] = (1, index, _level_sort_key(title_by_id[title_id]))
        index += 1

    for title in titles:
        if title.name == "Other":
            order[title.id] = (2, 0)
    return order


def _promotion_mapping_validation_key(session, mapping):
    titles = {title.id: title for title in session.query(Title).all()}
    used_targets = {}
    for from_title_id, target_id in mapping.items():
        if from_title_id >= 0:
            source = titles.get(from_title_id)
            if not source:
                return "promotion_source_missing"
            if source.name == "Other" and target_id is not None:
                return "promotion_target_other_forbidden"
        if target_id is None:
            continue
        if target_id == from_title_id:
            return "promotion_target_same_level"
        target = titles.get(target_id)
        if not target:
            return "promotion_target_missing"
        if target.name == "Other":
            return "promotion_target_other_forbidden"
        if target_id in used_targets:
            return "promotion_target_duplicate"
        used_targets[target_id] = from_title_id

    if _has_promotion_cycle(mapping):
        return "promotion_target_cycle_error"
    return None


def _has_promotion_cycle(mapping):
    for start in mapping:
        seen = set()
        current = start
        while current in mapping and mapping[current] is not None:
            if current in seen:
                return True
            seen.add(current)
            current = mapping[current]
    return False


def _valid_currency_code(value):
    code = (value or "").strip()
    return 2 <= len(code) <= 10 and code.replace("-", "").isalnum()


def _salary_transition_validation_key(source_min, source_max, source_currency, target):
    if not target or target.name == "Other":
        return None
    if (source_currency or "").upper() != (target.currency or "").upper():
        return None
    if float(source_max or 0) >= float(target.base_salary_max or 0):
        return "promotion_salary_range_order_warning"
    if float(source_min or 0) >= float(target.base_salary_max or 0):
        return "promotion_salary_range_order_warning"
    return None


def _promotion_rules_salary_validation_key(titles, mapping):
    for from_title_id, target_id in mapping.items():
        if target_id is None:
            continue
        source = titles.get(from_title_id)
        target = titles.get(target_id)
        if not source or not target:
            return "promotion_target_missing"
        key = _salary_transition_validation_key(
            source.base_salary_min,
            source.base_salary_max,
            source.currency,
            target,
        )
        if key:
            return key
    return None


def _salary_policy_validation_key(titles, rules):
    for title in titles.values():
        if float(title.base_salary_min or 0) > float(title.base_salary_max or 0):
            return "salary_min_max_warning"
        if not _valid_currency_code(title.currency):
            return "currency_code_warning"
    return _promotion_rules_salary_validation_key(
        titles,
        {rule.from_title_id: rule.to_title_id for rule in rules if rule.is_active},
    )


def _level_option_label(title):
    return f"{title.name} - {title.label}" if title.label else title.name


def _level_sort_key(title):
    name = title.name if hasattr(title, "name") else str(title)
    if name == "Other":
        return (2, 0)
    if name.startswith("L") and name[1:].isdigit():
        return (0, -int(name[1:]))
    return (1, LEVEL_ORDER.get(name, 999), name)


def _format_increment(title):
    currency = title.currency or "EUR"
    if title.annual_increment_type == "fixed":
        return f"+{title.annual_increment_value:.0f} {currency}"
    value = title.annual_increment_value
    return f"+{value:.0f}%" if float(value).is_integer() else f"+{value:.1f}%"


def _format_promotion_bump(title):
    value = title.promotion_salary_increase_pct
    return f"+{value:.0f}%" if float(value).is_integer() else f"+{value:.1f}%"


def _summary_table_ss():
    return table_style(row_font_size=13, header_height=42, item_padding=14)


def _clear_table_widgets(table):
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            widget = table.cellWidget(row, col)
            if widget:
                table.removeCellWidget(row, col)
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            widget = item.widget()
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout():
            child_layout = item.layout()
            _clear_layout(child_layout)
            child_layout.setParent(None)
            child_layout.deleteLater()


def _set_tooltip_item(table, row, col, text):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    item.setToolTip(str(text))
    table.setItem(row, col, item)


def _pill_cell(text, color, background, bold=False, align=Qt.AlignLeft, min_width=None, fixed_width=False):
    cell = prepare_table_cell_widget(QWidget())
    layout = QHBoxLayout(cell)
    if align == Qt.AlignCenter:
        layout.setContentsMargins(0, 7, 0, 7)
    else:
        layout.setContentsMargins(14, 7, 8, 7)
    layout.setSpacing(0)
    layout.setAlignment(align | Qt.AlignVCenter)
    label = QLabel(str(text))
    label.setToolTip(str(text))
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        f"background: {background}; color: {color}; border: none; border-radius: 7px; "
        f"font-size: 13px; font-weight: {'900' if bold else '500'}; padding: 2px 9px;"
    )
    label.setMinimumHeight(24)
    computed_width = max(44, len(str(text)) * 8 + 24)
    width = max(min_width or 0, computed_width)
    label.setMinimumWidth(width)
    if fixed_width:
        label.setFixedWidth(width)
    if align == Qt.AlignCenter:
        label.setMinimumWidth(max(label.minimumWidth(), 44))
    layout.addWidget(label)
    if align != Qt.AlignCenter:
        layout.addStretch()
    return cell


def _primary_button_ss():
    return """
QPushButton {
    background: #030213;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 800;
    padding: 0 18px;
}
QPushButton:hover { background: #111827; }
QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
"""


def _secondary_button_ss():
    return """
QPushButton {
    background: white;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 800;
    padding: 0 18px;
}
QPushButton:hover { background: #f3f4f6; }
"""


def _danger_icon_button_ss():
    return """
QPushButton {
    background: white;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 8px;
}
QPushButton:hover {
    background: #fef2f2;
    border-color: #fca5a5;
}
QPushButton:disabled {
    background: #f9fafb;
    color: #9ca3af;
    border: 1px solid #e5e7eb;
}
"""


def _styled_message_box(parent, icon, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    box.setStyleSheet(MESSAGE_BOX_SS)
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
