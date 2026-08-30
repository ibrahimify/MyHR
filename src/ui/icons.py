from __future__ import annotations

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


_ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons" / "lucide"
_CACHE: dict[tuple[str, str, int, float], QIcon] = {}

_ALIASES = {
    "dashboard": "layout-dashboard",
    "employees": "users",
    "hierarchy": "network",
    "promotions": "chart-no-axes-combined",
    "commendations": "medal",
    "sanctions": "triangle-alert",
    "audit": "clipboard-list",
    "import": "cloud-upload",
    "settings": "settings",
    "logout": "log-out",
    "company": "building",
    "profile": "user",
    "language": "globe",
    "password": "lock",
    "back": "arrow-left",
    "save": "save",
    "money": "coins",
    "edit": "square-pen",
    "delete": "trash-2",
    "success": "circle-check",
    "warning": "circle-alert",
}

_QTA_TO_LUCIDE = {
    "fa5s.th-large": "layout-dashboard",
    "fa5s.users": "users",
    "fa5s.user-friends": "users",
    "fa5s.building": "building",
    "fa5s.chart-line": "chart-no-axes-combined",
    "fa5s.award": "medal",
    "fa5s.exclamation-triangle": "triangle-alert",
    "fa5s.clipboard-list": "clipboard-list",
    "fa5s.cloud-upload-alt": "cloud-upload",
    "fa5s.cog": "settings",
    "fa5s.sign-out-alt": "log-out",
    "fa5s.user": "user",
    "fa5s.chevron-down": "chevron-down",
    "fa5s.globe": "globe",
    "fa5s.lock": "lock",
    "fa5s.eye": "eye",
    "fa5s.eye-slash": "eye-off",
    "fa5s.user-plus": "user-plus",
    "fa5s.arrow-left": "arrow-left",
    "fa5s.arrow-right": "arrow-right",
    "fa5s.save": "save",
    "fa5s.coins": "coins",
    "fa5s.check-double": "check-check",
    "fa5s.calendar": "calendar",
    "fa5s.calendar-alt": "calendar",
    "fa5s.search": "search",
    "fa5s.plus": "plus",
    "fa5s.edit": "square-pen",
    "fa5s.trash-alt": "trash-2",
    "fa5s.check": "check",
    "fa5s.check-circle": "circle-check",
    "fa5s.download": "download",
    "fa5s.file-pdf": "file-text",
    "fa5s.database": "database",
    "fa5s.info-circle": "info",
    "fa5s.clock": "clock",
    "fa5s.stopwatch": "clock",
    "fa5s.upload": "upload",
    "fa5s.envelope": "mail",
    "fa5s.phone": "phone",
    "fa5s.map-marker-alt": "map-pin",
    "fa5s.graduation-cap": "graduation-cap",
    "fa5s.layer-group": "layers",
    "fa5s.sitemap": "workflow",
    "fa5s.briefcase": "briefcase-business",
    "fa5s.user-tie": "user-round",
    "fa5s.circle": "circle",
    "fa5s.chevron-right": "chevron-right",
    "fa5s.expand-arrows-alt": "maximize",
    "fa5s.undo": "rotate-ccw",
    "fa5s.file-alt": "file-text",
    "fa5s.route": "route",
    "fa5s.money-bill-wave": "banknote",
    "fa5s.user-cog": "user-cog",
    "fa5s.percentage": "percent",
    "fa5s.balance-scale": "scale",
    "fa5s.calendar-check": "calendar-check",
    "fa5s.users-cog": "users-round",
    "fa5s.shield-alt": "shield",
    "fa5s.key": "key-round",
    "fa5s.file-export": "file-output",
    "fa5s.heartbeat": "heart-pulse",
}


def app_icon(name: str, *, color: str = "#111827", size: int = 20) -> QIcon:
    """Return a themed app icon, preferring local Lucide SVGs with QtAwesome fallback."""
    lucide_name = _ALIASES.get(name, _QTA_TO_LUCIDE.get(name, name))
    path = _ICON_DIR / f"{lucide_name}.svg"
    if not path.exists():
        return qta.icon(name, color=color)

    dpr = _render_dpr()
    cache_key = (lucide_name, color.lower(), int(size), dpr)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    icon = QIcon(_render_svg_pixmap(path, color, int(size), dpr))
    _CACHE[cache_key] = icon
    return icon


def app_pixmap(name: str, *, color: str = "#111827", size: int = 20) -> QPixmap:
    lucide_name = _ALIASES.get(name, _QTA_TO_LUCIDE.get(name, name))
    path = _ICON_DIR / f"{lucide_name}.svg"
    if not path.exists():
        return qta.icon(name, color=color).pixmap(QSize(size, size))
    return _render_svg_pixmap(path, color, int(size), _render_dpr())


def _render_dpr() -> float:
    app = QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    screen_dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
    return min(max(screen_dpr, 2.0), 3.0)


def _render_svg_pixmap(path: Path, color: str, size: int, dpr: float) -> QPixmap:
    svg = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    physical_size = max(1, int(round(size * dpr)))
    pixmap = QPixmap(physical_size, physical_size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, physical_size, physical_size))
    painter.end()

    if pixmap.isNull():
        fallback = QPixmap(physical_size, physical_size)
        fallback.fill(QColor(color))
        fallback.setDevicePixelRatio(dpr)
        return fallback
    pixmap.setDevicePixelRatio(dpr)
    return pixmap
