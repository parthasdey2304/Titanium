from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

class CodeViewerWindow(QWidget):
    """Sleek dark-mode window for displaying code and research results."""

    def __init__(self, title: str = "Titanium Response", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(650, 480)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #12131C;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
            }
            QTextEdit {
                background-color: #1A1B26;
                color: #A9B1D6;
                border: 1px solid #292E42;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #A855F7);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #9333EA);
            }
            QLabel {
                font-size: 15px;
                font-weight: 600;
                color: #F8FAFC;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("✨ Titanium Assistant")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.copy_btn = QPushButton("Copy Text")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(self.copy_btn)

        layout.addLayout(header_layout)

        # Content Text Box
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

    def display_content(self, text: str, title: str = "Titanium Response"):
        self.title_label.setText(f"✨ {title}")
        self.text_area.setPlainText(text)
        self.show()
        self.raise_()
        self.activateWindow()

    def _copy_to_clipboard(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_area.toPlainText())
        self.copy_btn.setText("Copied! ✓")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy Text"))
