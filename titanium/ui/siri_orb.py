import math
import sys
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QMenu, QApplication, QInputDialog, QLineEdit
)
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QRectF, Signal, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient,
    QPen, QBrush, QCursor, QPainterPath
)

class SiriOrbWidget(QWidget):
    """Next-Gen Siri / Apple Intelligence Organic Glass Orb with 4 distinct states:
    - Listening: Acoustic shockwaves and electric cyan-violet fluid plasma
    - Thinking: Dual-vortex cosmic nebula rotating in real-time
    - Speaking: Rhythmic voice-reactive coral/amber warm bounce
    - Seeing: Emerald-mint cybernetic vision scanner and targeting reticle
    
    Auto-Show & Auto-Hide:
    - Invisible when doing other things in Windows.
    - Instantly reveals when 'Hey Titanium' is spoken or hotkey triggered.
    - Gracefully fades away after conversation goes idle.
    """

    request_circle_search = Signal()
    request_screen_share_toggle = Signal()
    request_user_prompt = Signal(str)
    request_install = Signal()
    request_toggle_listening = Signal()

    def __init__(self, size: int = 94):
        super().__init__()
        self.orb_size = size
        # Generous padding for multi-layer bloom and acoustic shockwaves
        self.setFixedSize(size + 50, size + 50)

        # Transparent, frameless, always-on-top window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # States: 'idle', 'listening', 'thinking', 'speaking', 'seeing'
        self.state = "idle"
        self.screen_sharing = False

        # Physics & Animation Variables
        self.phase = 0.0
        self.pulse_scale = 1.0
        self.glow_intensity = 0.7
        self.drag_position = QPoint()

        # Ensure 100% permanent visibility at full opacity
        self.setWindowOpacity(1.0)

        # 60 FPS animation loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)

        self._dock_to_bottom_left()

    def _dock_to_bottom_left(self):
        """Positions the orb at bottom-left above the Windows taskbar."""
        screen = QApplication.primaryScreen().availableGeometry()
        margin_x = 35
        margin_y = 45
        x = screen.left() + margin_x
        y = screen.bottom() - self.height() - margin_y
        self.move(x, y)

    def reveal(self):
        """Ensures Orb is raised and visible."""
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()

    def set_state(self, new_state: str):
        """Updates visual state ('idle', 'listening', 'thinking', 'speaking', 'seeing')."""
        self.state = new_state
        if self.screen_sharing:
            self.state = "seeing"
        self.update()

    def set_screen_sharing(self, active: bool):
        self.screen_sharing = active
        self.set_state("seeing" if active else "idle")

    def _update_animation(self):
        """Calculates dynamic fluid physics for each specific state."""
        self.phase += 0.05
        if self.phase > 1000:
            self.phase = 0.0

        if self.state == "idle":
            self.pulse_scale = 1.0 + 0.03 * math.sin(self.phase * 1.5)
            self.glow_intensity = 0.6
        elif self.state == "listening":
            # High-energy responsive audio wave pulse
            self.pulse_scale = 1.0 + 0.09 * math.sin(self.phase * 4.2)
            self.glow_intensity = 0.95
        elif self.state == "thinking":
            # Smooth cosmic breathing
            self.pulse_scale = 1.0 + 0.05 * math.cos(self.phase * 2.8)
            self.glow_intensity = 0.90
        elif self.state == "speaking":
            # Voice-amplitude bounce
            self.pulse_scale = 1.0 + 0.12 * abs(math.sin(self.phase * 5.5))
            self.glow_intensity = 0.95
        elif self.state == "seeing":
            # Controlled cybernetic pulse
            self.pulse_scale = 1.0 + 0.04 * math.sin(self.phase * 2.0)
            self.glow_intensity = 0.88

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = (self.orb_size / 2.0) * self.pulse_scale

        if self.state == "seeing":
            self._paint_seeing_state(painter, cx, cy, r)
        elif self.state == "listening":
            self._paint_listening_state(painter, cx, cy, r)
        elif self.state == "thinking":
            self._paint_thinking_state(painter, cx, cy, r)
        elif self.state == "speaking":
            self._paint_speaking_state(painter, cx, cy, r)
        else: # idle
            self._paint_idle_state(painter, cx, cy, r)

    # =========================================================================
    # LOOK 1: LISTENING (Acoustic shockwaves + Electric Cyan/Azure/Purple Plasma)
    # =========================================================================
    def _paint_listening_state(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Concentric Acoustic Waves Radiating Outward
        for i in range(3):
            wave_progress = ((self.phase * 1.8 + i * 0.33) % 1.0)
            wave_r = r * (1.05 + wave_progress * 0.42)
            wave_alpha = int(180 * (1.0 - wave_progress))
            pen = QPen(QColor(0, 245, 255, wave_alpha), 1.8)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - wave_r, cy - wave_r, wave_r * 2, wave_r * 2))

        # 2. Outer Electric Atmosphere Glow
        grad_outer = QRadialGradient(cx, cy, r * 1.35)
        grad_outer.setColorAt(0.0, QColor(0, 229, 255, 170))
        grad_outer.setColorAt(0.5, QColor(99, 102, 241, 100))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.35, cy - r * 1.35, r * 2.7, r * 2.7))

        # 3. Siri Organic Plasma Core (Multi-Center Radial Blend)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Base Sphere
        base_grad = QRadialGradient(cx, cy, r)
        base_grad.setColorAt(0.0, QColor(147, 51, 234, 240))  # Purple
        base_grad.setColorAt(0.7, QColor(30, 27, 75, 240))
        base_grad.setColorAt(1.0, QColor(15, 23, 42, 250))
        p.setBrush(QBrush(base_grad))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Orbiting Cyan Plasma Light
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        angle1 = self.phase * 3.5
        c1x = cx + math.cos(angle1) * (r * 0.38)
        c1y = cy + math.sin(angle1) * (r * 0.38)
        p1 = QRadialGradient(c1x, c1y, r * 0.75)
        p1.setColorAt(0.0, QColor(0, 245, 255, 250))
        p1.setColorAt(0.6, QColor(0, 122, 255, 160))
        p1.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(p1))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Orbiting Magenta Plasma Light (Counter-phase)
        c2x = cx + math.cos(angle1 + math.pi) * (r * 0.38)
        c2y = cy + math.sin(angle1 + math.pi) * (r * 0.38)
        p2 = QRadialGradient(c2x, c2y, r * 0.75)
        p2.setColorAt(0.0, QColor(244, 63, 94, 240))
        p2.setColorAt(0.6, QColor(168, 85, 247, 140))
        p2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(p2))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Glass Highlight Cap
        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 2: THINKING (Cosmic Nebula & Swirling Dual-Vortex Ring)
    # =========================================================================
    def _paint_thinking_state(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Outer Cosmic Nebula Glow
        grad_outer = QRadialGradient(cx, cy, r * 1.35)
        grad_outer.setColorAt(0.0, QColor(147, 51, 234, 160))
        grad_outer.setColorAt(0.6, QColor(236, 72, 153, 90))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.35, cy - r * 1.35, r * 2.7, r * 2.7))

        # 2. Deep Galaxy Core
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        base_grad = QRadialGradient(cx, cy, r)
        base_grad.setColorAt(0.0, QColor(15, 23, 42, 240))
        base_grad.setColorAt(0.8, QColor(30, 27, 75, 240))
        base_grad.setColorAt(1.0, QColor(10, 10, 20, 250))
        p.setBrush(QBrush(base_grad))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # 3. Rotating Vortex Ring (Smooth Conical Plasma)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        rot_angle = (self.phase * 80) % 360
        conic = QConicalGradient(cx, cy, rot_angle)
        conic.setColorAt(0.0, QColor(168, 85, 247, 240))
        conic.setColorAt(0.33, QColor(236, 72, 153, 240))
        conic.setColorAt(0.66, QColor(99, 102, 241, 240))
        conic.setColorAt(1.0, QColor(168, 85, 247, 240))
        p.setBrush(QBrush(conic))
        p.drawEllipse(QRectF(cx - r * 0.92, cy - r * 0.92, r * 1.84, r * 1.84))

        # 4. Swirling Internal Galaxy Core
        core = QRadialGradient(cx, cy, r * 0.55)
        core.setColorAt(0.0, QColor(255, 255, 255, 220))
        core.setColorAt(0.4, QColor(192, 132, 252, 180))
        core.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(core))
        p.drawEllipse(QRectF(cx - r * 0.55, cy - r * 0.55, r * 1.1, r * 1.1))

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 3: SPEAKING (Warm Sunset Coral, Amber & Voice Amplitude Bounce)
    # =========================================================================
    def _paint_speaking_state(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Radiant Sunset Corona
        grad_outer = QRadialGradient(cx, cy, r * 1.4)
        grad_outer.setColorAt(0.0, QColor(255, 75, 43, 170))
        grad_outer.setColorAt(0.5, QColor(245, 158, 11, 100))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.4, cy - r * 1.4, r * 2.8, r * 2.8))

        # 2. Base Sphere
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(225, 29, 72, 240))
        base.setColorAt(0.7, QColor(136, 19, 55, 240))
        base.setColorAt(1.0, QColor(15, 23, 42, 250))
        p.setBrush(QBrush(base))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # 3. Dynamic Audio Plasma Heat (Screen Blend)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        heat_phase = self.phase * 4.0
        hx = cx + math.cos(heat_phase) * (r * 0.25)
        hy = cy + math.sin(heat_phase) * (r * 0.25)
        heat = QRadialGradient(hx, hy, r * 0.85)
        heat.setColorAt(0.0, QColor(251, 191, 36, 250))  # Bright Amber
        heat.setColorAt(0.5, QColor(244, 63, 94, 200))   # Hot Rose
        heat.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(heat))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 4: SEEING / VISION (Cyber Emerald, Matrix Mint & Radar Reticle)
    # =========================================================================
    def _paint_seeing_state(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Cyber Emerald Outer Aura
        grad_outer = QRadialGradient(cx, cy, r * 1.35)
        grad_outer.setColorAt(0.0, QColor(16, 185, 129, 180))
        grad_outer.setColorAt(0.6, QColor(6, 182, 212, 100))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.35, cy - r * 1.35, r * 2.7, r * 2.7))

        # 2. Cyber Core
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(6, 78, 59, 240))
        base.setColorAt(0.8, QColor(15, 23, 42, 250))
        base.setColorAt(1.0, QColor(5, 5, 10, 250))
        p.setBrush(QBrush(base))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # 3. Rotating Radar Scanner Beam
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        radar_angle = (self.phase * 120) % 360
        conic = QConicalGradient(cx, cy, radar_angle)
        conic.setColorAt(0.0, QColor(52, 211, 153, 240))
        conic.setColorAt(0.2, QColor(6, 182, 212, 140))
        conic.setColorAt(0.4, QColor(0, 0, 0, 0))
        conic.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(conic))
        p.drawEllipse(QRectF(cx - r * 0.95, cy - r * 0.95, r * 1.9, r * 1.9))

        # 4. Concentric Targeting Aperture Ring & Ticks
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        reticle_pen = QPen(QColor(52, 211, 153, 220), 1.5)
        p.setPen(reticle_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r * 0.7, cy - r * 0.7, r * 1.4, r * 1.4))

        # 4 Precision Tick Marks
        tick_len = r * 0.15
        p.drawLine(cx, cy - r * 0.75, cx, cy - r * 0.75 + tick_len)
        p.drawLine(cx, cy + r * 0.75 - tick_len, cx, cy + r * 0.75)
        p.drawLine(cx - r * 0.75, cy, cx - r * 0.75 + tick_len, cy)
        p.drawLine(cx + r * 0.75 - tick_len, cy, cx + r * 0.75, cy)

        # Center Optical Pupil
        pupil = QRadialGradient(cx, cy, r * 0.28)
        pupil.setColorAt(0.0, QColor(255, 255, 255, 240))
        pupil.setColorAt(0.5, QColor(52, 211, 153, 190))
        pupil.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(pupil))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r * 0.28, cy - r * 0.28, r * 0.56, r * 0.56))

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 5: IDLE (Tranquil Iridescent Glass Orb)
    # =========================================================================
    def _paint_idle_state(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.3)
        grad_outer.setColorAt(0.0, QColor(99, 102, 241, 120))
        grad_outer.setColorAt(0.6, QColor(236, 72, 153, 60))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.3, cy - r * 1.3, r * 2.6, r * 2.6))

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(99, 102, 241, 230))
        base.setColorAt(0.7, QColor(30, 27, 75, 230))
        base.setColorAt(1.0, QColor(15, 23, 42, 240))
        p.setBrush(QBrush(base))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        rot_angle = (self.phase * 30) % 360
        conic = QConicalGradient(cx, cy, rot_angle)
        conic.setColorAt(0.0, QColor(0, 242, 254, 180))
        conic.setColorAt(0.5, QColor(236, 72, 153, 180))
        conic.setColorAt(1.0, QColor(0, 242, 254, 180))
        p.setBrush(QBrush(conic))
        p.drawEllipse(QRectF(cx - r * 0.95, cy - r * 0.95, r * 1.9, r * 1.9))

        self._draw_glass_specular(p, cx, cy, r)

    def _draw_glass_specular(self, p: QPainter, cx: float, cy: float, r: float):
        """Draws curvature depth and specular glass reflection cap."""
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Specular light reflection on top-left
        specular = QRadialGradient(cx - r * 0.32, cy - r * 0.35, r * 0.55)
        specular.setColorAt(0.0, QColor(255, 255, 255, 175))
        specular.setColorAt(0.35, QColor(255, 255, 255, 45))
        specular.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(specular))
        p.drawEllipse(QRectF(cx - r * 0.65, cy - r * 0.7, r * 0.85, r * 0.6))

        # Thin outer chromatic edge rim
        rim_pen = QPen(QColor(255, 255, 255, 90), 1.0)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r * 0.98, cy - r * 0.98, r * 1.96, r * 1.96))

    # --- Mouse & Interaction Events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # If mouse didn't drag more than 5px, treat as a click to talk
            if hasattr(self, '_press_pos'):
                dist = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
                if dist < 6:
                    self.request_toggle_listening.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.request_circle_search.emit()

    def contextMenuEvent(self, event):
        self.reveal()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181926;
                color: #CAD3F5;
                border: 1px solid #363A4F;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #363A4F;
                color: #FFFFFF;
            }
        """)

        search_act = menu.addAction("🔍 Circle to Search (Ctrl+Shift+S)")
        search_act.triggered.connect(lambda: self.request_circle_search.emit())

        screen_share_text = "⏹️ Stop Screen Share" if self.screen_sharing else "🖥️ Screen Share with Gemini Live"
        share_act = menu.addAction(screen_share_text)
        share_act.triggered.connect(lambda: self.request_screen_share_toggle.emit())

        prompt_act = menu.addAction("💬 Ask Titanium (Hinglish)")
        prompt_act.triggered.connect(self._prompt_dialog)

        menu.addSeparator()

        install_act = menu.addAction("📥 Install to System (Start Menu & Startup)")
        install_act.triggered.connect(lambda: self.request_install.emit())

        reset_pos_act = menu.addAction("📍 Reset to Bottom-Left")
        reset_pos_act.triggered.connect(self._dock_to_bottom_left)

        menu.addSeparator()

        exit_act = menu.addAction("❌ Exit Titanium")
        exit_act.triggered.connect(QApplication.instance().quit)

        menu.exec(event.globalPos())

    def _prompt_dialog(self):
        self.reveal()
        text, ok = QInputDialog.getText(
            self,
            "Titanium Assistant",
            "Bataiye, kya madad chahiye? (English / Hinglish):",
            QLineEdit.EchoMode.Normal
        )
        if ok and text.strip():
            self.request_user_prompt.emit(text.strip())
