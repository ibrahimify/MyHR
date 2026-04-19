"""
Login Window — first screen the user sees.
Features:
- Language selector (EN / HU / AR) — sets session language before login
- Username + password fields
- Validates against DB, opens MainWindow on success
- RTL layout applied automatically for Arabic
"""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QSize
from src.database.connection import verify_login
from src.core.i18n import t, set_language, is_rtl


LANGUAGES = [
    ("English",           "en", "🇬🇧"),
    ("Magyar (Hungarian)","hu", "🇭🇺"),
    ("العربية (Arabic)",  "ar", "🇸🇦"),
]


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyHR")
        self.setObjectName("LoginWindow")
        self._build()
        self.showMaximized()

    def _build(self):
        self.setStyleSheet("""
            QWidget#LoginWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eff6ff, stop:1 #dbeafe);
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        # ── Card ─────────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame#LoginCard {
                background: white;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
            QFrame#LoginCard QLabel { background: transparent; }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(0)

        # ── Language selector ─────────────────────────────────────────────────
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)

        globe_lbl = QLabel()
        globe_lbl.setPixmap(qta.icon("fa5s.globe", color="#6b7280").pixmap(16, 16))
        lang_row.addWidget(globe_lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedHeight(32)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
                background: #f9fafb;
                color: #374151;
                min-height: 32px;
            }
            QComboBox:hover { border-color: #2563eb; }
        """)
        for label, code, flag in LANGUAGES:
            self.lang_combo.addItem(f"{flag}  {label}", code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        card_layout.addLayout(lang_row)
        card_layout.addSpacing(24)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)

        logo_box = QLabel()
        logo_box.setFixedSize(64, 64)
        logo_box.setAlignment(Qt.AlignCenter)
        logo_box.setStyleSheet("""
            background: #2563eb;
            border-radius: 16px;
        """)
        logo_box.setPixmap(qta.icon("fa5s.building", color="white").pixmap(28, 28))
        logo_row.addWidget(logo_box)
        card_layout.addLayout(logo_row)
        card_layout.addSpacing(14)

        # ── Title ─────────────────────────────────────────────────────────────
        self.title_lbl = QLabel(t("app_name"))
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #111827;")
        card_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel(t("app_subtitle"))
        self.subtitle_lbl.setAlignment(Qt.AlignCenter)
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #6b7280;")
        card_layout.addWidget(self.subtitle_lbl)
        card_layout.addSpacing(28)

        # ── Username ──────────────────────────────────────────────────────────
        self.username_lbl = QLabel(t("username"))
        self.username_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        card_layout.addWidget(self.username_lbl)
        card_layout.addSpacing(6)

        username_wrap = self._icon_input_row("fa5s.user", t("username_placeholder"))
        self.username_input = username_wrap[0]
        card_layout.addLayout(username_wrap[1])
        card_layout.addSpacing(16)

        # ── Password ──────────────────────────────────────────────────────────
        self.password_lbl = QLabel(t("password"))
        self.password_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        card_layout.addWidget(self.password_lbl)
        card_layout.addSpacing(6)

        password_wrap = self._icon_input_row("fa5s.lock", t("password_placeholder"), password=True)
        self.password_input = password_wrap[0]
        card_layout.addLayout(password_wrap[1])
        self.password_input.returnPressed.connect(self._attempt_login)
        card_layout.addSpacing(22)

        # ── Login button ──────────────────────────────────────────────────────
        self.login_btn = QPushButton(t("login_button"))
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #030213;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover   { background: #1e293b; }
            QPushButton:pressed { background: #111827; }
        """)
        self.login_btn.clicked.connect(self._attempt_login)
        card_layout.addWidget(self.login_btn)
        card_layout.addSpacing(20)

        # ── Footer ────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #e5e7eb; background: transparent;")
        sep.setFixedHeight(1)
        card_layout.addWidget(sep)
        card_layout.addSpacing(14)

        self.footer_lbl = QLabel(t("authorized_only"))
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        self.footer_lbl.setStyleSheet("font-size: 12px; color: #9ca3af;")
        card_layout.addWidget(self.footer_lbl)
        card_layout.addSpacing(8)

        roles_row = QHBoxLayout()
        roles_row.setAlignment(Qt.AlignCenter)
        roles_row.setSpacing(16)

        for role_key, color in [("role_admin", "#2563eb"), ("role_hr", "#10b981")]:
            pill = QFrame()
            pill.setStyleSheet(f"background: {color}18; border-radius: 10px; border: 1px solid {color}40;")
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(10, 4, 10, 4)
            pl.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 9px;")
            lbl = QLabel(t(role_key))
            lbl.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: 600;")
            pl.addWidget(dot)
            pl.addWidget(lbl)
            roles_row.addWidget(pill)

        card_layout.addLayout(roles_row)
        outer.addWidget(card, 0, Qt.AlignHCenter)
        outer.addStretch(1)

    def _icon_input_row(self, icon_name, placeholder, password=False):
        row = QHBoxLayout()
        row.setSpacing(0)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 42)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(qta.icon(icon_name, color="#9ca3af").pixmap(15, 15))
        icon_lbl.setStyleSheet("""
            QLabel {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-right: none;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }
        """)

        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        if password:
            field.setEchoMode(QLineEdit.Password)
        field.setFixedHeight(42)
        field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                padding: 0 14px;
                font-size: 14px;
                color: #111827;
                background: #f9fafb;
                min-height: 0px;
            }
            QLineEdit:focus {
                border-color: #2563eb;
                background: white;
            }
        """)

        row.addWidget(icon_lbl)
        row.addWidget(field, 1)
        return field, row

    def _on_language_changed(self, index):
        code = self.lang_combo.itemData(index)
        set_language(code)

        from PySide6.QtWidgets import QApplication
        if is_rtl():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)
        else:
            QApplication.instance().setLayoutDirection(Qt.LeftToRight)

        self._refresh_text()

    def _refresh_text(self):
        self.title_lbl.setText(t("app_name"))
        self.subtitle_lbl.setText(t("app_subtitle"))
        self.username_lbl.setText(t("username"))
        self.username_input.setPlaceholderText(t("username_placeholder"))
        self.password_lbl.setText(t("password"))
        self.password_input.setPlaceholderText(t("password_placeholder"))
        self.login_btn.setText(t("login_button"))
        self.footer_lbl.setText(t("authorized_only"))

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, t("warning"), t("login_fill_fields"))
            return

        user = verify_login(username, password)
        if user:
            from src.ui.main_window import MainWindow
            self.main_window = MainWindow(user)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.critical(self, t("error"), t("login_failed"))
            self.password_input.clear()
            self.password_input.setFocus()
