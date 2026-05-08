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
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QMessageBox, QTabWidget,
    QSpinBox, QDoubleSpinBox, QFileDialog, QSizePolicy
)

from src.core.i18n import t
from src.core.app_settings import app_settings, company_name
from src.database.connection import get_session, log_action, DB_PATH
from src.database.models import Title, SystemUser, PromotionRule, Employee


PAGE_BG = "#f9fafb"
TEXT = "#030213"
MUTED = "#4b5563"
BORDER = "#e5e7eb"
BLACK = "#030213"
BLUE = "#2563eb"

LEVEL_META = {
    "L7": ("Entry Level (BSc)", "#2563eb", "#dbeafe"),
    "L6": ("Mid Level (MSc)", "#16a34a", "#dcfce7"),
    "L5": ("Senior Level (PhD)", "#d97706", "#fef3c7"),
    "L4": ("Management Level", "#7c3aed", "#ede9fe"),
    "L3": ("Director Level", "#db2777", "#fce7f3"),
    "L2": ("Executive Level", "#0284c7", "#e0f2fe"),
    "L1": ("CEO / Board", "#dc2626", "#fee2e2"),
}
LEVEL_ORDER = {level: index for index, level in enumerate(["L7", "L6", "L5", "L4", "L3", "L2", "L1"])}

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
    border-radius: 8px;
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
        self.setStyleSheet(f"background: {PAGE_BG};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel("System Settings")
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {TEXT}; background: transparent;")
        subtitle = QLabel("Configure salary levels, promotion rules, account security, and database tools")
        subtitle.setStyleSheet(f"font-size: 16px; color: {MUTED}; background: transparent;")

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_SS)
        self.tabs.addTab(GeneralTab(self.user), "General")
        self.tabs.addTab(SalaryTab(self.user), "Salary Ranges")
        self.tabs.addTab(SettingsPromotionTab(self.user), "Promotion Rules")
        self.tabs.addTab(IncrementTab(self.user), "Annual Increment")
        self.tabs.addTab(SecurityTab(self.user), "Security")
        self.tabs.addTab(DatabaseTab(self.user), "Database")
        layout.addWidget(self.tabs, 1)


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

        form, form_layout = _section_card("Organization Information", "Basic company details shown in the sidebar, login screen, reports, and exports", "fa5s.building", BLUE)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)

        self.company_name = _line_edit()
        self.company_subtitle = _line_edit()
        self.company_address = _line_edit()
        self.fiscal_start = _line_edit("01-01")
        self.timezone = _line_edit("Europe/Budapest")

        _add_form_field(grid, 0, 0, "Company Name", self.company_name)
        _add_form_field(grid, 0, 1, "Company Subtitle", self.company_subtitle)
        _add_form_field(grid, 1, 0, "Company Address", self.company_address)
        _add_form_field(grid, 1, 1, "Fiscal Year Start (MM-DD)", self.fiscal_start)
        _add_form_field(grid, 2, 0, "Timezone", self.timezone)
        form_layout.addLayout(grid)
        row.addWidget(form, 3)

        actions, actions_layout = _section_card("Actions", None, "fa5s.save", BLACK)
        save = _button("Save General Settings", "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        actions_layout.addWidget(save)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(_note_card(
            "Branding Update",
            [
                "Company name updates the sidebar immediately.",
                "The same name is used on the login screen.",
                "Subtitle controls the small text under the brand.",
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
            window.setWindowTitle(f"{company_name('MyHR')} - Employee Management System")
        _information(self, t("success"), "General settings saved.")


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

        top, top_layout = _section_card("Salary Range Configuration", "Configure currency and level salary ranges", "fa5s.coins", BLUE)
        currency_row = QHBoxLayout()
        currency_row.setSpacing(14)
        currency_row.addWidget(_label("Currency Code"))
        self.currency_input = _line_edit("EUR")
        self.currency_input.setFixedWidth(130)
        self.currency_input.textChanged.connect(self._on_currency_changed)
        currency_row.addWidget(self.currency_input)
        note = QLabel("Applies to all levels")
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

        save = _button("Save Salary Ranges", "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        outer.addWidget(save, alignment=Qt.AlignLeft)
        outer.addStretch()
        _set_page(self, content)

    def _salary_card(self, title):
        label, color, bg = LEVEL_META.get(title.name, (title.label, BLUE, "#dbeafe"))
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

        fields.addWidget(_label("Minimum Salary"), 0, 0)
        fields.addWidget(_label("Currency"), 0, 1)
        fields.addWidget(_label("Maximum Salary"), 0, 2)
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
            _information(self, t("success"), "Salary ranges saved.")
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

        card, layout = _section_card("Promotion Track Configuration", "Configure the promotion race timeline and salary bump for each level", "fa5s.chart-line", BLUE)
        layout.addWidget(_promotion_guide())
        self.rules_list = QVBoxLayout()
        self.rules_list.setSpacing(18)
        layout.addLayout(self.rules_list)
        layout.addWidget(_note_card(
            "Track Modifiers",
            [
                "Commendations reduce months remaining.",
                "Sanctions add delay months to the promotion timeline.",
                "After promotion, the next race starts from month zero.",
            ],
            "fa5s.clock",
            "#92400e",
            NOTE_YELLOW_SS,
        ))
        save = _button("Save Promotion Settings", "fa5s.save", primary=True)
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

        rows.sort(key=lambda row: LEVEL_ORDER.get(row["from"], 99))
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
        title = QLabel(f"{row['from']} -> {row['to']}")
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
        grid.addWidget(_label("Base Track Duration (months)"), 0, 0)
        grid.addWidget(_label("Base Salary Increase"), 0, 1)
        grid.addWidget(months, 1, 0)
        grid.addWidget(salary, 1, 1)
        grid.addWidget(_hint("Starting point for the promotion race"), 2, 0)
        grid.addWidget(_hint("Upon promotion to next level"), 2, 1)
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
            _information(self, t("success"), "Promotion settings saved.")
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
            "Annual Increment Rules",
            ["Applied manually by admin when employees reach their anniversary date."],
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

        save = _button("Save Increment Rules", "fa5s.save", primary=True)
        save.clicked.connect(self._save)
        outer.addWidget(save, alignment=Qt.AlignLeft)
        outer.addStretch()
        _set_page(self, content)

    def _increment_card(self, title):
        label, color, bg = LEVEL_META.get(title.name, (title.label, BLUE, "#dbeafe"))
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
        type_combo.addItem("Percentage (%)", "percentage")
        type_combo.addItem("Fixed Amount", "fixed")
        _style_combo(type_combo)
        value_spin = _percent_spin(3.0)
        fields.addWidget(_label("Increment Type"), 0, 0)
        fields.addWidget(_label("Increment Value"), 0, 1)
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
            _information(self, t("success"), "Annual increment rules saved.")
        except Exception as exc:
            session.rollback()
            _critical(self, t("error"), str(exc))
        finally:
            session.close()


class SecurityTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()

    def _build(self):
        content, outer = _content()
        row = QHBoxLayout()
        row.setSpacing(30)
        row.setAlignment(Qt.AlignTop)

        card, layout = _section_card("Change Password", "Update your account password", "fa5s.lock", BLUE)
        self.current_pwd = _line_edit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd = _line_edit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd = _line_edit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        form = QGridLayout()
        form.setVerticalSpacing(16)
        _add_form_field(form, 0, 0, "Current Password", self.current_pwd)
        _add_form_field(form, 1, 0, "New Password", self.new_pwd)
        _add_form_field(form, 2, 0, "Confirm New Password", self.confirm_pwd)
        layout.addLayout(form)
        row.addWidget(card, 3)

        actions, actions_layout = _section_card("Actions", None, "fa5s.key", BLACK)
        change = _button("Change Password", "fa5s.key", primary=True)
        change.clicked.connect(self._change_password)
        actions_layout.addWidget(change)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(_note_card(
            "Security Information",
            [
                "Audit logs are retained indefinitely for compliance.",
                "All actions are logged with user identity and timestamp.",
                "Only admin and HR Officer accounts can log in.",
                "Passwords are stored as SHA-256 hashes.",
            ],
            "fa5s.shield-alt",
            "#1e40af",
            NOTE_BLUE_SS,
        ))
        actions_layout.addStretch()
        row.addWidget(actions, 1)
        outer.addLayout(row)
        outer.addStretch()
        _set_page(self, content)

    def _change_password(self):
        current = self.current_pwd.text()
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if not current or not new or not confirm:
            _warning(self, t("warning"), "All fields are required.")
            return
        if new != confirm:
            _warning(self, t("warning"), "New passwords do not match.")
            return
        if len(new) < 6:
            _warning(self, t("warning"), "Password must be at least 6 characters.")
            return

        session = get_session()
        try:
            user = session.query(SystemUser).filter_by(id=self.user.id).first()
            if not user or user.password_hash != sha256(current.encode()).hexdigest():
                _critical(self, t("error"), "Current password is incorrect.")
                return
            user.password_hash = sha256(new.encode()).hexdigest()
            log_action(session, action="settings.password_change", performed_by_id=self.user.id, description=f"Password changed for user: {self.user.username}")
            session.commit()
            self.current_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
            _information(self, t("success"), "Password changed successfully.")
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

        backup, backup_layout = _section_card("Database Backup", "Create a copy of the local SQLite database", "fa5s.database", BLUE)
        backup_info = QLabel("Backs up the myhr.db database file to a location you choose.")
        backup_info.setWordWrap(True)
        backup_info.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        backup_layout.addWidget(backup_info)
        backup_btn = _button("Create Backup", "fa5s.save", primary=True)
        backup_btn.clicked.connect(self._backup)
        backup_layout.addWidget(backup_btn, alignment=Qt.AlignLeft)
        left.addWidget(backup)

        export, export_layout = _section_card("Export All Employees", "Export all employee records to CSV", "fa5s.file-export", BLUE)
        export_info = QLabel("Exports a CSV file containing employee records for reporting or migration.")
        export_info.setWordWrap(True)
        export_info.setStyleSheet(f"font-size: 14px; color: {MUTED}; background: transparent;")
        export_layout.addWidget(export_info)
        export_btn = _button("Export Employees CSV", "fa5s.download", primary=True)
        export_btn.clicked.connect(self._export)
        export_layout.addWidget(export_btn, alignment=Qt.AlignLeft)
        left.addWidget(export)
        row.addLayout(left, 3)

        right, right_layout = _section_card("Database Notes", None, "fa5s.info-circle", BLACK)
        right_layout.addWidget(_note_card(
            "Coming in Thesis Extension",
            [
                "Scheduled automatic backups.",
                "Yearly reporting summaries.",
                "Data export by department or date range.",
                "Database health check and integrity validation.",
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
        path, _ = QFileDialog.getSaveFileName(self, "Save Backup", "myhr_backup.db", "SQLite Database (*.db)")
        if not path:
            return
        try:
            shutil.copy2(DB_PATH, path)
            _information(self, t("success"), f"Backup saved to:\n{path}")
        except Exception as exc:
            _critical(self, t("error"), str(exc))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Employees", "employees_export.csv", "CSV Files (*.csv)")
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
            _information(self, t("success"), f"Exported {len(employees)} employee records to:\n{path}")
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
        "How the Promotion Race Works",
        [
            "Each promotion level is a <b>race track</b> with a base duration in months.",
            "Employees move forward <b>1 checkpoint per month</b> automatically.",
            "<b>Commendations</b> speed up the race by reducing months remaining.",
            "<b>Sanctions</b> delay the race by adding months to the timeline.",
            "When the employee reaches 0 months remaining, they become eligible for promotion.",
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
        "QListView { background: white; color: #111827; border: 1px solid #d1d5db; border-radius: 8px; padding: 4px; outline: none; }"
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
        titles.sort(key=lambda title: LEVEL_ORDER.get(title.name, 99))
        return titles
    finally:
        session.close()


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()


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
