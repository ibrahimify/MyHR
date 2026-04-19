import qtawesome as qta
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSize
from src.core.i18n import t


NAV_ITEMS = [
    ("nav_dashboard",     "dashboard",      "fa5s.th-large"),
    ("nav_employees",     "employees",      "fa5s.users"),
    ("nav_hierarchy",     "hierarchy",      "fa5s.building"),
    ("nav_promotions",    "promotions",     "fa5s.chart-line"),
    ("nav_commendations", "commendations",  "fa5s.award"),
    ("nav_sanctions",     "sanctions",      "fa5s.exclamation-triangle"),
    ("nav_audit",         "audit_log",      "fa5s.file-alt"),
    ("nav_import",        "import_data",    "fa5s.upload"),
    ("nav_settings",      "settings",       "fa5s.cog"),
]

ADMIN_ONLY_PAGES = {"settings"}

_INACTIVE_CLR = "#6b7280"
_ACTIVE_CLR   = "#1d4ed8"
_ICON_SZ      = QSize(16, 16)


class Sidebar(QWidget):
    def __init__(self, user, on_navigate, on_logout, parent=None):
        super().__init__(parent)
        self.user = user
        self.on_navigate = on_navigate
        self.on_logout = on_logout
        self.nav_buttons = {}   # key → (QPushButton, icon_name)
        self.active_key = "dashboard"
        self._build()

    def _build(self):
        self.setFixedWidth(256)
        self.setObjectName("Sidebar")
        self.setStyleSheet("QWidget#Sidebar { background: white; border-right: 1px solid #e5e7eb; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_w = QWidget()
        logo_w.setFixedHeight(72)
        logo_w.setStyleSheet("background: white; border-bottom: 1px solid #e5e7eb;")
        ll = QHBoxLayout(logo_w)
        ll.setContentsMargins(20, 0, 20, 0)
        ll.setSpacing(12)

        logo_mark = QLabel()
        logo_mark.setFixedSize(40, 40)
        logo_mark.setAlignment(Qt.AlignCenter)
        logo_mark.setStyleSheet("background: #2563eb; border-radius: 10px;")
        logo_mark.setPixmap(qta.icon("fa5s.building", color="white").pixmap(20, 20))

        nc = QVBoxLayout()
        nc.setSpacing(1)
        n = QLabel("MyHR")
        n.setStyleSheet("color: #111827; font-size: 16px; font-weight: bold; background: transparent;")
        s = QLabel("Employee Management")
        s.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")
        nc.addWidget(n)
        nc.addWidget(s)

        ll.addWidget(logo_mark)
        ll.addLayout(nc)
        ll.addStretch()
        layout.addWidget(logo_w)

        # ── Nav ───────────────────────────────────────────────────────────────
        nav_w = QWidget()
        nav_w.setStyleSheet("background: white;")
        nav_l = QVBoxLayout(nav_w)
        nav_l.setContentsMargins(12, 16, 12, 16)
        nav_l.setSpacing(2)

        for key, page_key, icon_name in NAV_ITEMS:
            if page_key in ADMIN_ONLY_PAGES and self.user.role != "admin":
                continue
            btn = QPushButton("  " + t(key))
            btn.setIcon(qta.icon(icon_name, color=_INACTIVE_CLR))
            btn.setIconSize(_ICON_SZ)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(self._inactive_style())
            btn.clicked.connect(lambda _, k=page_key: self._on_click(k))
            self.nav_buttons[page_key] = (btn, icon_name)
            nav_l.addWidget(btn)

        nav_l.addStretch()
        layout.addWidget(nav_w, 1)

        # ── User card + logout ────────────────────────────────────────────────
        bottom = QWidget()
        bottom.setStyleSheet("background: white; border-top: 1px solid #e5e7eb;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 12, 12, 12)
        bl.setSpacing(8)

        user_card = QFrame()
        user_card.setStyleSheet("background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;")
        ucl = QHBoxLayout(user_card)
        ucl.setContentsMargins(10, 8, 10, 8)
        ucl.setSpacing(10)

        initials = "".join(p[0].upper() for p in self.user.full_name.split()[:2])
        avatar = QLabel(initials)
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background: #dbeafe; color: #1d4ed8; border-radius: 16px;"
            " font-size: 12px; font-weight: bold;"
        )

        ic = QVBoxLayout()
        ic.setSpacing(0)
        name_lbl = QLabel(self.user.full_name)
        name_lbl.setStyleSheet("color: #111827; font-size: 13px; font-weight: 600; background: transparent;")
        role_display = t("role_admin") if self.user.role == "admin" else t("role_hr")
        role_lbl = QLabel(role_display)
        role_lbl.setStyleSheet("color: #6b7280; font-size: 11px; background: transparent;")
        ic.addWidget(name_lbl)
        ic.addWidget(role_lbl)

        ucl.addWidget(avatar)
        ucl.addLayout(ic)
        ucl.addStretch()
        bl.addWidget(user_card)

        logout_btn = QPushButton("  " + t("logout"))
        logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color="#6b7280"))
        logout_btn.setIconSize(_ICON_SZ)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setFixedHeight(34)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: white; color: #6b7280;
                border: 1px solid #e5e7eb; border-radius: 8px;
                font-size: 13px; text-align: left; padding-left: 12px;
            }
            QPushButton:hover { background: #f9fafb; color: #374151; border-color: #d1d5db; }
        """)
        logout_btn.clicked.connect(self.on_logout)
        bl.addWidget(logout_btn)
        layout.addWidget(bottom)

        self._set_active("dashboard")

    def _on_click(self, key):
        self._set_active(key)
        self.on_navigate(key)

    def _set_active(self, key):
        if self.active_key in self.nav_buttons:
            btn, icon_name = self.nav_buttons[self.active_key]
            btn.setIcon(qta.icon(icon_name, color=_INACTIVE_CLR))
            btn.setStyleSheet(self._inactive_style())
        self.active_key = key
        if key in self.nav_buttons:
            btn, icon_name = self.nav_buttons[key]
            btn.setIcon(qta.icon(icon_name, color=_ACTIVE_CLR))
            btn.setStyleSheet(self._active_style())

    def _active_style(self):
        return (
            "QPushButton {"
            " background: #eff6ff; color: #1d4ed8;"
            " border: none; border-radius: 8px;"
            " text-align: left; padding-left: 12px;"
            " font-size: 13px; font-weight: 600;"
            "}"
        )

    def _inactive_style(self):
        return (
            "QPushButton {"
            " background: transparent; color: #6b7280;"
            " border: none; border-radius: 8px;"
            " text-align: left; padding-left: 12px;"
            " font-size: 13px;"
            "}"
            " QPushButton:hover { background: #f3f4f6; color: #374151; }"
        )


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle("MyHR - Employee Management System")
        self.setMinimumSize(1024, 600)
        self._pages_cache = {}
        self._build()
        self.showMaximized()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(
            user=self.user,
            on_navigate=self._navigate,
            on_logout=self._logout,
        )
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f9fafb;")
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
                page = PromotionsPage(self.user, navigate_to_employee=self._navigate_to_employee)
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
        if key in ADMIN_ONLY_PAGES and self.user.role != "admin":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Access Denied", "This section is for administrators only.")
            return
        if key in ("dashboard", "employees", "promotions") and key in self._pages_cache:
            old = self._pages_cache.pop(key)
            self.stack.removeWidget(old)
            old.deleteLater()
        page = self._get_page(key)
        self.stack.setCurrentWidget(page)
        self.sidebar._set_active(key)

    def _navigate_to_employee(self, emp_db_id: int):
        if "employees" in self._pages_cache:
            old = self._pages_cache.pop("employees")
            self.stack.removeWidget(old)
            old.deleteLater()
        page = self._get_page("employees")
        self.stack.setCurrentWidget(page)
        self.sidebar._set_active("employees")
        page._show_profile(emp_db_id)

    def _logout(self):
        from src.ui.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()


class _PlaceholderPage(QWidget):
    def __init__(self, key, error=None):
        super().__init__()
        layout = QVBoxLayout(self)
        msg = (
            f"{key.replace('_', ' ').title()}\n\nUnder construction"
            if not error else
            f"Error loading {key}:\n{error}"
        )
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; color: #9ca3af;")
        layout.addWidget(lbl)
