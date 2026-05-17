"""Dashboard page matching the MockUI React dashboard layout."""

from datetime import datetime

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, get_increment_due_employees, apply_salary_increment,
    calculate_months_remaining
)
from src.database.models import Employee, Sanction, Commendation, AuditLog, Title
from src.ui.styles import btn_primary, btn_outline, btn_ghost, TABLE_SS, SCROLL_SS


_ICO = QSize(16, 16)

DASH_CARD_SS = """
QFrame#DashboardCard {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame#DashboardCard QLabel {
    border: none;
    background: transparent;
}
"""


class SalaryIncrementReviewDialog(QDialog):
    def __init__(self, increment_data, user, parent=None):
        super().__init__(parent)
        self.increment_data = increment_data
        self.user = user
        self.approved_ids = set()
        self.setWindowTitle(t("review_salary_increments"))
        self.setMinimumSize(700, 460)
        self.setStyleSheet("background: white; color: #111827;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(t("annual_salary_increment_review"))
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        sub = QLabel(t("salary_increment_review_subtitle", count=len(self.increment_data)))
        sub.setStyleSheet("font-size: 13px; color: #6b7280;")
        layout.addWidget(title)
        layout.addWidget(sub)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            t("employee"),
            t("current_salary"),
            t("new_salary"),
            t("increment"),
            t("action"),
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setRowCount(len(self.increment_data))

        for i, row in enumerate(self.increment_data):
            self.table.setRowHeight(i, 52)
            self.table.setItem(i, 0, QTableWidgetItem(f"{row['name']}  ({row['emp_id']})"))
            self.table.setItem(i, 1, QTableWidgetItem(f"${row['salary_before']:,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"${row['salary_after']:,.2f}"))
            inc_item = QTableWidgetItem(row["increment_str"])
            inc_item.setForeground(QColor("#10b981"))
            self.table.setItem(i, 3, inc_item)
            self._set_row_btn(i, row["id"])

        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        approve_all = QPushButton("  " + t("approve_all"))
        approve_all.setIcon(qta.icon("fa5s.check-double", color="white"))
        approve_all.setIconSize(_ICO)
        approve_all.setFixedHeight(36)
        approve_all.setCursor(Qt.PointingHandCursor)
        approve_all.setStyleSheet(btn_primary(36))
        approve_all.clicked.connect(self._approve_all)

        close_btn = QPushButton(t("close"))
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(btn_outline(36))
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(approve_all)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _set_row_btn(self, idx, emp_id):
        if emp_id in self.approved_ids:
            lbl = QLabel(t("approved"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 700;")
            self.table.setCellWidget(idx, 4, lbl)
            return

        btn = QPushButton(t("approve"))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background: #dcfce7; color: #166534; border: none;"
            " border-radius: 6px; font-size: 12px; font-weight: 600; margin: 8px; }"
            " QPushButton:hover { background: #bbf7d0; }"
        )
        btn.clicked.connect(lambda _, eid=emp_id, ridx=idx: self._approve_one(eid, ridx))
        self.table.setCellWidget(idx, 4, btn)

    def _approve_one(self, emp_id, row_idx):
        session = get_session()
        try:
            result = apply_salary_increment(emp_id, self.user.id, session)
            if result["success"]:
                self.approved_ids.add(emp_id)
                self._set_row_btn(row_idx, emp_id)
            else:
                _warning(self, t("error"), result.get("error", "Failed."))
        except Exception as e:
            _critical(self, t("error"), str(e))
        finally:
            session.close()

    def _approve_all(self):
        pending = [r for r in self.increment_data if r["id"] not in self.approved_ids]
        if not pending:
            _information(self, t("done"), t("all_increments_approved"))
            return

        errors = []
        for i, row in enumerate(self.increment_data):
            if row["id"] in self.approved_ids:
                continue
            session = get_session()
            try:
                result = apply_salary_increment(row["id"], self.user.id, session)
                if result["success"]:
                    self.approved_ids.add(row["id"])
                    self._set_row_btn(i, row["id"])
                else:
                    errors.append(f"{row['name']}: {result.get('error', 'failed')}")
            except Exception as e:
                errors.append(f"{row['name']}: {str(e)}")
            finally:
                session.close()

        if errors:
            _warning(self, t("some_failed"), "\n".join(errors))
        else:
            _information(self, t("done"), t("all_increments_done", count=len(pending)))


class DashboardPage(QWidget):
    def __init__(self, user, navigate_fn):
        super().__init__()
        self.user = user
        self.navigate = navigate_fn
        self.setStyleSheet("QWidget { background: #f9fafb; } QLabel { border: none; }")
        self._load_data()
        self._build()

    def _load_data(self):
        session = get_session()
        try:
            self.emp_count = session.query(Employee).count()
            self.sanction_count = session.query(Sanction).filter_by(is_resolved=False).count()
            self.commend_count = session.query(Commendation).count()
            self.promotion_count = 0

            increment_due = get_increment_due_employees(session)
            self.increment_count = len(increment_due)
            self.increment_names = [e.first_name + " " + e.last_name for e in increment_due[:3]]

            self.increment_data = []
            for emp in increment_due:
                title = session.query(Title).filter_by(id=emp.title_id).first()
                if not title:
                    continue
                salary_before = emp.base_salary
                if title.annual_increment_type == "percentage":
                    salary_after = round(salary_before * (1 + title.annual_increment_value / 100), 2)
                    inc_str = f"+{title.annual_increment_value}%"
                else:
                    salary_after = round(salary_before + title.annual_increment_value, 2)
                    inc_str = f"+${title.annual_increment_value:,.2f}"
                self.increment_data.append({
                    "id": emp.id,
                    "name": emp.full_name,
                    "emp_id": emp.employee_id,
                    "salary_before": salary_before,
                    "salary_after": salary_after,
                    "increment_str": inc_str,
                })

            now = datetime.utcnow()
            recent = session.query(AuditLog).order_by(AuditLog.performed_at.desc(), AuditLog.id.desc()).limit(50).all()
            recent = [log for log in recent if not log.performed_at or log.performed_at <= now][:5]
            self.logs_data = [
                {
                    "action": (log.action or "Activity").replace(".", " ").replace("_", " ").title(),
                    "target": log.description or t("organization_record_updated"),
                    "user": log.performed_by.full_name if log.performed_by else "System",
                    "time": log.performed_at.strftime("%b %d, %H:%M") if log.performed_at else "",
                }
                for log in recent
            ]

            upcoming = []
            active_emps = session.query(Employee).filter_by(status="active").all()
            for emp in active_emps:
                race = calculate_months_remaining(emp, session)
                if not race["has_next_level"]:
                    continue
                if race["eligible"]:
                    self.promotion_count += 1
                months_remaining = race["months_remaining"]
                if months_remaining > 12:
                    continue
                next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
                upcoming.append({
                    "name": emp.full_name,
                    "current": emp.title.name if emp.title else "?",
                    "next": next_title.name if next_title else "?",
                    "months_remaining": months_remaining,
                    "eligible": race["eligible"],
                    "progress_pct": race["progress_pct"],
                })
            upcoming.sort(key=lambda x: (0 if x["eligible"] else 1, x["months_remaining"]))
            self.upcoming_promotions = upcoming[:3]
        finally:
            session.close()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_SS)

        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("dashboard_title"))
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel(t("dashboard_subtitle"))
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(32)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        add_btn = QPushButton("  " + t("add_employee"))
        add_btn.setIcon(qta.icon("fa5s.user-plus", color="white"))
        add_btn.setIconSize(_ICO)
        add_btn.setFixedHeight(44)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(btn_primary(44))
        add_btn.clicked.connect(lambda: self.navigate("employees"))

        imp_btn = QPushButton("  " + t("nav_import"))
        imp_btn.setIcon(qta.icon("fa5s.calendar", color="#111827"))
        imp_btn.setIconSize(_ICO)
        imp_btn.setFixedHeight(44)
        imp_btn.setCursor(Qt.PointingHandCursor)
        imp_btn.setStyleSheet(btn_outline(44))
        imp_btn.clicked.connect(lambda: self.navigate("import_data"))

        actions.addWidget(add_btn)
        actions.addWidget(imp_btn)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addSpacing(40)

        if self.increment_count > 0:
            layout.addWidget(self._increment_alert())
            layout.addSpacing(24)

        stats = QGridLayout()
        stats.setHorizontalSpacing(24)
        stats.setVerticalSpacing(24)
        for i, card in enumerate([
            self._stat_card(t("total_employees"), str(self.emp_count), t("organization_records"), "#3b82f6", "fa5s.users"),
            self._stat_card(t("pending_promotions"), str(self.promotion_count), t("eligible_right_now"), "#10b981", "fa5s.chart-line"),
            self._stat_card(t("commendations_this_month"), str(self.commend_count), t("awards_recorded"), "#f59e0b", "fa5s.award"),
            self._stat_card(t("active_sanctions"), str(self.sanction_count), t("open_disciplinary_actions"), "#ef4444", "fa5s.exclamation-triangle"),
        ]):
            stats.addWidget(card, 0, i)
        layout.addLayout(stats)
        layout.addSpacing(36)

        bottom = QHBoxLayout()
        bottom.setSpacing(24)
        bottom.addWidget(self._recent_card(), 1)
        bottom.addWidget(self._upcoming_card(), 1)
        layout.addLayout(bottom)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _increment_alert(self):
        alert = QFrame()
        alert.setObjectName("IncrementAlert")
        alert.setStyleSheet(
            "QFrame#IncrementAlert { background: #fefce8; border: 1px solid #fde047; border-radius: 8px; }"
            "QFrame#IncrementAlert QLabel { border: none; background: transparent; }"
        )
        row = QHBoxLayout(alert)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.coins", color="#ca8a04").pixmap(22, 22))
        row.addWidget(icon)
        txt = QLabel(t("salary_increment_prompt", count=self.increment_count))
        txt.setStyleSheet("font-size: 13px; color: #854d0e;")
        row.addWidget(txt, 1)
        btn = QPushButton(t("review"))
        btn.setFixedHeight(34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("QPushButton { background: #ca8a04; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: 600; }")
        btn.clicked.connect(self._open_increment_dialog)
        row.addWidget(btn)
        return alert

    def _open_increment_dialog(self):
        SalaryIncrementReviewDialog(self.increment_data, self.user, parent=self).exec()

    def _card(self):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setStyleSheet(DASH_CARD_SS)
        return card

    def _stat_card(self, label, value, change, color, icon_name):
        card = self._card()
        card.setMinimumHeight(172)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(12)

        text = QVBoxLayout()
        text.setSpacing(10)
        label_lbl = QLabel(label)
        label_lbl.setWordWrap(True)
        label_lbl.setStyleSheet("font-size: 16px; color: #4b5563;")
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("font-size: 36px; font-weight: 800; color: #111827;")
        change_lbl = QLabel(change)
        change_lbl.setWordWrap(True)
        change_lbl.setStyleSheet("font-size: 15px; color: #059669;")
        text.addWidget(label_lbl)
        text.addWidget(value_lbl)
        text.addWidget(change_lbl)
        layout.addLayout(text)
        layout.addStretch()

        icon_box = QLabel()
        icon_box.setFixedSize(56, 56)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(f"background: {color}; border: none; border-radius: 8px;")
        icon_box.setPixmap(qta.icon(icon_name, color="white").pixmap(26, 26))
        layout.addWidget(icon_box, 0, Qt.AlignTop)
        return card

    def _recent_card(self):
        card = self._card()
        card.setMinimumHeight(460)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        header = QHBoxLayout()
        title = QLabel(t("recent_activity"))
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827;")
        view = QPushButton(t("view_all"))
        view.setCursor(Qt.PointingHandCursor)
        view.setStyleSheet(btn_ghost(32))
        view.clicked.connect(lambda: self.navigate("audit_log"))
        header.addWidget(title)
        header.addStretch()
        header.addWidget(view)
        layout.addLayout(header)
        layout.addSpacing(28)

        if self.logs_data:
            for index, item in enumerate(self.logs_data[:5]):
                layout.addWidget(self._activity_row(item, index == len(self.logs_data[:5]) - 1))
        else:
            empty = QLabel(t("no_recent_activity"))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 15px; color: #6b7280; background: #f9fafb; border: none; border-radius: 8px; padding: 28px;")
            layout.addWidget(empty)
        layout.addStretch()
        return card

    def _activity_row(self, item, is_last):
        row = QFrame()
        row.setObjectName("ActivityRow")
        row.setMinimumHeight(94)
        border = "none" if is_last else "1px solid #f3f4f6"
        row.setStyleSheet(
            f"QFrame#ActivityRow {{ background: transparent; border: none; border-bottom: {border}; border-radius: 0; }}"
            "QFrame#ActivityRow QLabel { border: none; background: transparent; }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet("background: #2563eb; border: none; border-radius: 5px;")
        layout.addWidget(dot, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(4)
        action = QLabel(item["action"])
        action.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        target = QLabel(item["target"])
        target.setWordWrap(True)
        target.setStyleSheet("font-size: 16px; color: #4b5563;")
        byline = QLabel(t("by_user", user=item["user"]))
        byline.setStyleSheet("font-size: 14px; color: #6b7280;")
        text.addWidget(action)
        text.addWidget(target)
        text.addWidget(byline)
        layout.addLayout(text, 1)

        time = QLabel(item["time"])
        time.setStyleSheet("font-size: 14px; color: #6b7280;")
        layout.addWidget(time, 0, Qt.AlignTop)
        return row

    def _upcoming_card(self):
        card = self._card()
        card.setMinimumHeight(460)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        header = QHBoxLayout()
        title = QLabel(t("upcoming_promotions"))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827;")
        view = QPushButton(t("view_all"))
        view.setCursor(Qt.PointingHandCursor)
        view.setStyleSheet(btn_ghost(32))
        view.clicked.connect(lambda: self.navigate("promotions"))
        header.addWidget(title)
        header.addStretch()
        header.addWidget(view)
        layout.addLayout(header)
        layout.addSpacing(28)

        if self.upcoming_promotions:
            for index, item in enumerate(self.upcoming_promotions[:3]):
                layout.addWidget(self._promo_row(item))
                if index < len(self.upcoming_promotions[:3]) - 1:
                    layout.addSpacing(20)
        else:
            empty = QLabel(t("no_upcoming_promotions"))
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 15px; color: #6b7280; background: #f9fafb; border: none; border-radius: 8px; padding: 28px;")
            layout.addWidget(empty)
        layout.addStretch()
        return card

    def _promo_row(self, item):
        row = QFrame()
        row.setObjectName("PromoRow")
        row.setMinimumHeight(142)
        row.setStyleSheet(
            "QFrame#PromoRow { background: #f9fafb; border: none; border-radius: 8px; }"
            "QFrame#PromoRow QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(row)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(6)
        name = QLabel(item["name"])
        name.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        level = QLabel(f"{item['current']} to {item['next']}")
        level.setStyleSheet("font-size: 16px; color: #4b5563;")
        text.addWidget(name)
        text.addWidget(level)
        top.addLayout(text)
        top.addStretch()

        badge_text = item.get("badge")
        if not badge_text:
            badge_text = "Eligible" if item["eligible"] else f"{item['months_remaining']} mo"
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background: #dbeafe; color: #2563eb; border: none; border-radius: 14px; padding: 4px 10px; font-size: 14px;")
        top.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(top)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(item["progress_pct"])
        progress.setFixedHeight(10)
        progress.setTextVisible(False)
        progress.setStyleSheet(
            "QProgressBar { background: #e5e7eb; border: none; border-radius: 5px; }"
            "QProgressBar::chunk { background: #2563eb; border-radius: 5px; }"
        )
        layout.addWidget(progress)

        complete = QLabel(f"{item['progress_pct']}% complete")
        complete.setStyleSheet("font-size: 14px; color: #6b7280;")
        layout.addWidget(complete)
        return row


def _styled_message_box(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet("""
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
    """)
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)
