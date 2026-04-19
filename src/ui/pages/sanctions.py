"""
Sanctions Page
- Issue sanctions with 1-12 month promotion delay
- Unique auto-generated SAN- ID per sanction
- Active sanctions table
- History of resolved sanctions
- Shows clearly how many months added to promotion race
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QTextEdit,
    QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import get_session, generate_sanction_ref, log_action
from src.database.models import Employee, Sanction
from datetime import datetime


SANCTION_TYPES = [
    ("verbal_warning",  "Verbal Warning",  "#f59e0b", "#fefce8"),
    ("written_warning", "Written Warning", "#ef4444", "#fef2f2"),
    ("suspension",      "Suspension",      "#dc2626", "#fef2f2"),
    ("final_warning",   "Final Warning",   "#991b1b", "#fef2f2"),
]


class SanctionsPage(QWidget):
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
        title = QLabel(t("sanctions_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        h.addWidget(title)
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

        self.active_tab  = ActiveSanctionsTab(self.user)
        self.history_tab = SanctionHistoryTab(self.user)
        self.issue_tab   = IssueSanctionTab(self.user, self._on_issued)

        self.tabs.addTab(self.active_tab,  "Active Sanctions")
        self.tabs.addTab(self.history_tab, "Sanction History")
        self.tabs.addTab(self.issue_tab,   "Issue Sanction")

        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs)

    def _on_tab_change(self, index):
        if index == 0:
            self.active_tab.refresh()
        elif index == 1:
            self.history_tab.refresh()
        elif index == 2:
            self.issue_tab.refresh_employees()

    def _on_issued(self):
        self.tabs.setCurrentIndex(0)
        self.active_tab.refresh()

    def showEvent(self, event):
        self.active_tab.refresh()
        super().showEvent(event)


# ── Active Sanctions Tab ──────────────────────────────────────────────────────
class ActiveSanctionsTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Stats row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        layout.addLayout(self.stats_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), "Employee", t("sanction_type"),
            "Reason", "Issue Date", "Promotion Delay", "Actions"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; font-size: 13px; color: #111827; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #111827; }
            QTableWidget::item:selected { background: #fef2f2; color: #111827; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            active = session.query(Sanction).filter_by(is_resolved=False).all()
            rows = [{
                "id": s.id,
                "ref": s.sanction_ref,
                "emp_name": s.employee.full_name,
                "emp_id": s.employee.employee_id,
                "type": s.sanction_type,
                "reason": s.reason,
                "date": s.issued_at.strftime("%Y-%m-%d") if s.issued_at else "—",
                "delay": s.delay_months,
            } for s in active]
        finally:
            session.close()

        # Stats
        for label, val, color, bg in [
            ("Active Sanctions",   len(rows), "#ef4444", "#fef2f2"),
            ("Total Delay Months", sum(r["delay"] for r in rows), "#f59e0b", "#fefce8"),
        ]:
            card = QFrame()
            card.setFixedHeight(80)
            card.setStyleSheet(f"background: white; border-radius: 10px; border: 1px solid #e5e7eb;")
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

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 50)

            ref_item = QTableWidgetItem(row["ref"])
            ref_item.setForeground(QColor("#6b7280"))
            self.table.setItem(i, 0, ref_item)

            self.table.setItem(i, 1, QTableWidgetItem(f"{row['emp_name']}\n{row['emp_id']}"))

            type_color = next(
                (c for st, _, c, _ in SANCTION_TYPES if st == row["type"]), "#374151"
            )
            type_bg = next(
                (b for st, _, _, b in SANCTION_TYPES if st == row["type"]), "#f9fafb"
            )
            type_item = QTableWidgetItem(row["type"].replace("_", " ").title())
            type_item.setBackground(QColor(type_bg))
            type_item.setForeground(QColor(type_color))
            self.table.setItem(i, 2, type_item)

            reason_item = QTableWidgetItem(row["reason"][:60] + "..." if len(row["reason"]) > 60 else row["reason"])
            self.table.setItem(i, 3, reason_item)
            self.table.setItem(i, 4, QTableWidgetItem(row["date"]))

            delay_item = QTableWidgetItem(f"+{row['delay']} month{'s' if row['delay'] != 1 else ''}")
            delay_item.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 5, delay_item)

            resolve_btn = QPushButton("✓ Mark Resolved")
            resolve_btn.setCursor(Qt.PointingHandCursor)
            resolve_btn.setStyleSheet("QPushButton { background: #dcfce7; color: #166534; border: none; border-radius: 6px; font-size: 11px; font-weight: bold; margin: 8px; } QPushButton:hover { background: #bbf7d0; }")
            resolve_btn.clicked.connect(lambda _, sid=row["id"]: self._resolve(sid))
            self.table.setCellWidget(i, 6, resolve_btn)

    def _resolve(self, sanction_id):
        confirm = QMessageBox.question(self, "Resolve Sanction",
            "Mark this sanction as resolved?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        session = get_session()
        try:
            s = session.query(Sanction).filter_by(id=sanction_id).first()
            s.is_resolved = True
            s.resolved_at = datetime.utcnow()
            log_action(session, self.user.id, "sanction.resolve", "sanction", sanction_id,
                description=f"Sanction {s.sanction_ref} marked as resolved for {s.employee.full_name}")
            session.commit()
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


# ── History Tab ───────────────────────────────────────────────────────────────
class SanctionHistoryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), "Employee", "Type", "Reason",
            "Issue Date", "Delay Applied", "Status"
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; font-size: 13px; color: #111827; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #111827; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            sanctions = session.query(Sanction).order_by(Sanction.issued_at.desc()).all()
            rows = [{
                "ref": s.sanction_ref,
                "emp": f"{s.employee.full_name} ({s.employee.employee_id})",
                "type": s.sanction_type.replace("_", " ").title(),
                "reason": s.reason[:60] + "..." if len(s.reason) > 60 else s.reason,
                "date": s.issued_at.strftime("%Y-%m-%d") if s.issued_at else "—",
                "delay": f"+{s.delay_months} month{'s' if s.delay_months != 1 else ''}",
                "resolved": s.is_resolved,
            } for s in sanctions]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)
            ref = QTableWidgetItem(row["ref"])
            ref.setForeground(QColor("#6b7280"))
            self.table.setItem(i, 0, ref)
            self.table.setItem(i, 1, QTableWidgetItem(row["emp"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["type"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["reason"]))
            self.table.setItem(i, 4, QTableWidgetItem(row["date"]))
            delay = QTableWidgetItem(row["delay"])
            delay.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 5, delay)
            status = QTableWidgetItem("Resolved" if row["resolved"] else "Active")
            status.setForeground(QColor("#10b981") if row["resolved"] else QColor("#ef4444"))
            self.table.setItem(i, 6, status)


# ── Issue Sanction Tab ────────────────────────────────────────────────────────
class IssueSanctionTab(QWidget):
    def __init__(self, user, on_issued):
        super().__init__()
        self.user = user
        self.on_issued = on_issued
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        main = QHBoxLayout(content)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(20)
        main.setAlignment(Qt.AlignTop)

        # ── Left: form ────────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(16)

        form_card = QFrame()
        form_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        fc = QVBoxLayout(form_card)
        fc.setContentsMargins(20, 16, 20, 20)
        fc.setSpacing(12)

        fc_title = QLabel("Issue New Sanction")
        fc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        fc.addWidget(fc_title)

        input_style = "QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #111827; background: #f9fafb; } QLineEdit:focus { border-color: #2563eb; background: white; }"
        combo_style = "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; color: #111827; background: #f9fafb; }"
        ta_style    = "QTextEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px; font-size: 13px; color: #111827; background: #f9fafb; } QTextEdit:focus { border-color: #2563eb; background: white; }"
        spin_style  = "QSpinBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px; font-size: 13px; color: #111827; background: #f9fafb; min-height: 36px; }"

        # Employee
        emp_lbl = QLabel("Select Employee *")
        emp_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.emp_combo = QComboBox()
        self.emp_combo.setFixedHeight(36)
        self.emp_combo.setStyleSheet(combo_style)
        fc.addWidget(emp_lbl)
        fc.addWidget(self.emp_combo)

        # Type
        type_lbl = QLabel("Sanction Type *")
        type_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(36)
        self.type_combo.setStyleSheet(combo_style)
        for val, label, _, _ in SANCTION_TYPES:
            self.type_combo.addItem(label, val)
        fc.addWidget(type_lbl)
        fc.addWidget(self.type_combo)

        # Reason
        reason_lbl = QLabel("Reason / Description *")
        reason_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(100)
        self.reason_input.setPlaceholderText("Describe the reason for this sanction...")
        self.reason_input.setStyleSheet(ta_style)
        fc.addWidget(reason_lbl)
        fc.addWidget(self.reason_input)

        # Delay months
        delay_lbl = QLabel("Promotion Delay (months) *")
        delay_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 12)
        self.delay_spin.setValue(1)
        self.delay_spin.setFixedHeight(36)
        self.delay_spin.setStyleSheet(spin_style)
        self.delay_spin.valueChanged.connect(self._update_delay_preview)
        fc.addWidget(delay_lbl)
        fc.addWidget(self.delay_spin)

        self.delay_preview = QLabel("+1 month will be added to the employee's promotion race")
        self.delay_preview.setStyleSheet("font-size: 12px; color: #ef4444; background: transparent;")
        fc.addWidget(self.delay_preview)

        left.addWidget(form_card)
        main.addLayout(left, 3)

        # ── Right: sidebar ────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Race impact info
        impact_card = QFrame()
        impact_card.setStyleSheet("background: #fef2f2; border-radius: 12px; border: 1px solid #fecaca;")
        ic = QVBoxLayout(impact_card)
        ic.setContentsMargins(16, 14, 16, 14)
        ic.setSpacing(8)
        ic_title = QLabel("Promotion Race Impact")
        ic_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #991b1b; background: transparent;")
        ic.addWidget(ic_title)
        for line in [
            "Sanctions delay the promotion race",
            "Duration range: 1–12 months",
            "Only active (unresolved) sanctions count",
            "Sanctions reset after promotion",
            "Each sanction gets a unique SAN- ID",
        ]:
            lbl = QLabel(f"• {line}")
            lbl.setStyleSheet("font-size: 12px; color: #b91c1c; background: transparent;")
            ic.addWidget(lbl)
        right.addWidget(impact_card)

        # Guidelines
        guide_card = QFrame()
        guide_card.setStyleSheet("background: #eff6ff; border-radius: 12px; border: 1px solid #bfdbfe;")
        gc = QVBoxLayout(guide_card)
        gc.setContentsMargins(16, 14, 16, 14)
        gc.setSpacing(6)
        gc_title = QLabel("Sanction Guidelines")
        gc_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; background: transparent;")
        gc.addWidget(gc_title)
        for stype, desc in [
            ("Verbal Warning",  "Minor violations → 1–2 months"),
            ("Written Warning", "Repeated violations → 3–6 months"),
            ("Suspension",      "Serious misconduct → 6–9 months"),
            ("Final Warning",   "Severe misconduct → 9–12 months"),
        ]:
            lbl = QLabel(f"• {stype}: {desc}")
            lbl.setStyleSheet("font-size: 12px; color: #1d4ed8; background: transparent;")
            gc.addWidget(lbl)
        right.addWidget(guide_card)

        # Issue button
        issue_btn = QPushButton("⚠  Issue Sanction")
        issue_btn.setCursor(Qt.PointingHandCursor)
        issue_btn.setFixedHeight(44)
        issue_btn.setStyleSheet("QPushButton { background: #dc2626; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #b91c1c; }")
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

    def refresh_employees(self):
        self.emp_combo.clear()
        self.emp_combo.addItem("— Select employee —", None)
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            for e in emps:
                self.emp_combo.addItem(f"{e.employee_id} — {e.full_name}", e.id)
        finally:
            session.close()

    def _update_delay_preview(self, val):
        self.delay_preview.setText(
            f"+{val} month{'s' if val != 1 else ''} will be added to the employee's promotion race"
        )

    def _clear(self):
        self.emp_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self.reason_input.clear()
        self.delay_spin.setValue(1)

    def _issue(self):
        emp_id = self.emp_combo.currentData()
        reason = self.reason_input.toPlainText().strip()
        delay  = self.delay_spin.value()

        if not emp_id:
            QMessageBox.warning(self, t("warning"), "Please select an employee.")
            return
        if not reason:
            QMessageBox.warning(self, t("warning"), "Reason is required.")
            return

        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=emp_id).first()
            ref = generate_sanction_ref(session)

            sanction = Sanction(
                sanction_ref=ref,
                employee_id=emp_id,
                sanction_type=self.type_combo.currentData(),
                reason=reason,
                delay_months=delay,
                issued_by_id=self.user.id,
            )
            session.add(sanction)
            session.flush()

            log_action(session, self.user.id, "sanction.issue", "sanction", sanction.id,
                description=f"Sanction issued [{ref}]: {sanction.sanction_type} to {emp.full_name} (+{delay} months)")

            session.commit()
            QMessageBox.information(self, t("success"),
                f"Sanction [{ref}] issued to {emp.full_name}.\n+{delay} month(s) added to their promotion race.")
            self._clear()
            self.on_issued()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()