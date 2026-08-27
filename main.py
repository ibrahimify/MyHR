import sys
from PySide6.QtWidgets import QApplication, QLabel, QAbstractItemView
from PySide6.QtCore import Qt, QObject, QEvent, QPoint
from src.database.connection import init_db
from src.ui.login_window import LoginWindow
from src.ui.theme import apply_theme, theme_manager, tokens


class AppTooltipFilter(QObject):
    """Consistent black tooltip surface for all widgets and item views."""

    def __init__(self, app):
        super().__init__(app)
        self._popup = QLabel()
        self._popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self._popup.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.refresh_style()

    def refresh_style(self):
        t = tokens()
        self._popup.setStyleSheet(f"""
            QLabel {{
                background: {t.tooltip_bg};
                color: {t.tooltip_fg};
                border: 1px solid {t.border_strong};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }}
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
    apply_theme(app)
    tooltip_filter = AppTooltipFilter(app)
    app.installEventFilter(tooltip_filter)
    app._tooltip_filter = tooltip_filter
    theme_manager.theme_changed.connect(lambda _: tooltip_filter.refresh_style())

    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
