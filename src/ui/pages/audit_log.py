"""
Audit Log Page
- Immutable record of all admin/HR actions
- Searchable and filterable
- Shows who, what, when, before/after values
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import get_session
from src.database.models import AuditLog, SystemUser


ACTION_COLORS = {
    "employee":    ("#dbeafe", "#1e40af"),
    "promotion":   ("#dcfce7", "#166534"),
    "commendation":("#fef9c3", "#854d0e"),
    "sanction":    ("#fef2f2", "#991b1b"),
    "salary":      ("#f3e8ff", "#6b21a8"),
    "org_unit":    ("#e0f2fe", "#0369a1"),
    "import":      ("#f0fdf4", "#166534"),
    "settings":    ("#f9fafb", "#374151"),
}


class AuditLogPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.all_logs = []
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

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
        title = QLabel(t("audit_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        sub = QLabel(t("audit_subtitle"))
        sub.setStyleSheet("font-size: 13px; color: #9ca3af; margin-left: 12px;")
        h.addWidget(title)
        h.addWidget(sub)
        h.addStretch()
        layout.addWidget(header)

        # Filter bar
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet("background: white; border-bottom: 1px solid #f0f0f0;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(28, 0, 28, 0)
        bl.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search actions, descriptions...")
        self.search.setFixedHeight(34)
        self.search.setStyleSheet("QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #111827; background: #f9fafb; } QLineEdit:focus { border-color: #2563eb; }")
        self.search.textChanged.connect(self._filter)
        bl.addWidget(self.search, 3)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(34)
        self.category_filter.setStyleSheet("QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; color: #111827; background: #f9fafb; min-height: 34px; }")
        self.category_filter.addItem("All Categories", None)
        for cat in ACTION_COLORS:
            self.category_filter.addItem(cat.replace("_", " ").title(), cat)
        self.category_filter.addItem("Other", "other")
        self.category_filter.currentIndexChanged.connect(self._filter)
        bl.addWidget(self.category_filter, 2)

        self.user_filter = QComboBox()
        self.user_filter.setFixedHeight(34)
        self.user_filter.setStyleSheet(self.category_filter.styleSheet())
        self.user_filter.addItem("All Users", None)
        self.user_filter.currentIndexChanged.connect(self._filter)
        bl.addWidget(self.user_filter, 2)

        layout.addWidget(bar)

        # Count label
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size: 12px; color: #9ca3af; padding: 6px 28px;")
        layout.addWidget(self.count_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("timestamp"), t("performed_by"), t("action"),
            "Description", "Category", "Target"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e5e7eb; border-radius: 12px; font-size: 13px; color: #111827; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #111827; }
            QTableWidget::item:selected { background: #eff6ff; color: #111827; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMouseTracking(True)
        layout.addWidget(self.table)

        # Info footer
        footer = QFrame()
        footer.setFixedHeight(40)
        footer.setStyleSheet("background: #f9fafb; border-top: 1px solid #e5e7eb;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 0, 28, 0)
        note = QLabel("🔒  Audit logs are immutable — they cannot be modified or deleted.")
        note.setStyleSheet("font-size: 12px; color: #6b7280;")
        fl.addWidget(note)
        fl.addStretch()
        layout.addWidget(footer)

    def refresh(self):
        session = get_session()
        try:
            logs = session.query(AuditLog).order_by(AuditLog.performed_at.desc()).limit(500).all()
            self.all_logs = [{
                "timestamp": l.performed_at.strftime("%Y-%m-%d %H:%M:%S") if l.performed_at else "—",
                "user": l.performed_by.full_name if l.performed_by else "System",
                "action": l.action,
                "description": l.description or "—",
                "category": l.action.split(".")[0] if l.action else "other",
                "target": f"{l.target_table} #{l.target_id}" if l.target_table else "—",
            } for l in logs]

            # Populate user filter
            users = sorted({x["user"] for x in self.all_logs})
            self.user_filter.blockSignals(True)
            self.user_filter.clear()
            self.user_filter.addItem("All Users", None)
            for u in users:
                self.user_filter.addItem(u, u)
            self.user_filter.blockSignals(False)
        finally:
            session.close()

        self._filter()

    def _filter(self):
        search   = self.search.text().lower()
        category = self.category_filter.currentData()
        user     = self.user_filter.currentData()

        filtered = [l for l in self.all_logs if
            (not search   or search in l["action"].lower() or search in l["description"].lower()) and
            (not category or l["category"] == category) and
            (not user     or l["user"] == user)
        ]

        self.count_lbl.setText(f"Showing {len(filtered)} of {len(self.all_logs)} log entries")
        self._populate(filtered)

    def _populate(self, logs):
        self.table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table.setRowHeight(i, 46)

            ts = QTableWidgetItem(log["timestamp"])
            ts.setForeground(QColor("#6b7280"))
            self.table.setItem(i, 0, ts)

            user_item = QTableWidgetItem(log["user"])
            user_item.setForeground(QColor("#2563eb"))
            self.table.setItem(i, 1, user_item)

            desc = log["description"]
            desc_item = QTableWidgetItem(desc[:80] + "..." if len(desc) > 80 else desc)
            desc_item.setToolTip(desc)
            self.table.setItem(i, 3, desc_item)

            action_full = QTableWidgetItem(log["action"].replace(".", " › "))
            action_full.setToolTip(log["action"])
            action_full.setForeground(QColor("#111827"))
            self.table.setItem(i, 2, action_full)

            cat = log["category"]
            bg, fg = ACTION_COLORS.get(cat, ("#f9fafb", "#374151"))
            cat_item = QTableWidgetItem(cat.replace("_", " ").title())
            cat_item.setBackground(QColor(bg))
            cat_item.setForeground(QColor(fg))
            self.table.setItem(i, 4, cat_item)

            self.table.setItem(i, 5, QTableWidgetItem(log["target"]))

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)