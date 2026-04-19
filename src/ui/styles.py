"""Shared QSS constants matching the Figma MockUI design system."""

# ── Colors ────────────────────────────────────────────────────────────────────
CLR_BG          = "#f9fafb"
CLR_WHITE       = "white"
CLR_PRIMARY     = "#030213"      # near-black — buttons
CLR_BLUE        = "#2563eb"      # logo, active nav, links
CLR_BLUE_DARK   = "#1d4ed8"
CLR_BORDER      = "#e5e7eb"
CLR_TEXT        = "#111827"
CLR_TEXT_MUTED  = "#6b7280"
CLR_TEXT_LIGHT  = "#9ca3af"
CLR_INPUT_BG    = "#f3f3f5"
CLR_ROW_HOVER   = "#f9fafb"

# ── Button styles ─────────────────────────────────────────────────────────────
BTN_PRIMARY = """
QPushButton {{
    background: #030213; color: white; border: none;
    border-radius: 8px; font-size: 13px; font-weight: 600;
    padding: 0 16px; min-height: {h}px;
}}
QPushButton:hover   {{ background: #1a1d2e; }}
QPushButton:pressed {{ background: #111827; }}
QPushButton:disabled {{ background: #9ca3af; }}
"""

BTN_BLUE = """
QPushButton {{
    background: #2563eb; color: white; border: none;
    border-radius: 8px; font-size: 13px; font-weight: 600;
    padding: 0 16px; min-height: {h}px;
}}
QPushButton:hover   {{ background: #1d4ed8; }}
QPushButton:pressed {{ background: #1e40af; }}
"""

BTN_OUTLINE = """
QPushButton {{
    background: white; color: #374151;
    border: 1px solid #e5e7eb; border-radius: 8px;
    font-size: 13px; padding: 0 16px; min-height: {h}px;
}}
QPushButton:hover {{ background: #f9fafb; border-color: #d1d5db; }}
"""

BTN_GHOST = """
QPushButton {{
    background: transparent; color: #374151; border: none;
    border-radius: 8px; font-size: 13px; padding: 0 12px; min-height: {h}px;
}}
QPushButton:hover {{ background: #f3f4f6; }}
"""

BTN_DANGER = """
QPushButton {{
    background: #fee2e2; color: #dc2626; border: none;
    border-radius: 8px; font-size: 13px; font-weight: 600;
    padding: 0 16px; min-height: {h}px;
}}
QPushButton:hover {{ background: #fecaca; }}
"""

def btn_primary(h=34):  return BTN_PRIMARY.format(h=h)
def btn_blue(h=34):     return BTN_BLUE.format(h=h)
def btn_outline(h=34):  return BTN_OUTLINE.format(h=h)
def btn_ghost(h=34):    return BTN_GHOST.format(h=h)
def btn_danger(h=34):   return BTN_DANGER.format(h=h)

# ── Input style ───────────────────────────────────────────────────────────────
INPUT_SS = """
QLineEdit, QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 13px;
    color: #111827;
    background: #f3f3f5;
    min-height: 36px;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2563eb;
    background: white;
}
QComboBox {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 13px;
    color: #111827;
    background: #f3f3f5;
    min-height: 36px;
}
QComboBox:focus { border-color: #2563eb; background: white; }
"""

# ── Table style ───────────────────────────────────────────────────────────────
TABLE_SS = """
QTableWidget {
    background: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 13px;
    color: #111827;
    outline: none;
}
QTableWidget::item {
    padding: 0 12px;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
}
QTableWidget::item:selected {
    background: #eff6ff;
    color: #111827;
}
QHeaderView::section {
    background: #f9fafb;
    border: none;
    border-bottom: 2px solid #e5e7eb;
    padding: 0 12px;
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    min-height: 40px;
}
"""

# ── Card style ────────────────────────────────────────────────────────────────
CARD_SS = "background: white; border-radius: 10px; border: 1px solid #e5e7eb;"

# ── Page scroll area ──────────────────────────────────────────────────────────
SCROLL_SS = "border: none; background: transparent;"

# ── Tab bar ───────────────────────────────────────────────────────────────────
TAB_SS = """
QTabWidget::pane { border: none; background: #f9fafb; }
QTabBar::tab {
    background: transparent;
    color: #6b7280;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #030213;
    border-bottom: 2px solid #030213;
    font-weight: 600;
}
QTabBar::tab:hover { color: #111827; }
"""

# ── Badge helpers ─────────────────────────────────────────────────────────────
def badge_ss(bg, fg):
    return f"background: {bg}; color: {fg}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;"

BADGE_BLUE   = badge_ss("#dbeafe", "#1e40af")
BADGE_GREEN  = badge_ss("#dcfce7", "#166534")
BADGE_YELLOW = badge_ss("#fef9c3", "#854d0e")
BADGE_RED    = badge_ss("#fee2e2", "#991b1b")
BADGE_GRAY   = badge_ss("#f3f4f6", "#374151")
