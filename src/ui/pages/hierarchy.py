"""Organization hierarchy page with lazy canvas rendering."""

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsPathItem, QGridLayout
)

from src.core.i18n import t
from src.ui.styles import polish_combo_box
from src.database.connection import get_session, log_action
from src.database.models import OrgUnit, Employee


UNIT_TYPES = ["organization", "division", "department", "unit", "team", "position"]
TYPE_ORDER_HINT = ["organization", "division", "department", "unit", "team", "employee"]
NEXT_TYPE_LABEL = {
    "organization": ("division", "divisions"),
    "division": ("department", "departments"),
    "department": ("unit", "units"),
    "unit": ("team", "teams"),
    "team": ("member", "members"),
    "position": ("employee", "employees"),
}
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
    "employee": ("#f8fafc", "#475569", "#e2e8f0", "fa5s.user-tie"),
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
    border-radius: 8px;
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


NODE_W = 350
NODE_H = 98
H_GAP = 56
V_GAP = 98


class HierarchyCanvasView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QGraphicsView {
                background: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#f3f4f6"))
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        spacing = 22
        left = int(rect.left()) - (int(rect.left()) % spacing)
        top = int(rect.top()) - (int(rect.top()) % spacing)
        for x in range(left, int(rect.right()) + spacing, spacing):
            for y in range(top, int(rect.bottom()) + spacing, spacing):
                painter.drawPoint(x, y)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        next_scale = current * factor
        if 0.08 <= next_scale <= 2.5:
            self.scale(factor, factor)


class HierarchyNodeItem(QGraphicsItem):
    def __init__(self, data, expanded=False, selected=False, callbacks=None):
        super().__init__()
        self.data = data
        self.expanded = expanded
        self.selected = selected
        self.callbacks = callbacks or {}
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        subtitle = data.get("subtitle") or data.get("type", "")
        self.setToolTip(f"{data.get('name', '-')}\n{subtitle}")

    def boundingRect(self):
        return QRectF(0, 0, NODE_W, NODE_H)

    def paint(self, painter, option, widget=None):
        bg, fg, border, _ = TYPE_COLORS.get(
            self.data.get("type", "team"),
            ("#f9fafb", "#374151", "#e5e7eb", "fa5s.circle"),
        )
        painter.setPen(QPen(QColor("#2563eb" if self.selected else border), 2 if self.selected else 1))
        painter.setBrush(QBrush(QColor(bg)))
        painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 8, 8)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(14, 18, 34, 34), 8, 8)
        icon = qta.icon(self._icon_name(), color=fg)
        painter.drawPixmap(QRectF(21, 25, 20, 20).toRect(), icon.pixmap(20, 20))

        painter.setPen(QColor("#111827"))
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRectF(58, 15, 245, 24), Qt.AlignLeft | Qt.AlignVCenter, self._elide(painter, self.data.get("name", "-"), 245))

        painter.setPen(QColor("#4b5563"))
        meta_font = QFont()
        meta_font.setPointSize(8)
        painter.setFont(meta_font)
        meta = self.data.get("subtitle") or self.data.get("type", "").title()
        painter.drawText(QRectF(58, 40, 255, 18), Qt.AlignLeft | Qt.AlignVCenter, self._elide(painter, meta, 255))

        count_text = self.data.get("count_text", "")
        if count_text:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(QRectF(58, 66, 132, 18), 6, 6)
            painter.setPen(QColor(fg))
            painter.drawText(QRectF(58, 66, 132, 18), Qt.AlignCenter, count_text)

        if self.data.get("has_children"):
            painter.setPen(QPen(QColor("#cbd5e1"), 1))
            painter.setBrush(QBrush(QColor("#ffffff")))
            self.toggle_rect = QRectF(NODE_W - 38, 37, 24, 24)
            painter.drawRoundedRect(self.toggle_rect, 12, 12)
            painter.setPen(QPen(QColor("#374151"), 1.6, Qt.SolidLine, Qt.RoundCap))
            center = self.toggle_rect.center()
            painter.drawLine(QPointF(center.x() - 5, center.y()), QPointF(center.x() + 5, center.y()))
            if not self.expanded:
                painter.drawLine(QPointF(center.x(), center.y() - 5), QPointF(center.x(), center.y() + 5))
        else:
            self.toggle_rect = QRectF()

    def mousePressEvent(self, event):
        if self.toggle_rect.contains(event.pos()) and self.data.get("has_children"):
            callback = self.callbacks.get("toggle")
            if callback:
                callback(self.data["id"], self.data.get("kind", "unit"))
        else:
            callback = self.callbacks.get("select")
            if callback:
                callback(self.data)
        event.accept()

    def _icon_name(self):
        if self.data.get("kind") == "employee":
            return "fa5s.user-tie"
        return {
            "organization": "fa5s.building",
            "division": "fa5s.layer-group",
            "department": "fa5s.sitemap",
            "unit": "fa5s.briefcase",
            "team": "fa5s.users",
            "position": "fa5s.user-tie",
            "employee": "fa5s.user-tie",
        }.get(self.data.get("type"), "fa5s.circle")

    def _elide(self, painter, text, width):
        return painter.fontMetrics().elidedText(str(text), Qt.ElideRight, int(width))


class HierarchyPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.scene = QGraphicsScene(self)
        self.expanded = set()
        self.children_cache = {}
        self.selected_node = None
        self.node_items = {}
        self.edge_items = []
        self._did_initial_expand = False
        self.setObjectName("HierarchyPage")
        self.setStyleSheet("QWidget#HierarchyPage { background: #f9fafb; }")
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        title = QLabel(t("hierarchy_title"))
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel(t("hierarchy_subtitle"))
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)

        add_root = QPushButton("  " + t("add_unit"))
        add_root.setIcon(qta.icon("fa5s.plus", color="white"))
        add_root.setIconSize(QSize(14, 14))
        add_root.setCursor(Qt.PointingHandCursor)
        add_root.setFixedHeight(42)
        add_root.setStyleSheet(_primary_btn())
        add_root.clicked.connect(lambda: self._add_unit())
        header.addWidget(add_root)
        root.addLayout(header)

        toolbar = QFrame()
        toolbar.setObjectName("HierarchyToolbar")
        toolbar.setStyleSheet("QFrame#HierarchyToolbar { background: white; border: 1px solid #e5e7eb; border-radius: 8px; }")
        tools = QHBoxLayout(toolbar)
        tools.setContentsMargins(16, 14, 16, 14)
        tools.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_hierarchy"))
        self.search.setFixedHeight(40)
        self.search.setStyleSheet(INPUT_SS)
        self.search.addAction(qta.icon("fa5s.search", color="#9ca3af"), QLineEdit.LeadingPosition)
        self.search.returnPressed.connect(self._run_search)
        self.search.textChanged.connect(self._on_search_text_changed)
        tools.addWidget(self.search, 1)

        search_btn = QPushButton(t("search"))
        search_btn.setIcon(qta.icon("fa5s.search", color="#111827"))
        search_btn.setIconSize(QSize(13, 13))
        search_btn.setFixedHeight(40)
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.setStyleSheet(_outline_btn())
        search_btn.clicked.connect(self._run_search)
        tools.addWidget(search_btn)
        root.addWidget(toolbar)

        structure = QFrame()
        structure.setObjectName("HierarchyStructureHint")
        structure.setStyleSheet("QFrame#HierarchyStructureHint { background: transparent; border: none; }")
        structure_row = QHBoxLayout(structure)
        structure_row.setContentsMargins(2, 0, 2, 0)
        structure_row.setSpacing(8)
        for index, unit_type in enumerate(TYPE_ORDER_HINT):
            structure_row.addWidget(_hierarchy_step(unit_type))
            if index < len(TYPE_ORDER_HINT) - 1:
                arrow = QLabel()
                arrow.setPixmap(qta.icon("fa5s.chevron-right", color="#9ca3af").pixmap(9, 9))
                arrow.setStyleSheet("background: transparent; border: none;")
                structure_row.addWidget(arrow)
        structure_row.addStretch()
        root.addWidget(structure)

        body = QHBoxLayout()
        body.setSpacing(18)
        self.view = HierarchyCanvasView()
        self.view.setScene(self.scene)
        self.view.setMinimumHeight(620)

        canvas_shell = QWidget()
        canvas_shell.setStyleSheet("background: transparent;")
        canvas_grid = QGridLayout(canvas_shell)
        canvas_grid.setContentsMargins(0, 0, 0, 0)
        canvas_grid.setSpacing(0)
        canvas_grid.addWidget(self.view, 0, 0)
        canvas_controls = QFrame()
        canvas_controls.setObjectName("CanvasControls")
        canvas_controls.setStyleSheet("""
            QFrame#CanvasControls {
                background: rgba(255,255,255,235);
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                margin-top: 10px;
                margin-right: 10px;
            }
        """)
        controls_row = QHBoxLayout(canvas_controls)
        controls_row.setContentsMargins(8, 8, 8, 8)
        controls_row.setSpacing(6)
        for label, icon, handler in [
            ("Fit", "fa5s.expand-arrows-alt", self._fit_canvas),
            ("Reset", "fa5s.undo", self._reset_canvas),
            ("-", None, lambda: self._zoom(0.85)),
            ("+", None, lambda: self._zoom(1.15)),
        ]:
            btn = QPushButton(label)
            if icon:
                btn.setIcon(qta.icon(icon, color="#111827"))
                btn.setIconSize(QSize(12, 12))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_canvas_control_btn())
            btn.clicked.connect(handler)
            controls_row.addWidget(btn)
        canvas_grid.addWidget(canvas_controls, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)
        body.addWidget(canvas_shell, 1)

        self.inspector = self._build_inspector()
        body.addWidget(self.inspector)
        root.addLayout(body, 1)

    def _build_inspector(self):
        card = QFrame()
        card.setFixedWidth(320)
        card.setObjectName("HierarchyInspector")
        card.setStyleSheet("""
            QFrame#HierarchyInspector { background: white; border: 1px solid #e5e7eb; border-radius: 8px; }
            QFrame#HierarchyInspector QLabel { background: transparent; border: none; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        self.inspector_title = QLabel("Selected Node")
        self.inspector_title.setWordWrap(True)
        self.inspector_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #111827;")
        self.inspector_subtitle = QLabel("Select a unit or employee on the canvas.")
        self.inspector_subtitle.setWordWrap(True)
        self.inspector_subtitle.setStyleSheet("font-size: 13px; color: #6b7280;")
        layout.addWidget(self.inspector_title)
        layout.addWidget(self.inspector_subtitle)

        self.inspector_meta = QVBoxLayout()
        self.inspector_meta.setSpacing(10)
        layout.addLayout(self.inspector_meta)

        self.action_add = QPushButton("  Add Child Unit")
        self.action_add.setIcon(qta.icon("fa5s.plus", color="white"))
        self.action_add.setStyleSheet(_primary_btn())
        self.action_add.clicked.connect(self._add_child_from_selection)
        self.action_edit = QPushButton("  Edit Unit")
        self.action_edit.setIcon(qta.icon("fa5s.edit", color="#111827"))
        self.action_edit.setStyleSheet(_outline_btn())
        self.action_edit.clicked.connect(self._edit_selected_unit)
        self.action_view = QPushButton("  View Employees")
        self.action_view.setIcon(qta.icon("fa5s.user-friends", color="#111827"))
        self.action_view.setStyleSheet(_outline_btn())
        self.action_view.clicked.connect(self._view_selected_unit_employees)
        self.action_delete = QPushButton("  Delete Unit")
        self.action_delete.setIcon(qta.icon("fa5s.trash-alt", color="#dc2626"))
        self.action_delete.setStyleSheet(_danger_outline_btn())
        self.action_delete.clicked.connect(self._delete_selected_unit)
        for btn in [self.action_add, self.action_edit, self.action_view, self.action_delete]:
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
        layout.addStretch()
        self._sync_inspector()
        return card

    def refresh(self):
        self.children_cache.clear()
        self.selected_node = None
        self._render_initial()

    def _render_initial(self, preserve_view=False):
        view_state = self._capture_view_state() if preserve_view else None
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        query = self.search.text().strip()
        if query:
            self._render_search(query)
            return

        roots = self._load_children(None)
        if not roots:
            self._render_empty(t("no_org_units"))
            self._sync_inspector()
            return
        if not self._did_initial_expand:
            self.expanded.update(self._node_key(root) for root in roots)
            self._did_initial_expand = True
        self._layout_tree(roots)
        if view_state:
            self._restore_view_state(view_state)
        else:
            self.view.resetTransform()
            self.view.centerOn(self.scene.itemsBoundingRect().center())
        self._sync_inspector()

    def _layout_tree(self, roots):
        self.scene.clear()
        self.node_items.clear()
        positioned = []
        x_cursor = 0
        for root in roots:
            width = self._subtree_width(root)
            self._position_subtree(root, x_cursor + width / 2 - NODE_W / 2, 0, positioned)
            x_cursor += width + H_GAP

        if not positioned:
            return
        min_x = min(x for _, x, _ in positioned)
        for node, x, y in positioned:
            self._add_canvas_node(node, x - min_x + 40, y + 40)
        for node, x, y in positioned:
            if self._node_key(node) not in self.expanded:
                continue
            parent_item = self.node_items.get((node["kind"], node["id"]))
            child_items = []
            for child in self._load_children(node):
                child_item = self.node_items.get((child["kind"], child["id"]))
                if child_item:
                    child_items.append(child_item)
            if parent_item and child_items:
                self._draw_edges(parent_item, child_items)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-80, -80, 80, 80))

    def _subtree_width(self, node):
        if self._node_key(node) not in self.expanded:
            return NODE_W
        children = self._load_children(node)
        if not children:
            return NODE_W
        return max(NODE_W, sum(self._subtree_width(child) for child in children) + H_GAP * (len(children) - 1))

    def _position_subtree(self, node, x, y, positioned):
        positioned.append((node, x, y))
        if self._node_key(node) not in self.expanded:
            return
        children = self._load_children(node)
        if not children:
            return
        total_width = sum(self._subtree_width(child) for child in children) + H_GAP * (len(children) - 1)
        child_x = x + NODE_W / 2 - total_width / 2
        for child in children:
            width = self._subtree_width(child)
            self._position_subtree(child, child_x + width / 2 - NODE_W / 2, y + NODE_H + V_GAP, positioned)
            child_x += width + H_GAP

    def _add_canvas_node(self, node, x, y):
        item = HierarchyNodeItem(
            node,
            expanded=self._node_key(node) in self.expanded,
            selected=self.selected_node and self.selected_node.get("kind") == node["kind"] and self.selected_node.get("id") == node["id"],
            callbacks={"toggle": self._toggle_node, "select": self._select_node},
        )
        item.setPos(QPointF(x, y))
        self.scene.addItem(item)
        self.node_items[(node["kind"], node["id"])] = item

    def _draw_edges(self, parent_item, child_items):
        parent_pos = parent_item.pos()
        child_centers = [QPointF(item.pos().x() + NODE_W / 2, item.pos().y()) for item in child_items]
        parent_center = QPointF(parent_pos.x() + NODE_W / 2, parent_pos.y() + NODE_H)
        trunk_y = parent_center.y() + (child_centers[0].y() - parent_center.y()) / 2
        path = QPainterPath(parent_center)
        path.lineTo(QPointF(parent_center.x(), trunk_y))
        min_x = min(point.x() for point in child_centers)
        max_x = max(point.x() for point in child_centers)
        path.moveTo(QPointF(min_x, trunk_y))
        path.lineTo(QPointF(max_x, trunk_y))
        for child_center in child_centers:
            path.moveTo(QPointF(child_center.x(), trunk_y))
            path.lineTo(child_center)
        edge = QGraphicsPathItem(path)
        edge.setPen(QPen(QColor("#94a3b8"), 1.35))
        edge.setZValue(-1)
        self.scene.addItem(edge)
        self.edge_items.append(edge)

    def _draw_edge(self, parent_pos, child_pos):
        start = QPointF(parent_pos.x() + NODE_W / 2, parent_pos.y() + NODE_H)
        end = QPointF(child_pos.x() + NODE_W / 2, child_pos.y())
        mid_y = start.y() + (end.y() - start.y()) / 2
        path = QPainterPath(start)
        path.lineTo(QPointF(start.x(), mid_y))
        path.lineTo(QPointF(end.x(), mid_y))
        path.lineTo(end)
        edge = QGraphicsPathItem(path)
        edge.setPen(QPen(QColor("#94a3b8"), 1.5))
        edge.setZValue(-1)
        self.scene.addItem(edge)
        self.edge_items.append(edge)

    def _node_key(self, node):
        return (node.get("kind", "unit"), node["id"])

    def _capture_view_state(self):
        return self.view.transform(), self.view.mapToScene(self.view.viewport().rect().center())

    def _restore_view_state(self, view_state):
        transform, center = view_state
        self.view.setTransform(transform)
        self.view.centerOn(center)

    def _load_children(self, parent):
        parent_id = None if parent is None else parent["id"]
        cache_key = ("root", None) if parent is None else self._node_key(parent)
        if cache_key in self.children_cache:
            return self.children_cache[cache_key]
        session = get_session()
        try:
            if parent and parent.get("kind") == "employee":
                employees = (
                    session.query(Employee)
                    .filter_by(reports_to_id=parent_id, status="active")
                    .order_by(Employee.last_name, Employee.first_name)
                    .all()
                )
                data = [self._employee_to_node(session, employee) for employee in employees]
                self.children_cache[cache_key] = data
                return data
            if parent_id is None:
                organization = session.query(OrgUnit).filter(OrgUnit.unit_type == "organization").order_by(OrgUnit.id).first()
                if organization:
                    data = [self._unit_to_node(session, organization)]
                    self.children_cache[cache_key] = data
                    return data
                else:
                    query = session.query(OrgUnit).filter(OrgUnit.parent_id.is_(None))
            else:
                query = session.query(OrgUnit).filter(OrgUnit.parent_id == parent_id)
            units = query.order_by(OrgUnit.unit_type, OrgUnit.name).all()
            data = [self._unit_to_node(session, unit) for unit in units]
            if parent and parent.get("kind") == "unit" and not units:
                employees = self._leaf_unit_employees(session, parent_id, parent.get("head_employee_id"))
                data.extend(self._employee_to_node(session, employee) for employee in employees)
        finally:
            session.close()
        self.children_cache[cache_key] = data
        return data

    def _unit_to_node(self, session, unit):
        child_count = session.query(OrgUnit.id).filter_by(parent_id=unit.id).count()
        direct_people = session.query(Employee.id).filter_by(org_unit_id=unit.id, status="active").count()
        visible_people = self._leaf_unit_employee_count(session, unit) if child_count == 0 else 0
        head_name = unit.head.full_name if unit.head else "Unassigned"
        head_position = _display_position(unit.head.position) if unit.head and unit.head.position else unit.unit_type.title()
        count_text = self._unit_count_text(unit.unit_type, child_count, visible_people)
        return {
            "kind": "unit",
            "id": unit.id,
            "name": unit.name,
            "type": unit.unit_type,
            "parent_id": unit.parent_id,
            "subtitle": f"{head_name} - {head_position}" if unit.head else head_name,
            "head": head_name,
            "head_position": head_position,
            "head_employee_id": unit.head_employee_id,
            "child_count": child_count,
            "direct_people": direct_people,
            "visible_people": visible_people,
            "has_children": child_count > 0 or visible_people > 0,
            "count_text": count_text,
        }

    def _leaf_unit_employees(self, session, unit_id, head_employee_id):
        query = session.query(Employee).filter_by(org_unit_id=unit_id, status="active")
        if head_employee_id:
            direct_reports = (
                query
                .filter(Employee.reports_to_id == head_employee_id)
                .order_by(Employee.last_name, Employee.first_name)
                .all()
            )
            if direct_reports:
                return direct_reports
            query = query.filter(Employee.id != head_employee_id)
        return query.order_by(Employee.last_name, Employee.first_name).all()

    def _leaf_unit_employee_count(self, session, unit):
        if not unit.head_employee_id:
            return session.query(Employee.id).filter_by(org_unit_id=unit.id, status="active").count()
        direct_reports = (
            session.query(Employee.id)
            .filter_by(org_unit_id=unit.id, reports_to_id=unit.head_employee_id, status="active")
            .count()
        )
        if direct_reports:
            return direct_reports
        return (
            session.query(Employee.id)
            .filter(Employee.org_unit_id == unit.id, Employee.status == "active", Employee.id != unit.head_employee_id)
            .count()
        )

    def _unit_count_text(self, unit_type, child_count, direct_people):
        if direct_people:
            label = "member" if unit_type == "team" and direct_people == 1 else "members" if unit_type == "team" else "employee" if direct_people == 1 else "employees"
            return f"{direct_people} {label}"
        if child_count:
            singular, plural = NEXT_TYPE_LABEL.get(unit_type, ("child unit", "child units"))
            return f"{child_count} {singular if child_count == 1 else plural}"
        return ""

    def _toggle_node(self, node_id, kind="unit"):
        if kind not in {"unit", "employee"}:
            return
        key = (kind, node_id)
        if key in self.expanded:
            self.expanded.remove(key)
        else:
            self.expanded.add(key)
        self._render_initial(preserve_view=True)

    def _select_node(self, node):
        self.selected_node = node
        self._render_initial(preserve_view=True)
        self._sync_inspector()

    def _sync_inspector(self):
        while self.inspector_meta.count():
            item = self.inspector_meta.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        node = self.selected_node
        is_unit = bool(node and node.get("kind") == "unit")
        self.inspector_title.setText(node["name"] if node else "Selected Node")
        self.inspector_subtitle.setText((node.get("type", "").title() if is_unit else node.get("subtitle", "")) if node else "Select a unit or employee on the canvas.")
        if node:
            rows = [
                ("Type", node.get("type", node.get("kind", "-")).title()),
                ("Head", node.get("head", "-")),
                ("Direct employees", str(node.get("direct_people", "-"))),
                ("Child units", str(node.get("child_count", "-"))),
            ] if is_unit else [
                ("Employee ID", node.get("employee_id", "-")),
                ("Position", node.get("position", "-")),
                ("Level", node.get("level", "-")),
                ("Direct reports", str(node.get("child_count", 0))),
            ]
            for label, value in rows:
                self.inspector_meta.addWidget(_meta_row(label, value))
        for btn in [self.action_add, self.action_edit, self.action_view, self.action_delete]:
            btn.setVisible(is_unit)

    def _run_search(self):
        self.expanded.clear()
        self._render_initial()

    def _on_search_text_changed(self):
        if not self.search.text().strip():
            self.refresh()

    def _render_search(self, query):
        self.scene.clear()
        self.node_items.clear()
        result = self._search_context(query)
        if not result:
            self._render_empty(t("no_matching_org_units"))
            self._sync_inspector()
            return
        nodes, edges = result
        y_step = NODE_H + 54
        x_center = 360
        for index, node in enumerate(nodes):
            if node.get("relation") == "report":
                continue
            self._add_canvas_node(node, x_center, 50 + index * y_step)
        report_nodes = [node for node in nodes if node.get("relation") == "report"]
        start_x = max(40, x_center - ((len(report_nodes) - 1) * (NODE_W + 34)) / 2)
        report_y = 50 + (len(nodes) - len(report_nodes)) * y_step
        for idx, node in enumerate(report_nodes[:4]):
            self._add_canvas_node(node, start_x + idx * (NODE_W + 34), report_y)
        for parent_key, child_key in edges:
            parent = self.node_items.get(parent_key)
            child = self.node_items.get(child_key)
            if parent and child:
                self._draw_edge(parent.pos(), child.pos())
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-80, -80, 80, 80))
        self.view.resetTransform()
        self.view.centerOn(self.scene.itemsBoundingRect().center())
        self._sync_inspector()

    def _search_context(self, query):
        session = get_session()
        try:
            pattern = f"%{query}%"
            employee = (
                session.query(Employee)
                .filter((Employee.first_name + " " + Employee.last_name).like(pattern) | Employee.employee_id.like(pattern))
                .order_by(Employee.id)
                .first()
            )
            if employee:
                return self._employee_context(session, employee)
            unit = session.query(OrgUnit).filter(OrgUnit.name.like(pattern)).order_by(OrgUnit.id).first()
            if unit:
                return self._unit_context(session, unit)
            return None
        finally:
            session.close()

    def _employee_context(self, session, employee):
        chain = []
        current = employee
        seen = set()
        while current and current.id not in seen:
            seen.add(current.id)
            chain.append(self._employee_to_node(session, current))
            current = current.reports_to
        chain.reverse()
        report_query = session.query(Employee).filter_by(reports_to_id=employee.id, status="active")
        total_reports = report_query.count()
        reports = report_query.order_by(Employee.first_name, Employee.last_name).limit(4).all()
        report_nodes = [self._employee_to_node(session, report, relation="report") for report in reports]
        if total_reports > len(report_nodes):
            report_nodes.append({
                "kind": "employee",
                "id": -employee.id,
                "name": f"+{total_reports - len(report_nodes)} more direct reports",
                "type": "employee",
                "subtitle": "Grouped reports",
                "child_count": 0,
                "has_children": False,
                "relation": "report",
                "count_text": "",
            })
        nodes = chain + report_nodes
        edges = []
        for parent, child in zip(chain, chain[1:]):
            edges.append((("employee", parent["id"]), ("employee", child["id"])))
        for report in report_nodes:
            edges.append((("employee", employee.id), ("employee", report["id"])))
        self.selected_node = chain[-1] if chain else None
        return nodes, edges

    def _unit_context(self, session, unit):
        chain = []
        current = unit
        while current:
            chain.append(self._unit_to_node(session, current))
            current = current.parent
        chain.reverse()
        child_units = session.query(OrgUnit).filter_by(parent_id=unit.id).order_by(OrgUnit.name).limit(4).all()
        children = [self._unit_to_node(session, child) for child in child_units]
        if not child_units:
            employees = self._leaf_unit_employees(session, unit.id, unit.head_employee_id)[:4]
            children.extend(self._employee_to_node(session, employee) for employee in employees)
        for child in children:
            child["relation"] = "report"
        nodes = chain + children
        edges = []
        for parent, child in zip(chain, chain[1:]):
            edges.append((("unit", parent["id"]), ("unit", child["id"])))
        for child in children:
            edges.append((("unit", unit.id), ("unit", child["id"])))
        self.selected_node = chain[-1] if chain else None
        return nodes, edges

    def _employee_to_node(self, session, employee, relation=None):
        direct_reports = session.query(Employee.id).filter_by(reports_to_id=employee.id, status="active").count()
        return {
            "kind": "employee",
            "id": employee.id,
            "name": employee.full_name,
            "type": "employee",
            "employee_id": employee.employee_id,
            "position": employee.position or "-",
            "level": employee.title.name if employee.title else "-",
            "subtitle": _display_position(employee.position) if employee.position else employee.employee_id,
            "child_count": direct_reports,
            "has_children": direct_reports > 0,
            "relation": relation,
            "count_text": f"{direct_reports} reports" if direct_reports else "",
        }

    def _render_empty(self, text):
        self.scene.clear()
        label = self.scene.addText(text)
        label.setDefaultTextColor(QColor("#6b7280"))
        label.setPos(40, 40)
        self.scene.setSceneRect(QRectF(0, 0, 600, 320))

    def _fit_canvas(self):
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-80, -80, 80, 80), Qt.KeepAspectRatio)

    def _reset_canvas(self):
        self.view.resetTransform()
        if self.scene.items():
            self.view.centerOn(self.scene.sceneRect().center())

    def _zoom(self, factor):
        current = self.view.transform().m11()
        next_scale = current * factor
        if 0.08 <= next_scale <= 2.5:
            self.view.scale(factor, factor)

    def _add_child_from_selection(self):
        if self.selected_node and self.selected_node.get("kind") == "unit":
            self._add_unit(parent_id=self.selected_node["id"])

    def _edit_selected_unit(self):
        if self.selected_node and self.selected_node.get("kind") == "unit":
            self._edit_unit(self.selected_node["id"])

    def _view_selected_unit_employees(self):
        if self.selected_node and self.selected_node.get("kind") == "unit":
            self._show_unit_employees(self.selected_node["id"])

    def _delete_selected_unit(self):
        if self.selected_node and self.selected_node.get("kind") == "unit":
            self._delete_unit(self.selected_node["id"])

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
            emp_count = session.query(Employee).filter_by(org_unit_id=unit_id).count()
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
        self.table.setShowGrid(False)
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


def _hierarchy_step(unit_type):
    bg, fg, border, icon = TYPE_COLORS.get(unit_type, TYPE_COLORS["employee"])
    label = "Employee" if unit_type == "employee" else unit_type.title()
    pill = QFrame()
    pill.setObjectName("HierarchyStep")
    pill.setStyleSheet(f"""
        QFrame#HierarchyStep {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QFrame#HierarchyStep QLabel {{
            background: transparent;
            border: none;
        }}
    """)
    row = QHBoxLayout(pill)
    row.setContentsMargins(10, 5, 10, 5)
    row.setSpacing(7)
    icon_lbl = QLabel()
    icon_lbl.setPixmap(qta.icon(icon, color=fg).pixmap(12, 12))
    icon_lbl.setStyleSheet("background: transparent; border: none;")
    text_lbl = QLabel(label)
    text_lbl.setStyleSheet(f"background: transparent; border: none; color: {fg}; font-size: 12px; font-weight: 800;")
    row.addWidget(icon_lbl)
    row.addWidget(text_lbl)
    return pill


def _display_position(position):
    if not position:
        return ""
    normalized = position.strip().lower()
    abbreviations = {
        "chief executive officer": "CEO",
        "chief technology officer": "CTO",
        "chief operating officer": "COO",
        "chief financial officer": "CFO",
        "chief human resources officer": "CHRO",
        "vice president": "VP",
    }
    return abbreviations.get(normalized, position)


def _meta_row(label, value):
    row = QFrame()
    row.setStyleSheet("QFrame { background: #f9fafb; border: 1px solid #eef2f7; border-radius: 8px; }")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(10)
    label_widget = QLabel(label)
    label_widget.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent; border: none;")
    value_widget = QLabel(str(value))
    value_widget.setWordWrap(True)
    value_widget.setStyleSheet("font-size: 13px; color: #111827; font-weight: 700; background: transparent; border: none;")
    layout.addWidget(label_widget)
    layout.addStretch()
    layout.addWidget(value_widget)
    return row


def _form_label(text):
    label = QLabel(text)
    label.setMinimumWidth(122)
    label.setStyleSheet("font-size: 14px; color: #111827; background: transparent; border: none;")
    return label


def _prepare_combo(combo):
    combo.setMinimumWidth(390)
    combo.view().setMinimumWidth(390)
    combo.view().setTextElideMode(Qt.ElideNone)
    polish_combo_box(combo, max_visible_items=8, popup_min_width=390)


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


def _canvas_control_btn():
    return "QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 7px; padding: 0 10px; font-size: 12px; font-weight: 800; min-width: 32px; } QPushButton:hover { background: #f3f4f6; border-color: #cbd5e1; }"


def _danger_outline_btn():
    return "QPushButton { background: white; color: #dc2626; border: 1px solid #fecaca; border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 700; min-height: 36px; } QPushButton:hover { background: #fef2f2; }"
