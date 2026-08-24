"""Shared QSS constants matching the MockUI design system."""

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import QAbstractItemView, QFrame

# Colors
CLR_BG = "#f9fafb"
CLR_WHITE = "white"
CLR_PRIMARY = "#030213"
CLR_BLUE = "#2563eb"
CLR_BLUE_DARK = "#1d4ed8"
CLR_BORDER = "#e5e7eb"
CLR_TEXT = "#111827"
CLR_TEXT_MUTED = "#6b7280"
CLR_TEXT_LIGHT = "#9ca3af"
CLR_INPUT_BG = "#f3f3f5"
CLR_ROW_HOVER = "#f9fafb"
TABLE_ROW_BG = "white"
TABLE_ROW_HOVER_BG = "#f8fafc"
TABLE_ROW_SELECTED_BG = "#eff6ff"

# Buttons
BTN_PRIMARY = """
QPushButton {{
    background: #030213;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 16px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: #1a1d2e; }}
QPushButton:pressed {{ background: #111827; }}
QPushButton:disabled {{ background: #9ca3af; color: white; }}
"""

BTN_BLUE = """
QPushButton {{
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 16px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: #1d4ed8; }}
QPushButton:pressed {{ background: #1e40af; }}
"""

BTN_OUTLINE = """
QPushButton {{
    background: white;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    padding: 0 12px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: #f3f4f6; color: #111827; }}
QPushButton:pressed {{ background: #e5e7eb; }}
"""

BTN_GHOST = """
QPushButton {{
    background: #f9fafb;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 12px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: #f3f4f6; color: #111827; border-color: #d1d5db; }}
"""

BTN_DANGER = """
QPushButton {{
    background: #fee2e2;
    color: #dc2626;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 16px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: #fecaca; }}
"""


def btn_primary(h=36):
    return BTN_PRIMARY.format(h=h)


def btn_blue(h=36):
    return BTN_BLUE.format(h=h)


def btn_outline(h=36):
    return BTN_OUTLINE.format(h=h)


def btn_ghost(h=36):
    return BTN_GHOST.format(h=h)


def btn_danger(h=36):
    return BTN_DANGER.format(h=h)


# Inputs
INPUT_SS = """
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit,
QSpinBox, QDoubleSpinBox {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    min-height: 36px;
    selection-background-color: #2563eb;
    outline: none;
}
QTextEdit, QPlainTextEdit {
    padding: 8px 12px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2563eb;
    background: white;
}
QComboBox {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 32px 0 12px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    min-height: 36px;
    outline: none;
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
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    selection-background-color: #eff6ff;
    selection-color: #111827;
    outline: none;
    padding: 4px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0;
    border: none;
}
"""

# Tables
TABLE_SS = """
QTableWidget {
    background: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 14px;
    color: #111827;
    outline: none;
    selection-background-color: #eff6ff;
}
QTableWidget::item {
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
}
QTableWidget::item:selected {
    background: #eff6ff;
    color: #111827;
}
QTableWidget::item:hover {
    background: #f8fafc;
}
QHeaderView::section {
    background: #f9fafb;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 12px;
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    min-height: 40px;
}
QTableCornerButton::section {
    background: #f9fafb;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}
"""


def table_cell_widget_ss(background=TABLE_ROW_BG):
    return (
        f"QWidget#TableCellWidget {{ background: {background}; border: none; }}"
        "QWidget#TableCellWidget QLabel { background: transparent; border: none; }"
    )


def prepare_table_cell_widget(widget, background=TABLE_ROW_BG):
    widget.setObjectName("TableCellWidget")
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setStyleSheet(table_cell_widget_ss(background))
    return widget


def sync_table_widget_cells(table, selected_bg=TABLE_ROW_SELECTED_BG):
    for row in range(table.rowCount()):
        selected = table.selectionModel().isRowSelected(row, table.rootIndex())
        bg = selected_bg if selected else TABLE_ROW_BG
        for col in range(table.columnCount()):
            widget = table.cellWidget(row, col)
            if widget and widget.objectName() == "TableCellWidget":
                widget.setStyleSheet(table_cell_widget_ss(bg))


def enable_table_row_selection(table, selected_bg=TABLE_ROW_SELECTED_BG):
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setMouseTracking(True)
    table.setShowGrid(False)
    if getattr(table, "_myhr_selection_sync_installed", False):
        return
    table.itemSelectionChanged.connect(lambda: sync_table_widget_cells(table, selected_bg))
    table._myhr_selection_sync_installed = True

# Cards. The QLabel rule prevents frame borders from appearing around text.
CARD_SS = """
QFrame {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame QLabel {
    border: none;
    background: transparent;
}
"""

# Page scroll area
SCROLL_SS = """
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 5px;
    min-height: 32px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    border: none;
    background: transparent;
}
"""

# Tabs
TAB_SS = """
QTabWidget::pane {
    border: none;
    background: #f9fafb;
}
QTabBar::tab {
    background: transparent;
    color: #6b7280;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #030213;
    border-bottom: 2px solid #030213;
    font-weight: 600;
}
QTabBar::tab:hover {
    color: #111827;
}
"""


PILL_TAB_SS = """
QTabWidget::pane {
    border: none;
    background: #f9fafb;
    margin-top: 26px;
}
QTabBar {
    background: #e8ebf0;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 5px;
}
QTabBar::tab {
    background: transparent;
    color: #030213;
    border: none;
    border-radius: 13px;
    padding: 7px 16px;
    margin: 4px 2px;
    min-height: 24px;
    font-size: 14px;
    font-weight: 800;
}
QTabBar::tab:selected {
    background: white;
    border: 1px solid #f8fafc;
    color: #030213;
}
QTabBar::tab:hover {
    background: #f3f4f6;
}
"""


def badge_ss(bg, fg):
    return (
        f"background: {bg}; color: {fg}; border: none; border-radius: 4px; "
        "padding: 2px 8px; font-size: 11px; font-weight: 600;"
    )


BADGE_BLUE = badge_ss("#dbeafe", "#1e40af")
BADGE_GREEN = badge_ss("#dcfce7", "#166534")
BADGE_YELLOW = badge_ss("#fef9c3", "#854d0e")
BADGE_RED = badge_ss("#fee2e2", "#991b1b")
BADGE_GRAY = badge_ss("#f3f4f6", "#374151")


COMBO_POPUP_VIEW_SS = """
QListView {
    background: white;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}
QListView::item {
    min-height: 30px;
    padding: 6px 10px;
    background: white;
    color: #111827;
    border-radius: 6px;
}
QListView::item:selected,
QListView::item:hover {
    background: #eff6ff;
    color: #111827;
}
QListView::item:disabled {
    background: #fef2f2;
    color: #991b1b;
}
"""


EMPLOYEE_PICKER_LIST_SS = """
QListWidget {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    min-height: 40px;
    padding: 8px 10px;
    border-radius: 7px;
    color: #111827;
}
QListWidget::item:hover {
    background: #f8fafc;
}
QListWidget::item:selected {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
}
QListWidget::item:disabled {
    background: #fef2f2;
    color: #991b1b;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    border: none;
}
"""


def employee_picker_row_ss(*, enabled=True, selected=False):
    if not enabled:
        return (
            "QFrame#EmployeePickerRow { background: #fef2f2; border: 1px solid #fecaca; "
            "border-radius: 8px; }"
            "QFrame#EmployeePickerRow:hover { background: #fee2e2; }"
        )
    if selected:
        return (
            "QFrame#EmployeePickerRow { background: #eff6ff; border: 1px solid #2563eb; "
            "border-radius: 8px; }"
        )
    return (
        "QFrame#EmployeePickerRow { background: white; border: 1px solid transparent; "
        "border-radius: 8px; }"
        "QFrame#EmployeePickerRow:hover { background: #f8fafc; border-color: #e5e7eb; }"
    )


def employee_picker_checkbox_ss(enabled=True):
    color = "#991b1b" if not enabled else "#111827"
    return f"""
        QCheckBox {{
            background: transparent;
            color: {color};
            font-size: 12px;
            font-weight: 600;
            spacing: 10px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            background: white;
        }}
        QCheckBox::indicator:checked {{
            background: #2563eb;
            border-color: #2563eb;
        }}
        QCheckBox::indicator:disabled {{
            background: #fee2e2;
            border-color: #fca5a5;
        }}
    """


class _ComboPopupMask(QObject):
    def __init__(self, combo, radius=8):
        super().__init__(combo)
        self.combo = combo
        self.radius = radius

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Show, QEvent.Resize):
            self._apply_mask()
        return super().eventFilter(obj, event)

    def _apply_mask(self):
        view = self.combo.view()
        popup = view.window()
        path = QPainterPath()
        path.addRoundedRect(QRectF(popup.rect()).adjusted(0, 0, -1, -1), self.radius, self.radius)
        popup.setMask(QRegion(path.toFillPolygon().toPolygon()))


def polish_combo_box(combo, *, max_visible_items=12, popup_min_width=None):
    """Make combo popups use the same rounded, clean dropdown treatment."""
    combo.setMaxVisibleItems(max_visible_items)
    view = combo.view()

    if popup_min_width is not None:
        view.setMinimumWidth(popup_min_width)

    view.setFrameShape(QFrame.NoFrame)
    view.setTextElideMode(Qt.ElideNone)
    view.setAttribute(Qt.WA_StyledBackground, True)
    view.setStyleSheet(COMBO_POPUP_VIEW_SS)

    popup = view.window()
    popup.setAttribute(Qt.WA_TranslucentBackground, True)
    popup.setStyleSheet("background: transparent; border: none;")

    mask = _ComboPopupMask(combo)
    view.installEventFilter(mask)
    popup.installEventFilter(mask)
    combo._myhr_combo_popup_mask = mask
    return combo
