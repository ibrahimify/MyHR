"""
Dashboard Page
Shows: stat cards, salary increment alert, recent audit activity, upcoming promotions.
All data is live from DB.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt
from src.core.i18n import t
from src.database.connection import get_session, get_increment_due_employees
from src.database.models import Employee, Sanction, Commendation, PromotionHistory, AuditLog, SystemUser


class DashboardPage(QWidget):
    def __init__(self, user, navigate_fn):
        super().__init__()
        self.user = user
        self.navigate = navigate_fn
        self.setStyleSheet("background: #f4f6fb;")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background: white; border-bottom: 1px solid #e5e7eb;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)
        title = QLabel(t("dashboard_title"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a1d2e;")
        sub = QLabel(t("dashboard_subtitle"))
        sub.setStyleSheet("font-size: 12px; color: #9ca3af; margin-left: 12px;")
        h_layout.addWidget(title)
        h_layout.addWidget(sub)
        h_layout.addStretch()

        # Quick action buttons
        add_btn = QPushButton("+ " + t("add_employee"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet("""
            QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 0 16px; }
            QPushButton:hover { background: #3a57e8; }
        """)
        add_btn.clicked.connect(lambda: self.navigate("employees"))

        import_btn = QPushButton("↓ " + t("nav_import"))
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setFixedHeight(34)
        import_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #4f6ef7; border: 1px solid #4f6ef7; border-radius: 8px; font-size: 13px; padding: 0 16px; }
            QPushButton:hover { background: #eef2ff; }
        """)
        import_btn.clicked.connect(lambda: self.navigate("import_data"))

        h_layout.addWidget(add_btn)
        h_layout.addSpacing(8)
        h_layout.addWidget(import_btn)
        outer.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        # Fetch DB data
        session = get_session()
        try:
            emp_count        = session.query(Employee).count()
            sanction_count   = session.query(Sanction).filter_by(is_resolved=False).count()
            commend_count    = session.query(Commendation).count()
            promotion_count  = session.query(PromotionHistory).count()
            increment_due    = get_increment_due_employees(session)
            recent_logs      = session.query(AuditLog).order_by(
                AuditLog.performed_at.desc()
            ).limit(6).all()
            # Detach data before closing session
            logs_data = [(
                l.action,
                l.description or "",
                l.performed_at.strftime("%Y-%m-%d %H:%M") if l.performed_at else "",
            ) for l in recent_logs]
            increment_count  = len(increment_due)
            increment_names  = [e.first_name + " " + e.last_name for e in increment_due[:3]]
        finally:
            session.close()

        # ── Salary increment alert ────────────────────────────────────────────
        if increment_count > 0:
            alert = QFrame()
            alert.setStyleSheet("""
                QFrame {
                    background: #fefce8;
                    border: 1px solid #fde047;
                    border-radius: 10px;
                }
            """)
            alert_layout = QHBoxLayout(alert)
            alert_layout.setContentsMargins(16, 12, 16, 12)

            icon_lbl = QLabel("💰")
            icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
            alert_layout.addWidget(icon_lbl)

            text_col = QVBoxLayout()
            alert_title = QLabel(t("salary_increment_due"))
            alert_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #854d0e; background: transparent;")
            names_preview = ", ".join(increment_names) + (" ..." if increment_count > 3 else "")
            alert_msg = QLabel(t("salary_increment_prompt", count=increment_count) + f"  ({names_preview})")
            alert_msg.setStyleSheet("font-size: 12px; color: #a16207; background: transparent;")
            text_col.addWidget(alert_title)
            text_col.addWidget(alert_msg)
            alert_layout.addLayout(text_col)
            alert_layout.addStretch()

            review_btn = QPushButton(t("review_increments"))
            review_btn.setCursor(Qt.PointingHandCursor)
            review_btn.setFixedHeight(32)
            review_btn.setStyleSheet("""
                QPushButton { background: #ca8a04; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; padding: 0 14px; }
                QPushButton:hover { background: #a16207; }
            """)
            review_btn.clicked.connect(lambda: self.navigate("employees"))
            alert_layout.addWidget(review_btn)
            layout.addWidget(alert)

        # ── Stat cards ────────────────────────────────────────────────────────
        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)

        stats = [
            (t("total_employees"),    str(emp_count),      "#4f6ef7", "👤"),
            (t("active_sanctions"),   str(sanction_count), "#ef4444", "⚠"),
            (t("commendations_total"),str(commend_count),  "#f59e0b", "★"),
            (t("promotions_total"),   str(promotion_count),"#10b981", "↑"),
        ]
        for i, (label, value, color, icon) in enumerate(stats):
            card = self._stat_card(label, value, color, icon)
            stats_grid.addWidget(card, 0, i)

        layout.addLayout(stats_grid)

        # ── Bottom two-column ─────────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # Recent activity
        activity_card = QFrame()
        activity_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        ac_layout = QVBoxLayout(activity_card)
        ac_layout.setContentsMargins(20, 16, 20, 16)
        ac_layout.setSpacing(0)

        ac_header = QHBoxLayout()
        ac_title = QLabel(t("recent_activity"))
        ac_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1d2e; background: transparent;")
        view_all = QPushButton(t("view_all"))
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.setStyleSheet("background: transparent; color: #4f6ef7; border: none; font-size: 12px;")
        view_all.clicked.connect(lambda: self.navigate("audit_log"))
        ac_header.addWidget(ac_title)
        ac_header.addStretch()
        ac_header.addWidget(view_all)
        ac_layout.addLayout(ac_header)
        ac_layout.addSpacing(12)

        ACTION_COLORS = {
            "employee": "#4f6ef7",
            "promotion": "#10b981",
            "commendation": "#f59e0b",
            "sanction": "#ef4444",
            "salary": "#8b5cf6",
            "import": "#06b6d4",
        }

        if logs_data:
            for action, desc, ts in logs_data:
                color = "#9ca3af"
                for k, v in ACTION_COLORS.items():
                    if k in action.lower():
                        color = v
                        break
                row = self._activity_row(action, desc, ts, color)
                ac_layout.addWidget(row)
        else:
            empty = QLabel("No activity yet")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9ca3af; font-size: 13px; padding: 20px; background: transparent;")
            ac_layout.addWidget(empty)

        ac_layout.addStretch()
        bottom_row.addWidget(activity_card, 3)

        # Upcoming promotions placeholder
        promo_card = QFrame()
        promo_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        pc_layout = QVBoxLayout(promo_card)
        pc_layout.setContentsMargins(20, 16, 20, 16)
        pc_layout.setSpacing(0)

        pc_header = QHBoxLayout()
        pc_title = QLabel(t("upcoming_promotions"))
        pc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1d2e; background: transparent;")
        view_promo = QPushButton(t("view_all"))
        view_promo.setCursor(Qt.PointingHandCursor)
        view_promo.setStyleSheet("background: transparent; color: #4f6ef7; border: none; font-size: 12px;")
        view_promo.clicked.connect(lambda: self.navigate("promotions"))
        pc_header.addWidget(pc_title)
        pc_header.addStretch()
        pc_header.addWidget(view_promo)
        pc_layout.addLayout(pc_header)
        pc_layout.addSpacing(12)

        empty_promo = QLabel("Add employees to see\npromotion eligibility here.")
        empty_promo.setAlignment(Qt.AlignCenter)
        empty_promo.setStyleSheet("color: #9ca3af; font-size: 13px; padding: 30px; background: transparent;")
        pc_layout.addWidget(empty_promo)
        pc_layout.addStretch()
        bottom_row.addWidget(promo_card, 2)

        layout.addLayout(bottom_row)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _stat_card(self, label, value, color, icon):
        card = QFrame()
        card.setFixedHeight(100)
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(14)

        icon_box = QLabel(icon)
        icon_box.setFixedSize(44, 44)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(f"background: {color}18; border-radius: 10px; font-size: 20px;")
        layout.addWidget(icon_box)

        text = QVBoxLayout()
        text.setSpacing(2)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color}; background: transparent;")
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent;")
        text.addWidget(val_lbl)
        text.addWidget(lbl)
        layout.addLayout(text)
        layout.addStretch()
        return card

    def _activity_row(self, action, desc, ts, color):
        row = QFrame()
        row.setFixedHeight(46)
        row.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #f3f4f6;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setStyleSheet(f"color: {color}; font-size: 9px; background: transparent;")
        layout.addWidget(dot)

        action_lbl = QLabel(action.replace(".", " › ").replace("_", " ").title())
        action_lbl.setFixedWidth(180)
        action_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1a1d2e; background: transparent;")
        layout.addWidget(action_lbl)

        desc_lbl = QLabel(desc[:50] + "..." if len(desc) > 50 else desc)
        desc_lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        layout.addWidget(desc_lbl)
        layout.addStretch()

        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")
        layout.addWidget(ts_lbl)
        return row