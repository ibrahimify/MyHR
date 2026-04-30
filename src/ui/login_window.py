"""
Login Window - first screen the user sees.

The language selector controls the current session language before login. The
same session language is kept when the user logs out and returns here.
"""

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import company_name, company_subtitle
from src.core.i18n import get_language, is_rtl, set_language, t
from src.database.connection import verify_login


LANGUAGES = [
    ("English", "en"),
    ("Magyar", "hu"),
    ("\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "ar"),
]


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyHR")
        self.setObjectName("LoginWindow")
        self.role_labels = {}
        self._build()
        self.showMaximized()

    def _build(self):
        self.setStyleSheet("""
            QWidget#LoginWindow {
                background: #eaf4ff;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(450)
        card.setMinimumHeight(0)
        card.setStyleSheet("""
            QFrame#LoginCard {
                background: white;
                border: 1px solid #d8dee8;
                border-radius: 16px;
            }
            QFrame#LoginCard QLabel {
                background: transparent;
                border: none;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(0)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)
        logo_box = QLabel()
        logo_box.setFixedSize(64, 64)
        logo_box.setAlignment(Qt.AlignCenter)
        logo_box.setPixmap(qta.icon("fa5s.clipboard-list", color="white").pixmap(40, 40))
        logo_box.setStyleSheet("background: #1f62f2; border-radius: 16px;")
        logo_row.addWidget(logo_box)
        card_layout.addLayout(logo_row)
        card_layout.addSpacing(24)

        self.title_lbl = QLabel()
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 34px; font-weight: 800; color: #111827;")
        card_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setAlignment(Qt.AlignCenter)
        self.subtitle_lbl.setStyleSheet("font-size: 18px; color: #334155;")
        card_layout.addWidget(self.subtitle_lbl)
        card_layout.addSpacing(32)

        language_title = QHBoxLayout()
        language_title.setSpacing(10)
        language_icon = QLabel()
        language_icon.setFixedSize(22, 22)
        language_icon.setAlignment(Qt.AlignCenter)
        language_icon.setPixmap(qta.icon("fa5s.globe", color="#111827").pixmap(18, 18))
        self.language_lbl = QLabel()
        self.language_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        language_title.addWidget(language_icon)
        language_title.addWidget(self.language_lbl)
        language_title.addStretch()
        card_layout.addLayout(language_title)
        card_layout.addSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedHeight(46)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background: #f3f3f5;
                border: none;
                border-radius: 8px;
                color: #111827;
                font-size: 16px;
                padding: 0 16px;
            }
            QComboBox:hover { background: #eeeeF1; }
            QComboBox:focus { border: 1px solid #2563eb; }
            QComboBox::drop-down {
                border: none;
                width: 36px;
            }
        """)
        for label, code in LANGUAGES:
            self.lang_combo.addItem(label, code)
        self._select_current_language()
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        card_layout.addWidget(self.lang_combo)
        card_layout.addSpacing(24)

        self.username_lbl = self._field_label()
        card_layout.addWidget(self.username_lbl)
        card_layout.addSpacing(8)

        self.username_input, username_row = self._icon_input("fa5s.user")
        card_layout.addWidget(username_row)
        card_layout.addSpacing(26)

        self.password_lbl = self._field_label()
        card_layout.addWidget(self.password_lbl)
        card_layout.addSpacing(8)

        self.password_input, password_row = self._icon_input("fa5s.lock", password=True)
        self.password_input.returnPressed.connect(self._attempt_login)
        card_layout.addWidget(password_row)
        card_layout.addSpacing(30)

        self.login_btn = QPushButton()
        self.login_btn.setFixedHeight(50)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._attempt_login)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #030213;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: #111827; }
            QPushButton:pressed { background: #020617; }
        """)
        card_layout.addWidget(self.login_btn)
        card_layout.addSpacing(70)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("border: none; border-top: 1px solid #e5e7eb;")
        card_layout.addWidget(separator)
        card_layout.addSpacing(30)

        self.footer_lbl = QLabel()
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        self.footer_lbl.setStyleSheet("font-size: 16px; color: #334155;")
        card_layout.addWidget(self.footer_lbl)
        card_layout.addSpacing(12)

        roles_row = QHBoxLayout()
        roles_row.setAlignment(Qt.AlignCenter)
        roles_row.setSpacing(18)
        self._add_role_indicator(roles_row, "role_admin", "#2563eb")
        self._add_role_indicator(roles_row, "role_hr", "#10b981")
        card_layout.addLayout(roles_row)

        outer.addWidget(card, 0, Qt.AlignHCenter)
        outer.addStretch(1)
        self._refresh_text()

    def _field_label(self):
        label = QLabel()
        label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        return label

    def _icon_input(self, icon_name, password=False):
        container = QFrame()
        container.setObjectName("LoginInput")
        container.setFixedHeight(46)
        container.setStyleSheet("""
            QFrame#LoginInput {
                background: #f3f3f5;
                border: none;
                border-radius: 8px;
            }
        """)

        row = QHBoxLayout(container)
        row.setContentsMargins(16, 0, 12, 0)
        row.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(22, 22)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(qta.icon(icon_name, color="#94a3b8").pixmap(20, 20))
        icon_label.setStyleSheet("background: transparent; border: none;")
        row.addWidget(icon_label)

        field = QLineEdit()
        field.setFixedHeight(44)
        if password:
            field.setEchoMode(QLineEdit.Password)
        field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #111827;
                font-size: 16px;
                padding: 0;
            }
            QLineEdit:focus { border: none; }
        """)
        row.addWidget(field, 1)
        return field, container

    def _add_role_indicator(self, row, role_key, color):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {color}; border-radius: 5px;")
        label = QLabel()
        label.setStyleSheet("font-size: 14px; color: #334155;")
        layout.addWidget(dot)
        layout.addWidget(label)
        row.addWidget(wrap)
        self.role_labels[role_key] = label

    def _select_current_language(self):
        current = get_language()
        self.lang_combo.blockSignals(True)
        for index in range(self.lang_combo.count()):
            if self.lang_combo.itemData(index) == current:
                self.lang_combo.setCurrentIndex(index)
                break
        self.lang_combo.blockSignals(False)
        self._apply_layout_direction()

    def _apply_layout_direction(self):
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)

    def _language_caption(self):
        language = get_language()
        if language == "ar":
            return "\u0627\u0644\u0644\u063a\u0629 / Language / Nyelv"
        if language == "hu":
            return "Nyelv / Language / \u0627\u0644\u0644\u063a\u0629"
        return "Language / Nyelv / \u0627\u0644\u0644\u063a\u0629"

    def _on_language_changed(self, index):
        set_language(self.lang_combo.itemData(index))
        self._apply_layout_direction()
        self._refresh_text()

    def _refresh_text(self):
        self.title_lbl.setText(company_name(t("app_name")))
        self.subtitle_lbl.setText(company_subtitle(t("app_subtitle")))
        self.language_lbl.setText(self._language_caption())
        self.username_lbl.setText(t("username"))
        self.username_input.setPlaceholderText(t("username_placeholder"))
        self.password_lbl.setText(t("password"))
        self.password_input.setPlaceholderText(t("password_placeholder"))
        self.login_btn.setText(t("login_button"))
        self.footer_lbl.setText(t("authorized_only"))
        for role_key, label in self.role_labels.items():
            label.setText(t(role_key))

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
