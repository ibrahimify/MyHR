"""
Audit Log Page
- Immutable record of all admin/HR actions
- Searchable and filterable
- Shows who, what, when, before/after values
"""

from collections import Counter
from datetime import datetime, timedelta

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QScrollArea
)

from src.database.connection import get_session
from src.database.models import AuditLog


ACTION_LABELS = {
    "employee.create": "Employee Added",
    "employee.update": "Employee Updated",
    "employee.delete": "Employee Deleted",
    "promotion.approve": "Promotion Approved",
    "promotion_rule.update": "Promotion Rule Updated",
    "commendation.issue": "Commendation Issued",
    "sanction.issue": "Sanction Applied",
    "sanction.resolve": "Sanction Resolved",
    "import.bulk_employees": "CSV Import",
    "settings.salary_ranges": "Salary Ranges Updated",
    "settings.increment_rules": "Increment Rules Updated",
    "settings.general": "General Settings Updated",
    "settings.promotion_rules": "Promotion Settings Updated",
    "settings.password_change": "Password Changed",
    "settings.export_employees": "Employee Data Exported",
    "org_unit.create": "Organization Unit Added",
    "org_unit.update": "Organization Unit Updated",
    "org_unit.delete": "Organization Unit Deleted",
    "salary_increment.apply": "Salary Increment Applied",
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
        self.stat_values = {}
        self.setStyleSheet("background: #f9fafb;")
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

        title = QLabel("Audit Log")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel("Complete record of all system activities and changes")
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(20)
        self._add_stat_card("total", "Total Logs", "fa5s.file-alt", "#2563eb", "#dbeafe")
        self._add_stat_card("today", "Today's Activities", "fa5s.user", "#16a34a", "#dcfce7")
        self._add_stat_card("week", "This Week", "fa5s.calendar-alt", "#9333ea", "#f3e8ff")
        self._add_stat_card("active_user", "Most Active User", "fa5s.clipboard-list", "#d97706", "#fef3c7")
        layout.addLayout(self.stats_row)
        layout.addSpacing(30)

        filter_card = QFrame()
        filter_card.setObjectName("Card")
        filter_card.setStyleSheet(CARD_SS)
        fl = QHBoxLayout(filter_card)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setSpacing(16)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search actions, targets, or details...")
        self.search.setFixedHeight(44)
        self.search.setStyleSheet(INPUT_SS)
        self.search.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._filter)
        fl.addWidget(self.search, 4)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(44)
        self.category_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.category_filter)
        self.category_filter.addItem("All Categories", None)
        for key, meta in CATEGORY_META.items():
            if key != "other":
                self.category_filter.addItem(meta["label"], key)
        self.category_filter.addItem("Other", "other")
        self.category_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.category_filter, 1)

        self.user_filter = QComboBox()
        self.user_filter.setFixedHeight(44)
        self.user_filter.setStyleSheet(COMBO_SS)
        _polish_combo(self.user_filter)
        self.user_filter.addItem("All Users", None)
        self.user_filter.currentIndexChanged.connect(self._filter)
        fl.addWidget(self.user_filter, 1)

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
            "Timestamp", "User", "Action", "Target", "Details", "Category"
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 190)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMouseTracking(True)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tl.addWidget(self.table)
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
        info_title = QLabel("Audit Log Information")
        info_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #1e40af; background: transparent;")
        info_head.addWidget(info_icon)
        info_head.addWidget(info_title)
        info_head.addStretch()
        il.addLayout(info_head)

        for text in [
            "All system activities are automatically logged for compliance and security",
            "Logs cannot be modified or deleted to ensure data integrity",
            "Records include user identity, timestamp, and detailed action information",
            "Logs are retained indefinitely for audit purposes",
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
        session = get_session()
        try:
            logs = session.query(AuditLog).order_by(AuditLog.performed_at.desc()).limit(500).all()
            self.all_logs = [self._serialize_log(log) for log in logs]

            users = sorted({entry["user"] for entry in self.all_logs})
            current_user = self.user_filter.currentData()
            self.user_filter.blockSignals(True)
            self.user_filter.clear()
            self.user_filter.addItem("All Users", None)
            for name in users:
                self.user_filter.addItem(name, name)
            if current_user in users:
                self.user_filter.setCurrentText(current_user)
            self.user_filter.blockSignals(False)
        finally:
            session.close()

        self._update_stats()
        self._filter()

    def _serialize_log(self, log):
        action = log.action or "other"
        category = _category_for_action(action)
        target = "-"
        if log.target_table:
            table = log.target_table.replace("_", " ").title()
            target = f"{table} #{log.target_id}" if log.target_id else table

        return {
            "timestamp": log.performed_at.strftime("%Y-%m-%d %H:%M:%S") if log.performed_at else "-",
            "date": log.performed_at.date() if log.performed_at else None,
            "user": log.performed_by.full_name if log.performed_by else "System",
            "action": ACTION_LABELS.get(action, action.replace("_", " ").replace(".", " ").title()),
            "raw_action": action,
            "details": log.description or "-",
            "category": category,
            "target": target,
        }

    def _update_stats(self):
        today = datetime.now().date()
        week_start = today - timedelta(days=6)
        user_counts = Counter(entry["user"] for entry in self.all_logs)
        most_active = user_counts.most_common(1)[0][0] if user_counts else "-"

        self.stat_values["total"].setText(str(len(self.all_logs)))
        self.stat_values["today"].setText(str(sum(1 for entry in self.all_logs if entry["date"] == today)))
        self.stat_values["week"].setText(str(sum(1 for entry in self.all_logs if entry["date"] and entry["date"] >= week_start)))
        self.stat_values["active_user"].setText(most_active)
        self.stat_values["active_user"].setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #030213; background: transparent;"
        )

    def _filter(self):
        search = self.search.text().strip().lower()
        category = self.category_filter.currentData()
        user = self.user_filter.currentData()

        filtered = []
        for entry in self.all_logs:
            haystack = " ".join([
                entry["action"], entry["raw_action"], entry["details"],
                entry["target"], entry["user"], CATEGORY_META[entry["category"]]["label"]
            ]).lower()
            if search and search not in haystack:
                continue
            if category and entry["category"] != category:
                continue
            if user and entry["user"] != user:
                continue
            filtered.append(entry)

        self.count_lbl.setText(f"Showing {len(filtered)} of {len(self.all_logs)} log entries")
        self._populate(filtered)

    def _populate(self, logs):
        self.table.setRowCount(len(logs))
        self.table.setMinimumHeight(112 + (56 * max(1, len(logs))))

        for row_index, log in enumerate(logs):
            self.table.setRowHeight(row_index, 56)

            timestamp = QTableWidgetItem(log["timestamp"])
            timestamp.setForeground(QColor("#374151"))
            timestamp.setToolTip(log["timestamp"])
            self.table.setItem(row_index, 0, timestamp)

            user_item = QTableWidgetItem(log["user"])
            user_item.setIcon(qta.icon("fa5s.user", color="#2563eb"))
            user_font = user_item.font()
            user_font.setBold(True)
            user_item.setFont(user_font)
            user_item.setToolTip(log["user"])
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

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)


def _category_for_action(action):
    root = action.split(".")[0].lower() if action else "other"
    if root == "promotion_rule":
        return "promotion"
    if root == "org_unit":
        return "hierarchy"
    if root in {"salary", "salary_increment"}:
        return "salary"
    return root if root in CATEGORY_META else "other"


def _category_badge(category):
    meta = CATEGORY_META.get(category, CATEGORY_META["other"])
    cell = QWidget()
    cell.setStyleSheet("background: transparent; border: none;")
    layout = QHBoxLayout(cell)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    badge = QLabel(meta["label"])
    badge.setStyleSheet(
        f"background: {meta['bg']}; color: {meta['fg']}; border: none; "
        "border-radius: 7px; padding: 4px 10px; font-size: 12px; font-weight: 800;"
    )
    badge.setToolTip(meta["label"])
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
