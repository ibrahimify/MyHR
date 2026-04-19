"""
Settings Page
- General: company name, address, currency
- Salary Ranges: min/max per level (L3-L7)
- Promotion Rules: base months per transition (redirect to promotions page rules tab)
- Annual Increment: per-level increment type and value
- Security: session timeout, password expiry
- Database: backup, export
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QMessageBox,
    QTabWidget, QSpinBox, QDoubleSpinBox, QFileDialog
)
from PySide6.QtCore import Qt

from src.core.i18n import t
from src.database.connection import get_session, log_action
from src.database.models import Title, SystemUser
import csv
import os


class SettingsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        title = QLabel(t("settings_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        sub = QLabel(t("settings_subtitle"))
        sub.setStyleSheet("font-size: 13px; color: #9ca3af; margin-left: 12px;")
        h.addWidget(title)
        h.addWidget(sub)
        h.addStretch()
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f9fafb; }
            QTabBar::tab { background: white; color: #6b7280; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; font-size: 13px; }
            QTabBar::tab:selected { color: #030213; border-bottom: 2px solid #030213; font-weight: bold; }
            QTabBar::tab:hover { color: #111827; }
        """)

        self.tabs.addTab(SalaryTab(self.user),     "Salary Ranges")
        self.tabs.addTab(IncrementTab(self.user),  "Annual Increment")
        self.tabs.addTab(SecurityTab(self.user),   "Security")
        self.tabs.addTab(DatabaseTab(self.user),   "Database")

        layout.addWidget(self.tabs)


# ── Shared helpers ────────────────────────────────────────────────────────────
INPUT_STYLE  = "QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #111827; background: #f9fafb; min-height: 36px; } QLineEdit:focus { border-color: #2563eb; background: white; }"
SPIN_STYLE   = "QSpinBox, QDoubleSpinBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px; font-size: 13px; color: #111827; background: #f9fafb; min-height: 36px; } QSpinBox:focus, QDoubleSpinBox:focus { border-color: #2563eb; background: white; }"
COMBO_STYLE  = "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; color: #111827; background: #f9fafb; min-height: 36px; }"
SAVE_STYLE   = "QPushButton { background: #2563eb; color: white; border: none; border-radius: 8px; padding: 0 24px; font-size: 13px; font-weight: bold; min-height: 38px; } QPushButton:hover { background: #111827; }"

LEVEL_COLORS = {
    "L7": ("#dbeafe", "#1e40af", "Entry Level (BSc)"),
    "L6": ("#dcfce7", "#166534", "Mid Level (MSc)"),
    "L5": ("#fef9c3", "#854d0e", "Senior Level (PhD)"),
    "L4": ("#f3e8ff", "#6b21a8", "Management Level"),
    "L3": ("#fce7f3", "#9d174d", "Director Level"),
}


def _card(title, subtitle=None):
    card = QFrame()
    card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(24, 18, 24, 20)
    layout.setSpacing(14)
    t_lbl = QLabel(title)
    t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
    layout.addWidget(t_lbl)
    if subtitle:
        s_lbl = QLabel(subtitle)
        s_lbl.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent;")
        layout.addWidget(s_lbl)
    return card, layout


def _lbl(text):
    l = QLabel(text)
    l.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
    return l


def _scroll_wrap(widget):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("border: none;")
    scroll.setWidget(widget)
    return scroll


# ── Salary Ranges Tab ─────────────────────────────────────────────────────────
class SalaryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.fields = {}
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self._load()

    def _build(self):
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 20, 28, 28)
        outer.setSpacing(16)

        # Currency card
        curr_card, curr_layout = _card("Currency", "Currency code shown next to all salary ranges below")
        curr_row = QHBoxLayout()
        curr_row.setSpacing(12)
        curr_row.setAlignment(Qt.AlignLeft)
        curr_lbl = _lbl("Currency Code")
        curr_row.addWidget(curr_lbl)
        self.currency_input = QLineEdit()
        self.currency_input.setFixedWidth(100)
        self.currency_input.setPlaceholderText("e.g. EUR")
        self.currency_input.setStyleSheet(
            "QLineEdit { border: 2px solid #2563eb; border-radius: 8px; padding: 0 12px;"
            " font-size: 14px; font-weight: bold; color: #2563eb; background: #eff6ff;"
            " min-height: 36px; text-align: center; }"
            " QLineEdit:focus { border-color: #1d4ed8; background: white; }"
        )
        curr_row.addWidget(self.currency_input)
        note = QLabel("← editable — applies to all levels")
        note.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent;")
        curr_row.addWidget(note)
        curr_layout.addLayout(curr_row)
        outer.addWidget(curr_card)

        # Level cards
        for level, (bg, fg, label) in LEVEL_COLORS.items():
            card = QFrame()
            card.setStyleSheet(f"background: {bg}40; border-radius: 12px; border: 1px solid {fg}30;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 14, 20, 16)
            cl.setSpacing(10)

            badge = QLabel(f"{level}  —  {label}")
            badge.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {fg}; background: transparent;")
            cl.addWidget(badge)

            row = QHBoxLayout()
            row.setSpacing(0)
            row.setAlignment(Qt.AlignLeft)

            min_col = QVBoxLayout()
            min_col.setSpacing(4)
            min_col.addWidget(_lbl("Minimum Salary"))
            min_spin = QDoubleSpinBox()
            min_spin.setRange(0, 9999999)
            min_spin.setDecimals(0)
            min_spin.setFixedWidth(150)
            min_spin.setStyleSheet(
                f"QDoubleSpinBox {{ border: 1px solid {fg}40; border-right: none;"
                " border-top-left-radius: 8px; border-bottom-left-radius: 8px;"
                " padding: 0 10px; font-size: 13px; color: #111827; background: white; min-height: 38px; }}"
                f" QDoubleSpinBox:focus {{ border-color: {fg}; }}"
            )
            min_col.addWidget(min_spin)
            row.addLayout(min_col)

            curr_badge = QLabel("...")
            curr_badge.setObjectName(f"curr_{level}")
            curr_badge.setFixedHeight(38)
            curr_badge.setFixedWidth(64)
            curr_badge.setAlignment(Qt.AlignCenter)
            curr_badge.setStyleSheet(
                f"background: {fg}18; color: {fg}; font-size: 13px; font-weight: bold;"
                f" border: 1px solid {fg}40; border-left: none; border-right: none;"
                " margin-top: 20px;"
            )
            row.addWidget(curr_badge)
            self._currency_badges = getattr(self, "_currency_badges", {})
            self._currency_badges[level] = curr_badge

            max_col = QVBoxLayout()
            max_col.setSpacing(4)
            max_col.addWidget(_lbl("Maximum Salary"))
            max_spin = QDoubleSpinBox()
            max_spin.setRange(0, 9999999)
            max_spin.setDecimals(0)
            max_spin.setFixedWidth(150)
            max_spin.setStyleSheet(
                f"QDoubleSpinBox {{ border: 1px solid {fg}40; border-left: none;"
                " border-top-right-radius: 8px; border-bottom-right-radius: 8px;"
                " padding: 0 10px; font-size: 13px; color: #111827; background: white; min-height: 38px; }}"
                f" QDoubleSpinBox:focus {{ border-color: {fg}; }}"
            )
            max_col.addWidget(max_spin)
            row.addLayout(max_col)
            row.addStretch()

            cl.addLayout(row)
            outer.addWidget(card)
            self.fields[level] = (min_spin, max_spin)

        self.currency_input.textChanged.connect(self._update_currency_badges)

        # Save
        save_btn = QPushButton("Save Salary Ranges")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(SAVE_STYLE)
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn, alignment=Qt.AlignLeft)
        outer.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_scroll_wrap(content))

    def _update_currency_badges(self, text=None):
        code = (text or self.currency_input.text()).strip() or "—"
        for lbl in getattr(self, "_currency_badges", {}).values():
            lbl.setText(code)

    def _load(self):
        session = get_session()
        try:
            titles = session.query(Title).all()
            for title in titles:
                if title.name in self.fields:
                    mn, mx = self.fields[title.name]
                    mn.setValue(title.base_salary_min)
                    mx.setValue(title.base_salary_max)
                    if hasattr(self, 'currency_input'):
                        self.currency_input.setText(title.currency)
        finally:
            session.close()
        self._update_currency_badges()

    def _save(self):
        session = get_session()
        try:
            currency = self.currency_input.text().strip() or "EUR"
            for level, (mn, mx) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    title.base_salary_min = mn.value()
                    title.base_salary_max = mx.value()
                    title.currency = currency
            log_action(session, self.user.id, "settings.salary_ranges", description="Salary ranges updated")
            session.commit()
            QMessageBox.information(self, t("success"), "Salary ranges saved successfully.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── Annual Increment Tab ──────────────────────────────────────────────────────
class IncrementTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.fields = {}
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self._load()

    def _build(self):
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 20, 28, 28)
        outer.setSpacing(16)

        # Info banner
        info = QFrame()
        info.setStyleSheet("background: #fefce8; border-radius: 10px; border: 1px solid #fde047;")
        il = QVBoxLayout(info)
        il.setContentsMargins(16, 12, 16, 12)
        note = QLabel(t("increment_note"))
        note.setStyleSheet("font-size: 13px; color: #a16207; background: transparent;")
        note.setWordWrap(True)
        il.addWidget(note)
        outer.addWidget(info)

        for level, (bg, fg, label) in LEVEL_COLORS.items():
            card = QFrame()
            card.setStyleSheet(f"background: {bg}40; border-radius: 12px; border: 1px solid {fg}30;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 14, 20, 16)
            cl.setSpacing(10)

            badge = QLabel(f"{level}  —  {label}")
            badge.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {fg}; background: transparent;")
            cl.addWidget(badge)

            row = QHBoxLayout()
            row.setSpacing(16)

            type_col = QVBoxLayout()
            type_col.addWidget(_lbl("Increment Type"))
            type_combo = QComboBox()
            type_combo.setStyleSheet(COMBO_STYLE)
            type_combo.addItem("Percentage (%)", "percentage")
            type_combo.addItem("Fixed Amount", "fixed")
            type_col.addWidget(type_combo)
            row.addLayout(type_col)

            val_col = QVBoxLayout()
            val_col.addWidget(_lbl("Increment Value"))
            val_spin = QDoubleSpinBox()
            val_spin.setRange(0, 9999)
            val_spin.setDecimals(1)
            val_spin.setStyleSheet(SPIN_STYLE)
            val_col.addWidget(val_spin)
            row.addLayout(val_col)
            row.addStretch()

            cl.addLayout(row)
            outer.addWidget(card)
            self.fields[level] = (type_combo, val_spin)

        save_btn = QPushButton("Save Increment Rules")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(SAVE_STYLE)
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn, alignment=Qt.AlignLeft)
        outer.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_scroll_wrap(content))

    def _load(self):
        session = get_session()
        try:
            for level, (type_combo, val_spin) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    idx = type_combo.findData(title.annual_increment_type)
                    if idx >= 0:
                        type_combo.setCurrentIndex(idx)
                    val_spin.setValue(title.annual_increment_value)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            for level, (type_combo, val_spin) in self.fields.items():
                title = session.query(Title).filter_by(name=level).first()
                if title:
                    title.annual_increment_type  = type_combo.currentData()
                    title.annual_increment_value = val_spin.value()
            log_action(session, self.user.id, "settings.increment_rules", description="Annual increment rules updated")
            session.commit()
            QMessageBox.information(self, t("success"), "Annual increment rules saved.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── Security Tab ──────────────────────────────────────────────────────────────
class SecurityTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 20, 28, 28)
        outer.setSpacing(16)

        # Change password card
        pwd_card, pwd_layout = _card("Change Password", "Update your account password")

        pwd_layout.addWidget(_lbl("Current Password"))
        self.current_pwd = QLineEdit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.current_pwd.setStyleSheet(INPUT_STYLE)
        pwd_layout.addWidget(self.current_pwd)

        pwd_layout.addWidget(_lbl("New Password"))
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setStyleSheet(INPUT_STYLE)
        pwd_layout.addWidget(self.new_pwd)

        pwd_layout.addWidget(_lbl("Confirm New Password"))
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setStyleSheet(INPUT_STYLE)
        pwd_layout.addWidget(self.confirm_pwd)

        change_btn = QPushButton("Change Password")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.setStyleSheet(SAVE_STYLE)
        change_btn.clicked.connect(self._change_password)
        pwd_layout.addWidget(change_btn, alignment=Qt.AlignLeft)
        outer.addWidget(pwd_card)

        # Info card
        info_card, info_layout = _card("Security Information")
        for line in [
            "Audit logs are retained indefinitely for compliance",
            "All actions are logged with user identity and timestamp",
            "Employees cannot log in — admin and HR Officer only",
            "Passwords are stored as SHA-256 hashes",
        ]:
            lbl = QLabel(f"• {line}")
            lbl.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent;")
            info_layout.addWidget(lbl)
        outer.addWidget(info_card)
        outer.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_scroll_wrap(content))

    def _change_password(self):
        from hashlib import sha256
        current = self.current_pwd.text()
        new     = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if not current or not new or not confirm:
            QMessageBox.warning(self, t("warning"), "All fields are required.")
            return
        if new != confirm:
            QMessageBox.warning(self, t("warning"), "New passwords do not match.")
            return
        if len(new) < 6:
            QMessageBox.warning(self, t("warning"), "Password must be at least 6 characters.")
            return

        session = get_session()
        try:
            user = session.query(SystemUser).filter_by(id=self.user.id).first()
            if user.password_hash != sha256(current.encode()).hexdigest():
                QMessageBox.critical(self, t("error"), "Current password is incorrect.")
                return
            user.password_hash = sha256(new.encode()).hexdigest()
            log_action(session, self.user.id, "settings.password_change",
                description=f"Password changed for user: {self.user.username}")
            session.commit()
            QMessageBox.information(self, t("success"), "Password changed successfully.")
            self.current_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── Database Tab ──────────────────────────────────────────────────────────────
class DatabaseTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 20, 28, 28)
        outer.setSpacing(16)

        # Backup card
        backup_card, backup_layout = _card("Database Backup", "Create a copy of the database file")
        backup_row = QHBoxLayout()
        backup_info = QLabel("Backs up the SQLite database file (myhr.db) to a location you choose.")
        backup_info.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent;")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        backup_btn = QPushButton("💾  Create Backup")
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.setStyleSheet(SAVE_STYLE)
        backup_btn.clicked.connect(self._backup)
        backup_layout.addWidget(backup_btn, alignment=Qt.AlignLeft)
        outer.addWidget(backup_card)

        # Export card
        export_card, export_layout = _card("Export All Employees", "Export all employee records to CSV")
        export_info = QLabel("Exports a CSV file containing all employee records for reporting or migration.")
        export_info.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent;")
        export_info.setWordWrap(True)
        export_layout.addWidget(export_info)

        export_btn = QPushButton("📤  Export Employees CSV")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(SAVE_STYLE)
        export_btn.clicked.connect(self._export)
        export_layout.addWidget(export_btn, alignment=Qt.AlignLeft)
        outer.addWidget(export_card)

        # Coming soon card
        future_card, future_layout = _card("Coming in Thesis Extension")
        future_card.setStyleSheet("background: #f9fafb; border-radius: 12px; border: 1px dashed #d1d5db;")
        for feat in [
            "Scheduled automatic backups",
            "Yearly reporting summaries (PDF)",
            "Data export by department or date range",
            "Database health check and integrity validation",
        ]:
            lbl = QLabel(f"• {feat}")
            lbl.setStyleSheet("font-size: 13px; color: #9ca3af; background: transparent;")
            future_layout.addWidget(lbl)
        outer.addWidget(future_card)
        outer.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_scroll_wrap(content))

    def _backup(self):
        import shutil
        from src.database.connection import DB_PATH
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", "myhr_backup.db", "SQLite Database (*.db)"
        )
        if not path:
            return
        try:
            shutil.copy2(DB_PATH, path)
            QMessageBox.information(self, t("success"), f"Backup saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Employees", "employees_export.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        session = get_session()
        try:
            from src.database.models import Employee
            employees = session.query(Employee).all()
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "employee_id", "first_name", "last_name", "degree",
                    "position", "level", "department", "base_salary",
                    "status", "join_date", "work_email", "phone"
                ])
                for e in employees:
                    writer.writerow([
                        e.employee_id, e.first_name, e.last_name, e.degree,
                        e.position,
                        e.title.name if e.title else "",
                        e.org_unit.name if e.org_unit else "",
                        e.base_salary, e.status,
                        str(e.join_date.date()) if e.join_date else "",
                        e.work_email or "", e.phone or ""
                    ])
            log_action(session, self.user.id, "settings.export_employees",
                description=f"Employee data exported to CSV: {len(employees)} records")
            session.commit()
            QMessageBox.information(self, t("success"),
                f"Exported {len(employees)} employee records to:\n{path}")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()