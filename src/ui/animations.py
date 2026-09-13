import math
from time import monotonic

import shiboken6
from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QRectF, Qt, QParallelAnimationGroup, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from src.ui.theme import tokens


def animate_widget_entry(widget, *, duration=190, offset=8):
    """Subtle page entry animation for stacked pages and tab contents."""
    if widget is None:
        return
    try:
        if not shiboken6.isValid(widget):
            return
    except RuntimeError:
        return

    current = getattr(widget, "_myhr_entry_animation", None)
    if current is not None:
        current.stop()

    def start():
        try:
            if not shiboken6.isValid(widget):
                return
        except RuntimeError:
            return
        end_pos = widget.pos()
        start_pos = end_pos + QPoint(0, offset)

        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        if offset:
            widget.move(start_pos)

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(duration)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(widget)
        group.addAnimation(fade)
        if offset:
            slide = QPropertyAnimation(widget, b"pos")
            slide.setDuration(duration)
            slide.setStartValue(start_pos)
            slide.setEndValue(end_pos)
            slide.setEasingCurve(QEasingCurve.OutCubic)
            group.addAnimation(slide)

        def finish():
            try:
                if not shiboken6.isValid(widget):
                    return
            except RuntimeError:
                return
            widget.move(end_pos)
            widget.setGraphicsEffect(None)
            widget._myhr_entry_animation = None

        group.finished.connect(finish)
        widget._myhr_entry_animation = group
        group.start()

    QTimer.singleShot(0, start)


def install_tab_transition(tab_widget, *, duration=180, offset=7):
    """Attach a restrained entry animation to QTabWidget page changes."""
    if getattr(tab_widget, "_myhr_tab_transition_installed", False):
        return

    tab_widget.currentChanged.connect(
        lambda index: animate_widget_entry(
            tab_widget.widget(index),
            duration=duration,
            offset=offset,
        )
    )
    tab_widget._myhr_tab_transition_installed = True


class Spinner(QWidget):
    """Theme-aware vector spinner for moments where a page needs a beat to load."""

    def __init__(self, parent=None, *, size=48):
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self._running = False
        self._started_at = monotonic()
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._running = True
        self._started_at = monotonic()
        if not self._timer.isActive():
            self._timer.start()
        self.show()
        self.update()

    def stop(self):
        self._running = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = self._current_angle()
        self.update()

    def _current_angle(self):
        if not self._running:
            return self._angle
        elapsed = monotonic() - self._started_at
        return int((elapsed * 430) % 360)

    def paintEvent(self, _event):
        t = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._angle = self._current_angle()

        rect = QRectF(6, 6, self._size - 12, self._size - 12)
        base = QColor(t.border_strong)
        base.setAlpha(120 if t.name == "dark" else 150)
        accent = QColor(t.brand)
        glow = QColor(t.brand)
        glow.setAlpha(42 if t.name == "dark" else 52)

        painter.setPen(QPen(glow, 8, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect.adjusted(1, 1, -1, -1), int(-self._angle * 16), int(-116 * 16))

        painter.setPen(QPen(base, 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)

        painter.setPen(QPen(accent, 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, int(-self._angle * 16), int(-118 * 16))

        radius = rect.width() / 2
        center = rect.center()
        radians = math.radians(self._angle + 118)
        dot_x = center.x() + math.cos(radians) * radius
        dot_y = center.y() - math.sin(radians) * radius
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(QRectF(dot_x - 3, dot_y - 3, 6, 6))


class LoadingOverlay(QWidget):
    def __init__(self, parent, *, text=""):
        super().__init__(parent)
        self._text = text
        self._fade = None
        self._shown_at = 0.0
        self.setObjectName("LoadingOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.spinner = Spinner(self)
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setVisible(bool(text))
        layout.addWidget(self.spinner, 0, Qt.AlignCenter)
        layout.addWidget(self.label, 0, Qt.AlignCenter)

        parent.installEventFilter(self)
        self._sync_geometry()
        self.apply_theme()

    def apply_theme(self):
        t = tokens()
        bg = QColor(t.canvas if t.name == "dark" else t.surface)
        bg.setAlpha(218 if t.name == "dark" else 228)
        self.setStyleSheet(f"""
            QWidget#LoadingOverlay {{
                background: rgba({bg.red()}, {bg.green()}, {bg.blue()}, {bg.alpha()});
                border: none;
            }}
            QWidget#LoadingOverlay QLabel {{
                color: {t.text_muted};
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 700;
            }}
        """)

    def show_loading(self, text=None, *, animated=True):
        if text:
            self._text = text
            self.label.setText(text)
            self.label.setVisible(True)
        else:
            self.label.setVisible(bool(self._text))
        self.apply_theme()
        self._sync_geometry()
        self.raise_()
        self.show()
        self.spinner.start()
        self._shown_at = monotonic()
        if animated:
            self._animate_opacity(0.0, 1.0, 120)
        else:
            if self._fade is not None:
                self._fade.stop()
            effect = self.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(self)
                self.setGraphicsEffect(effect)
            effect.setOpacity(1.0)
            self.repaint()
            self.spinner.repaint()

    def hide_loading(self, *, minimum_ms=260):
        if not self.isVisible():
            return
        elapsed_ms = int((monotonic() - self._shown_at) * 1000)
        if elapsed_ms < minimum_ms:
            QTimer.singleShot(minimum_ms - elapsed_ms, lambda: self.hide_loading(minimum_ms=0))
            return

        def finish():
            self.spinner.stop()
            self.hide()
            self.setGraphicsEffect(None)

        self._animate_opacity(1.0, 0.0, 120, finish)

    def eventFilter(self, watched, event):
        try:
            parent = self.parentWidget()
        except RuntimeError:
            return False
        if watched is parent and event.type() in (QEvent.Resize, QEvent.Show):
            self._sync_geometry()
        return super().eventFilter(watched, event)

    def _sync_geometry(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def _animate_opacity(self, start, end, duration, finished=None):
        if self._fade is not None:
            self._fade.stop()
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect.setOpacity(start)
        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(duration)
        fade.setStartValue(start)
        fade.setEndValue(end)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        if finished is not None:
            fade.finished.connect(finished)
        self._fade = fade
        fade.start()
