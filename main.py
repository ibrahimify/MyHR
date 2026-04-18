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

    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    # Global fix — force dark text on all widgets
    app.setStyleSheet("""
        QWidget { color: #1a1d2e; }
        QLabel  { color: #1a1d2e; }
        QLineEdit, QTextEdit, QDateEdit, QComboBox, QSpinBox {
            color: #1a1d2e;
            background: #f9fafb;
        }
        QTableWidget { color: #1a1d2e; }
        QMessageBox  { color: #1a1d2e; background: white; }
        QMessageBox QLabel { color: #1a1d2e; }
    """)

    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()