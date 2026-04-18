"""
Promotions Page
- Eligible employees tracker (live race calculation)
- Promotion history
- Configurable promotion rules (base months per level transition)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout,
    QLineEdit, QComboBox, QMessageBox, QSpinBox, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, log_action, calculate_months_remaining
)
from src.database.models import (
    Employee, Title, PromotionRule, PromotionHistory, Commendation,
    CommendationEmployee, Sanction
)
from datetime import datetime


class PromotionsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f4f6fb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background: white; border-bottom: 1px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        title = QLabel(t("promotions_title"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a1d2e;")
        sub = QLabel(t("promotions_subtitle"))
        sub.setStyleSheet("font-size: 12px; color: #9ca3af; margin-left: 12px;")
        h.addWidget(title)
        h.addWidget(sub)
        h.addStretch()
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f4f6fb; }
            QTabBar::tab { background: white; color: #6b7280; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; font-size: 13px; }
            QTabBar::tab:selected { color: #4f6ef7; border-bottom: 2px solid #4f6ef7; font-weight: bold; }
            QTabBar::tab:hover { color: #1a1d2e; }
        """)

        self.eligible_tab = EligibleTab(self.user)
        self.history_tab  = HistoryTab(self.user)
        self.rules_tab    = RulesTab(self.user)

        self.tabs.addTab(self.eligible_tab, "Eligible Employees")
        self.tabs.addTab(self.history_tab,  "Promotion History")
        self.tabs.addTab(self.rules_tab,    "Promotion Rules")

        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs)

    def _on_tab_change(self, index):
        if index == 0:
            self.eligible_tab.refresh()
        elif index == 1:
            self.history_tab.refresh()
        elif index == 2:
            self.rules_tab.refresh()

    def showEvent(self, event):
        self.eligible_tab.refresh()
        super().showEvent(event)


# ── Eligible Employees Tab ────────────────────────────────────────────────────
class EligibleTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f4f6fb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Race explanation banner
        banner = QFrame()
        banner.setStyleSheet("background: #eef2ff; border-radius: 10px; border: 1px solid #c7d2fe;")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(10)
        icon = QLabel("🏁")
        icon.setStyleSheet("font-size: 20px; background: transparent;")
        text = QLabel(t("race_explanation"))
        text.setStyleSheet("font-size: 13px; color: #3730a3; background: transparent;")
        text.setWordWrap(True)
        bl.addWidget(icon)
        bl.addWidget(text, 1)
        layout.addWidget(banner)

        # Stat cards
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        layout.addLayout(self.stats_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Current Level", "Next Level",
            "Months Elapsed", "Commendation −months",
            "Sanction +months", "Months Remaining", "Actions"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; gridline-color: #f3f4f6; font-size: 13px; color: #1a1d2e; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #1a1d2e; }
            QTableWidget::item:selected { background: #eef2ff; color: #1a1d2e; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        # Clear stats
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            employees = session.query(Employee).filter_by(status="active").all()
            rows = []
            eligible_count = soon_count = progress_count = 0

            for emp in employees:
                race = calculate_months_remaining(emp, session)
                if not race["has_next_level"]:
                    continue

                mr = race["months_remaining"]
                if mr == 0:
                    status = "eligible"
                    eligible_count += 1
                elif mr <= 6:
                    status = "soon"
                    soon_count += 1
                else:
                    status = "progress"
                    progress_count += 1

                rows.append({
                    "id": emp.id,
                    "name": emp.full_name,
                    "emp_id": emp.employee_id,
                    "current": emp.title.name if emp.title else "—",
                    "next": session.query(Title).filter_by(id=race["next_title_id"]).first().name if race["next_title_id"] else "—",
                    "elapsed": race["months_elapsed"],
                    "comm_reduction": race["commendation_reduction"],
                    "sanction_addition": race["sanction_addition"],
                    "months_remaining": mr,
                    "status": status,
                })
        finally:
            session.close()

        # Stat cards
        for label, val, color in [
            (t("eligible_now"),  eligible_count, "#10b981"),
            (t("eligible_soon"), soon_count,     "#f59e0b"),
            (t("in_progress"),   progress_count, "#4f6ef7"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"background: white; border-radius: 10px; border: 1px solid #e5e7eb;")
            card.setFixedHeight(80)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(16, 0, 16, 0)
            v = QLabel(str(val))
            v.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
            l = QLabel(label)
            l.setStyleSheet("font-size: 12px; color: #9ca3af;")
            col = QVBoxLayout()
            col.addWidget(v)
            col.addWidget(l)
            cl.addLayout(col)
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        # Populate table
        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.table.setRowHeight(row_idx, 50)

            # Employee name + ID
            name_item = QTableWidgetItem(f"{row['name']}\n{row['emp_id']}")
            name_item.setData(Qt.UserRole, row["id"])
            self.table.setItem(row_idx, 0, name_item)

            self.table.setItem(row_idx, 1, self._badge_item(row["current"], "#dbeafe", "#1e40af"))
            self.table.setItem(row_idx, 2, self._badge_item(row["next"], "#dcfce7", "#166534"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{row['elapsed']} mo"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"−{row['comm_reduction']} mo"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"+{row['sanction_addition']} mo"))

            mr = row["months_remaining"]
            if mr == 0:
                mr_item = self._badge_item("✅ Eligible!", "#dcfce7", "#166534")
            elif mr <= 6:
                mr_item = self._badge_item(f"{mr} months", "#fef9c3", "#854d0e")
            else:
                mr_item = QTableWidgetItem(f"{mr} months")
            self.table.setItem(row_idx, 6, mr_item)

            # Action button
            if row["status"] == "eligible":
                btn = QPushButton("Approve ↑")
                btn.setStyleSheet("QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; margin: 8px; } QPushButton:hover { background: #3a57e8; }")
                btn.clicked.connect(lambda _, eid=row["id"]: self._approve_promotion(eid))
            else:
                btn = QPushButton("View")
                btn.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 6px; font-size: 12px; margin: 8px; } QPushButton:hover { background: #e5e7eb; }")
            self.table.setCellWidget(row_idx, 7, btn)

    def _badge_item(self, text, bg, fg):
        item = QTableWidgetItem(text)
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        return item

    def _approve_promotion(self, employee_id):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_id).first()
            race = calculate_months_remaining(emp, session)

            if not race["eligible"]:
                QMessageBox.warning(self, t("warning"), "Employee is not yet eligible.")
                return

            next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
            old_title  = emp.title

            confirm = QMessageBox.question(self, "Confirm Promotion",
                f"Promote {emp.full_name}\nfrom {old_title.name} → {next_title.name}?",
                QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return

            # Apply promotion
            emp.title_id = next_title.id

            history = PromotionHistory(
                employee_id=emp.id,
                from_title_id=old_title.id,
                to_title_id=next_title.id,
                approved_by_id=self.user.id,
                basis="accelerated" if race["commendation_reduction"] > 0 else "time_based",
                months_taken=race["months_elapsed"],
                notes=f"Commendation reduction: {race['commendation_reduction']}mo, Sanction addition: {race['sanction_addition']}mo",
            )
            session.add(history)

            log_action(session, self.user.id, "promotion.approve", "employee", emp.id,
                description=f"Promoted {emp.full_name}: {old_title.name} → {next_title.name}",
                before_value=f'{{"title": "{old_title.name}"}}',
                after_value=f'{{"title": "{next_title.name}"}}',
            )
            session.commit()
            QMessageBox.information(self, t("success"),
                f"{emp.full_name} promoted to {next_title.name}!\nPromotion race clock has been reset.")
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── History Tab ───────────────────────────────────────────────────────────────
class HistoryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f4f6fb;")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Promotion", "Basis", "Months Taken", "Approved By", "Date"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; font-size: 13px; color: #1a1d2e; }
            QTableWidget::item { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; color: #1a1d2e; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            history = session.query(PromotionHistory).order_by(
                PromotionHistory.promoted_at.desc()
            ).all()
            rows = [{
                "name": h.employee.full_name,
                "emp_id": h.employee.employee_id,
                "from": h.from_title.name,
                "to": h.to_title.name,
                "basis": h.basis.replace("_", " ").title(),
                "months": str(h.months_taken) + " mo" if h.months_taken else "—",
                "approved_by": h.approved_by.full_name,
                "date": h.promoted_at.strftime("%Y-%m-%d") if h.promoted_at else "—",
            } for h in history]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 48)
            self.table.setItem(i, 0, QTableWidgetItem(f"{row['name']} ({row['emp_id']})"))
            promo = QTableWidgetItem(f"{row['from']}  →  {row['to']}")
            promo.setForeground(QColor("#10b981"))
            self.table.setItem(i, 1, promo)
            self.table.setItem(i, 2, QTableWidgetItem(row["basis"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["months"]))
            self.table.setItem(i, 4, QTableWidgetItem(row["approved_by"]))
            self.table.setItem(i, 5, QTableWidgetItem(row["date"]))


# ── Rules Tab ─────────────────────────────────────────────────────────────────
class RulesTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f4f6fb;")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Modifiers info
        info = QFrame()
        info.setStyleSheet("background: #fefce8; border-radius: 10px; border: 1px solid #fde047;")
        il = QVBoxLayout(info)
        il.setContentsMargins(16, 12, 16, 12)
        t1 = QLabel("Track Modifiers (Optional)")
        t1.setStyleSheet("font-size: 13px; font-weight: bold; color: #854d0e; background: transparent;")
        t2 = QLabel("• Commendations reduce months remaining (Cat 1: −1mo, Cat 2: −3mo, Cat 3: −6mo)\n• Sanctions add months to the race (+1 to +12 months)\n• After promotion, the clock resets to zero — no carryover")
        t2.setStyleSheet("font-size: 12px; color: #a16207; background: transparent;")
        il.addWidget(t1)
        il.addWidget(t2)
        layout.addWidget(info)

        # Rules table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Level Transition", "Base Track Duration (months)",
            "Salary Increase on Promotion", "Status", "Actions"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; font-size: 13px; color: #1a1d2e; }
            QTableWidget::item { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; color: #1a1d2e; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            rules = session.query(PromotionRule).all()
            rows = [{
                "id": r.id,
                "transition": f"{r.from_title.name}  →  {r.to_title.name}",
                "base_months": r.base_months,
                "salary_increase": f"{r.to_title.promotion_salary_increase_pct}%",
                "active": r.is_active,
            } for r in rules]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 48)
            trans = QTableWidgetItem(row["transition"])
            trans.setForeground(QColor("#4f6ef7"))
            trans.setFont(self._bold_font())
            self.table.setItem(i, 0, trans)
            self.table.setItem(i, 1, QTableWidgetItem(str(row["base_months"]) + " months"))
            self.table.setItem(i, 2, QTableWidgetItem(row["salary_increase"]))

            status = QTableWidgetItem("Active" if row["active"] else "Inactive")
            status.setForeground(QColor("#10b981") if row["active"] else QColor("#ef4444"))
            self.table.setItem(i, 3, status)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("QPushButton { background: #eef2ff; color: #4f6ef7; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; margin: 8px; } QPushButton:hover { background: #e0e7ff; }")
            edit_btn.clicked.connect(lambda _, rid=row["id"]: self._edit_rule(rid))
            self.table.setCellWidget(i, 4, edit_btn)

    def _bold_font(self):
        from PySide6.QtGui import QFont
        f = QFont()
        f.setBold(True)
        return f

    def _edit_rule(self, rule_id):
        dialog = RuleEditDialog(self.user, rule_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()


class RuleEditDialog(QDialog):
    def __init__(self, user, rule_id, parent=None):
        super().__init__(parent)
        self.user = user
        self.rule_id = rule_id
        self.setWindowTitle("Edit Promotion Rule")
        self.setFixedWidth(420)
        self.setStyleSheet("background: white; color: #1a1d2e;")
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Promotion Rule")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1d2e;")
        layout.addWidget(title)

        self.transition_lbl = QLabel("")
        self.transition_lbl.setStyleSheet("font-size: 14px; color: #4f6ef7; font-weight: bold;")
        layout.addWidget(self.transition_lbl)

        input_style = "QSpinBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #1a1d2e; background: #f9fafb; min-height: 36px; }"

        form = QFormLayout()
        form.setSpacing(10)

        self.months_spin = QSpinBox()
        self.months_spin.setRange(1, 120)
        self.months_spin.setStyleSheet(input_style)
        form.addRow("Base Track Duration (months) *", self.months_spin)

        layout.addLayout(form)

        note = QLabel("Commendations and sanctions are optional modifiers applied on top of this base duration.")
        note.setStyleSheet("font-size: 11px; color: #9ca3af;")
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(36)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 8px; padding: 0 20px; } QPushButton:hover { background: #e5e7eb; }")
        cancel.clicked.connect(self.reject)

        save = QPushButton(t("save"))
        save.setFixedHeight(36)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet("QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 8px; padding: 0 20px; font-weight: bold; } QPushButton:hover { background: #3a57e8; }")
        save.clicked.connect(self._save)

        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _load(self):
        session = get_session()
        try:
            rule = session.query(PromotionRule).filter_by(id=self.rule_id).first()
            if rule:
                self.transition_lbl.setText(f"{rule.from_title.name} → {rule.to_title.name}")
                self.months_spin.setValue(rule.base_months)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            rule = session.query(PromotionRule).filter_by(id=self.rule_id).first()
            old_months = rule.base_months
            rule.base_months = self.months_spin.value()
            log_action(session, self.user.id, "promotion_rule.update", "promotion_rule", self.rule_id,
                description=f"Promotion rule updated: base months {old_months} → {rule.base_months}",
                before_value=f'{{"base_months": {old_months}}}',
                after_value=f'{{"base_months": {rule.base_months}}}',
            )
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()