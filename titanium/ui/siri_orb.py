import math
import sys
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QMenu, QApplication, QInputDialog, QLineEdit
)
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QRectF, Signal, QPointF
)
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient,
    QPen, QBrush, QCursor, QPainterPath
)

class SiriOrbWidget(QWidget):
    """Siri AI Animated Fluid Sphere (Inspired by Rob on Dribbble).
    
    Features:
    - Organic 3D fluid blob with harmonic surface wave deformation
    - Multi-layer liquid glass iridescence (Cyan, Magenta, Violet, Sunset Coral)
    - Specular liquid curvature highlights and subsurface scattering glow
    - Docked at Top-Right with minimal margins
    - 4 distinct animated states:
        1. Listening: Reactive acoustic liquid shockwaves & electric cyan-violet plasma
        2. Thinking: Swirling dual-vortex cosmic nebula
        3. Speaking: Voice-amplitude liquid bounce with warm coral & amber flare
        4. Seeing: Cyber emerald vision scanner with optical targeting reticle
    """

    request_circle_search = Signal()
    request_screen_share_toggle = Signal()
    request_user_prompt = Signal(str)
    request_install = Signal()
    request_toggle_listening = Signal()

    def __init__(self, size: int = 94):
        super().__init__()
        self.orb_size = size
        # Generous widget bounds for fluid deformation waves & atmosphere bloom
        self.setFixedSize(size + 60, size + 60)

        # Frameless, transparent, always-on-top window
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

        # Physics & Harmonic Wave Variables
        self.phase = 0.0
        self.pulse_scale = 1.0
        self.glow_intensity = 0.75
        self.drag_position = QPoint()

        # Ensure permanent visibility at full opacity
        self.setWindowOpacity(1.0)

        # 60 FPS animation loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)

        # Dock at top-right corner with decreased margins
        self._dock_to_top_right()

    def _dock_to_top_right(self):
        """Positions the orb at the top-right corner of the screen with compact margins."""
        screen = QApplication.primaryScreen().availableGeometry()
        margin_x = 16  # Decreased margin
        margin_y = 16  # Decreased margin
        x = screen.right() - self.width() - margin_x
        y = screen.top() + margin_y
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
        """Calculates harmonic fluid dynamics and pulse physics."""
        self.phase += 0.045
        if self.phase > 1000:
            self.phase = 0.0

        if self.state == "idle":
            self.pulse_scale = 1.0 + 0.025 * math.sin(self.phase * 1.4)
            self.glow_intensity = 0.65
        elif self.state == "listening":
            self.pulse_scale = 1.0 + 0.08 * math.sin(self.phase * 4.0)
            self.glow_intensity = 0.95
        elif self.state == "thinking":
            self.pulse_scale = 1.0 + 0.045 * math.cos(self.phase * 2.8)
            self.glow_intensity = 0.88
        elif self.state == "speaking":
            self.pulse_scale = 1.0 + 0.12 * abs(math.sin(self.phase * 5.2))
            self.glow_intensity = 0.96
        elif self.state == "seeing":
            self.pulse_scale = 1.0 + 0.035 * math.sin(self.phase * 2.2)
            self.glow_intensity = 0.90

        self.update()

    def _generate_blob_path(self, cx: float, cy: float, base_r: float, wave_amp: float, num_pts: int = 56) -> QPainterPath:
        """Generates an organic morphing fluid spline path using harmonic surface wave functions."""
        path = QPainterPath()
        points = []

        for i in range(num_pts):
            theta = (2.0 * math.pi * i) / num_pts
            # Multi-frequency harmonic liquid surface displacement
            h1 = math.sin(2.0 * theta + self.phase * 2.8)
            h2 = math.cos(3.0 * theta - self.phase * 1.9) * 0.6
            h3 = math.sin(5.0 * theta + self.phase * 3.6) * 0.35

            r_eff = base_r + wave_amp * (h1 + h2 + h3)
            px = cx + r_eff * math.cos(theta)
            py = cy + r_eff * math.sin(theta)
            points.append(QPointF(px, py))

        # Construct smooth closed cubic bezier spline through points
        path.moveTo(points[0])
        for i in range(num_pts):
            p0 = points[(i - 1) % num_pts]
            p1 = points[i]
            p2 = points[(i + 1) % num_pts]
            p3 = points[(i + 2) % num_pts]

            # Catmull-Rom to Cubic Bezier control points
            c1x = p1.x() + (p2.x() - p0.x()) / 6.0
            c1y = p1.y() + (p2.y() - p0.y()) / 6.0
            c2x = p2.x() - (p3.x() - p1.x()) / 6.0
            c2y = p2.y() - (p3.y() - p1.y()) / 6.0

            path.cubicTo(c1x, c1y, c2x, c2y, p2.x(), p2.y())

        path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        base_r = (self.orb_size / 2.0) * self.pulse_scale

        if self.state == "seeing":
            self._paint_seeing_blob(painter, cx, cy, base_r)
        elif self.state == "listening":
            self._paint_listening_blob(painter, cx, cy, base_r)
        elif self.state == "thinking":
            self._paint_thinking_blob(painter, cx, cy, base_r)
        elif self.state == "speaking":
            self._paint_speaking_blob(painter, cx, cy, base_r)
        else:
            self._paint_idle_blob(painter, cx, cy, base_r)

    # =========================================================================
    # LOOK 1: LISTENING (Acoustic Shockwaves + Electric Cyan / Azure Fluid Blob)
    # =========================================================================
    def _paint_listening_blob(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Concentric Acoustic Waves Radiating Outward
        for i in range(3):
            wave_progress = ((self.phase * 1.8 + i * 0.33) % 1.0)
            wave_r = r * (1.08 + wave_progress * 0.44)
            wave_alpha = int(180 * (1.0 - wave_progress))
            pen = QPen(QColor(0, 245, 255, wave_alpha), 1.8)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - wave_r, cy - wave_r, wave_r * 2, wave_r * 2))

        # 2. Atmospheric Outer Glow
        grad_outer = QRadialGradient(cx, cy, r * 1.45)
        grad_outer.setColorAt(0.0, QColor(0, 242, 254, 180))
        grad_outer.setColorAt(0.5, QColor(147, 51, 234, 90))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.45, cy - r * 1.45, r * 2.9, r * 2.9))

        # 3. Organic Fluid Blob
        wave_amp = r * 0.09
        blob_path = self._generate_blob_path(cx, cy, r, wave_amp)

        p.save()
        p.setClipPath(blob_path)

        # Base Deep Iridescent Sphere
        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(79, 70, 229, 240))  # Indigo
        base.setColorAt(0.7, QColor(24, 24, 48, 250))
        base.setColorAt(1.0, QColor(10, 10, 22, 255))
        p.setBrush(QBrush(base))
        p.drawRect(self.rect())

        # Orbiting Electric Cyan Plasma Light
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        angle1 = self.phase * 3.5
        c1x = cx + math.cos(angle1) * (r * 0.4)
        c1y = cy + math.sin(angle1) * (r * 0.4)
        p1 = QRadialGradient(c1x, c1y, r * 0.8)
        p1.setColorAt(0.0, QColor(0, 245, 255, 255))
        p1.setColorAt(0.5, QColor(79, 172, 254, 170))
        p1.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(p1))
        p.drawRect(self.rect())

        # Orbiting Hot Magenta Plasma Light
        c2x = cx + math.cos(angle1 + math.pi) * (r * 0.4)
        c2y = cy + math.sin(angle1 + math.pi) * (r * 0.4)
        p2 = QRadialGradient(c2x, c2y, r * 0.8)
        p2.setColorAt(0.0, QColor(244, 63, 94, 240))
        p2.setColorAt(0.5, QColor(168, 85, 247, 150))
        p2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(p2))
        p.drawRect(self.rect())

        p.restore()

        # 4. Fluid Edge Fresnel Glow
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        rim_pen = QPen(QColor(0, 245, 255, 220), 2.0)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(blob_path)

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 2: THINKING (Swirling Cosmic Nebula & Spiral Dual-Vortex Fluid)
    # =========================================================================
    def _paint_thinking_blob(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.4)
        grad_outer.setColorAt(0.0, QColor(147, 51, 234, 160))
        grad_outer.setColorAt(0.6, QColor(236, 72, 153, 80))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.4, cy - r * 1.4, r * 2.8, r * 2.8))

        wave_amp = r * 0.075
        blob_path = self._generate_blob_path(cx, cy, r, wave_amp)

        p.save()
        p.setClipPath(blob_path)

        # Base Galaxy
        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(24, 16, 48, 250))
        base.setColorAt(0.8, QColor(15, 12, 30, 250))
        base.setColorAt(1.0, QColor(8, 6, 16, 255))
        p.setBrush(QBrush(base))
        p.drawRect(self.rect())

        # Rotating Vortex Plasma Ring
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        rot_angle = (self.phase * 80) % 360
        conic = QConicalGradient(cx, cy, rot_angle)
        conic.setColorAt(0.0, QColor(168, 85, 247, 240))
        conic.setColorAt(0.33, QColor(236, 72, 153, 240))
        conic.setColorAt(0.66, QColor(99, 102, 241, 240))
        conic.setColorAt(1.0, QColor(168, 85, 247, 240))
        p.setBrush(QBrush(conic))
        p.drawRect(self.rect())

        # Swirling Center Stardust Core
        core = QRadialGradient(cx, cy, r * 0.55)
        core.setColorAt(0.0, QColor(255, 255, 255, 230))
        core.setColorAt(0.4, QColor(192, 132, 252, 180))
        core.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(core))
        p.drawRect(self.rect())

        p.restore()

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        rim_pen = QPen(QColor(192, 132, 252, 200), 2.0)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(blob_path)

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 3: SPEAKING (Warm Sunset Coral, Amber & Dynamic Liquid Voice Bounce)
    # =========================================================================
    def _paint_speaking_blob(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.45)
        grad_outer.setColorAt(0.0, QColor(255, 75, 43, 180))
        grad_outer.setColorAt(0.5, QColor(245, 158, 11, 100))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.45, cy - r * 1.45, r * 2.9, r * 2.9))

        wave_amp = r * 0.11
        blob_path = self._generate_blob_path(cx, cy, r, wave_amp)

        p.save()
        p.setClipPath(blob_path)

        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(225, 29, 72, 240))
        base.setColorAt(0.7, QColor(136, 19, 55, 245))
        base.setColorAt(1.0, QColor(18, 12, 18, 255))
        p.setBrush(QBrush(base))
        p.drawRect(self.rect())

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        heat_phase = self.phase * 4.0
        hx = cx + math.cos(heat_phase) * (r * 0.28)
        hy = cy + math.sin(heat_phase) * (r * 0.28)
        heat = QRadialGradient(hx, hy, r * 0.85)
        heat.setColorAt(0.0, QColor(251, 191, 36, 255))  # Amber
        heat.setColorAt(0.5, QColor(244, 63, 94, 210))   # Hot Coral
        heat.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(heat))
        p.drawRect(self.rect())

        p.restore()

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        rim_pen = QPen(QColor(251, 191, 36, 220), 2.0)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(blob_path)

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 4: SEEING / VISION (Cyber Emerald, Matrix Mint & Radar Reticle)
    # =========================================================================
    def _paint_seeing_blob(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.4)
        grad_outer.setColorAt(0.0, QColor(16, 185, 129, 180))
        grad_outer.setColorAt(0.6, QColor(6, 182, 212, 90))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.4, cy - r * 1.4, r * 2.8, r * 2.8))

        wave_amp = r * 0.05
        blob_path = self._generate_blob_path(cx, cy, r, wave_amp)

        p.save()
        p.setClipPath(blob_path)

        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(6, 78, 59, 240))
        base.setColorAt(0.8, QColor(10, 25, 20, 250))
        base.setColorAt(1.0, QColor(4, 10, 8, 255))
        p.setBrush(QBrush(base))
        p.drawRect(self.rect())

        # Rotating Radar Scanner Beam
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        radar_angle = (self.phase * 120) % 360
        conic = QConicalGradient(cx, cy, radar_angle)
        conic.setColorAt(0.0, QColor(52, 211, 153, 240))
        conic.setColorAt(0.2, QColor(6, 182, 212, 140))
        conic.setColorAt(0.4, QColor(0, 0, 0, 0))
        conic.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(conic))
        p.drawRect(self.rect())

        # Concentric Targeting Aperture Ring
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        reticle_pen = QPen(QColor(52, 211, 153, 220), 1.6)
        p.setPen(reticle_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r * 0.65, cy - r * 0.65, r * 1.3, r * 1.3))

        tick = r * 0.15
        p.drawLine(cx, cy - r * 0.7, cx, cy - r * 0.7 + tick)
        p.drawLine(cx, cy + r * 0.7 - tick, cx, cy + r * 0.7)
        p.drawLine(cx - r * 0.7, cy, cx - r * 0.7 + tick, cy)
        p.drawLine(cx + r * 0.7 - tick, cy, cx + r * 0.7, cy)

        pupil = QRadialGradient(cx, cy, r * 0.28)
        pupil.setColorAt(0.0, QColor(255, 255, 255, 240))
        pupil.setColorAt(0.5, QColor(52, 211, 153, 190))
        pupil.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(pupil))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r * 0.28, cy - r * 0.28, r * 0.56, r * 0.56))

        p.restore()

        rim_pen = QPen(QColor(52, 211, 153, 220), 2.0)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(blob_path)

        self._draw_glass_specular(p, cx, cy, r)

    # =========================================================================
    # LOOK 5: IDLE (Tranquil Iridescent Liquid Droplet)
    # =========================================================================
    def _paint_idle_blob(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.35)
        grad_outer.setColorAt(0.0, QColor(99, 102, 241, 130))
        grad_outer.setColorAt(0.6, QColor(236, 72, 153, 60))
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.35, cy - r * 1.35, r * 2.7, r * 2.7))

        wave_amp = r * 0.045
        blob_path = self._generate_blob_path(cx, cy, r, wave_amp)

        p.save()
        p.setClipPath(blob_path)

        base = QRadialGradient(cx, cy, r)
        base.setColorAt(0.0, QColor(79, 70, 229, 230))
        base.setColorAt(0.7, QColor(24, 20, 50, 240))
        base.setColorAt(1.0, QColor(12, 10, 24, 255))
        p.setBrush(QBrush(base))
        p.drawRect(self.rect())

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        rot_angle = (self.phase * 35) % 360
        conic = QConicalGradient(cx, cy, rot_angle)
        conic.setColorAt(0.0, QColor(0, 242, 254, 190))
        conic.setColorAt(0.5, QColor(236, 72, 153, 190))
        conic.setColorAt(1.0, QColor(0, 242, 254, 190))
        p.setBrush(QBrush(conic))
        p.drawRect(self.rect())

        p.restore()

        rim_pen = QPen(QColor(168, 85, 247, 180), 1.8)
        p.setPen(rim_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(blob_path)

        self._draw_glass_specular(p, cx, cy, r)

    def _draw_glass_specular(self, p: QPainter, cx: float, cy: float, r: float):
        """Draws curvature depth and specular glass reflection cap."""
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        specular = QRadialGradient(cx - r * 0.32, cy - r * 0.35, r * 0.55)
        specular.setColorAt(0.0, QColor(255, 255, 255, 180))
        specular.setColorAt(0.35, QColor(255, 255, 255, 45))
        specular.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(specular))
        p.drawEllipse(QRectF(cx - r * 0.65, cy - r * 0.7, r * 0.85, r * 0.6))

    # --- Mouse & Interaction Events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

        reset_pos_act = menu.addAction("📍 Reset to Top-Right")
        reset_pos_act.triggered.connect(self._dock_to_top_right)

        menu.addSeparator()

        exit_act = menu.addAction("❌ Exit Titanium")
        exit_act.triggered.connect(QApplication.instance().quit)

        menu.exec(event.globalPos())

    def _prompt_dialog(self):
        text, ok = QInputDialog.getText(
            self,
            "Titanium Assistant",
            "Bataiye, kya madad chahiye? (English / Hinglish):",
            QLineEdit.EchoMode.Normal
        )
        if ok and text.strip():
            self.request_user_prompt.emit(text.strip())
