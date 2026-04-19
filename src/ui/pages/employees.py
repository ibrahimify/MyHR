"""
Employees Page
- Employee list with search + filter
- Add Employee form (degree → level auto-assign)
- View/Edit Employee profile
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QFormLayout,
    QTextEdit, QMessageBox, QDateEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, generate_employee_id, log_action,
    degree_to_title_name, calculate_months_remaining
)
from src.database.models import Employee, Title, OrgUnit, SystemUser
from datetime import datetime


DEGREE_OPTIONS = ["BSc", "MSc", "PhD", "Other"]
STATUS_OPTIONS = ["active", "inactive", "on_leave"]


class EmployeesPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.list_page = EmployeeListView(self.user, self._show_add, self._show_profile)
        self.add_page  = AddEmployeeView(self.user, self._show_list)
        self.profile_page = EmployeeProfileView(self.user, self._show_list)

        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.add_page)
        self.stack.addWidget(self.profile_page)
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


# ── Employee List ─────────────────────────────────────────────────────────────
class EmployeeListView(QWidget):
    def __init__(self, user, on_add, on_profile):
        super().__init__()
        self.user = user
        self.on_add = on_add
        self.on_profile = on_profile
        self.all_employees = []
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

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
        title = QLabel(t("employees_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
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

        # Search + filter bar
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
        self.dept_filter.setStyleSheet("QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; background: #f9fafb; color: #111827; }")
        self.dept_filter.addItem("All Departments", None)
        self.dept_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.dept_filter, 2)

        self.status_filter = QComboBox()
        self.status_filter.setFixedHeight(34)
        self.status_filter.setStyleSheet(self.dept_filter.styleSheet())
        self.status_filter.addItem("All Status", None)
        for s in STATUS_OPTIONS:
            self.status_filter.addItem(s.replace("_", " ").title(), s)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        bl.addWidget(self.status_filter, 1)

        layout.addWidget(bar)

        # Count label
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size: 12px; color: #9ca3af; padding: 6px 28px;")
        layout.addWidget(self.count_lbl)

        # Table
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
        self.table.setColumnWidth(7, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            emps = session.query(Employee).all()
            self.all_employees = [{
                "id": e.id,
                "employee_id": e.employee_id,
                "full_name": e.full_name,
                "dept": e.org_unit.name if e.org_unit else "—",
                "position": e.position,
                "level": e.title.name if e.title else "—",
                "degree": e.degree,
                "status": e.status,
            } for e in emps]

            # Populate dept filter
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
        STATUS_COLORS = {
            "active":   ("#dcfce7", "#166534"),
            "inactive": ("#f3f4f6", "#374151"),
            "on_leave": ("#fef9c3", "#854d0e"),
        }
        LEVEL_COLORS = {
            "L7": ("#dbeafe", "#1e40af"),
            "L6": ("#dcfce7", "#166534"),
            "L5": ("#fef9c3", "#854d0e"),
            "L4": ("#f3e8ff", "#6b21a8"),
            "L3": ("#fce7f3", "#9d174d"),
        }

        for row, emp in enumerate(employees):
            self.table.setRowHeight(row, 48)

            for col, val in enumerate([
                emp["employee_id"], emp["full_name"], emp["dept"],
                emp["position"], emp["level"], emp["degree"], emp["status"]
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, emp["id"])

                if col == 4:  # Level badge color
                    bg, fg = LEVEL_COLORS.get(val, ("#f3f4f6", "#374151"))
                    item.setBackground(QColor(bg))
                    item.setForeground(QColor(fg))
                elif col == 6:  # Status badge color
                    bg, fg = STATUS_COLORS.get(val, ("#f3f4f6", "#374151"))
                    item.setBackground(QColor(bg))
                    item.setForeground(QColor(fg))
                    item.setText(val.replace("_", " ").title())

                self.table.setItem(row, col, item)

            # View button
            view_btn = QPushButton("View")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("QPushButton { background: #eff6ff; color: #2563eb; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; margin: 8px; } QPushButton:hover { background: #dbeafe; }")
            view_btn.clicked.connect(lambda _, eid=emp["id"]: self.on_profile(eid))
            self.table.setCellWidget(row, 7, view_btn)


# ── Add Employee ──────────────────────────────────────────────────────────────
class AddEmployeeView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.reset()

    def _build(self):
        self.fields = {}  # initialize before _section_card writes to it

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
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

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(28, 24, 28, 28)
        cl.setSpacing(20)
        cl.setAlignment(Qt.AlignTop)

        # ── Left: main form ───────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(16)

        # Personal info card
        left.addWidget(self._section_card("Personal Information", [
            ("first_name",     t("first_name"),     "text"),
            ("last_name",      t("last_name"),       "text"),
            ("date_of_birth",  t("date_of_birth"),   "date"),
            ("personal_email", t("personal_email"),  "text"),
            ("phone",          t("phone"),           "text"),
            ("address",        t("address"),         "textarea"),
        ]))

        # Degree + level card
        degree_card = QFrame()
        degree_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        dc_layout = QVBoxLayout(degree_card)
        dc_layout.setContentsMargins(20, 16, 20, 16)
        dc_layout.setSpacing(12)

        dc_title = QLabel("Education & Level Assignment")
        dc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        dc_layout.addWidget(dc_title)

        row = QHBoxLayout()
        row.setSpacing(12)

        dl = QVBoxLayout()
        deg_lbl = QLabel(t("degree") + " *")
        deg_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.degree_combo = QComboBox()
        self.degree_combo.setFixedHeight(36)
        self.degree_combo.setStyleSheet(self._combo_style())
        for d in DEGREE_OPTIONS:
            self.degree_combo.addItem(d)
        self.degree_combo.currentTextChanged.connect(self._on_degree_change)
        dl.addWidget(deg_lbl)
        dl.addWidget(self.degree_combo)
        row.addLayout(dl)

        ll = QVBoxLayout()
        lv_lbl = QLabel(t("auto_level"))
        lv_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.level_display = QLabel("L7")
        self.level_display.setFixedHeight(36)
        self.level_display.setAlignment(Qt.AlignCenter)
        self.level_display.setStyleSheet("background: #eff6ff; color: #2563eb; border-radius: 8px; font-size: 16px; font-weight: bold; border: 1px solid #bfdbfe;")
        ll.addWidget(lv_lbl)
        ll.addWidget(self.level_display)
        row.addLayout(ll)

        dc_layout.addLayout(row)
        hint = QLabel(t("level_rule"))
        hint.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")
        dc_layout.addWidget(hint)
        left.addWidget(degree_card)

        # Employment details
        left.addWidget(self._section_card("Employment Details", [
            ("work_email",  t("work_email"),  "text"),
            ("work_phone",  t("work_phone"),  "text"),
            ("position",    t("position"),    "text"),
            ("join_date",   t("join_date"),   "date"),
            ("base_salary", t("base_salary"), "text"),
        ]))

        cl.addLayout(left, 3)

        # ── Right: sidebar ────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Org unit selector
        org_card = QFrame()
        org_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        oc = QVBoxLayout(org_card)
        oc.setContentsMargins(20, 16, 20, 16)
        oc.setSpacing(10)
        oc_title = QLabel("Organization")
        oc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        oc.addWidget(oc_title)

        org_lbl = QLabel("Org Unit")
        org_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.org_combo = QComboBox()
        self.org_combo.setFixedHeight(36)
        self.org_combo.setStyleSheet(self._combo_style())
        oc.addWidget(org_lbl)
        oc.addWidget(self.org_combo)

        manager_lbl = QLabel(t("reports_to"))
        manager_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
        self.manager_combo = QComboBox()
        self.manager_combo.setFixedHeight(36)
        self.manager_combo.setStyleSheet(self._combo_style())
        oc.addWidget(manager_lbl)
        oc.addWidget(self.manager_combo)
        right.addWidget(org_card)

        # Salary guideline info
        info_card = QFrame()
        info_card.setStyleSheet("background: #eff6ff; border-radius: 12px; border: 1px solid #bfdbfe;")
        ic = QVBoxLayout(info_card)
        ic.setContentsMargins(16, 14, 16, 14)
        ic.setSpacing(6)
        ic_title = QLabel("Salary Guidelines")
        ic_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; background: transparent;")
        ic.addWidget(ic_title)
        for line in ["L7 (BSc): €2,000 – €2,800", "L6 (MSc): €2,800 – €3,500", "L5 (PhD): €3,500 – €4,500"]:
            lbl = QLabel(line)
            lbl.setStyleSheet("font-size: 12px; color: #4338ca; background: transparent;")
            ic.addWidget(lbl)
        right.addWidget(info_card)

        # Save button
        save_btn = QPushButton("💾  " + t("save") + " Employee")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #111827; }")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)

        cl.addLayout(right, 2)
        scroll.setWidget(content)
        layout.addWidget(scroll)


    def _section_card(self, title, fields):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        layout.addWidget(title_lbl)

        grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()

        for i, (key, label, ftype) in enumerate(fields):
            col = col1 if i % 2 == 0 else col2
            lbl = QLabel(label + (" *" if key in ["first_name","last_name","position","join_date","degree"] else ""))
            lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b7280; background: transparent;")
            col.addWidget(lbl)

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
                widget.setStyleSheet("QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; background: #f9fafb; color: #111827; } QLineEdit:focus { border-color: #2563eb; background: white; }")

            col.addWidget(widget)
            col.addSpacing(2)
            self.fields[key] = widget

        grid.addLayout(col1)
        grid.addSpacing(12)
        grid.addLayout(col2)
        layout.addLayout(grid)
        return card

    def _on_degree_change(self, degree):
        level = degree_to_title_name(degree)
        self.level_display.setText(level)

    def reset(self):
        for key, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
        self.degree_combo.setCurrentIndex(0)
        self.level_display.setText("L7")
        self._load_org_units()
        self._load_managers()

    def _load_org_units(self):
        self.org_combo.clear()
        self.org_combo.addItem("— None —", None)
        session = get_session()
        try:
            units = session.query(OrgUnit).all()
            for u in units:
                self.org_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
        finally:
            session.close()

    def _load_managers(self):
        self.manager_combo.clear()
        self.manager_combo.addItem("— None —", None)
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            for e in emps:
                self.manager_combo.addItem(f"{e.employee_id} — {e.full_name}", e.id)
        finally:
            session.close()

    def _get_field_value(self, key):
        w = self.fields.get(key)
        if isinstance(w, QLineEdit):
            return w.text().strip()
        elif isinstance(w, QTextEdit):
            return w.toPlainText().strip()
        elif isinstance(w, QDateEdit):
            return w.date().toPython()
        return None

    def _save(self):
        # Validate required fields
        required = {"first_name": t("first_name"), "last_name": t("last_name"),
                    "position": t("position")}
        for key, label in required.items():
            if not self._get_field_value(key):
                QMessageBox.warning(self, t("warning"), f"{label} is required.")
                return

        session = get_session()
        try:
            degree = self.degree_combo.currentText()
            title_name = degree_to_title_name(degree)
            title = session.query(Title).filter_by(name=title_name).first()
            if not title:
                QMessageBox.critical(self, t("error"), f"Title {title_name} not found in DB.")
                return

            emp_id = generate_employee_id(session)
            join_dt = self._get_field_value("join_date")
            dob_dt  = self._get_field_value("date_of_birth")

            employee = Employee(
                employee_id    = emp_id,
                first_name     = self._get_field_value("first_name"),
                last_name      = self._get_field_value("last_name"),
                date_of_birth  = datetime.combine(dob_dt, datetime.min.time()) if dob_dt else None,
                personal_email = self._get_field_value("personal_email"),
                phone          = self._get_field_value("phone"),
                address        = self._get_field_value("address"),
                degree         = degree,
                work_email     = self._get_field_value("work_email"),
                work_phone     = self._get_field_value("work_phone"),
                position       = self._get_field_value("position"),
                join_date      = datetime.combine(join_dt, datetime.min.time()),
                base_salary    = float(self._get_field_value("base_salary") or 0),
                status         = "active",
                title_id       = title.id,
                org_unit_id    = self.org_combo.currentData(),
                reports_to_id  = self.manager_combo.currentData(),
            )
            session.add(employee)
            session.flush()

            log_action(
                session=session,
                performed_by_id=self.user.id,
                action="employee.create",
                target_table="employee",
                target_id=employee.id,
                description=f"New employee added: {employee.full_name} ({emp_id})",
            )
            session.commit()
            QMessageBox.information(self, t("success"), f"Employee {employee.full_name} ({emp_id}) added successfully.")
            self.on_back()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()

    def _combo_style(self):
        return "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px 0 12px; font-size: 13px; background: #f9fafb; color: #111827; } QComboBox:focus { border-color: #2563eb; }"


# ── Employee Profile ──────────────────────────────────────────────────────────
class EmployeeProfileView(QWidget):
    def __init__(self, user, on_back):
        super().__init__()
        self.user = user
        self.on_back = on_back
        self.employee_id = None
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        # Header
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
        self.layout_.addWidget(self.header)

        # Content placeholder
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.layout_.addWidget(self.scroll)

    def load(self, employee_db_id):
        self.employee_id = employee_db_id
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

            # Profile card
            profile_card = QFrame()
            profile_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
            pc = QHBoxLayout(profile_card)
            pc.setContentsMargins(24, 20, 24, 20)
            pc.setSpacing(20)

            # Avatar
            initials = (emp.first_name[0] + emp.last_name[0]).upper()
            avatar = QLabel(initials)
            avatar.setFixedSize(72, 72)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet("background: #2563eb; color: white; border-radius: 36px; font-size: 26px; font-weight: bold;")
            pc.addWidget(avatar)

            # Basic info
            info = QVBoxLayout()
            info.setSpacing(4)

            name_row = QHBoxLayout()
            name_lbl = QLabel(emp.full_name)
            name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827; background: transparent;")
            name_row.addWidget(name_lbl)

            STATUS_COLORS = {"active": ("#dcfce7","#166534"), "inactive": ("#f3f4f6","#374151"), "on_leave": ("#fef9c3","#854d0e")}
            sbg, sfg = STATUS_COLORS.get(emp.status, ("#f3f4f6","#374151"))
            status_badge = QLabel(emp.status.replace("_"," ").title())
            status_badge.setStyleSheet(f"background: {sbg}; color: {sfg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(status_badge)

            level_badge = QLabel(emp.title.name if emp.title else "—")
            level_badge.setStyleSheet("background: #eff6ff; color: #2563eb; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            name_row.addWidget(level_badge)
            name_row.addStretch()
            info.addLayout(name_row)

            pos_lbl = QLabel(f"{emp.position}  ·  {emp.org_unit.name if emp.org_unit else '—'}")
            pos_lbl.setStyleSheet("font-size: 13px; color: #6b7280; background: transparent;")
            info.addWidget(pos_lbl)

            detail_row = QHBoxLayout()
            for icon, val in [("✉", emp.work_email or "—"), ("📅", str(emp.join_date.date()) if emp.join_date else "—"), ("🎓", emp.degree), ("📍", emp.address or "—")]:
                lbl = QLabel(f"{icon} {val}")
                lbl.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent; margin-right: 16px;")
                detail_row.addWidget(lbl)
            detail_row.addStretch()
            info.addLayout(detail_row)
            pc.addLayout(info)
            cl.addWidget(profile_card)

            # Two columns below
            cols = QHBoxLayout()
            cols.setSpacing(16)

            # Left: employment details
            emp_card = self._info_card("Employment Information", [
                (t("employee_id"), emp.employee_id),
                (t("department"), emp.org_unit.name if emp.org_unit else "—"),
                (t("position"), emp.position),
                (t("level"), emp.title.name if emp.title else "—"),
                (t("base_salary"), f"€{emp.base_salary:,.2f}"),
                (t("reports_to"), emp.reports_to.full_name if emp.reports_to else "—"),
                (t("join_date"), str(emp.join_date.date()) if emp.join_date else "—"),
            ])
            cols.addWidget(emp_card)

            # Right: promotion race status
            race_card = QFrame()
            race_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
            rc = QVBoxLayout(race_card)
            rc.setContentsMargins(20, 16, 20, 16)
            rc.setSpacing(10)

            rc_title = QLabel("Promotion Race Status")
            rc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
            rc.addWidget(rc_title)

            if race["has_next_level"]:
                pct = race["progress_pct"]
                # Progress bar
                bar_bg = QFrame()
                bar_bg.setFixedHeight(10)
                bar_bg.setStyleSheet("background: #e5e7eb; border-radius: 5px;")
                bar_fill = QFrame(bar_bg)
                bar_fill.setFixedHeight(10)
                fill_color = "#10b981" if pct >= 100 else "#2563eb"
                bar_fill.setStyleSheet(f"background: {fill_color}; border-radius: 5px;")
                bar_fill.setFixedWidth(max(10, int(pct / 100 * 300)))
                rc.addWidget(bar_bg)

                eligible_lbl = QLabel("✅ Eligible for promotion!" if race["eligible"] else f"⏱ {race['months_remaining']} months remaining")
                eligible_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {'#10b981' if race['eligible'] else '#2563eb'}; background: transparent;")
                rc.addWidget(eligible_lbl)

                for label, val in [
                    ("Base track duration", f"{race['base_months']} months"),
                    ("Months elapsed", f"{race['months_elapsed']} months"),
                    ("Commendation reduction", f"−{race['commendation_reduction']} months"),
                    ("Sanction addition", f"+{race['sanction_addition']} months"),
                ]:
                    row = QHBoxLayout()
                    k = QLabel(label)
                    k.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
                    v = QLabel(str(val))
                    v.setStyleSheet("font-size: 12px; font-weight: bold; color: #111827; background: transparent;")
                    row.addWidget(k)
                    row.addStretch()
                    row.addWidget(v)
                    rc.addLayout(row)
            else:
                lbl = QLabel("No further promotion track defined.")
                lbl.setStyleSheet("font-size: 13px; color: #9ca3af; background: transparent;")
                rc.addWidget(lbl)

            rc.addStretch()
            cols.addWidget(race_card)
            cl.addLayout(cols)

            # Admin-only: personal info card
            if self.user.role == "admin":
                personal_card = self._info_card("Personal Information (Admin Only)", [
                    (t("personal_email"), emp.personal_email or "—"),
                    (t("phone"), emp.phone or "—"),
                    (t("date_of_birth"), str(emp.date_of_birth.date()) if emp.date_of_birth else "—"),
                    (t("address"), emp.address or "—"),
                ], badge="Admin Only")
                cl.addWidget(personal_card)

            cl.addStretch()
            self.scroll.setWidget(content)
            self.header_title.setText(emp.full_name)
        finally:
            session.close()

    def _info_card(self, title, rows, badge=None):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        title_row.addWidget(t_lbl)
        if badge:
            b = QLabel(badge)
            b.setStyleSheet("background: #fef2f2; color: #991b1b; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            title_row.addWidget(b)
        title_row.addStretch()
        layout.addLayout(title_row)

        for key, val in rows:
            row = QHBoxLayout()
            k = QLabel(key)
            k.setFixedWidth(140)
            k.setStyleSheet("font-size: 13px; color: #6b7280; background: transparent;")
            v = QLabel(str(val))
            v.setStyleSheet("font-size: 13px; color: #111827; font-weight: bold; background: transparent;")
            v.setWordWrap(True)
            row.addWidget(k)
            row.addWidget(v)
            row.addStretch()
            layout.addLayout(row)

        return card