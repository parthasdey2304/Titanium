import sys
import os
import shutil
import tempfile
import subprocess
import winreg
from pathlib import Path
from typing import Optional
import requests

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QProgressBar, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont, QPixmap, QDesktopServices, QImage, QPainter, QColor, QPen, QPainterPath
from PySide6.QtCore import QUrl

APP_NAME = "Titanium"
DESCRIPTION = "Titanium AI Virtual Assistant for Windows"


def get_checkmark_icon_path() -> str:
    """Generates a high-contrast anti-aliased black checkmark tick icon and returns its URI."""
    temp_icon = Path(tempfile.gettempdir()) / "titanium_checkmark.png"
    try:
        img = QImage(32, 32, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(10, 15, 30), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(7, 16)
        path.lineTo(13, 22)
        path.lineTo(25, 9)
        p.drawPath(path)
        p.end()
        img.save(str(temp_icon))
    except Exception as e:
        print(f"Error generating checkmark: {e}")
    return str(temp_icon).replace("\\", "/")


class InstallWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(
        self,
        target_dir: Path,
        api_key: str,
        elevenlabs_key: str,
        elevenlabs_voice: str,
        elevenlabs_model: str,
        create_desktop: bool,
        create_start: bool,
        autostart: bool
    ):
        super().__init__()
        self.target_dir = target_dir
        self.api_key = api_key.strip()
        self.elevenlabs_key = elevenlabs_key.strip()
        self.elevenlabs_voice = elevenlabs_voice.strip() or "Charlie"
        self.elevenlabs_model = elevenlabs_model.strip() or "eleven_flash_v2_5"
        self.create_desktop = create_desktop
        self.create_start = create_start
        self.autostart = autostart

    def run(self):
        try:
            self.progress.emit(10, "Closing active Titanium instances...")
            subprocess.run(["taskkill", "/F", "/IM", "Titanium.exe"], capture_output=True, timeout=5)

            self.progress.emit(15, "Verifying Google Gemini API Key...")
            if not self._verify_key(self.api_key):
                self.finished.emit(False, "API key verification failed. Please check your key at aistudio.google.com and retry.")
                return

            self.progress.emit(35, "Creating installation directory...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # Locate source files (from PyInstaller bundle or local project)
            if getattr(sys, 'frozen', False):
                base_source = Path(sys._MEIPASS)
            else:
                base_source = Path(__file__).resolve().parent

            source_exe = base_source / "Titanium.exe"
            if not source_exe.exists():
                source_exe = base_source / "dist" / "Titanium.exe"
            if not source_exe.exists():
                source_exe = Path(__file__).resolve().parent / "Titanium.exe"

            source_ico = base_source / "titanium.ico"
            if not source_ico.exists():
                source_ico = Path(__file__).resolve().parent / "titanium.ico"

            dest_exe = self.target_dir / "Titanium.exe"
            dest_ico = self.target_dir / "titanium.ico"

            self.progress.emit(55, "Deploying Titanium executable and assets...")
            if source_exe.exists() and source_exe.resolve() != dest_exe.resolve():
                shutil.copy2(source_exe, dest_exe)

            if source_ico.exists() and source_ico.resolve() != dest_ico.resolve():
                shutil.copy2(source_ico, dest_ico)

            self.progress.emit(70, "Writing configuration and environment settings...")
            env_file = self.target_dir / ".env"
            env_content = (
                f"# Titanium Configuration\n"
                f"GEMINI_API_KEY={self.api_key}\n"
                f"ELEVENLABS_API_KEY={self.elevenlabs_key}\n"
                f"ELEVENLABS_VOICE_NAME={self.elevenlabs_voice}\n"
                f"ELEVENLABS_MODEL_ID={self.elevenlabs_model}\n"
                f"ASSISTANT_NAME=Titanium\n"
                f"LANGUAGE_MODE=hinglish\n"
            )
            env_file.write_text(env_content, encoding="utf-8")

            # Write uninstaller script in target directory
            uninstaller_script = self.target_dir / "uninstall.bat"
            uninstaller_content = (
                "@echo off\n"
                "title Titanium - Uninstall\n"
                "echo Uninstalling Titanium shortcuts and registry settings...\n"
                f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{APP_NAME}" /f >nul 2>&1\n'
                f'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\{APP_NAME}.lnk" >nul 2>&1\n'
                f'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{APP_NAME}.lnk" >nul 2>&1\n'
                f'del "%USERPROFILE%\\Desktop\\{APP_NAME}.lnk" >nul 2>&1\n'
                "echo Titanium system integrations removed.\n"
                "pause\n"
            )
            uninstaller_script.write_text(uninstaller_content, encoding="utf-8")

            self.progress.emit(85, "Creating Windows shortcuts...")
            appdata = Path(os.environ.get("APPDATA", ""))
            userprofile = Path(os.environ.get("USERPROFILE", ""))

            # Start Menu shortcut
            if self.create_start:
                start_lnk = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"
                self._create_shortcut(dest_exe, dest_ico, start_lnk, self.target_dir)

            # Desktop shortcut
            if self.create_desktop:
                desktop_lnk = userprofile / "Desktop" / f"{APP_NAME}.lnk"
                self._create_shortcut(dest_exe, dest_ico, desktop_lnk, self.target_dir)

            # Startup shortcut / Registry
            if self.autostart:
                self._register_startup(dest_exe)

            # Refresh Windows icon cache
            try:
                subprocess.run(["ie4uinit.exe", "-show"], capture_output=True, timeout=3)
            except Exception:
                pass

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, "Installation succeeded.")
        except Exception as e:
            self.finished.emit(False, f"Installation error: {str(e)}")

    def _verify_key(self, key: str) -> bool:
        if not key:
            return False
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            resp = requests.get(url, timeout=7)
            return resp.status_code == 200
        except Exception:
            return False

    def _create_shortcut(self, target_exe: Path, icon_path: Path, lnk_path: Path, work_dir: Path):
        lnk_path.parent.mkdir(parents=True, exist_ok=True)
        ps_cmd = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{str(lnk_path)}')
$Shortcut.TargetPath = '{str(target_exe)}'
$Shortcut.WorkingDirectory = '{str(work_dir)}'
$Shortcut.IconLocation = '{str(icon_path)},0'
$Shortcut.Description = '{DESCRIPTION}'
$Shortcut.WindowStyle = 1
$Shortcut.Save()
"""
        try:
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=5)
        except Exception as e:
            print(f"Error creating shortcut {lnk_path}: {e}")

    def _register_startup(self, target_exe: Path):
        try:
            reg_key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(reg_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{str(target_exe)}"')
        except Exception as e:
            print(f"Error registering startup: {e}")


class UninstallWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, target_dir: Optional[Path]):
        super().__init__()
        self.target_dir = target_dir

    def run(self):
        try:
            self.progress.emit(20, "Stopping active Titanium processes...")
            subprocess.run(["taskkill", "/F", "/IM", "Titanium.exe"], capture_output=True, timeout=5)

            self.progress.emit(45, "Removing Windows Startup registry entries...")
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                    for name in [APP_NAME, "TitaniumAssistant"]:
                        try:
                            winreg.DeleteValue(key, name)
                        except Exception:
                            pass
            except Exception:
                pass

            self.progress.emit(65, "Deleting Windows shortcuts...")
            appdata = Path(os.environ.get("APPDATA", ""))
            userprofile = Path(os.environ.get("USERPROFILE", ""))
            
            for lnk in [
                appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk",
                appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.lnk",
                userprofile / "Desktop" / f"{APP_NAME}.lnk"
            ]:
                if lnk.exists():
                    try:
                        lnk.unlink()
                    except Exception:
                        pass

            self.progress.emit(85, "Removing application files...")
            if self.target_dir and self.target_dir.exists():
                is_source_repo = (self.target_dir / "main.py").exists() and (self.target_dir / "titanium").exists()
                if not is_source_repo:
                    try:
                        shutil.rmtree(self.target_dir, ignore_errors=True)
                    except Exception as e:
                        print(f"Error deleting target_dir: {e}")
                else:
                    for f in [self.target_dir / "uninstall.bat"]:
                        if f.exists():
                            f.unlink()

            try:
                subprocess.run(["ie4uinit.exe", "-show"], capture_output=True, timeout=3)
            except Exception:
                pass

            self.progress.emit(100, "Uninstallation complete!")
            self.finished.emit(True, "Titanium has been uninstalled successfully.")
        except Exception as e:
            self.finished.emit(False, f"Uninstallation error: {str(e)}")


class TitaniumInstallerWindow(QMainWindow):
    """Modern Dark Gemini Setup Wizard for Titanium Virtual Assistant."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Titanium Virtual Assistant - Setup")

        # Set App Icon
        icon_path = Path(__file__).resolve().parent / "titanium.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.existing_dir = self._detect_existing_installation()
        self.detected_keys = self._detect_local_keys()
        self.setFixedSize(580, 800 if self.existing_dir else 720)
        self._apply_dark_style()
        self._init_ui()

    def _apply_dark_style(self):
        check_path = get_checkmark_icon_path()
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #131314;
            }}
            QWidget {{
                color: #E3E3E3;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QFrame#card {{
                background-color: #1E1F20;
                border: 1px solid #28292A;
                border-radius: 12px;
                padding: 18px;
            }}
            QFrame#alertCard {{
                background-color: rgba(56, 189, 248, 0.08);
                border: 1px solid rgba(56, 189, 248, 0.28);
                border-radius: 8px;
            }}
            QLabel#headerTitle {{
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
            }}
            QLabel#headerSubtitle {{
                font-size: 13px;
                color: #9AA0A6;
            }}
            QLabel#sectionLabel {{
                font-size: 13px;
                font-weight: 600;
                color: #D2E3FC;
            }}
            QLineEdit {{
                background-color: #131314;
                color: #FFFFFF;
                border: 1.5px solid #3C4043;
                border-radius: 8px;
                padding: 0px 14px;
                min-height: 44px;
                height: 44px;
                font-size: 13px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QLineEdit:focus {{
                border: 1.5px solid #8AB4F8;
                background-color: #18191A;
            }}
            QPushButton#actionBtn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1A73E8, stop:1 #8AB4F8);
                color: #000000;
                font-weight: 700;
                font-size: 13px;
                border-radius: 8px;
                padding: 0px 24px;
                min-height: 44px;
                height: 44px;
                border: none;
            }}
            QPushButton#actionBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E88E5, stop:1 #A8C7FA);
            }}
            QPushButton#actionBtn:disabled {{
                background-color: #3C4043;
                color: #80868B;
            }}
            QPushButton#secondaryBtn {{
                background-color: #28292A;
                color: #E3E3E3;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
                padding: 0px 20px;
                min-height: 44px;
                height: 44px;
                border: 1px solid #3C4043;
            }}
            QPushButton#secondaryBtn:hover {{
                background-color: #35373A;
                border-color: #5F6368;
            }}
            QPushButton#dangerBtn {{
                background-color: rgba(239, 68, 68, 0.15);
                color: #F87171;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
                padding: 0px 18px;
                min-height: 44px;
                height: 44px;
                border: 1px solid rgba(239, 68, 68, 0.4);
            }}
            QPushButton#dangerBtn:hover {{
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #DC2626;
            }}
            QCheckBox {{
                font-size: 13px;
                color: #E3E3E3;
                spacing: 12px;
                min-height: 32px;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 1.5px solid #5F6368;
                background-color: #131314;
            }}
            QCheckBox::indicator:hover {{
                border-color: #8AB4F8;
                background-color: #1E1F20;
            }}
            QCheckBox::indicator:checked {{
                background-color: #8AB4F8;
                border-color: #8AB4F8;
                image: url("{check_path}");
            }}
            QProgressBar {{
                background-color: #1E1F20;
                border: 1px solid #3C4043;
                border-radius: 6px;
                text-align: center;
                color: #FFFFFF;
                font-size: 12px;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1A73E8, stop:1 #8AB4F8);
                border-radius: 5px;
            }}
        """)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # Header with Logo & Title
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        title_lbl = QLabel("Titanium Virtual Assistant")
        title_lbl.setObjectName("headerTitle")
        sub_lbl = QLabel("Native Windows AI Assistant Setup Wizard")
        sub_lbl.setObjectName("headerSubtitle")
        header_text_layout.addWidget(title_lbl)
        header_text_layout.addWidget(sub_lbl)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        icon_lbl = QLabel("🌌")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)
        main_layout.addLayout(header_layout)

        # Stacked Pages (Page 0: Form, Page 1: Install Success, Page 2: Uninstall Success)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # ---- PAGE 0: CONFIGURATION & INSTALL / UNINSTALL ----
        page0 = QWidget()
        p0_layout = QVBoxLayout(page0)
        p0_layout.setContentsMargins(0, 0, 0, 0)
        p0_layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        # Existing Installation Banner
        if self.existing_dir:
            alert = QFrame()
            alert.setObjectName("alertCard")
            alert.setMinimumHeight(60)
            alert_layout = QHBoxLayout(alert)
            alert_layout.setContentsMargins(14, 10, 14, 10)
            alert_lbl = QLabel(f"ℹ️  Existing installation detected at:\n{str(self.existing_dir)}")
            alert_lbl.setWordWrap(True)
            alert_lbl.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 500; line-height: 18px;")
            alert_layout.addWidget(alert_lbl)
            card_layout.addWidget(alert)

        # 1. Install Directory
        card_layout.addWidget(QLabel("1. Where would you like to install Titanium?", objectName="sectionLabel"))
        dir_box = QHBoxLayout()
        default_dir = self.existing_dir or (Path(os.environ.get("LOCALAPPDATA", "C:\\")) / "Programs" / "Titanium")
        self.dir_input = QLineEdit(str(default_dir))
        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._browse_directory)
        dir_box.addWidget(self.dir_input)
        dir_box.addWidget(browse_btn)
        card_layout.addLayout(dir_box)

        # 2. Gemini API Key
        card_layout.addWidget(QLabel("2. Google Gemini API Key:", objectName="sectionLabel"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste Gemini API Key (AIzaSy...)")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.key_input)

        if self.detected_keys.get("gemini"):
            self.key_input.setText(self.detected_keys["gemini"])
            status_hint = QLabel("✓ Auto-detected existing Gemini API key on this machine.")
            status_hint.setStyleSheet("color: #81C995; font-size: 12px; font-weight: 500;")
            card_layout.addWidget(status_hint)
        else:
            hint_box = QHBoxLayout()
            hint_lbl = QLabel("Required for AI voice and intelligence.")
            hint_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
            key_link = QLabel('<a style="color: #8AB4F8; text-decoration: none;" href="https://aistudio.google.com/app/apikey">Get free API key ↗</a>')
            key_link.setOpenExternalLinks(True)
            hint_box.addWidget(hint_lbl)
            hint_box.addStretch()
            hint_box.addWidget(key_link)
            card_layout.addLayout(hint_box)

        # 3. ElevenLabs Voice API Key (Optional)
        card_layout.addWidget(QLabel("3. ElevenLabs Voice API Key (Optional):", objectName="sectionLabel"))
        self.eleven_input = QLineEdit()
        self.eleven_input.setPlaceholderText("Paste ElevenLabs API Key (sk_... - for ultra-realistic Hinglish voice)")
        self.eleven_input.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.eleven_input)

        if self.detected_keys.get("elevenlabs"):
            self.eleven_input.setText(self.detected_keys["elevenlabs"])
            eleven_msg = "✓ Auto-detected ElevenLabs API key on this machine."
            eleven_color = "#81C995"
            try:
                sub = requests.get(
                    "https://api.elevenlabs.io/v1/user/subscription",
                    headers={"xi-api-key": self.detected_keys["elevenlabs"]},
                    timeout=3,
                )
                if sub.status_code == 200:
                    d = sub.json()
                    rem = d.get("character_limit", 0) - d.get("character_count", 0)
                    if rem < 40:
                        eleven_msg = "⚠️ Detected ElevenLabs key has 0 credits left — will use consistent Neural Voice."
                        eleven_color = "#FBBF24"
                    else:
                        eleven_msg = f"✓ Auto-detected ElevenLabs API key ({rem:,} credits remaining)."
            except Exception:
                pass
            eleven_hint = QLabel(eleven_msg)
            eleven_hint.setStyleSheet(f"color: {eleven_color}; font-size: 12px; font-weight: 500;")
            card_layout.addWidget(eleven_hint)
        else:
            e_hint_box = QHBoxLayout()
            e_hint_lbl = QLabel("Enables ultra-realistic voice. (Falls back to Windows speech if blank)")
            e_hint_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
            e_key_link = QLabel('<a style="color: #8AB4F8; text-decoration: none;" href="https://elevenlabs.io">Get ElevenLabs key ↗</a>')
            e_key_link.setOpenExternalLinks(True)
            e_hint_box.addWidget(e_hint_lbl)
            e_hint_box.addStretch()
            e_hint_box.addWidget(e_key_link)
            card_layout.addLayout(e_hint_box)

        # 4. Shortcuts & Autostart Checkboxes
        card_layout.addWidget(QLabel("4. System Shortcuts:", objectName="sectionLabel"))
        self.chk_desktop = QCheckBox("Create Desktop shortcut")
        self.chk_desktop.setChecked(True)
        self.chk_start = QCheckBox("Add to Windows Start Menu (searchable in Windows)")
        self.chk_start.setChecked(True)
        self.chk_autostart = QCheckBox("Launch on Windows startup (minimize to system tray)")
        self.chk_autostart.setChecked(True)

        card_layout.addWidget(self.chk_desktop)
        card_layout.addWidget(self.chk_start)
        card_layout.addWidget(self.chk_autostart)

        p0_layout.addWidget(card)

        # Progress Indicator (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #8AB4F8;")
        self.status_lbl.setVisible(False)
        p0_layout.addWidget(self.status_lbl)
        p0_layout.addWidget(self.progress_bar)

        # Bottom Buttons
        p0_btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.close)
        p0_btns.addWidget(cancel_btn)

        # Optional Uninstall Button if installation exists
        if self.existing_dir:
            self.uninstall_btn = QPushButton("🗑️ Uninstall Titanium")
            self.uninstall_btn.setObjectName("dangerBtn")
            self.uninstall_btn.clicked.connect(self._confirm_uninstallation)
            p0_btns.addWidget(self.uninstall_btn)

        p0_btns.addStretch()

        btn_text = "Update / Reinstall" if self.existing_dir else "Install Titanium"
        self.install_btn = QPushButton(btn_text)
        self.install_btn.setObjectName("actionBtn")
        self.install_btn.clicked.connect(self._start_installation)
        p0_btns.addWidget(self.install_btn)
        p0_layout.addLayout(p0_btns)

        self.stack.addWidget(page0)

        # ---- PAGE 1: INSTALL SUCCESS ----
        page1 = QWidget()
        p1_layout = QVBoxLayout(page1)
        p1_layout.setContentsMargins(0, 0, 0, 0)
        p1_layout.setSpacing(16)

        succ_card = QFrame()
        succ_card.setObjectName("card")
        succ_layout = QVBoxLayout(succ_card)
        succ_layout.setSpacing(16)

        succ_icon = QLabel("🎉")
        succ_icon.setStyleSheet("font-size: 40px;")
        succ_layout.addWidget(succ_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        succ_title = QLabel("Titanium Installed Successfully!")
        succ_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        succ_layout.addWidget(succ_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.succ_desc = QLabel("")
        self.succ_desc.setStyleSheet("color: #9AA0A6; font-size: 13px; text-align: center;")
        self.succ_desc.setWordWrap(True)
        succ_layout.addWidget(self.succ_desc, alignment=Qt.AlignmentFlag.AlignCenter)

        self.chk_launch = QCheckBox("Launch Titanium now")
        self.chk_launch.setChecked(True)
        succ_layout.addWidget(self.chk_launch, alignment=Qt.AlignmentFlag.AlignCenter)

        p1_layout.addWidget(succ_card)

        p1_btns = QHBoxLayout()
        p1_btns.addStretch()
        finish_btn = QPushButton("Finish")
        finish_btn.setObjectName("actionBtn")
        finish_btn.clicked.connect(self._finish_and_launch)
        p1_btns.addWidget(finish_btn)
        p1_layout.addLayout(p1_btns)

        self.stack.addWidget(page1)

        # ---- PAGE 2: UNINSTALL SUCCESS ----
        page2 = QWidget()
        p2_layout = QVBoxLayout(page2)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        p2_layout.setSpacing(16)

        un_card = QFrame()
        un_card.setObjectName("card")
        un_layout = QVBoxLayout(un_card)
        un_layout.setSpacing(16)

        un_icon = QLabel("🗑️")
        un_icon.setStyleSheet("font-size: 40px;")
        un_layout.addWidget(un_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        un_title = QLabel("Titanium Uninstalled Successfully")
        un_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        un_layout.addWidget(un_title, alignment=Qt.AlignmentFlag.AlignCenter)

        un_desc = QLabel(
            "All shortcuts, registry autostart entries, and deployed application files\n"
            "have been safely removed from your computer."
        )
        un_desc.setStyleSheet("color: #9AA0A6; font-size: 13px; text-align: center;")
        un_desc.setWordWrap(True)
        un_layout.addWidget(un_desc, alignment=Qt.AlignmentFlag.AlignCenter)

        p2_layout.addWidget(un_card)

        p2_btns = QHBoxLayout()
        p2_btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("actionBtn")
        close_btn.clicked.connect(self.close)
        p2_btns.addWidget(close_btn)
        p2_layout.addLayout(p2_btns)

        self.stack.addWidget(page2)

    def _detect_existing_installation(self) -> Optional[Path]:
        """Detects whether Titanium is already installed anywhere on the system."""
        # 1. Check HKCU Run registry
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                for name in [APP_NAME, "TitaniumAssistant"]:
                    try:
                        val, _ = winreg.QueryValueEx(key, name)
                        if val:
                            p = val.strip().strip('"')
                            exe_path = Path(p)
                            if exe_path.exists():
                                return exe_path.parent
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. Check Start Menu shortcut target
        appdata = Path(os.environ.get("APPDATA", ""))
        start_lnk = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"
        if start_lnk.exists():
            try:
                cmd = f'(New-Object -ComObject WScript.Shell).CreateShortcut("{str(start_lnk)}").TargetPath'
                res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True, timeout=3)
                p = res.stdout.strip().strip('"')
                if p and Path(p).exists():
                    return Path(p).parent
            except Exception:
                pass

        # 3. Check default LocalAppData install dir
        default_dir = Path(os.environ.get("LOCALAPPDATA", "C:\\")) / "Programs" / "Titanium"
        if (default_dir / "Titanium.exe").exists():
            return default_dir

        return None

    def _detect_local_keys(self) -> dict:
        result = {
            "gemini": os.getenv("GEMINI_API_KEY", "").strip(),
            "elevenlabs": os.getenv("ELEVENLABS_API_KEY", "").strip(),
            "voice": os.getenv("ELEVENLABS_VOICE_NAME", "Charlie").strip(),
            "model": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()
        }

        candidates = []
        if self.existing_dir:
            candidates.append(self.existing_dir / ".env")

        user_home = Path(os.environ.get("USERPROFILE", ""))
        candidates.extend([
            user_home / "Downloads" / "Titanium" / ".env",
            Path(__file__).resolve().parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            Path(sys.executable).resolve().parent / ".env",
            Path(os.environ.get("LOCALAPPDATA", "C:\\")) / "Programs" / "Titanium" / ".env"
        ])

        for candidate in candidates:
            if candidate.exists():
                try:
                    for line in candidate.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k == "GEMINI_API_KEY" and not result["gemini"] and v and v != "your_gemini_api_key_here":
                            result["gemini"] = v
                        elif k == "ELEVENLABS_API_KEY" and not result["elevenlabs"] and v and v != "your_elevenlabs_api_key_here":
                            result["elevenlabs"] = v
                        elif k == "ELEVENLABS_VOICE_NAME" and v:
                            result["voice"] = v
                        elif k == "ELEVENLABS_MODEL_ID" and v:
                            result["model"] = v
                except Exception:
                    pass
        return result

    def _browse_directory(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.dir_input.text())
        if chosen:
            self.dir_input.setText(chosen)

    def _start_installation(self):
        target_path = Path(self.dir_input.text().strip())
        key = self.key_input.text().strip()
        eleven_key = self.eleven_input.text().strip()

        if not key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter your Google Gemini API Key.\n\n"
                "If you don't have one yet, you can get a free key instantly at:\nhttps://aistudio.google.com/app/apikey"
            )
            return

        self.install_btn.setEnabled(False)
        if hasattr(self, "uninstall_btn"):
            self.uninstall_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("Verifying API Key...")
        self.progress_bar.setValue(10)

        self.worker = InstallWorker(
            target_dir=target_path,
            api_key=key,
            elevenlabs_key=eleven_key,
            elevenlabs_voice=self.detected_keys.get("voice", "Charlie"),
            elevenlabs_model=self.detected_keys.get("model", "eleven_flash_v2_5"),
            create_desktop=self.chk_desktop.isChecked(),
            create_start=self.chk_start.isChecked(),
            autostart=self.chk_autostart.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _confirm_uninstallation(self):
        loc = str(self.existing_dir) if self.existing_dir else "your system"
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall Titanium from {loc}?\n\n"
            "This will delete shortcuts, remove Windows autostart entries, and clean up application files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_uninstallation()

    def _start_uninstallation(self):
        self.install_btn.setEnabled(False)
        if hasattr(self, "uninstall_btn"):
            self.uninstall_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("Uninstalling Titanium...")
        self.progress_bar.setValue(10)

        self.un_worker = UninstallWorker(self.existing_dir)
        self.un_worker.progress.connect(self._on_progress)
        self.un_worker.finished.connect(self._on_uninstall_finished)
        self.un_worker.start()

    def _on_uninstall_finished(self, success: bool, msg: str):
        if success:
            self.stack.setCurrentIndex(2) # Show uninstall success page
        else:
            self.install_btn.setEnabled(True)
            if hasattr(self, "uninstall_btn"):
                self.uninstall_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_lbl.setVisible(False)
            QMessageBox.critical(self, "Uninstallation Failed", msg)

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        self.install_btn.setEnabled(True)
        if hasattr(self, "uninstall_btn"):
            self.uninstall_btn.setEnabled(True)
        if success:
            dest = self.dir_input.text().strip()
            self.succ_desc.setText(
                f"Titanium has been installed to:\n{dest}\n\n"
                "The 3D Siri Orb, multimodal screen vision, and headless background audio are ready to run."
            )
            self.installed_exe_path = Path(dest) / "Titanium.exe"
            self.stack.setCurrentIndex(1)
        else:
            self.progress_bar.setVisible(False)
            self.status_lbl.setVisible(False)
            QMessageBox.critical(self, "Installation Failed", msg)

    def _finish_and_launch(self):
        if self.chk_launch.isChecked() and hasattr(self, "installed_exe_path"):
            if self.installed_exe_path.exists():
                try:
                    subprocess.Popen([str(self.installed_exe_path)], cwd=str(self.installed_exe_path.parent))
                except Exception as e:
                    print(f"Error launching: {e}")
        self.close()


def main():
    app = QApplication(sys.argv)
    window = TitaniumInstallerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
