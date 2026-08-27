from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton

from src.ui.theme import THEME_DARK, is_dark, theme_manager, tokens


class ThemeToggle(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(is_dark())
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(64, 32)
        self.setToolTip("Light / Dark")
        self._offset = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.clicked.connect(self._toggle_theme)
        theme_manager.theme_changed.connect(self._sync_theme)

    def _toggle_theme(self):
        theme_manager.toggle()

    def _sync_theme(self, theme: str):
        checked = theme == THEME_DARK
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    def paintEvent(self, event):
        del event
        t = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rail = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setPen(QPen(QColor(t.border_strong), 1))
        painter.setBrush(QColor(t.surface_muted if not is_dark() else "#151515"))
        painter.drawRoundedRect(rail, 16, 16)

        thumb_size = 26
        margin = 3
        x = margin + (self.width() - thumb_size - (margin * 2)) * self._offset
        thumb = QRectF(x, margin, thumb_size, thumb_size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(t.brand_accent if is_dark() else t.surface))
        painter.drawEllipse(thumb)

        sun_color = t.brand if not is_dark() else t.text_soft
        moon_color = "#062f28" if is_dark() else t.text_soft
        self._draw_sun(painter, 16, 16, QColor(sun_color))
        self._draw_moon(painter, self.width() - 17, 16, QColor(moon_color), QColor(t.brand_accent if is_dark() else t.surface))

        painter.end()

    def _draw_sun(self, painter: QPainter, cx: int, cy: int, color: QColor) -> None:
        painter.save()
        painter.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(cx - 3.5, cy - 3.5, 7, 7))
        for x1, y1, x2, y2 in [
            (cx, cy - 10, cx, cy - 7),
            (cx, cy + 7, cx, cy + 10),
            (cx - 10, cy, cx - 7, cy),
            (cx + 7, cy, cx + 10, cy),
            (cx - 7, cy - 7, cx - 5, cy - 5),
            (cx + 5, cy - 5, cx + 7, cy - 7),
            (cx - 7, cy + 7, cx - 5, cy + 5),
            (cx + 5, cy + 5, cx + 7, cy + 7),
        ]:
            painter.drawLine(x1, y1, x2, y2)
        painter.restore()

    def _draw_moon(self, painter: QPainter, cx: int, cy: int, color: QColor, cutout: QColor) -> None:
        painter.save()
        moon = QPainterPath()
        moon.addEllipse(QRectF(cx - 6, cy - 7, 14, 14))
        shadow = QPainterPath()
        shadow.addEllipse(QRectF(cx - 1, cy - 9, 14, 14))
        moon = moon.subtracted(shadow)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawPath(moon)
        painter.restore()
