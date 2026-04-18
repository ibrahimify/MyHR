from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CommendationsPage(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        layout = QVBoxLayout(self)
        lbl = QLabel("🔧  Commendations\n\nUnder construction")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; color: #9ca3af;")
        layout.addWidget(lbl)
