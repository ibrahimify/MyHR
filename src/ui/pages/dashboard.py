"""Dashboard Page — live stats, salary increment alert, recent activity."""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import get_session, get_increment_due_employees, apply_salary_increment
from src.database.models import Employee, Sanction, Commendation, PromotionHistory, AuditLog, Title
from src.ui.styles import (
    btn_primary, btn_blue, btn_outline, btn_ghost,
    TABLE_SS, CARD_SS, SCROLL_SS
)

_ICO = QSize(16, 16)


# ── Salary Increment Dialog ───────────────────────────────────────────────────
class SalaryIncrementReviewDialog(QDialog):
    def __init__(self, increment_data, user, parent=None):
        super().__init__(parent)
        self.increment_data = increment_data
        self.user = user
        self.approved_ids = set()
        self.setWindowTitle("Review Salary Increments")
        self.setMinimumSize(700, 460)
        self.setStyleSheet("background: white; color: #111827;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header
        title = QLabel("Annual Salary Increment Review")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #111827;")
        sub = QLabel(f"{len(self.increment_data)} employee(s) are due for their annual salary increment.")
        sub.setStyleSheet("font-size: 13px; color: #6b7280;")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Current Salary", "New Salary", "Increment", "Action"
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
            self.table.setItem(i, 1, QTableWidgetItem(f"€{row['salary_before']:,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"€{row['salary_after']:,.2f}"))
            inc_item = QTableWidgetItem(row["increment_str"])
            inc_item.setForeground(QColor("#10b981"))
            self.table.setItem(i, 3, inc_item)
            self._set_row_btn(i, row["id"])

        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        approve_all = QPushButton("  Approve All")
        approve_all.setIcon(qta.icon("fa5s.check-double", color="white"))
        approve_all.setIconSize(_ICO)
        approve_all.setFixedHeight(36)
        approve_all.setCursor(Qt.PointingHandCursor)
        approve_all.setStyleSheet(btn_blue(36))
        approve_all.clicked.connect(self._approve_all)

        close_btn = QPushButton("Close")
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
            lbl = QLabel("✓  Approved")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            self.table.setCellWidget(idx, 4, lbl)
        else:
            btn = QPushButton("Approve")
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
                QMessageBox.warning(self, "Error", result.get("error", "Failed."))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def _approve_all(self):
        pending = [r for r in self.increment_data if r["id"] not in self.approved_ids]
        if not pending:
            QMessageBox.information(self, "Done", "All increments already approved.")
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
            QMessageBox.warning(self, "Some Failed", "\n".join(errors))
        else:
            QMessageBox.information(self, "Done", f"All {len(pending)} increment(s) approved.")


# ── Dashboard Page ────────────────────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self, user, navigate_fn):
        super().__init__()
        self.user = user
        self.navigate = navigate_fn
        self.setStyleSheet("background: #f9fafb;")
        self._load_data()
        self._build()

    def _load_data(self):
        session = get_session()
        try:
            self.emp_count       = session.query(Employee).count()
            self.sanction_count  = session.query(Sanction).filter_by(is_resolved=False).count()
            self.commend_count   = session.query(Commendation).count()
            self.promotion_count = session.query(PromotionHistory).count()

            increment_due = get_increment_due_employees(session)
            self.increment_count = len(increment_due)
            self.increment_names = [e.first_name + " " + e.last_name for e in increment_due[:3]]

            self.increment_data = []
            for emp in increment_due:
                title = session.query(Title).filter_by(id=emp.title_id).first()
                if not title:
                    continue
                sb = emp.base_salary
                if title.annual_increment_type == "percentage":
                    sa = round(sb * (1 + title.annual_increment_value / 100), 2)
                    inc_str = f"+{title.annual_increment_value}%"
                else:
                    sa = round(sb + title.annual_increment_value, 2)
                    inc_str = f"+€{title.annual_increment_value:,.2f}"
                self.increment_data.append({
                    "id": emp.id, "name": emp.full_name, "emp_id": emp.employee_id,
                    "salary_before": sb, "salary_after": sa, "increment_str": inc_str,
                })

            recent = session.query(AuditLog).order_by(AuditLog.performed_at.desc()).limit(6).all()
            self.logs_data = [
                (l.action, l.description or "",
                 l.performed_at.strftime("%b %d, %H:%M") if l.performed_at else "")
                for l in recent
            ]
        finally:
            session.close()

    def _build(self):
        # Outer scroll
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_SS)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # ── Page title ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        t1 = QLabel(t("dashboard_title"))
        t1.setStyleSheet("font-size: 24px; font-weight: bold; color: #111827;")
        t2 = QLabel(t("dashboard_subtitle"))
        t2.setStyleSheet("font-size: 14px; color: #6b7280;")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        hdr.addLayout(title_col)
        hdr.addStretch()

        add_btn = QPushButton("  " + t("add_employee"))
        add_btn.setIcon(qta.icon("fa5s.user-plus", color="white"))
        add_btn.setIconSize(_ICO)
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(btn_primary(36))
        add_btn.clicked.connect(lambda: self.navigate("employees"))

        imp_btn = QPushButton("  " + t("nav_import"))
        imp_btn.setIcon(qta.icon("fa5s.upload", color="#374151"))
        imp_btn.setIconSize(_ICO)
        imp_btn.setFixedHeight(36)
        imp_btn.setCursor(Qt.PointingHandCursor)
        imp_btn.setStyleSheet(btn_outline(36))
        imp_btn.clicked.connect(lambda: self.navigate("import_data"))

        hdr.addWidget(imp_btn)
        hdr.addSpacing(8)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # ── Increment alert ───────────────────────────────────────────────────
        if self.increment_count > 0:
            alert = QFrame()
            alert.setStyleSheet(
                "QFrame { background: #fefce8; border: 1px solid #fde047; border-radius: 10px; }"
            )
            al = QHBoxLayout(alert)
            al.setContentsMargins(16, 14, 16, 14)
            al.setSpacing(12)

            ico = QLabel()
            ico.setPixmap(qta.icon("fa5s.coins", color="#ca8a04").pixmap(22, 22))
            al.addWidget(ico)

            tc = QVBoxLayout()
            tc.setSpacing(2)
            at = QLabel(t("salary_increment_due"))
            at.setStyleSheet("font-size: 14px; font-weight: bold; color: #854d0e; background: transparent;")
            names = ", ".join(self.increment_names) + (" …" if self.increment_count > 3 else "")
            am = QLabel(t("salary_increment_prompt", count=self.increment_count) + f"  ({names})")
            am.setStyleSheet("font-size: 13px; color: #a16207; background: transparent;")
            tc.addWidget(at)
            tc.addWidget(am)
            al.addLayout(tc)
            al.addStretch()

            rev_btn = QPushButton("  " + t("review_increments"))
            rev_btn.setIcon(qta.icon("fa5s.check-circle", color="white"))
            rev_btn.setIconSize(_ICO)
            rev_btn.setFixedHeight(34)
            rev_btn.setCursor(Qt.PointingHandCursor)
            rev_btn.setStyleSheet(
                "QPushButton { background: #ca8a04; color: white; border: none;"
                " border-radius: 6px; font-size: 13px; font-weight: 600; padding: 0 14px; }"
                " QPushButton:hover { background: #a16207; }"
            )
            rev_btn.clicked.connect(self._open_increment_dialog)
            al.addWidget(rev_btn)
            layout.addWidget(alert)

        # ── Stat cards ────────────────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)

        stats = [
            (t("total_employees"),     self.emp_count,      "#3b82f6", "fa5s.users"),
            (t("promotions_total"),    self.promotion_count, "#10b981", "fa5s.chart-line"),
            (t("commendations_total"), self.commend_count,  "#f59e0b", "fa5s.award"),
            (t("active_sanctions"),    self.sanction_count,  "#ef4444", "fa5s.exclamation-triangle"),
        ]
        for i, (label, value, color, icon_name) in enumerate(stats):
            card = self._stat_card(label, str(value), color, icon_name)
            grid.addWidget(card, 0, i)
        layout.addLayout(grid)

        # ── Bottom section ────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # Recent activity card
        act_card = QFrame()
        act_card.setStyleSheet(CARD_SS)
        acl = QVBoxLayout(act_card)
        acl.setContentsMargins(24, 20, 24, 20)
        acl.setSpacing(0)

        ach = QHBoxLayout()
        act_title = QLabel(t("recent_activity"))
        act_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #111827; background: transparent;")
        va_btn = QPushButton(t("view_all"))
        va_btn.setCursor(Qt.PointingHandCursor)
        va_btn.setStyleSheet(btn_ghost(28))
        va_btn.clicked.connect(lambda: self.navigate("audit_log"))
        ach.addWidget(act_title)
        ach.addStretch()
        ach.addWidget(va_btn)
        acl.addLayout(ach)
        acl.addSpacing(12)

        ACTION_COLORS = {
            "employee": "#2563eb", "promotion": "#10b981",
            "commendation": "#f59e0b", "sanction": "#ef4444",
            "salary": "#8b5cf6", "import": "#06b6d4",
        }
        if self.logs_data:
            for action, desc, ts in self.logs_data:
                color = "#9ca3af"
                for k, v in ACTION_COLORS.items():
                    if k in action.lower():
                        color = v
                        break
                acl.addWidget(self._activity_row(action, desc, ts, color))
        else:
            empty = QLabel("No activity yet")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9ca3af; font-size: 13px; padding: 20px; background: transparent;")
            acl.addWidget(empty)
        acl.addStretch()
        bottom.addWidget(act_card, 3)

        # Upcoming promotions card
        promo_card = QFrame()
        promo_card.setStyleSheet(CARD_SS)
        pcl = QVBoxLayout(promo_card)
        pcl.setContentsMargins(24, 20, 24, 20)
        pcl.setSpacing(0)

        pch = QHBoxLayout()
        promo_title = QLabel(t("upcoming_promotions"))
        promo_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #111827; background: transparent;")
        vp_btn = QPushButton(t("view_all"))
        vp_btn.setCursor(Qt.PointingHandCursor)
        vp_btn.setStyleSheet(btn_ghost(28))
        vp_btn.clicked.connect(lambda: self.navigate("promotions"))
        pch.addWidget(promo_title)
        pch.addStretch()
        pch.addWidget(vp_btn)
        pcl.addLayout(pch)
        pcl.addSpacing(12)

        empty_p = QLabel("Navigate to Promotions to\nsee eligible employees.")
        empty_p.setAlignment(Qt.AlignCenter)
        empty_p.setStyleSheet("color: #9ca3af; font-size: 13px; padding: 32px; background: transparent;")
        pcl.addWidget(empty_p)
        pcl.addStretch()
        bottom.addWidget(promo_card, 2)

        layout.addLayout(bottom)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _open_increment_dialog(self):
        SalaryIncrementReviewDialog(self.increment_data, self.user, parent=self).exec()

    def _stat_card(self, label, value, color, icon_name):
        card = QFrame()
        card.setFixedHeight(108)
        card.setStyleSheet(CARD_SS)
        cl = QHBoxLayout(card)
        cl.setContentsMargins(20, 0, 20, 0)
        cl.setSpacing(16)

        ico_box = QLabel()
        ico_box.setFixedSize(48, 48)
        ico_box.setAlignment(Qt.AlignCenter)
        ico_box.setStyleSheet(f"background: {color}1a; border-radius: 12px;")
        ico_box.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))
        cl.addWidget(ico_box)

        txt = QVBoxLayout()
        txt.setSpacing(2)
        v = QLabel(value)
        v.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {color}; background: transparent;")
        l = QLabel(label)
        l.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        txt.addWidget(v)
        txt.addWidget(l)
        cl.addLayout(txt)
        cl.addStretch()
        return card

    def _activity_row(self, action, desc, ts, color):
        row = QFrame()
        row.setFixedHeight(52)
        row.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #f3f4f6;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px; min-width: 8px; max-width: 8px;")
        rl.addWidget(dot)

        ac = QLabel(action.replace(".", " › ").replace("_", " ").title())
        ac.setFixedWidth(170)
        ac.setStyleSheet("font-size: 13px; font-weight: 600; color: #111827; background: transparent;")
        rl.addWidget(ac)

        dl = QLabel(desc[:48] + "…" if len(desc) > 48 else desc)
        dl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        rl.addWidget(dl)
        rl.addStretch()

        tl = QLabel(ts)
        tl.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")
        rl.addWidget(tl)
        return row
