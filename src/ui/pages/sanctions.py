"""
Sanctions Page
- Issue sanctions with 1-12 month promotion delay
- Unique auto-generated SAN- ID per sanction
- Active sanctions table
- History of resolved sanctions
- Shows clearly how many months added to promotion race
"""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QTextEdit,
    QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QSize
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

TAB_SS = """
QTabWidget::pane { border: none; background: #f9fafb; margin-top: 24px; }
QTabBar { background: #e5e7eb; border-radius: 14px; }
QTabBar::tab {
    background: transparent;
    color: #111827;
    padding: 9px 14px;
    border: none;
    font-size: 14px;
    font-weight: 700;
    min-height: 24px;
}
QTabBar::tab:first { border-top-left-radius: 14px; border-bottom-left-radius: 14px; }
QTabBar::tab:last { border-top-right-radius: 14px; border-bottom-right-radius: 14px; }
QTabBar::tab:selected { background: white; color: #030213; }
"""

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

FIELD_SS = """
QTextEdit, QSpinBox {
    border: none;
    border-radius: 8px;
    padding: 0 16px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    selection-background-color: #2563eb;
    outline: none;
}
QTextEdit { padding: 10px 16px; }
QTextEdit:focus, QSpinBox:focus { background: white; border: 1px solid #2563eb; }
QSpinBox::up-button, QSpinBox::down-button { width: 0; border: none; }
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
    border-radius: 8px;
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
    selection-background-color: #fef2f2;
}
QTableWidget::item {
    background: white;
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
}
QTableWidget::item:hover { background: #f9fafb; }
QTableWidget::item:selected { background: #fef2f2; color: #111827; }
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
"""

MESSAGE_BOX_SS = """
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
"""


class SanctionsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel("Sanctions Management")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel("Manage employee disciplinary actions and warnings")
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_SS)

        self.active_tab  = ActiveSanctionsTab(self.user)
        self.history_tab = SanctionHistoryTab(self.user)
        self.issue_tab   = IssueSanctionTab(self.user, self._on_issued)

        self.tabs.addTab(self.issue_tab,   "Issue Sanction")
        self.tabs.addTab(self.history_tab, "Sanction History")
        self.tabs.addTab(self.active_tab,  "Active Sanctions")

        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs, 1)

    def _on_tab_change(self, index):
        if index == 0:
            self.issue_tab.refresh_employees()
        elif index == 1:
            self.history_tab.refresh()
        elif index == 2:
            self.active_tab.refresh()

    def _on_issued(self):
        self.tabs.setCurrentIndex(2)
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Stats row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(20)
        layout.addLayout(self.stats_row)

        # Table card
        table_card = QFrame()
        table_card.setObjectName("Card")
        table_card.setStyleSheet(CARD_SS)
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        card_header = QFrame()
        card_header.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(card_header)
        chl.setContentsMargins(30, 28, 30, 28)
        ch_title = QLabel("Current Active Sanctions")
        ch_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        chl.addWidget(ch_title)
        chl.addStretch()
        tcl.addWidget(card_header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), "Employee", t("sanction_type"),
            "Reason", "Issue Date", "Promotion Delay", "Actions"
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        tcl.addWidget(self.table)
        layout.addWidget(table_card)

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
                "date": s.issued_at.strftime("%Y-%m-%d") if s.issued_at else "-",
                "delay": s.delay_months,
            } for s in active]
        finally:
            session.close()

        # Stats
        for label, val, color, icon_name, bg in [
            ("Active Sanctions", len(rows), "#ef4444", "fa5s.exclamation-triangle", "#fee2e2"),
            ("Total Delay Months", sum(r["delay"] for r in rows), "#f59e0b", "fa5s.clock", "#fef3c7"),
        ]:
            card = QFrame()
            card.setObjectName("Card")
            card.setFixedHeight(96)
            card.setStyleSheet(CARD_SS)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(22, 0, 22, 0)
            cl.setSpacing(14)
            icon = QLabel()
            icon.setFixedSize(48, 48)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(f"background: {bg}; border-radius: 8px;")
            icon.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))
            col = QVBoxLayout()
            col.setSpacing(0)
            col.setAlignment(Qt.AlignVCenter)
            l = QLabel(label)
            l.setStyleSheet("font-size: 14px; color: #374151; background: transparent;")
            v = QLabel(str(val))
            v.setStyleSheet("font-size: 24px; font-weight: 800; color: #030213; background: transparent;")
            col.addWidget(l)
            col.addWidget(v)
            cl.addWidget(icon)
            cl.addLayout(col)
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (56 * max(1, len(rows))))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 50)

            ref_item = QTableWidgetItem(row["ref"])
            ref_item.setForeground(QColor("#6b7280"))
            ref_item.setToolTip(row["ref"])
            self.table.setItem(i, 0, ref_item)

            emp_item = QTableWidgetItem(f"{row['emp_name']}\n{row['emp_id']}")
            emp_item.setToolTip(f"{row['emp_name']} ({row['emp_id']})")
            self.table.setItem(i, 1, emp_item)

            type_color = next(
                (c for st, _, c, _ in SANCTION_TYPES if st == row["type"]), "#374151"
            )
            type_bg = next(
                (b for st, _, _, b in SANCTION_TYPES if st == row["type"]), "#f9fafb"
            )
            type_item = QTableWidgetItem(row["type"].replace("_", " ").title())
            type_item.setBackground(QColor(type_bg))
            type_item.setForeground(QColor(type_color))
            type_item.setToolTip(type_item.text())
            self.table.setItem(i, 2, type_item)

            reason_item = QTableWidgetItem(row["reason"][:60] + "..." if len(row["reason"]) > 60 else row["reason"])
            reason_item.setToolTip(row["reason"])
            self.table.setItem(i, 3, reason_item)
            date_item = QTableWidgetItem(row["date"])
            date_item.setToolTip(row["date"])
            self.table.setItem(i, 4, date_item)

            delay_item = QTableWidgetItem(f"+{row['delay']} month{'s' if row['delay'] != 1 else ''}")
            delay_item.setForeground(QColor("#ef4444"))
            delay_item.setToolTip(delay_item.text())
            self.table.setItem(i, 5, delay_item)

            resolve_btn = QPushButton("Mark Resolved")
            resolve_btn.setText("  Mark Resolved")
            resolve_btn.setIcon(qta.icon("fa5s.check-circle", color="#166534"))
            resolve_btn.setIconSize(QSize(13, 13))
            resolve_btn.setCursor(Qt.PointingHandCursor)
            resolve_btn.setStyleSheet("QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 12px; font-weight: 700; margin: 7px; } QPushButton:hover { background: #dcfce7; color: #166534; }")
            resolve_btn.clicked.connect(lambda _, sid=row["id"]: self._resolve(sid))
            self.table.setCellWidget(i, 6, resolve_btn)

    def _resolve(self, sanction_id):
        confirm = _question(self, "Resolve Sanction",
            "Mark this sanction as resolved?")
        if confirm != QMessageBox.Yes:
            return

        session = get_session()
        try:
            s = session.query(Sanction).filter_by(id=sanction_id).first()
            s.is_resolved = True
            s.resolved_at = datetime.utcnow()
            log_action(
                session, action="sanction.resolve", performed_by_id=self.user.id,
                target_table="sanction", target_id=sanction_id,
                description=f"Sanction {s.sanction_ref} marked as resolved for {s.employee.full_name}"
            )
            session.commit()
            self.refresh()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


def _styled_message_box(parent, icon, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    box.setStyleSheet(MESSAGE_BOX_SS)
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


def _note_line(text, color):
    lbl = QLabel("&bull; " + text)
    lbl.setTextFormat(Qt.RichText)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
    return lbl


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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(30, 28, 30, 28)
        title = QLabel("Resolved Sanctions")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        hl.addWidget(title)
        hl.addStretch()
        cl.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), "Employee", "Type", "Reason",
            "Issue Date", "Delay Applied", "Status"
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        cl.addWidget(self.table)
        layout.addWidget(card)

    def refresh(self):
        session = get_session()
        try:
            sanctions = session.query(Sanction).order_by(Sanction.issued_at.desc()).all()
            rows = [{
                "ref": s.sanction_ref,
                "emp": f"{s.employee.full_name} ({s.employee.employee_id})",
                "type": s.sanction_type.replace("_", " ").title(),
                "reason": s.reason[:60] + "..." if len(s.reason) > 60 else s.reason,
                "date": s.issued_at.strftime("%Y-%m-%d") if s.issued_at else "-",
                "delay": f"+{s.delay_months} month{'s' if s.delay_months != 1 else ''}",
                "resolved": s.is_resolved,
                "resolved_at": s.resolved_at.strftime("%Y-%m-%d") if s.resolved_at else "-",
            } for s in sanctions]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (56 * max(1, len(rows))))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)
            ref = QTableWidgetItem(row["ref"])
            ref.setForeground(QColor("#6b7280"))
            ref.setToolTip(row["ref"])
            self.table.setItem(i, 0, ref)
            for col, key in [(1, "emp"), (2, "type"), (3, "reason"), (4, "date")]:
                item = QTableWidgetItem(row[key])
                item.setToolTip(row[key])
                self.table.setItem(i, col, item)
            delay = QTableWidgetItem(row["delay"])
            delay.setForeground(QColor("#ef4444"))
            delay.setToolTip(row["delay"])
            self.table.setItem(i, 5, delay)
            status_text = f"Resolved ({row['resolved_at']})" if row["resolved"] else "Active"
            status = QTableWidgetItem(status_text)
            status.setForeground(QColor("#10b981") if row["resolved"] else QColor("#ef4444"))
            status.setToolTip(status_text)
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main = QHBoxLayout(content)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(30)
        main.setAlignment(Qt.AlignTop)

        # ── Left: form ────────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(16)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_card.setStyleSheet(CARD_SS)
        fc = QVBoxLayout(form_card)
        fc.setContentsMargins(30, 28, 30, 28)
        fc.setSpacing(18)

        fc_title = QLabel("Issue New Sanction")
        fc_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        fc.addWidget(fc_title)

        # Employee
        emp_lbl = QLabel("Select Employee *")
        emp_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.emp_combo = QComboBox()
        self.emp_combo.setFixedHeight(44)
        self.emp_combo.setStyleSheet(COMBO_SS)
        fc.addWidget(emp_lbl)
        fc.addWidget(self.emp_combo)

        # Type
        type_lbl = QLabel("Sanction Type *")
        type_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(44)
        self.type_combo.setStyleSheet(COMBO_SS)
        self.type_combo.addItem("Select sanction type", None)
        for val, label, _, _ in SANCTION_TYPES:
            self.type_combo.addItem(label, val)
        fc.addWidget(type_lbl)
        fc.addWidget(self.type_combo)

        # Reason
        reason_lbl = QLabel("Reason / Description *")
        reason_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(80)
        self.reason_input.setPlaceholderText("Describe the reason for this sanction...")
        self.reason_input.setStyleSheet(FIELD_SS)
        fc.addWidget(reason_lbl)
        fc.addWidget(self.reason_input)

        # Delay months
        delay_lbl = QLabel("Promotion Delay (months) *")
        delay_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 12)
        self.delay_spin.setValue(1)
        self.delay_spin.setFixedHeight(44)
        self.delay_spin.setStyleSheet(FIELD_SS)
        self.delay_spin.valueChanged.connect(self._update_delay_preview)
        fc.addWidget(delay_lbl)
        fc.addWidget(self.delay_spin)

        self.delay_preview = QLabel("+1 month will be added to the employee's promotion race")
        self.delay_preview.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")
        fc.addWidget(self.delay_preview)

        left.addWidget(form_card)
        main.addLayout(left, 3)

        # ── Right: sidebar ────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Race impact info
        impact_card = QFrame()
        impact_card.setStyleSheet("QFrame { background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca; } QLabel { background: transparent; border: none; }")
        ic = QVBoxLayout(impact_card)
        ic.setContentsMargins(30, 28, 30, 28)
        ic.setSpacing(12)
        impact_head = QHBoxLayout()
        impact_icon = QLabel()
        impact_icon.setPixmap(qta.icon("fa5s.stopwatch", color="#dc2626").pixmap(18, 18))
        ic_title = QLabel("Promotion Race Impact")
        ic_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #991b1b; background: transparent;")
        impact_head.addWidget(impact_icon)
        impact_head.addWidget(ic_title)
        impact_head.addStretch()
        ic.addLayout(impact_head)
        for line in [
            "Sanctions delay the promotion race by adding months to the timeline",
            "The employee must wait longer before becoming eligible for promotion",
            "Duration range: 1-12 months",
            "Each sanction receives a unique auto-generated ID",
        ]:
            lbl = QLabel(f"• {line}")
            lbl.setTextFormat(Qt.RichText)
            lbl.setText("&bull; " + line)
            lbl.setStyleSheet("font-size: 14px; color: #b91c1c; background: transparent;")
            ic.addWidget(lbl)
        right.addWidget(impact_card)

        notes_card = QFrame()
        notes_card.setStyleSheet("QFrame { background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca; } QLabel { background: transparent; border: none; }")
        nc = QVBoxLayout(notes_card)
        nc.setContentsMargins(30, 28, 30, 28)
        nc.setSpacing(12)
        notes_head = QHBoxLayout()
        notes_icon = QLabel()
        notes_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color="#dc2626").pixmap(18, 18))
        notes_title = QLabel("Important Notes")
        notes_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #991b1b; background: transparent;")
        notes_head.addWidget(notes_icon)
        notes_head.addWidget(notes_title)
        notes_head.addStretch()
        nc.addLayout(notes_head)
        for line in [
            "All sanctions are recorded in the audit log",
            "Employee will be notified of the sanction",
            "Sanctions directly impact promotion timeline",
            "Ensure proper documentation is attached",
        ]:
            nc.addWidget(_note_line(line, "#b91c1c"))
        right.addWidget(notes_card)

        # Guidelines
        guide_card = QFrame()
        guide_card.setStyleSheet("QFrame { background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; } QLabel { background: transparent; border: none; }")
        gc = QVBoxLayout(guide_card)
        gc.setContentsMargins(30, 28, 30, 28)
        gc.setSpacing(12)
        guide_head = QHBoxLayout()
        guide_icon = QLabel()
        guide_icon.setPixmap(qta.icon("fa5s.user", color="#2563eb").pixmap(18, 18))
        gc_title = QLabel("Sanction Guidelines")
        gc_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #1e40af; background: transparent;")
        guide_head.addWidget(guide_icon)
        guide_head.addWidget(gc_title)
        guide_head.addStretch()
        gc.addLayout(guide_head)
        for stype, desc in [
            ("Verbal Warning",  "Minor violations (1-2 months delay)"),
            ("Written Warning", "Repeated violations (3-6 months delay)"),
            ("Suspension",      "Serious misconduct (6-9 months delay)"),
            ("Final Warning",   "Severe misconduct (9-12 months delay)"),
        ]:
            lbl = QLabel(f"• {stype}: {desc}")
            lbl.setText(f"<b>{stype}:</b><br>{desc}")
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size: 14px; color: #1d4ed8; background: transparent;")
            gc.addWidget(lbl)
        right.addWidget(guide_card)

        # Issue button
        issue_btn = QPushButton("Issue Sanction")
        issue_btn.setText("  Issue Sanction")
        issue_btn.setIcon(qta.icon("fa5s.exclamation-triangle", color="white"))
        issue_btn.setIconSize(QSize(14, 14))
        issue_btn.setCursor(Qt.PointingHandCursor)
        issue_btn.setFixedHeight(50)
        issue_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 800; } QPushButton:hover { background: #111827; }")
        issue_btn.clicked.connect(self._issue)
        right.addWidget(issue_btn)

        clear_btn = QPushButton("Clear Form")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(44)
        clear_btn.setStyleSheet("QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-weight: 700; } QPushButton:hover { background: #f3f4f6; }")
        clear_btn.clicked.connect(self._clear)
        right.addWidget(clear_btn)

        main.addLayout(right, 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh_employees(self):
        self.emp_combo.clear()
        self.emp_combo.addItem("Choose an employee", None)
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            for e in emps:
                self.emp_combo.addItem(f"{e.employee_id} - {e.full_name}", e.id)
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
        sanction_type = self.type_combo.currentData()
        reason = self.reason_input.toPlainText().strip()
        delay  = self.delay_spin.value()

        if not emp_id:
            _warning(self, t("warning"), "Please select an employee.")
            return
        if not sanction_type:
            _warning(self, t("warning"), "Please select a sanction type.")
            return
        if not reason:
            _warning(self, t("warning"), "Reason is required.")
            return

        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=emp_id).first()
            ref = generate_sanction_ref(session)

            sanction = Sanction(
                sanction_ref=ref,
                employee_id=emp_id,
                sanction_type=sanction_type,
                reason=reason,
                delay_months=delay,
                issued_by_id=self.user.id,
            )
            session.add(sanction)
            session.flush()

            log_action(
                session, action="sanction.issue", performed_by_id=self.user.id,
                target_table="sanction", target_id=sanction.id,
                description=f"Sanction issued [{ref}]: {sanction.sanction_type} to {emp.full_name} (+{delay} months)"
            )

            session.commit()
            _information(self, t("success"),
                f"Sanction [{ref}] issued to {emp.full_name}.\n+{delay} month(s) added to their promotion race.")
            self._clear()
            self.on_issued()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()
