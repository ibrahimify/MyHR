"""
Employees Page - Fixed version
Fixes:
- Employee Edit functionality added
- Org unit graceful handling when none exist
- Status combo on add/edit forms
- Edit button wired up properly
"""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QTabWidget,
    QTextEdit, QMessageBox, QDateEdit, QGridLayout
)
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, generate_employee_id, log_action,
    degree_to_title_name, calculate_months_remaining
)
from src.database.models import (
    Employee, Title, OrgUnit,
    CommendationEmployee, PromotionHistory, SalaryIncrementHistory, Sanction
)
from datetime import datetime
import json

DEGREE_OPTIONS = ["BSc", "MSc", "PhD", "Other"]
STATUS_OPTIONS = ["active", "inactive", "on_leave"]
COMBO_STYLE = """
QComboBox {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 32px 0 12px;
    font-size: 14px;
    background: #f3f4f6;
    color: #111827;
    min-height: 40px;
}
QComboBox:focus {
    border-color: #2563eb;
    background: white;
}
QComboBox::drop-down {
    width: 28px;
    border: none;
    background: transparent;
}
"""
INPUT_STYLE = """
QLineEdit {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 14px;
    background: #f3f4f6;
    color: #111827;
    min-height: 40px;
}
QLineEdit:focus {
    border-color: #2563eb;
    background: white;
}
"""
EMP_CARD_SS = """
QFrame#EmployeeCard {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame#EmployeeCard QLabel {
    border: none;
    background: transparent;
}
"""


class EmployeesPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
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

    def _show_list(self):
        self.list_page.refresh()
        self.stack.setCurrentWidget(self.list_page)

    def _show_add(self):
        self.add_page.reset()
        self.stack.setCurrentWidget(self.add_page)

    def _show_profile(self, employee_id):
        self.profile_page.load(employee_id)
        self.stack.setCurrentWidget(self.profile_page)

    def _show_edit(self, employee_id):
        self.edit_page.load(employee_id)
        self.stack.setCurrentWidget(self.edit_page)


class EmployeeListView(QWidget):
    def __init__(self, user, on_add, on_profile):
        super().__init__()
        self.user = user
        self.on_add = on_add
        self.on_profile = on_profile
        self.all_employees = []
        self._on_edit_cb = None
        self.setStyleSheet("QWidget { background: #f9fafb; font-family: 'Segoe UI'; }")
        self._build()
        self.refresh()

    def set_edit_callback(self, cb):
        self._on_edit_cb = cb

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel("Employee Management")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel("Manage and view all employee records")
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        bar = QFrame()
        bar.setObjectName("EmployeeCard")
        bar.setStyleSheet(EMP_CARD_SS)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(20, 20, 20, 20)
        bl.setSpacing(16)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, ID, or email...")
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._apply_filter)
        bl.addWidget(self.search_input, 1)

        self.dept_filter = QComboBox()
        self.dept_filter.setFixedHeight(44)
        self.dept_filter.setMinimumWidth(220)
        self.dept_filter.setStyleSheet(COMBO_STYLE)
        self.dept_filter.addItem("All Departments", None)
        self.dept_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.dept_filter)

        self.status_filter = QComboBox()
        self.status_filter.setFixedHeight(44)
        self.status_filter.setMinimumWidth(180)
        self.status_filter.setStyleSheet(COMBO_STYLE)
        self.status_filter.addItem("All Status", None)
        for s in STATUS_OPTIONS:
            self.status_filter.addItem(s.replace("_", " ").title(), s)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.status_filter)

        add_btn = QPushButton("  " + t("add_employee"))
        add_btn.setIcon(qta.icon("fa5s.user-plus", color="white"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(44)
        add_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; padding: 0 18px; } QPushButton:hover { background: #111827; }")
        add_btn.clicked.connect(self.on_add)
        bl.addWidget(add_btn)
        layout.addWidget(bar)
        layout.addSpacing(28)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size: 14px; color: #4b5563; background: transparent;")
        layout.addWidget(self.count_lbl)
        layout.addSpacing(20)

        table_card = QFrame()
        table_card.setObjectName("EmployeeCard")
        table_card.setStyleSheet(EMP_CARD_SS)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Employee ID", "Name", "Email", "Department",
            "Position", "Level", "Status", "Actions"
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: none;
                gridline-color: #f3f4f6;
                font-size: 14px;
                color: #111827;
                outline: none;
            }
            QTableWidget::item {
                padding: 0 12px;
                border: none;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget::item:selected { background: #eff6ff; color: #111827; }
            QHeaderView::section {
                background: white;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 0 12px;
                font-size: 13px;
                font-weight: 700;
                color: #111827;
                min-height: 50px;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 270)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 240)
        self.table.setColumnWidth(5, 95)
        self.table.setColumnWidth(6, 140)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 132)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

    def refresh(self):
        session = get_session()
        try:
            emps = session.query(Employee).all()
            self.all_employees = [{
                "id": e.id, "employee_id": e.employee_id, "full_name": e.full_name,
                "email": e.work_email or e.personal_email or "—",
                "dept": e.org_unit.name if e.org_unit else "—",
                "position": e.position,
                "level": e.title.name if e.title else "—",
                "degree": e.degree, "status": e.status,
            } for e in emps]
            depts = sorted({x["dept"] for x in self.all_employees if x["dept"] != "—"})
            self.dept_filter.blockSignals(True)
            self.dept_filter.clear()
            self.dept_filter.addItem("All Departments", None)
            for d in depts:
                self.dept_filter.addItem(d, d)
            self.dept_filter.blockSignals(False)
        finally:
            session.close()
        self._apply_filter()

    def _apply_filter(self):
        search = self.search_input.text().lower()
        dept   = self.dept_filter.currentData()
        status = self.status_filter.currentData()
        filtered = [e for e in self.all_employees if
            (not search or search in e["full_name"].lower() or search in e["employee_id"].lower() or search in e["email"].lower()) and
            (not dept   or e["dept"] == dept) and
            (not status or e["status"] == status)
        ]
        self.count_lbl.setText(f"Showing {len(filtered)} of {len(self.all_employees)} employees")
        self._populate_table(filtered)

    def _populate_table(self, employees):
        self.table.setRowCount(len(employees))
        self.table.setMinimumHeight(52 + (62 * max(1, len(employees))))
        STATUS_COLORS = {"active": ("#dcfce7","#166534"), "inactive": ("#f3f4f6","#374151"), "on_leave": ("#fef9c3","#854d0e")}

        for row, emp in enumerate(employees):
            self.table.setRowHeight(row, 62)
            for col, val in enumerate([emp["employee_id"], emp["full_name"], emp["email"], emp["dept"], emp["position"]]):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, emp["id"])
                if col == 2:
                    item.setForeground(QColor("#4b5563"))
                self.table.setItem(row, col, item)

            self.table.setCellWidget(row, 3, self._badge(emp["dept"], "white", "#111827", border="#e5e7eb"))
            self.table.setCellWidget(row, 5, self._badge(emp["level"], "#dbeafe", "#1d4ed8"))
            bg, fg = STATUS_COLORS.get(emp["status"], ("#f3f4f6","#374151"))
            self.table.setCellWidget(row, 6, self._badge(emp["status"].replace("_", " ").title(), bg, fg))

            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(6, 0, 6, 0)
            btn_layout.setSpacing(8)
            btn_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            _ico = QSize(16, 16)
            _btn_ss = (
                "QPushButton {{ background: transparent; border: none; border-radius: 6px;"
                " min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }}"
                " QPushButton:hover {{ background: {hover}; }}"
            )

            view_btn = QPushButton()
            view_btn.setIcon(qta.icon("fa5s.eye", color="#2563eb"))
            view_btn.setIconSize(_ico)
            view_btn.setToolTip("View profile")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet(_btn_ss.format(hover="#eff6ff"))
            view_btn.clicked.connect(lambda _, eid=emp["id"]: self.on_profile(eid))

            edit_btn = QPushButton()
            edit_btn.setIcon(qta.icon("fa5s.edit", color="#374151"))
            edit_btn.setIconSize(_ico)
            edit_btn.setToolTip("Edit employee")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(_btn_ss.format(hover="#f3f4f6"))
            edit_btn.clicked.connect(lambda _, eid=emp["id"]: self._do_edit(eid))

            del_btn = QPushButton()
            del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#dc2626"))
            del_btn.setIconSize(_ico)
            del_btn.setToolTip("Delete employee")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(_btn_ss.format(hover="#fee2e2"))
            del_btn.clicked.connect(lambda _, eid=emp["id"]: self._do_delete(eid))

            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 7, btn_widget)

    def _badge(self, text, bg, fg, border=None):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
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
        confirm = QMessageBox.question(
            self, "Delete Employee",
            "Are you sure you want to permanently delete this employee?\n\n"
            "All promotion history, commendations, sanctions, and salary records "
            "for this employee will also be removed.\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
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
            QMessageBox.information(self, t("success"), f"{emp_name} ({emp_code}) has been deleted.")
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


class AddEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.fields = {}
        self.setStyleSheet("QWidget { background: #f9fafb; font-family: 'Segoe UI'; }")
        self._build()
        self.reset()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: #f9fafb; border: none;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("  Back to Employees")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; font-weight: 600; } QPushButton:hover { text-decoration: underline; }")
        back_btn.clicked.connect(self.on_back)
        title = QLabel("Add New Employee")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #111827; margin-left: 12px;")
        h.addWidget(back_btn)
        h.addWidget(title)
        h.addStretch()
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(40, 24, 40, 40)
        cl.setSpacing(24)
        cl.setAlignment(Qt.AlignTop)

        left = QVBoxLayout()
        left.setSpacing(24)
        left.addWidget(self._section_card("Personal Information", [
            ("first_name",    t("first_name"),    "text"),
            ("last_name",     t("last_name"),      "text"),
            ("date_of_birth", t("date_of_birth"),  "date"),
            ("personal_email",t("personal_email"), "text"),
            ("phone",         t("phone"),          "text"),
            ("address",       t("address"),        "textarea"),
        ]))

        deg_card = QFrame()
        deg_card.setObjectName("EmployeeCard")
        deg_card.setStyleSheet(EMP_CARD_SS)
        dcl = QVBoxLayout(deg_card)
        dcl.setContentsMargins(24, 24, 24, 24)
        dcl.setSpacing(18)
        dcl.addWidget(self._lbl("Education & Level Assignment", bold=True, size=18, color="#111827"))
        row = QHBoxLayout()
        row.setSpacing(12)
        dl = QVBoxLayout()
        dl.addWidget(self._lbl(t("degree") + " *"))
        self.degree_combo = QComboBox()
        self.degree_combo.setFixedHeight(44)
        self.degree_combo.setStyleSheet(COMBO_STYLE)
        for d in DEGREE_OPTIONS:
            self.degree_combo.addItem(d)
        self.degree_combo.currentTextChanged.connect(lambda deg: self.level_display.setText(degree_to_title_name(deg)))
        dl.addWidget(self.degree_combo)
        row.addLayout(dl)
        ll = QVBoxLayout()
        ll.addWidget(self._lbl(t("auto_level")))
        self.level_display = QLabel("L7")
        self.level_display.setFixedHeight(44)
        self.level_display.setAlignment(Qt.AlignCenter)
        self.level_display.setStyleSheet("background: #eff6ff; color: #2563eb; border-radius: 8px; font-size: 16px; font-weight: bold; border: 1px solid #bfdbfe;")
        ll.addWidget(self.level_display)
        row.addLayout(ll)
        dcl.addLayout(row)
        dcl.addWidget(self._lbl(t("level_rule"), color="#9ca3af", size=11))
        left.addWidget(deg_card)

        left.addWidget(self._section_card("Employment Details", [
            ("work_email",  t("work_email"),  "text"),
            ("work_phone",  t("work_phone"),  "text"),
            ("position",    t("position"),    "text"),
            ("join_date",   t("join_date"),   "date"),
            ("base_salary", t("base_salary"), "text"),
        ]))
        cl.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        org_card = QFrame()
        org_card.setObjectName("EmployeeCard")
        org_card.setStyleSheet(EMP_CARD_SS)
        oc = QVBoxLayout(org_card)
        oc.setContentsMargins(24, 24, 24, 24)
        oc.setSpacing(10)
        oc.addWidget(self._lbl("Organization", bold=True, size=18, color="#111827"))
        oc.addWidget(self._lbl("Org Unit"))
        self.org_combo = QComboBox()
        self.org_combo.setFixedHeight(44)
        self.org_combo.setStyleSheet(COMBO_STYLE)
        oc.addWidget(self.org_combo)
        oc.addWidget(self._lbl(t("reports_to")))
        self.manager_combo = QComboBox()
        self.manager_combo.setFixedHeight(44)
        self.manager_combo.setStyleSheet(COMBO_STYLE)
        oc.addWidget(self.manager_combo)
        oc.addWidget(self._lbl(t("status")))
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(44)
        self.status_combo.setStyleSheet(COMBO_STYLE)
        for s in STATUS_OPTIONS:
            self.status_combo.addItem(s.replace("_"," ").title(), s)
        oc.addWidget(self.status_combo)
        right.addWidget(org_card)

        info_card = QFrame()
        info_card.setStyleSheet("QFrame { background: #f0fdf4; border-radius: 12px; border: 1px solid #bbf7d0; } QLabel { border: none; background: transparent; }")
        ic = QVBoxLayout(info_card)
        ic.setContentsMargins(24, 22, 24, 22)
        ic.setSpacing(10)
        ic.addWidget(self._lbl("Salary Guidelines", bold=True, size=16, color="#166534"))
        for line in ["L7 (BSc): €2,000 – €2,800", "L6 (MSc): €2,800 – €3,500", "L5 (PhD): €3,500 – €4,500"]:
            l = QLabel(line)
            l.setStyleSheet("font-size: 13px; color: #166534; background: transparent;")
            ic.addWidget(l)
        right.addWidget(info_card)

        save_btn = QPushButton("Save Employee")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setIcon(qta.icon("fa5s.save", color="white"))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; } QPushButton:hover { background: #111827; }")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet("QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-weight: 600; } QPushButton:hover { background: #f3f4f6; }")
        cancel_btn.clicked.connect(self.on_back)
        right.addWidget(cancel_btn)
        cl.addLayout(right, 2)
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _lbl(self, text, bold=False, size=12, color="#6b7280"):
        l = QLabel(text)
        fw = "bold" if bold else "normal"
        l.setStyleSheet(f"font-size: {size}px; font-weight: {fw}; color: {color}; background: transparent;")
        return l

    def _section_card(self, title, fields):
        card = QFrame()
        card.setObjectName("EmployeeCard")
        card.setStyleSheet(EMP_CARD_SS)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(self._lbl(title, bold=True, size=18, color="#111827"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(16)
        grid_row = 0
        grid_col = 0
        for key, label, ftype in fields:
            field = QVBoxLayout()
            field.setSpacing(6)
            field.addWidget(self._lbl(label + (" *" if key in ["first_name","last_name","position","join_date"] else ""), bold=True, color="#111827"))
            if ftype == "textarea":
                widget = QTextEdit()
                widget.setFixedHeight(80)
                widget.setStyleSheet("QTextEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 12px; font-size: 14px; background: #f3f4f6; color: #111827; } QTextEdit:focus { border-color: #2563eb; background: white; }")
            elif ftype == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setFixedHeight(44)
                widget.setDate(QDate.currentDate())
                widget.setStyleSheet("QDateEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 14px; background: #f3f4f6; color: #111827; } QDateEdit:focus { border-color: #2563eb; background: white; }")
            else:
                widget = QLineEdit()
                widget.setFixedHeight(44)
                widget.setStyleSheet(INPUT_STYLE)
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
        self.level_display.setText("L7")
        self.status_combo.setCurrentIndex(0)
        self._load_org_units()
        self._load_managers()

    def _load_org_units(self):
        self.org_combo.clear()
        self.org_combo.addItem("— None —", None)
        session = get_session()
        try:
            for u in session.query(OrgUnit).all():
                self.org_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
        finally:
            session.close()

    def _load_managers(self):
        self.manager_combo.clear()
        self.manager_combo.addItem("— None —", None)
        session = get_session()
        try:
            for e in session.query(Employee).filter_by(status="active").all():
                self.manager_combo.addItem(f"{e.employee_id} — {e.full_name}", e.id)
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
                QMessageBox.warning(self, t("warning"), f"{label} is required.")
                return
        session = get_session()
        try:
            degree = self.degree_combo.currentText()
            title = session.query(Title).filter_by(name=degree_to_title_name(degree)).first()
            if not title:
                QMessageBox.critical(self, t("error"), "Title not found.")
                return
            emp_id = generate_employee_id(session)
            join_dt = self._get("join_date")
            dob_dt  = self._get("date_of_birth")
            salary_raw = self._get("base_salary")
            try:
                salary = float(salary_raw) if salary_raw else 0.0
            except ValueError:
                QMessageBox.warning(self, t("warning"), "Base salary must be a number.")
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
                title_id=title.id, org_unit_id=self.org_combo.currentData(),
                reports_to_id=self.manager_combo.currentData(),
            )
            session.add(emp)
            session.flush()
            log_action(session=session, performed_by_id=self.user.id, action="employee.create",
                target_table="employee", target_id=emp.id,
                description=f"New employee added: {emp.full_name} ({emp_id})")
            session.commit()
            QMessageBox.information(self, t("success"), f"Employee {emp.full_name} ({emp_id}) added successfully.")
            self.on_back()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


class EditEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.employee_db_id = None
        self.fields = {}
        self.setStyleSheet("background: #f9fafb;")
        self._build_shell()

    def _build_shell(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("  Back to Employees")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; font-weight: 600; } QPushButton:hover { text-decoration: underline; }")
        back_btn.clicked.connect(self.on_back)
        self.header_title = QLabel("Edit Employee")
        self.header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827; margin-left: 12px;")
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
            self.header_title.setText(f"Edit — {emp.full_name}")

            content = QWidget()
            content.setStyleSheet("background: #f9fafb;")
            cl = QHBoxLayout(content)
            cl.setContentsMargins(28, 24, 28, 28)
            cl.setSpacing(20)
            cl.setAlignment(Qt.AlignTop)

            left = QVBoxLayout()
            left.setSpacing(16)

            # Work card
            wcard = self._form_card("Employment Details", [
                ("position",   "Position *",     emp.position),
                ("work_email", "Work Email",      emp.work_email or ""),
                ("work_phone", "Work Phone",      emp.work_phone or ""),
                ("base_salary","Base Salary (€)", str(emp.base_salary)),
            ])
            left.addWidget(wcard)

            if self.user.role == "admin":
                pcard = self._form_card("Personal Information (Admin Only)", [
                    ("first_name",    "First Name *",   emp.first_name),
                    ("last_name",     "Last Name *",    emp.last_name),
                    ("personal_email","Personal Email", emp.personal_email or ""),
                    ("phone",         "Phone",          emp.phone or ""),
                    ("address",       "Address",        emp.address or ""),
                ])
                left.addWidget(pcard)

            cl.addLayout(left, 3)

            right = QVBoxLayout()
            right.setSpacing(16)
            right.setAlignment(Qt.AlignTop)

            org_card = QFrame()
            org_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
            oc = QVBoxLayout(org_card)
            oc.setContentsMargins(20, 16, 20, 16)
            oc.setSpacing(8)
            t_lbl = QLabel("Organization & Status")
            t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
            oc.addWidget(t_lbl)

            oc.addWidget(self._small_lbl("Org Unit"))
            self.org_combo = QComboBox()
            self.org_combo.setFixedHeight(36)
            self.org_combo.setStyleSheet(COMBO_STYLE)
            self.org_combo.addItem("— None —", None)
            for u in session.query(OrgUnit).all():
                self.org_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
                if emp.org_unit_id == u.id:
                    self.org_combo.setCurrentIndex(self.org_combo.count() - 1)
            oc.addWidget(self.org_combo)

            oc.addWidget(self._small_lbl("Reports To"))
            self.manager_combo = QComboBox()
            self.manager_combo.setFixedHeight(36)
            self.manager_combo.setStyleSheet(COMBO_STYLE)
            self.manager_combo.addItem("— None —", None)
            for e in session.query(Employee).filter(Employee.id != employee_db_id).all():
                self.manager_combo.addItem(f"{e.employee_id} — {e.full_name}", e.id)
                if emp.reports_to_id == e.id:
                    self.manager_combo.setCurrentIndex(self.manager_combo.count() - 1)
            oc.addWidget(self.manager_combo)

            oc.addWidget(self._small_lbl("Current Level / Role"))
            self.title_combo = QComboBox()
            self.title_combo.setFixedHeight(36)
            self.title_combo.setStyleSheet(COMBO_STYLE)
            for title in session.query(Title).order_by(Title.name.desc()).all():
                self.title_combo.addItem(f"{title.name} - {title.label}", title.id)
                if emp.title_id == title.id:
                    self.title_combo.setCurrentIndex(self.title_combo.count() - 1)
            oc.addWidget(self.title_combo)

            oc.addWidget(self._small_lbl("Status"))
            self.status_combo = QComboBox()
            self.status_combo.setFixedHeight(36)
            self.status_combo.setStyleSheet(COMBO_STYLE)
            for s in STATUS_OPTIONS:
                self.status_combo.addItem(s.replace("_"," ").title(), s)
                if emp.status == s:
                    self.status_combo.setCurrentIndex(self.status_combo.count() - 1)
            oc.addWidget(self.status_combo)
            right.addWidget(org_card)

            save_btn = QPushButton("Save Changes")
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.setFixedHeight(44)
            save_btn.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #1d4ed8; }")
            save_btn.clicked.connect(self._save)
            right.addWidget(save_btn)
            cl.addLayout(right, 2)
            self.scroll.setWidget(content)
        finally:
            session.close()

    def _small_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        return l

    def _form_card(self, title, fields):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        layout.addWidget(t_lbl)
        grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        for i, (key, label, val) in enumerate(fields):
            col = col1 if i % 2 == 0 else col2
            col.addWidget(self._small_lbl(label))
            widget = QLineEdit(val)
            widget.setStyleSheet(INPUT_STYLE)
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

    def _save(self):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=self.employee_db_id).first()
            before = json.dumps({"position": emp.position, "status": emp.status, "base_salary": emp.base_salary})

            if self._get("position"): emp.position = self._get("position")
            emp.work_email = self._get("work_email") or emp.work_email
            emp.work_phone = self._get("work_phone") or emp.work_phone
            salary_raw = self._get("base_salary")
            if salary_raw:
                try:
                    emp.base_salary = float(salary_raw)
                except ValueError:
                    QMessageBox.warning(self, t("warning"), "Base salary must be a number.")
                    return

            emp.org_unit_id   = self.org_combo.currentData()
            emp.reports_to_id = self.manager_combo.currentData()
            emp.title_id      = self.title_combo.currentData()
            emp.status        = self.status_combo.currentData()

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
            QMessageBox.information(self, t("success"), f"{emp.full_name} updated successfully.")
            self.on_back()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


class EmployeeProfileView(QWidget):
    def __init__(self, user, on_back, on_edit):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.on_edit = on_edit
        self.employee_db_id = None
        self.setStyleSheet("background: #f9fafb;")
        self._build_shell()

    def _build_shell(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        self.header = QFrame()
        self.header.setFixedHeight(72)
        self.header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("  Back to Employees")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))
        back_btn.setIconSize(QSize(12, 12))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; font-weight: 600; } QPushButton:hover { text-decoration: underline; }")
        back_btn.clicked.connect(self.on_back)
        self.header_title = QLabel("Employee Profile")
        self.header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827; margin-left: 12px;")
        h.addWidget(back_btn)
        h.addWidget(self.header_title)
        h.addStretch()
        edit_btn = QPushButton("Edit Employee")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedHeight(34)
        edit_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; } QPushButton:hover { background: #111827; }")
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
            content.setStyleSheet("background: #f9fafb;")
            cl = QVBoxLayout(content)
            cl.setContentsMargins(28, 24, 28, 28)
            cl.setSpacing(16)

            # Profile header card
            profile_card = QFrame()
            profile_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
            pc = QHBoxLayout(profile_card)
            pc.setContentsMargins(24, 20, 24, 20)
            pc.setSpacing(20)

            initials = (emp.first_name[0] + emp.last_name[0]).upper()
            avatar = QLabel(initials)
            avatar.setFixedSize(72, 72)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet("background: #2563eb; color: white; border-radius: 36px; font-size: 26px; font-weight: bold;")
            pc.addWidget(avatar)

            info = QVBoxLayout()
            info.setSpacing(4)
            name_row = QHBoxLayout()
            name_lbl = QLabel(emp.full_name)
            name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827; background: transparent;")
            name_row.addWidget(name_lbl)
            STATUS_COLORS = {"active": ("#dcfce7","#166534"), "inactive": ("#f3f4f6","#374151"), "on_leave": ("#fef9c3","#854d0e")}
            sbg, sfg = STATUS_COLORS.get(emp.status, ("#f3f4f6","#374151"))
            sb = QLabel(emp.status.replace("_"," ").title())
            sb.setStyleSheet(f"background: {sbg}; color: {sfg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(sb)
            lb = QLabel(emp.title.name if emp.title else "—")
            lb.setStyleSheet("background: #eff6ff; color: #2563eb; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(lb)
            name_row.addStretch()
            info.addLayout(name_row)
            pos_lbl = QLabel(f"{emp.position}  ·  {emp.org_unit.name if emp.org_unit else '—'}")
            pos_lbl.setStyleSheet("font-size: 13px; color: #6b7280; background: transparent;")
            info.addWidget(pos_lbl)
            dr = QHBoxLayout()
            for icon, val in [("✉", emp.work_email or "—"), ("📅", str(emp.join_date.date()) if emp.join_date else "—"), ("🎓", emp.degree), ("💰", f"€{emp.base_salary:,.2f}")]:
                l = QLabel(f"{icon} {val}")
                l.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent; margin-right: 16px;")
                dr.addWidget(l)
            dr.addStretch()
            info.addLayout(dr)
            pc.addLayout(info)
            cl.addWidget(profile_card)

            cols = QHBoxLayout()
            cols.setSpacing(16)

            emp_card = self._info_card("Employment Information", [
                (t("employee_id"), emp.employee_id),
                (t("department"),  emp.org_unit.name if emp.org_unit else "—"),
                (t("position"),    emp.position),
                (t("level"),       emp.title.name if emp.title else "—"),
                (t("base_salary"), f"€{emp.base_salary:,.2f}"),
                (t("reports_to"),  emp.reports_to.full_name if emp.reports_to else "—"),
                (t("join_date"),   str(emp.join_date.date()) if emp.join_date else "—"),
            ])
            cols.addWidget(emp_card)

            race_card = QFrame()
            race_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
            rc = QVBoxLayout(race_card)
            rc.setContentsMargins(20, 16, 20, 16)
            rc.setSpacing(10)
            rc.addWidget(self._info_title("Promotion Race Status"))

            if race["has_next_level"]:
                pct = race["progress_pct"]
                bar_bg = QFrame()
                bar_bg.setFixedHeight(10)
                bar_bg.setStyleSheet("background: #e5e7eb; border-radius: 5px;")
                bar_fill = QFrame(bar_bg)
                bar_fill.setFixedHeight(10)
                bar_fill.setStyleSheet(f"background: {'#10b981' if pct >= 100 else '#2563eb'}; border-radius: 5px;")
                bar_fill.setFixedWidth(max(10, int(pct / 100 * 300)))
                rc.addWidget(bar_bg)
                el = QLabel("✅ Eligible for promotion!" if race["eligible"] else f"⏱ {race['months_remaining']} months remaining")
                el.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {'#10b981' if race['eligible'] else '#2563eb'}; background: transparent;")
                rc.addWidget(el)
                for label, val in [
                    ("Base track duration",   f"{race['base_months']} months"),
                    ("Months elapsed",         f"{race['months_elapsed']} months"),
                    ("Commendation reduction", f"−{race['commendation_reduction']} months"),
                    ("Sanction addition",      f"+{race['sanction_addition']} months"),
                ]:
                    row = QHBoxLayout()
                    k = QLabel(label); k.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
                    v = QLabel(str(val)); v.setStyleSheet("font-size: 12px; font-weight: bold; color: #111827; background: transparent;")
                    row.addWidget(k); row.addStretch(); row.addWidget(v)
                    rc.addLayout(row)
            else:
                rc.addWidget(QLabel("No further promotion track defined."))
            rc.addStretch()
            cols.addWidget(race_card)
            cl.addLayout(cols)

            if self.user.role == "admin":
                cl.addWidget(self._info_card("Personal Information (Admin Only)", [
                    (t("personal_email"), emp.personal_email or "—"),
                    (t("phone"),          emp.phone or "—"),
                    (t("date_of_birth"),  str(emp.date_of_birth.date()) if emp.date_of_birth else "—"),
                    (t("address"),        emp.address or "—"),
                ], badge="Admin Only"))

            cl.addStretch()
            self.scroll.setWidget(content)
            self.header_title.setText(emp.full_name)
        finally:
            session.close()

    def _info_title(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        return l

    def _info_card(self, title, rows, badge=None):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        tr = QHBoxLayout()
        tr.addWidget(self._info_title(title))
        if badge:
            b = QLabel(badge)
            b.setStyleSheet("background: #fef2f2; color: #991b1b; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            tr.addWidget(b)
        tr.addStretch()
        layout.addLayout(tr)
        for key, val in rows:
            row = QHBoxLayout()
            k = QLabel(key); k.setFixedWidth(140); k.setStyleSheet("font-size: 13px; color: #6b7280; background: transparent;")
            v = QLabel(str(val)); v.setStyleSheet("font-size: 13px; color: #111827; font-weight: bold; background: transparent;"); v.setWordWrap(True)
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
        self.setStyleSheet("QWidget { background: #f9fafb; font-family: 'Segoe UI'; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: #f9fafb;")
        layout.addWidget(self.scroll)

    def load(self, employee_db_id):
        self.employee_db_id = employee_db_id
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_db_id).first()
            if not emp:
                return
            race = calculate_months_remaining(emp, session)
            content = QWidget()
            content.setStyleSheet("background: #f9fafb;")
            page = QVBoxLayout(content)
            page.setContentsMargins(28, 28, 28, 28)
            page.setSpacing(18)

            back = QPushButton("  Back to Employees")
            back.setIcon(qta.icon("fa5s.arrow-left", color="#111827"))
            back.setIconSize(QSize(12, 12))
            back.setCursor(Qt.PointingHandCursor)
            back.setFixedWidth(170)
            back.setStyleSheet("QPushButton { background: transparent; color: #111827; border: none; font-size: 13px; font-weight: 600; text-align: left; } QPushButton:hover { color: #2563eb; }")
            back.clicked.connect(self.on_back)
            page.addWidget(back)
            page.addWidget(self._profile_header(emp))

            tabs = QTabWidget()
            tabs.setStyleSheet("""
                QTabWidget::pane { border: none; background: #f9fafb; margin-top: 14px; }
                QTabBar::tab { background: #e5e7eb; color: #111827; padding: 8px 14px; border: none; font-size: 12px; font-weight: 600; }
                QTabBar::tab:first { border-top-left-radius: 9px; border-bottom-left-radius: 9px; }
                QTabBar::tab:last { border-top-right-radius: 9px; border-bottom-right-radius: 9px; }
                QTabBar::tab:selected { background: white; color: #030213; }
            """)
            tabs.addTab(self._details_tab(emp), "Personal Details")
            tabs.addTab(self._promotion_tab(emp, race), "Promotion History")
            tabs.addTab(self._commendations_tab(emp), "Commendations")
            tabs.addTab(self._sanctions_tab(emp), "Sanctions")
            page.addWidget(tabs)
            page.addStretch()
            self.scroll.setWidget(content)
        finally:
            session.close()

    def _profile_header(self, emp):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        initials = (emp.first_name[:1] + emp.last_name[:1]).upper()
        avatar = QLabel(initials)
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background: #2563eb; color: white; border-radius: 40px; font-size: 26px; font-weight: bold;")
        layout.addWidget(avatar)
        info = QVBoxLayout()
        info.setSpacing(6)
        name_row = QHBoxLayout()
        name = QLabel(emp.full_name)
        name.setStyleSheet("font-size: 24px; font-weight: 800; color: #111827; background: transparent;")
        name_row.addWidget(name)
        name_row.addWidget(self._badge(emp.status.replace("_", " ").title(), "#dcfce7", "#166534"))
        name_row.addWidget(self._badge(emp.title.name if emp.title else "-", "#dbeafe", "#1e40af"))
        name_row.addStretch()
        info.addLayout(name_row)
        pos = QLabel(emp.position)
        pos.setStyleSheet("font-size: 14px; color: #6b7280; background: transparent;")
        info.addWidget(pos)
        meta = QHBoxLayout()
        for icon_name, value in [
            ("fa5s.envelope", emp.work_email or "-"),
            ("fa5s.phone", emp.work_phone or emp.phone or "-"),
            ("fa5s.map-marker-alt", emp.address or "-"),
            ("fa5s.calendar-alt", f"Joined {emp.join_date.date()}" if emp.join_date else "-"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(5)
            ico = QLabel()
            ico.setPixmap(qta.icon(icon_name, color="#6b7280").pixmap(13, 13))
            lbl = QLabel(str(value))
            lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
            row.addWidget(ico)
            row.addWidget(lbl)
            meta.addLayout(row)
            meta.addSpacing(16)
        meta.addStretch()
        info.addLayout(meta)
        layout.addLayout(info, 1)
        edit = QPushButton("  Edit Profile")
        edit.setIcon(qta.icon("fa5s.edit", color="white"))
        edit.setIconSize(QSize(13, 13))
        edit.setCursor(Qt.PointingHandCursor)
        edit.setFixedHeight(36)
        edit.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; padding: 0 14px; } QPushButton:hover { background: #111827; }")
        edit.clicked.connect(lambda: self.on_edit(self.employee_db_id) if self.employee_db_id else None)
        layout.addWidget(edit, alignment=Qt.AlignTop)
        return card

    def _details_tab(self, emp):
        page = QWidget()
        page.setStyleSheet("background: #f9fafb;")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._info_card("Employment Information", [
            (t("employee_id"), emp.employee_id),
            (t("department"), emp.org_unit.name if emp.org_unit else "-"),
            (t("position"), emp.position),
            (t("level"), emp.title.name if emp.title else "-"),
            (t("base_salary"), f"EUR {emp.base_salary:,.2f}"),
            (t("reports_to"), emp.reports_to.full_name if emp.reports_to else "-"),
            (t("join_date"), str(emp.join_date.date()) if emp.join_date else "-"),
        ]))
        if self.user.role == "admin":
            layout.addWidget(self._info_card("Personal Information (Admin Only)", [
                ("Full Name", emp.full_name),
                (t("personal_email"), emp.personal_email or "-"),
                (t("phone"), emp.phone or "-"),
                (t("address"), emp.address or "-"),
                (t("degree"), emp.degree),
                (t("base_salary"), f"EUR {emp.base_salary:,.2f}"),
            ], badge="Admin Only"))
        layout.addStretch()
        return page

    def _promotion_tab(self, emp, race):
        page = QWidget()
        page.setStyleSheet("background: #f9fafb;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        card = self._list_card("Promotion History")
        body = card.layout()
        for promo in reversed(list(emp.promotions)):
            body.addWidget(self._event_row("fa5s.chart-line", "#10b981", f"Promoted from {promo.from_title.name} to {promo.to_title.name}", promo.notes or promo.basis.replace("_", " ").title(), promo.promoted_at.strftime("%Y-%m-%d") if promo.promoted_at else "-"))
        body.addWidget(self._event_row("fa5s.chart-line", "#10b981", "Initial Position", f"Initial hire ({emp.degree} degree)", emp.join_date.strftime("%Y-%m-%d") if emp.join_date else "-"))
        if race["has_next_level"]:
            body.addWidget(self._event_row("fa5s.clock", "#2563eb", "Current Promotion Race", f"{race['progress_pct']}% complete, {race['months_remaining']} month(s) remaining", "Live"))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _commendations_tab(self, emp):
        page = QWidget()
        page.setStyleSheet("background: #f9fafb;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        card = self._list_card("Commendations")
        body = card.layout()
        if emp.commendations:
            for comm in sorted(emp.commendations, key=lambda c: c.issued_at or datetime.min, reverse=True):
                body.addWidget(self._event_row("fa5s.award", "#f59e0b", f"{comm.title} ({comm.commendation_ref})", f"Category {comm.category} - {abs(comm.months_impact)} month(s) faster", comm.issued_at.strftime("%Y-%m-%d") if comm.issued_at else "-"))
        else:
            body.addWidget(self._empty_row("No commendations recorded for this employee."))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _sanctions_tab(self, emp):
        page = QWidget()
        page.setStyleSheet("background: #f9fafb;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        card = self._list_card("Sanctions")
        body = card.layout()
        if emp.sanctions:
            for sanction in sorted(emp.sanctions, key=lambda s: s.issued_at or datetime.min, reverse=True):
                status = "Resolved" if sanction.is_resolved else "Active"
                resolved = f", resolved {sanction.resolved_at:%Y-%m-%d}" if sanction.resolved_at else ""
                body.addWidget(self._event_row("fa5s.exclamation-triangle", "#ef4444", f"{sanction.sanction_type.replace('_', ' ').title()} ({sanction.sanction_ref})", f"{sanction.reason} - +{sanction.delay_months} month(s), {status}{resolved}", sanction.issued_at.strftime("%Y-%m-%d") if sanction.issued_at else "-"))
        else:
            body.addWidget(self._empty_row("No sanctions recorded for this employee."))
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _info_title(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 15px; font-weight: 700; color: #111827; background: transparent;")
        return label

    def _badge(self, text, bg, fg):
        label = QLabel(text)
        label.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 6px; padding: 2px 9px; font-size: 11px; font-weight: 700;")
        return label

    def _info_card(self, title, rows, badge=None):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(self._info_title(title))
        if badge:
            header.addWidget(self._badge(badge, "#fee2e2", "#991b1b"))
        header.addStretch()
        layout.addLayout(header)
        for key, val in rows:
            field = QVBoxLayout()
            field.setSpacing(4)
            k = QLabel(key)
            k.setStyleSheet("font-size: 12px; font-weight: 700; color: #111827; background: transparent;")
            v = QLabel(str(val))
            v.setWordWrap(True)
            v.setStyleSheet("font-size: 12px; color: #6b7280; background: #f9fafb; border-radius: 7px; padding: 8px 10px;")
            field.addWidget(k)
            field.addWidget(v)
            layout.addLayout(field)
        return card

    def _list_card(self, title):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(self._info_title(title))
        return card

    def _event_row(self, icon_name, color, title, subtitle, date_text):
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #f3f4f6;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: {color}18; border-radius: 8px;")
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(15, 15))
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #111827; background: transparent;")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        text_col.addWidget(title_lbl)
        text_col.addWidget(sub_lbl)
        date = QLabel(date_text)
        date.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        layout.addWidget(icon)
        layout.addLayout(text_col, 1)
        layout.addWidget(date, alignment=Qt.AlignTop)
        return row

    def _empty_row(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 24px; background: transparent;")
        return label
