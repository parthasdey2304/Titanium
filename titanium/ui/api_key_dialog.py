import sys
import os
import requests
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QDesktopServices, QUrl


class KeyValidationWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key.strip()

    def run(self):
        if not self.api_key:
            self.finished.emit(False, "API key cannot be empty.")
            return

        try:
            # Fast ping to Gemini models endpoint to check key validity
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            resp = requests.get(url, timeout=7)
            if resp.status_code == 200:
                self.finished.emit(True, "Key verified successfully!")
            else:
                err_data = resp.json().get("error", {})
                msg = err_data.get("message", f"HTTP {resp.status_code} Error")
                self.finished.emit(False, f"Verification failed: {msg[:60]}")
        except Exception as e:
            self.finished.emit(False, f"Network error: {str(e)[:50]}")


class ApiKeySetupDialog(QDialog):
    """Modern Gemini-themed dark mode on-screen dialog to enter and validate Gemini API Key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Titanium - Gemini API Key Setup")
        self.setFixedSize(480, 290)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #131314;
                border-radius: 14px;
                border: 1px solid #28292A;
            }
            QLabel {
                color: #E3E3E3;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #1E1F20;
                color: #FFFFFF;
                border: 1.5px solid #3C4043;
                border-radius: 8px;
                padding: 0px 14px;
                min-height: 44px;
                height: 44px;
                font-size: 13px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                selection-background-color: #1A73E8;
            }
            QLineEdit:focus {
                border: 1.5px solid #8AB4F8;
                background-color: #242628;
            }
            QPushButton#saveBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1A73E8, stop:1 #8AB4F8);
                color: #000000;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                padding: 10px 20px;
                border: none;
            }
            QPushButton#saveBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E88E5, stop:1 #A8C7FA);
            }
            QPushButton#saveBtn:disabled {
                background-color: #3C4043;
                color: #80868B;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: #9AA0A6;
                font-size: 13px;
                border-radius: 8px;
                padding: 10px 16px;
                border: 1px solid #3C4043;
            }
            QPushButton#cancelBtn:hover {
                background-color: #1E1F20;
                color: #FFFFFF;
            }
            QLabel#linkBtn {
                color: #8AB4F8;
                font-size: 12px;
                text-decoration: underline;
                cursor: pointer;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel("✨")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title_box.addWidget(icon_lbl)

        title_lbl = QLabel("Welcome to Titanium")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()
        layout.addLayout(title_box)

        # Subtitle
        sub_lbl = QLabel("To get started, please enter your Google Gemini API Key below.\nTitanium verifies the key in real time before launching.")
        sub_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px; line-height: 1.4;")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)

        # Input Field
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste Gemini API Key (AIzaSy...)")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.textChanged.connect(self._clear_status)
        layout.addWidget(self.key_input)

        # Status Label (shows success or errors)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.status_lbl.setVisible(False)
        layout.addWidget(self.status_lbl)

        # Bottom Bar: Link & Buttons
        btn_layout = QHBoxLayout()
        get_key_link = QLabel('<a style="color: #8AB4F8; text-decoration: none;" href="https://aistudio.google.com/app/apikey">Get free API key ↗</a>')
        get_key_link.setOpenExternalLinks(True)
        btn_layout.addWidget(get_key_link)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Verify & Launch")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._start_validation)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _clear_status(self):
        self.status_lbl.setVisible(False)

    def _start_validation(self):
        key = self.key_input.text().strip()
        if not key:
            self.status_lbl.setText("⚠️ Please paste your Gemini API key.")
            self.status_lbl.setStyleSheet("color: #F28B82; font-size: 12px;")
            self.status_lbl.setVisible(True)
            return

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Verifying...")
        self.status_lbl.setText("⏳ Connecting to Gemini API...")
        self.status_lbl.setStyleSheet("color: #8AB4F8; font-size: 12px;")
        self.status_lbl.setVisible(True)

        self.worker = KeyValidationWorker(key)
        self.worker.finished.connect(self._on_validation_result)
        self.worker.start()

    def _on_validation_result(self, success: bool, message: str):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Verify & Launch")

        if success:
            self.status_lbl.setText("✅ " + message)
            self.status_lbl.setStyleSheet("color: #81C995; font-size: 12px; font-weight: 600;")
            self.status_lbl.setVisible(True)

            # Save key to .env file next to executable or root
            self._save_key_to_env(self.key_input.text().strip())

            # Close dialog after brief success indicator
            from PySide6.QtCore import QTimer
            QTimer.singleShot(700, self.accept)
        else:
            self.status_lbl.setText("❌ " + message)
            self.status_lbl.setStyleSheet("color: #F28B82; font-size: 12px;")
            self.status_lbl.setVisible(True)

    def _save_key_to_env(self, key: str):
        if getattr(sys, 'frozen', False):
            env_file = Path(sys.executable).resolve().parent / ".env"
        else:
            env_file = Path(__file__).resolve().parent.parent.parent / ".env"

        lines = []
        if env_file.exists():
            try:
                lines = env_file.read_text(encoding="utf-8").splitlines()
            except Exception:
                pass

        key_found = False
        new_lines = []
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f"GEMINI_API_KEY={key}")

        try:
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            print(f"[ApiKeyDialog] Error writing .env: {e}")

        # Set environment variable in active process
        os.environ["GEMINI_API_KEY"] = key
