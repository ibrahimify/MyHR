"""
Settings Page
- General company branding and organization details
- Salary ranges and annual increment rules
- Promotion race settings
- Security and database utilities
"""

from hashlib import sha256
import csv
import shutil

import qtawesome as qta
from sqlalchemy import func
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QMessageBox, QTabWidget,
    QSpinBox, QDoubleSpinBox, QFileDialog, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout
)

from src.core.i18n import t
from src.core.app_settings import app_settings, company_name
from src.database.connection import get_session, log_action, DB_PATH
from src.database.models import Title, SystemUser, PromotionRule, Employee


PAGE_BG = "#f9fafb"
TEXT = "#030213"
MUTED = "#4b5563"
BLACK = "#030213"
BLUE = "#2563eb"

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

CARD_SS = """
QFrame#Card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame#Card QLabel {
    background: transparent;
    border: none;
}
"""

NOTE_BLUE_SS = """
QFrame {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
}
QLabel {
    background: transparent;
    border: none;
}
"""

NOTE_YELLOW_SS = """
QFrame {
    background: #fefce8;
    border: 1px solid #fde047;
    border-radius: 8px;
}
QLabel {
    background: transparent;
    border: none;
}
"""

INPUT_SS = """
QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #f3f3f5;
    color: #111827;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0 12px;
    min-height: 44px;
    font-size: 14px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    background: white;
    border: 1px solid #2563eb;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    border: none;
}
"""

COMBO_SS = """
QComboBox {
    background: #f3f3f5;
    color: #111827;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0 34px 0 12px;
    min-height: 44px;
    font-size: 14px;
}
QComboBox:focus {
    background: white;
    border: 1px solid #2563eb;
}
QComboBox::drop-down {
    width: 30px;
    border: none;
}
QComboBox::down-arrow {
    image: url(src/ui/assets/chevron_down.svg);
    width: 13px;
    height: 13px;
}
QComboBox QAbstractItemView {
    background: white;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 0px;
    padding: 4px;
    selection-background-color: #eff6ff;
    selection-color: #111827;
    outline: none;
}
"""

TAB_SS = """
QTabWidget::pane {
    border: none;
    background: #f9fafb;
    margin-top: 26px;
}
QTabBar {
    background: #e5e7eb;
    border-radius: 14px;
}
QTabBar::tab {
    background: transparent;
    color: #030213;
    border: none;
    padding: 9px 16px;
    min-height: 26px;
    font-size: 14px;
    font-weight: 800;
}
QTabBar::tab:selected {
    background: white;
    border-radius: 14px;
}
QTabBar::tab:hover {
    background: #f3f4f6;
    border-radius: 14px;
}
"""

MESSAGE_BOX_SS = """
QMessageBox { background: white; color: #111827; }
QMessageBox QLabel { color: #111827; background: transparent; font-size: 13px; }
QPushButton {
    background: white;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}
QPushButton:hover { background: #f3f4f6; }
QPushButton:default { background: #030213; color: white; border: none; }
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
        self.tabs.setStyleSheet(TAB_SS)
        self.tabs.addTab(GeneralTab(self.user), t("general"))
        self._add_policy_tabs()
        self.tabs.addTab(UserManagementTab(self.user), t("user_management"))
        self.tabs.addTab(DatabaseTab(self.user), t("database_tab"))
        self.tabs.currentChanged.connect(self._refresh_current_tab)
        layout.addWidget(self.tabs, 1)

    def _add_policy_tabs(self, insert_at=None):
        self.summary_tab = PolicySummaryTab(self.user)
        self.level_tab = LevelManagementTab(self.user, on_saved=self._reload_policy_tabs)
        self.salary_tab = SalaryTab(self.user)
        self.promotion_tab = SettingsPromotionTab(self.user)
        self.increment_tab = IncrementTab(self.user)
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

    def _refresh_current_tab(self, index):
        widget = self.tabs.widget(index)
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()


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
            titles = session.query(Title).all()
            titles.sort(key=_level_sort_key)
            title_counts = {
                title_id: count for title_id, count in
                session.query(Employee.title_id, func.count(Employee.id))
                .filter(Employee.status == "active")
                .group_by(Employee.title_id)
                .all()
            }
            rules = session.query(PromotionRule).all()
            rules.sort(key=lambda rule: _level_sort_key(rule.from_title))

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
        table.setSelectionBehavior(QTableWidget.SelectRows)
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
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
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
            titles = session.query(Title).all()
            titles.sort(key=_level_sort_key)
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
            self.table.setCellWidget(row_index, 0, _pill_cell(row["values"][0], "#1d4ed8", "#dbeafe"))
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
        compact = {
            0: 96,
            2: 78,
            4: 112,
            5: 96,
            6: 100,
            7: 116,
            8: 118,
        }
        remaining = max(260, available - sum(compact.values()))
        widths = dict(compact)
        widths[1] = int(remaining * 0.44)
        widths[3] = remaining - widths[1]
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, max(56, widths.get(col, 80)))

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
        cell = QWidget()
        cell.setStyleSheet("background: transparent; border: none;")
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
        self.increment_value = _percent_spin(3.0)
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

    def _save(self):
        level = self.level_name.text().strip()
        label = self.level_label.text().strip()
        currency = self.currency.text().strip().upper() or "EUR"
        target_id = self.target_title.currentData()

        if not level or not label:
            _warning(self, t("warning"), t("level_name_label_required"))
            return
        if level.lower() == "other":
            _warning(self, t("warning"), t("level_name_format_warning"))
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
            target = session.query(Title).filter_by(id=target_id).first() if target_id else None
            if not target and not self.is_edit:
                _warning(self, t("warning"), t("promotion_target_required"))
                return
            if self.is_edit:
                title = session.query(Title).filter_by(id=self.title_id).first()
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
    def __init__(self, user):
        super().__init__()
        self.user = user
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
        self.fields[title.name] = (min_spin, max_spin)
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
                if title.name in self.fields:
                    min_spin, max_spin = self.fields[title.name]
                    min_spin.setValue(title.base_salary_min)
                    max_spin.setValue(title.base_salary_max)
                    self.currency_input.setText(title.currency or "EUR")
        finally:
            session.close()
        self._update_currency_badges()

    def _save(self):
        session = get_session()
        try:
            currency = self.currency_input.text().strip() or "EUR"
            for level, (min_spin, max_spin) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    title.base_salary_min = min_spin.value()
                    title.base_salary_max = max_spin.value()
                    title.currency = currency
            log_action(session, action="settings.salary_ranges", performed_by_id=self.user.id, description="Salary ranges updated")
            session.commit()
            _information(self, t("success"), t("salary_ranges_saved"))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class SettingsPromotionTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
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
            rows = []
            for rule in session.query(PromotionRule).all():
                rows.append({
                    "id": rule.id,
                    "from": rule.from_title.name,
                    "to": rule.to_title.name,
                    "base_months": rule.base_months,
                    "salary_increase": rule.to_title.promotion_salary_increase_pct,
                })
        finally:
            session.close()

        rows.sort(key=lambda row: _level_sort_key(row["from"]))
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
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        months = _spin(1, 120, row["base_months"])
        salary = _percent_spin(row["salary_increase"])
        grid.addWidget(_label(t("base_track_duration_months")), 0, 0)
        grid.addWidget(_label(t("base_salary_increase")), 0, 1)
        grid.addWidget(months, 1, 0)
        grid.addWidget(salary, 1, 1)
        grid.addWidget(_hint(t("starting_point_for_race")), 2, 0)
        grid.addWidget(_hint(t("upon_promotion_to_next")), 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.fields[row["id"]] = (months, salary)
        return card

    def _save(self):
        session = get_session()
        try:
            for rule_id, (months_spin, salary_spin) in self.fields.items():
                rule = session.query(PromotionRule).filter_by(id=rule_id).first()
                if rule:
                    rule.base_months = months_spin.value()
                    rule.to_title.promotion_salary_increase_pct = salary_spin.value()
            log_action(session, action="settings.promotion_rules", performed_by_id=self.user.id, description="Promotion settings updated")
            session.commit()
            _information(self, t("success"), t("promotion_settings_saved"))
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class IncrementTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
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
        value_spin = _percent_spin(3.0)
        fields.addWidget(_label(t("increment_type")), 0, 0)
        fields.addWidget(_label(t("increment_value")), 0, 1)
        fields.addWidget(type_combo, 1, 0)
        fields.addWidget(value_spin, 1, 1)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        layout.addLayout(fields)
        self.fields[title.name] = (type_combo, value_spin)
        return card

    def _load(self):
        session = get_session()
        try:
            for level, (combo, spin) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    index = combo.findData(title.annual_increment_type)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                    spin.setValue(title.annual_increment_value)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            for level, (combo, spin) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    title.annual_increment_type = combo.currentData()
                    title.annual_increment_value = spin.value()
            log_action(session, action="settings.increment_rules", performed_by_id=self.user.id, description="Annual increment rules updated")
            session.commit()
            _information(self, t("success"), t("increment_rules_saved"))
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
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
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
        cell = QWidget()
        cell.setStyleSheet("background: transparent; border: none;")
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
        row.addLayout(left, 3)

        right, right_layout = _section_card(t("database_notes"), None, "fa5s.info-circle", BLACK)
        right_layout.addWidget(_note_card(
            t("coming_in_thesis_extension"),
            [
                t("db_note_scheduled_backups"),
                t("db_note_yearly_reports"),
                t("db_note_export_filters"),
                t("db_note_health_check"),
            ],
            "fa5s.tools",
            "#92400e",
            NOTE_YELLOW_SS,
        ))
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


def _content():
    content = QWidget()
    content.setStyleSheet(f"background: {PAGE_BG};")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(24)
    return content, layout


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


def _style_combo(combo):
    combo.setStyleSheet(COMBO_SS)
    combo.setFixedHeight(44)
    combo.view().setStyleSheet(
        "QListView { background: white; color: #111827; border: 1px solid #d1d5db; border-radius: 0px; padding: 4px; outline: none; }"
        "QListView::item { min-height: 30px; padding: 6px 10px; color: #111827; background: white; }"
        "QListView::item:hover, QListView::item:selected { background: #eff6ff; color: #111827; }"
    )


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
        titles = session.query(Title).all()
        titles.sort(key=_level_sort_key)
        return titles
    finally:
        session.close()


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
    return """
QTableWidget {
    background: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 13px;
    color: #111827;
    outline: none;
    selection-background-color: #eff6ff;
}
QTableWidget::item {
    background: white;
    padding: 0 16px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
}
QTableWidget::item:selected { background: #eff6ff; color: #111827; }
QHeaderView::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 16px;
    font-size: 12px;
    font-weight: 800;
    color: #111827;
    min-height: 42px;
    text-align: left;
}
QTableCornerButton::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 5px;
    min-height: 32px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    border: none;
    background: transparent;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
"""


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


def _pill_cell(text, color, background, bold=False, align=Qt.AlignLeft):
    cell = QWidget()
    cell.setStyleSheet("background: transparent; border: none;")
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
        f"font-size: 13px; font-weight: {'900' if bold else '500'}; padding: 3px 10px;"
    )
    label.setMinimumHeight(26)
    label.setMinimumWidth(max(44, len(str(text)) * 9 + 20))
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
