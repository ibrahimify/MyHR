"""
Commendations Page
- Issue single or bulk (team) commendations
- 3 categories: Cat1=-1mo, Cat2=-3mo, Cat3=-6mo
- Max 3 commendations per employee per role (enforced)
- Unique auto-generated ID per commendation
- History view
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QLineEdit, QComboBox, QTextEdit,
    QMessageBox, QCheckBox, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, generate_commendation_ref, log_action,
    can_receive_commendation, count_commendations_in_current_role
)
from src.database.models import Employee, Commendation, CommendationEmployee
from datetime import datetime


CATEGORIES = {
    1: {"label": "Category 1", "months": -1, "desc": "Good performance recognition",  "color": "#10b981", "bg": "#dcfce7"},
    2: {"label": "Category 2", "months": -3, "desc": "Excellent achievement",          "color": "#4f6ef7", "bg": "#eef2ff"},
    3: {"label": "Category 3", "months": -6, "desc": "Outstanding / exceptional work", "color": "#8b5cf6", "bg": "#f3e8ff"},
}


class CommendationsPage(QWidget):
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
        title = QLabel(t("commendations_title"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a1d2e;")
        h.addWidget(title)
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

        self.issue_tab   = IssueCommendationTab(self.user, self._on_issued)
        self.history_tab = CommendationHistoryTab(self.user)

        self.tabs.addTab(self.issue_tab,   t("issue_commendation"))
        self.tabs.addTab(self.history_tab, t("commendation_history"))
        self.tabs.currentChanged.connect(lambda i: self.history_tab.refresh() if i == 1 else None)
        layout.addWidget(self.tabs)

    def _on_issued(self):
        self.tabs.setCurrentIndex(1)
        self.history_tab.refresh()

    def showEvent(self, event):
        self.issue_tab.refresh_employees()
        super().showEvent(event)


# ── Issue Commendation Tab ────────────────────────────────────────────────────
class IssueCommendationTab(QWidget):
    def __init__(self, user, on_issued):
        super().__init__()
        self.user = user
        self.on_issued = on_issued
        self.selected_employees = set()
        self.mode = "single"
        self.setStyleSheet("background: #f4f6fb;")
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        content.setStyleSheet("background: #f4f6fb;")
        main = QHBoxLayout(content)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(20)
        main.setAlignment(Qt.AlignTop)

        # ── Left: form ────────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(16)

        # Mode selector
        mode_card = QFrame()
        mode_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        mc = QVBoxLayout(mode_card)
        mc.setContentsMargins(20, 16, 20, 16)
        mc.setSpacing(10)
        mc_title = QLabel("Commendation Type")
        mc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1d2e; background: transparent;")
        mc.addWidget(mc_title)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self.single_btn = QPushButton("👤  Single Employee")
        self.single_btn.setFixedHeight(52)
        self.single_btn.setCursor(Qt.PointingHandCursor)
        self.single_btn.clicked.connect(lambda: self._set_mode("single"))

        self.bulk_btn = QPushButton("👥  Team Award")
        self.bulk_btn.setFixedHeight(52)
        self.bulk_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_btn.clicked.connect(lambda: self._set_mode("bulk"))

        mode_row.addWidget(self.single_btn)
        mode_row.addWidget(self.bulk_btn)
        mc.addLayout(mode_row)
        left.addWidget(mode_card)

        # Details card
        details_card = QFrame()
        details_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        dc = QVBoxLayout(details_card)
        dc.setContentsMargins(20, 16, 20, 16)
        dc.setSpacing(12)

        dc_title = QLabel("Commendation Details")
        dc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1d2e; background: transparent;")
        dc.addWidget(dc_title)

        input_style = "QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #1a1d2e; background: #f9fafb; } QLineEdit:focus { border-color: #4f6ef7; background: white; }"
        combo_style = "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px; font-size: 13px; color: #1a1d2e; background: #f9fafb; } QComboBox::drop-down { border: none; }"
        ta_style    = "QTextEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px; font-size: 13px; color: #1a1d2e; background: #f9fafb; } QTextEdit:focus { border-color: #4f6ef7; background: white; }"

        title_lbl = QLabel("Award Title *")
        title_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Project Excellence Award")
        self.title_input.setFixedHeight(36)
        self.title_input.setStyleSheet(input_style)
        dc.addWidget(title_lbl)
        dc.addWidget(self.title_input)

        cat_lbl = QLabel(t("commendation_category") + " *")
        cat_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(36)
        self.cat_combo.setStyleSheet(combo_style)
        self.cat_combo.addItem("— Select category —", None)
        for cat_id, cat in CATEGORIES.items():
            self.cat_combo.addItem(f"{cat['label']} (−{abs(cat['months'])} month{'s' if abs(cat['months']) > 1 else ''})", cat_id)
        dc.addWidget(cat_lbl)
        dc.addWidget(self.cat_combo)

        desc_lbl = QLabel("Description *")
        desc_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(90)
        self.desc_input.setPlaceholderText("Describe the achievement or reason...")
        self.desc_input.setStyleSheet(ta_style)
        dc.addWidget(desc_lbl)
        dc.addWidget(self.desc_input)
        left.addWidget(details_card)

        # Employee selection card
        emp_card = QFrame()
        emp_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        ec = QVBoxLayout(emp_card)
        ec.setContentsMargins(20, 16, 20, 16)
        ec.setSpacing(8)

        self.emp_card_title = QLabel("Select Employee")
        self.emp_card_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1d2e; background: transparent;")
        ec.addWidget(self.emp_card_title)

        # Single employee combo
        self.single_combo = QComboBox()
        self.single_combo.setFixedHeight(36)
        self.single_combo.setStyleSheet(combo_style)
        ec.addWidget(self.single_combo)

        # Bulk employee checkboxes container
        self.bulk_scroll = QScrollArea()
        self.bulk_scroll.setFixedHeight(200)
        self.bulk_scroll.setWidgetResizable(True)
        self.bulk_scroll.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 8px;")
        self.bulk_container = QWidget()
        self.bulk_container.setStyleSheet("background: white;")
        self.bulk_layout = QVBoxLayout(self.bulk_container)
        self.bulk_layout.setContentsMargins(8, 8, 8, 8)
        self.bulk_layout.setSpacing(4)
        self.bulk_scroll.setWidget(self.bulk_container)
        ec.addWidget(self.bulk_scroll)

        self.selected_count_lbl = QLabel("0 selected")
        self.selected_count_lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        ec.addWidget(self.selected_count_lbl)
        left.addWidget(emp_card)
        main.addLayout(left, 3)

        # ── Right: sidebar ────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Category impact info
        impact_card = QFrame()
        impact_card.setStyleSheet("background: #eef2ff; border-radius: 12px; border: 1px solid #c7d2fe;")
        ic = QVBoxLayout(impact_card)
        ic.setContentsMargins(16, 14, 16, 14)
        ic.setSpacing(10)

        ic_title = QLabel(t("promotion_track_impact"))
        ic_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #3730a3; background: transparent;")
        ic.addWidget(ic_title)

        for cat_id, cat in CATEGORIES.items():
            row = QFrame()
            row.setStyleSheet(f"background: white; border-radius: 6px; border: 1px solid {cat['color']}40;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 8, 10, 8)
            name = QLabel(cat["label"])
            name.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {cat['color']}; background: transparent;")
            badge = QLabel(f"−{abs(cat['months'])} mo")
            badge.setStyleSheet(f"background: {cat['bg']}; color: {cat['color']}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            desc = QLabel(cat["desc"])
            desc.setStyleSheet(f"font-size: 11px; color: #6b7280; background: transparent;")
            rl.addWidget(name)
            rl.addStretch()
            rl.addWidget(badge)
            ic.addWidget(row)
            ic.addWidget(desc)

        right.addWidget(impact_card)

        # Rules card
        rules_card = QFrame()
        rules_card.setStyleSheet("background: #fefce8; border-radius: 12px; border: 1px solid #fde047;")
        rc = QVBoxLayout(rules_card)
        rc.setContentsMargins(16, 14, 16, 14)
        rc.setSpacing(6)
        rc_title = QLabel("Important Rules")
        rc_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #854d0e; background: transparent;")
        rc.addWidget(rc_title)
        for rule in [
            "Max 3 commendations per employee per role",
            "Each commendation gets a unique auto-generated ID",
            "Commendations reset after promotion",
            "Recorded in audit log",
        ]:
            lbl = QLabel(f"• {rule}")
            lbl.setStyleSheet("font-size: 12px; color: #a16207; background: transparent;")
            rc.addWidget(lbl)
        right.addWidget(rules_card)

        # Issue button
        issue_btn = QPushButton("★  Issue Commendation")
        issue_btn.setCursor(Qt.PointingHandCursor)
        issue_btn.setFixedHeight(44)
        issue_btn.setStyleSheet("QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #3a57e8; }")
        issue_btn.clicked.connect(self._issue)
        right.addWidget(issue_btn)

        clear_btn = QPushButton("Clear Form")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(36)
        clear_btn.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 8px; font-size: 13px; } QPushButton:hover { background: #e5e7eb; }")
        clear_btn.clicked.connect(self._clear)
        right.addWidget(clear_btn)

        main.addLayout(right, 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._set_mode("single")
        self.checkboxes = []

    def _set_mode(self, mode):
        self.mode = mode
        active   = "QPushButton { background: #eef2ff; color: #4f6ef7; border: 2px solid #4f6ef7; border-radius: 8px; font-size: 13px; font-weight: bold; }"
        inactive = "QPushButton { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; }"
        self.single_btn.setStyleSheet(active if mode == "single" else inactive)
        self.bulk_btn.setStyleSheet(active if mode == "bulk" else inactive)
        self.single_combo.setVisible(mode == "single")
        self.bulk_scroll.setVisible(mode == "bulk")
        self.selected_count_lbl.setVisible(mode == "bulk")
        self.emp_card_title.setText("Select Employee" if mode == "single" else "Select Employees")

    def refresh_employees(self):
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            emp_data = [{
                "id": e.id,
                "label": f"{e.employee_id} — {e.full_name} ({e.title.name if e.title else '?'})",
                "can": can_receive_commendation(e, session),
                "count": count_commendations_in_current_role(e, session),
            } for e in emps]
        finally:
            session.close()

        # Single combo
        self.single_combo.clear()
        self.single_combo.addItem("— Select employee —", None)
        for e in emp_data:
            suffix = f"  [{e['count']}/3]" + (" ⚠ Max reached" if not e["can"] else "")
            self.single_combo.addItem(e["label"] + suffix, e["id"] if e["can"] else None)

        # Bulk checkboxes
        while self.bulk_layout.count():
            item = self.bulk_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.checkboxes = []
        self.selected_employees = set()

        for e in emp_data:
            cb = QCheckBox(e["label"] + f"  [{e['count']}/3 commendations]")
            cb.setStyleSheet("font-size: 12px; color: #1a1d2e; padding: 4px;")
            if not e["can"]:
                cb.setEnabled(False)
                cb.setStyleSheet("font-size: 12px; color: #9ca3af; padding: 4px;")
            cb.setProperty("emp_id", e["id"])
            cb.stateChanged.connect(self._on_checkbox_change)
            self.bulk_layout.addWidget(cb)
            self.checkboxes.append(cb)

        self.bulk_layout.addStretch()

    def _on_checkbox_change(self):
        self.selected_employees = {
            cb.property("emp_id") for cb in self.checkboxes
            if cb.isChecked() and cb.isEnabled()
        }
        self.selected_count_lbl.setText(f"{len(self.selected_employees)} selected")

    def _clear(self):
        self.title_input.clear()
        self.desc_input.clear()
        self.cat_combo.setCurrentIndex(0)
        self.single_combo.setCurrentIndex(0)
        for cb in self.checkboxes:
            cb.setChecked(False)
        self.selected_employees = set()

    def _issue(self):
        title_text = self.title_input.text().strip()
        desc_text  = self.desc_input.toPlainText().strip()
        cat_id     = self.cat_combo.currentData()

        if not title_text:
            QMessageBox.warning(self, t("warning"), "Award title is required.")
            return
        if not cat_id:
            QMessageBox.warning(self, t("warning"), "Please select a commendation category.")
            return
        if not desc_text:
            QMessageBox.warning(self, t("warning"), "Description is required.")
            return

        if self.mode == "single":
            emp_id = self.single_combo.currentData()
            if not emp_id:
                QMessageBox.warning(self, t("warning"), "Please select an employee.")
                return
            target_ids = [emp_id]
        else:
            if not self.selected_employees:
                QMessageBox.warning(self, t("warning"), "Please select at least one employee.")
                return
            target_ids = list(self.selected_employees)

        cat = CATEGORIES[cat_id]

        session = get_session()
        try:
            # Final cap check
            blocked = []
            for eid in target_ids:
                emp = session.query(Employee).filter_by(id=eid).first()
                if not can_receive_commendation(emp, session):
                    blocked.append(emp.full_name)

            if blocked:
                QMessageBox.warning(self, t("warning"),
                    f"Max 3 commendations reached for: {', '.join(blocked)}\nRemove them from selection.")
                return

            ref = generate_commendation_ref(session)
            comm = Commendation(
                commendation_ref=ref,
                title=title_text,
                description=desc_text,
                category=cat_id,
                months_impact=cat["months"],
                is_team_award=(len(target_ids) > 1),
                issued_by_id=self.user.id,
            )
            session.add(comm)
            session.flush()

            for eid in target_ids:
                session.add(CommendationEmployee(commendation_id=comm.id, employee_id=eid))

            names = []
            for eid in target_ids:
                emp = session.query(Employee).filter_by(id=eid).first()
                names.append(emp.full_name)

            log_action(session, self.user.id, "commendation.issue", "commendation", comm.id,
                description=f"Commendation issued [{ref}]: '{title_text}' (Cat {cat_id}, {cat['months']}mo) to {', '.join(names)}")

            session.commit()
            QMessageBox.information(self, t("success"),
                f"Commendation [{ref}] issued successfully!\n{cat['label']}: {cat['months']} months to promotion race for {len(target_ids)} employee(s).")
            self._clear()
            self.refresh_employees()
            self.on_issued()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── History Tab ───────────────────────────────────────────────────────────────
class CommendationHistoryTab(QWidget):
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("commendation_id"), "Title", "Category", "Promotion Impact",
            "Recipients", "Issued By", "Date"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; font-size: 13px; color: #1a1d2e; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #1a1d2e; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            comms = session.query(Commendation).order_by(Commendation.issued_at.desc()).all()
            rows = []
            for c in comms:
                recipients = ", ".join(e.full_name for e in c.employees)
                cat = CATEGORIES.get(c.category, {})
                rows.append({
                    "ref": c.commendation_ref,
                    "title": c.title,
                    "category": cat.get("label", f"Cat {c.category}"),
                    "impact": f"−{abs(c.months_impact)} month{'s' if abs(c.months_impact) > 1 else ''}",
                    "recipients": recipients,
                    "issued_by": c.issued_by.full_name,
                    "date": c.issued_at.strftime("%Y-%m-%d") if c.issued_at else "—",
                    "cat_id": c.category,
                })
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 48)

            ref_item = QTableWidgetItem(row["ref"])
            ref_item.setForeground(QColor("#6b7280"))
            self.table.setItem(i, 0, ref_item)
            self.table.setItem(i, 1, QTableWidgetItem(row["title"]))

            cat = CATEGORIES.get(row["cat_id"], {})
            cat_item = QTableWidgetItem(row["category"])
            cat_item.setBackground(QColor(cat.get("bg", "#f9fafb")))
            cat_item.setForeground(QColor(cat.get("color", "#374151")))
            self.table.setItem(i, 2, cat_item)

            impact_item = QTableWidgetItem(row["impact"])
            impact_item.setForeground(QColor("#10b981"))
            self.table.setItem(i, 3, impact_item)

            self.table.setItem(i, 4, QTableWidgetItem(row["recipients"]))
            self.table.setItem(i, 5, QTableWidgetItem(row["issued_by"]))
            self.table.setItem(i, 6, QTableWidgetItem(row["date"]))