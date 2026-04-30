"""Organization hierarchy page with Figma-style readable node cards."""

import qtawesome as qta
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox
)

from src.core.i18n import t
from src.database.connection import get_session, log_action
from src.database.models import OrgUnit, Employee


UNIT_TYPES = ["organization", "division", "department", "unit", "team"]
TYPE_COLORS = {
    "organization": ("#f3e8ff", "#6b21a8", "fa5s.building"),
    "division": ("#fff7ed", "#9a3412", "fa5s.layer-group"),
    "department": ("#eff6ff", "#1e40af", "fa5s.sitemap"),
    "unit": ("#f0fdf4", "#166534", "fa5s.briefcase"),
    "team": ("#f9fafb", "#374151", "fa5s.users"),
}


class HierarchyPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.units_data = []
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
        self.layout.setContentsMargins(28, 28, 28, 28)
        self.layout.setSpacing(18)

        title = QLabel("Organization Hierarchy")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel("View and manage the organizational structure")
        subtitle.setStyleSheet("font-size: 14px; color: #6b7280; background: transparent;")
        self.layout.addWidget(title)
        self.layout.addWidget(subtitle)

        controls = QFrame()
        controls.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        cl = QHBoxLayout(controls)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search departments, units, or positions...")
        self.search.setFixedHeight(38)
        self.search.textChanged.connect(self.refresh)
        cl.addWidget(self.search, 1)
        add_dept = QPushButton("  Add Department")
        add_dept.setIcon(qta.icon("fa5s.building", color="#111827"))
        add_dept.setIconSize(QSize(14, 14))
        add_dept.setCursor(Qt.PointingHandCursor)
        add_dept.setFixedHeight(36)
        add_dept.setStyleSheet(_outline_btn())
        add_dept.clicked.connect(lambda: self._add_unit("department"))
        add_unit = QPushButton("  Add Unit")
        add_unit.setIcon(qta.icon("fa5s.plus", color="white"))
        add_unit.setIconSize(QSize(14, 14))
        add_unit.setCursor(Qt.PointingHandCursor)
        add_unit.setFixedHeight(36)
        add_unit.setStyleSheet(_primary_btn())
        add_unit.clicked.connect(self._add_unit)
        cl.addWidget(add_dept)
        cl.addWidget(add_unit)
        self.layout.addWidget(controls)

        legend = QHBoxLayout()
        legend.setSpacing(16)
        for kind, (bg, fg, icon) in TYPE_COLORS.items():
            legend.addWidget(_legend(kind.title(), bg, fg, icon))
        legend.addStretch()
        self.layout.addLayout(legend)

        self.tree_container = QFrame()
        self.tree_container.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        self.tree_layout = QVBoxLayout(self.tree_container)
        self.tree_layout.setContentsMargins(18, 18, 18, 18)
        self.tree_layout.setSpacing(12)
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
            self.units_data = [{
                "id": u.id,
                "name": u.name,
                "type": u.unit_type,
                "parent_id": u.parent_id,
                "head": u.head.full_name if u.head else "Unassigned",
                "emp_count": len(u.employees),
            } for u in units if not query or query in u.name.lower() or query in u.unit_type.lower()]
        finally:
            session.close()

        if not self.units_data:
            empty = QLabel("No organization units found. Add an organization or department to begin.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 32px; background: transparent;")
            self.tree_layout.addWidget(empty)
            return

        children = {}
        for unit in self.units_data:
            children.setdefault(unit["parent_id"], []).append(unit)
        for root_unit in children.get(None, []):
            self._add_node(root_unit, children, 0)

    def _add_node(self, unit, children, depth):
        node = QFrame()
        bg, fg, icon = TYPE_COLORS.get(unit["type"], ("#f9fafb", "#374151", "fa5s.circle"))
        node.setStyleSheet(f"background: {bg}; border-radius: 10px; border: 1px solid #e5e7eb;")
        row = QHBoxLayout(node)
        row.setContentsMargins(16 + depth * 36, 12, 14, 12)
        row.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color=fg).pixmap(18, 18))
        row.addWidget(icon_lbl)
        text_col = QVBoxLayout()
        title_row = QHBoxLayout()
        name = QLabel(unit["name"])
        name.setStyleSheet("font-size: 14px; font-weight: 800; color: #111827; background: transparent;")
        badge = QLabel(unit["type"])
        badge.setStyleSheet("background: white; color: #374151; border-radius: 5px; padding: 2px 8px; font-size: 11px; font-weight: 700;")
        title_row.addWidget(name)
        title_row.addWidget(badge)
        title_row.addStretch()
        meta = QLabel(f"Head: {unit['head']}    {unit['emp_count']} employees")
        meta.setStyleSheet("font-size: 12px; color: #4b5563; background: transparent;")
        text_col.addLayout(title_row)
        text_col.addWidget(meta)
        row.addLayout(text_col, 1)

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

        self.tree_layout.addWidget(node)
        for child in children.get(unit["id"], []):
            self._add_node(child, children, depth + 1)

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
                QMessageBox.warning(self, t("warning"), "Reassign child units and employees before deleting this node.")
                return
            if QMessageBox.question(self, "Delete Unit", f"Delete '{unit.name}'?") != QMessageBox.Yes:
                return
            log_action(session, action="org_unit.delete", performed_by_id=self.user.id, target_table="org_unit", target_id=unit_id, description=f"Org unit deleted: {unit.name} ({unit.unit_type})")
            session.delete(unit)
            session.commit()
            self.refresh()
        finally:
            session.close()


class OrgUnitDialog(QDialog):
    def __init__(self, user, unit_id=None, default_type=None, parent_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.unit_id = unit_id
        self.default_type = default_type
        self.default_parent_id = parent_id
        self.setWindowTitle("Edit Unit" if unit_id else "Add Org Unit")
        self.setFixedWidth(460)
        self.setStyleSheet("background: white; color: #111827;")
        self._build()
        if unit_id:
            self._load(unit_id)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("Edit Organization Unit" if self.unit_id else "Add Organization Unit")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #111827;")
        layout.addWidget(title)
        form = QFormLayout()
        form.setSpacing(10)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Technology Division")
        form.addRow("Name *", self.name_input)
        self.type_combo = QComboBox()
        for unit_type in UNIT_TYPES:
            self.type_combo.addItem(unit_type.title(), unit_type)
        form.addRow("Type *", self.type_combo)
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (root)", None)
        self._load_parents()
        form.addRow("Parent Unit", self.parent_combo)
        self.head_combo = QComboBox()
        self.head_combo.addItem("None", None)
        self._load_employees()
        form.addRow("Head / In-Charge", self.head_combo)
        layout.addLayout(form)
        if self.default_type:
            idx = self.type_combo.findData(self.default_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        if self.default_parent_id:
            idx = self.parent_combo.findData(self.default_parent_id)
            if idx >= 0:
                self.parent_combo.setCurrentIndex(idx)
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

    def _load_parents(self):
        session = get_session()
        try:
            for unit in session.query(OrgUnit).all():
                if unit.id != self.unit_id:
                    self.parent_combo.addItem(f"{unit.unit_type.title()}: {unit.name}", unit.id)
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
                self.parent_combo.setCurrentIndex(max(0, self.parent_combo.findData(unit.parent_id)))
                self.head_combo.setCurrentIndex(max(0, self.head_combo.findData(unit.head_employee_id)))
        finally:
            session.close()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, t("warning"), "Name is required.")
            return
        session = get_session()
        try:
            if self.unit_id:
                unit = session.query(OrgUnit).filter_by(id=self.unit_id).first()
                unit.name = name
                unit.unit_type = self.type_combo.currentData()
                unit.parent_id = self.parent_combo.currentData()
                unit.head_employee_id = self.head_combo.currentData()
                action = "org_unit.update"
            else:
                unit = OrgUnit(name=name, unit_type=self.type_combo.currentData(), parent_id=self.parent_combo.currentData(), head_employee_id=self.head_combo.currentData())
                session.add(unit)
                session.flush()
                action = "org_unit.create"
            log_action(session, action=action, performed_by_id=self.user.id, target_table="org_unit", target_id=unit.id, description=f"Org unit saved: {unit.name} ({unit.unit_type})")
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


def _legend(text, bg, fg, icon):
    label = QLabel(f"  {text}")
    label.setPixmap(qta.icon(icon, color=fg).pixmap(12, 12))
    label.setStyleSheet(f"background: transparent; color: #6b7280; font-size: 12px; padding: 2px 6px;")
    return label


def _primary_btn():
    return "QPushButton { background: #030213; color: white; border: none; border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 700; min-height: 36px; } QPushButton:hover { background: #111827; }"


def _outline_btn():
    return "QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 700; min-height: 36px; } QPushButton:hover { background: #f9fafb; }"
