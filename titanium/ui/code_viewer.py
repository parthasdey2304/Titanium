from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QApplication
)
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QFont, QColor

class CodeViewerWindow(QWidget):
    """Floating frosted-glass response card that docks directly below the Siri Orb."""

    def __init__(self, title: str = "Titanium Response", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(460, 420)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: rgba(18, 19, 28, 240);
                border: 1px solid rgba(99, 102, 241, 140);
                border-radius: 14px;
            }
            QTextEdit {
                background-color: rgba(13, 14, 22, 220);
                color: #E2E8F0;
                border: 1px solid rgba(54, 58, 79, 160);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
            QPushButton#CopyBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #A855F7);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#CopyBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #9333EA);
            }
            QPushButton#CloseBtn {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton#CloseBtn:hover {
                color: #F43F5E;
            }
            QLabel#TitleLabel {
                font-size: 13px;
                font-weight: 700;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
        """)

        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Card Container
        container = QWidget()
        container.setObjectName("MainContainer")
        card_layout = QVBoxLayout(container)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)

        # Header Bar
        header = QHBoxLayout()
        self.title_label = QLabel("✨ Titanium Assistant")
        self.title_label.setObjectName("TitleLabel")
        header.addWidget(self.title_label)
        header.addStretch()

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("CopyBtn")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        header.addWidget(self.copy_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)

        card_layout.addLayout(header)

        # Content Text Area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        card_layout.addWidget(self.text_area)

        outer.addWidget(container)

    def display_below_orb(self, text: str, orb_rect: QRect, title: str = "Titanium Response"):
        """Positions and displays the result card directly underneath the Orb."""
        self.title_label.setText(f"✨ {title}")
        self.text_area.setPlainText(text)

        # Dock below the orb, right-aligned with the orb
        screen = QApplication.primaryScreen().availableGeometry()
        x = orb_rect.right() - self.width() + 10
        y = orb_rect.bottom() + 12

        # Stay within screen edges
        if x + self.width() > screen.right() - 16:
            x = screen.right() - self.width() - 16
        if x < screen.left() + 16:
            x = screen.left() + 16
        if y + self.height() > screen.bottom() - 16:
            # If not enough room below, dock to the left of the orb
            y = orb_rect.top()
            x = orb_rect.left() - self.width() - 12

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def _copy_to_clipboard(self):
        QApplication.clipboard().setText(self.text_area.toPlainText())
        self.copy_btn.setText("Copied! ✓")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy"))
