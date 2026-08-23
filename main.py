import sys
import os
from PySide6.QtWidgets import QApplication, QLabel, QAbstractItemView
from PySide6.QtCore import Qt, QObject, QEvent, QPoint
from PySide6.QtGui import QColor, QPalette
from src.database.connection import init_db
from src.ui.login_window import LoginWindow


class AppTooltipFilter(QObject):
    """Consistent black tooltip surface for all widgets and item views."""

    def __init__(self, app):
        super().__init__(app)
        self._popup = QLabel()
        self._popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self._popup.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._popup.setStyleSheet("""
            QLabel {
                background: #111827;
                color: #ffffff;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.ToolTip:
            text = self._tooltip_text(watched, event)
            if text:
                self._show(text, event.globalPos())
                return True
            self._popup.hide()
            return False

        if event.type() in (
            QEvent.Leave,
            QEvent.MouseButtonPress,
            QEvent.Wheel,
            QEvent.KeyPress,
            QEvent.Hide,
        ):
            self._popup.hide()
        return False

    def _tooltip_text(self, watched, event):
        view = watched.parent() if isinstance(watched.parent(), QAbstractItemView) else None
        if view is not None:
            index = view.indexAt(event.pos())
            if index.isValid():
                return str(index.data(Qt.ToolTipRole) or "").strip()

        current = watched
        while current is not None:
            tooltip = str(current.toolTip() or "").strip() if hasattr(current, "toolTip") else ""
            if tooltip:
                return tooltip
            current = current.parent()
        return ""

    def _show(self, text, global_pos):
        self._popup.setText(text)
        self._popup.adjustSize()
        self._popup.move(global_pos + QPoint(12, 18))
        self._popup.show()


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("MyHR")
    app.setStyle("Fusion")

    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    palette = app.palette()
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        palette.setColor(group, QPalette.ToolTipBase, QColor("#111827"))
        palette.setColor(group, QPalette.ToolTipText, QColor("#ffffff"))
    app.setPalette(palette)
    tooltip_filter = AppTooltipFilter(app)
    app.installEventFilter(tooltip_filter)
    app._tooltip_filter = tooltip_filter

    arrow_path = os.path.join(os.path.dirname(__file__), "src", "ui", "assets", "chevron_down.svg").replace("\\", "/")

    app.setStyleSheet(f"""
        QLabel                {{ color: #111827; }}
        QFrame QLabel         {{ border: none; }}
        QPushButton           {{ font-family: 'Segoe UI'; }}
        QLineEdit, QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {{
            color: #111827; background: #f9fafb;
            border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 0 12px; min-height: 36px;
            font-size: 13px;
        }}
        QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {{
            border-color: #2563eb; background: white;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: #2563eb; background: white;
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 0px; border: none; background: transparent;
        }}
        QCalendarWidget QWidget {{ color: #111827; background: white; }}
        QCalendarWidget QToolButton {{
            color: #111827; background: #f9fafb; border: 1px solid #e5e7eb;
            border-radius: 6px; padding: 4px 8px;
        }}
        QCalendarWidget QMenu {{ background: white; color: #111827; border: 1px solid #e5e7eb; }}
        QComboBox {{
            color: #111827; background: #f9fafb;
            border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 0 10px 0 12px; min-height: 36px;
            font-size: 13px;
        }}
        QComboBox:focus {{ border-color: #2563eb; }}
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
            background: white; color: #111827;
            border: 1px solid #e5e7eb; border-radius: 8px;
            selection-background-color: #eff6ff;
            selection-color: #111827;
            padding: 4px;
        }}
        QTableWidget          {{ color: #111827; gridline-color: #f3f4f6; border: none; }}
        QTableWidget::item    {{ color: #111827; }}
        QHeaderView::section  {{ color: #6b7280; background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 8px 12px; font-size: 12px; font-weight: bold; }}
        QScrollBar:vertical   {{ width: 6px; background: transparent; }}
        QScrollBar::handle:vertical {{ background: #d1d5db; border-radius: 3px; min-height: 20px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ height: 6px; background: transparent; }}
        QScrollBar::handle:horizontal {{ background: #d1d5db; border-radius: 3px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QMessageBox           {{ color: #111827; background: white; }}
        QMessageBox QLabel    {{ color: #111827; }}
        QMessageBox QPushButton {{ background: white; color: #111827; border: 1px solid #d1d5db; border-radius: 6px; min-width: 84px; min-height: 30px; font-weight: 600; }}
        QMessageBox QPushButton:hover {{ background: #f3f4f6; }}
        QMessageBox QPushButton:default {{ background: #030213; color: white; border: none; }}
        QDialog               {{ background: white; color: #111827; }}
        QDialog QLabel        {{ color: #111827; }}
        QToolTip, QTipLabel   {{
            background: #111827;
            background-color: #111827;
            color: #ffffff;
            border: 1px solid #374151;
            padding: 6px 8px;
            border-radius: 6px;
            font-size: 12px;
            opacity: 255;
        }}
        QTabWidget::pane      {{ border: none; background: #f9fafb; }}
        QTabBar::tab          {{ background: white; color: #6b7280; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; font-size: 13px; }}
        QTabBar::tab:selected {{ color: #030213; border-bottom: 2px solid #030213; font-weight: bold; }}
        QTabBar::tab:hover    {{ color: #111827; }}
    """)

    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
