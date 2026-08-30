import shiboken6
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.icons import app_pixmap
from src.ui.theme import THEME_DARK, theme_manager, tokens


class AppSelect(QWidget):
    currentIndexChanged = Signal(int)

    def __init__(self, *, height=44, max_visible_items=10, parent=None):
        super().__init__(parent)
        self._items = []
        self._current_index = -1
        self._height = height
        self._max_visible_items = max_visible_items

        self.setFixedHeight(height)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.trigger = QFrame()
        self.trigger.setFixedHeight(height)
        self.trigger.setCursor(Qt.PointingHandCursor)
        trigger_layout = QHBoxLayout(self.trigger)
        trigger_layout.setContentsMargins(12, 0, 12, 0)
        trigger_layout.setSpacing(8)

        self.label = QLabel("")
        self.arrow = QLabel()
        self.arrow.setFixedSize(16, 16)
        self.arrow.setAlignment(Qt.AlignCenter)

        trigger_layout.addWidget(self.label, 1)
        trigger_layout.addWidget(self.arrow)
        root.addWidget(self.trigger)

        self.popup = _SelectPopupFrame()
        self.popup.hide()
        self.popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_TranslucentBackground, True)
        self.popup.setAutoFillBackground(False)

        self.popup_opacity = QGraphicsOpacityEffect(self.popup)
        self.popup_opacity.setOpacity(1)
        self.popup.setGraphicsEffect(self.popup_opacity)
        self.popup_pos_animation = QPropertyAnimation(self.popup, b"pos", self)
        self.popup_pos_animation.setDuration(120)
        self.popup_pos_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.popup_opacity_animation = QPropertyAnimation(self.popup_opacity, b"opacity", self)
        self.popup_opacity_animation.setDuration(100)
        self.popup_opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.setSpacing(0)

        self.popup_box = QFrame()
        self.popup_box.setObjectName("AppSelectPopupBox")
        self.popup_box.setAttribute(Qt.WA_StyledBackground, True)
        box_layout = QVBoxLayout(self.popup_box)
        box_layout.setContentsMargins(4, 4, 4, 4)
        box_layout.setSpacing(0)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        box_layout.addWidget(self.list_widget)
        popup_layout.addWidget(self.popup_box)

        self.trigger.mousePressEvent = self._toggle_popup
        self.list_widget.itemClicked.connect(self._select_item)
        theme_manager.theme_changed.connect(self._on_theme_changed)
        self.destroyed.connect(self._disconnect_theme_signal)
        self._apply_theme()

    def addItem(self, text, data=None):
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, data)
        item.setSizeHint(QSize(0, 34))
        self.list_widget.addItem(item)
        self._items.append((text, data))
        self._resize_popup_list()
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def clear(self):
        self.list_widget.clear()
        self._items.clear()
        self._current_index = -1
        self.label.setText("")
        self._resize_popup_list()

    def count(self):
        return len(self._items)

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def setCurrentIndex(self, index):
        if index < 0 or index >= len(self._items):
            return
        self._current_index = index
        self.label.setText(self._items[index][0])
        self.list_widget.setCurrentRow(index)
        self.currentIndexChanged.emit(index)

    def setCurrentText(self, text):
        for index, (label, _data) in enumerate(self._items):
            if label == text:
                self.setCurrentIndex(index)
                return

    def findData(self, data):
        for index, (_label, value) in enumerate(self._items):
            if value == data:
                return index
        return -1

    def showPopup(self):
        self._show_popup()

    def hidePopup(self):
        self.popup.hide()

    def _toggle_popup(self, _event):
        if self.popup.isVisible():
            self.popup.hide()
        else:
            self._show_popup()

    def _show_popup(self):
        if not self._items:
            return
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.popup.setFixedSize(self.width(), self.popup.sizeHint().height())
        end_pos = QPoint(pos.x(), pos.y() + 4)
        start_pos = QPoint(end_pos.x(), end_pos.y() - 6)
        self.popup.move(start_pos)
        self.popup_opacity.setOpacity(0)
        self.popup.show()
        self.popup.raise_()
        self.popup_pos_animation.stop()
        self.popup_pos_animation.setStartValue(start_pos)
        self.popup_pos_animation.setEndValue(end_pos)
        self.popup_opacity_animation.stop()
        self.popup_opacity_animation.setStartValue(0)
        self.popup_opacity_animation.setEndValue(1)
        self.popup_pos_animation.start()
        self.popup_opacity_animation.start()

    def _select_item(self, item):
        row = self.list_widget.row(item)
        self._current_index = row
        self.label.setText(item.text())
        self.popup.hide()
        self.currentIndexChanged.emit(row)

    def _resize_popup_list(self):
        visible_count = min(max(1, self.list_widget.count()), self._max_visible_items)
        self.list_widget.setFixedHeight((34 * visible_count) + 2)

    def _on_theme_changed(self, _theme_name):
        self._apply_theme()

    def _disconnect_theme_signal(self, *_args):
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (RuntimeError, TypeError):
            pass

    def _is_valid_widget_tree(self):
        try:
            return shiboken6.isValid(self) and shiboken6.isValid(self.trigger)
        except RuntimeError:
            return False

    def _apply_theme(self):
        if not self._is_valid_widget_tree():
            return
        t = tokens()
        selected_text = "#062f28" if t.name == THEME_DARK else "#ffffff"
        self.trigger.setStyleSheet(f"""
            QFrame {{
                background: {t.input};
                border: 1px solid transparent;
                border-radius: 8px;
            }}
            QFrame:hover {{
                background: {t.hover};
            }}
        """)
        self.label.setStyleSheet(f"font-size: 14px; color: {t.text}; background: transparent; border: none;")
        self.arrow.setPixmap(app_pixmap("chevron-down", color=t.text_muted, size=12))
        self.popup_box.setStyleSheet(f"""
            QFrame#AppSelectPopupBox {{
                background: {t.surface};
                border: 1px solid {t.border};
                border-radius: 8px;
            }}
        """)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {t.text};
                font-size: 14px;
                border: none;
            }}
            QListWidget::item:hover {{
                background: {t.hover};
            }}
            QListWidget::item:selected {{
                background: {t.brand};
                color: {selected_text};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.border_strong};
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                border: none;
            }}
        """)


class _SelectPopupFrame(QFrame):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0, 0, -1, -1), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
