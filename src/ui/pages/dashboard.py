"""Dashboard page matching the MockUI React dashboard layout."""

from datetime import datetime, timedelta
from html import escape

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QDateEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QRectF, QPointF, QDate
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QLinearGradient

from src.core.i18n import is_rtl, t
from src.database.connection import (
    get_session, get_increment_due_employees, apply_salary_increment,
    calculate_months_remaining_batch, OTHER_ORG_UNIT_NAME
)
from src.database.models import (
    Employee, Sanction, Commendation, AuditLog, Title, OrgUnit,
    PromotionHistory, SalaryIncrementHistory
)
from src.ui.styles import (
    btn_primary, btn_outline, btn_ghost, table_style, scroll_ss, message_box_ss,
    enable_table_row_selection, prepare_table_cell_widget, primary_button_fg,
    race_color, race_soft_color, race_progress_bar_ss,
)
from src.ui.chart_theme import chart_axis_color, chart_color, chart_grid_color, chart_soft_color
from src.ui.icons import app_icon, app_pixmap
from src.ui.theme import THEME_DARK, tokens


_ICO = QSize(16, 16)


def _alpha(color, value):
    tinted = QColor(color)
    tinted.setAlpha(value)
    return tinted


def _series_color(color_key):
    return QColor(chart_color(color_key))


def _line_path(points):
    if not points:
        return QPainterPath()
    path = QPainterPath(points[0])
    for index in range(1, len(points)):
        previous = points[index - 1]
        current = points[index]
        dx = (current.x() - previous.x()) * 0.45
        path.cubicTo(
            QPointF(previous.x() + dx, previous.y()),
            QPointF(current.x() - dx, current.y()),
            current,
        )
    return path


def _chart_tooltip_ss(accent):
    tkn = tokens()
    return (
        f"background: {tkn.surface_raised}; color: {tkn.text}; "
        f"border: 1px solid {tkn.border_strong}; border-radius: 8px; "
        "padding: 8px 10px; font-size: 12px;"
    )


def _hide_chart_tooltip(widget):
    tooltip = getattr(widget, "_chart_tooltip", None)
    if tooltip is not None:
        tooltip.hide()


def _show_chart_tooltip(widget, pos, title, rows, accent_key="promotion"):
    accent = chart_color(accent_key)
    tooltip = getattr(widget, "_chart_tooltip", None)
    if tooltip is None:
        tooltip = QLabel(widget)
        tooltip.setObjectName("ChartTooltip")
        tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)
        tooltip.setTextFormat(Qt.RichText)
        widget._chart_tooltip = tooltip

    row_html = "".join(
        f"<div style='white-space:nowrap; color:{tokens().text_muted};'>"
        f"<span style='color:{chart_color(color_key)};'>{escape(str(name))}</span>: "
        f"<b style='color:{tokens().text};'>{escape(str(value))}</b></div>"
        for name, value, color_key in rows
    )
    tooltip.setStyleSheet(_chart_tooltip_ss(accent))
    tooltip.setText(
        f"<div style='white-space:nowrap; font-weight:600; color:{tokens().text}; margin-bottom:4px;'>{escape(str(title))}</div>"
        f"{row_html}"
    )
    tooltip.adjustSize()
    x = int(pos.x() + 14)
    y = int(pos.y() - tooltip.height() - 12)
    if y < 8:
        y = int(pos.y() + 14)
    x = min(max(8, x), max(8, widget.width() - tooltip.width() - 8))
    y = min(max(8, y), max(8, widget.height() - tooltip.height() - 8))
    tooltip.move(x, y)
    tooltip.raise_()
    tooltip.show()


def _draw_hover_rule(painter, chart, x, color_key):
    if x is None or x < chart.left() or x > chart.right():
        return
    color = _alpha(_series_color(color_key), 70 if tokens().name == THEME_DARK else 58)
    painter.setPen(QPen(color, 1, Qt.DashLine))
    painter.drawLine(QPointF(x, chart.top()), QPointF(x, chart.bottom()))


def _draw_hollow_marker(painter, point, color, *, radius=4.0, width=2.0, active=False):
    tkn = tokens()
    marker_radius = radius + (0.8 if active else 0)
    marker_width = width + (0.25 if active else 0)
    painter.setBrush(QBrush(QColor(tkn.surface)))
    painter.setPen(QPen(color, marker_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawEllipse(point, marker_radius, marker_radius)


def _same_point(first, second):
    return (
        second is not None and
        abs(first.x() - second.x()) < 0.5 and
        abs(first.y() - second.y()) < 0.5
    )


def _mini_progress_ss(color_key="increment", radius=4):
    tkn = tokens()
    return (
        f"QProgressBar {{ background: {tkn.border}; border: none; border-radius: {radius}px; }}"
        f"QProgressBar::chunk {{ background: {chart_color(color_key)}; border-radius: {radius}px; }}"
    )


def dashboard_card_ss():
    tkn = tokens()
    return f"""
QFrame#DashboardCard {{
    background: {tkn.surface};
    border: 1px solid {tkn.border};
    border-radius: 8px;
}}
QFrame#DashboardCard QLabel {{
    border: none;
    background: transparent;
}}
"""


DASH_CARD_SS = dashboard_card_ss()

FILTERS = ("week", "month", "year", "ytd", "custom")
ORG_LEVELS = ("division", "department", "unit", "team")
WORKFORCE_FILTERS = ("week", "month", "year", "ytd")
WORKFORCE_METRICS = ("headcount", "promotions", "increments", "all")


def _pct_delta(current, previous):
    if previous == 0:
        if current == 0:
            return "0%"
        return f"+{current}"
    value = ((current - previous) / previous) * 100
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.0f}%"


def _month_key(dt):
    return dt.strftime("%Y-%m")


def _filter_window(filter_key, custom_start=None, custom_end=None):
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    if filter_key == "week":
        start = today - timedelta(days=6)
        previous_start = start - timedelta(days=7)
        previous_end = start
        return start, now, previous_start, previous_end
    if filter_key == "year":
        start = datetime(now.year - 1, now.month, 1)
        previous_start = datetime(now.year - 2, now.month, 1)
        previous_end = start
        return start, now, previous_start, previous_end
    if filter_key == "ytd":
        start = datetime(now.year, 1, 1)
        previous_start = datetime(now.year - 1, 1, 1)
        previous_end = datetime(now.year - 1, now.month, now.day)
        return start, now, previous_start, previous_end
    if filter_key == "custom" and custom_start and custom_end:
        start = custom_start
        end = custom_end
        span = max(end - start, timedelta(days=1))
        return start, end, start - span, start
    start = today - timedelta(days=29)
    previous_start = start - timedelta(days=30)
    previous_end = start
    return start, now, previous_start, previous_end


def _safe_anniversary(join_date, year):
    try:
        return join_date.replace(year=year)
    except ValueError:
        return join_date.replace(year=year, day=28)


def _month_range(months=6):
    now = datetime.utcnow()
    first = datetime(now.year, now.month, 1)
    start_month = first
    for _ in range(months - 1):
        if start_month.month == 1:
            start_month = datetime(start_month.year - 1, 12, 1)
        else:
            start_month = datetime(start_month.year, start_month.month - 1, 1)

    months_list = []
    cursor = start_month
    while cursor <= first:
        months_list.append(cursor)
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1)
    return months_list


def _next_month_start(dt):
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1)
    return datetime(dt.year, dt.month + 1, 1)


def _timeline_buckets(filter_key):
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    buckets = []
    if filter_key == "week":
        start = today - timedelta(days=6)
        for index in range(7):
            day = start + timedelta(days=index)
            buckets.append((day.strftime("%a"), day, day + timedelta(days=1)))
        return buckets
    if filter_key == "month":
        start = today - timedelta(days=27)
        for index in range(4):
            week_start = start + timedelta(days=index * 7)
            week_end = week_start + timedelta(days=7)
            buckets.append((week_start.strftime("%b %d"), week_start, min(week_end, now + timedelta(days=1))))
        return buckets
    if filter_key == "ytd":
        cursor = datetime(now.year, 1, 1)
        while cursor <= now:
            buckets.append((cursor.strftime("%b"), cursor, _next_month_start(cursor)))
            cursor = _next_month_start(cursor)
        return buckets

    first = datetime(now.year, now.month, 1)
    cursor = first
    for _ in range(11):
        cursor = datetime(cursor.year - 1, 12, 1) if cursor.month == 1 else datetime(cursor.year, cursor.month - 1, 1)
    while cursor <= first:
        buckets.append((cursor.strftime("%b"), cursor, _next_month_start(cursor)))
        cursor = _next_month_start(cursor)
    return buckets


class BarChartWidget(QWidget):
    def __init__(self, data=None, color="dimension", parent=None):
        super().__init__(parent)
        self.data = data or []
        self.color = color
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

    def set_data(self, data):
        self.data = data or []
        self.update()

    def mouseMoveEvent(self, event):
        hit = getattr(self, "_hit_boxes", [])
        for rect, label, value in hit:
            if rect.contains(event.position().toPoint()):
                _show_chart_tooltip(
                    self,
                    event.position(),
                    label,
                    [(t("employees"), value, self.color)],
                    self.color,
                )
                return
        _hide_chart_tooltip(self)

    def leaveEvent(self, event):
        _hide_chart_tooltip(self)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 10, -12, -10)
        chart = rect.adjusted(168, 8, -38, -18)

        if not self.data:
            self._draw_empty(painter, rect)
            return

        max_value = max([value for _, value in self.data] + [1])
        count = len(self.data)
        gap = 8
        bar_h = max(11, min(24, (chart.height() - gap * (count - 1)) / max(count, 1)))
        self._hit_boxes = []

        tkn = tokens()
        painter.setPen(QPen(QColor(chart_grid_color()), 1, Qt.DashLine))
        for i in range(1, 4):
            x = chart.left() + chart.width() * i / 4
            painter.drawLine(QPointF(x, chart.top()), QPointF(x, chart.bottom()))

        label_font = QFont()
        label_font.setPointSize(8)
        painter.setFont(label_font)

        for idx, (label, value) in enumerate(self.data):
            ratio = value / max_value if max_value else 0
            bar_w = max(3, chart.width() * ratio)
            x = chart.left()
            y = chart.top() + idx * (bar_h + gap)
            bar = QRectF(x, y, bar_w, bar_h)
            painter.setPen(Qt.NoPen)
            radius = min(7, bar_h / 2)
            painter.setBrush(QBrush(_series_color(self.color)))
            painter.drawRoundedRect(bar, radius, radius)
            self._hit_boxes.append((bar.toRect(), label, value))

            painter.setPen(QColor(tkn.text_muted))
            short = painter.fontMetrics().elidedText(label, Qt.ElideRight, 156)
            painter.drawText(QRectF(rect.left(), y - 1, 156, bar_h + 2), Qt.AlignVCenter | Qt.AlignRight, short)
            painter.setPen(QColor(tkn.text_soft))
            painter.drawText(QRectF(chart.left() + bar_w + 8, y - 1, 34, bar_h + 2), Qt.AlignVCenter | Qt.AlignLeft, str(value))

        painter.setPen(QColor(tkn.text_soft))
        painter.drawText(QRectF(chart.left(), chart.bottom() + 2, 40, 18), Qt.AlignLeft, "0")

    def _draw_grid(self, painter, chart):
        painter.setPen(QPen(QColor(chart_grid_color()), 1, Qt.DashLine))
        for i in range(1, 4):
            y = chart.top() + chart.height() * i / 4
            painter.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))

    def _draw_empty(self, painter, rect):
        painter.setPen(QColor(tokens().text_soft))
        painter.drawText(rect, Qt.AlignCenter, t("no_data"))


class LineChartWidget(QWidget):
    def __init__(self, data=None, color="promotion", parent=None):
        super().__init__(parent)
        self.data = data or []
        self.color = color
        self.setMinimumHeight(260)
        self.setMouseTracking(True)

    def set_data(self, data):
        self.data = data or []
        self.update()

    def mouseMoveEvent(self, event):
        for point, label, value in getattr(self, "_hit_points", []):
            if (point - event.position()).manhattanLength() <= 10:
                self._hover_point = point
                self._hover_color = self.color
                self.update()
                _show_chart_tooltip(
                    self,
                    event.position(),
                    label,
                    [(t("promotions"), value, self.color)],
                    self.color,
                )
                return
        if getattr(self, "_hover_point", None) is not None:
            self._hover_point = None
            self.update()
        _hide_chart_tooltip(self)

    def leaveEvent(self, event):
        self._hover_point = None
        self.update()
        _hide_chart_tooltip(self)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 14, -10, -18)
        chart = rect.adjusted(42, 10, -12, -34)
        tkn = tokens()
        line_color = _series_color(self.color)
        painter.setPen(QPen(QColor(chart_grid_color()), 1, Qt.DashLine))
        for i in range(1, 4):
            y = chart.top() + chart.height() * i / 4
            painter.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))

        painter.setPen(QPen(QColor(chart_axis_color()), 1))
        painter.drawLine(chart.bottomLeft(), chart.bottomRight())
        painter.drawLine(chart.bottomLeft(), chart.topLeft())
        _draw_hover_rule(painter, chart, getattr(self, "_hover_point", None).x() if getattr(self, "_hover_point", None) else None, getattr(self, "_hover_color", self.color))

        if not self.data:
            painter.setPen(QColor(tkn.text_soft))
            painter.drawText(rect, Qt.AlignCenter, t("no_data"))
            return

        max_value = max([value for _, value in self.data] + [1])
        step = chart.width() / max(len(self.data) - 1, 1)
        points = []
        self._hit_points = []
        for idx, (label, value) in enumerate(self.data):
            x = chart.left() + idx * step
            y = chart.bottom() - (chart.height() * value / max_value if max_value else 0)
            point = QPointF(x, y)
            points.append(point)
            self._hit_points.append((point, label, value))

        if len(points) > 1:
            path = _line_path(points)
            area = QPainterPath(path)
            area.lineTo(points[-1].x(), chart.bottom())
            area.lineTo(points[0].x(), chart.bottom())
            area.closeSubpath()
            fill = QLinearGradient(0, chart.top(), 0, chart.bottom())
            fill.setColorAt(0.0, _alpha(line_color, 24 if tkn.name == THEME_DARK else 18))
            fill.setColorAt(1.0, _alpha(line_color, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(fill))
            painter.drawPath(area)

            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(line_color, 2.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)

        for point in points:
            _draw_hollow_marker(
                painter,
                point,
                line_color,
                radius=4.4,
                width=2.1,
                active=_same_point(point, getattr(self, "_hover_point", None)),
            )

        painter.setPen(QColor(tkn.text_muted))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        for idx, (label, _) in enumerate(self.data):
            if len(self.data) > 8 and idx % 2:
                continue
            x = chart.left() + idx * step
            painter.drawText(QRectF(x - 34, chart.bottom() + 8, 68, 22), Qt.AlignCenter, label)

        self._draw_y_axis_labels(painter, rect, chart, max_value)

    def _draw_y_axis_labels(self, painter, rect, chart, max_value):
        painter.setPen(QColor(tokens().text_soft))
        for value in sorted(set([0, max_value // 2, max_value])):
            y = chart.bottom() - (chart.height() * value / max_value if max_value else 0)
            painter.drawText(QRectF(rect.left(), y - 9, 38, 18), Qt.AlignRight | Qt.AlignVCenter, str(value))


class WorkforceTimelineWidget(QWidget):
    def __init__(self, labels=None, series=None, parent=None):
        super().__init__(parent)
        self.labels = labels or []
        self.series = series or []
        self.setMinimumHeight(300)
        self.setMouseTracking(True)

    def set_data(self, labels, series):
        self.labels = labels or []
        self.series = series or []
        self.update()

    def mouseMoveEvent(self, event):
        for point, title, rows, accent_key in getattr(self, "_hit_points", []):
            if (point - event.position()).manhattanLength() <= 12:
                self._hover_point = point
                self._hover_color = accent_key
                self.update()
                _show_chart_tooltip(self, event.position(), title, rows, accent_key)
                return
        if getattr(self, "_hover_point", None) is not None:
            self._hover_point = None
            self.update()
        _hide_chart_tooltip(self)

    def leaveEvent(self, event):
        self._hover_point = None
        self.update()
        _hide_chart_tooltip(self)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)

        if not self.labels or not self.series:
            painter.setPen(QColor(tokens().text_soft))
            painter.drawText(rect, Qt.AlignCenter, t("no_data"))
            return

        if len(self.series) > 1:
            self._paint_indexed_overlay(painter, rect)
            return

        chart = rect.adjusted(48, 14, -18, -58)

        step = chart.width() / max(len(self.labels) - 1, 1)
        self._hit_points = []

        tkn = tokens()
        painter.setPen(QPen(QColor(chart_grid_color()), 1, Qt.DashLine))
        for i in range(1, 4):
            y = chart.top() + chart.height() * i / 4
            painter.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))
        painter.setPen(QPen(QColor(chart_axis_color()), 1))
        painter.drawLine(chart.bottomLeft(), chart.bottomRight())
        painter.drawLine(chart.bottomLeft(), chart.topLeft())
        _draw_hover_rule(painter, chart, getattr(self, "_hover_point", None).x() if getattr(self, "_hover_point", None) else None, getattr(self, "_hover_color", "promotion"))

        max_value = max([value for _, values, _ in self.series for value in values] + [1])
        for name, values, color in self.series:
            line_color = _series_color(color)
            points = []
            for idx, value in enumerate(values):
                x = chart.left() + idx * step
                y = chart.bottom() - (chart.height() * value / max_value if max_value else 0)
                point = QPointF(x, y)
                points.append(point)
                rows = [
                    (series_name, series_values[idx] if idx < len(series_values) else 0, series_color)
                    for series_name, series_values, series_color in self.series
                ]
                self._hit_points.append((point, self.labels[idx], rows, color))

            if len(points) > 1:
                path = _line_path(points)
                area = QPainterPath(path)
                area.lineTo(points[-1].x(), chart.bottom())
                area.lineTo(points[0].x(), chart.bottom())
                area.closeSubpath()
                fill = QLinearGradient(0, chart.top(), 0, chart.bottom())
                fill.setColorAt(0.0, _alpha(line_color, 22 if tkn.name == THEME_DARK else 16))
                fill.setColorAt(1.0, _alpha(line_color, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(fill))
                painter.drawPath(area)

                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(line_color, 2.25, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(path)
            for point in points:
                _draw_hollow_marker(
                    painter,
                    point,
                    line_color,
                    radius=3.8,
                    width=1.9,
                    active=_same_point(point, getattr(self, "_hover_point", None)),
                )

        painter.setPen(QColor(tkn.text_muted))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        for idx, label in enumerate(self.labels):
            x = chart.left() + idx * step
            painter.drawText(QRectF(x - 36, chart.bottom() + 10, 72, 20), Qt.AlignCenter, label)

        legend_items = []
        for name, _, color in self.series:
            text_w = painter.fontMetrics().horizontalAdvance(name)
            legend_items.append((name, color, text_w + 28))
        total_legend_w = sum(width for _, _, width in legend_items)
        legend_x = chart.center().x() - total_legend_w / 2
        legend_y = rect.bottom() - 20
        for name, color, width in legend_items:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(_series_color(color)))
            painter.drawEllipse(QPointF(legend_x + 5, legend_y + 5), 4, 4)
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(QRectF(legend_x + 16, legend_y - 4, width - 18, 20), Qt.AlignLeft | Qt.AlignVCenter, name)
            legend_x += width

        painter.setPen(QColor(tokens().text_soft))
        for value in sorted(set([0, max_value // 2, max_value])):
            y = chart.bottom() - (chart.height() * value / max_value if max_value else 0)
            painter.drawText(QRectF(rect.left(), y - 9, 42, 18), Qt.AlignRight | Qt.AlignVCenter, str(value))

    def _paint_indexed_overlay(self, painter, rect):
        chart = rect.adjusted(48, 14, -18, -58)
        step = chart.width() / max(len(self.labels) - 1, 1)
        self._hit_points = []

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        tkn = tokens()
        painter.setPen(QPen(QColor(chart_grid_color()), 1, Qt.DashLine))
        for i in range(1, 4):
            y = chart.top() + chart.height() * i / 4
            painter.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))
        painter.setPen(QPen(QColor(chart_axis_color()), 1))
        painter.drawLine(chart.bottomLeft(), chart.bottomRight())
        painter.drawLine(chart.bottomLeft(), chart.topLeft())
        _draw_hover_rule(painter, chart, getattr(self, "_hover_point", None).x() if getattr(self, "_hover_point", None) else None, getattr(self, "_hover_color", "promotion"))

        painter.setPen(QColor(tkn.text_soft))
        for value in (0, 50, 100):
            y = chart.bottom() - (chart.height() * value / 100)
            painter.drawText(QRectF(rect.left(), y - 9, 42, 18), Qt.AlignRight | Qt.AlignVCenter, f"{value}%")

        for name, values, color in self.series:
            line_color = _series_color(color)
            normalized_values = self._aligned_series_values(values)
            max_value = max(normalized_values + [1])
            indexed_values = [(value / max_value) * 100 if max_value else 0 for value in normalized_values]
            points = []
            for idx, indexed_value in enumerate(indexed_values):
                x = chart.left() + idx * step
                y = chart.bottom() - (chart.height() * indexed_value / 100)
                point = QPointF(x, y)
                points.append(point)
                rows = [
                    (
                        series_name,
                        self._aligned_series_values(series_values)[idx] if idx < len(self.labels) else 0,
                        series_color,
                    )
                    for series_name, series_values, series_color in self.series
                ]
                self._hit_points.append((point, self.labels[idx], rows, color))

            if len(points) > 1:
                path = _line_path(points)
                fill_alpha = 0
                if str(color) == "promotion":
                    fill_alpha = 26 if tkn.name == THEME_DARK else 18
                if fill_alpha:
                    area = QPainterPath(path)
                    area.lineTo(points[-1].x(), chart.bottom())
                    area.lineTo(points[0].x(), chart.bottom())
                    area.closeSubpath()
                    fill = QLinearGradient(0, chart.top(), 0, chart.bottom())
                    fill.setColorAt(0.0, _alpha(line_color, fill_alpha))
                    fill.setColorAt(1.0, _alpha(line_color, 0))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(fill))
                    painter.drawPath(area)

                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(line_color, 2.15, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(path)
            elif points:
                painter.setPen(QPen(line_color, 2.15))
                painter.drawPoint(points[0])

            for point in points:
                _draw_hollow_marker(
                    painter,
                    point,
                    line_color,
                    radius=3.4,
                    width=1.8,
                    active=_same_point(point, getattr(self, "_hover_point", None)),
                )

        painter.setPen(QColor(tkn.text_muted))
        for idx, label in enumerate(self.labels):
            if len(self.labels) > 10 and idx % 2:
                continue
            x = chart.left() + idx * step
            painter.drawText(QRectF(x - 36, chart.bottom() + 10, 72, 20), Qt.AlignCenter, label)

        self._draw_centered_legend(painter, rect, chart)

    def _aligned_series_values(self, values):
        aligned = list(values[:len(self.labels)])
        if len(aligned) < len(self.labels):
            aligned.extend([0] * (len(self.labels) - len(aligned)))
        return aligned

    def _smooth_points(self, points):
        if len(points) == 2:
            return points

        smooth_points = [points[0]]
        min_y = min(point.y() for point in points)
        max_y = max(point.y() for point in points)
        for index in range(len(points) - 1):
            p0 = points[max(index - 1, 0)]
            p1 = points[index]
            p2 = points[index + 1]
            p3 = points[min(index + 2, len(points) - 1)]
            for step in range(1, 13):
                t_value = step / 12
                t2 = t_value * t_value
                t3 = t2 * t_value
                x = 0.5 * (
                    (2 * p1.x()) +
                    (-p0.x() + p2.x()) * t_value +
                    (2 * p0.x() - 5 * p1.x() + 4 * p2.x() - p3.x()) * t2 +
                    (-p0.x() + 3 * p1.x() - 3 * p2.x() + p3.x()) * t3
                )
                y = 0.5 * (
                    (2 * p1.y()) +
                    (-p0.y() + p2.y()) * t_value +
                    (2 * p0.y() - 5 * p1.y() + 4 * p2.y() - p3.y()) * t2 +
                    (-p0.y() + 3 * p1.y() - 3 * p2.y() + p3.y()) * t3
                )
                smooth_points.append(QPointF(x, min(max(y, min_y), max_y)))
        return smooth_points

    def _draw_centered_legend(self, painter, rect, chart):
        legend_items = []
        for name, _, color in self.series:
            text_w = painter.fontMetrics().horizontalAdvance(name)
            legend_items.append((name, color, text_w + 34))
        total_legend_w = sum(width for _, _, width in legend_items)
        legend_x = chart.center().x() - total_legend_w / 2
        legend_y = rect.bottom() - 22
        for name, color, width in legend_items:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(_series_color(color)))
            painter.drawEllipse(QPointF(legend_x + 5, legend_y + 5), 4, 4)
            painter.setPen(QColor(tokens().text_muted))
            painter.drawText(QRectF(legend_x + 16, legend_y - 5, width - 18, 22), Qt.AlignLeft | Qt.AlignVCenter, name)
            legend_x += width


class SalaryIncrementReviewDialog(QDialog):
    def __init__(self, increment_data, user, parent=None):
        super().__init__(parent)
        self.increment_data = increment_data
        self.user = user
        self.approved_ids = set()
        self.setWindowTitle(t("review_salary_increments"))
        self.setMinimumSize(700, 460)
        self.setStyleSheet(f"background: {tokens().surface}; color: {tokens().text};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(t("annual_salary_increment_review"))
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {tokens().text};")
        sub = QLabel(t("salary_increment_review_subtitle", count=len(self.increment_data)))
        sub.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted};")
        layout.addWidget(title)
        layout.addWidget(sub)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            t("employee"),
            t("current_salary"),
            t("new_salary"),
            t("increment"),
            t("action"),
        ])
        self.table.setStyleSheet(table_style())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 172)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        enable_table_row_selection(self.table)
        self.table.setRowCount(len(self.increment_data))

        for i, row in enumerate(self.increment_data):
            self.table.setRowHeight(i, 52)
            self.table.setItem(i, 0, QTableWidgetItem(f"{row['name']}  ({row['emp_id']})"))
            self.table.setItem(i, 1, QTableWidgetItem(f"${row['salary_before']:,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"${row['salary_after']:,.2f}"))
            inc_item = QTableWidgetItem(row["increment_str"])
            inc_item.setForeground(QColor(tokens().success))
            self.table.setItem(i, 3, inc_item)
            self._set_row_btn(i, row["id"])

        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        approve_all = QPushButton("  " + t("approve_all"))
        approve_all.setIcon(app_icon("fa5s.check-double", color=primary_button_fg(), size=16))
        approve_all.setIconSize(_ICO)
        approve_all.setFixedHeight(36)
        approve_all.setCursor(Qt.PointingHandCursor)
        approve_all.setStyleSheet(btn_primary(36))
        approve_all.clicked.connect(self._approve_all)

        close_btn = QPushButton(t("close"))
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(btn_outline(36))
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(approve_all)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _set_row_btn(self, idx, emp_id):
        cell = prepare_table_cell_widget(QWidget())
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setAlignment(Qt.AlignCenter)
        if emp_id in self.approved_ids:
            lbl = QLabel(t("approved"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(120, 32)
            lbl.setStyleSheet(
                f"background: {tokens().success_soft}; color: {tokens().success}; border: 1px solid {tokens().success}; border-radius: 8px; "
                "font-size: 12px; font-weight: 800;"
            )
            layout.addWidget(lbl)
            self.table.setCellWidget(idx, 4, cell)
            return

        btn = QPushButton("  " + t("approve"))
        btn.setIcon(app_icon("fa5s.check", color=tokens().success, size=13))
        btn.setIconSize(QSize(13, 13))
        btn.setFixedSize(120, 34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {tokens().surface}; color: {tokens().success}; border: 1px solid {tokens().success}; "
            "border-radius: 8px; font-size: 12px; font-weight: 800; padding: 0 12px; } "
            f"QPushButton:hover {{ background: {tokens().success_soft}; }} "
            f"QPushButton:pressed {{ background: {tokens().success_soft}; }}"
        )
        btn.setIcon(app_icon("fa5s.check", color=tokens().success, size=13))
        btn.clicked.connect(lambda _, eid=emp_id, ridx=idx: self._approve_one(eid, ridx))
        layout.addWidget(btn)
        self.table.setCellWidget(idx, 4, cell)

    def _approve_one(self, emp_id, row_idx):
        session = get_session()
        try:
            result = apply_salary_increment(emp_id, self.user.id, session)
            if result["success"]:
                self.approved_ids.add(emp_id)
                self._set_row_btn(row_idx, emp_id)
            else:
                _warning(self, t("error"), result.get("error", "Failed."))
        except Exception as e:
            _critical(self, t("error"), str(e))
        finally:
            session.close()

    def _approve_all(self):
        pending = [r for r in self.increment_data if r["id"] not in self.approved_ids]
        if not pending:
            _information(self, t("done"), t("all_increments_approved"))
            return

        errors = []
        for i, row in enumerate(self.increment_data):
            if row["id"] in self.approved_ids:
                continue
            session = get_session()
            try:
                result = apply_salary_increment(row["id"], self.user.id, session)
                if result["success"]:
                    self.approved_ids.add(row["id"])
                    self._set_row_btn(i, row["id"])
                else:
                    errors.append(f"{row['name']}: {result.get('error', 'failed')}")
            except Exception as e:
                errors.append(f"{row['name']}: {str(e)}")
            finally:
                session.close()

        if errors:
            _warning(self, t("some_failed"), "\n".join(errors))
        else:
            _information(self, t("done"), t("all_increments_done", count=len(pending)))


class DashboardPage(QWidget):
    def __init__(self, user, navigate_fn):
        super().__init__()
        self.user = user
        self.navigate = navigate_fn
        self.chart_filter = "ytd"
        self.org_chart_level = "division"
        self.workforce_filter = "ytd"
        self.workforce_metric = "all"
        self.custom_start = None
        self.custom_end = None
        self.filter_buttons = {}
        self.org_filter_buttons = {}
        self.workforce_filter_buttons = {}
        self.workforce_metric_buttons = {}
        self.setObjectName("DashboardPage")
        self.setStyleSheet(
            f"QWidget#DashboardPage {{ background: {tokens().canvas}; }} "
            "QWidget#DashboardPage QLabel { border: none; }"
        )
        self._load_data()
        self._build()

    def _load_data(self):
        session = get_session()
        try:
            start, end, prev_start, prev_end = _filter_window(
                self.chart_filter, self.custom_start, self.custom_end
            )

            self.emp_count = session.query(Employee).count()
            self.sanction_count = session.query(Sanction).filter_by(is_resolved=False).count()
            self.commend_count = session.query(Commendation).filter(
                Commendation.issued_at >= start,
                Commendation.issued_at <= end,
            ).count()
            self.promotion_count = 0
            self.employee_delta = _pct_delta(
                session.query(Employee).filter(Employee.created_at >= start, Employee.created_at <= end).count(),
                session.query(Employee).filter(Employee.created_at >= prev_start, Employee.created_at < prev_end).count(),
            )
            self.commend_delta = _pct_delta(
                self.commend_count,
                session.query(Commendation).filter(
                    Commendation.issued_at >= prev_start,
                    Commendation.issued_at < prev_end,
                ).count(),
            )
            self.sanction_delta = _pct_delta(
                session.query(Sanction).filter(
                    Sanction.issued_at >= start,
                    Sanction.issued_at <= end,
                ).count(),
                session.query(Sanction).filter(
                    Sanction.issued_at >= prev_start,
                    Sanction.issued_at < prev_end,
                ).count(),
            )

            increment_due = get_increment_due_employees(session)
            self.increment_count = len(increment_due)
            self.increment_names = [e.first_name + " " + e.last_name for e in increment_due[:3]]
            titles_by_id = {title.id: title for title in session.query(Title).all()}

            self.increment_data = []
            for emp in increment_due:
                title = titles_by_id.get(emp.title_id)
                if not title:
                    continue
                salary_before = emp.base_salary
                if title.annual_increment_type == "percentage":
                    salary_after = round(salary_before * (1 + title.annual_increment_value / 100), 2)
                    inc_str = f"+{title.annual_increment_value}%"
                else:
                    salary_after = round(salary_before + title.annual_increment_value, 2)
                    inc_str = f"+${title.annual_increment_value:,.2f}"
                self.increment_data.append({
                    "id": emp.id,
                    "name": emp.full_name,
                    "emp_id": emp.employee_id,
                    "salary_before": salary_before,
                    "salary_after": salary_after,
                    "increment_str": inc_str,
                })

            now = datetime.utcnow()
            recent = session.query(AuditLog).order_by(AuditLog.performed_at.desc(), AuditLog.id.desc()).limit(50).all()
            recent = [log for log in recent if not log.performed_at or log.performed_at <= now][:5]
            self.logs_data = [
                {
                    "action": (log.action or "Activity").replace(".", " ").replace("_", " ").title(),
                    "target": log.description or t("organization_record_updated"),
                    "user": log.performed_by_name or (log.performed_by.full_name if log.performed_by else "System"),
                    "time": log.performed_at.strftime("%b %d, %H:%M") if log.performed_at else "",
                }
                for log in recent
            ]

            upcoming = []
            eligible_now = 0
            due_three = 0
            due_six = 0
            other_track_count = 0
            blocked_by_sanction = set()
            active_sanctions = session.query(Sanction).filter_by(is_resolved=False).all()
            for sanction in active_sanctions:
                blocked_by_sanction.add(sanction.employee_id)
            active_emps = session.query(Employee).filter_by(status="active").all()
            races = calculate_months_remaining_batch(active_emps, session)
            for emp in active_emps:
                if emp.title and emp.title.name == "Other":
                    other_track_count += 1
                race = races.get(emp.id)
                if not race:
                    continue
                if not race["has_next_level"]:
                    continue
                if race["eligible"]:
                    self.promotion_count += 1
                    eligible_now += 1
                months_remaining = race["months_remaining"]
                if 1 <= months_remaining <= 3:
                    due_three += 1
                if 4 <= months_remaining <= 6:
                    due_six += 1
                if months_remaining > 12:
                    continue
                next_title = titles_by_id.get(race["next_title_id"])
                upcoming.append({
                    "name": emp.full_name,
                    "current": emp.title.name if emp.title else "?",
                    "next": next_title.name if next_title else "?",
                    "months_remaining": months_remaining,
                    "eligible": race["eligible"],
                    "progress_pct": race["progress_pct"],
                })
            upcoming.sort(key=lambda x: (0 if x["eligible"] else 1, x["months_remaining"]))
            self.upcoming_promotions = upcoming[:3]
            self.promotion_delta = f"+{self.promotion_count}"
            self.department_chart_data = self._org_distribution(session, self.org_chart_level)
            self.promotion_trend_data = self._promotion_trend(session, start, end)
            self.timeline_labels, self.timeline_series = self._workforce_timeline(
                session, self.workforce_filter, self.workforce_metric
            )
            self.promotion_pipeline = {
                "eligible_now": eligible_now,
                "due_three": due_three,
                "due_six": due_six,
            }
            self.increment_queue = self._increment_queue(active_emps)
            self.attention_signals = [
                {
                    "label": t("active_sanctions"),
                    "value": len(active_sanctions),
                    "detail": t("open_disciplinary_actions"),
                    "color": chart_color("sanction"),
                    "target": "sanctions_active",
                },
                {
                    "label": t("sanction_delay_months"),
                    "value": sum(s.delay_months for s in active_sanctions),
                    "detail": t("total_months_added_to_races"),
                    "color": chart_color("sanction"),
                    "target": "sanctions_active",
                },
                {
                    "label": t("other_track"),
                    "value": other_track_count,
                    "detail": t("misc_employees_dashboard_note"),
                    "color": chart_color("neutral"),
                    "target": "employees",
                },
            ]
        finally:
            session.close()

    def _org_distribution(self, session, level):
        units = {unit.id: unit for unit in session.query(OrgUnit).all()}

        def display_label(label):
            return t("other_track") if label == OTHER_ORG_UNIT_NAME else label

        def level_label(org_unit_id):
            unit = units.get(org_unit_id)
            fallback = display_label(unit.name) if unit else t("not_available")
            while unit is not None:
                if unit.unit_type == level:
                    return display_label(unit.name)
                unit = units.get(unit.parent_id) if unit.parent_id else None
            return fallback

        counts = {}
        employee_units = (
            session.query(Employee.org_unit_id)
            .filter(Employee.status == "active")
            .all()
        )
        for (org_unit_id,) in employee_units:
            label = level_label(org_unit_id)
            counts[label] = counts.get(label, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if level == "division" or len(ranked) <= 14:
            return ranked
        top = ranked[:13]
        grouped_count = sum(value for _, value in ranked[13:])
        return top + [(t(f"all_other_{level}s"), grouped_count)]

    def _workforce_timeline(self, session, filter_key, metric):
        buckets = _timeline_buckets(filter_key)
        labels = [label for label, _, _ in buckets]

        headcount_values = []
        promotion_values = []
        increment_values = []

        for _, bucket_start, bucket_end in buckets:
            headcount_values.append(
                session.query(Employee.id).filter(
                    Employee.status == "active",
                    Employee.join_date != None,
                    Employee.join_date < bucket_end,
                ).count()
            )
            promotion_values.append(
                session.query(PromotionHistory.id).filter(
                    PromotionHistory.promoted_at != None,
                    PromotionHistory.promoted_at >= bucket_start,
                    PromotionHistory.promoted_at < bucket_end,
                ).count()
            )
            increment_values.append(
                session.query(SalaryIncrementHistory.id).filter(
                    SalaryIncrementHistory.applied_at != None,
                    SalaryIncrementHistory.applied_at >= bucket_start,
                    SalaryIncrementHistory.applied_at < bucket_end,
                ).count()
            )

        options = {
            "headcount": (t("headcount"), headcount_values, "headcount"),
            "promotions": (t("promotions"), promotion_values, "promotion"),
            "increments": (t("increments"), increment_values, "increment"),
        }
        if metric == "all":
            return labels, list(options.values())
        return labels, [options.get(metric, options["headcount"])]

    def _increment_queue(self, active_employees):
        today = datetime.utcnow()
        buckets = {
            "due_now": self.increment_count,
            "next_30": 0,
            "next_60": 0,
            "next_90": 0,
        }
        due_ids = {row["id"] for row in self.increment_data}
        for emp in active_employees:
            if emp.id in due_ids or not emp.join_date:
                continue
            if (today - emp.join_date).days < 365:
                continue
            anniversary = _safe_anniversary(emp.join_date, today.year)
            if anniversary <= today:
                anniversary = _safe_anniversary(emp.join_date, today.year + 1)
            days_until = (anniversary - today).days
            if 0 < days_until <= 30:
                buckets["next_30"] += 1
            elif 30 < days_until <= 60:
                buckets["next_60"] += 1
            elif 60 < days_until <= 90:
                buckets["next_90"] += 1
        return buckets

    def _promotion_trend(self, session, start, end):
        promotions = session.query(PromotionHistory.promoted_at).filter(
            PromotionHistory.promoted_at >= start,
            PromotionHistory.promoted_at <= end,
        ).all()
        dates = [row[0] for row in promotions if row[0]]
        span_days = max((end - start).days, 1)
        if span_days <= 45:
            labels = []
            cursor = datetime(start.year, start.month, start.day)
            end_day = datetime(end.year, end.month, end.day)
            while cursor <= end_day:
                labels.append(cursor.strftime("%b %d"))
                cursor += timedelta(days=1)
            counts = {label: 0 for label in labels}
            for dt in dates:
                label = dt.strftime("%b %d")
                if label in counts:
                    counts[label] += 1
            if len(labels) > 14:
                compact = []
                for i in range(0, len(labels), 3):
                    label_slice = labels[i:i + 3]
                    compact.append((label_slice[0], sum(counts[label] for label in label_slice)))
                return compact
            return [(label, counts[label]) for label in labels]

        labels = []
        cursor = datetime(start.year, start.month, 1)
        end_month = datetime(end.year, end.month, 1)
        while cursor <= end_month:
            labels.append(_month_key(cursor))
            if cursor.month == 12:
                cursor = datetime(cursor.year + 1, 1, 1)
            else:
                cursor = datetime(cursor.year, cursor.month + 1, 1)
        counts = {label: 0 for label in labels}
        for dt in dates:
            key = _month_key(dt)
            if key in counts:
                counts[key] += 1
        return [(datetime.strptime(label, "%Y-%m").strftime("%b"), counts[label]) for label in labels]

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(scroll_ss())

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        content.setStyleSheet(f"background: {tokens().canvas};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("dashboard_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {tokens().text}; background: transparent;")
        subtitle = QLabel(t("dashboard_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {tokens().text_muted}; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(32)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        add_btn = QPushButton("  " + t("add_employee"))
        add_btn.setIcon(app_icon("fa5s.user-plus", color=primary_button_fg(), size=16))
        add_btn.setIconSize(_ICO)
        add_btn.setFixedHeight(44)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(btn_primary(44))
        add_btn.clicked.connect(lambda: self.navigate("employees"))

        imp_btn = QPushButton("  " + t("nav_import"))
        imp_btn.setIcon(app_icon("fa5s.calendar", color=tokens().text, size=16))
        imp_btn.setIconSize(_ICO)
        imp_btn.setFixedHeight(44)
        imp_btn.setCursor(Qt.PointingHandCursor)
        imp_btn.setStyleSheet(btn_outline(44))
        imp_btn.clicked.connect(lambda: self.navigate("import_data"))

        if is_rtl():
            actions.addStretch()
            actions.addWidget(imp_btn)
            actions.addWidget(add_btn)
        else:
            actions.addWidget(add_btn)
            actions.addWidget(imp_btn)
            actions.addStretch()
        layout.addLayout(actions)
        layout.addSpacing(32)

        if self.increment_count > 0:
            layout.addWidget(self._increment_alert())
            layout.addSpacing(24)

        self.stats_layout = QGridLayout()
        self.stats_layout.setHorizontalSpacing(20)
        self.stats_layout.setVerticalSpacing(20)
        self.stat_cards = [
            self._stat_card(t("total_employees"), str(self.emp_count), self.employee_delta, t("new_ytd"), "headcount", "fa5s.users"),
            self._stat_card(t("pending_promotions"), str(self.promotion_count), self.promotion_delta, t("eligible_now_snapshot"), "promotion", "fa5s.chart-line"),
            self._stat_card(t("commendations"), str(self.commend_count), self.commend_delta, t("vs_previous_ytd"), "commendation", "fa5s.award"),
            self._stat_card(t("active_sanctions"), str(self.sanction_count), self.sanction_delta, t("issued_vs_previous_ytd"), "sanction", "fa5s.exclamation-triangle"),
        ]
        layout.addLayout(self.stats_layout)
        layout.addSpacing(28)

        self.charts_layout = QGridLayout()
        self.charts_layout.setHorizontalSpacing(20)
        self.charts_layout.setVerticalSpacing(20)
        self.department_card = self._department_chart_card()
        self.promotion_card = self._promotion_chart_card()
        layout.addLayout(self.charts_layout)
        layout.addSpacing(28)

        self.insights_layout = QGridLayout()
        self.insights_layout.setHorizontalSpacing(20)
        self.insights_layout.setVerticalSpacing(20)
        self.timeline_card = self._workforce_timeline_card()
        self.priority_card = self._priority_signals_card()
        layout.addLayout(self.insights_layout)
        layout.addSpacing(28)

        self.bottom_layout = QGridLayout()
        self.bottom_layout.setHorizontalSpacing(20)
        self.bottom_layout.setVerticalSpacing(20)
        self.recent_card = self._recent_card()
        self.upcoming_card = self._upcoming_card()
        layout.addLayout(self.bottom_layout)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._dashboard_compact = None
        self._apply_responsive_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "stats_layout"):
            self._apply_responsive_layout()

    def _clear_layout(self, layout):
        while layout.count():
            layout.takeAt(0)

    def _apply_responsive_layout(self):
        compact = self.width() < 1280
        if getattr(self, "_dashboard_compact", None) == compact:
            return
        self._dashboard_compact = compact

        self._clear_layout(self.stats_layout)
        stats_columns = 2 if compact else 4
        for index, card in enumerate(self.stat_cards):
            self.stats_layout.addWidget(card, index // stats_columns, index % stats_columns)
        for column in range(4):
            self.stats_layout.setColumnStretch(column, 1 if column < stats_columns else 0)

        self._clear_layout(self.charts_layout)
        if compact:
            self.charts_layout.addWidget(self.department_card, 0, 0)
            self.charts_layout.addWidget(self.promotion_card, 1, 0)
            self.charts_layout.setColumnStretch(0, 1)
        else:
            self.charts_layout.addWidget(self.department_card, 0, 0)
            self.charts_layout.addWidget(self.promotion_card, 0, 1)
            self.charts_layout.setColumnStretch(0, 1)
            self.charts_layout.setColumnStretch(1, 1)

        self._clear_layout(self.insights_layout)
        if compact:
            self.insights_layout.addWidget(self.timeline_card, 0, 0)
            self.insights_layout.addWidget(self.priority_card, 1, 0)
            self.insights_layout.setColumnStretch(0, 1)
        else:
            self.insights_layout.addWidget(self.timeline_card, 0, 0)
            self.insights_layout.addWidget(self.priority_card, 0, 1)
            self.insights_layout.setColumnStretch(0, 2)
            self.insights_layout.setColumnStretch(1, 1)

        self._clear_layout(self.bottom_layout)
        if compact:
            self.bottom_layout.addWidget(self.recent_card, 0, 0)
            self.bottom_layout.addWidget(self.upcoming_card, 1, 0)
            self.bottom_layout.setColumnStretch(0, 1)
        else:
            self.bottom_layout.addWidget(self.recent_card, 0, 0)
            self.bottom_layout.addWidget(self.upcoming_card, 0, 1)
            self.bottom_layout.setColumnStretch(0, 1)
            self.bottom_layout.setColumnStretch(1, 1)

    def _increment_alert(self):
        accent = chart_color("increment")
        soft = chart_soft_color("increment")
        alert = QFrame()
        alert.setObjectName("IncrementAlert")
        alert.setMinimumHeight(64)
        alert.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        alert.setStyleSheet(
            f"QFrame#IncrementAlert {{ background: {soft}; border: 1px solid {accent}; border-radius: 8px; }}"
            "QFrame#IncrementAlert QLabel { border: none; background: transparent; }"
        )
        row = QHBoxLayout(alert)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: {tokens().surface}; border: 1px solid {tokens().border}; border-radius: 8px;")
        icon.setPixmap(app_pixmap("fa5s.coins", color=accent, size=15))
        row.addWidget(icon)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        title = QLabel(t("salary_increment_due"))
        title.setStyleSheet(f"font-size: 13px; color: {tokens().text}; font-weight: 700;")
        txt = QLabel(t("salary_increment_prompt", count=self.increment_count))
        txt.setWordWrap(True)
        txt.setStyleSheet(f"font-size: 12px; color: {tokens().text_muted}; font-weight: 500;")
        copy.addWidget(title)
        copy.addWidget(txt)
        row.addLayout(copy, 1)

        btn = QPushButton(t("review"))
        btn.setFixedHeight(34)
        btn.setMinimumWidth(90)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(btn_outline(34))
        btn.clicked.connect(self._open_increment_dialog)
        row.addWidget(btn)
        return alert

    def _open_increment_dialog(self):
        SalaryIncrementReviewDialog(self.increment_data, self.user, parent=self).exec()

    def _card(self):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setStyleSheet(dashboard_card_ss())
        return card

    def _stat_card(self, label, value, delta, detail, color_key, icon_name):
        card = self._card()
        card.setMinimumHeight(132)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        accent = chart_color(color_key)
        soft = chart_soft_color(color_key)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        text = QVBoxLayout()
        text.setSpacing(8)
        label_lbl = QLabel(label)
        label_lbl.setWordWrap(True)
        label_lbl.setMinimumWidth(0)
        label_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label_lbl.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted}; font-weight: 700;")
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {tokens().text};")
        delta_color = tokens().success if not str(delta).startswith("-") else tokens().danger
        change_lbl = QLabel(f"{delta} {detail}")
        change_lbl.setWordWrap(True)
        change_lbl.setMinimumWidth(0)
        change_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        change_lbl.setStyleSheet(f"font-size: 12px; color: {delta_color}; font-weight: 700;")
        change_lbl.setToolTip(f"{delta} {detail}")
        text.addWidget(label_lbl)
        text.addWidget(value_lbl)
        text.addWidget(change_lbl)
        layout.addLayout(text, 1)

        icon_box = QLabel()
        icon_box.setFixedSize(42, 42)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(
            f"background: {soft}; border: 1px solid {tokens().border}; border-radius: 8px;"
        )
        icon_box.setPixmap(app_pixmap(icon_name, color=accent, size=22))
        layout.addWidget(icon_box, 0, Qt.AlignTop)
        return card

    def _department_chart_card(self):
        card = self._card()
        card.setMinimumHeight(390)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self.org_chart_title = QLabel(t("employees_by_division"))
        self.org_chart_title.setMinimumWidth(220)
        self.org_chart_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.org_chart_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        header.addWidget(self.org_chart_title, 1)
        header.addLayout(self._org_filter_pills(), 0)
        layout.addLayout(header)

        self.department_chart = BarChartWidget(self.department_chart_data, self.org_chart_level)
        layout.addWidget(self.department_chart, 1)
        return card

    def _org_filter_pills(self):
        row = QHBoxLayout()
        row.setSpacing(6)
        self.org_filter_buttons = {}
        labels = {
            "division": t("filter_division"),
            "department": t("filter_department"),
            "unit": t("filter_unit"),
            "team": t("filter_team"),
        }
        for key in ORG_LEVELS:
            btn = QPushButton(labels[key])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, value=key: self._set_org_chart_level(value))
            self.org_filter_buttons[key] = btn
            row.addWidget(btn)
        self._sync_org_filter_buttons()
        return row

    def _sync_org_filter_buttons(self):
        for key, btn in self.org_filter_buttons.items():
            btn.setStyleSheet(self._filter_button_ss(key == self.org_chart_level))

    def _set_org_chart_level(self, level):
        self.org_chart_level = level
        session = get_session()
        try:
            self.department_chart_data = self._org_distribution(session, level)
        finally:
            session.close()
        self.department_chart.color = level
        self.department_chart.set_data(self.department_chart_data)
        self.org_chart_title.setText(t(f"employees_by_{level}"))
        self._sync_org_filter_buttons()

    def _promotion_chart_card(self):
        card = self._card()
        card.setMinimumHeight(340)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel(t("promotion_trend"))
        title.setMinimumWidth(180)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        header.addWidget(title, 1)
        header.addLayout(self._filter_pills(), 0)
        layout.addLayout(header)

        self.promotion_chart = LineChartWidget(self.promotion_trend_data, "promotion")
        layout.addWidget(self.promotion_chart, 1)
        return card

    def _filter_pills(self):
        row = QHBoxLayout()
        row.setSpacing(6)
        self.filter_buttons = {}
        labels = {
            "week": t("filter_week"),
            "month": t("filter_month"),
            "year": t("filter_year"),
            "ytd": t("filter_ytd"),
            "custom": t("filter_custom"),
        }
        for key in FILTERS:
            btn = QPushButton(labels[key])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, value=key: self._set_chart_filter(value))
            self.filter_buttons[key] = btn
            row.addWidget(btn)
        self._sync_filter_buttons()
        return row

    def _filter_button_ss(self, active):
        tkn = tokens()
        active_bg = chart_color("promotion") if tkn.name == THEME_DARK else tkn.brand
        active_text = "#062f28" if tkn.name == THEME_DARK else "#ffffff"
        if active:
            return (
                f"QPushButton {{ background: {active_bg}; color: {active_text}; border: none; "
                "border-radius: 15px; padding: 0 14px; font-size: 12px; font-weight: 700; }"
            )
        return (
            f"QPushButton {{ background: {tkn.surface_muted}; color: {tkn.text_muted}; border: 1px solid {tkn.border}; "
            "border-radius: 15px; padding: 0 14px; font-size: 12px; font-weight: 600; }"
            f"QPushButton:hover {{ background: {tkn.hover}; color: {tkn.text}; }}"
        )

    def _sync_filter_buttons(self):
        for key, btn in self.filter_buttons.items():
            btn.setStyleSheet(self._filter_button_ss(key == self.chart_filter))

    def _set_chart_filter(self, filter_key):
        if filter_key == "custom" and not self._choose_custom_range():
            return
        self.chart_filter = filter_key
        session = get_session()
        try:
            start, end, _, _ = _filter_window(self.chart_filter, self.custom_start, self.custom_end)
            self.promotion_trend_data = self._promotion_trend(session, start, end)
        finally:
            session.close()
        self.promotion_chart.set_data(self.promotion_trend_data)
        self._sync_filter_buttons()

    def _choose_custom_range(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(t("custom_date_range"))
        dialog.setStyleSheet(f"background: {tokens().surface}; color: {tokens().text};")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(t("custom_date_range"))
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {tokens().text};")
        layout.addWidget(title)

        start_edit = QDateEdit()
        start_edit.setCalendarPopup(True)
        start_edit.setDisplayFormat("yyyy-MM-dd")
        end_edit = QDateEdit()
        end_edit.setCalendarPopup(True)
        end_edit.setDisplayFormat("yyyy-MM-dd")

        today = QDate.currentDate()
        default_start = today.addMonths(-1)
        start_edit.setDate(default_start)
        end_edit.setDate(today)

        layout.addWidget(QLabel(t("start_date")))
        layout.addWidget(start_edit)
        layout.addWidget(QLabel(t("end_date")))
        layout.addWidget(end_edit)

        row = QHBoxLayout()
        apply_btn = QPushButton(t("apply"))
        apply_btn.setStyleSheet(btn_primary(36))
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setStyleSheet(btn_outline(36))
        apply_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        row.addStretch()
        row.addWidget(cancel_btn)
        row.addWidget(apply_btn)
        layout.addLayout(row)

        custom_btn = self.filter_buttons.get("custom")
        if custom_btn:
            pos = custom_btn.mapToGlobal(custom_btn.rect().bottomRight())
            dialog.adjustSize()
            dialog.move(pos.x() - dialog.width(), pos.y() + 8)

        if dialog.exec() != QDialog.Accepted:
            return False
        start_date = start_edit.date().toPython()
        end_date = end_edit.date().toPython()
        if start_date > end_date:
            _warning(self, t("warning"), t("invalid_date_range"))
            return False
        self.custom_start = datetime(start_date.year, start_date.month, start_date.day)
        self.custom_end = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        return True

    def _workforce_timeline_card(self):
        card = self._card()
        card.setMinimumHeight(360)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(t("workforce_timeline"))
        title.setMinimumWidth(220)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        header.addWidget(title, 1)
        header.addLayout(self._workforce_filter_pills(), 0)
        layout.addLayout(header)

        metric_row = QHBoxLayout()
        metric_row.addStretch()
        metric_row.addLayout(self._workforce_metric_pills())
        metric_row.addStretch()
        layout.addLayout(metric_row)

        self.timeline_chart = WorkforceTimelineWidget(self.timeline_labels, self.timeline_series)
        layout.addWidget(self.timeline_chart, 1)
        return card

    def _workforce_filter_pills(self):
        row = QHBoxLayout()
        row.setSpacing(6)
        self.workforce_filter_buttons = {}
        labels = {
            "week": t("filter_week"),
            "month": t("filter_month"),
            "year": t("filter_year"),
            "ytd": t("filter_ytd"),
        }
        for key in WORKFORCE_FILTERS:
            btn = QPushButton(labels[key])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, value=key: self._set_workforce_filter(value))
            self.workforce_filter_buttons[key] = btn
            row.addWidget(btn)
        self._sync_workforce_filter_buttons()
        return row

    def _workforce_metric_pills(self):
        row = QHBoxLayout()
        row.setSpacing(6)
        self.workforce_metric_buttons = {}
        labels = {
            "headcount": t("headcount"),
            "promotions": t("promotions"),
            "increments": t("increments"),
            "all": t("all"),
        }
        for key in WORKFORCE_METRICS:
            btn = QPushButton(labels[key])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda _, value=key: self._set_workforce_metric(value))
            self.workforce_metric_buttons[key] = btn
            row.addWidget(btn)
        self._sync_workforce_metric_buttons()
        return row

    def _sync_workforce_filter_buttons(self):
        for key, btn in self.workforce_filter_buttons.items():
            btn.setStyleSheet(self._filter_button_ss(key == self.workforce_filter))

    def _sync_workforce_metric_buttons(self):
        for key, btn in self.workforce_metric_buttons.items():
            btn.setStyleSheet(self._filter_button_ss(key == self.workforce_metric))

    def _refresh_workforce_chart(self):
        session = get_session()
        try:
            self.timeline_labels, self.timeline_series = self._workforce_timeline(
                session, self.workforce_filter, self.workforce_metric
            )
        finally:
            session.close()
        self.timeline_chart.set_data(self.timeline_labels, self.timeline_series)

    def _set_workforce_filter(self, filter_key):
        self.workforce_filter = filter_key
        self._refresh_workforce_chart()
        self._sync_workforce_filter_buttons()

    def _set_workforce_metric(self, metric):
        self.workforce_metric = metric
        self._refresh_workforce_chart()
        self._sync_workforce_metric_buttons()

    def _priority_signals_card(self):
        card = self._card()
        card.setMinimumHeight(390)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(t("priority_signals"))
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        layout.addWidget(title)

        pipeline = QFrame()
        pipeline.setObjectName("SignalBlock")
        pipeline.setStyleSheet(
            f"QFrame#SignalBlock {{ background: {tokens().surface_muted}; border: 1px solid {tokens().border}; border-radius: 8px; }}"
            "QFrame#SignalBlock QLabel { background: transparent; border: none; }"
        )
        pl = QVBoxLayout(pipeline)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(12)
        pl.addWidget(self._section_label(t("promotion_pipeline")))
        pl.addLayout(self._metric_strip([
            (t("eligible_now_short"), self.promotion_pipeline["eligible_now"], chart_color("promotion")),
            (t("due_in_3_months"), self.promotion_pipeline["due_three"], chart_color("increment")),
            (t("due_in_6_months"), self.promotion_pipeline["due_six"], chart_color("neutral")),
        ]))
        layout.addWidget(pipeline)

        queue = QFrame()
        queue.setObjectName("SignalBlock")
        queue.setStyleSheet(pipeline.styleSheet())
        ql = QVBoxLayout(queue)
        ql.setContentsMargins(16, 14, 16, 14)
        ql.setSpacing(10)
        ql.addWidget(self._section_label(t("salary_increment_queue")))
        max_queue = max(self.increment_queue.values()) if self.increment_queue else 1
        for label_key, bucket_key in [
            ("due_now", "due_now"),
            ("next_30_days", "next_30"),
            ("next_60_days", "next_60"),
            ("next_90_days", "next_90"),
        ]:
            ql.addWidget(self._queue_row(t(label_key), self.increment_queue.get(bucket_key, 0), max_queue))
        layout.addWidget(queue)

        for signal in self.attention_signals:
            layout.addWidget(self._attention_row(signal))
        layout.addStretch()
        return card

    def _section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 12px; color: {tokens().text_muted}; font-weight: 800;")
        return label

    def _metric_strip(self, metrics):
        row = QHBoxLayout()
        row.setSpacing(8)
        for label, value, color in metrics:
            box = QFrame()
            box.setObjectName("MetricBox")
            box.setMinimumHeight(58)
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            box.setStyleSheet(
                f"QFrame#MetricBox {{ background: {tokens().surface}; border: 1px solid {tokens().border}; border-radius: 8px; }}"
                "QFrame#MetricBox QLabel { background: transparent; border: none; }"
            )
            box_l = QVBoxLayout(box)
            box_l.setContentsMargins(10, 8, 10, 8)
            box_l.setSpacing(2)
            value_lbl = QLabel(str(value))
            value_lbl.setAlignment(Qt.AlignCenter)
            value_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {color};")
            label_lbl = QLabel(label)
            label_lbl.setAlignment(Qt.AlignCenter)
            label_lbl.setWordWrap(True)
            label_lbl.setStyleSheet(f"font-size: 11px; color: {tokens().text_soft};")
            box_l.addWidget(value_lbl)
            box_l.addWidget(label_lbl)
            row.addWidget(box, 1)
        return row

    def _queue_row(self, label, value, max_value):
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = QLabel(label)
        name.setFixedWidth(84)
        name.setStyleSheet(f"font-size: 12px; color: {tokens().text_muted};")
        layout.addWidget(name)

        progress = QProgressBar()
        progress.setRange(0, max(1, max_value))
        progress.setValue(value)
        progress.setFixedHeight(8)
        progress.setTextVisible(False)
        progress.setStyleSheet(_mini_progress_ss("increment", radius=4))
        layout.addWidget(progress, 1)

        value_lbl = QLabel(str(value))
        value_lbl.setFixedWidth(28)
        value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_lbl.setStyleSheet(f"font-size: 12px; color: {tokens().text}; font-weight: 700;")
        layout.addWidget(value_lbl)
        return row

    def _attention_row(self, signal):
        row = QFrame()
        row.setObjectName("AttentionRow")
        row.setStyleSheet(
            f"QFrame#AttentionRow {{ background: {tokens().surface}; border: 1px solid {tokens().border}; border-radius: 8px; }}"
            "QFrame#AttentionRow QLabel { background: transparent; border: none; }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {signal['color']}; border-radius: 5px;")
        layout.addWidget(dot, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(3)
        label = QLabel(signal["label"])
        label.setStyleSheet(f"font-size: 13px; color: {tokens().text}; font-weight: 800;")
        detail = QLabel(signal["detail"])
        detail.setWordWrap(True)
        detail.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft};")
        text.addWidget(label)
        text.addWidget(detail)
        layout.addLayout(text, 1)

        value = QLabel(str(signal["value"]))
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setStyleSheet(f"font-size: 20px; color: {signal['color']}; font-weight: 800;")
        layout.addWidget(value)

        action = QPushButton(t("view"))
        action.setCursor(Qt.PointingHandCursor)
        action.setFixedHeight(28)
        action.setStyleSheet(btn_ghost(28))
        action.clicked.connect(lambda checked=False, target=signal.get("target"): self._open_priority_signal(target))
        layout.addWidget(action)
        return row

    def _open_priority_signal(self, target):
        if target:
            self.navigate(target)

    def _recent_card(self):
        card = self._card()
        card.setMinimumHeight(420)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        header = QHBoxLayout()
        title = QLabel(t("recent_activity"))
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        view = QPushButton(t("view_all"))
        view.setCursor(Qt.PointingHandCursor)
        view.setStyleSheet(btn_ghost(32))
        view.clicked.connect(lambda: self.navigate("audit_log"))
        header.addWidget(title)
        header.addStretch()
        header.addWidget(view)
        layout.addLayout(header)
        layout.addSpacing(20)

        if self.logs_data:
            for index, item in enumerate(self.logs_data[:5]):
                layout.addWidget(self._activity_row(item, index == len(self.logs_data[:5]) - 1))
        else:
            empty = QLabel(t("no_recent_activity"))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"font-size: 15px; color: {tokens().text_soft}; background: {tokens().surface_muted}; "
                "border: none; border-radius: 8px; padding: 28px;"
            )
            layout.addWidget(empty)
        layout.addStretch()
        return card

    def _activity_row(self, item, is_last):
        row = QFrame()
        row.setObjectName("ActivityRow")
        row.setMinimumHeight(76)
        border = "none" if is_last else f"1px solid {tokens().border}"
        row.setStyleSheet(
            f"QFrame#ActivityRow {{ background: transparent; border: none; border-bottom: {border}; border-radius: 0; }}"
            "QFrame#ActivityRow QLabel { border: none; background: transparent; }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(14)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {chart_color('promotion')}; border: none; border-radius: 4px;")
        layout.addWidget(dot, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(4)
        action = QLabel(item["action"])
        action.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {tokens().text};")
        target = QLabel(item["target"])
        target.setWordWrap(True)
        target.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted};")
        byline = QLabel(t("by_user", user=item["user"]))
        byline.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft};")
        text.addWidget(action)
        text.addWidget(target)
        text.addWidget(byline)
        layout.addLayout(text, 1)

        time = QLabel(item["time"])
        time.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft};")
        layout.addWidget(time, 0, Qt.AlignTop)
        return row

    def _upcoming_card(self):
        card = self._card()
        card.setMinimumHeight(420)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        header = QHBoxLayout()
        title = QLabel(t("upcoming_promotions"))
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {tokens().text};")
        view = QPushButton(t("view_all"))
        view.setCursor(Qt.PointingHandCursor)
        view.setStyleSheet(btn_ghost(32))
        view.clicked.connect(lambda: self.navigate("promotions"))
        header.addWidget(title)
        header.addStretch()
        header.addWidget(view)
        layout.addLayout(header)
        layout.addSpacing(20)

        if self.upcoming_promotions:
            for index, item in enumerate(self.upcoming_promotions[:3]):
                layout.addWidget(self._promo_row(item))
                if index < len(self.upcoming_promotions[:3]) - 1:
                    layout.addSpacing(14)
        else:
            empty = QLabel(t("no_upcoming_promotions"))
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"font-size: 15px; color: {tokens().text_soft}; background: {tokens().surface_muted}; "
                "border: none; border-radius: 8px; padding: 28px;"
            )
            layout.addWidget(empty)
        layout.addStretch()
        return card

    def _promo_row(self, item):
        row = QFrame()
        row.setObjectName("PromoRow")
        row.setMinimumHeight(118)
        row.setStyleSheet(
            f"QFrame#PromoRow {{ background: {tokens().surface}; border: 1px solid {tokens().border}; border-radius: 8px; }}"
            "QFrame#PromoRow QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(row)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(6)
        name = QLabel(item["name"])
        name.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {tokens().text};")
        level = QLabel(f"{item['current']} to {item['next']}")
        level.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted};")
        text.addWidget(name)
        text.addWidget(level)
        top.addLayout(text)
        top.addStretch()

        badge_text = item.get("badge")
        if not badge_text:
            badge_text = "Eligible" if item["eligible"] else f"{item['months_remaining']} mo"
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignCenter)
        badge_status = "eligible" if item["eligible"] else "progress"
        badge.setStyleSheet(
            f"background: {race_soft_color(badge_status)}; color: {race_color(badge_status)}; border: none; "
            "border-radius: 12px; padding: 3px 9px; font-size: 12px; font-weight: 700;"
        )
        top.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(top)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(item["progress_pct"])
        progress.setFixedHeight(6)
        progress.setTextVisible(False)
        progress.setStyleSheet(race_progress_bar_ss("eligible" if item["eligible"] else "progress", radius=3))
        layout.addWidget(progress)

        complete = QLabel(f"{item['progress_pct']}% complete")
        complete.setStyleSheet(f"font-size: 12px; color: {tokens().text_soft};")
        layout.addWidget(complete)
        return row


def _styled_message_box(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet(message_box_ss())
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)
