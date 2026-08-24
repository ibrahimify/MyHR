"""
Audit Log Page
- Immutable record of all admin/HR actions
- Searchable and filterable
- Shows who, what, when, before/after values
"""

import math
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from html import escape

import qtawesome as qta
from PySide6.QtCore import QMarginsF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QScrollArea, QPushButton, QFileDialog,
    QDialog, QTextEdit, QMessageBox
)
from sqlalchemy import String, cast, func, or_

from src.core.app_settings import company_name, company_subtitle
from src.core.i18n import is_rtl, t
from src.database.connection import get_session, log_action
from src.database.models import (
    AuditLog,
    Commendation,
    Employee,
    OrgUnit,
    PromotionRule,
    SalaryIncrementHistory,
    Sanction,
    SystemUser,
    Title,
)


ACTION_LABEL_KEYS = {
    "employee.create": "audit_action_employee_create",
    "employee.update": "audit_action_employee_update",
    "employee.delete": "audit_action_employee_delete",
    "promotion.approve": "audit_action_promotion_approve",
    "promotion_rule.update": "audit_action_promotion_rule_update",
    "commendation.issue": "audit_action_commendation_issue",
    "sanction.issue": "audit_action_sanction_issue",
    "sanction.resolve": "audit_action_sanction_resolve",
    "import.bulk_employees": "audit_action_import_bulk",
    "settings.salary_ranges": "audit_action_settings_salary",
    "settings.increment_rules": "audit_action_settings_increment",
    "settings.general": "audit_action_settings_general",
    "settings.promotion_rules": "audit_action_settings_promotion",
    "settings.password_change": "audit_action_password_change",
    "settings.export_employees": "audit_action_export_employees",
    "settings.export_yearly_report": "audit_action_export_yearly_report",
    "settings.database_health_check": "audit_action_database_health_check",
    "audit.export": "audit_action_export_audit",
    "audit.export_pdf": "audit_action_export_audit_pdf",
    "settings.level_create": "audit_action_level_create",
    "settings.level_update": "audit_action_level_update",
    "settings.level_delete": "audit_action_level_delete",
    "settings.user_create": "audit_action_user_create",
    "settings.user_update": "audit_action_user_update",
    "settings.user_deactivate": "audit_action_user_deactivate",
    "settings.user_reactivate": "audit_action_user_reactivate",
    "settings.user_delete": "audit_action_user_delete",
    "org_unit.create": "audit_action_org_create",
    "org_unit.update": "audit_action_org_update",
    "org_unit.delete": "audit_action_org_delete",
    "salary_increment.apply": "audit_action_salary_increment",
}

CATEGORY_META = {
    "employee": {"label": "Employee Management", "bg": "#dbeafe", "fg": "#2563eb", "icon": "fa5s.file-alt"},
    "promotion": {"label": "Promotions", "bg": "#dcfce7", "fg": "#16a34a", "icon": "fa5s.chart-line"},
    "commendation": {"label": "Commendations", "bg": "#fef3c7", "fg": "#d97706", "icon": "fa5s.award"},
    "sanction": {"label": "Sanctions", "bg": "#fee2e2", "fg": "#dc2626", "icon": "fa5s.exclamation-triangle"},
    "import": {"label": "Data Import", "bg": "#f3e8ff", "fg": "#9333ea", "icon": "fa5s.upload"},
    "settings": {"label": "Settings", "bg": "#f3f4f6", "fg": "#374151", "icon": "fa5s.cog"},
    "hierarchy": {"label": "Hierarchy", "bg": "#e0e7ff", "fg": "#4f46e5", "icon": "fa5s.sitemap"},
    "salary": {"label": "Salary", "bg": "#f3e8ff", "fg": "#7e22ce", "icon": "fa5s.coins"},
    "other": {"label": "Other", "bg": "#f3f4f6", "fg": "#374151", "icon": "fa5s.clipboard-list"},
}

CATEGORY_LABEL_KEYS = {
    "employee": "employee_management",
    "promotion": "promotions_title",
    "commendation": "commendations",
    "sanction": "sanctions",
    "import": "data_import",
    "settings": "settings_title",
    "hierarchy": "hierarchy",
    "salary": "salary",
    "other": "other",
}

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

INPUT_SS = """
QLineEdit {
    border: none;
    border-radius: 8px;
    padding: 0 16px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    selection-background-color: #2563eb;
    outline: none;
}
QLineEdit:focus {
    background: white;
    border: 1px solid #2563eb;
}
"""

COMBO_SS = """
QComboBox {
    border: none;
    border-radius: 8px;
    padding: 0 36px 0 16px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    min-height: 40px;
    outline: none;
}
QComboBox:focus { border: 1px solid #2563eb; background: white; }
QComboBox::drop-down { width: 32px; border: none; background: transparent; }
QComboBox::down-arrow { image: url(src/ui/assets/chevron_down.svg); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background: white;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 0;
    selection-background-color: #eff6ff;
    selection-color: #111827;
    outline: none;
    padding: 4px;
}
"""

TABLE_SS = """
QTableWidget {
    background: white;
    alternate-background-color: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 14px;
    color: #111827;
    outline: none;
    selection-background-color: #eff6ff;
}
QTableWidget::item {
    background: white;
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
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
QTableCornerButton::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}
QToolTip {
    background-color: #111827;
    color: white;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 6px 8px;
}
"""


class AuditLogPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.all_logs = []
        self.filtered_logs = []
        self.current_page = 1
        self.page_size = 50
        self.total_pages = 1
        self.stat_values = {}
        self._target_session = None
        self.setObjectName("AuditLogPage")
        self.setStyleSheet("QWidget#AuditLogPage { background: #f9fafb; }")
        self._build()
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("audit_title"))
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel(t("audit_subtitle"))
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(20)
        self._add_stat_card("total", t("total_logs"), "fa5s.file-alt", "#2563eb", "#dbeafe")
        self._add_stat_card("today", t("todays_activities"), "fa5s.user", "#16a34a", "#dcfce7")
        self._add_stat_card("week", t("this_week"), "fa5s.calendar-alt", "#9333ea", "#f3e8ff")
        self._add_stat_card("active_user", t("most_active_user"), "fa5s.clipboard-list", "#d97706", "#fef3c7")
        layout.addLayout(self.stats_row)
        layout.addSpacing(30)

        filter_card = QFrame()
        filter_card.setObjectName("Card")
        filter_card.setStyleSheet(CARD_SS)
        fl = QGridLayout(filter_card)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setHorizontalSpacing(14)
        fl.setVerticalSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_logs"))
        self.search.setFixedHeight(44)
        self.search.setMinimumWidth(360)
        self.search.setStyleSheet(INPUT_SS)
        self.search.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._filter)
        fl.addWidget(self.search, 0, 0, 1, 4)

        self.search_btn = QPushButton(t("search"))
        self.search_btn.setFixedHeight(44)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setIcon(qta.icon("fa5s.search", color="white"))
        self.search_btn.setStyleSheet(
            "QPushButton { background: #020617; color: white; border: 1px solid #020617; "
            "border-radius: 8px; padding: 0 18px; font-size: 13px; font-weight: 800; }"
            "QPushButton:hover { background: #111827; }"
        )
        self.search_btn.clicked.connect(self._filter)
        fl.addWidget(self.search_btn, 0, 4)

        self.export_csv_btn = QPushButton(t("export_csv"))
        self.export_csv_btn.setFixedHeight(44)
        self.export_csv_btn.setCursor(Qt.PointingHandCursor)
        self.export_csv_btn.setIcon(qta.icon("fa5s.download", color="#111827"))
        self.export_csv_btn.setStyleSheet(
            "QPushButton { background: white; color: #111827; border: 1px solid #d1d5db; "
            "border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 800; }"
            "QPushButton:hover { background: #f9fafb; }"
        )
        self.export_csv_btn.clicked.connect(self._export_current_view)
        fl.addWidget(self.export_csv_btn, 0, 5)

        self.export_pdf_btn = QPushButton(t("export_pdf"))
        self.export_pdf_btn.setFixedHeight(44)
        self.export_pdf_btn.setCursor(Qt.PointingHandCursor)
        self.export_pdf_btn.setIcon(qta.icon("fa5s.file-pdf", color="#111827"))
        self.export_pdf_btn.setStyleSheet(
            "QPushButton { background: white; color: #111827; border: 1px solid #d1d5db; "
            "border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 800; }"
            "QPushButton:hover { background: #f9fafb; }"
        )
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        fl.addWidget(self.export_pdf_btn, 0, 6)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(44)
        self.category_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.category_filter)
        self.category_filter.addItem(t("all_categories"), None)
        for key, meta in CATEGORY_META.items():
            if key != "other":
                self.category_filter.addItem(_category_label(key), key)
        self.category_filter.addItem(t("other"), "other")
        self.category_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.category_filter, 1, 0)

        self.target_filter = QComboBox()
        self.target_filter.setFixedHeight(44)
        self.target_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.target_filter)
        self.target_filter.addItem(t("all_targets"), None)
        self.target_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.target_filter, 1, 1)

        self.date_filter = QComboBox()
        self.date_filter.setFixedHeight(44)
        self.date_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.date_filter)
        self.date_filter.addItem(t("all_dates"), "all")
        self.date_filter.addItem(t("today"), "today")
        self.date_filter.addItem(t("last_7_days"), "last_7")
        self.date_filter.addItem(t("last_30_days"), "last_30")
        self.date_filter.addItem(t("this_year"), "this_year")
        self.date_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.date_filter, 1, 2)

        self.user_filter = QComboBox()
        self.user_filter.setFixedHeight(44)
        self.user_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.user_filter)
        self.user_filter.addItem(t("all_users"), None)
        self.user_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.user_filter, 1, 3, 1, 4)

        for col in range(7):
            fl.setColumnStretch(col, 1)
        fl.setColumnStretch(0, 2)
        fl.setColumnStretch(1, 2)
        fl.setColumnStretch(2, 2)
        fl.setColumnStretch(3, 2)

        layout.addWidget(filter_card)
        layout.addSpacing(26)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size: 14px; color: #4b5563; background: transparent;")
        layout.addWidget(self.count_lbl)
        layout.addSpacing(18)

        table_card = QFrame()
        table_card.setObjectName("Card")
        table_card.setStyleSheet(CARD_SS)
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("timestamp"), t("user"), t("action"), t("target"), t("details"), t("category")
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 190)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.cellDoubleClicked.connect(self._open_log_details)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tl.addWidget(self.table)
        tl.addWidget(self._pager())
        layout.addWidget(table_card)
        layout.addSpacing(30)

        info_card = QFrame()
        info_card.setStyleSheet(
            "QFrame { background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; } "
            "QLabel { background: transparent; border: none; }"
        )
        il = QVBoxLayout(info_card)
        il.setContentsMargins(30, 28, 30, 28)
        il.setSpacing(12)

        info_head = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(qta.icon("fa5s.clipboard-list", color="#2563eb").pixmap(18, 18))
        info_title = QLabel(t("audit_log_information"))
        info_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #1e40af; background: transparent;")
        info_head.addWidget(info_icon)
        info_head.addWidget(info_title)
        info_head.addStretch()
        il.addLayout(info_head)

        for text in [
            t("audit_info_auto_logged"),
            t("audit_info_immutable"),
            t("audit_info_identity"),
            t("audit_info_retained"),
            t("audit_info_double_click"),
        ]:
            item = QLabel("&bull; " + text)
            item.setTextFormat(Qt.RichText)
            item.setStyleSheet("font-size: 14px; color: #1d4ed8; background: transparent;")
            il.addWidget(item)
        layout.addWidget(info_card)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _add_stat_card(self, key, label, icon_name, color, bg):
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedHeight(96)
        card.setStyleSheet(CARD_SS)
        cl = QHBoxLayout(card)
        cl.setContentsMargins(30, 0, 30, 0)
        cl.setSpacing(14)

        icon = QLabel()
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: {bg}; border-radius: 8px;")
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))

        col = QVBoxLayout()
        col.setSpacing(0)
        col.setAlignment(Qt.AlignVCenter)
        title = QLabel(label)
        title.setStyleSheet("font-size: 14px; color: #374151; background: transparent;")
        value = QLabel("0")
        value.setStyleSheet("font-size: 24px; font-weight: 800; color: #030213; background: transparent;")
        col.addWidget(title)
        col.addWidget(value)

        cl.addWidget(icon)
        cl.addLayout(col)
        self.stats_row.addWidget(card)
        self.stat_values[key] = value

    def refresh(self):
        self.current_page = 1
        session = get_session()
        try:
            users = self._load_user_filter_values(session)
            targets = self._load_target_filter_values(session)
            current_user = self.user_filter.currentData()
            current_target = self.target_filter.currentData()
            self.user_filter.blockSignals(True)
            self.user_filter.clear()
            self.user_filter.addItem(t("all_users"), None)
            for name in users:
                self.user_filter.addItem(name, name)
            if current_user in users:
                self.user_filter.setCurrentText(current_user)
            self.user_filter.blockSignals(False)
            self.target_filter.blockSignals(True)
            self.target_filter.clear()
            self.target_filter.addItem(t("all_targets"), None)
            for value, label in targets:
                self.target_filter.addItem(label, value)
            if current_target in [value for value, _ in targets]:
                self.target_filter.setCurrentIndex(self.target_filter.findData(current_target))
            self.target_filter.blockSignals(False)
        finally:
            session.close()

        self._update_stats()
        self._filter()

    def _load_user_filter_values(self, session):
        rows = (
            session.query(AuditLog.performed_by_username, AuditLog.performed_by_name)
            .filter(AuditLog.performed_at <= datetime.utcnow())
            .distinct()
            .all()
        )
        names = []
        for username, full_name in rows:
            display = _user_display_from_snapshot(username, full_name)
            if display != "System":
                names.append(display)
        return sorted(set(names))

    def _load_target_filter_values(self, session):
        rows = (
            session.query(AuditLog.target_table)
            .filter(AuditLog.performed_at <= datetime.utcnow())
            .filter(AuditLog.target_table.isnot(None))
            .distinct()
            .all()
        )
        values = sorted({row[0] for row in rows if row[0]})
        return [(value, _target_table_label(value)) for value in values]

    def _serialize_log(self, log):
        action = log.action or "other"
        category = _category_for_action(action)

        return {
            "id": log.id,
            "timestamp": log.performed_at.strftime("%Y-%m-%d %H:%M:%S") if log.performed_at else "-",
            "date": log.performed_at.date() if log.performed_at else None,
            "user": _user_display(log),
            "user_name": log.performed_by_name or (log.performed_by.full_name if log.performed_by else "System"),
            "action": _action_label(action),
            "raw_action": action,
            "details": log.description or "-",
            "category": category,
            "target": _resolve_target(self._target_session, log),
            "before": log.before_value or "",
            "after": log.after_value or "",
        }

    def _update_stats(self):
        session = get_session()
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=6)
            base = session.query(AuditLog).filter(AuditLog.performed_at <= now)
            total = base.count()
            today_count = base.filter(AuditLog.performed_at >= today_start).count()
            week_count = base.filter(AuditLog.performed_at >= week_start).count()
            active_row = (
                session.query(
                    AuditLog.performed_by_username,
                    AuditLog.performed_by_name,
                    func.count(AuditLog.id).label("activity_count"),
                )
                .filter(AuditLog.performed_at <= now)
                .group_by(AuditLog.performed_by_username, AuditLog.performed_by_name)
                .order_by(func.count(AuditLog.id).desc())
                .first()
            )
            most_active = _user_display_from_snapshot(active_row[0], active_row[1]) if active_row else "-"
        finally:
            session.close()

        self.stat_values["total"].setText(str(total))
        self.stat_values["today"].setText(str(today_count))
        self.stat_values["week"].setText(str(week_count))
        self.stat_values["active_user"].setText(most_active)
        self.stat_values["active_user"].setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #030213; background: transparent;"
        )

    def _filter(self):
        self.current_page = 1
        self._load_page()

    def _populate_page(self):
        self._load_page()

    def _filtered_query(self, session):
        query = session.query(AuditLog).filter(AuditLog.performed_at <= datetime.utcnow())
        search = self.search.text().strip().lower()
        if search:
            pattern = f"%{search}%"
            target_text = func.coalesce(AuditLog.target_table, "") + " #" + func.coalesce(cast(AuditLog.target_id, String), "")
            query = query.filter(or_(
                func.lower(AuditLog.action).like(pattern),
                func.lower(func.coalesce(AuditLog.description, "")).like(pattern),
                func.lower(func.coalesce(AuditLog.target_table, "")).like(pattern),
                func.lower(target_text).like(pattern),
                func.lower(func.coalesce(AuditLog.performed_by_username, "")).like(pattern),
                func.lower(func.coalesce(AuditLog.performed_by_name, "")).like(pattern),
            ))

        category = self.category_filter.currentData()
        category_filter = _category_filter(AuditLog.action, category)
        if category_filter is not None:
            query = query.filter(category_filter)

        date_range = self.date_filter.currentData() if hasattr(self, "date_filter") else "all"
        start_at = _date_range_start(date_range)
        if start_at:
            query = query.filter(AuditLog.performed_at >= start_at)

        user = self.user_filter.currentData()
        if user:
            query = query.filter(
                (func.coalesce(AuditLog.performed_by_username, "") + ": " + func.coalesce(AuditLog.performed_by_name, "")) == user
            )
        target = self.target_filter.currentData()
        if target:
            query = query.filter(AuditLog.target_table == target)
        return query

    def _load_page(self):
        session = get_session()
        try:
            query = self._filtered_query(session)
            total = query.count()
            self.total_pages = max(1, math.ceil(total / self.page_size))
            self.current_page = max(1, min(self.current_page, self.total_pages))
            start = (self.current_page - 1) * self.page_size
            logs = (
                query
                .order_by(AuditLog.performed_at.desc(), AuditLog.id.desc())
                .offset(start)
                .limit(self.page_size)
                .all()
            )
            self._target_session = session
            page_rows = [self._serialize_log(log) for log in logs]
        finally:
            self._target_session = None
            session.close()

        start = (self.current_page - 1) * self.page_size
        shown = f"{start + 1}-{start + len(page_rows)}" if page_rows else "0"
        self.count_lbl.setText(t("showing_logs", shown=shown, total=total))
        self.page_lbl.setText(t("page_status", page=self.current_page, pages=self.total_pages))
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        self._populate(page_rows)

    def _previous_page(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self._populate_page()

    def _next_page(self):
        if self.current_page >= self.total_pages:
            return
        self.current_page += 1
        self._populate_page()

    def _populate(self, logs):
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(logs))
        row_height = 56
        header_height = 52
        self.table.setFixedHeight(max(620, header_height + (len(logs) * row_height) + 4))

        try:
            for row_index, log in enumerate(logs):
                self.table.setRowHeight(row_index, row_height)

                timestamp = QTableWidgetItem(log["timestamp"])
                timestamp.setForeground(QColor("#374151"))
                timestamp.setToolTip(log["timestamp"])
                timestamp.setData(Qt.UserRole, log["id"])
                self.table.setItem(row_index, 0, timestamp)

                user_item = QTableWidgetItem(log["user"])
                user_item.setIcon(qta.icon("fa5s.user", color="#2563eb"))
                user_font = user_item.font()
                user_font.setBold(True)
                user_item.setFont(user_font)
                user_item.setToolTip(log.get("user_name") or log["user"])
                self.table.setItem(row_index, 1, user_item)

                action_item = QTableWidgetItem(log["action"])
                action_font = action_item.font()
                action_font.setBold(True)
                action_item.setFont(action_font)
                action_item.setToolTip(log["raw_action"])
                self.table.setItem(row_index, 2, action_item)

                target_item = QTableWidgetItem(log["target"])
                target_item.setForeground(QColor("#374151"))
                target_item.setToolTip(log["target"])
                self.table.setItem(row_index, 3, target_item)

                details = log["details"]
                details_item = QTableWidgetItem(details[:90] + "..." if len(details) > 90 else details)
                details_item.setForeground(QColor("#374151"))
                details_item.setToolTip(details)
                self.table.setItem(row_index, 4, details_item)

                self.table.setCellWidget(row_index, 5, _category_badge(log["category"]))
        finally:
            self.table.setUpdatesEnabled(True)

    def _open_log_details(self, row, _column):
        item = self.table.item(row, 0)
        if not item:
            return
        log_id = item.data(Qt.UserRole)
        if not log_id:
            return
        session = get_session()
        try:
            log = session.query(AuditLog).filter_by(id=log_id).first()
            if not log:
                return
            self._target_session = session
            data = self._serialize_log(log)
        finally:
            self._target_session = None
            session.close()
        AuditDetailDialog(data, self).exec()

    def _export_rows(self, session):
        logs = (
            self._filtered_query(session)
            .order_by(AuditLog.performed_at.desc(), AuditLog.id.desc())
            .all()
        )
        self._target_session = session
        try:
            return [self._serialize_log(log) for log in logs]
        finally:
            self._target_session = None

    def _export_current_view(self):
        path, _ = QFileDialog.getSaveFileName(self, t("export_audit"), "audit_log_export.csv", t("csv_files_filter"))
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        session = get_session()
        try:
            rows = self._export_rows(session)
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "Timestamp",
                    "User",
                    "Action",
                    "Action Code",
                    "Target",
                    "Details",
                    "Category",
                    "Changes",
                    "Before",
                    "After",
                ])
                for row in rows:
                    writer.writerow([
                        row["timestamp"],
                        row["user"],
                        row["action"],
                        row["raw_action"],
                        row["target"],
                        row["details"],
                        _category_label(row["category"]),
                        _format_diff_for_export(row["before"], row["after"]),
                        _format_snapshot_for_export(row["before"]),
                        _format_snapshot_for_export(row["after"]),
                    ])
            log_action(
                session,
                action="audit.export",
                performed_by_id=self.user.id,
                description=f"Audit log exported to CSV: {len(rows)} records",
                after_value=json.dumps(
                    {"count": len(rows), "path": path, "scope": self._export_scope_text()},
                    ensure_ascii=False,
                ),
            )
            session.commit()
            _info(self, t("success"), t("audit_exported_to", count=len(rows), path=path))
            self.refresh()
        except Exception as exc:
            session.rollback()
            _error(self, t("error"), str(exc))
        finally:
            self._target_session = None
            session.close()

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, t("export_audit_pdf"), "audit_log_report.pdf", t("pdf_files_filter"))
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        session = get_session()
        try:
            rows = self._export_rows(session)
            scope = self._export_scope_text()
            generated_at = datetime.utcnow()
            html = _build_audit_pdf_html(rows, scope, generated_at, self.user)
            _write_audit_pdf(path, html)
            log_action(
                session,
                action="audit.export_pdf",
                performed_by_id=self.user.id,
                description=f"Audit log exported to PDF: {len(rows)} records",
                after_value=json.dumps(
                    {"count": len(rows), "path": path, "scope": scope},
                    ensure_ascii=False,
                ),
            )
            session.commit()
            _info(self, t("success"), t("audit_pdf_exported_to", count=len(rows), path=path))
            self.refresh()
        except Exception as exc:
            session.rollback()
            _error(self, t("error"), str(exc))
        finally:
            self._target_session = None
            session.close()

    def _export_scope_text(self):
        parts = []
        search = self.search.text().strip()
        if search:
            parts.append(f"{t('search')}: {search}")
        for label_key, combo in [
            ("category", self.category_filter),
            ("target", self.target_filter),
            ("date", self.date_filter),
            ("user", self.user_filter),
        ]:
            data = combo.currentData()
            if data is None or data == "all":
                continue
            parts.append(f"{t(label_key)}: {combo.currentText()}")
        return "; ".join(parts) if parts else t("all_audit_records")

    def _pager(self):
        pager = QFrame()
        pager.setStyleSheet("background: white; border: none; border-top: 1px solid #f3f4f6;")
        layout = QHBoxLayout(pager)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent;")

        btn_ss = (
            "QPushButton { background: white; color: #111827; border: 1px solid #d1d5db;"
            " border-radius: 6px; font-size: 13px; font-weight: 700; padding: 0 14px; }"
            " QPushButton:hover { background: #f9fafb; }"
            " QPushButton:disabled { color: #9ca3af; background: #f9fafb; }"
        )
        self.prev_btn = QPushButton(t("previous_page"))
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(btn_ss)
        self.prev_btn.clicked.connect(self._previous_page)

        self.next_btn = QPushButton(t("next_page"))
        self.next_btn.setFixedHeight(34)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(btn_ss)
        self.next_btn.clicked.connect(self._next_page)

        layout.addStretch()
        layout.addWidget(self.page_lbl)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        return pager

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)


def _build_audit_pdf_html(rows, scope, generated_at, user):
    generated = generated_at.strftime("%Y-%m-%d %H:%M")
    generated_by = _user_display_from_snapshot(
        getattr(user, "username", ""),
        getattr(user, "full_name", ""),
    )
    direction = "rtl" if is_rtl() else "ltr"
    align = "right" if is_rtl() else "left"
    opposite_align = "left" if is_rtl() else "right"
    category_counts = Counter(_category_label(row["category"]) for row in rows)
    category_rows = "".join(
        f"<tr><td>{_html(category)}</td><td>{count}</td></tr>"
        for category, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
    ) or f"<tr><td>{_html(t('no_data'))}</td><td>0</td></tr>"
    record_rows = "".join(_audit_pdf_row(row) for row in rows) or (
        "<tr>"
        f"<td colspan=\"6\">{_html(t('audit_pdf_no_records'))}</td>"
        "</tr>"
    )
    return f"""
<!doctype html>
<html dir="{direction}">
<head>
<meta charset="utf-8">
<style>
body {{
    color: #1f2937;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 7.4pt;
    line-height: 1.25;
    margin: 0;
    background: #ffffff;
}}
html {{
    background: #ffffff;
}}
h1, h2 {{
    color: #111827;
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 700;
}}
.cover {{
    border-bottom: 2px solid #1f3a5f;
    margin-bottom: 10px;
    padding-bottom: 8px;
}}
.masthead {{
    color: #6b7280;
    font-size: 7pt;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.company {{
    color: #111827;
    font-size: 10pt;
    font-weight: 700;
    margin-top: 3px;
}}
.subtitle {{
    color: #4b5563;
    font-size: 7.5pt;
}}
h1 {{
    font-size: 18pt;
    margin: 16px 0 3px;
}}
.generated {{
    color: #1f3a5f;
    font-size: 8pt;
    margin-bottom: 6px;
}}
.summary {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 10px;
}}
.summary td {{
    border: 1px solid #d8dee7;
    padding: 6px 8px;
    vertical-align: top;
}}
.label {{
    color: #6b7280;
    font-size: 6.8pt;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}
.value {{
    color: #111827;
    font-size: 8.5pt;
    font-weight: 700;
    margin-top: 2px;
}}
.section-title {{
    color: #111827;
    font-size: 10pt;
    margin: 10px 0 5px;
}}
table.data {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}}
table.data th {{
    background: #f3f4f6;
    border-bottom: 1px solid #1f3a5f;
    color: #111827;
    font-size: 6.8pt;
    font-weight: 700;
    padding: 5px 6px;
    text-align: {align};
}}
table.data td {{
    border-bottom: 1px solid #e5e7eb;
    color: #1f2937;
    padding: 5px 6px;
    vertical-align: top;
    word-wrap: break-word;
}}
table.data tr:nth-child(even) td {{
    background: #fafafa;
}}
.small {{
    color: #4b5563;
    font-size: 7.5pt;
}}
.footer {{
    border-top: 1px solid #d8dee7;
    color: #6b7280;
    font-size: 6.8pt;
    margin-top: 12px;
    padding-top: 6px;
    text-align: {opposite_align};
}}
</style>
</head>
<body>
    <div class="cover">
        <div class="masthead">{_html(t("audit_pdf_title"))}</div>
        <div class="company">{_html(company_name("MyHR"))}</div>
        <div class="subtitle">{_html(company_subtitle("Employee Management"))}</div>
        <h1>{_html(t("audit_pdf_title"))}</h1>
        <div class="generated">{_html(t("generated_on", value=generated))}</div>
    </div>
    <table class="summary">
        <tr>
            <td><div class="label">{_html(t("audit_pdf_total_records"))}</div><div class="value">{len(rows)}</div></td>
            <td><div class="label">{_html(t("audit_pdf_generated_by"))}</div><div class="value">{_html(generated_by)}</div></td>
            <td><div class="label">{_html(t("audit_pdf_scope"))}</div><div class="value">{_html(scope)}</div></td>
        </tr>
    </table>
    <h2 class="section-title">{_html(t("audit_pdf_category_summary"))}</h2>
    <table class="data">
        <tr><th>{_html(t("category"))}</th><th>{_html(t("events"))}</th></tr>
        {category_rows}
    </table>
    <h2 class="section-title">{_html(t("audit_pdf_records"))}</h2>
    <table class="data">
        <tr>
            <th style="width: 12%;">{_html(t("timestamp"))}</th>
            <th style="width: 16%;">{_html(t("user"))}</th>
            <th style="width: 15%;">{_html(t("action"))}</th>
            <th style="width: 18%;">{_html(t("target"))}</th>
            <th style="width: 12%;">{_html(t("category"))}</th>
            <th style="width: 27%;">{_html(t("changes"))}</th>
        </tr>
        {record_rows}
    </table>
    <div class="footer">{_html(t("report_footer_note"))}</div>
</body>
</html>
"""


def _audit_pdf_row(row):
    changes = _format_diff_for_export(row["before"], row["after"]) or row["details"] or t("not_available")
    return (
        "<tr>"
        f"<td>{_html(row['timestamp'])}</td>"
        f"<td>{_html(row['user'])}</td>"
        f"<td>{_html(row['action'])}</td>"
        f"<td>{_html(row['target'])}</td>"
        f"<td>{_html(_category_label(row['category']))}</td>"
        f"<td>{_html(changes)}</td>"
        "</tr>"
    )


def _write_audit_pdf(path, html):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.A4),
        QPageLayout.Landscape,
        QMarginsF(10, 10, 10, 10),
        QPageLayout.Millimeter,
    ))
    document = QTextDocument()
    document.setDefaultFont(QFont("Segoe UI", 9))
    document.setPageSize(printer.pageLayout().paintRectPoints().size())
    document.setHtml(html)
    document.print_(printer)


def _html(value):
    return escape(str(value or "-")).replace("\n", "<br>")


class AuditDetailDialog(QDialog):
    def __init__(self, log, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("audit_detail_title"))
        self.setMinimumSize(760, 620)
        self.setStyleSheet("QDialog { background: white; color: #111827; } QLabel { background: transparent; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: #eff6ff; border-radius: 8px;")
        icon.setPixmap(qta.icon("fa5s.clipboard-list", color="#2563eb").pixmap(18, 18))
        titles = QVBoxLayout()
        title = QLabel(t("audit_detail_title"))
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #030213;")
        subtitle = QLabel(t("audit_detail_subtitle"))
        subtitle.setStyleSheet("font-size: 13px; color: #4b5563;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addWidget(icon)
        header.addLayout(titles)
        header.addStretch()
        layout.addLayout(header)

        meta = QFrame()
        meta.setObjectName("Card")
        meta.setStyleSheet(CARD_SS)
        grid = QVBoxLayout(meta)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setSpacing(8)
        for label, value in [
            (t("timestamp"), log["timestamp"]),
            (t("user"), log["user"]),
            (t("action"), log["raw_action"]),
            (t("target"), log["target"]),
            (t("category"), _category_label(log["category"])),
            (t("details"), log["details"]),
        ]:
            grid.addLayout(_detail_line(label, value))
        layout.addWidget(meta)

        layout.addWidget(_diff_box(t("changes"), log["before"], log["after"]))

        changes = QHBoxLayout()
        changes.setSpacing(14)
        changes.addWidget(_snapshot_box(t("before_value"), log["before"]))
        changes.addWidget(_snapshot_box(t("after_value"), log["after"]))
        layout.addLayout(changes, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton(t("close"))
        close.setFixedHeight(38)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet(
            "QPushButton { background: #030213; color: white; border: none; border-radius: 8px; "
            "font-size: 13px; font-weight: 800; padding: 0 18px; }"
            "QPushButton:hover { background: #111827; }"
        )
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)


def _detail_line(label, value):
    row = QHBoxLayout()
    row.setSpacing(10)
    left = QLabel(label)
    left.setFixedWidth(130)
    left.setStyleSheet("font-size: 12px; font-weight: 900; color: #4b5563;")
    right = QLabel(str(value or "-"))
    right.setWordWrap(True)
    right.setStyleSheet("font-size: 13px; color: #111827;")
    row.addWidget(left)
    row.addWidget(right, 1)
    return row


def _snapshot_box(title, value):
    box = QFrame()
    box.setObjectName("Card")
    box.setStyleSheet(CARD_SS)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    label = QLabel(title)
    label.setStyleSheet("font-size: 13px; font-weight: 900; color: #030213;")
    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(_format_snapshot(value))
    text.setStyleSheet(
        "QTextEdit { background: #f9fafb; color: #111827; border: 1px solid #e5e7eb; "
        "border-radius: 8px; padding: 10px; font-size: 12px; }"
    )
    layout.addWidget(label)
    layout.addWidget(text, 1)
    return box


def _diff_box(title, before, after):
    box = QFrame()
    box.setObjectName("Card")
    box.setStyleSheet(CARD_SS)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(8)
    label = QLabel(title)
    label.setStyleSheet("font-size: 13px; font-weight: 900; color: #030213;")
    layout.addWidget(label)
    text = QLabel(_format_diff(before, after))
    text.setWordWrap(True)
    text.setStyleSheet(
        "font-size: 12px; color: #374151; background: #f9fafb; border: 1px solid #e5e7eb; "
        "border-radius: 8px; padding: 10px;"
    )
    layout.addWidget(text)
    return box


def _format_diff(before, after):
    before_payload = _json_dict(before)
    after_payload = _json_dict(after)
    if not before_payload and not after_payload:
        return t("not_available")
    if not before_payload:
        summary = _format_snapshot_pairs(after_payload, include_path=False)
        return f"Recorded: {summary}" if summary else t("no_changes_detected")
    if not after_payload:
        summary = _format_snapshot_pairs(before_payload, include_path=False)
        return f"Previous record: {summary}" if summary else t("no_changes_detected")
    keys = sorted(set(before_payload) | set(after_payload))
    changes = []
    for key in keys:
        old = before_payload.get(key, "-")
        new = after_payload.get(key, "-")
        if old != new:
            label = _audit_field_label(key)
            changes.append(f"{label}: {_export_value(old, key)} -> {_export_value(new, key)}")
    return "\n".join(changes) if changes else t("no_changes_detected")


def _format_snapshot(value):
    if not value:
        return t("not_available")
    try:
        return json.dumps(json.loads(value), indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _format_snapshot_for_export(value):
    if not value:
        return ""
    payload = _json_dict(value)
    if payload:
        return _format_snapshot_pairs(payload)
    return str(value)


def _format_diff_for_export(before, after):
    diff = _format_diff(before, after)
    if diff == t("not_available"):
        return ""
    return diff.replace("\n", "; ")


def _export_value(value, key=None):
    if _is_blank_audit_value(value):
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value)
    if key in {"report_type", "status"}:
        return text.replace("_", " ").title()
    if "_" in text and len(text.split()) == 1:
        return text.replace("_", " ").title()
    return text


def _format_snapshot_pairs(payload, include_path=True):
    pairs = []
    for key, value in payload.items():
        if key == "path" and not include_path:
            continue
        if str(key).endswith("_id") and key != "employee_id":
            continue
        if _is_blank_audit_value(value):
            continue
        pairs.append(f"{_audit_field_label(key)}: {_export_value(value, key)}")
    return "; ".join(pairs)


def _audit_field_label(key):
    labels = {
        "base_salary": "Base Salary",
        "base_salary_min": "Minimum Salary",
        "base_salary_max": "Maximum Salary",
        "employee_id": "Employee ID",
        "full_name": "Full Name",
        "is_active": "Active",
        "org_unit_id": "Org Unit Filter",
        "performed_by_id": "Performed By",
        "report_type": "Report Type",
        "salary_max": "Maximum Salary",
        "salary_min": "Minimum Salary",
        "target_id": "Target ID",
        "title_id": "Level Filter",
    }
    return labels.get(str(key), str(key).replace("_", " ").title())


def _is_blank_audit_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "none", "null", "-"}
    return False


def _resolve_target(session, log):
    table = (log.target_table or "").strip().lower()
    target_id = log.target_id
    action_label = _target_from_action(log)
    if not table:
        return action_label or "-"

    snapshot_label = _target_from_snapshot(table, log)
    if table in {"title", "system_user"} and snapshot_label:
        return snapshot_label

    if session is not None and target_id:
        current_label = _target_from_database(session, table, target_id)
        if current_label:
            return current_label

    if snapshot_label:
        return snapshot_label

    description_label = _target_from_description(log)
    if description_label:
        return description_label

    if action_label:
        return action_label

    label = _target_table_label(table)
    return f"{label} #{target_id}" if target_id else label


def _target_from_action(log):
    action = log.action or ""
    payload = _json_dict(log.after_value) or _json_dict(log.before_value)
    if action == "settings.export_yearly_report":
        year = payload.get("year") or _first_number(log.description)
        return t("target_yearly_report_for_year", year=year) if year else t("target_yearly_report")
    mapping = {
        "audit.export": "target_audit_log",
        "audit.export_pdf": "target_audit_log",
        "settings.database_health_check": "target_database",
        "settings.promotion_rules": "target_promotion_policies",
        "settings.salary_ranges": "target_salary_ranges",
        "settings.increment_rules": "target_annual_increment_rules",
        "settings.general": "target_organization_settings",
        "settings.export_employees": "target_employee_export",
        "settings.password_change": "target_user_security",
    }
    key = mapping.get(action)
    return t(key) if key else ""


def _target_from_database(session, table, target_id):
    if table == "employee":
        employee = session.query(Employee).filter_by(id=target_id).first()
        if employee:
            return f"{employee.employee_id} - {employee.full_name}"
    if table == "title":
        title = session.query(Title).filter_by(id=target_id).first()
        if title:
            return _join_target_parts(title.name, title.label)
    if table == "org_unit":
        unit = session.query(OrgUnit).filter_by(id=target_id).first()
        if unit:
            unit_type = (unit.unit_type or "").replace("_", " ").title()
            return f"{unit.name} ({unit_type})" if unit_type else unit.name
    if table == "promotion_rule":
        rule = session.query(PromotionRule).filter_by(id=target_id).first()
        if rule and rule.from_title and rule.to_title:
            return f"{rule.from_title.name} -> {rule.to_title.name} ({rule.base_months} mo)"
    if table == "commendation":
        commendation = session.query(Commendation).filter_by(id=target_id).first()
        if commendation:
            return _join_target_parts(commendation.commendation_ref, commendation.title)
    if table == "sanction":
        sanction = session.query(Sanction).filter_by(id=target_id).first()
        if sanction:
            employee_name = sanction.employee.full_name if sanction.employee else ""
            return _join_target_parts(sanction.sanction_ref, employee_name)
    if table == "salary_increment_history":
        increment = session.query(SalaryIncrementHistory).filter_by(id=target_id).first()
        if increment and increment.employee:
            return f"{increment.employee.employee_id} - {increment.employee.full_name}"
    if table == "system_user":
        user = session.query(SystemUser).filter_by(id=target_id).first()
        if user:
            return _user_display_from_snapshot(user.username, user.full_name)
    return ""


def _target_from_snapshot(table, log):
    payload = _json_dict(log.after_value) or _json_dict(log.before_value)
    if not payload:
        return ""
    if table == "title":
        return _join_target_parts(payload.get("name"), payload.get("label"))
    if table == "system_user":
        return _user_display_from_snapshot(payload.get("username"), payload.get("full_name"))
    return ""


def _target_from_description(log):
    description = (log.description or "").strip()
    prefixes = [
        "Level created:",
        "Level updated:",
        "Level deleted:",
        "Org unit saved:",
        "Org unit deleted:",
        "User account updated:",
        "HR account created:",
        "HR login deleted:",
    ]
    for prefix in prefixes:
        if description.startswith(prefix):
            return description[len(prefix):].strip()
    return ""


def _target_table_label(table):
    labels = {
        "employee": "Employee",
        "title": "Level",
        "org_unit": "Org Unit",
        "promotion_rule": "Promotion Rule",
        "commendation": "Commendation",
        "sanction": "Sanction",
        "salary_increment_history": "Salary Increment",
        "system_user": "User",
    }
    return labels.get(table, table.replace("_", " ").title())


def _join_target_parts(primary, secondary):
    primary = str(primary or "").strip()
    secondary = str(secondary or "").strip()
    if primary and secondary:
        return f"{primary} - {secondary}"
    return primary or secondary


def _json_dict(value):
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_number(value):
    for part in (value or "").replace(":", " ").split():
        if part.isdigit():
            return part
    return ""


def _date_range_start(date_range):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_range == "today":
        return today_start
    if date_range == "last_7":
        return today_start - timedelta(days=6)
    if date_range == "last_30":
        return today_start - timedelta(days=29)
    if date_range == "this_year":
        return datetime(now.year, 1, 1)
    return None


def _info(parent, title, text):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()


def _error(parent, title, text):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()


def _category_for_action(action):
    root = action.split(".")[0].lower() if action else "other"
    if root == "promotion_rule":
        return "promotion"
    if root == "org_unit":
        return "hierarchy"
    if root in {"salary", "salary_increment"}:
        return "salary"
    return root if root in CATEGORY_META else "other"


def _category_filter(action_column, category):
    if not category:
        return None
    mapping = {
        "employee": [action_column.like("employee.%")],
        "promotion": [action_column.like("promotion.%"), action_column.like("promotion_rule.%")],
        "commendation": [action_column.like("commendation.%")],
        "sanction": [action_column.like("sanction.%")],
        "import": [action_column.like("import.%")],
        "settings": [action_column.like("settings.%")],
        "hierarchy": [action_column.like("org_unit.%")],
        "salary": [action_column.like("salary.%"), action_column.like("salary_increment.%")],
    }
    if category == "other":
        known = []
        for filters in mapping.values():
            known.extend(filters)
        return ~or_(*known)
    filters = mapping.get(category)
    return or_(*filters) if filters else None


def _action_label(action):
    key = ACTION_LABEL_KEYS.get(action)
    return t(key) if key else action.replace("_", " ").replace(".", " ").title()


def _user_display(log):
    username = log.performed_by_username or (log.performed_by.username if log.performed_by else None)
    full_name = log.performed_by_name or (log.performed_by.full_name if log.performed_by else None)
    return _user_display_from_snapshot(username, full_name)


def _user_display_from_snapshot(username, full_name):
    if username and full_name:
        return f"{username}: {full_name}"
    return username or full_name or "System"


def _category_label(category):
    return t(CATEGORY_LABEL_KEYS.get(category, "other"))


def _category_badge(category):
    meta = CATEGORY_META.get(category, CATEGORY_META["other"])
    cell = QWidget()
    cell.setStyleSheet("background: transparent; border: none;")
    layout = QHBoxLayout(cell)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    label = _category_label(category)
    badge = QLabel(label)
    badge.setStyleSheet(
        f"background: {meta['bg']}; color: {meta['fg']}; border: none; "
        "border-radius: 7px; padding: 4px 10px; font-size: 12px; font-weight: 800;"
    )
    badge.setToolTip(label)
    layout.addWidget(badge)
    return cell


def _polish_combo(combo):
    combo.setMaxVisibleItems(12)
    view = combo.view()
    view.setStyleSheet("""
        QListView {
            background: white;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 0;
            outline: none;
            padding: 4px;
        }
        QListView::item {
            min-height: 30px;
            padding: 6px 10px;
            background: white;
            color: #111827;
        }
        QListView::item:selected,
        QListView::item:hover {
            background: #eff6ff;
            color: #111827;
        }
    """)
    view.window().setStyleSheet("background: white; border: none;")
