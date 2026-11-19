from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QRect, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QCursor

class CompactSubtitlePill(QWidget):
    """Ultra-compact, sleek floating pill that displays crisp AI conversational responses
    docked cleanly right below the AmazingUI Sphere Orb, without giant window clutter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.max_pill_width = 320
        self._init_ui()

        # Auto-dismiss timer (default 6.5s)
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide)

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget#PillContainer {
                background-color: rgba(14, 16, 26, 235);
                border: 1px solid rgba(139, 92, 246, 110);
                border-radius: 16px;
            }
            QLabel#SparkleIcon {
                font-size: 14px;
                color: #A855F7;
                padding-top: 1px;
            }
            QLabel#SubtitleText {
                color: #F8FAFC;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
                font-weight: 500;
                line-height: 1.38;
            }
        """)

        # Drop shadow for clean separation from any background window
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.container = QWidget()
        self.container.setObjectName("PillContainer")
        self.container.setGraphicsEffect(shadow)

        pill_layout = QHBoxLayout(self.container)
        pill_layout.setContentsMargins(14, 10, 14, 10)
        pill_layout.setSpacing(10)

        # AI Sparkle Icon
        self.sparkle = QLabel("✨")
        self.sparkle.setObjectName("SparkleIcon")
        self.sparkle.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        pill_layout.addWidget(self.sparkle)

        # Crisp Response Text Label
        self.label = QLabel("")
        self.label.setObjectName("SubtitleText")
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        pill_layout.addWidget(self.label, 1)

        outer_layout.addWidget(self.container)

    def display_below_orb(self, text: str, orb_rect: QRect, duration_ms: int = 7000):
        """Formats and docks the pill directly under the orb."""
        if not text:
            return

        # Clean text
        clean_text = text.strip()
        # Remove markdown headers or bold symbols if any for super clean reading
        clean_text = clean_text.replace("### ", "").replace("## ", "").replace("# ", "")

        self.label.setText(clean_text)
        self.label.setMaximumWidth(self.max_pill_width)
        self.container.setMaximumWidth(self.max_pill_width + 36)
        
        self.adjustSize()

        # Position right below the orb, right-aligned to screen margin
        margin_x = 16
        screen = QApplication.primaryScreen().availableGeometry()
        x = min(screen.right() - self.width() - margin_x, orb_rect.right() - self.width() + 20)
        y = orb_rect.bottom() + 4

        # Bounds check
        if y + self.height() > screen.bottom() - 20:
            y = screen.bottom() - self.height() - 20
        if x < screen.left() + 20:
            x = screen.left() + 20

        self.move(x, y)
        self.show()
        self.raise_()

        # Reset dismiss timer
        self.dismiss_timer.stop()
        # Calculate reading duration: min 5s, + 60ms per word
        word_count = len(clean_text.split())
        read_time = max(5000, min(14000, 3500 + word_count * 65))
        self.dismiss_timer.start(read_time)

    def mousePressEvent(self, event):
        """Clicking the pill copies text to clipboard and dismisses it cleanly."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.label.text())
        self.hide()
