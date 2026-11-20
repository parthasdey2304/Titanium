from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QColor, QCursor

class CompactSubtitlePill(QWidget):
    """Sleek floating conversational pill docked directly below the Siri Orb.
    Renders user prompt in a Gemini-style dark bubble (black background, shifted right)
    and AI response with sparkle icon, floating cleanly on screen without giant window clutter.
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
        
        self.max_pill_width = 330
        self._last_user_text = ""
        self._last_ai_text = ""
        self._init_ui()

        # Auto-dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide)

    def _init_ui(self):
        # Drop shadow for clean separation from desktop windows
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(6, 6, 6, 6)
        self.outer_layout.setSpacing(6)

        # 1. USER MESSAGE CONTAINER (Gemini Dark Mode style - black background, shifted to the right)
        self.user_wrapper = QWidget()
        self.user_wrapper_layout = QHBoxLayout(self.user_wrapper)
        self.user_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.user_wrapper_layout.addStretch(1) # Pushes user bubble to the right

        self.user_bubble = QWidget()
        self.user_bubble.setStyleSheet("""
            QWidget {
                background-color: #131314;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px 16px 4px 16px;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
                font-weight: 500;
                line-height: 1.35;
                padding: 6px 12px;
            }
        """)
        user_bubble_layout = QHBoxLayout(self.user_bubble)
        user_bubble_layout.setContentsMargins(0, 0, 0, 0)
        self.user_label = QLabel("")
        self.user_label.setWordWrap(True)
        self.user_label.setMaximumWidth(self.max_pill_width - 40)
        user_bubble_layout.addWidget(self.user_label)
        self.user_wrapper_layout.addWidget(self.user_bubble)
        self.user_wrapper.hide() # Hidden until user speaks

        self.outer_layout.addWidget(self.user_wrapper)

        # 2. AI RESPONSE CONTAINER (Sleek dark card with purple border and sparkle)
        self.ai_bubble = QWidget()
        self.ai_bubble.setObjectName("AIBubbleContainer")
        self.ai_bubble.setGraphicsEffect(shadow)
        self.ai_bubble.setStyleSheet("""
            QWidget#AIBubbleContainer {
                background-color: rgba(14, 16, 26, 240);
                border: 1px solid rgba(139, 92, 246, 115);
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

        ai_layout = QHBoxLayout(self.ai_bubble)
        ai_layout.setContentsMargins(12, 9, 14, 9)
        ai_layout.setSpacing(9)

        self.sparkle = QLabel("✨")
        self.sparkle.setObjectName("SparkleIcon")
        self.sparkle.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        ai_layout.addWidget(self.sparkle)

        self.ai_label = QLabel("")
        self.ai_label.setObjectName("SubtitleText")
        self.ai_label.setWordWrap(True)
        self.ai_label.setMaximumWidth(self.max_pill_width)
        ai_layout.addWidget(self.ai_label, 1)

        self.outer_layout.addWidget(self.ai_bubble)

    def show_user_prompt(self, user_text: str, orb_rect: QRect):
        """Immediately displays user's spoken words in black Gemini dark-mode bubble shifted right."""
        if not user_text or not user_text.strip():
            return

        self._last_user_text = user_text.strip()
        self.user_label.setText(self._last_user_text)
        self.user_wrapper.show()

        # Show thinking state on AI bubble while processing
        self.sparkle.setText("✨")
        self.ai_label.setText("Thinking...")
        self.ai_bubble.show()

        self._reposition_below_orb(orb_rect)
        self.dismiss_timer.stop()
        self.dismiss_timer.start(10000)

    def display_below_orb(self, ai_text: str, orb_rect: QRect, user_text: str = ""):
        """Formats and docks the conversation turn directly under the orb."""
        if not ai_text and not user_text:
            return

        if user_text and user_text.strip():
            self._last_user_text = user_text.strip()
            self.user_label.setText(self._last_user_text)
            self.user_wrapper.show()
        elif not self._last_user_text:
            self.user_wrapper.hide()

        clean_ai = ai_text.strip().replace("### ", "").replace("## ", "").replace("# ", "")
        self._last_ai_text = clean_ai
        if "🔴" in clean_ai:
            self.sparkle.setText("🔴")
        else:
            self.sparkle.setText("✨")
        self.ai_label.setText(clean_ai)
        self.ai_bubble.show()

        self._reposition_below_orb(orb_rect)

        # Reading duration: min 5s, + 65ms per word
        word_count = len(clean_ai.split())
        read_time = max(5500, min(14000, 3600 + word_count * 65))
        self.dismiss_timer.stop()
        self.dismiss_timer.start(read_time)

    def _reposition_below_orb(self, orb_rect: QRect):
        """Calculates geometry docking below the orb, shifted slightly to the right."""
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()

        # Shift slightly right towards the screen edge
        shift_right_offset = 28
        x = min(screen.right() - self.width() - 14, orb_rect.right() - self.width() + shift_right_offset)
        y = orb_rect.bottom() + 6

        # Screen boundary constraints
        if y + self.height() > screen.bottom() - 20:
            y = screen.bottom() - self.height() - 20
        if x < screen.left() + 16:
            x = screen.left() + 16

        self.move(x, y)
        self.show()
        self.raise_()

    def mousePressEvent(self, event):
        """Clicking copies conversation turn to clipboard and hides the pill."""
        clipboard = QApplication.clipboard()
        copy_text = f"User: {self._last_user_text}\nTitanium: {self._last_ai_text}" if self._last_user_text else self._last_ai_text
        clipboard.setText(copy_text)
        self.hide()
