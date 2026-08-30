"""Theme-aware colors for dashboard charts and data visualization."""

from src.ui.theme import THEME_DARK, tokens


_LIGHT = {
    "headcount": "#20352e",
    "dimension": "#0f8f5f",
    "division": "#0f8f5f",
    "department": "#0f8f5f",
    "unit": "#0f8f5f",
    "team": "#0f8f5f",
    "promotion": "#0f8f5f",
    "eligible": "#0f8f5f",
    "increment": "#8a6a18",
    "commendation": "#0f7a45",
    "sanction": "#c92323",
    "neutral": "#64748b",
}

_DARK = {
    "headcount": "#c7d0c9",
    "dimension": "#62cf87",
    "division": "#62cf87",
    "department": "#62cf87",
    "unit": "#62cf87",
    "team": "#62cf87",
    "promotion": "#62cf87",
    "eligible": "#62cf87",
    "increment": "#c0a15a",
    "commendation": "#72d38f",
    "sanction": "#ff6b6b",
    "neutral": "#9aa3ad",
}

_SOFT_LIGHT = {
    "headcount": "#edf1ee",
    "dimension": "#e5f6ed",
    "division": "#e5f6ed",
    "department": "#e5f6ed",
    "unit": "#e5f6ed",
    "team": "#e5f6ed",
    "promotion": "#e5f6ed",
    "eligible": "#e5f6ed",
    "increment": "#f4eddb",
    "commendation": "#e5f6ed",
    "sanction": "#fee8e8",
    "neutral": "#eef2f6",
}

_SOFT_DARK = {
    "headcount": "#222622",
    "dimension": "#1e3320",
    "division": "#1e3320",
    "department": "#1e3320",
    "unit": "#1e3320",
    "team": "#1e3320",
    "promotion": "#1e3320",
    "eligible": "#1e3320",
    "increment": "#2e2616",
    "commendation": "#1e3320",
    "sanction": "#351616",
    "neutral": "#1f242a",
}


def chart_color(key: str = "neutral") -> str:
    if key and str(key).startswith("#"):
        return str(key)
    palette = _DARK if tokens().name == THEME_DARK else _LIGHT
    return palette.get(str(key), palette["neutral"])


def chart_soft_color(key: str = "neutral") -> str:
    if key and str(key).startswith("#"):
        return tokens().surface_muted
    palette = _SOFT_DARK if tokens().name == THEME_DARK else _SOFT_LIGHT
    return palette.get(str(key), palette["neutral"])


def chart_grid_color() -> str:
    return "#242824" if tokens().name == THEME_DARK else "#edf0ed"


def chart_axis_color() -> str:
    return "#303530" if tokens().name == THEME_DARK else "#d8ddd8"
