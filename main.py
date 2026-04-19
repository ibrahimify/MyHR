import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.database.connection import init_db
from src.ui.login_window import LoginWindow


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("MyHR")
    app.setStyle("Fusion")

    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    arrow_path = os.path.join(os.path.dirname(__file__), "src", "ui", "assets", "chevron_down.svg").replace("\\", "/")

    app.setStyleSheet(f"""
        QLabel                {{ color: #111827; }}
        QPushButton           {{ font-family: 'Segoe UI'; }}
        QLineEdit, QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {{
            color: #111827; background: #f9fafb;
            border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 0 12px; min-height: 36px;
            font-size: 13px;
        }}
        QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {{
            border-color: #2563eb; background: white;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: #2563eb; background: white;
        }}
        QComboBox {{
            color: #111827; background: #f9fafb;
            border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 0 10px 0 12px; min-height: 36px;
            font-size: 13px;
        }}
        QComboBox:focus {{ border-color: #2563eb; }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url({arrow_path});
            width: 10px;
            height: 6px;
        }}
        QTableWidget          {{ color: #111827; gridline-color: #f3f4f6; border: none; }}
        QTableWidget::item    {{ color: #111827; }}
        QHeaderView::section  {{ color: #6b7280; background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 8px 12px; font-size: 12px; font-weight: bold; }}
        QScrollBar:vertical   {{ width: 6px; background: transparent; }}
        QScrollBar::handle:vertical {{ background: #d1d5db; border-radius: 3px; min-height: 20px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ height: 6px; background: transparent; }}
        QScrollBar::handle:horizontal {{ background: #d1d5db; border-radius: 3px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QMessageBox           {{ color: #111827; background: white; }}
        QMessageBox QLabel    {{ color: #111827; }}
        QDialog               {{ background: white; color: #111827; }}
        QDialog QLabel        {{ color: #111827; }}
        QToolTip              {{ background: #111827; color: white; border: none; padding: 4px 8px; border-radius: 6px; }}
        QTabWidget::pane      {{ border: none; background: #f9fafb; }}
        QTabBar::tab          {{ background: white; color: #6b7280; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; font-size: 13px; }}
        QTabBar::tab:selected {{ color: #030213; border-bottom: 2px solid #030213; font-weight: bold; }}
        QTabBar::tab:hover    {{ color: #111827; }}
    """)

    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
