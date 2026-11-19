import sys
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Slot

from titanium.memory.sqlite_memory import MemoryManager
from titanium.core.elevenlabs_tts import ElevenLabsTTS
from titanium.core.agent_router import AgentRouter
from titanium.core.live_client import GeminiLiveClient
from titanium.core.wake_listener import WakeWordListener
from titanium.ui.siri_orb import SiriOrbWidget
from titanium.ui.circle_search import CircleToSearchOverlay
from titanium.ui.code_viewer import CodeViewerWindow
from titanium.ui.tray import TitaniumTrayIcon
from titanium.tools.installer import WindowsInstaller

class TitaniumApp(QObject):
    """Main Application Controller for Titanium Virtual Assistant."""
    
    # Internal signals for cross-thread Qt UI updates
    update_orb_state = Signal(str)
    show_response_signal = Signal(str, str)
    start_circle_search_signal = Signal()

    def __init__(self):
        super().__init__()
        
        # 1. Initialize Core Services (< 70MB total RAM)
        self.memory = MemoryManager()
        self.tts = ElevenLabsTTS()
        self.router = AgentRouter(memory=self.memory)
        self.live_client = GeminiLiveClient(tts=self.tts)

        # 2. Initialize UI Components
        self.orb = SiriOrbWidget()
        self.overlay = CircleToSearchOverlay(on_crop_captured=self.on_circle_crop_captured)
        self.code_viewer = CodeViewerWindow(title="Titanium Assistant")
        self.tray = TitaniumTrayIcon(
            on_toggle_orb=self.toggle_orb_visibility,
            on_circle_search=self.start_circle_search,
            on_install=self.install_system_integration
        )

        # 3. Connect UI Signals
        self.orb.request_circle_search.connect(self.start_circle_search)
        self.orb.request_screen_share_toggle.connect(self.toggle_screen_share)
        self.orb.request_user_prompt.connect(self.handle_user_prompt)
        self.orb.request_install.connect(self.install_system_integration)
        self.orb.request_toggle_listening.connect(self.toggle_live_session)

        self.update_orb_state.connect(self.orb.set_state)
        self.show_response_signal.connect(self._on_show_response)
        self.start_circle_search_signal.connect(self.overlay.trigger)

        # 4. Bind Live Client State Callbacks
        self.live_client.on_state_change = lambda state: self.update_orb_state.emit(state)

        # 5. Register Global Hotkey (Ctrl+Shift+S for Circle to Search)
        self._setup_global_hotkey()

        # 6. Initialize Always-On Wake Word Listener ('Hey Titanium')
        self.wake_listener = WakeWordListener(
            on_wake=self.on_wake_word_triggered,
            on_wake_chime=self.tts.play_wake_chime,
            on_listening_state=self.on_mic_activity
        )
        self.wake_listener.start()

        # 7. Show initial components
        self.orb.reveal()
        self.tray.show()

        print("[Titanium] Initialized and running in system tray with Wake Word.")

    def _on_show_response(self, text: str, title: str):
        """Displays code or rich response card docked directly below the Siri Orb."""
        self.code_viewer.display_below_orb(text, self.orb.geometry(), title)

    def toggle_orb_visibility(self):
        if self.orb.isVisible():
            self.orb.hide()
        else:
            self.orb.show()
            self.orb.raise_()

    def start_circle_search(self):
        """Triggers Circle to Search overlay."""
        self.start_circle_search_signal.emit()

    def install_system_integration(self):
        """Installs Titanium into Windows Start Menu, Desktop, and Task Manager Startup."""
        res = WindowsInstaller.install()
        if res.get("success"):
            msg = "Titanium Windows Start Menu aur Task Manager Startup mein successfully install ho gaya hai!"
            self.show_response_signal.emit(
                "✅ Installation Complete!\n\n"
                "• Windows Start Menu: Search 'Titanium' to open anytime.\n"
                "• Task Manager Startup: Titanium is registered to autostart on boot.\n"
                "• Desktop: Shortcut created.",
                "System Installation"
            )
            self.tts.speak_text(msg)
        else:
            self.show_response_signal.emit(
                f"Installation note: {res.get('message', 'Check permissions.')}",
                "System Installation"
            )

    def speak_with_pause(self, text: str, on_done=None, next_state="listening"):
        """Speaks via ElevenLabs while temporarily pausing mic to avoid self-triggering."""
        def start_cb():
            self.wake_listener.pause()
            self.update_orb_state.emit("speaking")

        def finish_cb():
            self.wake_listener.resume()
            if self.wake_listener.in_active_session:
                self.update_orb_state.emit("listening")
            else:
                self.update_orb_state.emit(next_state)
            if on_done:
                on_done()

        self.tts.speak_text(text, on_start=start_cb, on_finish=finish_cb)

    def on_mic_activity(self, is_active: bool):
        if is_active and self.orb.state == "idle":
            self.update_orb_state.emit("listening")
        elif not is_active and self.orb.state == "listening" and not self.tts.is_speaking() and not self.wake_listener.in_active_session:
            self.update_orb_state.emit("idle")

    def on_wake_word_triggered(self, cmd: str):
        """Called when user says 'Hey Titanium' or speaks during an active session."""
        print(f"[TitaniumApp] Wake or voice received: '{cmd}'")
        if cmd == "exit_session":
            self.wake_listener.set_active_session(False)
            self.speak_with_pause("Shant ho gaya hoon. Jab bhi zaroorat ho, bas 'Hey Titanium' boliye.", next_state="idle")
            return

        if cmd and len(cmd.strip()) > 1:
            self.wake_listener.set_active_session(True)
            self.handle_user_prompt(cmd.strip())
        else:
            self.wake_listener.set_active_session(True)
            self.update_orb_state.emit("listening")
            self.speak_with_pause("Haanji! Bataiye, main sun raha hoon.", next_state="listening")

    def toggle_live_session(self):
        """Clicking the Orb toggles continuous Gemini Live conversation."""
        if self.wake_listener.in_active_session:
            self.wake_listener.set_active_session(False)
            self.update_orb_state.emit("idle")
            self.speak_with_pause("Listening paused.", next_state="idle")
        else:
            self.wake_listener.set_active_session(True)
            self.tts.play_wake_chime()
            self.update_orb_state.emit("listening")
            self.speak_with_pause("Haanji! I am listening.", next_state="listening")

    def on_circle_crop_captured(self, png_bytes: bytes):
        """Handles captured crop from Circle to Search."""
        self.orb.set_state("thinking")
        
        def worker():
            explanation = self.router.analyze_image_crop(
                png_bytes,
                user_query="Is selected area ko dekhein aur bataiye kya hai. Explain concisely in natural Hinglish."
            )
            self.show_response_signal.emit(explanation, "Circle to Search Analysis")
            self.speak_with_pause(explanation)

        threading.Thread(target=worker, daemon=True).start()

    def handle_user_prompt(self, prompt: str):
        """Processes a prompt from user dialog or voice."""
        self.orb.set_state("thinking")

        def worker():
            answer = self.router.handle_user_query(prompt)
            is_code_request = any(w in prompt.lower() for w in ["code", "python", "script", "function", "program", "sql", "html", "write", "create"])
            if is_code_request or "```" in answer or len(answer) > 200:
                self.show_response_signal.emit(answer, "Titanium Code & Intelligence")
            self.speak_with_pause(answer)

        threading.Thread(target=worker, daemon=True).start()

    def toggle_screen_share(self):
        """Toggles 1 FPS screen frame streaming into Gemini 3.8 Live."""
        is_active = self.live_client.toggle_screen_share()
        self.orb.set_screen_sharing(is_active)
        if is_active:
            self.live_client.start()
            self.speak_with_pause("Screen share active hai. Main aapki screen dekh raha hoon.")
        else:
            self.speak_with_pause("Screen share band ho gaya hai.")

    def _setup_global_hotkey(self):
        """Registers system-wide Ctrl+Shift+S hotkey using pynput."""
        def hotkey_thread():
            try:
                from pynput import keyboard
                with keyboard.GlobalHotKeys({
                    '<ctrl>+<shift>+s': self.start_circle_search
                }) as h:
                    h.join()
            except Exception as e:
                print(f"[Titanium] Global hotkey warning: {e}")

        threading.Thread(target=hotkey_thread, daemon=True).start()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in system tray
    
    titanium_controller = TitaniumApp()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
