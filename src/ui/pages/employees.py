"""
Employees Page - Fixed version
Fixes:
- Employee Edit functionality added
- Org unit graceful handling when none exist
- Status combo on add/edit forms
- Edit button wired up properly
"""

import qtawesome as qta
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QTabWidget,
    QTextEdit, QMessageBox, QDateEdit, QGridLayout, QListWidget,
    QListWidgetItem, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QDate, QSize, Signal, QTimer
from PySide6.QtGui import QColor
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from src.core.i18n import t
from src.ui.animations import animate_widget_entry, install_tab_transition
from src.ui.styles import (
    pill_tab_ss,
    btn_outline,
    btn_primary,
    card_ss,
    enable_table_row_selection,
    input_style,
    message_critical,
    message_information,
    message_question,
    message_warning,
    prepare_table_cell_widget,
    scroll_ss,
    table_style,
    polish_combo_box,
    primary_button_fg,
)
from src.ui.theme import THEME_DARK, tokens
from src.database.connection import (
    get_session, generate_employee_id, log_action,
    degree_to_title_name, calculate_months_remaining, calculate_sub_race,
    display_title_name, ensure_others_org_unit, is_other_employee,
    is_other_title, valid_other_manager_ids, validate_salary_for_title,
    OTHER_ORG_UNIT_NAME
)
from src.database.models import (
    Employee, Title, OrgUnit,
    CommendationEmployee, PromotionHistory, SalaryIncrementHistory, Sanction
)
from datetime import datetime
import json

DEGREE_OPTIONS = ["BSc", "MSc", "PhD", "Other"]
STATUS_OPTIONS = ["active", "inactive", "on_leave", "terminated"]


def _title_sort_key(title):
    name = title.name if title else ""
    if name == "Other":
        return (2, 0)
    if name.startswith("L") and name[1:].isdigit():
        return (0, -int(name[1:]))
    return (1, name)


def COMBO_STYLE():
    return input_style(40)


def INPUT_STYLE():
    return input_style(40)


def DATE_STYLE():
    return input_style(40) + """
QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}
QDateEdit::down-arrow { image: none; width: 0; height: 0; }
"""


def EMP_CARD_SS():
    return card_ss("QFrame#EmployeeCard")


def PROFILE_CARD_SS():
    return card_ss("QFrame#ProfileCard")

TOOLTIP_SS = """
QToolTip, QTipLabel {
    background: #111827;
    background-color: #111827;
    color: #ffffff;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 12px;
    opacity: 255;
}
"""


def _page_bg():
    return tokens().canvas


def _text():
    return tokens().text


def _muted():
    return tokens().text_muted


def _warning_ss():
    tkn = tokens()
    return f"font-size: 12px; color: {tkn.danger}; background: {tkn.danger_soft}; border: 1px solid {tkn.danger}; border-radius: 8px; padding: 9px 12px;"


def _level_badge_ss():
    return "background: #dbeafe; color: #1d4ed8; border-radius: 8px; font-size: 16px; font-weight: 700; border: none;"


def _level_badge_colors():
    return "#dbeafe", "#1d4ed8"


def _admin_badge_colors():
    tkn = tokens()
    return (tkn.danger_soft, tkn.danger) if tkn.name == THEME_DARK else ("#fee2e2", "#991b1b")


def _salary_text(emp):
    currency = emp.title.currency if getattr(emp, "title", None) and emp.title.currency else "EUR"
    return f"{currency} {emp.base_salary:,.2f}"


def _primary_button_fg():
    return primary_button_fg()


def _semantic_pair(kind="muted"):
    tkn = tokens()
    if kind == "level":
        return _level_badge_colors()
    if kind == "success":
        return tkn.success_soft, tkn.success
    if kind == "warning":
        return tkn.warning_soft, tkn.warning
    if kind == "danger":
        return tkn.danger_soft, tkn.danger
    return tkn.surface_muted, tkn.text_muted


def _soft_bg_for_color(color):
    tkn = tokens()
    if color in {"#10b981", "#166534"}:
        return tkn.success_soft
    if color == "#f59e0b":
        return tkn.warning_soft
    if color == "#ef4444":
        return tkn.danger_soft
    if color == "#2563eb":
        return "#dbeafe" if tkn.name != THEME_DARK else tkn.selected
    return tkn.surface_muted


def _would_create_manager_cycle(session, employee_id, manager_id):
    current_id = manager_id
    while current_id:
        if current_id == employee_id:
            return True
        manager = session.query(Employee).filter_by(id=current_id).first()
        current_id = manager.reports_to_id if manager else None
    return False


class CleanSelect(QWidget):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)
    valueChanged = Signal(object)

    def __init__(self):
        super().__init__()
        self._items = []
        self._current_index = -1
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.trigger = QFrame()
        self.trigger.setCursor(Qt.PointingHandCursor)
        self.trigger.setFixedHeight(44)

        trigger_layout = QHBoxLayout(self.trigger)
        trigger_layout.setContentsMargins(12, 0, 12, 0)
        trigger_layout.setSpacing(8)

        self.label = QLabel("")
        self.arrow = QLabel()
        self.arrow.setFixedSize(16, 16)
        self.arrow.setAlignment(Qt.AlignCenter)

        trigger_layout.addWidget(self.label, 1)
        trigger_layout.addWidget(self.arrow)
        layout.addWidget(self.trigger)

        self.popup = QFrame()
        self.popup.hide()
        self.popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_TranslucentBackground, True)
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)

        self.popup_box = QFrame()
        box_layout = QVBoxLayout(self.popup_box)
        box_layout.setContentsMargins(4, 4, 4, 4)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.apply_theme()
        box_layout.addWidget(self.list_widget)
        popup_layout.addWidget(self.popup_box)

        self.trigger.mousePressEvent = self._toggle_popup
        self.list_widget.itemClicked.connect(self._select_item)

    def apply_theme(self):
        tkn = tokens()
        self.trigger.setStyleSheet(f"""
            QFrame {{
                background: {tkn.input};
                border: 1px solid {tkn.border};
                border-radius: 8px;
            }}
            QFrame:hover {{ background: {tkn.hover}; }}
        """)
        self.label.setStyleSheet(f"font-size: 14px; color: {tkn.text}; background: transparent; border: none;")
        self.arrow.setPixmap(qta.icon("fa5s.chevron-down", color=tkn.text_muted).pixmap(12, 12))
        self.popup_box.setStyleSheet(f"""
            QFrame {{
                background: {tkn.surface};
                border: 1px solid {tkn.border_strong};
                border-radius: 8px;
            }}
        """)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {tkn.text};
                font-size: 14px;
            }}
            QListWidget::item:hover {{ background: {tkn.hover}; }}
            QListWidget::item:selected {{
                background: {tkn.selected};
                color: {tkn.brand};
            }}
        """)

    def addItem(self, label, value=None):
        self._items.append((label, value))
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, value)
        item.setSizeHint(QSize(0, 34))
        self.list_widget.addItem(item)
        self._resize_popup()
        if self._current_index == -1:
            self.setCurrentIndex(0)

    def clear(self):
        self._items.clear()
        self._current_index = -1
        self.label.setText("")
        self.list_widget.clear()
        self._resize_popup()

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def count(self):
        return len(self._items)

    def setCurrentIndex(self, index):
        if not 0 <= index < len(self._items):
            return
        self._current_index = index
        text, value = self._items[index]
        self.label.setText(text)
        self.list_widget.setCurrentRow(index)
        if not self.signalsBlocked():
            self.currentIndexChanged.emit(index)
            self.currentTextChanged.emit(text)
            self.valueChanged.emit(value)

    def _resize_popup(self):
        visible_items = min(max(self.list_widget.count(), 1), 8)
        self.list_widget.setFixedHeight((34 * visible_items) + 2)

    def _toggle_popup(self, event):
        if self.popup.isVisible():
            self.popup.hide()
            return
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.popup.setFixedWidth(self.width())
        self.popup.move(pos.x(), pos.y() + 4)
        self.popup.show()

    def _select_item(self, item):
        self.setCurrentIndex(self.list_widget.row(item))
        self.popup.hide()


class ChevronDateEdit(QDateEdit):
    def __init__(self):
        super().__init__()
        self._arrow = QLabel(self)
        self._arrow.setFixedSize(16, 16)
        self._arrow.setAlignment(Qt.AlignCenter)
        self._arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._arrow.setPixmap(qta.icon("fa5s.chevron-down", color=tokens().text_muted).pixmap(12, 12))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrow.move(self.width() - 28, (self.height() - self._arrow.height()) // 2)


class EmployeesPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setObjectName("EmployeesPage")
        self.setStyleSheet(f"QWidget#EmployeesPage {{ background: {_page_bg()}; }}")
        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.list_page    = EmployeeListView(self.user, self._show_add, self._show_profile)
        self.add_page     = AddEmployeeView(self.user, self._show_list)
        self.profile_page = EmployeeProfileView(self.user, self._show_list, self._show_edit)
        self.edit_page    = EditEmployeeView(self.user, self._show_list)

        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.add_page)
        self.stack.addWidget(self.profile_page)
        self.stack.addWidget(self.edit_page)
        self.stack.setCurrentWidget(self.list_page)

    def _set_view(self, widget):
        self.stack.setCurrentWidget(widget)
        animate_widget_entry(widget, duration=180, offset=8)

    def _show_list(self):
        self.list_page.refresh()
        self._set_view(self.list_page)

    def _show_add(self):
        self.add_page.reset()
        self._set_view(self.add_page)

    def _show_profile(self, employee_id):
        self.profile_page.editing = False
        self.profile_page.load(employee_id)
        self._set_view(self.profile_page)

    def _show_edit(self, employee_id):
        self.profile_page.load(employee_id)
        self._set_view(self.profile_page)
        self.profile_page._begin_inline_edit()


class EmployeeListView(QWidget):
    def __init__(self, user, on_add, on_profile):
        super().__init__()
        self.user = user
        self.on_add = on_add
        self.on_profile = on_profile
        self.all_employees = []
        self.filtered_employees = []
        self.page_size = 50
        self.current_page = 1
        self.total_count = 0
        self.total_pages = 1
        self._on_edit_cb = None
        self.setObjectName("EmployeeListView")
        self.setStyleSheet(f"QWidget#EmployeeListView {{ background: {_page_bg()}; font-family: 'Segoe UI'; }}" + TOOLTIP_SS)
        self._build()
        self.refresh()

    def set_edit_callback(self, cb):
        self._on_edit_cb = cb

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("employees_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {_text()}; background: transparent;")
        subtitle = QLabel(t("employees_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {_muted()}; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        bar = QFrame()
        bar.setObjectName("EmployeeCard")
        bar.setStyleSheet(EMP_CARD_SS())
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(20, 20, 20, 20)
        bl.setSpacing(16)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_employees"))
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(INPUT_STYLE())
        self.search_input.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._on_filter_changed)
        bl.addWidget(self.search_input, 1)

        self.dept_filter = CleanSelect()
        self.dept_filter.setFixedHeight(44)
        self.dept_filter.setMinimumWidth(220)
        self.dept_filter.addItem(t("all_departments"), None)
        self.dept_filter.currentIndexChanged.connect(lambda *_: self._on_filter_changed())
        bl.addWidget(self.dept_filter)

        self.status_filter = CleanSelect()
        self.status_filter.setFixedHeight(44)
        self.status_filter.setMinimumWidth(180)
        self.status_filter.addItem(t("all_status"), None)
        for s in STATUS_OPTIONS:
            self.status_filter.addItem(s.replace("_", " ").title(), s)
        self.status_filter.currentIndexChanged.connect(lambda *_: self._on_filter_changed())
        bl.addWidget(self.status_filter)

        add_btn = QPushButton("  " + t("add_employee"))
        add_btn.setIcon(qta.icon("fa5s.user-plus", color=_primary_button_fg()))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(44)
        add_btn.setStyleSheet(btn_primary(40))
        add_btn.clicked.connect(self.on_add)
        bl.addWidget(add_btn)
        layout.addWidget(bar)
        layout.addSpacing(28)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"font-size: 14px; color: {_muted()}; background: transparent;")
        layout.addWidget(self.count_lbl)
        layout.addSpacing(20)

        table_card = QFrame()
        table_card.setObjectName("EmployeeCard")
        table_card.setStyleSheet(EMP_CARD_SS())
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            t("employee_id"), t("name"), t("email"), t("department"),
            t("position"), t("level"), t("status"), t("actions")
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                align = Qt.AlignCenter if col in (5, 6, 7) else Qt.AlignLeft
                header_item.setTextAlignment(align | Qt.AlignVCenter)
        self.table.setStyleSheet(table_style())
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for col in (0, 5, 6, 7):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        for col in (1, 2, 3, 4):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setMinimumHeight(320)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table_layout.addWidget(self.table, 1)

        pager = QFrame()
        pager.setStyleSheet(f"background: {tokens().surface}; border: none; border-top: 1px solid {tokens().border};")
        pager_layout = QHBoxLayout(pager)
        pager_layout.setContentsMargins(16, 10, 16, 10)
        pager_layout.setSpacing(10)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(f"font-size: 13px; color: {_muted()}; background: transparent;")

        pager_btn_ss = btn_outline(32)
        self.prev_btn = QPushButton(t("previous_page"))
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(pager_btn_ss)
        self.prev_btn.clicked.connect(self._previous_page)

        self.next_btn = QPushButton(t("next_page"))
        self.next_btn.setFixedHeight(34)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(pager_btn_ss)
        self.next_btn.clicked.connect(self._next_page)

        pager_layout.addStretch()
        pager_layout.addWidget(self.page_lbl)
        pager_layout.addWidget(self.prev_btn)
        pager_layout.addWidget(self.next_btn)
        table_layout.addWidget(pager)
        layout.addWidget(table_card, 1)
        QTimer.singleShot(0, self._resize_columns)

    def refresh(self):
        self.current_page = 1
        self._load_departments()
        self._load_page()

    def _load_departments(self):
        current_dept = self.dept_filter.currentData()
        session = get_session()
        try:
            depts = [
                row[0] for row in
                session.query(OrgUnit.name)
                .join(Employee, Employee.org_unit_id == OrgUnit.id)
                .filter(OrgUnit.name.isnot(None))
                .distinct()
                .order_by(OrgUnit.name)
                .all()
            ]
            self.dept_filter.blockSignals(True)
            self.dept_filter.clear()
            self.dept_filter.addItem(t("all_departments"), None)
            for d in depts:
                self.dept_filter.addItem(d, d)
            if current_dept in depts:
                for idx, (_, value) in enumerate(self.dept_filter._items):
                    if value == current_dept:
                        self.dept_filter.setCurrentIndex(idx)
                        break
            self.dept_filter.blockSignals(False)
        finally:
            session.close()

    def _filtered_query(self, session):
        query = session.query(Employee)

        search = self.search_input.text().strip().lower()
        if search:
            pattern = f"%{search}%"
            full_name = func.lower(Employee.first_name + " " + Employee.last_name)
            query = query.filter(or_(
                func.lower(Employee.first_name).like(pattern),
                func.lower(Employee.last_name).like(pattern),
                full_name.like(pattern),
                func.lower(Employee.employee_id).like(pattern),
                func.lower(Employee.position).like(pattern),
                func.lower(Employee.work_email).like(pattern),
                func.lower(Employee.personal_email).like(pattern),
            ))

        dept = self.dept_filter.currentData()
        if dept:
            query = query.join(OrgUnit, Employee.org_unit_id == OrgUnit.id).filter(OrgUnit.name == dept)

        status = self.status_filter.currentData()
        if status:
            query = query.filter(Employee.status == status)

        return query

    def _load_page(self):
        session = get_session()
        try:
            base_query = self._filtered_query(session)
            self.total_count = base_query.count()
            self.total_pages = max(1, math.ceil(self.total_count / self.page_size))
            self.current_page = max(1, min(self.current_page, self.total_pages))

            emps = (
                base_query
                .options(joinedload(Employee.title), joinedload(Employee.org_unit))
                .order_by(Employee.id)
                .offset((self.current_page - 1) * self.page_size)
                .limit(self.page_size)
                .all()
            )

            self.filtered_employees = [{
                "id": e.id, "employee_id": e.employee_id, "full_name": e.full_name,
                "email": e.work_email or e.personal_email or "-",
                "dept": e.org_unit.name if e.org_unit else "-",
                "position": e.position,
                "level": e.title.name if e.title else "-",
                "degree": e.degree, "status": e.status,
            } for e in emps]
        finally:
            session.close()

        if self.total_count:
            shown_start = ((self.current_page - 1) * self.page_size) + 1
            shown_end = shown_start + len(self.filtered_employees) - 1
            shown = f"{shown_start}-{shown_end}"
        else:
            shown = "0"
        self.count_lbl.setText(t("showing_employees", shown=shown, total=self.total_count))
        self.page_lbl.setText(t("page_status", page=self.current_page, pages=self.total_pages))
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        self._populate_table(self.filtered_employees)

    def _on_filter_changed(self, *_):
        self.current_page = 1
        self._load_page()

    def _apply_filter(self):
        self._on_filter_changed()

    def _previous_page(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self._load_page()

    def _next_page(self):
        if self.current_page >= self.total_pages:
            return
        self.current_page += 1
        self._load_page()

    def _populate_table(self, employees):
        STATUS_COLORS = {
            "active": _semantic_pair("success"),
            "inactive": _semantic_pair("muted"),
            "on_leave": _semantic_pair("warning"),
        }
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            self.table.setRowCount(len(employees))

            for row, emp in enumerate(employees):
                self.table.setRowHeight(row, 62)
                for col, val in enumerate([emp["employee_id"], emp["full_name"], emp["email"], emp["dept"], emp["position"]]):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.UserRole, emp["id"])
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item.setToolTip(val)
                    if col == 0:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    if col == 2:
                        item.setForeground(QColor(tokens().text_muted))
                    self.table.setItem(row, col, item)

                self.table.setCellWidget(row, 5, self._badge(emp["level"], *_level_badge_colors()))
                bg, fg = STATUS_COLORS.get(emp["status"], _semantic_pair("muted"))
                self.table.setCellWidget(row, 6, self._badge(t(emp["status"]), bg, fg))

                btn_widget = prepare_table_cell_widget(QWidget())
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(6, 0, 6, 0)
                btn_layout.setSpacing(8)
                btn_layout.setAlignment(Qt.AlignCenter)

                _ico = QSize(16, 16)
                _btn_ss = (
                    "QPushButton {{ background: transparent; border: none; border-radius: 6px;"
                    " min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }}"
                    " QPushButton:hover {{ background: {hover}; }}"
                )

                view_btn = QPushButton()
                view_btn.setIcon(qta.icon("fa5s.eye", color="#2563eb"))
                view_btn.setIconSize(_ico)
                view_btn.setToolTip(t("view_profile"))
                view_btn.setCursor(Qt.PointingHandCursor)
                view_btn.setStyleSheet(_btn_ss.format(hover=tokens().hover))
                view_btn.clicked.connect(lambda _, eid=emp["id"]: self.on_profile(eid))

                edit_btn = QPushButton()
                edit_btn.setIcon(qta.icon("fa5s.edit", color=tokens().text_muted))
                edit_btn.setIconSize(_ico)
                edit_btn.setToolTip(t("edit_employee"))
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet(_btn_ss.format(hover=tokens().hover))
                edit_btn.clicked.connect(lambda _, eid=emp["id"]: self._do_edit(eid))

                del_btn = QPushButton()
                del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#dc2626"))
                del_btn.setIconSize(_ico)
                del_btn.setToolTip(t("delete_employee"))
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setStyleSheet(_btn_ss.format(hover=tokens().danger_soft))
                del_btn.clicked.connect(lambda _, eid=emp["id"]: self._do_delete(eid))

                btn_layout.addWidget(view_btn)
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(del_btn)
                self.table.setCellWidget(row, 7, btn_widget)
            self._resize_columns()
        finally:
            self.table.setUpdatesEnabled(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self._resize_columns()

    def _resize_columns(self):
        if not hasattr(self, "table"):
            return
        width = max(760, self.table.viewport().width())
        compact = width < 980
        fixed = {
            0: 104 if compact else 132,
            5: 70 if compact else 84,
            6: 96 if compact else 112,
            7: 96 if compact else 116,
        }
        for col, col_width in fixed.items():
            self.table.setColumnWidth(col, col_width)

    def _badge(self, text, bg, fg, border=None):
        wrap = prepare_table_cell_widget(QWidget())
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        if len(text) <= 3:
            label.setMinimumWidth(38)
        elif len(text) <= 9:
            label.setMinimumWidth(76)
        border_css = f"border: 1px solid {border};" if border else "border: none;"
        label.setStyleSheet(
            f"background: {bg}; color: {fg}; {border_css} border-radius: 8px;"
            " padding: 3px 10px; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(label, 0, Qt.AlignVCenter | Qt.AlignLeft)
        layout.addStretch()
        return wrap

    def _do_edit(self, emp_id):
        p = self.parent()
        while p and not isinstance(p, EmployeesPage):
            p = p.parent()
        if p:
            p._show_edit(emp_id)

    def _do_delete(self, emp_id):
        confirm = message_question(
            self, t("delete_employee_confirm_title"),
            t("delete_employee_confirm"),
            QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=emp_id).first()
            if not emp:
                return
            emp_name = emp.full_name
            emp_code = emp.employee_id

            # Clear org unit head references
            for unit in session.query(OrgUnit).filter_by(head_employee_id=emp_id).all():
                unit.head_employee_id = None

            # Clear reports_to references from other employees
            for e in session.query(Employee).filter(
                Employee.id != emp_id, Employee.reports_to_id == emp_id
            ).all():
                e.reports_to_id = None

            # Remove commendation junction rows
            session.query(CommendationEmployee).filter_by(employee_id=emp_id).delete(synchronize_session=False)

            # Remove sanctions
            session.query(Sanction).filter_by(employee_id=emp_id).delete(synchronize_session=False)

            # Remove promotion history
            session.query(PromotionHistory).filter_by(employee_id=emp_id).delete(synchronize_session=False)

            # Remove salary increment history
            session.query(SalaryIncrementHistory).filter_by(employee_id=emp_id).delete(synchronize_session=False)

            # Log before deleting (uses the employee's ID while it still exists)
            log_action(
                session, action="employee.delete", performed_by_id=self.user.id,
                target_table="employee", target_id=emp_id,
                description=f"Employee permanently deleted: {emp_name} ({emp_code})"
            )

            session.delete(emp)
            session.commit()
            message_information(self, t("success"), t("employee_deleted", name=emp_name, employee_id=emp_code))
            self.refresh()
        except Exception as e:
            session.rollback()
            message_critical(self, t("error"), str(e))
        finally:
            session.close()


class AddEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.fields = {}
        self.setObjectName("AddEmployeeView")
        self.setStyleSheet(f"QWidget#AddEmployeeView {{ background: {_page_bg()}; font-family: 'Segoe UI'; }}" + TOOLTIP_SS)
        self._build()
        self.reset()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(168)
        header.setStyleSheet(f"background: {_page_bg()}; border: none;")
        h = QVBoxLayout(header)
        h.setContentsMargins(40, 28, 40, 12)
        h.setSpacing(0)
        back_btn = QPushButton("  " + t("back_to_employees"))
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {tokens().brand}; border: none; font-size: 13px; font-weight: 600; }} QPushButton:hover {{ text-decoration: underline; }}")
        back_btn.clicked.connect(self.on_back)
        title = QLabel(t("add_employee_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {_text()}; background: transparent;")
        subtitle = QLabel(t("add_employee_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {_muted()}; background: transparent;")
        h.addWidget(back_btn, 0, Qt.AlignLeft)
        h.addSpacing(28)
        h.addWidget(title)
        h.addSpacing(6)
        h.addWidget(subtitle)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        content.setStyleSheet(f"background: {_page_bg()};")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(40, 0, 40, 40)
        cl.setSpacing(24)
        cl.setAlignment(Qt.AlignTop)

        left = QVBoxLayout()
        left.setSpacing(24)
        left.addWidget(self._section_card(t("personal_info"), [
            ("first_name",    t("first_name"),    "text"),
            ("last_name",     t("last_name"),      "text"),
            ("date_of_birth", t("date_of_birth"),  "date"),
            ("personal_email",t("personal_email"), "text"),
            ("phone",         t("phone"),          "text"),
            ("address",       t("address"),        "textarea"),
        ]))

        deg_card = QFrame()
        deg_card.setObjectName("EmployeeCard")
        deg_card.setStyleSheet(EMP_CARD_SS())
        dcl = QVBoxLayout(deg_card)
        dcl.setContentsMargins(24, 24, 24, 24)
        dcl.setSpacing(18)
        dcl.addWidget(self._lbl(t("education_level_assignment"), bold=True, size=18, color=_text()))
        row = QHBoxLayout()
        row.setSpacing(12)
        dl = QVBoxLayout()
        dl.addWidget(self._lbl(t("degree") + " *"))
        self.degree_combo = CleanSelect()
        self.degree_combo.setFixedHeight(44)
        for d in DEGREE_OPTIONS:
            self.degree_combo.addItem(d)
        self.degree_combo.currentTextChanged.connect(self._on_degree_changed)
        dl.addWidget(self.degree_combo)
        row.addLayout(dl)
        ll = QVBoxLayout()
        ll.addWidget(self._lbl(t("auto_level")))
        self.level_display = QLabel(self._starting_level_label("BSc"))
        self.level_display.setFixedHeight(44)
        self.level_display.setAlignment(Qt.AlignCenter)
        self.level_display.setStyleSheet(_level_badge_ss())
        ll.addWidget(self.level_display)
        row.addLayout(ll)
        dcl.addLayout(row)
        self.level_rule_label = self._lbl(t("level_rule_dynamic"), color="#9ca3af", size=11)
        dcl.addWidget(self.level_rule_label)
        left.addWidget(deg_card)

        employment_card = self._section_card(t("employment_info"), [
            ("work_email",  t("work_email"),  "text"),
            ("work_phone",  t("work_phone"),  "text"),
            ("position",    t("position"),    "text"),
            ("join_date",   t("join_date"),   "date"),
            ("base_salary", t("base_salary"), "text"),
        ])
        left.addWidget(employment_card)
        self.salary_warning = QLabel("")
        self.salary_warning.setWordWrap(True)
        self.salary_warning.hide()
        self.salary_warning.setStyleSheet(_warning_ss())
        left.addWidget(self.salary_warning)
        self.fields["base_salary"].textChanged.connect(self._update_salary_warning)
        cl.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        actions_card = QFrame()
        actions_card.setObjectName("EmployeeCard")
        actions_card.setStyleSheet(EMP_CARD_SS())
        ac = QVBoxLayout(actions_card)
        ac.setContentsMargins(24, 24, 24, 24)
        ac.setSpacing(16)
        ac.addWidget(self._lbl(t("actions"), bold=True, size=18, color=_text()))
        save_btn = QPushButton("  " + t("save"))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setIcon(qta.icon("fa5s.save", color=_primary_button_fg()))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.setStyleSheet(btn_primary(44))
        save_btn.clicked.connect(self._save)
        ac.addWidget(save_btn)
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet(btn_outline(44))
        cancel_btn.clicked.connect(self.on_back)
        ac.addWidget(cancel_btn)
        right.addWidget(actions_card)

        rules_card = QFrame()
        rules_card.setStyleSheet(
            f"QFrame {{ background: {tokens().selected}; border-radius: 8px; border: 1px solid {tokens().brand}; }}"
            "QLabel { border: none; background: transparent; }"
        )
        rc = QVBoxLayout(rules_card)
        rc.setContentsMargins(24, 22, 24, 22)
        rc.setSpacing(10)
        rc.addWidget(self._lbl(t("level_assignment_rules"), bold=True, size=16, color=tokens().brand))
        self.assignment_rules_layout = rc
        self.assignment_rule_rows = []
        for line in self._assignment_rule_lines():
            row = QHBoxLayout()
            icon = QLabel()
            icon.setFixedSize(14, 14)
            icon.setPixmap(qta.icon("fa5s.check-circle", color=tokens().brand).pixmap(12, 12))
            l = QLabel(line)
            l.setStyleSheet(f"font-size: 14px; color: {tokens().brand}; background: transparent;")
            row.addWidget(icon)
            row.addWidget(l)
            row.addStretch()
            rc.addLayout(row)
            self.assignment_rule_rows.append(l)
        org_card = QFrame()
        org_card.setObjectName("EmployeeCard")
        org_card.setStyleSheet(EMP_CARD_SS())
        oc = QVBoxLayout(org_card)
        oc.setContentsMargins(24, 24, 24, 24)
        oc.setSpacing(10)
        oc.addWidget(self._lbl(t("organization"), bold=True, size=18, color=_text()))
        oc.addWidget(self._lbl(t("org_unit")))
        self.org_combo = CleanSelect()
        self.org_combo.setFixedHeight(44)
        oc.addWidget(self.org_combo)
        oc.addWidget(self._lbl(t("reports_to")))
        self.manager_combo = CleanSelect()
        self.manager_combo.setFixedHeight(44)
        oc.addWidget(self.manager_combo)
        oc.addWidget(self._lbl(t("status")))
        self.status_combo = CleanSelect()
        self.status_combo.setFixedHeight(44)
        for s in STATUS_OPTIONS:
            self.status_combo.addItem(s.replace("_"," ").title(), s)
        oc.addWidget(self.status_combo)
        left.addWidget(org_card)
        right.addWidget(rules_card)

        info_card = QFrame()
        info_card.setStyleSheet(
            f"QFrame {{ background: {tokens().success_soft}; border-radius: 8px; border: 1px solid {tokens().success}; }}"
            "QLabel { border: none; background: transparent; }"
        )
        ic = QVBoxLayout(info_card)
        ic.setContentsMargins(24, 22, 24, 22)
        ic.setSpacing(10)
        ic.addWidget(self._lbl(t("salary_guidelines"), bold=True, size=16, color=tokens().success))
        self.salary_guideline_layout = ic
        right.addWidget(info_card)

        cl.addLayout(right, 2)
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _lbl(self, text, bold=False, size=12, color=None):
        l = QLabel(text)
        fw = "bold" if bold else "normal"
        l.setStyleSheet(f"font-size: {size}px; font-weight: {fw}; color: {color or _muted()}; background: transparent;")
        return l

    def _section_card(self, title, fields):
        card = QFrame()
        card.setObjectName("EmployeeCard")
        card.setStyleSheet(EMP_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(self._lbl(title, bold=True, size=18, color=_text()))
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(16)
        grid_row = 0
        grid_col = 0
        for key, label, ftype in fields:
            field = QVBoxLayout()
            field.setSpacing(6)
            field.addWidget(self._lbl(label + (" *" if key in ["first_name","last_name","position","join_date"] else ""), bold=True, color=_text()))
            if ftype == "textarea":
                widget = QTextEdit()
                widget.setFixedHeight(80)
                widget.setStyleSheet(INPUT_STYLE())
            elif ftype == "date":
                widget = ChevronDateEdit()
                widget.setCalendarPopup(True)
                widget.setFixedHeight(44)
                widget.setDate(QDate.currentDate())
                widget.setDisplayFormat("M/d/yyyy")
                widget.setStyleSheet(DATE_STYLE())
            else:
                widget = QLineEdit()
                widget.setFixedHeight(44)
                placeholders = {
                    "phone": "+36 20 123 4567",
                    "work_phone": "+36 20 123 4567",
                    "position": "e.g., Senior Developer",
                    "base_salary": "e.g., 3500",
                }
                widget.setPlaceholderText(placeholders.get(key, ""))
                widget.setStyleSheet(INPUT_STYLE())
            field.addWidget(widget)
            self.fields[key] = widget
            if ftype == "textarea":
                if grid_col:
                    grid_row += 1
                    grid_col = 0
                grid.addLayout(field, grid_row, 0, 1, 2)
                grid_row += 1
                grid_col = 0
            else:
                grid.addLayout(field, grid_row, grid_col)
                grid_col += 1
                if grid_col == 2:
                    grid_row += 1
                    grid_col = 0
        layout.addLayout(grid)
        return card

    def reset(self):
        for key, widget in self.fields.items():
            if isinstance(widget, QLineEdit): widget.clear()
            elif isinstance(widget, QTextEdit): widget.clear()
            elif isinstance(widget, QDateEdit): widget.setDate(QDate.currentDate())
        self.degree_combo.setCurrentIndex(0)
        self.level_display.setText(self._starting_level_label(self.degree_combo.currentText()))
        self.status_combo.setCurrentIndex(0)
        self._refresh_assignment_rules()
        self._load_org_units()
        self._load_managers()
        self._refresh_salary_guidelines()
        self._update_salary_warning()

    def _on_degree_changed(self, degree):
        level_name = degree_to_title_name(degree)
        self.level_display.setText(self._starting_level_label(degree))
        if level_name == "Other":
            self.level_display.setStyleSheet(_level_badge_ss())
        else:
            self.level_display.setStyleSheet(_level_badge_ss())
        self._load_org_units()
        self._load_managers()
        self._update_salary_warning()

    def _starting_level_label(self, degree):
        level_name = degree_to_title_name(degree)
        return t("other_misc") if level_name == "Other" else level_name

    def _assignment_rule_lines(self):
        return [
            t("degree_starts_at_level", degree="PhD", level=self._starting_level_label("PhD")),
            t("degree_starts_at_level", degree="MSc", level=self._starting_level_label("MSc")),
            t("degree_starts_at_level", degree="BSc", level=self._starting_level_label("BSc")),
            t("other_stays_other"),
        ]

    def _refresh_assignment_rules(self):
        if not hasattr(self, "assignment_rule_rows"):
            return
        for label, text in zip(self.assignment_rule_rows, self._assignment_rule_lines()):
            label.setText(text)

    def _selected_title(self, session):
        return session.query(Title).filter_by(name=degree_to_title_name(self.degree_combo.currentText())).first()

    def _refresh_salary_guidelines(self):
        if not hasattr(self, "salary_guideline_layout"):
            return
        while self.salary_guideline_layout.count() > 1:
            item = self.salary_guideline_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        session = get_session()
        try:
            titles = session.query(Title).all()
            for title in sorted(titles, key=_title_sort_key):
                label = display_title_name(title)
                line = f"{label}: {title.currency or 'EUR'} {title.base_salary_min:,.0f} to {title.base_salary_max:,.0f}"
                l = QLabel(line)
                l.setStyleSheet(f"font-size: 13px; color: {tokens().success}; background: transparent;")
                self.salary_guideline_layout.addWidget(l)
        finally:
            session.close()

    def _update_salary_warning(self):
        if not hasattr(self, "salary_warning"):
            return
        salary_raw = self._get("base_salary")
        if not salary_raw:
            self.salary_warning.hide()
            return
        try:
            salary = float(salary_raw)
        except ValueError:
            self.salary_warning.setText(t("salary_number_required"))
            self.salary_warning.show()
            return
        session = get_session()
        try:
            title = self._selected_title(session)
            ok, message = validate_salary_for_title(title, salary)
            self.salary_warning.setText(message)
            self.salary_warning.setVisible(not ok)
        finally:
            session.close()

    def _load_org_units(self):
        self.org_combo.clear()
        session = get_session()
        try:
            if self.degree_combo.currentText() == "Other":
                others = ensure_others_org_unit(session)
                session.commit()
                self.org_combo.addItem(OTHER_ORG_UNIT_NAME, others.id)
            else:
                self.org_combo.addItem(t("none"), None)
                for u in session.query(OrgUnit).filter(OrgUnit.name != OTHER_ORG_UNIT_NAME).all():
                    self.org_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
        finally:
            session.close()

    def _load_managers(self):
        self.manager_combo.clear()
        self.manager_combo.addItem(t("none"), None)
        session = get_session()
        try:
            manager_filter = None
            if self.degree_combo.currentText() == "Other":
                manager_filter = valid_other_manager_ids(session)
            for e in session.query(Employee).filter_by(status="active").all():
                if manager_filter is not None and e.id not in manager_filter:
                    continue
                self.manager_combo.addItem(f"{e.employee_id} - {e.full_name}", e.id)
        finally:
            session.close()

    def _get(self, key):
        w = self.fields.get(key)
        if isinstance(w, QLineEdit): return w.text().strip()
        elif isinstance(w, QTextEdit): return w.toPlainText().strip()
        elif isinstance(w, QDateEdit): return w.date().toPython()
        return None

    def _save(self):
        for key, label in {"first_name": t("first_name"), "last_name": t("last_name"), "position": t("position")}.items():
            if not self._get(key):
                message_warning(self, t("warning"), f"{label} is required.")
                return
        session = get_session()
        try:
            degree = self.degree_combo.currentText()
            title = session.query(Title).filter_by(name=degree_to_title_name(degree)).first()
            if not title:
                message_critical(self, t("error"), t("title_not_found"))
                return
            emp_id = generate_employee_id(session)
            join_dt = self._get("join_date")
            dob_dt  = self._get("date_of_birth")
            salary_raw = self._get("base_salary")
            try:
                salary = float(salary_raw) if salary_raw else 0.0
            except ValueError:
                message_warning(self, t("warning"), t("salary_number_required"))
                return
            ok, salary_message = validate_salary_for_title(title, salary)
            if not ok:
                message_warning(self, t("warning"), salary_message)
                return
            org_unit_id = self.org_combo.currentData()
            reports_to_id = self.manager_combo.currentData()
            if degree == "Other":
                others = ensure_others_org_unit(session)
                org_unit_id = others.id
                valid_managers = valid_other_manager_ids(session)
                if reports_to_id and reports_to_id not in valid_managers:
                    message_warning(self, t("warning"), t("other_manager_required"))
                    return
            emp = Employee(
                employee_id=emp_id, first_name=self._get("first_name"),
                last_name=self._get("last_name"), degree=degree,
                date_of_birth=datetime.combine(dob_dt, datetime.min.time()) if dob_dt else None,
                personal_email=self._get("personal_email"), phone=self._get("phone"),
                address=self._get("address"), work_email=self._get("work_email"),
                work_phone=self._get("work_phone"), position=self._get("position"),
                join_date=datetime.combine(join_dt, datetime.min.time()),
                base_salary=salary, status=self.status_combo.currentData(),
                title_id=title.id, org_unit_id=org_unit_id,
                reports_to_id=reports_to_id,
            )
            session.add(emp)
            session.flush()
            log_action(session=session, performed_by_id=self.user.id, action="employee.create",
                target_table="employee", target_id=emp.id,
                description=f"New employee added: {emp.full_name} ({emp_id})")
            session.commit()
            message_information(self, t("success"), t("employee_added", name=emp.full_name, employee_id=emp_id))
            self.on_back()
        except Exception as e:
            session.rollback()
            message_critical(self, t("error"), str(e))
        finally:
            session.close()


class EditEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.employee_db_id = None
        self.fields = {}
        self.setObjectName("EditEmployeeView")
        self.setStyleSheet(f"QWidget#EditEmployeeView {{ background: {_page_bg()}; }}" + TOOLTIP_SS)
        self._build_shell()

    def _build_shell(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet(f"background: {tokens().surface}; border-bottom: 1px solid {tokens().border};")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("  " + t("back_to_employees"))
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {tokens().brand}; border: none; font-size: 13px; font-weight: 600; }} QPushButton:hover {{ text-decoration: underline; }}")
        back_btn.clicked.connect(self.on_back)
        self.header_title = QLabel(t("edit_employee"))
        self.header_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {_text()}; margin-left: 12px;")
        h.addWidget(back_btn)
        h.addWidget(self.header_title)
        h.addStretch()
        self.layout_.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.layout_.addWidget(self.scroll)

    def load(self, employee_db_id):
        self.employee_db_id = employee_db_id
        self.fields = {}
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_db_id).first()
            if not emp:
                return
            self.header_title.setText(f"{t('edit')} - {emp.full_name}")

            content = QWidget()
            content.setStyleSheet(f"background: {_page_bg()};")
            cl = QHBoxLayout(content)
            cl.setContentsMargins(28, 24, 28, 28)
            cl.setSpacing(20)
            cl.setAlignment(Qt.AlignTop)

            left = QVBoxLayout()
            left.setSpacing(16)

            # Work card
            wcard = self._form_card(t("employment_info"), [
                ("position", " ".join([t("position"), "*"]), emp.position),
                ("work_email", t("work_email"), emp.work_email or ""),
                ("work_phone", t("work_phone"), emp.work_phone or ""),
                ("base_salary", t("base_salary"), str(emp.base_salary)),
            ])
            left.addWidget(wcard)

            if self.user.role == "admin":
                pcard = self._form_card(t("personal_info_admin"), [
                    ("first_name", " ".join([t("first_name"), "*"]), emp.first_name),
                    ("last_name", " ".join([t("last_name"), "*"]), emp.last_name),
                    ("personal_email", t("personal_email"), emp.personal_email or ""),
                    ("phone", t("phone"), emp.phone or ""),
                    ("address", t("address"), emp.address or ""),
                ])
                left.addWidget(pcard)

            cl.addLayout(left, 3)

            right = QVBoxLayout()
            right.setSpacing(16)
            right.setAlignment(Qt.AlignTop)

            org_card = QFrame()
            org_card.setStyleSheet(card_ss())
            oc = QVBoxLayout(org_card)
            oc.setContentsMargins(20, 16, 20, 16)
            oc.setSpacing(8)
            t_lbl = QLabel(t("organization_status"))
            t_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {_text()}; background: transparent;")
            oc.addWidget(t_lbl)

            oc.addWidget(self._small_lbl(t("org_unit")))
            self.org_combo = QComboBox()
            self.org_combo.setFixedHeight(36)
            self.org_combo.setStyleSheet(COMBO_STYLE())
            polish_combo_box(self.org_combo)
            if is_other_employee(emp):
                others = ensure_others_org_unit(session)
                session.flush()
                self.org_combo.addItem(OTHER_ORG_UNIT_NAME, others.id)
            else:
                self.org_combo.addItem(t("none"), None)
                for u in session.query(OrgUnit).filter(OrgUnit.name != OTHER_ORG_UNIT_NAME).all():
                    self.org_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
                    if emp.org_unit_id == u.id:
                        self.org_combo.setCurrentIndex(self.org_combo.count() - 1)
            oc.addWidget(self.org_combo)

            oc.addWidget(self._small_lbl(t("reports_to")))
            self.manager_combo = QComboBox()
            self.manager_combo.setFixedHeight(36)
            self.manager_combo.setStyleSheet(COMBO_STYLE())
            polish_combo_box(self.manager_combo)
            self.manager_combo.addItem(t("none"), None)
            manager_filter = valid_other_manager_ids(session) if is_other_employee(emp) else None
            for e in session.query(Employee).filter(Employee.id != employee_db_id).all():
                if manager_filter is not None and e.id not in manager_filter:
                    continue
                self.manager_combo.addItem(f"{e.employee_id} - {e.full_name}", e.id)
                if emp.reports_to_id == e.id:
                    self.manager_combo.setCurrentIndex(self.manager_combo.count() - 1)
            oc.addWidget(self.manager_combo)

            oc.addWidget(self._small_lbl(t("current_level_role")))
            self.title_combo = QComboBox()
            self.title_combo.setFixedHeight(36)
            self.title_combo.setStyleSheet(COMBO_STYLE())
            polish_combo_box(self.title_combo)
            for title in session.query(Title).order_by(Title.name.desc()).all():
                self.title_combo.addItem(f"{display_title_name(title)} - {title.label}", title.id)
                if emp.title_id == title.id:
                    self.title_combo.setCurrentIndex(self.title_combo.count() - 1)
            self.title_combo.currentIndexChanged.connect(self._update_edit_salary_warning)
            oc.addWidget(self.title_combo)

            self.edit_salary_warning = QLabel("")
            self.edit_salary_warning.setWordWrap(True)
            self.edit_salary_warning.hide()
            self.edit_salary_warning.setStyleSheet(_warning_ss())
            oc.addWidget(self.edit_salary_warning)
            self.fields["base_salary"].textChanged.connect(self._update_edit_salary_warning)

            oc.addWidget(self._small_lbl(t("status")))
            self.status_combo = QComboBox()
            self.status_combo.setFixedHeight(36)
            self.status_combo.setStyleSheet(COMBO_STYLE())
            polish_combo_box(self.status_combo)
            for s in STATUS_OPTIONS:
                self.status_combo.addItem(s.replace("_"," ").title(), s)
                if emp.status == s:
                    self.status_combo.setCurrentIndex(self.status_combo.count() - 1)
            oc.addWidget(self.status_combo)
            right.addWidget(org_card)

            save_btn = QPushButton(t("save_changes"))
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.setFixedHeight(44)
            save_btn.setStyleSheet(btn_primary(44))
            save_btn.clicked.connect(self._save)
            right.addWidget(save_btn)
            cl.addLayout(right, 2)
            self.scroll.setWidget(content)
            self._update_edit_salary_warning()
        finally:
            session.close()

    def _small_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {_muted()}; background: transparent;")
        return l

    def _form_card(self, title, fields):
        card = QFrame()
        card.setStyleSheet(card_ss())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {_text()}; background: transparent;")
        layout.addWidget(t_lbl)
        grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        for i, (key, label, val) in enumerate(fields):
            col = col1 if i % 2 == 0 else col2
            col.addWidget(self._small_lbl(label))
            widget = QLineEdit(val)
            widget.setStyleSheet(INPUT_STYLE())
            col.addWidget(widget)
            col.addSpacing(2)
            self.fields[key] = widget
        grid.addLayout(col1)
        grid.addSpacing(12)
        grid.addLayout(col2)
        layout.addLayout(grid)
        return card

    def _get(self, key):
        w = self.fields.get(key)
        return w.text().strip() if isinstance(w, QLineEdit) else None

    def _update_edit_salary_warning(self):
        if not hasattr(self, "edit_salary_warning"):
            return
        salary_raw = self._get("base_salary")
        if not salary_raw:
            self.edit_salary_warning.hide()
            return
        try:
            salary = float(salary_raw)
        except ValueError:
            self.edit_salary_warning.setText(t("salary_number_required"))
            self.edit_salary_warning.show()
            return
        session = get_session()
        try:
            title = session.query(Title).filter_by(id=self.title_combo.currentData()).first()
            ok, message = validate_salary_for_title(title, salary)
            self.edit_salary_warning.setText(message)
            self.edit_salary_warning.setVisible(not ok)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=self.employee_db_id).first()
            if not emp:
                return
            before = json.dumps({"position": emp.position, "status": emp.status, "base_salary": emp.base_salary})

            if self._get("position"): emp.position = self._get("position")
            emp.work_email = self._get("work_email") or emp.work_email
            emp.work_phone = self._get("work_phone") or emp.work_phone
            salary_raw = self._get("base_salary")
            new_salary = emp.base_salary
            if salary_raw:
                try:
                    new_salary = float(salary_raw)
                except ValueError:
                    message_warning(self, t("warning"), t("salary_number_required"))
                    return

            manager_id = self.manager_combo.currentData()
            title_id = self.title_combo.currentData()
            status = self.status_combo.currentData()
            if title_id is None:
                message_warning(self, t("warning"), t("valid_level_required"))
                return
            if status is None:
                message_warning(self, t("warning"), t("valid_status_required"))
                return
            if _would_create_manager_cycle(session, emp.id, manager_id):
                message_warning(self, t("warning"), t("manager_cycle_error"))
                return
            title = session.query(Title).filter_by(id=title_id).first()
            ok, salary_message = validate_salary_for_title(title, new_salary)
            if not ok:
                message_warning(self, t("warning"), salary_message)
                return
            if title and is_other_title(title):
                others = ensure_others_org_unit(session)
                valid_managers = valid_other_manager_ids(session)
                if manager_id and manager_id not in valid_managers:
                    message_warning(self, t("warning"), t("other_manager_required"))
                    return
                emp.org_unit_id = others.id
                emp.degree = "Other"
            else:
                emp.org_unit_id = self.org_combo.currentData()

            emp.reports_to_id = manager_id
            emp.title_id      = title_id
            emp.base_salary   = new_salary
            emp.status        = status

            if self.user.role == "admin":
                if self._get("first_name"): emp.first_name = self._get("first_name")
                if self._get("last_name"):  emp.last_name  = self._get("last_name")
                emp.personal_email = self._get("personal_email") or emp.personal_email
                emp.phone    = self._get("phone") or emp.phone
                emp.address  = self._get("address") or emp.address

            after = json.dumps({"position": emp.position, "status": emp.status, "base_salary": emp.base_salary})
            log_action(session=session, performed_by_id=self.user.id, action="employee.update",
                target_table="employee", target_id=emp.id,
                description=f"Employee updated: {emp.full_name} ({emp.employee_id})",
                before_value=before, after_value=after)
            session.commit()
            message_information(self, t("success"), t("employee_updated", name=emp.full_name))
            self.on_back()
        except Exception as e:
            session.rollback()
            message_critical(self, t("error"), str(e))
        finally:
            session.close()


class EmployeeProfileView(QWidget):
    def __init__(self, user, on_back, on_edit):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.on_edit = on_edit
        self.employee_db_id = None
        self.setObjectName("EmployeeProfileViewLegacy")
        self.setStyleSheet(f"QWidget#EmployeeProfileViewLegacy {{ background: {_page_bg()}; }}" + TOOLTIP_SS)
        self._build_shell()

    def _build_shell(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        self.header = QFrame()
        self.header.setFixedHeight(72)
        self.header.setStyleSheet(f"background: {tokens().surface}; border-bottom: 1px solid {tokens().border};")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("  " + t("back_to_employees"))
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {tokens().brand}; border: none; font-size: 13px; font-weight: 600; }} QPushButton:hover {{ text-decoration: underline; }}")
        back_btn.clicked.connect(self.on_back)
        self.header_title = QLabel(t("view_profile"))
        self.header_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {_text()}; margin-left: 12px;")
        h.addWidget(back_btn)
        h.addWidget(self.header_title)
        h.addStretch()
        edit_btn = QPushButton(t("edit_employee"))
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedHeight(34)
        edit_btn.setStyleSheet(btn_primary(36))
        edit_btn.clicked.connect(lambda: self.on_edit(self.employee_db_id) if self.employee_db_id else None)
        h.addWidget(edit_btn)
        self.layout_.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.layout_.addWidget(self.scroll)

    def load(self, employee_db_id):
        self.employee_db_id = employee_db_id
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_db_id).first()
            if not emp:
                return
            race = calculate_months_remaining(emp, session)
            content = QWidget()
            content.setStyleSheet(f"background: {_page_bg()};")
            cl = QVBoxLayout(content)
            cl.setContentsMargins(28, 24, 28, 28)
            cl.setSpacing(16)

            # Profile header card
            profile_card = QFrame()
            profile_card.setStyleSheet(card_ss())
            pc = QHBoxLayout(profile_card)
            pc.setContentsMargins(24, 20, 24, 20)
            pc.setSpacing(20)

            initials = (emp.first_name[0] + emp.last_name[0]).upper()
            avatar = QLabel(initials)
            avatar.setFixedSize(72, 72)
            avatar.setAlignment(Qt.AlignCenter)
            avatar_text = "#062f28" if tokens().name == THEME_DARK else "#ffffff"
            avatar.setStyleSheet(f"background: {tokens().brand}; color: {avatar_text}; border-radius: 36px; font-size: 26px; font-weight: bold;")
            pc.addWidget(avatar)

            info = QVBoxLayout()
            info.setSpacing(4)
            name_row = QHBoxLayout()
            name_lbl = QLabel(emp.full_name)
            name_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {_text()}; background: transparent;")
            name_row.addWidget(name_lbl)
            STATUS_COLORS = {
                "active": _semantic_pair("success"),
                "inactive": _semantic_pair("muted"),
                "on_leave": _semantic_pair("warning"),
            }
            sbg, sfg = STATUS_COLORS.get(emp.status, _semantic_pair("muted"))
            sb = QLabel(emp.status.replace("_"," ").title())
            sb.setStyleSheet(f"background: {sbg}; color: {sfg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(sb)
            lb = QLabel(emp.title.name if emp.title else "-")
            lb_bg, lb_fg = _semantic_pair("level")
            lb.setStyleSheet(f"background: {lb_bg}; color: {lb_fg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(lb)
            name_row.addStretch()
            info.addLayout(name_row)
            pos_lbl = QLabel(f"{emp.position} - {emp.org_unit.name if emp.org_unit else '-'}")
            pos_lbl.setStyleSheet(f"font-size: 13px; color: {_muted()}; background: transparent;")
            info.addWidget(pos_lbl)
            dr = QHBoxLayout()
            for icon_name, val in [
                ("fa5s.envelope", emp.work_email or "-"),
                ("fa5s.calendar-alt", str(emp.join_date.date()) if emp.join_date else "-"),
                ("fa5s.graduation-cap", emp.degree),
                ("fa5s.coins", _salary_text(emp)),
            ]:
                wrap = QWidget()
                wrap.setStyleSheet("background: transparent; border: none;")
                row = QHBoxLayout(wrap)
                row.setContentsMargins(0, 0, 16, 0)
                row.setSpacing(6)
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(14, 14)
                icon_lbl.setPixmap(qta.icon(icon_name, color=tokens().text_soft).pixmap(13, 13))
                l = QLabel(str(val))
                l.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft}; background: transparent;")
                row.addWidget(icon_lbl)
                row.addWidget(l)
                dr.addWidget(wrap)
            dr.addStretch()
            info.addLayout(dr)
            pc.addLayout(info)
            cl.addWidget(profile_card)

            cols = QHBoxLayout()
            cols.setSpacing(16)

            emp_card = self._info_card(t("employment_info"), [
                (t("employee_id"), emp.employee_id),
                (t("department"),  emp.org_unit.name if emp.org_unit else "-"),
                (t("position"),    emp.position),
                (t("level"),       emp.title.name if emp.title else "-"),
                (t("base_salary"), f"€{emp.base_salary:,.2f}"),
                (t("reports_to"),  emp.reports_to.full_name if emp.reports_to else "-"),
                (t("join_date"),   str(emp.join_date.date()) if emp.join_date else "-"),
            ])
            cols.addWidget(emp_card)

            race_card = QFrame()
            race_card.setStyleSheet(card_ss())
            rc = QVBoxLayout(race_card)
            rc.setContentsMargins(20, 16, 20, 16)
            rc.setSpacing(10)
            rc.addWidget(self._info_title(t("promotion_race_status")))

            if race["has_next_level"]:
                pct = race["progress_pct"]
                bar_bg = QFrame()
                bar_bg.setFixedHeight(10)
                bar_bg.setStyleSheet(f"background: {tokens().surface_muted}; border-radius: 5px;")
                bar_fill = QFrame(bar_bg)
                bar_fill.setFixedHeight(10)
                bar_fill.setStyleSheet(f"background: {tokens().success if pct >= 100 else tokens().brand}; border-radius: 5px;")
                bar_fill.setFixedWidth(max(10, int(pct / 100 * 300)))
                rc.addWidget(bar_bg)
                el = QLabel(t("eligible_for_promotion") if race["eligible"] else t("months_remaining_count", count=race["months_remaining"]))
                el.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {tokens().success if race['eligible'] else tokens().brand}; background: transparent;")
                rc.addWidget(el)
                for label, val in [
                    (t("base_track_duration"), f"{race['base_months']} months"),
                    (t("months_elapsed"),      f"{race['months_elapsed']} months"),
                    (t("commendation_reduction"), f"-{race['commendation_reduction']} months"),
                    (t("sanction_addition"),   f"+{race['sanction_addition']} months"),
                ]:
                    row = QHBoxLayout()
                    k = QLabel(label); k.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: transparent;")
                    v = QLabel(str(val)); v.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {_text()}; background: transparent;")
                    row.addWidget(k); row.addStretch(); row.addWidget(v)
                    rc.addLayout(row)
            else:
                rc.addWidget(QLabel(t("no_promotion_track")))
            rc.addStretch()
            cols.addWidget(race_card)
            cl.addLayout(cols)

            if self.user.role == "admin":
                cl.addWidget(self._info_card(t("personal_info_admin"), [
                    (t("personal_email"), emp.personal_email or "-"),
                    (t("phone"),          emp.phone or "-"),
                    (t("date_of_birth"),  str(emp.date_of_birth.date()) if emp.date_of_birth else "-"),
                    (t("address"),        emp.address or "-"),
                ], badge=t("admin_only_badge")))

            cl.addStretch()
            self.scroll.setWidget(content)
            self.header_title.setText(emp.full_name)
        finally:
            session.close()

    def _info_title(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {_text()}; background: transparent;")
        return l

    def _info_card(self, title, rows, badge=None):
        card = QFrame()
        card.setStyleSheet(card_ss())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        tr = QHBoxLayout()
        tr.addWidget(self._info_title(title))
        if badge:
            b = QLabel(badge)
            bg, fg = _admin_badge_colors()
            b.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            tr.addWidget(b)
        tr.addStretch()
        layout.addLayout(tr)
        for key, val in rows:
            row = QHBoxLayout()
            k = QLabel(key); k.setFixedWidth(140); k.setStyleSheet(f"font-size: 13px; color: {_muted()}; background: transparent;")
            v = QLabel(str(val)); v.setStyleSheet(f"font-size: 13px; color: {_text()}; font-weight: 700; background: transparent;"); v.setWordWrap(True)
            row.addWidget(k); row.addWidget(v); row.addStretch()
            layout.addLayout(row)
        return card


# Figma-style profile view. This intentionally redefines the earlier class so
# EmployeesPage gets the cleaner tabbed profile without disturbing form code above.
class EmployeeProfileView(QWidget):
    def __init__(self, user, on_back, on_edit):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.on_edit = on_edit
        self.employee_db_id = None
        self.editing = False
        self.edit_fields = {}
        self.setObjectName("EmployeeProfileView")
        self.setStyleSheet(f"QWidget#EmployeeProfileView {{ background: {_page_bg()}; font-family: 'Segoe UI'; }}" + TOOLTIP_SS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(scroll_ss(_page_bg()))
        layout.addWidget(self.scroll)

    def load(self, employee_db_id):
        if self.employee_db_id != employee_db_id:
            self.editing = False
        self.employee_db_id = employee_db_id
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_db_id).first()
            if not emp:
                return
            race = calculate_months_remaining(emp, session)
            sub_race = calculate_sub_race(emp, session)
            content = QWidget()
            content.setStyleSheet(f"background: {_page_bg()};")
            page = QVBoxLayout(content)
            page.setContentsMargins(28, 28, 28, 28)
            page.setSpacing(18)

            back = QPushButton("  " + t("back_to_employees"))
            back.setIcon(qta.icon("fa5s.arrow-left", color=tokens().text))
            back.setIconSize(QSize(12, 12))
            back.setCursor(Qt.PointingHandCursor)
            back.setFixedWidth(170)
            back.setStyleSheet(f"QPushButton {{ background: transparent; color: {_text()}; border: none; font-size: 13px; font-weight: 600; text-align: left; }} QPushButton:hover {{ color: {tokens().brand}; }}")
            back.clicked.connect(self.on_back)
            page.addWidget(back)
            page.addWidget(self._profile_header(emp))

            tabs = QTabWidget()
            tabs.setStyleSheet(pill_tab_ss())
            tabs.addTab(self._details_tab(emp, sub_race), t("personal_details"))
            tabs.addTab(self._promotion_tab(emp, race, sub_race), t("promotion_history"))
            if not is_other_employee(emp):
                tabs.addTab(self._commendations_tab(emp), t("commendations"))
                tabs.addTab(self._sanctions_tab(emp), t("sanctions"))
            install_tab_transition(tabs)
            page.addWidget(tabs)
            page.addStretch()
            self.scroll.setWidget(content)
        finally:
            session.close()

    def _profile_header(self, emp):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        initials = (emp.first_name[:1] + emp.last_name[:1]).upper()
        avatar = QLabel(initials)
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background: {tokens().brand}; color: {'#062f28' if tokens().name == THEME_DARK else '#ffffff'}; border-radius: 40px; font-size: 26px; font-weight: 800;")
        layout.addWidget(avatar)
        info = QVBoxLayout()
        info.setSpacing(6)
        name_row = QHBoxLayout()
        name = QLabel(emp.full_name)
        name.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {_text()}; background: transparent;")
        name_row.addWidget(name)
        sbg, sfg = _semantic_pair("success") if emp.status == "active" else _semantic_pair("muted")
        name_row.addWidget(self._badge(t(emp.status), sbg, sfg))
        name_row.addWidget(self._badge(display_title_name(emp.title), *_level_badge_colors()))
        name_row.addStretch()
        info.addLayout(name_row)
        pos = QLabel(emp.position)
        pos.setStyleSheet(f"font-size: 14px; color: {_muted()}; background: transparent;")
        info.addWidget(pos)
        meta = QHBoxLayout()
        for icon_name, value in [
            ("fa5s.envelope", emp.work_email or "-"),
            ("fa5s.phone", emp.work_phone or emp.phone or "-"),
            ("fa5s.map-marker-alt", emp.address or "-"),
            ("fa5s.calendar-alt", t("joined_on", date=emp.join_date.date()) if emp.join_date else "-"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(5)
            ico = QLabel()
            ico.setPixmap(qta.icon(icon_name, color=tokens().text_muted).pixmap(13, 13))
            lbl = QLabel(str(value))
            lbl.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: transparent;")
            row.addWidget(ico)
            row.addWidget(lbl)
            meta.addLayout(row)
            meta.addSpacing(16)
        meta.addStretch()
        info.addLayout(meta)
        layout.addLayout(info, 1)
        edit = QPushButton("  " + (t("editing") if self.editing else t("edit_profile")))
        edit.setIcon(qta.icon("fa5s.edit", color=_primary_button_fg()))
        edit.setIconSize(QSize(13, 13))
        edit.setCursor(Qt.PointingHandCursor)
        edit.setFixedHeight(36)
        edit.setStyleSheet(btn_primary(36))
        edit.clicked.connect(self._begin_inline_edit)
        layout.addWidget(edit, alignment=Qt.AlignTop)
        return card

    def _begin_inline_edit(self):
        if not self.employee_db_id:
            return
        self.editing = True
        self.load(self.employee_db_id)

    def _details_tab(self, emp, sub_race=None):
        if self.editing:
            return self._edit_details_tab(emp)
        page = QWidget()
        page.setStyleSheet(f"background: {_page_bg()};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        if sub_race:
            layout.addWidget(self._race_overview_card(sub_race))
            layout.addWidget(self._sub_race_card(sub_race))

        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        info_row.addWidget(self._info_card(t("employment_info"), [
            (t("employee_id"), emp.employee_id),
            (t("department"), emp.org_unit.name if emp.org_unit else "-"),
            (t("position"), emp.position),
            (t("level"), display_title_name(emp.title)),
            (t("base_salary"), _salary_text(emp)),
            (t("reports_to"), emp.reports_to.full_name if emp.reports_to else "-"),
            (t("join_date"), str(emp.join_date.date()) if emp.join_date else "-"),
        ]))
        if self.user.role == "admin":
            info_row.addWidget(self._info_card(t("personal_info_admin"), [
                (t("full_name"), emp.full_name),
                (t("personal_email"), emp.personal_email or "-"),
                (t("phone"), emp.phone or "-"),
                (t("address"), emp.address or "-"),
                (t("degree"), t("other_misc") if emp.degree == "Other" else emp.degree),
                (t("base_salary"), _salary_text(emp)),
            ], badge=t("admin_only_badge")))
        info_row.addStretch()
        layout.addLayout(info_row)
        layout.addStretch()
        return page

    def _edit_details_tab(self, emp):
        self.edit_fields = {}
        page = QWidget()
        page.setStyleSheet(f"background: {_page_bg()};")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(16)
        left.addWidget(self._edit_card("Employment Information", [
            ("position", t("position"), emp.position, True),
            ("work_email", t("work_email"), emp.work_email or "", False),
            ("work_phone", t("work_phone"), emp.work_phone or "", False),
            ("base_salary", t("base_salary"), str(emp.base_salary or 0), False),
        ]))
        if self.user.role == "admin":
            left.addWidget(self._edit_card(t("personal_info_admin"), [
                ("first_name", t("first_name"), emp.first_name, True),
                ("last_name", t("last_name"), emp.last_name, True),
                ("personal_email", t("personal_email"), emp.personal_email or "", False),
                ("phone", t("phone"), emp.phone or "", False),
                ("address", t("address"), emp.address or "", False),
            ]))
        layout.addLayout(left, 3)

        right_card = QFrame()
        right_card.setObjectName("ProfileCard")
        right_card.setStyleSheet(PROFILE_CARD_SS())
        right = QVBoxLayout(right_card)
        right.setContentsMargins(24, 24, 24, 24)
        right.setSpacing(12)
        right.addWidget(self._info_title(t("organization_and_status")))

        session = get_session()
        try:
            right.addWidget(self._edit_label(t("org_unit")))
            self.inline_org_combo = CleanSelect()
            if is_other_employee(emp):
                others = ensure_others_org_unit(session)
                session.flush()
                self.inline_org_combo.addItem(OTHER_ORG_UNIT_NAME, others.id)
            else:
                self.inline_org_combo.addItem(t("none"), None)
                for unit in session.query(OrgUnit).filter(OrgUnit.name != OTHER_ORG_UNIT_NAME).all():
                    self.inline_org_combo.addItem(f"{unit.unit_type.title()}: {unit.name}", unit.id)
                    if emp.org_unit_id == unit.id:
                        self.inline_org_combo.setCurrentIndex(self.inline_org_combo.count() - 1)
            right.addWidget(self.inline_org_combo)

            right.addWidget(self._edit_label(t("reports_to")))
            self.inline_manager_combo = CleanSelect()
            self.inline_manager_combo.addItem(t("none"), None)
            manager_filter = valid_other_manager_ids(session) if is_other_employee(emp) else None
            for manager in session.query(Employee).filter(Employee.id != emp.id).all():
                if manager_filter is not None and manager.id not in manager_filter:
                    continue
                self.inline_manager_combo.addItem(f"{manager.employee_id} - {manager.full_name}", manager.id)
                if emp.reports_to_id == manager.id:
                    self.inline_manager_combo.setCurrentIndex(self.inline_manager_combo.count() - 1)
            right.addWidget(self.inline_manager_combo)

            right.addWidget(self._edit_label(t("current_level_role")))
            self.inline_title_combo = CleanSelect()
            for title in session.query(Title).order_by(Title.name.desc()).all():
                self.inline_title_combo.addItem(f"{display_title_name(title)} - {title.label}", title.id)
                if emp.title_id == title.id:
                    self.inline_title_combo.setCurrentIndex(self.inline_title_combo.count() - 1)
            self.inline_title_combo.valueChanged.connect(self._update_inline_salary_warning)
            right.addWidget(self.inline_title_combo)
        finally:
            session.close()

        self.inline_salary_warning = QLabel("")
        self.inline_salary_warning.setWordWrap(True)
        self.inline_salary_warning.hide()
        self.inline_salary_warning.setStyleSheet(_warning_ss())
        right.addWidget(self.inline_salary_warning)
        self.edit_fields["base_salary"].textChanged.connect(self._update_inline_salary_warning)
        self._update_inline_salary_warning()

        right.addWidget(self._edit_label(t("status")))
        self.inline_status_combo = CleanSelect()
        for status in STATUS_OPTIONS:
            self.inline_status_combo.addItem(status.replace("_", " ").title(), status)
            if emp.status == status:
                self.inline_status_combo.setCurrentIndex(self.inline_status_combo.count() - 1)
        right.addWidget(self.inline_status_combo)
        right.addSpacing(10)

        save = QPushButton(t("save_changes"))
        save.setCursor(Qt.PointingHandCursor)
        save.setFixedHeight(44)
        save.setStyleSheet(btn_primary(40))
        save.clicked.connect(self._save_inline_profile)
        right.addWidget(save)

        cancel = QPushButton(t("cancel"))
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setFixedHeight(44)
        cancel.setStyleSheet(btn_outline(40))
        cancel.clicked.connect(self._cancel_inline_edit)
        right.addWidget(cancel)
        right.addStretch()

        layout.addWidget(right_card, 2)
        return page

    def _edit_card(self, title, fields):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self._info_title(title))
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)
        for i, (key, label, value, required) in enumerate(fields):
            field = QVBoxLayout()
            field.setSpacing(6)
            field.addWidget(self._edit_label(label + (" *" if required else "")))
            editor = QLineEdit(str(value))
            editor.setFixedHeight(44)
            editor.setStyleSheet(INPUT_STYLE())
            field.addWidget(editor)
            self.edit_fields[key] = editor
            grid.addLayout(field, i // 2, i % 2)
        layout.addLayout(grid)
        return card

    def _edit_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {_text()}; background: transparent; border: none;")
        return label

    def _cancel_inline_edit(self):
        self.editing = False
        self.load(self.employee_db_id)

    def _update_inline_salary_warning(self):
        if not hasattr(self, "inline_salary_warning"):
            return
        widget = self.edit_fields.get("base_salary")
        salary_raw = widget.text().strip() if widget else ""
        if not salary_raw:
            self.inline_salary_warning.hide()
            return
        try:
            salary = float(salary_raw)
        except ValueError:
            self.inline_salary_warning.setText(t("salary_number_required"))
            self.inline_salary_warning.show()
            return
        session = get_session()
        try:
            title = session.query(Title).filter_by(id=self.inline_title_combo.currentData()).first()
            ok, message = validate_salary_for_title(title, salary)
            self.inline_salary_warning.setText(message)
            self.inline_salary_warning.setVisible(not ok)
        finally:
            session.close()

    def _save_inline_profile(self):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=self.employee_db_id).first()
            if not emp:
                return
            before = json.dumps({"position": emp.position, "status": emp.status, "base_salary": emp.base_salary})

            def value(key):
                widget = self.edit_fields.get(key)
                return widget.text().strip() if widget else ""

            if not value("position"):
                message_warning(self, t("warning"), f"{t('position')} {t('required_field').lower()}.")
                return

            emp.position = value("position")
            emp.work_email = value("work_email") or None
            emp.work_phone = value("work_phone") or None
            salary_raw = value("base_salary")
            try:
                new_salary = float(salary_raw) if salary_raw else 0.0
            except ValueError:
                message_warning(self, t("warning"), t("salary_number_required"))
                return

            manager_id = self.inline_manager_combo.currentData()
            title_id = self.inline_title_combo.currentData()
            status = self.inline_status_combo.currentData()
            if title_id is None:
                message_warning(self, t("warning"), t("valid_level_required"))
                return
            if status is None:
                message_warning(self, t("warning"), t("valid_status_required"))
                return
            if _would_create_manager_cycle(session, emp.id, manager_id):
                message_warning(self, t("warning"), t("manager_cycle_error"))
                return
            title = session.query(Title).filter_by(id=title_id).first()
            ok, salary_message = validate_salary_for_title(title, new_salary)
            if not ok:
                message_warning(self, t("warning"), salary_message)
                return
            if title and is_other_title(title):
                others = ensure_others_org_unit(session)
                emp.org_unit_id = others.id
                valid_managers = valid_other_manager_ids(session)
                if manager_id and manager_id not in valid_managers:
                    message_warning(self, t("warning"), t("other_manager_required"))
                    return
                emp.degree = "Other"
            else:
                emp.org_unit_id = self.inline_org_combo.currentData()

            emp.reports_to_id = manager_id
            emp.title_id = title_id
            emp.base_salary = new_salary
            emp.status = status

            if self.user.role == "admin":
                if not value("first_name") or not value("last_name"):
                    message_warning(self, t("warning"), t("first_last_required"))
                    return
                emp.first_name = value("first_name")
                emp.last_name = value("last_name")
                emp.personal_email = value("personal_email") or None
                emp.phone = value("phone") or None
                emp.address = value("address") or None

            after = json.dumps({"position": emp.position, "status": emp.status, "base_salary": emp.base_salary})
            log_action(session=session, performed_by_id=self.user.id, action="employee.update",
                target_table="employee", target_id=emp.id,
                description=f"Employee updated: {emp.full_name} ({emp.employee_id})",
                before_value=before, after_value=after)
            session.commit()
            self.editing = False
            self.load(emp.id)
        except Exception as exc:
            session.rollback()
            message_critical(self, t("error"), str(exc))
        finally:
            session.close()

    def _promotion_tab(self, emp, race, sub_race):
        page = QWidget()
        page.setStyleSheet(f"background: {_page_bg()};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(14)
        card = self._list_card(t("promotion_history"))
        body = card.layout()
        timeline = []
        for promo in emp.promotions:
            timeline.append((
                promo.promoted_at or datetime.min,
                self._event_row(
                    "fa5s.chart-line",
                    "#10b981",
                    t("promotion_event_title", from_level=display_title_name(promo.from_title), to_level=display_title_name(promo.to_title)),
                    promo.notes or promo.basis.replace("_", " ").title(),
                    promo.promoted_at.strftime("%Y-%m-%d") if promo.promoted_at else "-",
                ),
            ))
        for inc in emp.salary_increments:
            timeline.append((
                inc.applied_at or datetime.min,
                self._event_row(
                    "fa5s.percentage",
                    "#2563eb",
                    t("sub_race_increment_event"),
                    inc.notes or t("annual_increment"),
                    inc.applied_at.strftime("%Y-%m-%d") if inc.applied_at else "-",
                ),
            ))
        for _, widget in sorted(timeline, key=lambda item: item[0], reverse=True):
            body.addWidget(widget)
        body.addWidget(self._event_row("fa5s.chart-line", "#10b981", t("initial_position"), t("initial_hire_degree", degree=emp.degree), emp.join_date.strftime("%Y-%m-%d") if emp.join_date else "-"))
        if race["has_next_level"]:
            body.addWidget(self._event_row("fa5s.clock", "#2563eb", t("current_promotion_race"), t("current_race_progress", percent=race["progress_pct"], months=race["months_remaining"]), t("live_label")))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _race_overview_card(self, sub_race):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        header = QHBoxLayout()
        header.addWidget(self._info_title(t("current_promotion_race")))
        header.addStretch()
        layout.addLayout(header)

        next_step = next((step for step in sub_race.get("steps", []) if not step.get("completed")), None)
        right_label = sub_race.get("next_title") or (next_step["label"] if next_step else t("annual_increment"))
        expected_date = sub_race.get("expected_promotion_date") or (next_step.get("due_date") if next_step else None)
        expected_text = expected_date.strftime("%Y-%m-%d") if expected_date else "-"
        start_text = sub_race["race_start"].strftime("%Y-%m-%d") if sub_race.get("race_start") else "-"
        middle_text = (
            t("months_remaining_count", count=sub_race["months_left"])
            if sub_race.get("months_left") is not None
            else t("ongoing_service_track")
        )

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._badge(sub_race["current_title"], *_level_badge_colors()))
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(sub_race.get("progress_pct") or 0)
        bar.setFixedHeight(12)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"QProgressBar {{ background: {tokens().surface_muted}; border-radius: 6px; border: none; }} QProgressBar::chunk {{ background: {tokens().warning}; border-radius: 6px; }}")
        bar.setToolTip(middle_text)
        row.addWidget(bar, 1)
        sbg, sfg = _semantic_pair("success")
        row.addWidget(self._badge(right_label, sbg, sfg))
        layout.addLayout(row)

        meta = QGridLayout()
        meta.setHorizontalSpacing(18)
        for col, (label, value, align) in enumerate([
            (t("started"), start_text, Qt.AlignLeft),
            (t("remaining"), middle_text, Qt.AlignCenter),
            (t("expected"), expected_text, Qt.AlignRight),
        ]):
            label_widget = QLabel(label.upper())
            label_widget.setAlignment(align)
            label_widget.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {tokens().text_soft}; letter-spacing: 0; background: transparent;")
            value_widget = QLabel(value)
            value_widget.setAlignment(align)
            value_widget.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {tokens().text}; background: transparent;")
            value_widget.setToolTip(value)
            meta.addWidget(label_widget, 0, col)
            meta.addWidget(value_widget, 1, col)
            meta.setColumnStretch(col, 1)
        layout.addLayout(meta)
        return card

    def _sub_race_card(self, sub_race):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(self._info_title(t("sub_race")))

        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroller.setFixedHeight(128)
        scroller.setStyleSheet("border: none; background: transparent;")
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        row = QHBoxLayout(holder)
        row.setContentsMargins(36, 0, 36, 0)
        row.setSpacing(12)
        for step in sub_race.get("steps", []):
            box = QFrame()
            done = step["completed"]
            bg, color = _semantic_pair("success") if done else _semantic_pair("muted")
            border = tokens().success if done else tokens().border
            box.setStyleSheet(f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }} QLabel {{ background: transparent; border: none; }}")
            box.setFixedWidth(118)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(10, 8, 10, 8)
            bl.setSpacing(4)
            title = QLabel(step["label"])
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {color};")
            date_text = step["due_date"].strftime("%Y-%m-%d") if step.get("due_date") else "-"
            box.setToolTip(f"{step['label']} - {date_text}")
            date = QLabel(date_text)
            date.setAlignment(Qt.AlignCenter)
            date.setStyleSheet(f"font-size: 11px; color: {color};")
            inc = QLabel(step.get("increment") or "")
            inc.setAlignment(Qt.AlignCenter)
            inc.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color};")
            bl.addWidget(title)
            bl.addWidget(date)
            bl.addWidget(inc)
            row.addWidget(box)
        row.addStretch()
        scroller.setWidget(holder)
        layout.addWidget(scroller)
        return card

    def _commendations_tab(self, emp):
        page = QWidget()
        page.setStyleSheet(f"background: {_page_bg()};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        card = self._list_card(t("commendations"))
        body = card.layout()
        if emp.commendations:
            for comm in sorted(emp.commendations, key=lambda c: c.issued_at or datetime.min, reverse=True):
                body.addWidget(self._event_row("fa5s.award", "#f59e0b", f"{comm.title} ({comm.commendation_ref})", f"{t('commendation_category')} {comm.category} - {abs(comm.months_impact)}", comm.issued_at.strftime("%Y-%m-%d") if comm.issued_at else "-"))
        else:
            body.addWidget(self._empty_row(t("no_commendations")))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _sanctions_tab(self, emp):
        page = QWidget()
        page.setStyleSheet(f"background: {_page_bg()};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        card = self._list_card(t("sanctions"))
        body = card.layout()
        if emp.sanctions:
            for sanction in sorted(emp.sanctions, key=lambda s: s.issued_at or datetime.min, reverse=True):
                status = t("resolved") if sanction.is_resolved else t("active")
                resolved = f", resolved {sanction.resolved_at:%Y-%m-%d}" if sanction.resolved_at else ""
                body.addWidget(self._event_row("fa5s.exclamation-triangle", "#ef4444", f"{t(sanction.sanction_type)} ({sanction.sanction_ref})", f"{sanction.reason} - +{sanction.delay_months}, {status}{resolved}", sanction.issued_at.strftime("%Y-%m-%d") if sanction.issued_at else "-"))
        else:
            body.addWidget(self._empty_row(t("no_sanctions")))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _info_title(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {_text()}; background: transparent;")
        return label

    def _small_meta(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: transparent;")
        return label

    def _badge(self, text, bg, fg):
        label = QLabel(text)
        label.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 6px; padding: 2px 9px; font-size: 11px; font-weight: 700;")
        return label

    def _info_card(self, title, rows, badge=None):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(self._info_title(title))
        if badge:
            header.addWidget(self._badge(badge, *_admin_badge_colors()))
        header.addStretch()
        layout.addLayout(header)
        for key, val in rows:
            field = QVBoxLayout()
            field.setSpacing(4)
            k = QLabel(key)
            k.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {_text()}; background: transparent;")
            v = QLabel(str(val))
            v.setWordWrap(True)
            v.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: {tokens().surface_muted}; border: none; border-radius: 7px; padding: 8px 10px;")
            field.addWidget(k)
            field.addWidget(v)
            layout.addLayout(field)
        return card

    def _list_card(self, title):
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet(PROFILE_CARD_SS())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(self._info_title(title))
        return card

    def _event_row(self, icon_name, color, title, subtitle, date_text):
        row = QFrame()
        row.setObjectName("EventRow")
        row.setStyleSheet(f"QFrame#EventRow {{ background: transparent; border: none; border-bottom: 1px solid {tokens().border}; }} QFrame#EventRow QLabel {{ border: none; background: transparent; }}")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(12)
        soft_bg = _soft_bg_for_color(color)
        icon = QLabel()
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: {soft_bg}; border-radius: 8px;")
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(15, 15))
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {_text()}; background: transparent;")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: transparent;")
        text_col.addWidget(title_lbl)
        text_col.addWidget(sub_lbl)
        date = QLabel(date_text)
        date.setStyleSheet(f"font-size: 12px; color: {_muted()}; background: transparent;")
        layout.addWidget(icon)
        layout.addLayout(text_col, 1)
        layout.addWidget(date, alignment=Qt.AlignTop)
        return row

    def _empty_row(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"font-size: 13px; color: {tokens().text_soft}; padding: 24px; background: transparent;")
        return label
