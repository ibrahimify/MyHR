"""
Main Window — the core shell of MyHR.
Contains the sidebar and the page stack.
All pages are loaded here and switched via sidebar navigation.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt
from src.core.i18n import t


NAV_ITEMS = [
    ("nav_dashboard",     "dashboard",      "⊞"),
    ("nav_employees",     "employees",      "👤"),
    ("nav_hierarchy",     "hierarchy",      "🏢"),
    ("nav_promotions",    "promotions",     "↑"),
    ("nav_commendations", "commendations",  "★"),
    ("nav_sanctions",     "sanctions",      "⚠"),
    ("nav_audit",         "audit_log",      "📋"),
    ("nav_import",        "import_data",    "↓"),
    ("nav_settings",      "settings",       "⚙"),
]


class Sidebar(QWidget):
    def __init__(self, user, on_navigate, on_logout, parent=None):
        super().__init__(parent)
        self.user = user
        self.on_navigate = on_navigate
        self.on_logout = on_logout
        self.nav_buttons = {}
        self.active_key = "dashboard"
        self._build()

    def _build(self):
        self.setFixedWidth(224)
        self.setObjectName("Sidebar")
        self.setStyleSheet("QWidget#Sidebar { background-color: #1e2130; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_widget = QWidget()
        logo_widget.setFixedHeight(64)
        logo_widget.setStyleSheet("background-color: #191c2a; border-bottom: 1px solid #2a2f45;")
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 0, 16, 0)
        logo_layout.setSpacing(10)

        logo_mark = QLabel("HR")
        logo_mark.setFixedSize(34, 34)
        logo_mark.setAlignment(Qt.AlignCenter)
        logo_mark.setStyleSheet("background: #4f6ef7; color: white; border-radius: 8px; font-weight: bold; font-size: 14px;")

        name_lbl = QLabel("MyHR")
        name_lbl.setStyleSheet("color: #e8eaf0; font-size: 15px; font-weight: bold; background: transparent;")

        logo_layout.addWidget(logo_mark)
        logo_layout.addWidget(name_lbl)
        logo_layout.addStretch()
        layout.addWidget(logo_widget)

        # Nav
        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(10, 12, 10, 12)
        nav_layout.setSpacing(2)

        for key, page_key, icon in NAV_ITEMS:
            btn = QPushButton(f"  {icon}   {t(key)}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(self._inactive_style())
            btn.clicked.connect(lambda _, k=page_key: self._on_click(k))
            self.nav_buttons[page_key] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        layout.addWidget(nav_container)

        # Bottom
        bottom = QWidget()
        bottom.setStyleSheet("background: #191c2a; border-top: 1px solid #2a2f45;")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(14, 12, 14, 12)
        bottom_layout.setSpacing(8)

        role_display = t("role_admin") if self.user.role == "admin" else t("role_hr")
        user_lbl = QLabel(f"{self.user.full_name}\n{role_display}")
        user_lbl.setStyleSheet("color: #8b90a0; font-size: 12px; background: transparent;")
        bottom_layout.addWidget(user_lbl)

        logout_btn = QPushButton(t("logout"))
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setFixedHeight(32)
        logout_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #8b90a0; border: 1px solid #2a2f45; border-radius: 6px; font-size: 13px; padding-left: 10px; text-align: left; }
            QPushButton:hover { background: #2a2f45; color: #e8eaf0; }
        """)
        logout_btn.clicked.connect(self.on_logout)
        bottom_layout.addWidget(logout_btn)
        layout.addWidget(bottom)

        self._set_active("dashboard")

    def _on_click(self, key):
        self._set_active(key)
        self.on_navigate(key)

    def _set_active(self, key):
        if self.active_key in self.nav_buttons:
            self.nav_buttons[self.active_key].setStyleSheet(self._inactive_style())
        self.active_key = key
        if key in self.nav_buttons:
            self.nav_buttons[key].setStyleSheet(self._active_style())

    def _active_style(self):
        return "QPushButton { background: #2d3250; color: #7b9cff; border: none; border-radius: 8px; text-align: left; padding-left: 12px; font-size: 13px; font-weight: bold; }"

    def _inactive_style(self):
        return "QPushButton { background: transparent; color: #8b90a0; border: none; border-radius: 8px; text-align: left; padding-left: 12px; font-size: 13px; } QPushButton:hover { background: #252840; color: #c8cadc; }"


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle("MyHR — Employee Management System")
        self.setMinimumSize(1200, 720)
        self._pages_cache = {}
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(user=self.user, on_navigate=self._navigate, on_logout=self._logout)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f4f6fb;")
        layout.addWidget(self.stack)

        self._navigate("dashboard")

    def _get_page(self, key):
        if key in self._pages_cache:
            return self._pages_cache[key]
        try:
            if key == "dashboard":
                from src.ui.pages.dashboard import DashboardPage
                page = DashboardPage(self.user, self._navigate)
            elif key == "employees":
                from src.ui.pages.employees import EmployeesPage
                page = EmployeesPage(self.user)
            elif key == "hierarchy":
                from src.ui.pages.hierarchy import HierarchyPage
                page = HierarchyPage(self.user)
            elif key == "promotions":
                from src.ui.pages.promotions import PromotionsPage
                page = PromotionsPage(self.user)
            elif key == "commendations":
                from src.ui.pages.commendations import CommendationsPage
                page = CommendationsPage(self.user)
            elif key == "sanctions":
                from src.ui.pages.sanctions import SanctionsPage
                page = SanctionsPage(self.user)
            elif key == "audit_log":
                from src.ui.pages.audit_log import AuditLogPage
                page = AuditLogPage(self.user)
            elif key == "import_data":
                from src.ui.pages.import_data import ImportDataPage
                page = ImportDataPage(self.user)
            elif key == "settings":
                from src.ui.pages.settings import SettingsPage
                page = SettingsPage(self.user)
            else:
                page = _PlaceholderPage(key)
        except Exception as e:
            page = _PlaceholderPage(key, str(e))

        self.stack.addWidget(page)
        self._pages_cache[key] = page
        return page

    def _navigate(self, key):
        # For data-heavy pages, recreate on each visit to get fresh data
        if key in ("dashboard", "employees") and key in self._pages_cache:
            old_page = self._pages_cache.pop(key)
            self.stack.removeWidget(old_page)
            old_page.deleteLater()
        page = self._get_page(key)
        self.stack.setCurrentWidget(page)
        self.sidebar._set_active(key)

    def _logout(self):
        from src.ui.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()


class _PlaceholderPage(QWidget):
    def __init__(self, key, error=None):
        super().__init__()
        layout = QVBoxLayout(self)
        msg = f"🔧  {key.replace('_', ' ').title()}\n\nUnder construction" if not error else f"Error loading {key}:\n{error}"
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; color: #9ca3af;")
        layout.addWidget(lbl)