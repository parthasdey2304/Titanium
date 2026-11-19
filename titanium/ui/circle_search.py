import io
from typing import Optional, Callable
from PIL import Image
import mss

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QFont

class CircleToSearchOverlay(QWidget):
    """Fullscreen screen-selection sniper overlay for Circle to Search."""
    selection_completed = Signal(bytes) # Emits PNG crop bytes

    def __init__(self, on_crop_captured: Optional[Callable[[bytes], None]] = None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        self.begin_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.fullscreen_pixmap = None
        
        if on_crop_captured:
            self.selection_completed.connect(on_crop_captured)

    def trigger(self):
        """Show overlay over all screens."""
        # Grab screen geometry
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.setGeometry(geo)
        self.is_selecting = False
        self.begin_point = QPoint()
        self.end_point = QPoint()
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_point = event.position().toPoint()
            self.end_point = self.begin_point
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.end_point = event.position().toPoint()
            self.hide()
            self._capture_crop()

    def keyPressEvent(self, event):
        # Escape key cancels selection
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Translucent dark mask
        painter.fillRect(self.rect(), QColor(10, 10, 20, 140))

        # Instructions banner at top center
        painter.setPen(QColor(255, 255, 255, 220))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        painter.drawText(
            self.rect().adjusted(0, 30, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "✨ Circle or Drag to select an area for Titanium to analyze (Esc to cancel)"
        )

        if self.is_selecting:
            selection_rect = QRect(self.begin_point, self.end_point).normalized()
            
            # Clear inside the selection rectangle so underlying screen is bright
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Glowing border around selection
            pen = QPen(QColor(99, 102, 241, 230), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRoundedRect(selection_rect, 6, 6)

            # Sub-glow
            pen2 = QPen(QColor(168, 85, 247, 180), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen2)
            painter.drawRoundedRect(selection_rect.adjusted(2, 2, -2, -2), 4, 4)

    def _capture_crop(self):
        rect = QRect(self.begin_point, self.end_point).normalized()
        if rect.width() < 10 or rect.height() < 10:
            return # Ignore accidental tiny clicks

        # Capture using mss
        with mss.mss() as sct:
            monitor = {
                "top": rect.top(),
                "left": rect.left(),
                "width": rect.width(),
                "height": rect.height()
            }
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
            self.selection_completed.emit(png_bytes)
