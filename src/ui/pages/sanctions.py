"""
Sanctions Page
- Issue sanctions with 1-12 month promotion delay
- Unique auto-generated SAN- ID per sanction
- Active sanctions table
- History of resolved sanctions
- Shows clearly how many months added to promotion race
"""

import math

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox, QTextEdit, QLineEdit,
    QListWidget, QListWidgetItem,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from sqlalchemy.orm import joinedload

from src.core.i18n import t
from src.ui.animations import install_tab_transition
from src.ui.styles import (
    employee_picker_list_ss,
    pill_tab_ss,
    enable_table_row_selection,
    prepare_table_cell_widget,
    btn_primary,
    btn_outline,
    card_ss,
    input_style,
    combo_style,
    message_box_ss,
    scroll_ss,
    pager_button_ss,
    polish_combo_box,
    table_style,
)
from src.ui.theme import THEME_DARK, tokens
from src.database.connection import get_session, generate_sanction_ref, log_action, is_other_employee
from src.database.models import Employee, Sanction
from datetime import datetime


SANCTION_TYPES = [
    ("verbal_warning",  "verbal_warning",  "#f59e0b", "#fefce8"),
    ("written_warning", "written_warning", "#ef4444", "#fef2f2"),
    ("suspension",      "suspension",      "#dc2626", "#fef2f2"),
    ("final_warning",   "final_warning",   "#991b1b", "#fef2f2"),
]


class _EmployeePickerCompat:
    """Combo-like adapter for tests and older internal callers."""

    def __init__(self, tab):
        self._tab = tab

    def count(self):
        return len(self._tab.employee_options) + 1

    def setCurrentIndex(self, index):
        if index <= 0:
            self._tab.selected_employee_id = None
            self._tab.emp_search.clear()
            return
        option_index = index - 1
        if option_index >= len(self._tab.employee_options):
            return
        option = self._tab.employee_options[option_index]
        self._tab.emp_search.blockSignals(True)
        self._tab.emp_search.setText(option["label"])
        self._tab.emp_search.blockSignals(False)
        self._tab.selected_employee_id = option["id"]

    def currentData(self):
        return self._tab.selected_employee_id


def CARD_SS():
    return card_ss("QFrame#Card")


def FIELD_SS():
    return input_style()


def COMBO_SS():
    return combo_style(40)


def TABLE_SS():
    return table_style(selected_bg="#fef2f2", hover_bg="#fff7f7")


def MESSAGE_BOX_SS():
    return message_box_ss()


class SanctionsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setObjectName("SanctionsPage")
        self.setStyleSheet(f"QWidget#SanctionsPage {{ background: {tokens().canvas}; }}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("sanctions_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {tokens().text}; background: transparent;")
        subtitle = QLabel(t("sanctions_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {tokens().text_muted}; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(pill_tab_ss())

        self.active_tab  = ActiveSanctionsTab(self.user)
        self.history_tab = SanctionHistoryTab(self.user)
        self.issue_tab   = IssueSanctionTab(self.user, self._on_issued)

        self.tabs.addTab(self.issue_tab,   t("issue_sanction"))
        self.tabs.addTab(self.history_tab, t("sanction_history"))
        self.tabs.addTab(self.active_tab,  t("active_sanctions_label"))

        self.tabs.currentChanged.connect(self._on_tab_change)
        install_tab_transition(self.tabs)
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

    def open_active_sanctions(self):
        self.tabs.setCurrentIndex(2)
        self.active_tab.refresh()

    def showEvent(self, event):
        if self.tabs.currentIndex() == 0:
            self.issue_tab.refresh_employees()
        self.active_tab.refresh()
        super().showEvent(event)


# Active Sanctions Tab
class ActiveSanctionsTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setObjectName("ActiveSanctionsTab")
        self.setStyleSheet(f"QWidget#ActiveSanctionsTab {{ background: {tokens().canvas}; }}")
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
        table_card.setStyleSheet(CARD_SS())
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        card_header = QFrame()
        card_header.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid {tokens().border};")
        chl = QHBoxLayout(card_header)
        chl.setContentsMargins(30, 28, 30, 28)
        ch_icon = QLabel()
        ch_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color="#ef4444").pixmap(18, 18))
        ch_title = QLabel(t("current_active_sanctions"))
        ch_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {tokens().text}; background: transparent;")
        chl.addWidget(ch_icon)
        chl.addWidget(ch_title)
        chl.addStretch()
        tcl.addWidget(card_header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), t("employee"), t("sanction_type"),
            t("reason"), t("issue_date"), t("promotion_delay"), t("actions")
        ])
        self.table.setStyleSheet(TABLE_SS())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 164)
        self.table.setColumnWidth(6, 208)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                if col == 6:
                    header_item.setTextAlignment(Qt.AlignCenter)
                else:
                    header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table, selected_bg="#fef2f2")
        self.table.setShowGrid(False)
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
            (t("active_sanctions_label"), len(rows), "#ef4444", "fa5s.exclamation-triangle", "#fee2e2"),
            (t("total_delay_months"), sum(r["delay"] for r in rows), "#f59e0b", "fa5s.clock", "#fef3c7"),
        ]:
            card = QFrame()
            card.setObjectName("Card")
            card.setFixedHeight(96)
            card.setStyleSheet(CARD_SS())
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
            l.setStyleSheet(f"font-size: 14px; color: {tokens().text_muted}; background: transparent;")
            v = QLabel(str(val))
            v.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {tokens().text}; background: transparent;")
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
            ref_item.setForeground(QColor(tokens().text_soft))
            ref_item.setToolTip(row["ref"])
            self.table.setItem(i, 0, ref_item)

            emp_item = QTableWidgetItem(f"{row['emp_name']}\n{row['emp_id']}")
            emp_item.setToolTip(f"{row['emp_name']} ({row['emp_id']})")
            self.table.setItem(i, 1, emp_item)

            type_color = next(
                (c for st, _, c, _ in SANCTION_TYPES if st == row["type"]), tokens().text_muted
            )
            type_bg = next(
                (b for st, _, _, b in SANCTION_TYPES if st == row["type"]), tokens().surface_muted
            )
            type_item = QTableWidgetItem(t(row["type"]))
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

            delay_item = QTableWidgetItem(t("positive_month_count", count=row["delay"]))
            delay_item.setIcon(qta.icon("fa5s.clock", color=tokens().danger))
            delay_item.setForeground(QColor(tokens().danger))
            delay_item.setToolTip(delay_item.text())
            self.table.setItem(i, 5, delay_item)

            resolve_btn = QPushButton(t("mark_resolved"))
            resolve_btn.setIcon(qta.icon("fa5s.check-circle", color=tokens().success))
            resolve_btn.setIconSize(QSize(15, 15))
            resolve_btn.setFixedSize(178, 36)
            resolve_btn.setCursor(Qt.PointingHandCursor)
            resolve_btn.setStyleSheet(
                f"QPushButton {{ background: {tokens().surface}; color: {tokens().success}; border: 1px solid {tokens().success}; "
                "border-radius: 8px; font-size: 13px; font-weight: 800; "
                "padding: 0 14px; text-align: center; } "
                f"QPushButton:hover {{ background: {tokens().success_soft}; }} "
                f"QPushButton:pressed {{ background: {tokens().success_soft}; }}"
            )
            resolve_btn.clicked.connect(lambda _, sid=row["id"]: self._resolve(sid))
            action_cell = prepare_table_cell_widget(QWidget())
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(8, 6, 8, 6)
            action_layout.setAlignment(Qt.AlignCenter)
            action_layout.addWidget(resolve_btn)
            self.table.setCellWidget(i, 6, action_cell)

    def _resolve(self, sanction_id):
        confirm = _question(self, t("resolve_sanction"),
            t("confirm_resolve_sanction"))
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
    box.setStyleSheet(MESSAGE_BOX_SS())
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)


def _note_line(text, color):
    lbl = QLabel("&bull; " + text)
    lbl.setTextFormat(Qt.RichText)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
    return lbl


def _polish_combo(combo):
    polish_combo_box(combo)


# History Tab
class SanctionHistoryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.current_page = 1
        self.page_size = 50
        self.total_pages = 1
        self.setObjectName("SanctionHistoryTab")
        self.setStyleSheet(f"QWidget#SanctionHistoryTab {{ background: {tokens().canvas}; }}")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(CARD_SS())
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid {tokens().border};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(30, 28, 30, 28)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.check-circle", color="#10b981").pixmap(18, 18))
        title = QLabel(t("resolved_sanctions"))
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {tokens().text}; background: transparent;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addStretch()
        cl.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("sanction_id"), t("employee"), t("type"), t("reason"),
            t("issue_date"), t("delay_applied"), t("status")
        ])
        self.table.setStyleSheet(TABLE_SS())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table, selected_bg="#fef2f2")
        self.table.setShowGrid(False)
        cl.addWidget(self.table)
        cl.addWidget(self._pager())
        layout.addWidget(card)

    def refresh(self):
        session = get_session()
        try:
            total = session.query(Sanction).count()
            self.total_pages = max(1, math.ceil(total / self.page_size))
            self.current_page = max(1, min(self.current_page, self.total_pages))
            sanctions = (
                session.query(Sanction)
                .options(joinedload(Sanction.employee))
                .order_by(Sanction.issued_at.desc(), Sanction.id.desc())
                .offset((self.current_page - 1) * self.page_size)
                .limit(self.page_size)
                .all()
            )
            rows = [{
                "ref": s.sanction_ref,
                "emp": f"{s.employee.full_name} ({s.employee.employee_id})",
                "type": t(s.sanction_type),
                "reason": s.reason[:60] + "..." if len(s.reason) > 60 else s.reason,
                "date": s.issued_at.strftime("%Y-%m-%d") if s.issued_at else "-",
                "delay": t("positive_month_count", count=s.delay_months),
                "resolved": s.is_resolved,
                "resolved_at": s.resolved_at.strftime("%Y-%m-%d") if s.resolved_at else "-",
            } for s in sanctions]
        finally:
            session.close()

        self.page_lbl.setText(t("page_status", page=self.current_page, pages=self.total_pages))
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(420)
        try:
            for i, row in enumerate(rows):
                self.table.setRowHeight(i, 52)
                ref = QTableWidgetItem(row["ref"])
                ref.setForeground(QColor(tokens().text_soft))
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
                status_text = f"{t('resolved')} ({row['resolved_at']})" if row["resolved"] else t("active")
                status = QTableWidgetItem(status_text)
                status.setForeground(QColor("#10b981") if row["resolved"] else QColor("#ef4444"))
                status.setToolTip(status_text)
                self.table.setItem(i, 6, status)
        finally:
            self.table.setUpdatesEnabled(True)

    def _previous_page(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self.refresh()

    def _next_page(self):
        if self.current_page >= self.total_pages:
            return
        self.current_page += 1
        self.refresh()

    def _pager(self):
        pager = QFrame()
        pager.setStyleSheet(f"background: {tokens().surface}; border: none; border-top: 1px solid {tokens().border};")
        layout = QHBoxLayout(pager)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)
        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted}; background: transparent;")
        btn_ss = pager_button_ss()
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


# Issue Sanction Tab
class IssueSanctionTab(QWidget):
    def __init__(self, user, on_issued):
        super().__init__()
        self.user = user
        self.on_issued = on_issued
        self.employee_options = []
        self.selected_employee_id = None
        self.emp_combo = _EmployeePickerCompat(self)
        self.setObjectName("IssueSanctionTab")
        self.setStyleSheet(f"QWidget#IssueSanctionTab {{ background: {tokens().canvas}; }}")
        self._build()
        self.refresh_employees()

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

        # Left form
        left = QVBoxLayout()
        left.setSpacing(16)
        left.setAlignment(Qt.AlignTop)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_card.setStyleSheet(CARD_SS())
        form_card.setMinimumHeight(560)
        form_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        fc = QVBoxLayout(form_card)
        fc.setContentsMargins(30, 30, 30, 30)
        fc.setSpacing(14)

        title_row = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color="#ef4444").pixmap(18, 18))
        fc_title = QLabel(t("issue_new_sanction"))
        fc_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {tokens().text}; background: transparent;")
        title_row.addWidget(title_icon)
        title_row.addWidget(fc_title)
        title_row.addStretch()
        fc.addLayout(title_row)
        fc.addSpacing(18)

        # Employee
        emp_lbl = QLabel(t("select_employee") + " *")
        emp_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().text}; background: transparent;")
        self.emp_search = QLineEdit()
        self.emp_search.setFixedHeight(42)
        self.emp_search.setPlaceholderText(t("search_employees"))
        self.emp_search.setClearButtonEnabled(True)
        self.emp_search.setStyleSheet(FIELD_SS())
        self.emp_search.textChanged.connect(self._filter_employees)

        self.emp_list = QListWidget()
        self.emp_list.setFixedHeight(180)
        self.emp_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.emp_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.emp_list.itemClicked.connect(self._select_employee_item)
        self.emp_list.setStyleSheet(employee_picker_list_ss())
        fc.addWidget(emp_lbl)
        fc.addWidget(self.emp_search)
        fc.addWidget(self.emp_list)

        # Type
        type_lbl = QLabel(t("sanction_type") + " *")
        type_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().text}; background: transparent;")
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(44)
        self.type_combo.setStyleSheet(COMBO_SS())
        _polish_combo(self.type_combo)
        self.type_combo.addItem(t("select_sanction_type"), None)
        for val, label, _, _ in SANCTION_TYPES:
            self.type_combo.addItem(t(label), val)
        fc.addWidget(type_lbl)
        fc.addWidget(self.type_combo)

        # Reason
        reason_lbl = QLabel(t("reason_description") + " *")
        reason_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().text}; background: transparent;")
        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(80)
        self.reason_input.setPlaceholderText(t("sanction_reason_placeholder"))
        self.reason_input.setStyleSheet(FIELD_SS())
        fc.addWidget(reason_lbl)
        fc.addWidget(self.reason_input)

        date_delay_row = QHBoxLayout()
        date_delay_row.setSpacing(20)

        date_col = QVBoxLayout()
        date_col.setSpacing(6)
        date_lbl = QLabel(t("issue_date") + " *")
        date_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().text}; background: transparent;")
        self.issue_date_field = QFrame()
        self.issue_date_field.setFixedHeight(44)
        self.issue_date_field.setStyleSheet(
            f"QFrame {{ background: {tokens().input}; border: 1px solid {tokens().border}; border-radius: 8px; }} "
            "QLabel { background: transparent; border: none; }"
        )
        date_field_layout = QHBoxLayout(self.issue_date_field)
        date_field_layout.setContentsMargins(16, 0, 16, 0)
        date_field_layout.setSpacing(10)
        date_icon = QLabel()
        date_icon.setPixmap(qta.icon("fa5s.calendar-alt", color="#9ca3af").pixmap(14, 14))
        date_text = QLabel(datetime.utcnow().strftime("%m/%d/%Y"))
        date_text.setStyleSheet(f"font-size: 14px; color: {tokens().text}; background: transparent;")
        date_field_layout.addWidget(date_icon)
        date_field_layout.addWidget(date_text)
        date_field_layout.addStretch()
        date_col.addWidget(date_lbl)
        date_col.addWidget(self.issue_date_field)

        delay_col = QVBoxLayout()
        delay_col.setSpacing(6)
        delay_lbl = QLabel(t("promotion_delay_months") + " *")
        delay_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().text}; background: transparent;")
        self.delay_combo = QComboBox()
        self.delay_combo.setFixedHeight(44)
        self.delay_combo.setStyleSheet(COMBO_SS())
        _polish_combo(self.delay_combo)
        self.delay_combo.addItem(t("select_delay_months"), None)
        for month in range(1, 13):
            self.delay_combo.addItem(t("month_count", count=month), month)
        self.delay_combo.currentIndexChanged.connect(lambda _: self._update_delay_preview())
        delay_col.addWidget(delay_lbl)
        delay_col.addWidget(self.delay_combo)

        date_delay_row.addLayout(date_col, 1)
        date_delay_row.addLayout(delay_col, 1)
        fc.addLayout(date_delay_row)

        self.delay_preview = QLabel(t("select_delay_preview"))
        self.delay_preview.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft}; background: transparent;")
        fc.addWidget(self.delay_preview)
        fc.addStretch()

        left.addWidget(form_card)
        main.addLayout(left, 3)

        # Right sidebar
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        actions_card = QFrame()
        actions_card.setObjectName("Card")
        actions_card.setStyleSheet(CARD_SS())
        actions_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        ac = QVBoxLayout(actions_card)
        ac.setContentsMargins(30, 28, 30, 28)
        ac.setSpacing(16)
        actions_title = QLabel(t("actions"))
        actions_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {tokens().text}; background: transparent;")
        ac.addWidget(actions_title)
        ac.addSpacing(24)
        self.issue_btn = QPushButton("  " + t("issue_sanction"))
        primary_text = "#062f28" if tokens().name == THEME_DARK else "#ffffff"
        self.issue_btn.setIcon(qta.icon("fa5s.exclamation-triangle", color=primary_text))
        self.issue_btn.setIconSize(QSize(14, 14))
        self.issue_btn.setCursor(Qt.PointingHandCursor)
        self.issue_btn.setFixedHeight(50)
        self.issue_btn.setStyleSheet(btn_primary(50))
        self.issue_btn.clicked.connect(self._issue)
        ac.addWidget(self.issue_btn)
        clear_btn = QPushButton(t("clear_form"))
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(44)
        clear_btn.setStyleSheet(btn_outline(44))
        clear_btn.clicked.connect(self._clear)
        ac.addWidget(clear_btn)
        right.addWidget(actions_card)

        # Race impact info
        impact_card = QFrame()
        impact_card.setStyleSheet(
            f"QFrame {{ background: {tokens().danger_soft}; border-radius: 8px; border: 1px solid {tokens().danger}; }} "
            "QLabel { background: transparent; border: none; }"
        )
        ic = QVBoxLayout(impact_card)
        ic.setContentsMargins(30, 28, 30, 28)
        ic.setSpacing(12)
        impact_head = QHBoxLayout()
        impact_icon = QLabel()
        impact_icon.setPixmap(qta.icon("fa5s.stopwatch", color=tokens().danger).pixmap(18, 18))
        ic_title = QLabel(t("promotion_race_impact"))
        ic_title.setStyleSheet(f"font-size: 17px; font-weight: 800; color: {tokens().danger}; background: transparent;")
        impact_head.addWidget(impact_icon)
        impact_head.addWidget(ic_title)
        impact_head.addStretch()
        ic.addLayout(impact_head)
        for line in [
            t("sanction_impact_delay"),
            t("sanction_impact_wait"),
            t("sanction_impact_range"),
            t("sanction_impact_unique_id"),
        ]:
            lbl = QLabel("&bull; " + line)
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet(f"font-size: 14px; color: {tokens().text_muted}; background: transparent;")
            ic.addWidget(lbl)
        right.addWidget(impact_card)

        notes_card = QFrame()
        notes_card.setStyleSheet(
            f"QFrame {{ background: {tokens().danger_soft}; border-radius: 8px; border: 1px solid {tokens().danger}; }} "
            "QLabel { background: transparent; border: none; }"
        )
        nc = QVBoxLayout(notes_card)
        nc.setContentsMargins(30, 28, 30, 28)
        nc.setSpacing(12)
        notes_head = QHBoxLayout()
        notes_icon = QLabel()
        notes_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color=tokens().danger).pixmap(18, 18))
        notes_title = QLabel(t("important_notes"))
        notes_title.setStyleSheet(f"font-size: 17px; font-weight: 800; color: {tokens().danger}; background: transparent;")
        notes_head.addWidget(notes_icon)
        notes_head.addWidget(notes_title)
        notes_head.addStretch()
        nc.addLayout(notes_head)
        for line in [
            t("sanction_note_audit"),
            t("sanction_note_notify"),
            t("sanction_note_timeline"),
            t("sanction_note_documentation"),
        ]:
            nc.addWidget(_note_line(line, tokens().text_muted))
        right.addWidget(notes_card)

        # Guidelines
        guide_card = QFrame()
        guide_card.setStyleSheet(f"QFrame {{ background: {tokens().selected}; border-radius: 8px; border: 1px solid {tokens().brand}; }} QLabel {{ background: transparent; border: none; }}")
        gc = QVBoxLayout(guide_card)
        gc.setContentsMargins(30, 28, 30, 28)
        gc.setSpacing(12)
        guide_head = QHBoxLayout()
        guide_icon = QLabel()
        guide_icon.setPixmap(qta.icon("fa5s.user", color=tokens().brand).pixmap(18, 18))
        gc_title = QLabel(t("sanction_guidelines"))
        gc_title.setStyleSheet(f"font-size: 17px; font-weight: 800; color: {tokens().brand}; background: transparent;")
        guide_head.addWidget(guide_icon)
        guide_head.addWidget(gc_title)
        guide_head.addStretch()
        gc.addLayout(guide_head)
        for stype, desc in [
            (t("verbal_warning"),  t("verbal_warning_guideline")),
            (t("written_warning"), t("written_warning_guideline")),
            (t("suspension"),      t("suspension_guideline")),
            (t("final_warning"),   t("final_warning_guideline")),
        ]:
            lbl = QLabel("")
            lbl.setText(f"<b>{stype}:</b><br>{desc}")
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet(f"font-size: 14px; color: {tokens().text_muted}; background: transparent;")
            gc.addWidget(lbl)
        right.addWidget(guide_card)

        main.addLayout(right, 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh_employees(self):
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            self.employee_options = []
            for e in emps:
                if is_other_employee(e):
                    continue
                self.employee_options.append({
                    "id": e.id,
                    "label": f"{e.employee_id} - {e.full_name}",
                    "search_text": (
                        f"{e.employee_id} {e.full_name} {e.work_email or ''} "
                        f"{e.personal_email or ''} {e.title.name if e.title else ''}"
                    ).lower(),
                })
        finally:
            session.close()
        self.selected_employee_id = None
        self._filter_employees(self.emp_search.text())

    def _filter_employees(self, text):
        needle = text.strip().lower()
        self.selected_employee_id = None
        self.emp_list.clear()

        visible = [
            emp for emp in self.employee_options
            if not needle or needle in emp["search_text"]
        ]

        if not visible:
            item = QListWidgetItem(t("no_data"))
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(QColor(tokens().text_soft))
            self.emp_list.addItem(item)
            return

        for emp in visible:
            item = QListWidgetItem(emp["label"])
            item.setData(Qt.UserRole, emp["id"])
            item.setToolTip(emp["label"])
            self.emp_list.addItem(item)

    def _select_employee_item(self, item):
        emp_id = item.data(Qt.UserRole)
        if not emp_id:
            return
        self.emp_search.blockSignals(True)
        self.emp_search.setText(item.text())
        self.emp_search.blockSignals(False)
        self.selected_employee_id = emp_id

    def _update_delay_preview(self):
        val = self.delay_combo.currentData()
        if val is None:
            self.delay_preview.setText(t("select_delay_preview"))
            return
        self.delay_preview.setText(
            t("delay_preview_text", count=val)
        )

    def _clear(self):
        self.selected_employee_id = None
        self.emp_search.clear()
        self.type_combo.setCurrentIndex(0)
        self.reason_input.clear()
        self.delay_combo.setCurrentIndex(0)

    def _issue(self):
        emp_id = self.selected_employee_id
        sanction_type = self.type_combo.currentData()
        reason = self.reason_input.toPlainText().strip()
        delay = self.delay_combo.currentData()

        if not emp_id:
            _warning(self, t("warning"), t("please_select_employee"))
            return
        if not sanction_type:
            _warning(self, t("warning"), t("please_select_sanction_type"))
            return
        if delay is None:
            _warning(self, t("warning"), t("please_select_promotion_delay"))
            return
        if not reason:
            _warning(self, t("warning"), t("reason_required"))
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
                t("sanction_issued_success", ref=ref, name=emp.full_name, count=delay))
            self._clear()
            self.on_issued()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()
