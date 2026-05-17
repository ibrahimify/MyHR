"""Organization hierarchy page with Figma-style readable node cards."""

import qtawesome as qta
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)

from src.core.i18n import t
from src.database.connection import get_session, log_action
from src.database.models import OrgUnit, Employee


UNIT_TYPES = ["organization", "division", "department", "unit", "team", "position"]
TYPE_ORDER_HINT = ["organization", "division", "department", "unit", "team", "position"]
PARENT_BY_TYPE = {
    "organization": None,
    "division": "organization",
    "department": "division",
    "unit": "department",
    "team": "unit",
    "position": "team",
}
TYPE_COLORS = {
    "organization": ("#f3e8ff", "#6b21a8", "#e9d5ff", "fa5s.building"),
    "division": ("#fff7ed", "#9a3412", "#fed7aa", "fa5s.layer-group"),
    "department": ("#eff6ff", "#1e40af", "#bfdbfe", "fa5s.sitemap"),
    "unit": ("#f0fdf4", "#166534", "#bbf7d0", "fa5s.briefcase"),
    "team": ("#f9fafb", "#374151", "#e5e7eb", "fa5s.users"),
    "position": ("#f9fafb", "#6b7280", "#e5e7eb", "fa5s.user-tie"),
}

INPUT_SS = """
QLineEdit {
    border: none;
    border-radius: 8px;
    padding: 0 14px;
    font-size: 14px;
    background: #f3f4f6;
    color: #111827;
}
QLineEdit:focus {
    border: 1px solid #2563eb;
    background: white;
}
"""

COMBO_SS = """
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
QComboBox QAbstractItemView {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0px;
    color: #111827;
    selection-background-color: #eff6ff;
    selection-color: #111827;
    outline: none;
    padding: 6px;
    font-size: 14px;
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
QPushButton:default {
    background: #030213;
    color: white;
    border: none;
}
"""


class HierarchyPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.units_data = []
        self.collapsed_units = set()
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: #f9fafb;")
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(0)

        title = QLabel(t("hierarchy_title"))
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel(t("hierarchy_subtitle"))
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        self.layout.addWidget(title)
        self.layout.addSpacing(6)
        self.layout.addWidget(subtitle)
        self.layout.addSpacing(40)

        controls = QFrame()
        controls.setObjectName("HierarchyControls")
        controls.setStyleSheet("QFrame#HierarchyControls { background: white; border-radius: 8px; border: 1px solid #e5e7eb; }")
        cl = QHBoxLayout(controls)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(16)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_hierarchy"))
        self.search.setFixedHeight(44)
        self.search.setStyleSheet(INPUT_SS)
        self.search.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self.refresh)
        cl.addWidget(self.search, 1)
        add_dept = QPushButton("  " + t("add_department"))
        add_dept.setIcon(qta.icon("fa5s.building", color="#111827"))
        add_dept.setIconSize(QSize(14, 14))
        add_dept.setCursor(Qt.PointingHandCursor)
        add_dept.setFixedHeight(44)
        add_dept.setStyleSheet(_outline_btn())
        add_dept.clicked.connect(lambda: self._add_unit("department"))
        add_unit = QPushButton("  " + t("add_unit"))
        add_unit.setIcon(qta.icon("fa5s.plus", color="white"))
        add_unit.setIconSize(QSize(14, 14))
        add_unit.setCursor(Qt.PointingHandCursor)
        add_unit.setFixedHeight(44)
        add_unit.setStyleSheet(_primary_btn())
        add_unit.clicked.connect(self._add_unit)
        cl.addWidget(add_dept)
        cl.addWidget(add_unit)
        self.layout.addWidget(controls)
        self.layout.addSpacing(28)

        legend = QHBoxLayout()
        legend.setSpacing(18)
        for kind in TYPE_ORDER_HINT:
            bg, fg, border, icon = TYPE_COLORS[kind]
            legend.addWidget(_legend(kind.title(), bg, fg, icon))
        legend.addStretch()
        self.layout.addLayout(legend)
        self.layout.addSpacing(14)

        hint = QHBoxLayout()
        hint.setSpacing(8)
        for i, kind in enumerate(TYPE_ORDER_HINT):
            bg, fg, border, icon = TYPE_COLORS[kind]
            hint.addWidget(_hint_pill(kind.title(), bg, fg, border, icon))
            if i < len(TYPE_ORDER_HINT) - 1:
                arrow = QLabel()
                arrow.setFixedSize(16, 16)
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setPixmap(qta.icon("fa5s.chevron-right", color="#9ca3af").pixmap(10, 10))
                arrow.setStyleSheet("background: transparent; border: none;")
                hint.addWidget(arrow)
        hint.addStretch()
        self.layout.addLayout(hint)
        self.layout.addSpacing(28)

        self.tree_container = QFrame()
        self.tree_container.setObjectName("HierarchyTree")
        self.tree_container.setStyleSheet("QFrame#HierarchyTree { background: white; border-radius: 8px; border: 1px solid #e5e7eb; }")
        self.tree_layout = QVBoxLayout(self.tree_container)
        self.tree_layout.setContentsMargins(28, 28, 28, 28)
        self.tree_layout.setSpacing(14)
        self.layout.addWidget(self.tree_container)
        self.layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def refresh(self):
        while self.tree_layout.count():
            item = self.tree_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            units = session.query(OrgUnit).all()
            query = self.search.text().strip().lower() if hasattr(self, "search") else ""
            unit_ids = [u.id for u in units]
            employees_by_unit = {unit_id: [] for unit_id in unit_ids}
            if unit_ids:
                for emp in session.query(Employee).filter(Employee.org_unit_id.in_(unit_ids)).all():
                    employees_by_unit.setdefault(emp.org_unit_id, []).append(emp)
            self.units_data = [{
                "id": u.id,
                "name": u.name,
                "type": u.unit_type,
                "parent_id": u.parent_id,
                "head": u.head.full_name if u.head else "Unassigned",
                "head_position": u.head.position if u.head and u.head.position else "",
                "emp_count": len(u.employees),
                "people_count": 0,
                "search_text": " ".join([
                    u.name or "",
                    u.unit_type or "",
                    u.head.full_name if u.head else "",
                    u.head.position if u.head and u.head.position else "",
                    " ".join(e.full_name for e in employees_by_unit.get(u.id, [])),
                    " ".join(e.position or "" for e in employees_by_unit.get(u.id, [])),
                ]).lower(),
            } for u in units]
        finally:
            session.close()

        if not self.units_data:
            empty = QLabel(t("no_org_units"))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 32px; background: transparent;")
            self.tree_layout.addWidget(empty)
            return

        children = {}
        for unit in self.units_data:
            children.setdefault(unit["parent_id"], []).append(unit)
        for siblings in children.values():
            siblings.sort(key=lambda item: (UNIT_TYPES.index(item["type"]) if item["type"] in UNIT_TYPES else 99, item["name"].lower()))

        by_id = {unit["id"]: unit for unit in self.units_data}

        def subtree_people_count(unit):
            total = unit["emp_count"]
            for child in children.get(unit["id"], []):
                total += subtree_people_count(child)
            return total

        for unit in self.units_data:
            unit["people_count"] = subtree_people_count(unit)

        visible_ids = None
        if query:
            visible_ids = set()
            matched = [unit for unit in self.units_data if query in unit["search_text"]]
            for unit in matched:
                current = unit
                while current:
                    visible_ids.add(current["id"])
                    current = by_id.get(current["parent_id"])

                stack = list(children.get(unit["id"], []))
                while stack:
                    child = stack.pop()
                    visible_ids.add(child["id"])
                    stack.extend(children.get(child["id"], []))

            if not visible_ids:
                empty = QLabel(t("no_matching_org_units"))
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 32px; background: transparent;")
                self.tree_layout.addWidget(empty)
                return

        for root_unit in children.get(None, []):
            if visible_ids is None or root_unit["id"] in visible_ids:
                self._add_node(root_unit, children, 0, visible_ids, bool(query))

    def _add_node(self, unit, children, depth, visible_ids=None, force_open=False):
        child_units = [
            child for child in children.get(unit["id"], [])
            if visible_ids is None or child["id"] in visible_ids
        ]
        has_children = bool(child_units)
        is_collapsed = unit["id"] in self.collapsed_units and not force_open

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        wrap_row = QHBoxLayout(wrap)
        wrap_row.setContentsMargins(0, 0, 0, 0)
        wrap_row.setSpacing(0)

        for _ in range(depth):
            guide = QFrame()
            guide.setFixedWidth(46)
            guide.setStyleSheet("background: transparent; border: none; border-left: 2px solid #e5e7eb; margin-left: 22px;")
            wrap_row.addWidget(guide)

        chevron = QPushButton()
        chevron.setFixedSize(28, 28)
        chevron.setCursor(Qt.PointingHandCursor if has_children else Qt.ArrowCursor)
        chevron.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 6px; } QPushButton:hover { background: #f3f4f6; }")
        if has_children:
            icon_name = "fa5s.chevron-right" if is_collapsed else "fa5s.chevron-down"
            chevron.setIcon(qta.icon(icon_name, color="#374151"))
            chevron.setIconSize(QSize(12, 12))
            chevron.clicked.connect(lambda _, uid=unit["id"]: self._toggle_node(uid))
        else:
            chevron.setEnabled(False)
        wrap_row.addWidget(chevron)

        node = QFrame()
        node.setObjectName("HierarchyNode")
        if unit["type"] == "team" and unit["people_count"] > 0:
            node.setCursor(Qt.PointingHandCursor)
            node.mouseReleaseEvent = lambda event, uid=unit["id"]: self._show_unit_employees(uid)
        bg, fg, border, icon = TYPE_COLORS.get(unit["type"], ("#f9fafb", "#374151", "#e5e7eb", "fa5s.circle"))
        node.setStyleSheet(f"""
            QFrame#HierarchyNode {{
                background: {bg};
                border-radius: 8px;
                border: 1px solid {border};
            }}
            QFrame#HierarchyNode QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        row = QHBoxLayout(node)
        row.setContentsMargins(20, 16, 16, 16)
        row.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(qta.icon(icon, color=fg).pixmap(18, 18))
        row.addWidget(icon_lbl)
        text_col = QVBoxLayout()
        text_col.setSpacing(8)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        name = QLabel(unit["name"])
        name.setStyleSheet("font-size: 16px; font-weight: 800; color: #111827; background: transparent;")
        badge = QLabel(unit["type"])
        badge.setStyleSheet("background: white; color: #111827; border: 1px solid #dbe2ea; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 700;")
        title_row.addWidget(name)
        title_row.addWidget(badge)
        title_row.addStretch()
        meta = QWidget()
        meta.setStyleSheet("background: transparent; border: none;")
        meta_row = QHBoxLayout(meta)
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)
        head_label = QLabel(t("head"))
        head_label.setStyleSheet("font-size: 14px; font-weight: 800; color: #374151; background: transparent; border: none;")
        head_text = unit["head"]
        if unit["head_position"]:
            head_text = f"{unit['head_position']} - {unit['head']}"
        head_value = QLabel(head_text)
        head_value.setStyleSheet("font-size: 14px; color: #374151; background: transparent; border: none;")
        people_icon = QLabel()
        people_icon.setFixedSize(16, 16)
        people_icon.setAlignment(Qt.AlignCenter)
        people_icon.setPixmap(qta.icon("fa5s.user-friends", color="#4b5563").pixmap(14, 14))
        people_icon.setStyleSheet("background: transparent; border: none;")
        people = QLabel(t("employees_count", count=unit["people_count"]))
        people.setStyleSheet("font-size: 14px; color: #374151; background: transparent; border: none;")
        meta_row.addWidget(head_label)
        meta_row.addWidget(head_value)
        meta_row.addSpacing(10)
        meta_row.addWidget(people_icon)
        meta_row.addWidget(people)
        meta_row.addStretch()
        text_col.addLayout(title_row)
        text_col.addWidget(meta)
        row.addLayout(text_col, 1)

        if unit["people_count"] > 0:
            view_btn = QPushButton()
            view_btn.setToolTip(t("view_employees"))
            view_btn.setIcon(qta.icon("fa5s.user-friends", color="#111827"))
            view_btn.setIconSize(QSize(13, 13))
            view_btn.setFixedSize(28, 28)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("QPushButton { background: white; border: 1px solid #e5e7eb; border-radius: 6px; } QPushButton:hover { background: #eff6ff; border-color: #bfdbfe; }")
            view_btn.clicked.connect(lambda _, uid=unit["id"]: self._show_unit_employees(uid))
            row.addWidget(view_btn)

        for icon_name, color, handler in [
            ("fa5s.plus", "#2563eb", lambda _, uid=unit["id"]: self._add_unit(parent_id=uid)),
            ("fa5s.edit", "#2563eb", lambda _, uid=unit["id"]: self._edit_unit(uid)),
            ("fa5s.trash-alt", "#dc2626", lambda _, uid=unit["id"]: self._delete_unit(uid)),
        ]:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setIconSize(QSize(13, 13))
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background: white; border: 1px solid #e5e7eb; border-radius: 6px; } QPushButton:hover { background: #f9fafb; }")
            btn.clicked.connect(handler)
            row.addWidget(btn)

        wrap_row.addWidget(node, 1)
        self.tree_layout.addWidget(wrap)

        if not is_collapsed:
            for child in child_units:
                self._add_node(child, children, depth + 1, visible_ids, force_open)

    def _toggle_node(self, unit_id):
        if unit_id in self.collapsed_units:
            self.collapsed_units.remove(unit_id)
        else:
            self.collapsed_units.add(unit_id)
        self.refresh()

    def _show_unit_employees(self, unit_id):
        dialog = UnitEmployeesDialog(unit_id, parent=self)
        dialog.exec()

    def _add_unit(self, default_type=None, parent_id=None):
        dialog = OrgUnitDialog(self.user, default_type=default_type, parent_id=parent_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_unit(self, unit_id):
        dialog = OrgUnitDialog(self.user, unit_id=unit_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_unit(self, unit_id):
        session = get_session()
        try:
            unit = session.query(OrgUnit).filter_by(id=unit_id).first()
            if not unit:
                return
            children = session.query(OrgUnit).filter_by(parent_id=unit_id).count()
            emp_count = len(unit.employees)
            if children or emp_count:
                _warning(self, t("warning"), "Reassign child units and employees before deleting this node.")
                return
            if _question(self, t("delete_unit"), f"Delete '{unit.name}'?") != QMessageBox.Yes:
                return
            log_action(session, action="org_unit.delete", performed_by_id=self.user.id, target_table="org_unit", target_id=unit_id, description=f"Org unit deleted: {unit.name} ({unit.unit_type})")
            session.delete(unit)
            session.commit()
            self.refresh()
        finally:
            session.close()


class UnitEmployeesDialog(QDialog):
    def __init__(self, unit_id, parent=None):
        super().__init__(parent)
        self.unit_id = unit_id
        self.setWindowTitle(t("employees_in_unit"))
        self.resize(860, 520)
        self.setStyleSheet("""
            QDialog { background: white; color: #111827; }
            QLabel { color: #111827; background: transparent; border: none; }
            QTableWidget {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                gridline-color: #f3f4f6;
                color: #111827;
                selection-background-color: #eff6ff;
                selection-color: #111827;
                outline: none;
            }
            QTableWidget::item {
                border: none;
                border-bottom: 1px solid #f3f4f6;
                padding: 0 10px;
                color: #111827;
            }
            QHeaderView::section {
                background: white;
                color: #030213;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 0 10px;
                font-size: 13px;
                font-weight: 800;
                min-height: 44px;
            }
        """)
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: #dbeafe; border-radius: 8px;")
        icon.setPixmap(qta.icon("fa5s.user-friends", color="#2563eb").pixmap(20, 20))
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title_lbl = QLabel("Employees")
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #030213;")
        self.subtitle_lbl = QLabel("")
        self.subtitle_lbl.setStyleSheet("font-size: 14px; color: #4b5563;")
        text.addWidget(self.title_lbl)
        text.addWidget(self.subtitle_lbl)
        header.addWidget(icon)
        header.addLayout(text)
        header.addStretch()
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("employee_id"), t("name"), t("position"), t("level"), t("status"), t("email")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton(t("close"))
        close.setCursor(Qt.PointingHandCursor)
        close.setFixedSize(110, 38)
        close.setStyleSheet(_outline_btn())
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)

    def _load(self):
        session = get_session()
        try:
            unit = session.query(OrgUnit).filter_by(id=self.unit_id).first()
            if not unit:
                return
            unit_ids = _descendant_unit_ids(session, unit.id)
            employees = (
                session.query(Employee)
                .filter(Employee.org_unit_id.in_(unit_ids))
                .order_by(Employee.last_name, Employee.first_name)
                .all()
            )
            self.title_lbl.setText(unit.name)
            scope = "team" if unit.unit_type == "team" else f"{unit.unit_type} and child units"
            self.subtitle_lbl.setText(t("employees_in_scope", count=len(employees), scope=scope))
            self.table.setRowCount(len(employees))
            for row, employee in enumerate(employees):
                self.table.setRowHeight(row, 50)
                values = [
                    employee.employee_id,
                    employee.full_name,
                    employee.position,
                    employee.title.name if employee.title else "",
                    employee.status.replace("_", " ").title(),
                    employee.work_email or employee.personal_email or "",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(value)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table.setItem(row, col, item)
        finally:
            session.close()


class OrgUnitDialog(QDialog):
    def __init__(self, user, unit_id=None, default_type=None, parent_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.unit_id = unit_id
        self.default_type = default_type
        self.default_parent_id = parent_id
        self.setWindowTitle(t("edit_unit") if unit_id else t("add_org_unit"))
        self.setFixedWidth(580)
        self.setStyleSheet("""
            QDialog { background: white; color: #111827; }
            QLabel { color: #111827; background: transparent; }
        """)
        self._build()
        if unit_id:
            self._load(unit_id)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel(t("edit_organization_unit") if self.unit_id else t("add_organization_unit"))
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #111827;")
        layout.addWidget(title)
        form = QFormLayout()
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Technology Division")
        self.name_input.setFixedHeight(42)
        self.name_input.setStyleSheet(INPUT_SS)
        form.addRow(_form_label(t("name") + " *"), self.name_input)
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(42)
        self.type_combo.setStyleSheet(COMBO_SS)
        self._load_types()
        _prepare_combo(self.type_combo)
        form.addRow(_form_label(t("type") + " *"), self.type_combo)
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(42)
        self.parent_combo.setStyleSheet(COMBO_SS)
        self._load_parents()
        _prepare_combo(self.parent_combo)
        form.addRow(_form_label("Parent Unit"), self.parent_combo)
        self.head_combo = QComboBox()
        self.head_combo.setFixedHeight(42)
        self.head_combo.setStyleSheet(COMBO_SS)
        self.head_combo.addItem(t("none"), None)
        self._load_employees()
        _prepare_combo(self.head_combo)
        form.addRow(_form_label("Head / In-Charge"), self.head_combo)
        layout.addLayout(form)
        if self.default_type:
            idx = self.type_combo.findData(self.default_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
                self._load_parents()
        if self.default_parent_id:
            idx = self.parent_combo.findData(self.default_parent_id)
            if idx >= 0:
                self.parent_combo.setCurrentIndex(idx)
        self.type_combo.currentIndexChanged.connect(lambda _: self._load_parents())
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setStyleSheet(_outline_btn())
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setStyleSheet(_primary_btn())
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _load_types(self):
        self.type_combo.clear()
        session = get_session()
        try:
            for unit_type in UNIT_TYPES:
                self.type_combo.addItem(unit_type.title(), unit_type)
                item = self.type_combo.model().item(self.type_combo.count() - 1)
                allowed, _ = _type_can_be_selected(session, unit_type, self.unit_id)
                if item and not allowed:
                    item.setEnabled(False)
                    item.setToolTip(_type_block_reason(unit_type))
            for index in range(self.type_combo.count()):
                item = self.type_combo.model().item(index)
                if item and item.isEnabled():
                    self.type_combo.setCurrentIndex(index)
                    break
        finally:
            session.close()

    def _load_parents(self):
        if not hasattr(self, "parent_combo"):
            return
        current_parent = self.parent_combo.currentData()
        self.parent_combo.clear()
        selected_type = self.type_combo.currentData()
        required_parent_type = PARENT_BY_TYPE.get(selected_type)
        if required_parent_type is None:
            self.parent_combo.addItem(t("none_root"), None)
            return
        session = get_session()
        try:
            for unit in session.query(OrgUnit).all():
                if unit.id != self.unit_id and unit.unit_type == required_parent_type:
                    self.parent_combo.addItem(f"{unit.unit_type.title()}: {unit.name}", unit.id)
            idx = self.parent_combo.findData(current_parent)
            if idx >= 0:
                self.parent_combo.setCurrentIndex(idx)
        finally:
            session.close()

    def _load_employees(self):
        session = get_session()
        try:
            for emp in session.query(Employee).filter_by(status="active").all():
                self.head_combo.addItem(f"{emp.employee_id} - {emp.full_name}", emp.id)
        finally:
            session.close()

    def _load(self, unit_id):
        session = get_session()
        try:
            unit = session.query(OrgUnit).filter_by(id=unit_id).first()
            if unit:
                self.name_input.setText(unit.name)
                self.type_combo.setCurrentIndex(max(0, self.type_combo.findData(unit.unit_type)))
                self._load_parents()
                self.parent_combo.setCurrentIndex(max(0, self.parent_combo.findData(unit.parent_id)))
                self.head_combo.setCurrentIndex(max(0, self.head_combo.findData(unit.head_employee_id)))
        finally:
            session.close()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            _warning(self, t("warning"), "Name is required.")
            return
        selected_type = self.type_combo.currentData()
        selected_parent_id = self.parent_combo.currentData()
        session = get_session()
        try:
            structure_error = _validate_unit_structure(session, selected_type, selected_parent_id, self.unit_id, name)
            if structure_error:
                _warning(self, t("warning"), structure_error)
                return
            if self.unit_id:
                if _would_create_parent_cycle(session, self.unit_id, selected_parent_id):
                    _warning(self, t("warning"), "A unit cannot be placed under itself or one of its child units.")
                    return
                unit = session.query(OrgUnit).filter_by(id=self.unit_id).first()
                unit.name = name
                unit.unit_type = selected_type
                unit.parent_id = selected_parent_id
                unit.head_employee_id = self.head_combo.currentData()
                action = "org_unit.update"
            else:
                unit = OrgUnit(name=name, unit_type=selected_type, parent_id=selected_parent_id, head_employee_id=self.head_combo.currentData())
                session.add(unit)
                session.flush()
                action = "org_unit.create"
            log_action(session, action=action, performed_by_id=self.user.id, target_table="org_unit", target_id=unit.id, description=f"Org unit saved: {unit.name} ({unit.unit_type})")
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


def _legend(text, bg, fg, icon):
    wrap = QWidget()
    wrap.setStyleSheet("background: transparent;")
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    swatch = QLabel()
    swatch.setFixedSize(18, 18)
    swatch.setStyleSheet(f"background: {bg}; border: 1px solid {fg}; border-radius: 4px;")
    text_lbl = QLabel(text)
    text_lbl.setStyleSheet("background: transparent; color: #374151; font-size: 14px;")
    row.addWidget(swatch)
    row.addWidget(text_lbl)
    return wrap


def _hint_pill(text, bg, fg, border, icon):
    pill = QFrame()
    pill.setObjectName("HierarchyHintPill")
    pill.setStyleSheet(f"""
        QFrame#HierarchyHintPill {{
            background: {bg};
            border: none;
            border-radius: 8px;
        }}
        QFrame#HierarchyHintPill QLabel {{
            background: transparent;
            border: none;
        }}
    """)
    row = QHBoxLayout(pill)
    row.setContentsMargins(10, 5, 10, 5)
    row.setSpacing(7)
    icon_lbl = QLabel()
    icon_lbl.setPixmap(qta.icon(icon, color=fg).pixmap(13, 13))
    icon_lbl.setStyleSheet("background: transparent; border: none;")
    text_lbl = QLabel(text)
    text_lbl.setStyleSheet(f"background: transparent; border: none; color: {fg}; font-size: 12px; font-weight: 700;")
    row.addWidget(icon_lbl)
    row.addWidget(text_lbl)
    return pill


def _form_label(text):
    label = QLabel(text)
    label.setMinimumWidth(122)
    label.setStyleSheet("font-size: 14px; color: #111827; background: transparent; border: none;")
    return label


def _prepare_combo(combo):
    combo.setMinimumWidth(390)
    combo.view().setMinimumWidth(390)
    combo.view().setTextElideMode(Qt.ElideNone)
    combo.view().setStyleSheet("""
        QListView {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 0px;
            color: #111827;
            outline: none;
            padding: 4px;
        }
        QListView::item {
            min-height: 30px;
            padding: 4px 10px;
            background: white;
            color: #111827;
        }
        QListView::item:selected {
            background: #eff6ff;
            color: #111827;
        }
    """)
    combo.setMaxVisibleItems(8)


def _type_can_be_selected(session, unit_type, current_unit_id=None):
    if unit_type == "organization":
        existing = session.query(OrgUnit).filter_by(unit_type="organization").first()
        if existing and existing.id != current_unit_id:
            return False, "Only one organization can exist in this workspace."
        return True, ""
    required_parent_type = PARENT_BY_TYPE.get(unit_type)
    if not required_parent_type:
        return True, ""
    exists = session.query(OrgUnit).filter_by(unit_type=required_parent_type).first()
    if not exists:
        return False, _type_block_reason(unit_type)
    return True, ""


def _type_block_reason(unit_type):
    required_parent_type = PARENT_BY_TYPE.get(unit_type)
    if unit_type == "organization":
        return "Only one organization can exist in this workspace."
    if required_parent_type:
        return f"Create a {required_parent_type} before adding a {unit_type}."
    return ""


def _validate_unit_structure(session, unit_type, parent_id, current_unit_id=None, name=""):
    if not unit_type:
        return "Please select a valid organization unit type."
    if unit_type == "organization":
        existing = session.query(OrgUnit).filter_by(unit_type="organization").first()
        if existing and existing.id != current_unit_id:
            return "Only one organization can exist in this workspace."
        if parent_id is not None:
            return "An organization must be the root node."
        return ""

    required_parent_type = PARENT_BY_TYPE.get(unit_type)
    if not parent_id:
        return _type_block_reason(unit_type)
    parent = session.query(OrgUnit).filter_by(id=parent_id).first()
    if not parent or parent.unit_type != required_parent_type:
        return f"A {unit_type} must be placed under a {required_parent_type}."
    return ""


def _would_create_parent_cycle(session, unit_id, parent_id):
    current_id = parent_id
    while current_id:
        if current_id == unit_id:
            return True
        parent = session.query(OrgUnit).filter_by(id=current_id).first()
        current_id = parent.parent_id if parent else None
    return False


def _descendant_unit_ids(session, root_id):
    ids = [root_id]
    stack = [root_id]
    while stack:
        current_id = stack.pop()
        children = session.query(OrgUnit.id).filter_by(parent_id=current_id).all()
        child_ids = [child_id for (child_id,) in children]
        ids.extend(child_ids)
        stack.extend(child_ids)
    return ids


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


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)


def _primary_btn():
    return "QPushButton { background: #030213; color: white; border: none; border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 700; min-height: 36px; } QPushButton:hover { background: #111827; }"


def _outline_btn():
    return "QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 700; min-height: 36px; } QPushButton:hover { background: #f9fafb; }"
