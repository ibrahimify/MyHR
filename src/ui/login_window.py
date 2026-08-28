"""
Login Window - first screen the user sees.

The language selector controls the current session language before login. The
same session language is kept when the user logs out and returns here.
"""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QSize, QRectF, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import company_name, company_subtitle
from src.core.i18n import available_languages, get_language, is_rtl, set_language, t
from src.database.connection import verify_login
from src.ui.components.theme_toggle import ThemeToggle
from src.ui.theme import theme_manager, tokens


LANGUAGES = available_languages()

def _message_box_ss():
    tkn = tokens()
    primary_text = "#062f28" if tkn.name == "dark" else "#ffffff"
    return f"""
QMessageBox {{ background: {tkn.surface}; color: {tkn.text}; }}
QMessageBox QLabel {{ color: {tkn.text}; background: transparent; font-size: 13px; }}
QPushButton {{
    background: {tkn.surface};
    color: {tkn.text};
    border: 1px solid {tkn.border_strong};
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {tkn.hover}; }}
QPushButton:default {{ background: {tkn.brand}; color: {primary_text}; border: none; }}
"""


class CustomSelect(QWidget):
    valueChanged = Signal(str)

    def __init__(self, items):
        super().__init__()
        self.items = items
        self.current_value = items[0][1]

        self.setFixedHeight(40)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.trigger = QFrame()
        self.trigger.setFixedHeight(40)
        self.trigger.setCursor(Qt.PointingHandCursor)
        self._apply_theme()

        trigger_layout = QHBoxLayout(self.trigger)
        trigger_layout.setContentsMargins(12, 0, 12, 0)
        trigger_layout.setSpacing(8)

        self.label = QLabel(items[0][0])
        self.label.setStyleSheet(f"font-size: 14px; color: {tokens().text};")

        self.arrow = QLabel()
        self.arrow.setFixedSize(16, 16)
        self.arrow.setAlignment(Qt.AlignCenter)
        self.arrow.setPixmap(qta.icon("fa5s.chevron-down", color=tokens().text_muted).pixmap(12, 12))

        trigger_layout.addWidget(self.label, 1)
        trigger_layout.addWidget(self.arrow)

        main_layout.addWidget(self.trigger)

        self.popup = SelectPopupFrame()
        self.popup.hide()
        self.popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_TranslucentBackground, True)
        self.popup.setAutoFillBackground(False)
        self.popup_opacity = QGraphicsOpacityEffect(self.popup)
        self.popup_opacity.setOpacity(1)
        self.popup.setGraphicsEffect(self.popup_opacity)
        self.popup_pos_animation = QPropertyAnimation(self.popup, b"pos", self)
        self.popup_pos_animation.setDuration(140)
        self.popup_pos_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.popup_opacity_animation = QPropertyAnimation(self.popup_opacity, b"opacity", self)
        self.popup_opacity_animation.setDuration(120)
        self.popup_opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.setSpacing(0)

        self.popup_box = QFrame()
        self.popup_box.setObjectName("SelectPopupBox")
        self.popup_box.setAttribute(Qt.WA_StyledBackground, True)
        self._apply_theme()

        box_layout = QVBoxLayout(self.popup_box)
        box_layout.setContentsMargins(4, 4, 4, 4)
        box_layout.setSpacing(0)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._apply_theme()

        for label, value in items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, value)
            item.setSizeHint(QSize(0, 34))
            self.list_widget.addItem(item)

        self.list_widget.setFixedHeight((34 * len(items)) + 2)

        box_layout.addWidget(self.list_widget)
        popup_layout.addWidget(self.popup_box)

        self.trigger.mousePressEvent = self.toggle_popup
        self.list_widget.itemClicked.connect(self.select_item)
        theme_manager.theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        tkn = tokens()
        selected_text = "#062f28" if tkn.name == "dark" else "#ffffff"
        if hasattr(self, "trigger"):
            self.trigger.setStyleSheet(f"""
                QFrame {{
                    background: {tkn.input};
                    border: 1px solid transparent;
                    border-radius: 8px;
                }}
                QFrame:hover {{
                    background: {tkn.hover};
                }}
            """)
        if hasattr(self, "label"):
            self.label.setStyleSheet(f"font-size: 14px; color: {tkn.text};")
            self.label.setAlignment((Qt.AlignRight if is_rtl() else Qt.AlignLeft) | Qt.AlignVCenter)
        if hasattr(self, "arrow"):
            self.arrow.setPixmap(qta.icon("fa5s.chevron-down", color=tkn.text_muted).pixmap(12, 12))
        if hasattr(self, "popup_box"):
            self.popup_box.setStyleSheet(f"""
                QFrame#SelectPopupBox {{
                    background: {tkn.surface};
                    border: 1px solid {tkn.border};
                    border-radius: 8px;
                }}
            """)
        if hasattr(self, "list_widget"):
            self.list_widget.setStyleSheet(f"""
                QListWidget {{
                    background: transparent;
                    border: none;
                    outline: none;
                }}
                QListWidget::item {{
                    padding: 8px 12px;
                    border-radius: 6px;
                    color: {tkn.text};
                    font-size: 14px;
                }}
                QListWidget::item:hover {{
                    background: {tkn.hover};
                }}
                QListWidget::item:selected {{
                    background: {tkn.brand};
                    color: {selected_text};
                }}
            """)

    def toggle_popup(self, event):
        if self.popup.isVisible():
            self.popup.hide()
            return

        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.popup.setFixedSize(self.width(), self.popup.sizeHint().height())
        end_pos = QPoint(pos.x(), pos.y() + 4)
        start_pos = QPoint(end_pos.x(), end_pos.y() - 6)
        self.popup.move(start_pos)
        self.popup_opacity.setOpacity(0)
        self.popup.show()
        self.popup.raise_()
        self.popup_pos_animation.stop()
        self.popup_pos_animation.setStartValue(start_pos)
        self.popup_pos_animation.setEndValue(end_pos)
        self.popup_opacity_animation.stop()
        self.popup_opacity_animation.setStartValue(0)
        self.popup_opacity_animation.setEndValue(1)
        self.popup_pos_animation.start()
        self.popup_opacity_animation.start()

    def select_item(self, item):
        self.label.setText(item.text())
        self.current_value = item.data(Qt.UserRole)
        self.popup.hide()
        self.valueChanged.emit(self.current_value)

    def set_value(self, value):
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)

            if item.data(Qt.UserRole) == value:
                self.label.setText(item.text())
                self.current_value = value
                self.list_widget.setCurrentItem(item)
                break


class SelectPopupFrame(QFrame):
    def resizeEvent(self, event):
        super().resizeEvent(event)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0, 0, -1, -1), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(company_name(t("app_name")))
        self.setObjectName("LoginWindow")
        self.role_labels = {}
        self._login_icons = []
        self._role_dots = []
        self._password_visible = False
        self.password_toggle_btn = None
        self._build()
        theme_manager.theme_changed.connect(lambda _: self._apply_theme())
        self.showMaximized()

    def _build(self):
        self._apply_theme()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.addStretch(1)

        self.card = QFrame()
        card = self.card
        card.setObjectName("LoginCard")
        card.setFixedWidth(450)
        card.setMinimumHeight(0)
        self.card_shadow = QGraphicsDropShadowEffect(card)
        self.card_shadow.setBlurRadius(34)
        self.card_shadow.setOffset(0, 14)
        self.card_shadow.setColor(QColor(6, 47, 40, 30))
        card.setGraphicsEffect(self.card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 24, 32, 32)
        card_layout.setSpacing(0)

        card_tools = QHBoxLayout()
        card_tools.setContentsMargins(0, 0, 0, 0)
        card_tools.setSpacing(0)
        card_tools.addStretch()
        self.theme_toggle = ThemeToggle()
        card_tools.addWidget(self.theme_toggle, 0, Qt.AlignRight)
        card_layout.addLayout(card_tools)
        card_layout.addSpacing(10)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)

        self.logo_box = QLabel()
        logo_box = self.logo_box
        logo_box.setFixedSize(64, 64)
        logo_box.setAlignment(Qt.AlignCenter)

        logo_row.addWidget(logo_box)
        card_layout.addLayout(logo_row)
        card_layout.addSpacing(16)

        self.title_lbl = QLabel()
        self.title_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.subtitle_lbl)

        card_layout.addSpacing(32)

        language_title = QHBoxLayout()
        language_title.setSpacing(8)

        language_icon = QLabel()
        language_icon.setFixedSize(20, 20)
        language_icon.setAlignment(Qt.AlignCenter)
        self.language_icon = language_icon

        self.language_lbl = QLabel()

        language_title.addWidget(language_icon)
        language_title.addWidget(self.language_lbl)
        language_title.addStretch()

        card_layout.addLayout(language_title)
        card_layout.addSpacing(8)

        self.lang_combo = CustomSelect(LANGUAGES)
        self._select_current_language()
        self.lang_combo.valueChanged.connect(self._on_language_changed)

        card_layout.addWidget(self.lang_combo)
        card_layout.addSpacing(24)

        self.username_lbl = self._field_label()
        card_layout.addWidget(self.username_lbl)
        card_layout.addSpacing(6)

        self.username_input, username_row = self._icon_input("fa5s.user")
        card_layout.addWidget(username_row)
        card_layout.addSpacing(20)

        self.password_lbl = self._field_label()
        card_layout.addWidget(self.password_lbl)
        card_layout.addSpacing(6)

        self.password_input, password_row = self._icon_input("fa5s.lock", password=True)
        self.password_input.returnPressed.connect(self._attempt_login)
        card_layout.addWidget(password_row)
        card_layout.addSpacing(24)

        self.login_btn = QPushButton()
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._attempt_login)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #030213;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #111827;
            }

            QPushButton:pressed {
                background: #020617;
            }
        """)

        card_layout.addWidget(self.login_btn)
        card_layout.addSpacing(32)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        self.separator = separator
        card_layout.addWidget(separator)
        card_layout.addSpacing(20)

        self.footer_lbl = QLabel()
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.footer_lbl)
        card_layout.addSpacing(8)

        roles_row = QHBoxLayout()
        roles_row.setAlignment(Qt.AlignCenter)
        roles_row.setSpacing(16)

        self._add_role_indicator(roles_row, "role_admin", "#064e3b")
        self._add_role_indicator(roles_row, "role_hr", "#9fe870")

        card_layout.addLayout(roles_row)

        outer.addWidget(card, 0, Qt.AlignHCenter)
        outer.addStretch(1)

        self._apply_theme()
        self._refresh_text()

    def _field_label(self):
        label = QLabel()
        return label

    def _icon_input(self, icon_name, password=False):
        container = QFrame()
        container.setObjectName("LoginInput")
        container.setFixedHeight(40)

        row = QHBoxLayout(container)
        row.setContentsMargins(16, 0, 12, 0)
        row.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(22, 22)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label._myhr_icon_name = icon_name
        icon_label.setStyleSheet("background: transparent; border: none;")
        self._login_icons.append(icon_label)
        row.addWidget(icon_label)

        field = QLineEdit()
        field.setFixedHeight(38)

        if password:
            field.setEchoMode(QLineEdit.Password)

        field.setStyleSheet("QLineEdit { background: transparent; border: none; padding: 0; } QLineEdit:focus { border: none; }")

        row.addWidget(field, 1)

        if password:
            toggle_btn = QPushButton()
            toggle_btn.setFixedSize(28, 28)
            toggle_btn.setCursor(Qt.PointingHandCursor)
            toggle_btn.setFocusPolicy(Qt.NoFocus)
            toggle_btn.clicked.connect(self._toggle_password_visibility)
            self.password_toggle_btn = toggle_btn
            row.addWidget(toggle_btn)
            self._update_password_toggle_icon()

        return field, container

    def _add_role_indicator(self, row, role_key, color):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot._myhr_dot_color = color
        self._role_dots.append(dot)

        label = QLabel()

        layout.addWidget(dot)
        layout.addWidget(label)
        row.addWidget(wrap)

        self.role_labels[role_key] = label

    def paintEvent(self, event):
        tkn = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fbfcf8" if tkn.name == "light" else "#050806"))

        if tkn.name == "light":
            blob = QColor("#9fe870")
            blob.setAlpha(54)
            line = QColor("#1f4a40")
            line.setAlpha(18)
            dot = QColor("#0f7a45")
            dot.setAlpha(58)
        else:
            blob = QColor("#9fe870")
            blob.setAlpha(24)
            line = QColor("#9fe870")
            line.setAlpha(16)
            dot = QColor("#9fe870")
            dot.setAlpha(46)

        painter.setPen(Qt.NoPen)
        painter.setBrush(blob)
        painter.drawEllipse(QRectF(-80, -70, 270, 270))
        painter.drawEllipse(QRectF(self.width() - 220, self.height() - 220, 320, 320))

        painter.setBrush(dot)
        spacing = 14
        start_x = int(self.width() * 0.70)
        start_y = int(self.height() * 0.26)
        for row in range(7):
            for col in range(7):
                painter.drawEllipse(QRectF(start_x + col * spacing, start_y + row * spacing, 2.2, 2.2))

        painter.setPen(QPen(line, 1))
        for i in range(13):
            painter.drawArc(QRectF(-120 + i * 16, 35 + i * 5, 520 + i * 18, 360 + i * 12), 20 * 16, 145 * 16)
        for i in range(10):
            painter.drawArc(QRectF(self.width() - 430 - i * 14, self.height() - 310 - i * 8, 460 + i * 18, 340 + i * 12), 190 * 16, 130 * 16)

        painter.end()
        super().paintEvent(event)

    def _apply_theme(self):
        tkn = tokens()
        primary_text = "#062f28" if tkn.name == "dark" else "#ffffff"
        self.setStyleSheet("QWidget#LoginWindow { background: transparent; }")
        if hasattr(self, "card_shadow"):
            self.card_shadow.setColor(QColor(6, 47, 40, 30 if tkn.name == "light" else 70))
        if hasattr(self, "card"):
            self.card.setStyleSheet(f"""
                QFrame#LoginCard {{
                    background: {tkn.surface};
                    border: 1px solid {tkn.border};
                    border-radius: 16px;
                }}
                QFrame#LoginCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        if hasattr(self, "logo_box"):
            self.logo_box.setPixmap(qta.icon("fa5s.clipboard-list", color=primary_text).pixmap(40, 40))
            self.logo_box.setStyleSheet(f"background: {tkn.brand}; border-radius: 12px;")
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {tkn.text};")
        if hasattr(self, "subtitle_lbl"):
            self.subtitle_lbl.setStyleSheet(f"font-size: 16px; color: {tkn.text_muted};")
        if hasattr(self, "language_icon"):
            self.language_icon.setPixmap(qta.icon("fa5s.globe", color=tkn.text).pixmap(16, 16))
        if hasattr(self, "language_lbl"):
            self.language_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {tkn.text};")
        for label in (getattr(self, "username_lbl", None), getattr(self, "password_lbl", None)):
            if label is not None:
                label.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {tkn.text};")
        for container in self.findChildren(QFrame, "LoginInput"):
            container.setStyleSheet(f"QFrame#LoginInput {{ background: {tkn.input}; border: 1px solid transparent; border-radius: 8px; }}")
        for icon_label in getattr(self, "_login_icons", []):
            icon_label.setPixmap(qta.icon(icon_label._myhr_icon_name, color=tkn.text_soft).pixmap(18, 18))
        if hasattr(self, "login_btn"):
            self.login_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tkn.brand};
                    border: none;
                    border-radius: 8px;
                    color: {primary_text};
                    font-size: 15px;
                    font-weight: 700;
                }}
                QPushButton:hover {{ background: {tkn.brand_hover}; }}
                QPushButton:pressed {{ background: {tkn.brand}; }}
            """)
        if hasattr(self, "separator"):
            self.separator.setStyleSheet(f"border: none; border-top: 1px solid {tkn.border};")
        if hasattr(self, "footer_lbl"):
            self.footer_lbl.setStyleSheet(f"font-size: 14px; color: {tkn.text_muted};")
        for dot in getattr(self, "_role_dots", []):
            dot.setStyleSheet(f"background: {dot._myhr_dot_color}; border-radius: 5px;")
        for label in self.role_labels.values():
            label.setStyleSheet(f"font-size: 14px; color: {tkn.text_muted};")
        self._update_password_toggle_icon()

    def _toggle_password_visibility(self):
        if not hasattr(self, "password_input"):
            return

        self._password_visible = not self._password_visible
        self.password_input.setEchoMode(QLineEdit.Normal if self._password_visible else QLineEdit.Password)
        self._update_password_toggle_icon()

    def _update_password_toggle_icon(self):
        if not getattr(self, "password_toggle_btn", None):
            return

        tkn = tokens()
        icon_name = "fa5s.eye-slash" if self._password_visible else "fa5s.eye"
        tooltip_key = "hide_password" if self._password_visible else "show_password"
        self.password_toggle_btn.setIcon(qta.icon(icon_name, color=tkn.text_soft))
        self.password_toggle_btn.setIconSize(QSize(15, 15))
        self.password_toggle_btn.setToolTip(t(tooltip_key))
        self.password_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {tkn.hover};
            }}
        """)

    def _select_current_language(self):
        self.lang_combo.set_value(get_language())
        self._apply_layout_direction()

    def _apply_layout_direction(self):
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)
        self._apply_text_direction()

    def _apply_text_direction(self):
        align = (Qt.AlignRight if is_rtl() else Qt.AlignLeft) | Qt.AlignVCenter
        for widget_name in ("username_lbl", "password_lbl", "username_input", "password_input"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setAlignment(align)

    def _language_caption(self):
        return t("language")

    def _on_language_changed(self, value):
        set_language(value)
        self._apply_layout_direction()
        self._refresh_text()

    def _refresh_text(self):
        self.setWindowTitle(company_name(t("app_name")))
        self.title_lbl.setText(company_name(t("app_name")))
        self.subtitle_lbl.setText(company_subtitle(t("app_subtitle")))
        self.language_lbl.setText(self._language_caption())
        self.username_lbl.setText(t("username"))
        self.username_input.setPlaceholderText(t("username_placeholder"))
        self.password_lbl.setText(t("password"))
        self.password_input.setPlaceholderText(t("password_placeholder"))
        self.login_btn.setText(t("login_button"))
        self.footer_lbl.setText(t("authorized_only"))
        self._update_password_toggle_icon()
        self._apply_text_direction()

        for role_key, label in self.role_labels.items():
            label.setText(t(role_key))

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            _warning(self, t("warning"), t("login_fill_fields"))
            return

        user = verify_login(username, password)

        if user:
            from src.ui.main_window import MainWindow

            self.main_window = MainWindow(user)
            self.main_window.show()
            self.close()
        else:
            _critical(self, t("error"), t("login_failed"))
            self.password_input.clear()
            self.password_input.setFocus()


def _styled_message_box(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet(_message_box_ss())
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)
