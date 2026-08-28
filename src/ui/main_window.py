import qtawesome as qta
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSize, QTimer
from src.core.i18n import t
from src.core.app_settings import company_name, company_subtitle
from src.ui.animations import animate_widget_entry
from src.ui.components.theme_toggle import ThemeToggle
from src.ui.styles import message_warning
from src.ui.theme import icon_color, theme_manager, tokens


NAV_SECTIONS = [
    ("nav_group_overview", [
        ("nav_dashboard",     "dashboard",      "fa5s.th-large"),
    ]),
    ("nav_group_people", [
        ("nav_employees",     "employees",      "fa5s.users"),
        ("nav_hierarchy",     "hierarchy",      "fa5s.building"),
    ]),
    ("nav_group_growth", [
        ("nav_promotions",    "promotions",     "fa5s.chart-line"),
        ("nav_commendations", "commendations",  "fa5s.award"),
    ]),
    ("nav_group_compliance", [
        ("nav_sanctions",     "sanctions",      "fa5s.exclamation-triangle"),
        ("nav_audit",         "audit_log",      "fa5s.clipboard-list"),
    ]),
    ("nav_group_data", [
        ("nav_import",        "import_data",    "fa5s.cloud-upload-alt"),
    ]),
    ("nav_group_system", [
        ("nav_settings",      "settings",       "fa5s.cog"),
    ]),
]

ADMIN_ONLY_PAGES = {"settings"}

_ICON_SZ = QSize(20, 20)


class Sidebar(QWidget):
    def __init__(self, user, on_navigate, on_logout, parent=None):
        super().__init__(parent)
        self.user = user
        self.on_navigate = on_navigate
        self.on_logout = on_logout
        self.nav_buttons = {}   # page key maps to (QPushButton, icon_name)
        self.nav_section_labels = []
        self.nav_section_lines = []
        self.active_key = "dashboard"
        self._theme_bound_labels = []
        self._build()
        theme_manager.theme_changed.connect(lambda _: self.apply_theme())

    def _build(self):
        self.setFixedWidth(256)
        self.setObjectName("Sidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        self.logo_w = QWidget()
        logo_w = self.logo_w
        logo_w.setObjectName("SidebarLogo")
        logo_w.setFixedHeight(88)
        ll = QHBoxLayout(logo_w)
        ll.setContentsMargins(24, 0, 24, 0)
        ll.setSpacing(8)
        ll.setAlignment(Qt.AlignVCenter)

        self.logo_mark = QLabel()
        logo_mark = self.logo_mark
        logo_mark.setFixedSize(40, 40)
        logo_mark.setAlignment(Qt.AlignCenter)

        nc = QVBoxLayout()
        nc.setContentsMargins(0, 0, 0, 0)
        nc.setSpacing(0)
        self.brand_name_lbl = QLabel("MyHR")
        self.brand_name_lbl.setFixedHeight(24)
        self.brand_name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self._theme_bound_labels.append((self.brand_name_lbl, "brand_name"))
        self.brand_subtitle_lbl = QLabel("Employee Management")
        self.brand_subtitle_lbl.setFixedHeight(18)
        self.brand_subtitle_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._theme_bound_labels.append((self.brand_subtitle_lbl, "brand_subtitle"))
        nc.addWidget(self.brand_name_lbl, 0, Qt.AlignLeft)
        nc.addWidget(self.brand_subtitle_lbl, 0, Qt.AlignLeft)

        ll.addWidget(logo_mark)
        ll.addLayout(nc)
        ll.addStretch()
        layout.addWidget(logo_w)

        # Navigation
        self.nav_w = QWidget()
        nav_w = self.nav_w
        nav_w.setObjectName("SidebarNav")
        nav_l = QVBoxLayout(nav_w)
        nav_l.setContentsMargins(0, 14, 16, 16)
        nav_l.setSpacing(4)

        for section_key, items in NAV_SECTIONS:
            visible_items = [
                item for item in items
                if item[1] not in ADMIN_ONLY_PAGES or self.user.role == "admin"
            ]
            if not visible_items:
                continue

            section_row = QWidget()
            section_row.setObjectName("SidebarSectionRow")
            section_l = QHBoxLayout(section_row)
            section_l.setContentsMargins(24, 8 if self.nav_buttons else 0, 0, 0)
            section_l.setSpacing(8)

            section_lbl = QLabel(t(section_key).upper())
            section_lbl.setObjectName("SidebarSectionLabel")
            section_lbl.setFixedHeight(18)
            self.nav_section_labels.append(section_lbl)

            line = QFrame()
            line.setFixedHeight(1)
            line.setObjectName("SidebarSectionLine")
            self.nav_section_lines.append(line)

            section_l.addWidget(section_lbl, 0, Qt.AlignVCenter)
            section_l.addWidget(line, 1, Qt.AlignVCenter)
            nav_l.addWidget(section_row)

            for key, page_key, icon_name in visible_items:
                btn = QPushButton("  " + t(key))
                btn.setIcon(qta.icon(icon_name, color=icon_color(muted=True)))
                btn.setIconSize(_ICON_SZ)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(34)
                btn.setStyleSheet(self._inactive_style())
                btn.clicked.connect(lambda _, k=page_key: self._on_click(k))
                self.nav_buttons[page_key] = (btn, icon_name)
                nav_l.addWidget(btn)

        nav_l.addStretch()
        layout.addWidget(nav_w, 1)

        # User card and logout
        self.bottom = QWidget()
        bottom = self.bottom
        bottom.setObjectName("SidebarBottom")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(8)

        self.user_card = QFrame()
        user_card = self.user_card
        user_card.setObjectName("SidebarUserCard")
        ucl = QHBoxLayout(user_card)
        ucl.setContentsMargins(12, 10, 12, 10)
        ucl.setSpacing(10)

        display_name = self.user.full_name
        self.avatar = QLabel()
        avatar = self.avatar
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)

        ic = QVBoxLayout()
        ic.setSpacing(0)
        self.name_lbl = QLabel(display_name)
        name_lbl = self.name_lbl
        self._theme_bound_labels.append((name_lbl, "user_name"))
        role_display = self.user.username if self.user.role == "admin" else t("role_hr")
        self.role_lbl = QLabel(role_display)
        role_lbl = self.role_lbl
        self._theme_bound_labels.append((role_lbl, "user_role"))
        ic.addWidget(name_lbl)
        ic.addWidget(role_lbl)

        ucl.addWidget(avatar)
        ucl.addLayout(ic)
        ucl.addStretch()
        bl.addWidget(user_card)

        self.theme_card = QFrame()
        self.theme_card.setObjectName("SidebarThemeCard")
        theme_layout = QHBoxLayout(self.theme_card)
        theme_layout.setContentsMargins(0, 6, 0, 6)
        theme_layout.setSpacing(0)
        theme_layout.addStretch()
        self.theme_toggle = ThemeToggle()
        theme_layout.addWidget(self.theme_toggle, 0, Qt.AlignCenter)
        theme_layout.addStretch()
        bl.addWidget(self.theme_card)

        self.logout_btn = QPushButton("  " + t("logout"))
        logout_btn = self.logout_btn
        logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color=icon_color(muted=True)))
        logout_btn.setIconSize(_ICON_SZ)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setFixedHeight(32)
        logout_btn.clicked.connect(self.on_logout)
        bl.addWidget(logout_btn)
        layout.addWidget(bottom)

        self.apply_theme()
        self._set_active("dashboard")
        self.refresh_branding()

    def apply_theme(self):
        tkn = tokens()
        primary_text = "#062f28" if tkn.name == "dark" else "#ffffff"
        self.setStyleSheet(f"""
            QWidget#Sidebar {{
                background: {tkn.sidebar};
                border-right: 1px solid {tkn.border};
            }}
            QWidget#Sidebar QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.logo_w.setStyleSheet(f"""
            QWidget#SidebarLogo {{
                background: {tkn.sidebar};
                border: none;
            }}
            QWidget#SidebarLogo QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.nav_w.setStyleSheet(f"QWidget#SidebarNav {{ background: {tkn.sidebar}; border: none; }}")
        self.bottom.setStyleSheet(f"""
            QWidget#SidebarBottom {{
                background: {tkn.sidebar};
                border-top: 1px solid {tkn.border};
            }}
            QWidget#SidebarBottom QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.logo_mark.setStyleSheet(f"background: {tkn.brand}; border: none; border-radius: 8px;")
        self.logo_mark.setPixmap(qta.icon("fa5s.building", color=primary_text).pixmap(24, 24))
        self.user_card.setStyleSheet(f"""
            QFrame#SidebarUserCard {{
                background: {tkn.surface};
                border: 1px solid {tkn.border};
                border-radius: 8px;
            }}
            QFrame#SidebarUserCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.theme_card.setStyleSheet(f"""
            QFrame#SidebarThemeCard {{
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QFrame#SidebarThemeCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        for label in self.nav_section_labels:
            label.setStyleSheet(f"""
                QLabel#SidebarSectionLabel {{
                    color: {tkn.text_soft};
                    font-size: 10px;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0px;
                    padding: 0px;
                    background: transparent;
                    border: none;
                }}
            """)
        for line in self.nav_section_lines:
            line.setStyleSheet(f"QFrame#SidebarSectionLine {{ background: {tkn.border}; border: none; margin: 0px 0px 0px 0px; }}")
        self.avatar.setStyleSheet(f"background: {tkn.brand}; color: {primary_text}; border: none; border-radius: 16px;")
        self.avatar.setPixmap(qta.icon("fa5s.user", color=primary_text).pixmap(16, 16))
        self.brand_name_lbl.setStyleSheet(f"color: {tkn.text}; font-size: 20px; font-weight: 700; background: transparent; border: none;")
        self.brand_subtitle_lbl.setStyleSheet(f"color: {tkn.text_muted}; font-size: 12px; background: transparent; border: none;")
        self.name_lbl.setStyleSheet(f"color: {tkn.text}; font-size: 14px; font-weight: 500; background: transparent; border: none;")
        self.role_lbl.setStyleSheet(f"color: {tkn.text_muted}; font-size: 12px; background: transparent; border: none;")
        self.logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color=tkn.text_muted))
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: {tkn.surface}; color: {tkn.text};
                border: 1px solid {tkn.border}; border-radius: 6px;
                font-size: 14px; font-weight: 500; text-align: left; padding-left: 12px;
                outline: none;
            }}
            QPushButton:hover {{ background: {tkn.hover}; color: {tkn.text}; border-color: {tkn.border_strong}; }}
        """)
        for page_key, (btn, icon_name) in self.nav_buttons.items():
            selected = page_key == self.active_key
            btn.setIcon(qta.icon(icon_name, color=icon_color(selected=selected, muted=not selected)))
            btn.setStyleSheet(self._active_style() if selected else self._inactive_style())

    def refresh_branding(self):
        name = company_name("MyHR")
        subtitle = company_subtitle("Employee Management")
        self.brand_name_lbl.setText(name)
        self.brand_subtitle_lbl.setText(subtitle)
        self.brand_name_lbl.setToolTip(name)
        self.brand_subtitle_lbl.setToolTip(subtitle)

    def _on_click(self, key):
        self._set_active(key)
        self.on_navigate(key)

    def _set_active(self, key):
        if self.active_key in self.nav_buttons:
            btn, icon_name = self.nav_buttons[self.active_key]
            btn.setIcon(qta.icon(icon_name, color=icon_color(muted=True)))
            btn.setStyleSheet(self._inactive_style())
        self.active_key = key
        if key in self.nav_buttons:
            btn, icon_name = self.nav_buttons[key]
            btn.setIcon(qta.icon(icon_name, color=icon_color(selected=True)))
            btn.setStyleSheet(self._active_style())

    def _active_style(self):
        return (
            f"QPushButton {{"
            f" background: {tokens().selected}; color: {tokens().brand};"
            f" border: none; border-left: 3px solid {tokens().brand};"
            " border-radius: 0px; border-top-right-radius: 8px; border-bottom-right-radius: 8px;"
            " text-align: left; padding-left: 22px;"
            " font-size: 14px; font-weight: 500;"
            " outline: none;"
            "}"
        )

    def _inactive_style(self):
        return (
            f"QPushButton {{"
            f" background: transparent; color: {tokens().text_muted};"
            " border: none; border-radius: 0px; border-top-right-radius: 8px; border-bottom-right-radius: 8px;"
            " text-align: left; padding-left: 25px;"
            " font-size: 14px; font-weight: 500;"
            " outline: none;"
            "}"
            f" QPushButton:hover {{ background: {tokens().hover}; color: {tokens().text}; }}"
        )


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"{company_name('MyHR')} - {t('employee_management_system')}")
        self.setMinimumSize(1024, 600)
        self.setStyleSheet(f"QMainWindow {{ background: {tokens().canvas}; }}")
        self.current_key = "dashboard"
        theme_manager.theme_changed.connect(self._handle_theme_changed)
        self._pages_cache = {}
        self._page_animation_ready = False
        self._build()
        self.showMaximized()
        QTimer.singleShot(350, self._enable_page_animations)

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
        self.stack.setObjectName("MainContent")
        self.apply_theme()
        layout.addWidget(self.stack)

        self._navigate("dashboard", animate=False)

    def apply_theme(self):
        tkn = tokens()
        self.setStyleSheet(f"QMainWindow {{ background: {tkn.canvas}; }}")
        if hasattr(self, "stack"):
            self.stack.setStyleSheet(f"""
                QStackedWidget#MainContent {{
                    background: {tkn.canvas};
                    border: none;
                }}
            """)
        if hasattr(self, "sidebar"):
            self.sidebar.apply_theme()

    def _handle_theme_changed(self, _theme):
        self.apply_theme()
        if not hasattr(self, "stack"):
            return
        key = getattr(self, "current_key", "dashboard")
        page = self._pages_cache.pop(key, None)
        if page is not None:
            self.stack.removeWidget(page)
            page.deleteLater()
        self._navigate(key, animate=False)

    def _enable_page_animations(self):
        self._page_animation_ready = True

    def _get_page(self, key):
        if key in self._pages_cache:
            return self._pages_cache[key]
        try:
            if key == "dashboard":
                DashboardPage = self._page_class("dashboard", "DashboardPage")
                page = DashboardPage(self.user, self._navigate)
            elif key == "employees":
                EmployeesPage = self._page_class("employees", "EmployeesPage")
                page = EmployeesPage(self.user)
            elif key == "hierarchy":
                HierarchyPage = self._page_class("hierarchy", "HierarchyPage")
                page = HierarchyPage(self.user)
            elif key == "promotions":
                PromotionsPage = self._page_class("promotions", "PromotionsPage")
                page = PromotionsPage(self.user, navigate_to_employee=self._navigate_to_employee)
            elif key == "commendations":
                CommendationsPage = self._page_class("commendations", "CommendationsPage")
                page = CommendationsPage(self.user)
            elif key == "sanctions":
                SanctionsPage = self._page_class("sanctions", "SanctionsPage")
                page = SanctionsPage(self.user)
            elif key == "audit_log":
                AuditLogPage = self._page_class("audit_log", "AuditLogPage")
                page = AuditLogPage(self.user)
            elif key == "import_data":
                ImportDataPage = self._page_class("import_data", "ImportDataPage")
                page = ImportDataPage(self.user)
            elif key == "settings":
                SettingsPage = self._page_class("settings", "SettingsPage")
                page = SettingsPage(self.user)
            else:
                page = _PlaceholderPage(key)
        except Exception as e:
            page = _PlaceholderPage(key, str(e))

        self.stack.addWidget(page)
        self._pages_cache[key] = page
        return page

    def _page_class(self, module_name, class_name):
        if module_name == "dashboard":
            from src.ui.pages.dashboard import DashboardPage
            return DashboardPage
        if module_name == "employees":
            from src.ui.pages.employees import EmployeesPage
            return EmployeesPage
        if module_name == "hierarchy":
            from src.ui.pages.hierarchy import HierarchyPage
            return HierarchyPage
        if module_name == "promotions":
            from src.ui.pages.promotions import PromotionsPage
            return PromotionsPage
        if module_name == "commendations":
            from src.ui.pages.commendations import CommendationsPage
            return CommendationsPage
        if module_name == "sanctions":
            from src.ui.pages.sanctions import SanctionsPage
            return SanctionsPage
        if module_name == "audit_log":
            from src.ui.pages.audit_log import AuditLogPage
            return AuditLogPage
        if module_name == "import_data":
            from src.ui.pages.import_data import ImportDataPage
            return ImportDataPage
        if module_name == "settings":
            from src.ui.pages.settings import SettingsPage
            return SettingsPage
        raise KeyError(module_name)

    def _navigate(self, key, animate=True):
        open_active_sanctions = key == "sanctions_active"
        if open_active_sanctions:
            key = "sanctions"
        if key in ADMIN_ONLY_PAGES and self.user.role != "admin":
            message_warning(self, t("access_denied"), t("admin_only_section"))
            return
        if key in ("dashboard", "employees", "promotions", "audit_log") and key in self._pages_cache:
            old = self._pages_cache.pop(key)
            self.stack.removeWidget(old)
            old.deleteLater()
        page = self._get_page(key)
        self.current_key = key
        self.stack.setCurrentWidget(page)
        self.sidebar._set_active(key)
        if hasattr(page, "refresh"):
            page.refresh()
        if animate and self._page_animation_ready:
            animate_widget_entry(page, duration=160, offset=0)
        if open_active_sanctions and hasattr(page, "open_active_sanctions"):
            page.open_active_sanctions()

    def _navigate_to_employee(self, emp_db_id: int):
        if "employees" in self._pages_cache:
            old = self._pages_cache.pop("employees")
            self.stack.removeWidget(old)
            old.deleteLater()
        page = self._get_page("employees")
        self.stack.setCurrentWidget(page)
        self.sidebar._set_active("employees")
        page._show_profile(emp_db_id)
        animate_widget_entry(page, duration=160, offset=0)

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
