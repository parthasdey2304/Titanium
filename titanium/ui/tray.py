import os
import sys
import winreg
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "TitaniumAssistant"

class TitaniumTrayIcon(QSystemTrayIcon):
    """Windows system tray icon with startup configuration and quick toggles."""

    def __init__(
        self,
        on_toggle_orb: Callable[[], None],
        on_circle_search: Callable[[], None],
        on_install: Optional[Callable[[], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.on_toggle_orb = on_toggle_orb
        self.on_circle_search = on_circle_search
        self.on_install = on_install

        self.setIcon(self._create_tray_pixmap())
        self.setToolTip("Titanium AI Assistant (Windows)")
        self._init_menu()
        self.activated.connect(self._on_activated)

    def _create_tray_pixmap(self) -> QIcon:
        """Loads the high-resolution AmazingUI Sphere icon for the tray."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        icon_path = root_dir / "titanium.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QRadialGradient(16, 16, 14)
        grad.setColorAt(0.0, QColor(0, 242, 254))
        grad.setColorAt(0.5, QColor(147, 51, 234))
        grad.setColorAt(1.0, QColor(244, 63, 94))

        painter.setPen(QColor(255, 255, 255, 200))
        painter.setBrush(grad)
        painter.drawEllipse(3, 3, 26, 26)
        painter.end()
        return QIcon(pixmap)

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #181926;
                color: #CAD3F5;
                border: 1px solid #363A4F;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item:selected {
                background-color: #363A4F;
            }
        """)

        toggle_act = menu.addAction("✨ Toggle Siri Orb")
        toggle_act.triggered.connect(self.on_toggle_orb)

        search_act = menu.addAction("🔍 Circle to Search")
        search_act.triggered.connect(self.on_circle_search)

        menu.addSeparator()

        if self.on_install:
            install_act = menu.addAction("📥 Install to Start Menu & Startup")
            install_act.triggered.connect(self.on_install)

        self.startup_act = menu.addAction("🚀 Launch on Windows Startup")
        self.startup_act.setCheckable(True)
        self.startup_act.setChecked(self.is_startup_enabled())
        self.startup_act.triggered.connect(self._toggle_startup)

        menu.addSeparator()

        exit_act = menu.addAction("❌ Quit Titanium")
        exit_act.triggered.connect(QApplication.instance().quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_toggle_orb()

    def is_startup_enabled(self) -> bool:
        """Checks if Titanium is set to launch on Windows boot."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
        except Exception:
            return False

    def _toggle_startup(self, checked: bool):
        """Adds or removes Titanium from Windows Startup registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if checked:
                    # Point to current python executable and main script
                    main_script = Path(__file__).resolve().parent.parent.parent / "main.py"
                    python_exe = sys.executable
                    cmd = f'"{python_exe}" "{main_script}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"[Tray] Error setting startup registry: {e}")
