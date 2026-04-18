"""
Login Window — first screen the user sees.
Features:
- Language selector (EN / HU / AR) — sets session language before login
- Username + password fields
- Validates against DB, opens MainWindow on success
- RTL layout applied automatically for Arabic
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

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
        self.setFixedSize(440, 560)
        self._build()

    def _build(self):
        self.setStyleSheet("background-color: #eef2ff;")
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(24, 24, 24, 24)

        # ── Card ─────────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background: white;
                border-radius: 16px;
                border: 1px solid #e0e4f0;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(0)

        # ── Language selector ─────────────────────────────────────────────────
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)

        globe_lbl = QLabel("🌐")
        globe_lbl.setStyleSheet("font-size: 16px; background: transparent;")
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
            }
            QComboBox:hover { border-color: #4f6ef7; }
            QComboBox::drop-down { border: none; }
        """)
        for label, code, flag in LANGUAGES:
            self.lang_combo.addItem(f"{flag}  {label}", code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        card_layout.addLayout(lang_row)
        card_layout.addSpacing(20)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)

        logo_box = QLabel("HR")
        logo_box.setFixedSize(60, 60)
        logo_box.setAlignment(Qt.AlignCenter)
        logo_box.setStyleSheet("""
            background: #4f6ef7;
            color: white;
            border-radius: 14px;
            font-size: 22px;
            font-weight: bold;
        """)
        logo_row.addWidget(logo_box)
        card_layout.addLayout(logo_row)
        card_layout.addSpacing(12)

        # ── Title ─────────────────────────────────────────────────────────────
        self.title_lbl = QLabel(t("app_name"))
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #1a1d2e; background: transparent;")
        card_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel(t("app_subtitle"))
        self.subtitle_lbl.setAlignment(Qt.AlignCenter)
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #9ca3af; background: transparent;")
        card_layout.addWidget(self.subtitle_lbl)
        card_layout.addSpacing(24)

        # ── Username ──────────────────────────────────────────────────────────
        self.username_lbl = QLabel(t("username"))
        self.username_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; background: transparent;")
        card_layout.addWidget(self.username_lbl)
        card_layout.addSpacing(4)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t("username_placeholder"))
        self.username_input.setFixedHeight(42)
        self.username_input.setStyleSheet(self._input_style())
        card_layout.addWidget(self.username_input)
        card_layout.addSpacing(12)

        # ── Password ──────────────────────────────────────────────────────────
        self.password_lbl = QLabel(t("password"))
        self.password_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; background: transparent;")
        card_layout.addWidget(self.password_lbl)
        card_layout.addSpacing(4)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(t("password_placeholder"))
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.returnPressed.connect(self._attempt_login)
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(20)

        # ── Login button ──────────────────────────────────────────────────────
        self.login_btn = QPushButton(t("login_button"))
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #4f6ef7;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover   { background: #3a57e8; }
            QPushButton:pressed { background: #2d47d4; }
        """)
        self.login_btn.clicked.connect(self._attempt_login)
        card_layout.addWidget(self.login_btn)
        card_layout.addSpacing(16)

        # ── Footer ────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e5e7eb;")
        card_layout.addWidget(sep)
        card_layout.addSpacing(12)

        self.footer_lbl = QLabel(t("authorized_only"))
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        self.footer_lbl.setStyleSheet("font-size: 12px; color: #9ca3af; background: transparent;")
        card_layout.addWidget(self.footer_lbl)
        card_layout.addSpacing(6)

        roles_row = QHBoxLayout()
        roles_row.setAlignment(Qt.AlignCenter)
        roles_row.setSpacing(20)

        for role_key, color in [("role_admin", "#4f6ef7"), ("role_hr", "#10b981")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
            lbl = QLabel(t(role_key))
            lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
            roles_row.addWidget(dot)
            roles_row.addWidget(lbl)

        card_layout.addLayout(roles_row)
        outer.addWidget(card)

    def _on_language_changed(self, index):
        code = self.lang_combo.itemData(index)
        set_language(code)

        # Apply RTL layout direction for Arabic
        from PySide6.QtCore import Qt as QtCore
        from PySide6.QtWidgets import QApplication
        if is_rtl():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)
        else:
            QApplication.instance().setLayoutDirection(Qt.LeftToRight)

        # Refresh all translatable text
        self._refresh_text()

    def _refresh_text(self):
        """Update all labels when language changes."""
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

    def _input_style(self):
        return """
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 14px;
                color: #1a1d2e;
                background: #f9fafb;
            }
            QLineEdit:focus {
                border-color: #4f6ef7;
                background: white;
            }
        """