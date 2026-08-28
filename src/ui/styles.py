"""Shared QSS constants matching the MockUI design system."""

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import QAbstractItemView, QFrame, QMessageBox

from src.ui.theme import THEME_DARK, tokens

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
    t = tokens()
    text = "#062f28" if t.name == THEME_DARK else "#ffffff"
    return f"""
QPushButton {{
    background: {t.brand};
    color: {text};
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 16px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: {t.brand_hover}; }}
QPushButton:pressed {{ background: {t.brand}; }}
QPushButton:disabled {{ background: {t.border_strong}; color: {t.text_soft}; }}
"""


def btn_blue(h=36):
    return btn_primary(h)


def btn_outline(h=36):
    t = tokens()
    return f"""
QPushButton {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    padding: 0 12px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: {t.hover}; color: {t.text}; border-color: {t.border_strong}; }}
QPushButton:pressed {{ background: {t.surface_muted}; }}
"""


def btn_ghost(h=36):
    t = tokens()
    return f"""
QPushButton {{
    background: {t.surface_muted};
    color: {t.text_muted};
    border: 1px solid {t.border};
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 12px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: {t.hover}; color: {t.text}; border-color: {t.border_strong}; }}
"""


def btn_danger(h=36):
    t = tokens()
    return f"""
QPushButton {{
    background: {t.danger_soft};
    color: {t.danger};
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 0 16px;
    min-height: {h}px;
    outline: none;
}}
QPushButton:hover {{ background: {t.danger_soft}; border: 1px solid {t.danger}; }}
"""


def input_style(min_height=36):
    t = tokens()
    return f"""
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit,
QSpinBox, QDoubleSpinBox {{
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 12px;
    font-size: 14px;
    color: {t.text};
    background: {t.input};
    min-height: {min_height}px;
    selection-background-color: {t.selected};
    selection-color: {t.text};
    outline: none;
}}
QTextEdit, QPlainTextEdit {{
    padding: 8px 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.brand};
    background: {t.surface};
}}
QComboBox {{
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 32px 0 12px;
    font-size: 14px;
    color: {t.text};
    background: {t.input};
    min-height: {min_height}px;
    outline: none;
}}
QComboBox:focus {{
    border-color: {t.brand};
    background: {t.surface};
}}
QComboBox::drop-down {{
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox QAbstractItemView {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: 8px;
    selection-background-color: {t.selected};
    selection-color: {t.text};
    outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0;
    border: none;
}}
"""


def combo_style(min_height=36):
    return input_style(min_height)


INPUT_SS = input_style()

# Tables
def table_style(
    *,
    selected_bg=TABLE_ROW_SELECTED_BG,
    hover_bg=TABLE_ROW_HOVER_BG,
    header_bg="white",
    header_color=CLR_PRIMARY,
    header_font_size=13,
    header_weight=800,
    header_height=48,
    row_font_size=14,
    item_padding=12,
):
    t = tokens()
    selected_bg = selected_bg if t.name != THEME_DARK else t.selected
    hover_bg = hover_bg if t.name != THEME_DARK else t.hover
    header_bg = header_bg if header_bg != "white" or t.name != THEME_DARK else t.surface
    header_color = header_color if t.name != THEME_DARK else t.text
    return """
QTableWidget {{
    background: {surface};
    alternate-background-color: {surface};
    border: none;
    gridline-color: {border};
    font-size: {row_font_size}px;
    color: {text};
    outline: none;
    selection-background-color: {selected_bg};
}}
QTableWidget::item {{
    background: {surface};
    padding: 0 {item_padding}px;
    border: none;
    border-bottom: 1px solid {border};
    color: {text};
}}
QTableWidget::item:selected {{
    background: {selected_bg};
    color: {text};
}}
QTableWidget::item:hover {{
    background: {hover_bg};
}}
QHeaderView {{
    background: {header_bg};
    border: none;
}}
QHeaderView::section {{
    background: {header_bg};
    border: none;
    border-bottom: 1px solid {border};
    padding: 0 {item_padding}px;
    font-size: {header_font_size}px;
    font-weight: {header_weight};
    color: {header_color};
    min-height: {header_height}px;
}}
QTableCornerButton::section {{
    background: {header_bg};
    border: none;
    border-bottom: 1px solid {border};
}}
QScrollBar:vertical {{
    background: transparent;
    border: none;
    width: 7px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border_strong};
    border: none;
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {text_soft};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    background: transparent;
    border: none;
    height: 0;
    width: 0;
}}
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {{
    background: transparent;
    border: none;
    width: 0;
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
}}
""".format(
        surface=t.surface,
        border=t.border,
        border_strong=t.border_strong,
        text=t.text,
        text_soft=t.text_soft,
        selected_bg=selected_bg,
        hover_bg=hover_bg,
        header_bg=header_bg,
        header_color=header_color,
        header_font_size=header_font_size,
        header_weight=header_weight,
        header_height=header_height,
        row_font_size=row_font_size,
        item_padding=item_padding,
    )


TABLE_SS = table_style()
SANCTION_TABLE_SS = table_style(selected_bg="#fef2f2", hover_bg="#fff7f7")


def pager_button_ss():
    t = tokens()
    return (
        f"QPushButton {{ background: {t.surface}; color: {t.text}; border: 1px solid {t.border_strong};"
        " border-radius: 6px; font-size: 13px; font-weight: 700; padding: 0 14px; }"
        f" QPushButton:hover {{ background: {t.hover}; }}"
        f" QPushButton:disabled {{ color: {t.text_soft}; background: {t.surface_muted}; }}"
    )


PAGER_BUTTON_SS = pager_button_ss()


def message_box_ss():
    t = tokens()
    default_text = "#062f28" if t.name == THEME_DARK else "#ffffff"
    return f"""
QMessageBox {{ background: {t.surface}; color: {t.text}; }}
QMessageBox QLabel {{ color: {t.text}; background: transparent; font-size: 13px; }}
QPushButton {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {t.hover}; }}
QPushButton:default {{ background: {t.brand}; color: {default_text}; border: none; }}
"""


MESSAGE_BOX_SS = message_box_ss()


def show_message_box(parent, icon, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    t = tokens()
    default_text = "#062f28" if t.name == THEME_DARK else "#ffffff"
    box.setStyleSheet(f"""
QMessageBox {{ background: {t.surface}; color: {t.text}; }}
QMessageBox QLabel {{ color: {t.text}; background: transparent; font-size: 13px; }}
QPushButton {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {t.hover}; }}
QPushButton:default {{ background: {t.brand}; color: {default_text}; border: none; }}
""")
    return box.exec()


def message_warning(parent, title, text):
    return show_message_box(parent, QMessageBox.Warning, title, text)


def message_critical(parent, title, text):
    return show_message_box(parent, QMessageBox.Critical, title, text)


def message_information(parent, title, text):
    return show_message_box(parent, QMessageBox.Information, title, text)


def message_question(parent, title, text, default_button=QMessageBox.Yes):
    return show_message_box(
        parent,
        QMessageBox.Question,
        title,
        text,
        QMessageBox.Yes | QMessageBox.No,
        default_button,
    )


def table_cell_widget_ss(background=TABLE_ROW_BG):
    if background == TABLE_ROW_BG:
        background = tokens().surface
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
        bg = selected_bg if selected else tokens().surface
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
def card_ss(object_name: str = "QFrame"):
    t = tokens()
    return f"""
{object_name} {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 8px;
}}
{object_name} QLabel {{
    border: none;
    background: transparent;
}}
"""

CARD_SS = card_ss()

# Page scroll area
def scroll_ss(background: str | None = None):
    t = tokens()
    bg = background or "transparent"
    return f"""
QScrollArea {{
    border: none;
    background: {bg};
}}
QScrollArea > QWidget > QWidget {{
    background: {bg};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border_strong};
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.text_soft};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
    background: transparent;
}}
"""

SCROLL_SS = scroll_ss()

# Tabs
def tab_ss():
    t = tokens()
    return f"""
QTabWidget::pane {{
    border: none;
    background: {t.canvas};
}}
QTabBar::tab {{
    background: transparent;
    color: {t.text_muted};
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {t.brand};
    border-bottom: 2px solid {t.brand};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {t.text};
}}
"""

TAB_SS = tab_ss()

def pill_tab_ss():
    t = tokens()
    selected_text = "#062f28" if t.name == THEME_DARK else t.text
    return f"""
QTabWidget::pane {{
    border: none;
    background: {t.canvas};
    margin-top: 26px;
}}
QTabBar {{
    background: {t.surface_muted};
    border: 1px solid {t.border};
    border-radius: 18px;
    padding: 5px;
}}
QTabBar::tab {{
    background: transparent;
    color: {t.text};
    border: none;
    border-radius: 13px;
    padding: 7px 16px;
    margin: 4px 2px;
    min-height: 24px;
    font-size: 14px;
    font-weight: 800;
}}
QTabBar::tab:selected {{
    background: {t.surface};
    border: 1px solid {t.border};
    color: {selected_text};
}}
QTabBar::tab:hover {{
    background: {t.hover};
}}
"""

PILL_TAB_SS = pill_tab_ss()


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


def combo_popup_view_ss():
    t = tokens()
    return f"""
QListView {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: 8px;
    outline: none;
    padding: 4px;
}}
QListView::item {{
    min-height: 30px;
    padding: 6px 10px;
    background: {t.surface};
    color: {t.text};
    border-radius: 6px;
}}
QListView::item:selected,
QListView::item:hover {{
    background: {t.selected};
    color: {t.text};
}}
QListView::item:disabled {{
    background: {t.danger_soft};
    color: {t.danger};
}}
"""

COMBO_POPUP_VIEW_SS = combo_popup_view_ss()

def employee_picker_list_ss():
    t = tokens()
    return f"""
QListWidget {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    min-height: 40px;
    padding: 8px 10px;
    border-radius: 7px;
    color: {t.text};
}}
QListWidget::item:hover {{
    background: {t.hover};
}}
QListWidget::item:selected {{
    background: {t.selected};
    color: {t.brand};
    border: 1px solid {t.brand};
}}
QListWidget::item:disabled {{
    background: {t.danger_soft};
    color: {t.danger};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t.border_strong};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}
"""

EMPLOYEE_PICKER_LIST_SS = employee_picker_list_ss()


def employee_picker_row_ss(*, enabled=True, selected=False):
    t = tokens()
    if not enabled:
        return (
            f"QFrame#EmployeePickerRow {{ background: {t.danger_soft}; border: 1px solid {t.danger}; "
            "border-radius: 8px; }"
            f"QFrame#EmployeePickerRow:hover {{ background: {t.danger_soft}; }}"
        )
    if selected:
        return (
            f"QFrame#EmployeePickerRow {{ background: {t.selected}; border: 1px solid {t.brand}; "
            "border-radius: 8px; }"
        )
    return (
        f"QFrame#EmployeePickerRow {{ background: {t.surface}; border: 1px solid transparent; "
        "border-radius: 8px; }"
        f"QFrame#EmployeePickerRow:hover {{ background: {t.hover}; border-color: {t.border}; }}"
    )


def employee_picker_checkbox_ss(enabled=True):
    t = tokens()
    color = t.danger if not enabled else t.text
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
            border: 1px solid {t.border_strong};
            border-radius: 4px;
            background: {t.surface};
        }}
        QCheckBox::indicator:checked {{
            background: {t.brand};
            border-color: {t.brand};
        }}
        QCheckBox::indicator:disabled {{
            background: {t.danger_soft};
            border-color: {t.danger};
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
    view.setStyleSheet(combo_popup_view_ss())

    popup = view.window()
    popup.setAttribute(Qt.WA_TranslucentBackground, True)
    popup.setStyleSheet("background: transparent; border: none;")

    mask = _ComboPopupMask(combo)
    view.installEventFilter(mask)
    popup.installEventFilter(mask)
    combo._myhr_combo_popup_mask = mask
    return combo
