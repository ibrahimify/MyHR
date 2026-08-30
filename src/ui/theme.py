from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


THEME_LIGHT = "light"
THEME_DARK = "dark"
_SETTINGS_KEY = "ui/theme"


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    canvas: str
    sidebar: str
    surface: str
    surface_raised: str
    surface_muted: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    text_soft: str
    brand: str
    brand_hover: str
    brand_accent: str
    brand_soft: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    input: str
    hover: str
    selected: str
    tooltip_bg: str
    tooltip_fg: str


LIGHT = ThemeTokens(
    name=THEME_LIGHT,
    canvas="#f7f7f6",
    sidebar="#f1f1f0",
    surface="#ffffff",
    surface_raised="#ffffff",
    surface_muted="#f3f4f3",
    border="#e4e4e2",
    border_strong="#d5d7d3",
    text="#111311",
    text_muted="#565b56",
    text_soft="#7b7b7b",
    brand="#062f28",
    brand_hover="#0b4238",
    brand_accent="#9fe870",
    brand_soft="#eaf8dd",
    success="#0f7a45",
    success_soft="#dcfce7",
    warning="#b77905",
    warning_soft="#fef3c7",
    danger="#c92323",
    danger_soft="#fee2e2",
    input="#f0f1f0",
    hover="#ecefed",
    selected="#e2f5d0",
    tooltip_bg="#111311",
    tooltip_fg="#ffffff",
)

DARK = ThemeTokens(
    name=THEME_DARK,
    canvas="#050505",
    sidebar="#080808",
    surface="#101010",
    surface_raised="#151515",
    surface_muted="#181818",
    border="#242424",
    border_strong="#303030",
    text="#f4f4f2",
    text_muted="#b7bbb5",
    text_soft="#858a84",
    brand="#9fe870",
    brand_hover="#b5f090",
    brand_accent="#9fe870",
    brand_soft="#1e3320",
    success="#9fe870",
    success_soft="#1e3320",
    warning="#f0b84f",
    warning_soft="#33260d",
    danger="#ff6b6b",
    danger_soft="#351616",
    input="#181818",
    hover="#1d1d1d",
    selected="#1e3320",
    tooltip_bg="#f4f4f2",
    tooltip_fg="#050505",
)


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._settings = QSettings("MyHR", "MyHR")
        self._theme = self._normalize(self._settings.value(_SETTINGS_KEY, THEME_LIGHT))

    @staticmethod
    def _normalize(value) -> str:
        value = str(value or THEME_LIGHT).lower()
        return THEME_DARK if value == THEME_DARK else THEME_LIGHT

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def tokens(self) -> ThemeTokens:
        return DARK if self._theme == THEME_DARK else LIGHT

    def set_theme(self, theme: str, *, persist: bool = True) -> None:
        theme = self._normalize(theme)
        if theme == self._theme:
            return
        self._theme = theme
        if persist:
            self._settings.setValue(_SETTINGS_KEY, theme)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app)
        self.theme_changed.emit(theme)

    def toggle(self) -> None:
        self.set_theme(THEME_DARK if self._theme == THEME_LIGHT else THEME_LIGHT)


theme_manager = ThemeManager()


def tokens() -> ThemeTokens:
    return theme_manager.tokens


def is_dark() -> bool:
    return theme_manager.theme == THEME_DARK


def icon_color(*, selected: bool = False, muted: bool = False, danger: bool = False) -> str:
    t = tokens()
    if danger:
        return t.danger
    if selected:
        return t.brand
    return t.text_soft if muted else t.text_muted


def apply_theme(app: QApplication, arrow_path: str | None = None) -> None:
    t = tokens()
    app.setProperty("myhr_theme", t.name)

    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    palette = app.palette()
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        palette.setColor(group, QPalette.Window, QColor(t.canvas))
        palette.setColor(group, QPalette.Base, QColor(t.surface))
        palette.setColor(group, QPalette.AlternateBase, QColor(t.surface_muted))
        palette.setColor(group, QPalette.Text, QColor(t.text))
        palette.setColor(group, QPalette.WindowText, QColor(t.text))
        palette.setColor(group, QPalette.ButtonText, QColor(t.text))
        palette.setColor(group, QPalette.ToolTipBase, QColor(t.tooltip_bg))
        palette.setColor(group, QPalette.ToolTipText, QColor(t.tooltip_fg))
        palette.setColor(group, QPalette.Highlight, QColor(t.selected))
        palette.setColor(group, QPalette.HighlightedText, QColor(t.text))
    app.setPalette(palette)

    if arrow_path is None:
        arrow_path = os.path.join(os.path.dirname(__file__), "assets", "chevron_down.svg").replace("\\", "/")

    app.setStyleSheet(app_stylesheet(t, arrow_path))


def app_stylesheet(t: ThemeTokens, arrow_path: str) -> str:
    return f"""
QWidget {{
    font-family: 'Segoe UI';
    color: {t.text};
}}
QLabel {{
    color: {t.text};
}}
QFrame QLabel {{
    border: none;
}}
QPushButton {{
    font-family: 'Segoe UI';
    outline: none;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QDateTimeEdit,
QSpinBox, QDoubleSpinBox {{
    color: {t.text};
    background: {t.input};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 12px;
    min-height: 36px;
    font-size: 13px;
    selection-background-color: {t.selected};
    selection-color: {t.text};
}}
QTextEdit, QPlainTextEdit {{
    padding: 8px 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.brand};
    background: {t.surface};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0px;
    border: none;
    background: transparent;
}}
QComboBox {{
    color: {t.text};
    background: {t.input};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0 30px 0 12px;
    min-height: 36px;
    font-size: 13px;
}}
QComboBox:focus {{
    border-color: {t.brand};
}}
QComboBox:hover {{
    background: {t.hover};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url({arrow_path});
    width: 10px;
    height: 6px;
}}
QComboBox QAbstractItemView {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 8px;
    selection-background-color: {t.brand};
    selection-color: {"#062f28" if t.name == THEME_DARK else "#ffffff"};
    outline: none;
    padding: 4px;
}}
QCalendarWidget QWidget {{
    color: {t.text};
    background: {t.surface};
}}
QCalendarWidget QToolButton {{
    color: {t.text};
    background: {t.surface_muted};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px 8px;
}}
QCalendarWidget QMenu {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
}}
QTableWidget {{
    color: {t.text};
    background: {t.surface};
    alternate-background-color: {t.surface};
    gridline-color: {t.border};
    border: none;
    outline: none;
    selection-background-color: {t.selected};
}}
QTableWidget::item {{
    color: {t.text};
    border: none;
    border-bottom: 1px solid {t.border};
}}
QTableWidget::item:selected {{
    color: {t.text};
    background: {t.selected};
}}
QHeaderView {{
    background: {t.surface};
    border: none;
}}
QHeaderView::section {{
    color: {t.text_muted};
    background: {t.surface};
    border: none;
    border-bottom: 1px solid {t.border};
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
}}
QScrollBar:vertical {{
    width: 7px;
    background: transparent;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border_strong};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.text_soft};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
    background: transparent;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    height: 7px;
    background: transparent;
    border: none;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t.border_strong};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    border: none;
    background: transparent;
}}
QMessageBox, QDialog {{
    background: {t.surface};
    color: {t.text};
}}
QMessageBox QLabel, QDialog QLabel {{
    color: {t.text};
    background: transparent;
}}
QMessageBox QPushButton {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}}
QMessageBox QPushButton:hover {{
    background: {t.hover};
}}
QMessageBox QPushButton:default {{
    background: {t.brand};
    color: {("#062f28" if t.name == THEME_DARK else "#ffffff")};
    border: none;
}}
QToolTip, QTipLabel {{
    background: {t.tooltip_bg};
    background-color: {t.tooltip_bg};
    color: {t.tooltip_fg};
    border: 1px solid {t.border_strong};
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 12px;
    opacity: 255;
}}
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
    font-size: 13px;
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
