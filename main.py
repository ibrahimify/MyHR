"""
MyHR — Entry point.
Run with: python main.py
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.database.connection import init_db
from src.ui.login_window import LoginWindow


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("MyHR")
    app.setStyle("Fusion")

    # Global font
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()