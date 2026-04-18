"""
Org Hierarchy Page
- Tree view of the full organization (unlimited depth)
- Add/Edit/Delete org units
- Self-referencing structure: Organization → Division → Department → Unit → Team
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from src.core.i18n import t
from src.database.connection import get_session, log_action
from src.database.models import OrgUnit, Employee


UNIT_TYPES = ["organization", "division", "department", "unit", "team"]

TYPE_COLORS = {
    "organization": ("#f3e8ff", "#6b21a8", "🏛"),
    "division":     ("#fff7ed", "#9a3412", "🏢"),
    "department":   ("#eff6ff", "#1e40af", "🏬"),
    "unit":         ("#f0fdf4", "#166534", "🏗"),
    "team":         ("#f9fafb", "#374151", "👥"),
}


class HierarchyPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f4f6fb;")
        self._build()
        self.refresh()

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

        title = QLabel(t("nav_hierarchy"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a1d2e;")
        h.addWidget(title)
        h.addStretch()

        add_btn = QPushButton("+ Add Unit")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet("QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 0 16px; } QPushButton:hover { background: #3a57e8; }")
        add_btn.clicked.connect(self._add_unit)
        h.addWidget(add_btn)
        layout.addWidget(header)

        # Legend
        legend = QFrame()
        legend.setFixedHeight(44)
        legend.setStyleSheet("background: white; border-bottom: 1px solid #f0f0f0;")
        ll = QHBoxLayout(legend)
        ll.setContentsMargins(28, 0, 28, 0)
        ll.setSpacing(20)
        for utype, (bg, fg, icon) in TYPE_COLORS.items():
            dot = QLabel(f"{icon} {utype.title()}")
            dot.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 4px; padding: 2px 10px; font-size: 12px; font-weight: bold;")
            ll.addWidget(dot)
        ll.addStretch()
        layout.addWidget(legend)

        # Stats row
        self.stats_row = QHBoxLayout()
        self.stats_row.setContentsMargins(28, 12, 28, 12)
        self.stats_row.setSpacing(12)
        layout.addLayout(self.stats_row)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: white;
                border: none;
                font-size: 13px;
                color: #1a1d2e;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border-bottom: 1px solid #f9fafb;
            }
            QTreeWidget::item:selected {
                background: #eef2ff;
                color: #1a1d2e;
            }
            QTreeWidget::branch {
                background: white;
            }
        """)
        self.tree.setIndentation(24)
        self.tree.setAnimated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.tree)

    def refresh(self):
        self.tree.clear()

        # Clear stats
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            all_units = session.query(OrgUnit).all()
            units_data = [{
                "id": u.id,
                "name": u.name,
                "type": u.unit_type,
                "parent_id": u.parent_id,
                "head": u.head.full_name if u.head else None,
                "emp_count": len(u.employees),
            } for u in all_units]
        finally:
            session.close()

        # Stats
        counts = {}
        for u in units_data:
            counts[u["type"]] = counts.get(u["type"], 0) + 1

        for utype, cnt in counts.items():
            bg, fg, icon = TYPE_COLORS.get(utype, ("#f9fafb", "#374151", "•"))
            lbl = QLabel(f"{icon} {cnt} {utype.title()}{'s' if cnt != 1 else ''}")
            lbl.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 6px; padding: 4px 12px; font-size: 12px; font-weight: bold;")
            self.stats_row.addWidget(lbl)
        self.stats_row.addStretch()

        if not units_data:
            root_item = QTreeWidgetItem(self.tree)
            root_item.setText(0, "No org units yet. Click '+ Add Unit' to create the organization root.")
            root_item.setForeground(0, QColor("#9ca3af"))
            return

        # Build tree
        id_to_item = {}
        roots = [u for u in units_data if not u["parent_id"]]
        non_roots = [u for u in units_data if u["parent_id"]]

        def make_item(u, parent_widget):
            bg, fg, icon = TYPE_COLORS.get(u["type"], ("#f9fafb", "#374151", "•"))
            item = QTreeWidgetItem(parent_widget)

            head_str = f"  ·  Head: {u['head']}" if u["head"] else ""
            emp_str  = f"  ·  👤 {u['emp_count']}" if u["emp_count"] > 0 else ""
            item.setText(0, f"{icon}  {u['name']}  [{u['type']}]{head_str}{emp_str}")
            item.setData(0, Qt.UserRole, u["id"])
            item.setForeground(0, QColor(fg))
            item.setBackground(0, QColor(bg + "60"))  # slight tint

            # Action buttons via custom widget
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            aw = QHBoxLayout(action_widget)
            aw.setContentsMargins(0, 2, 8, 2)
            aw.setSpacing(4)
            aw.addStretch()

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(48, 24)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 4px; font-size: 11px; } QPushButton:hover { background: #e5e7eb; }")
            edit_btn.clicked.connect(lambda _, uid=u["id"]: self._edit_unit(uid))

            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(52, 24)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("QPushButton { background: #fef2f2; color: #991b1b; border: none; border-radius: 4px; font-size: 11px; } QPushButton:hover { background: #fee2e2; }")
            del_btn.clicked.connect(lambda _, uid=u["id"]: self._delete_unit(uid))

            aw.addWidget(edit_btn)
            aw.addWidget(del_btn)
            self.tree.setItemWidget(item, 0, None)

            id_to_item[u["id"]] = item
            return item

        for u in roots:
            make_item(u, self.tree)

        # Multi-pass for nested items
        remaining = list(non_roots)
        max_passes = 10
        for _ in range(max_passes):
            if not remaining:
                break
            still_remaining = []
            for u in remaining:
                parent_item = id_to_item.get(u["parent_id"])
                if parent_item:
                    make_item(u, parent_item)
                else:
                    still_remaining.append(u)
            remaining = still_remaining

        self.tree.expandAll()

    def _add_unit(self):
        dialog = OrgUnitDialog(self.user, parent=self)
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

            # Check for children or employees
            children = session.query(OrgUnit).filter_by(parent_id=unit_id).count()
            emp_count = len(unit.employees)

            if children > 0:
                QMessageBox.warning(self, t("warning"),
                    f"Cannot delete '{unit.name}' — it has {children} child unit(s).\nDelete or reassign them first.")
                return

            if emp_count > 0:
                QMessageBox.warning(self, t("warning"),
                    f"Cannot delete '{unit.name}' — it has {emp_count} employee(s) assigned.\nReassign them first.")
                return

            confirm = QMessageBox.question(self, "Delete Unit",
                f"Delete '{unit.name}'?", QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return

            log_action(
                session=session,
                performed_by_id=self.user.id,
                action="org_unit.delete",
                target_table="org_unit",
                target_id=unit_id,
                description=f"Org unit deleted: {unit.name} ({unit.unit_type})",
            )
            session.delete(unit)
            session.commit()
            self.refresh()
        finally:
            session.close()


class OrgUnitDialog(QDialog):
    def __init__(self, user, unit_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.unit_id = unit_id
        self.setWindowTitle("Edit Unit" if unit_id else "Add Org Unit")
        self.setFixedWidth(460)
        self.setStyleSheet("background: white; color: #1a1d2e;")
        self._build()
        if unit_id:
            self._load(unit_id)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Org Unit" if self.unit_id else "Add New Org Unit")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1d2e;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        input_style = "QLineEdit { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #1a1d2e; background: #f9fafb; min-height: 36px; } QLineEdit:focus { border-color: #4f6ef7; }"
        combo_style = "QComboBox { border: 1px solid #e5e7eb; border-radius: 8px; padding: 0 10px; font-size: 13px; color: #1a1d2e; background: #f9fafb; min-height: 36px; } QComboBox::drop-down { border: none; }"

        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(input_style)
        self.name_input.setPlaceholderText("e.g. Technology Division")
        form.addRow("Name *", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet(combo_style)
        for ut in UNIT_TYPES:
            self.type_combo.addItem(ut.title(), ut)
        form.addRow("Type *", self.type_combo)

        self.parent_combo = QComboBox()
        self.parent_combo.setStyleSheet(combo_style)
        self.parent_combo.addItem("— None (root) —", None)
        self._load_parents()
        form.addRow("Parent Unit", self.parent_combo)

        self.head_combo = QComboBox()
        self.head_combo.setStyleSheet(combo_style)
        self.head_combo.addItem("— None —", None)
        self._load_employees()
        form.addRow("Head / In-Charge", self.head_combo)

        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(36)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: none; border-radius: 8px; padding: 0 20px; font-size: 13px; } QPushButton:hover { background: #e5e7eb; }")
        cancel.clicked.connect(self.reject)

        save = QPushButton(t("save"))
        save.setFixedHeight(36)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet("QPushButton { background: #4f6ef7; color: white; border: none; border-radius: 8px; padding: 0 20px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #3a57e8; }")
        save.clicked.connect(self._save)

        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _load_parents(self):
        session = get_session()
        try:
            units = session.query(OrgUnit).all()
            for u in units:
                if u.id != self.unit_id:
                    self.parent_combo.addItem(f"{u.unit_type.title()}: {u.name}", u.id)
        finally:
            session.close()

    def _load_employees(self):
        session = get_session()
        try:
            emps = session.query(Employee).filter_by(status="active").all()
            for e in emps:
                self.head_combo.addItem(f"{e.employee_id} — {e.full_name}", e.id)
        finally:
            session.close()

    def _load(self, unit_id):
        session = get_session()
        try:
            unit = session.query(OrgUnit).filter_by(id=unit_id).first()
            if unit:
                self.name_input.setText(unit.name)
                idx = self.type_combo.findData(unit.unit_type)
                if idx >= 0:
                    self.type_combo.setCurrentIndex(idx)
                if unit.parent_id:
                    idx = self.parent_combo.findData(unit.parent_id)
                    if idx >= 0:
                        self.parent_combo.setCurrentIndex(idx)
                if unit.head_employee_id:
                    idx = self.head_combo.findData(unit.head_employee_id)
                    if idx >= 0:
                        self.head_combo.setCurrentIndex(idx)
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
                old_name = unit.name
                unit.name = name
                unit.unit_type = self.type_combo.currentData()
                unit.parent_id = self.parent_combo.currentData()
                unit.head_employee_id = self.head_combo.currentData()
                log_action(session, self.user.id, "org_unit.update", "org_unit", self.unit_id,
                    f"Org unit updated: {old_name} → {name}")
            else:
                unit = OrgUnit(
                    name=name,
                    unit_type=self.type_combo.currentData(),
                    parent_id=self.parent_combo.currentData(),
                    head_employee_id=self.head_combo.currentData(),
                )
                session.add(unit)
                session.flush()
                log_action(session, self.user.id, "org_unit.create", "org_unit", unit.id,
                    f"Org unit created: {name} ({unit.unit_type})")

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()