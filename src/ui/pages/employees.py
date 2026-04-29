"""
Employees Page - Fixed version
Fixes:
- Employee Edit functionality added
- Org unit graceful handling when none exist
- Status combo on add/edit forms
- Edit button wired up properly
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget,
    QTextEdit, QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, generate_employee_id, log_action,
    degree_to_title_name, calculate_months_remaining
)
from src.database.models import Employee, Title, OrgUnit
from datetime import datetime
import json

DEGREE_OPTIONS = ["BSc", "MSc", "PhD", "Other"]
STATUS_OPTIONS = ["active", "inactive", "on_leave"]
COMBO_STYLE = "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; background: #f9fafb; color: #111827; min-height: 36px; } QComboBox:focus { border-color: #2563eb; }"
INPUT_STYLE = "QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; background: #f9fafb; color: #111827; min-height: 36px; } QLineEdit:focus { border-color: #2563eb; background: white; }"


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
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def set_edit_callback(self, cb):
        self._on_edit_cb = cb

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        title = QLabel(t("employees_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        h.addWidget(title)
        h.addStretch()
        add_btn = QPushButton("+ " + t("add_employee"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; } QPushButton:hover { background: #111827; }")
        add_btn.clicked.connect(self.on_add)
        h.addWidget(add_btn)
        layout.addWidget(header)

        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet("background: white; border-bottom: 1px solid #f0f0f0;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(28, 0, 28, 0)
        bl.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_employees"))
        self.search_input.setFixedHeight(34)
        self.search_input.setStyleSheet("QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; background: #f9fafb; color: #111827; } QLineEdit:focus { border-color: #2563eb; background: white; }")
        self.search_input.textChanged.connect(self._apply_filter)
        bl.addWidget(self.search_input, 3)

        self.dept_filter = QComboBox()
        self.dept_filter.setFixedHeight(34)
        self.dept_filter.setStyleSheet(COMBO_STYLE)
        self.dept_filter.addItem("All Departments", None)
        self.dept_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.dept_filter, 2)

        self.status_filter = QComboBox()
        self.status_filter.setFixedHeight(34)
        self.status_filter.setStyleSheet(COMBO_STYLE)
        self.status_filter.addItem("All Status", None)
        for s in STATUS_OPTIONS:
            self.status_filter.addItem(s.replace("_", " ").title(), s)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.status_filter, 1)
        layout.addWidget(bar)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size: 12px; color: #9ca3af; padding: 6px 28px;")
        layout.addWidget(self.count_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            t("employee_id"), t("full_name"), t("department"),
            t("position"), t("level"), t("degree"), t("status"), t("actions")
        ])
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: none; gridline-color: #f3f4f6; font-size: 13px; }
            QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; }
            QTableWidget::item:selected { background: #eff6ff; color: #111827; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            emps = session.query(Employee).all()
            self.all_employees = [{
                "id": e.id, "employee_id": e.employee_id, "full_name": e.full_name,
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
            (not search or search in e["full_name"].lower() or search in e["employee_id"].lower()) and
            (not dept   or e["dept"] == dept) and
            (not status or e["status"] == status)
        ]
        self.count_lbl.setText(f"Showing {len(filtered)} of {len(self.all_employees)} employees")
        self._populate_table(filtered)

    def _populate_table(self, employees):
        self.table.setRowCount(len(employees))
        STATUS_COLORS = {"active": ("#dcfce7","#166534"), "inactive": ("#f3f4f6","#374151"), "on_leave": ("#fef9c3","#854d0e")}
        LEVEL_COLORS  = {"L7": ("#dbeafe","#1e40af"), "L6": ("#dcfce7","#166534"), "L5": ("#fef9c3","#854d0e"), "L4": ("#f3e8ff","#6b21a8"), "L3": ("#fce7f3","#9d174d")}

        for row, emp in enumerate(employees):
            self.table.setRowHeight(row, 50)
            for col, val in enumerate([emp["employee_id"], emp["full_name"], emp["dept"], emp["position"], emp["level"], emp["degree"], emp["status"]]):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, emp["id"])
                if col == 4:
                    bg, fg = LEVEL_COLORS.get(val, ("#f3f4f6","#374151"))
                    item.setBackground(QColor(bg)); item.setForeground(QColor(fg))
                elif col == 6:
                    bg, fg = STATUS_COLORS.get(val, ("#f3f4f6","#374151"))
                    item.setBackground(QColor(bg)); item.setForeground(QColor(fg))
                    item.setText(val.replace("_"," ").title())
                self.table.setItem(row, col, item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 6, 4, 6)
            btn_layout.setSpacing(4)

            view_btn = QPushButton("View")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("QPushButton { background: #eff6ff; color: #2563eb; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; padding: 4px 10px; } QPushButton:hover { background: #dbeafe; }")
            view_btn.clicked.connect(lambda _, eid=emp["id"]: self.on_profile(eid))

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; padding: 4px 10px; } QPushButton:hover { background: #e5e7eb; }")
            edit_btn.clicked.connect(lambda _, eid=emp["id"]: self._do_edit(eid))

            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(edit_btn)
            self.table.setCellWidget(row, 7, btn_widget)

    def _do_edit(self, emp_id):
        p = self.parent()
        while p and not isinstance(p, EmployeesPage):
            p = p.parent()
        if p:
            p._show_edit(emp_id)


class AddEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.fields = {}
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.reset()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; } QPushButton:hover { text-decoration: underline; }")
        back_btn.clicked.connect(self.on_back)
        title = QLabel(t("add_employee"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827; margin-left: 12px;")
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
        cl.setContentsMargins(28, 24, 28, 28)
        cl.setSpacing(20)
        cl.setAlignment(Qt.AlignTop)

        left = QVBoxLayout()
        left.setSpacing(16)
        left.addWidget(self._section_card("Personal Information", [
            ("first_name",    t("first_name"),    "text"),
            ("last_name",     t("last_name"),      "text"),
            ("date_of_birth", t("date_of_birth"),  "date"),
            ("personal_email",t("personal_email"), "text"),
            ("phone",         t("phone"),          "text"),
            ("address",       t("address"),        "textarea"),
        ]))

        deg_card = QFrame()
        deg_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        dcl = QVBoxLayout(deg_card)
        dcl.setContentsMargins(20, 16, 20, 16)
        dcl.setSpacing(12)
        dcl.addWidget(self._lbl("Education & Level Assignment", bold=True, size=14))
        row = QHBoxLayout()
        row.setSpacing(12)
        dl = QVBoxLayout()
        dl.addWidget(self._lbl(t("degree") + " *"))
        self.degree_combo = QComboBox()
        self.degree_combo.setFixedHeight(36)
        self.degree_combo.setStyleSheet(COMBO_STYLE)
        for d in DEGREE_OPTIONS:
            self.degree_combo.addItem(d)
        self.degree_combo.currentTextChanged.connect(lambda deg: self.level_display.setText(degree_to_title_name(deg)))
        dl.addWidget(self.degree_combo)
        row.addLayout(dl)
        ll = QVBoxLayout()
        ll.addWidget(self._lbl(t("auto_level")))
        self.level_display = QLabel("L7")
        self.level_display.setFixedHeight(36)
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
        org_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        oc = QVBoxLayout(org_card)
        oc.setContentsMargins(20, 16, 20, 16)
        oc.setSpacing(8)
        oc.addWidget(self._lbl("Organization", bold=True, size=14))
        oc.addWidget(self._lbl("Org Unit"))
        self.org_combo = QComboBox()
        self.org_combo.setFixedHeight(36)
        self.org_combo.setStyleSheet(COMBO_STYLE)
        oc.addWidget(self.org_combo)
        oc.addWidget(self._lbl(t("reports_to")))
        self.manager_combo = QComboBox()
        self.manager_combo.setFixedHeight(36)
        self.manager_combo.setStyleSheet(COMBO_STYLE)
        oc.addWidget(self.manager_combo)
        oc.addWidget(self._lbl(t("status")))
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(36)
        self.status_combo.setStyleSheet(COMBO_STYLE)
        for s in STATUS_OPTIONS:
            self.status_combo.addItem(s.replace("_"," ").title(), s)
        oc.addWidget(self.status_combo)
        right.addWidget(org_card)

        info_card = QFrame()
        info_card.setStyleSheet("background: #eff6ff; border-radius: 12px; border: 1px solid #bfdbfe;")
        ic = QVBoxLayout(info_card)
        ic.setContentsMargins(16, 14, 16, 14)
        ic.setSpacing(6)
        ic.addWidget(self._lbl("Salary Guidelines", bold=True, color="#1e40af"))
        for line in ["L7 (BSc): €2,000 – €2,800", "L6 (MSc): €2,800 – €3,500", "L5 (PhD): €3,500 – €4,500"]:
            l = QLabel(line)
            l.setStyleSheet("font-size: 12px; color: #4338ca; background: transparent;")
            ic.addWidget(l)
        right.addWidget(info_card)

        save_btn = QPushButton("Save Employee")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #1d4ed8; }")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)
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
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(self._lbl(title, bold=True, size=14, color="#111827"))
        grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        for i, (key, label, ftype) in enumerate(fields):
            col = col1 if i % 2 == 0 else col2
            col.addWidget(self._lbl(label + (" *" if key in ["first_name","last_name","position","join_date"] else "")))
            if ftype == "textarea":
                widget = QTextEdit()
                widget.setFixedHeight(72)
                widget.setStyleSheet("QTextEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px; font-size: 13px; background: #f9fafb; color: #111827; } QTextEdit:focus { border-color: #2563eb; background: white; }")
            elif ftype == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setFixedHeight(36)
                widget.setDate(QDate.currentDate())
                widget.setStyleSheet("QDateEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px; font-size: 13px; background: #f9fafb; color: #111827; } QDateEdit:focus { border-color: #2563eb; }")
            else:
                widget = QLineEdit()
                widget.setFixedHeight(36)
                widget.setStyleSheet(INPUT_STYLE)
            col.addWidget(widget)
            col.addSpacing(2)
            self.fields[key] = widget
        grid.addLayout(col1)
        grid.addSpacing(12)
        grid.addLayout(col2)
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
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; } QPushButton:hover { text-decoration: underline; }")
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
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #2563eb; border: none; font-size: 13px; } QPushButton:hover { text-decoration: underline; }")
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