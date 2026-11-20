import math
import sys
from pathlib import Path
from typing import Optional, Callable

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QMenu, QApplication, QInputDialog, QLineEdit
)
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QRectF, Signal, QPointF
)
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient,
    QPen, QBrush, QCursor, QPainterPath, QImage
)

# Exact color palettes from AmazingUI's "Sphere for AI Assistant"
COLOR_ELECTRIC_BLUE = QColor(39, 28, 213)    # #271CD5
COLOR_MIDNIGHT_BLUE = QColor(20, 7, 92)     # #14075C
COLOR_DEEP_COSMIC   = QColor(31, 11, 87)    # #1F0B57
COLOR_ROYAL_VIOLET  = QColor(68, 13, 168)   # #440DA8
COLOR_BRIGHT_VIOLET = QColor(190, 27, 208)  # #BE1BD0
COLOR_NEON_MAGENTA  = QColor(203, 27, 193)  # #CB1BC1
COLOR_ACTIVE_CORAL  = QColor(218, 38, 68)   # #DA2644
COLOR_VIVID_RED     = QColor(233, 46, 38)   # #E92E26
COLOR_CYAN_SKY      = QColor(67, 167, 223)  # #43A7DF
COLOR_SOFT_ORCHID   = QColor(152, 95, 143)  # #985F8F
COLOR_MUTED_PLUM    = QColor(75, 40, 82)    # #4B2852

class SiriOrbWidget(QWidget):
    """Sphere for AI Assistant by AmazingUI (Dribbble shot 26280534).
    
    Features:
    - Procedural 3D living-energy sphere with translucent glass depth
    - Iconic AmazingUI Deep Velvet, Electric Blue & Cosmic Magenta palettes
    - Multi-layer luminous plasma fluid bodies in smooth orbital motion
    - Specular liquid curvature highlights and soft chromatic rim
    - Permanently docked at Top-Right with decreased margins (16px)
    - Responds immediately to 'Hey Titanium' with active acoustic waves
    """

    request_circle_search = Signal()
    request_screen_share_toggle = Signal()
    request_user_prompt = Signal(str)
    request_install = Signal()
    request_toggle_listening = Signal()
    request_toggle_live_mode = Signal()

    def __init__(self, size: int = 96):
        super().__init__()
        self.orb_size = size
        self.live_conversation_active = False
        # Generous widget bounds for outer glow and acoustic waves
        self.setFixedSize(size + 54, size + 54)

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

        # Load authentic AmazingUI 3D Sphere video frames (60 FPS)
        self.video_frames = []
        self.frame_idx = 0
        npz_path = Path(__file__).resolve().parent.parent / "assets" / "sphere_frames_160.npz"
        if npz_path.exists():
            try:
                arr = np.load(str(npz_path))['frames']
                for frame_data in arr:
                    qimg = QImage(frame_data.data, 160, 160, 160 * 4, QImage.Format.Format_RGBA8888)
                    self.video_frames.append(qimg.copy())
            except Exception as e:
                print(f"[Orb] Error loading video frames: {e}")

        # Static fallback texture
        asset_path = Path(__file__).resolve().parent.parent / "assets" / "amazingui_sphere.png"
        self.sphere_img = QImage(str(asset_path)) if asset_path.exists() else None

        # Physics & Animation Variables
        self.phase = 0.0
        self.pulse_scale = 1.0
        self.glow_intensity = 0.75
        self.drag_position = QPoint()

        # Permanent visibility
        self.setWindowOpacity(1.0)

        # 60 FPS animation loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)

        # Dock at top-right corner with decreased margins
        self._dock_to_top_right()

    def _dock_to_top_right(self):
        """Positions the sphere at the top-right corner with 16px margins."""
        screen = QApplication.primaryScreen().availableGeometry()
        margin_x = 16
        margin_y = 16
        x = screen.right() - self.width() - margin_x
        y = screen.top() + margin_y
        self.move(x, y)

    def reveal(self):
        self.setWindowOpacity(1.0)
        self._dock_to_top_right()
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

    def set_live_mode(self, active: bool):
        """Enables or disables continuous live conversation indicator."""
        self.live_conversation_active = active
        self.update()

    def _update_animation(self):
        """Calculates dynamic living-energy oscillations for AmazingUI Sphere and advances video."""
        self.phase += 0.042
        if self.phase > 1000:
            self.phase = 0.0

        # Advance 60 FPS video frame
        if self.video_frames:
            step = 2 if self.state == "thinking" else 1
            self.frame_idx = (self.frame_idx + step) % len(self.video_frames)

        if self.state == "idle":
            # Tranquil living breath
            self.pulse_scale = 1.0 + 0.025 * math.sin(self.phase * 1.5)
            self.glow_intensity = 0.70
        elif self.state == "listening":
            # Responsive acoustic energy
            self.pulse_scale = 1.0 + 0.08 * math.sin(self.phase * 4.2)
            self.glow_intensity = 0.95
        elif self.state == "thinking":
            # Cosmic Thinking Mode vortex breathing
            self.pulse_scale = 1.0 + 0.05 * math.cos(self.phase * 3.0)
            self.glow_intensity = 0.92
        elif self.state == "speaking":
            # Voice-amplitude bounce
            self.pulse_scale = 1.0 + 0.12 * abs(math.sin(self.phase * 5.5))
            self.glow_intensity = 0.98
        elif self.state == "seeing":
            # Precise scanner pulse
            self.pulse_scale = 1.0 + 0.035 * math.sin(self.phase * 2.2)
            self.glow_intensity = 0.88

        self.update()

    def _generate_organic_perimeter(self, cx: float, cy: float, base_r: float, amp: float, num_pts: int = 48) -> QPainterPath:
        """Constructs an organic living perimeter with smooth subtle harmonic surface waves."""
        path = QPainterPath()
        points = []

        for i in range(num_pts):
            theta = (2.0 * math.pi * i) / num_pts
            # Subtle living micro-fluctuations (keeps spherical volume intact like AmazingUI)
            w1 = math.sin(2.0 * theta + self.phase * 2.5) * amp
            w2 = math.cos(3.0 * theta - self.phase * 1.8) * (amp * 0.5)
            r_eff = base_r + w1 + w2

            px = cx + r_eff * math.cos(theta)
            py = cy + r_eff * math.sin(theta)
            points.append(QPointF(px, py))

        path.moveTo(points[0])
        for i in range(num_pts):
            p0 = points[(i - 1) % num_pts]
            p1 = points[i]
            p2 = points[(i + 1) % num_pts]
            p3 = points[(i + 2) % num_pts]

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
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        base_r = (self.orb_size / 2.0) * self.pulse_scale

        if self.state == "seeing":
            self._paint_seeing_sphere(painter, cx, cy, base_r)
        elif self.state == "listening":
            self._paint_listening_sphere(painter, cx, cy, base_r)
        elif self.state == "thinking":
            self._paint_thinking_sphere(painter, cx, cy, base_r)
        elif self.state == "speaking":
            self._paint_speaking_sphere(painter, cx, cy, base_r)
        else: # idle
            self._paint_idle_sphere(painter, cx, cy, base_r)

    def _draw_amazingui_texture(self, p: QPainter, cx: float, cy: float, r: float) -> bool:
        """Paints the current frame of the authentic AmazingUI Sphere video."""
        if self.video_frames:
            current_img = self.video_frames[self.frame_idx]
            target_rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)
            p.drawImage(target_rect, current_img)
            return True
        elif hasattr(self, 'sphere_img') and self.sphere_img is not None and not self.sphere_img.isNull():
            target_rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)
            p.drawImage(target_rect, self.sphere_img)
            return True
        return False

    # =========================================================================
    # 1. LISTENING MODE (Clean AmazingUI Sphere with subtle ambient breath - NO blue rings)
    # =========================================================================
    def _paint_listening_sphere(self, p: QPainter, cx: float, cy: float, r: float):
        # 1. Soft Outer Atmospheric Velvet Bloom (no concentric rings)
        grad_outer = QRadialGradient(cx, cy, r * 1.3)
        grad_outer.setColorAt(0.0, QColor(39, 28, 213, 110))   # Electric Blue
        grad_outer.setColorAt(0.6, QColor(67, 167, 223, 40))   # Soft Cyan
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.3, cy - r * 1.3, r * 2.6, r * 2.6))

        # 2. Base AmazingUI 3D Sphere Video Frame
        if not self._draw_amazingui_texture(p, cx, cy, r):
            orb_path = self._generate_organic_perimeter(cx, cy, r, r * 0.04)
            p.save()
            p.setClipPath(orb_path)
            base = QRadialGradient(cx, cy, r)
            base.setColorAt(0.0, QColor(20, 7, 92, 245))
            base.setColorAt(0.7, QColor(10, 4, 45, 250))
            base.setColorAt(1.0, QColor(3, 1, 15, 255))
            p.setBrush(QBrush(base))
            p.drawRect(self.rect())
            p.restore()

        self._draw_amazingui_specular(p, cx, cy, r)

    # =========================================================================
    # 2. THINKING MODE (AmazingUI Cosmic Agentic OS - Coral, Magenta & Purple)
    # =========================================================================
    def _paint_thinking_sphere(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.45)
        grad_outer.setColorAt(0.0, QColor(203, 27, 193, 175)) # Neon Magenta
        grad_outer.setColorAt(0.5, QColor(68, 13, 168, 95))   # Royal Violet
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.45, cy - r * 1.45, r * 2.9, r * 2.9))

        # Base AmazingUI 3D Sphere
        if not self._draw_amazingui_texture(p, cx, cy, r):
            orb_path = self._generate_organic_perimeter(cx, cy, r, r * 0.035)
            p.save()
            p.setClipPath(orb_path)
            base = QRadialGradient(cx, cy, r)
            base.setColorAt(0.0, QColor(31, 11, 87, 245))
            base.setColorAt(0.7, QColor(18, 5, 52, 250))
            base.setColorAt(1.0, QColor(5, 2, 16, 255))
            p.setBrush(QBrush(base))
            p.drawRect(self.rect())
            p.restore()

        # AmazingUI Cosmic Vortex Swirl & Glowing Core Knot
        p.save()
        clip_path = QPainterPath()
        clip_path.addEllipse(QRectF(cx - r, cy - r, r * 2.0, r * 2.0))
        p.setClipPath(clip_path)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        rot_angle = (self.phase * 75) % 360
        conic = QConicalGradient(cx, cy, rot_angle)
        conic.setColorAt(0.0, QColor(218, 38, 68, 170))   # Active Coral Red
        conic.setColorAt(0.33, QColor(203, 27, 193, 170)) # Neon Magenta
        conic.setColorAt(0.66, QColor(68, 13, 168, 150))  # Royal Violet
        conic.setColorAt(1.0, QColor(218, 38, 68, 170))
        p.setBrush(QBrush(conic))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r * 0.85, cy - r * 0.85, r * 1.7, r * 1.7))

        # Radiant Center Core Knot
        core = QRadialGradient(cx, cy, r * 0.45)
        core.setColorAt(0.0, QColor(255, 255, 255, 230))
        core.setColorAt(0.45, QColor(203, 27, 193, 150))
        core.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(core))
        p.drawEllipse(QRectF(cx - r * 0.45, cy - r * 0.45, r * 0.9, r * 0.9))
        p.restore()

        self._draw_amazingui_specular(p, cx, cy, r)

    # =========================================================================
    # 3. SPEAKING MODE (Active Crimson, Coral & Amber Warm Bounce)
    # =========================================================================
    def _paint_speaking_sphere(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.5)
        grad_outer.setColorAt(0.0, QColor(233, 46, 38, 180))  # Vivid Red
        grad_outer.setColorAt(0.5, QColor(245, 158, 11, 100)) # Golden Amber
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.5, cy - r * 1.5, r * 3.0, r * 3.0))

        # Base AmazingUI 3D Sphere
        if not self._draw_amazingui_texture(p, cx, cy, r):
            orb_path = self._generate_organic_perimeter(cx, cy, r, r * 0.05)
            p.save()
            p.setClipPath(orb_path)
            base = QRadialGradient(cx, cy, r)
            base.setColorAt(0.0, QColor(218, 38, 68, 245))
            base.setColorAt(1.0, QColor(15, 5, 8, 255))
            p.setBrush(QBrush(base))
            p.drawRect(self.rect())
            p.restore()

        # Warm voice-resonance core
        p.save()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        heat_phase = self.phase * 4.2
        hx = cx + math.cos(heat_phase) * (r * 0.22)
        hy = cy + math.sin(heat_phase) * (r * 0.22)
        heat = QRadialGradient(hx, hy, r * 0.75)
        heat.setColorAt(0.0, QColor(251, 191, 36, 210))  # Amber
        heat.setColorAt(0.5, QColor(233, 46, 38, 150))   # Vivid Red
        heat.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(heat))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(hx - r * 0.5, hy - r * 0.5, r, r))
        p.restore()

        self._draw_amazingui_specular(p, cx, cy, r)

    # =========================================================================
    # 4. SEEING MODE (Cyber Emerald & Matrix Vision Scanner)
    # =========================================================================
    def _paint_seeing_sphere(self, p: QPainter, cx: float, cy: float, r: float):
        grad_outer = QRadialGradient(cx, cy, r * 1.4)
        grad_outer.setColorAt(0.0, QColor(16, 185, 129, 180)) # Emerald
        grad_outer.setColorAt(0.6, QColor(67, 167, 223, 90))  # Cyan Sky
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.4, cy - r * 1.4, r * 2.8, r * 2.8))

        # Base AmazingUI 3D Sphere
        if not self._draw_amazingui_texture(p, cx, cy, r):
            orb_path = self._generate_organic_perimeter(cx, cy, r, r * 0.025)
            p.save()
            p.setClipPath(orb_path)
            base = QRadialGradient(cx, cy, r)
            base.setColorAt(0.0, QColor(6, 78, 59, 240))
            base.setColorAt(1.0, QColor(3, 10, 8, 255))
            p.setBrush(QBrush(base))
            p.drawRect(self.rect())
            p.restore()

        p.save()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        radar_angle = (self.phase * 120) % 360
        conic = QConicalGradient(cx, cy, radar_angle)
        conic.setColorAt(0.0, QColor(52, 211, 153, 200))
        conic.setColorAt(0.2, QColor(67, 167, 223, 100))
        conic.setColorAt(0.4, QColor(0, 0, 0, 0))
        conic.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(conic))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r * 0.9, cy - r * 0.9, r * 1.8, r * 1.8))
        p.restore()

        # Targeting reticle
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

        self._draw_amazingui_specular(p, cx, cy, r)

    # =========================================================================
    # 5. IDLE MODE (AmazingUI Deep Velvet & Soft Orchid Living Harmony)
    # =========================================================================
    def _paint_idle_sphere(self, p: QPainter, cx: float, cy: float, r: float):
        # Velvet & Indigo Ambient Corona
        grad_outer = QRadialGradient(cx, cy, r * 1.35)
        grad_outer.setColorAt(0.0, QColor(39, 28, 213, 110))  # Electric Blue bloom
        grad_outer.setColorAt(0.6, QColor(190, 27, 208, 45))   # Bright Violet
        grad_outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad_outer))
        p.drawEllipse(QRectF(cx - r * 1.35, cy - r * 1.35, r * 2.7, r * 2.7))

        # Base AmazingUI 3D Sphere
        if not self._draw_amazingui_texture(p, cx, cy, r):
            orb_path = self._generate_organic_perimeter(cx, cy, r, r * 0.02)
            p.save()
            p.setClipPath(orb_path)
            base = QRadialGradient(cx, cy, r)
            base.setColorAt(0.0, QColor(19, 27, 91, 245))
            base.setColorAt(0.7, QColor(12, 16, 55, 250))
            base.setColorAt(1.0, QColor(4, 5, 18, 255))
            p.setBrush(QBrush(base))
            p.drawRect(self.rect())
            p.restore()

        self._draw_amazingui_specular(p, cx, cy, r)

    def _draw_amazingui_specular(self, p: QPainter, cx: float, cy: float, r: float):
        """Glossy 3D glass specular curvature highlight (Cinema 4D style)."""
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Primary glossy glass highlight on upper-left
        specular = QRadialGradient(cx - r * 0.35, cy - r * 0.38, r * 0.52)
        specular.setColorAt(0.0, QColor(255, 255, 255, 190))
        specular.setColorAt(0.35, QColor(255, 255, 255, 50))
        specular.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(specular))
        p.drawEllipse(QRectF(cx - r * 0.65, cy - r * 0.72, r * 0.82, r * 0.58))

        # Delicate bottom reflection bounce
        bounce = QRadialGradient(cx + r * 0.25, cy + r * 0.35, r * 0.45)
        bounce.setColorAt(0.0, QColor(255, 255, 255, 45))
        bounce.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(bounce))
        p.drawEllipse(QRectF(cx - r * 0.2, cy + r * 0.15, r * 0.9, r * 0.5))

        # Distinct LIVE Mode indicator pill on sphere
        if self.live_conversation_active:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            badge_w, badge_h = 36, 15
            badge_x = cx - badge_w / 2
            badge_y = cy + r - 10
            badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
            
            p.setPen(QColor(239, 68, 68, 200))
            p.setBrush(QColor(185, 28, 28, 220))
            p.drawRoundedRect(badge_rect, 7, 7)
            
            # Pulsating white dot
            dot_alpha = int(180 + 75 * math.sin(self.phase * 4.0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, dot_alpha))
            p.drawEllipse(QRectF(badge_x + 5, badge_y + 4.5, 5, 5))
            
            # Text "LIVE"
            p.setPen(QColor(255, 255, 255, 240))
            f = p.font()
            f.setFamily("Segoe UI")
            f.setPointSize(7)
            f.setBold(True)
            p.setFont(f)
            p.drawText(QRectF(badge_x + 12, badge_y - 0.5, 22, badge_h), Qt.AlignmentFlag.AlignCenter, "LIVE")

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
                background-color: #14075C;
                color: #CAD3F5;
                border: 1px solid #440DA8;
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
                background-color: #440DA8;
                color: #FFFFFF;
            }
        """)

        search_act = menu.addAction("🔍 Circle to Search (Ctrl+Shift+S)")
        search_act.triggered.connect(lambda: self.request_circle_search.emit())

        live_text = "⏹️ Stop Live Conversation" if self.live_conversation_active else "🎙️ Start Live Conversation (Continuous)"
        live_act = menu.addAction(live_text)
        live_act.triggered.connect(lambda: self.request_toggle_live_mode.emit())

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
