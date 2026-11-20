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
from titanium.ui.subtitle_pill import CompactSubtitlePill
from titanium.ui.tray import TitaniumTrayIcon
from titanium.tools.installer import WindowsInstaller

class TitaniumApp(QObject):
    """Main Application Controller for Titanium Virtual Assistant."""
    
    # Internal signals for cross-thread Qt UI updates
    update_orb_state = Signal(str)
    show_response_signal = Signal(str, str)
    show_user_prompt_signal = Signal(str)
    start_circle_search_signal = Signal()

    def __init__(self):
        super().__init__()
        
        # 1. Initialize Core Services (< 70MB total RAM)
        self.memory = MemoryManager()
        self.tts = ElevenLabsTTS()
        self.router = AgentRouter(memory=self.memory)
        self.live_client = GeminiLiveClient(tts=self.tts)
        self.initial_greeting_done = False
        self.live_conversation_mode = False
        self.follow_conversation = False

        # 2. Initialize UI Components
        self.orb = SiriOrbWidget()
        self.overlay = CircleToSearchOverlay(on_crop_captured=self.on_circle_crop_captured)
        self.subtitle_pill = CompactSubtitlePill()
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
        self.orb.request_toggle_live_mode.connect(self.toggle_live_conversation)

        self.update_orb_state.connect(self.orb.set_state)
        self.show_response_signal.connect(self._on_show_response)
        self.show_user_prompt_signal.connect(self._on_show_user_prompt)
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

    def _on_show_response(self, text: str, user_text: str = ""):
        """Displays conversational response docked directly below the Siri Orb."""
        self.subtitle_pill.display_below_orb(text, self.orb.geometry(), user_text=user_text)

    def _on_show_user_prompt(self, user_text: str):
        """Displays user prompt immediately in black Gemini dark-mode bubble shifted right."""
        self.subtitle_pill.show_user_prompt(user_text, self.orb.geometry())

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

    def toggle_live_conversation(self):
        """Toggles persistent Live Conversation mode."""
        self.set_live_conversation_mode(not self.live_conversation_mode)

    def set_live_conversation_mode(self, enable: bool):
        """Controls persistent Gemini Live mode (mic never turns off, continuous conversation)."""
        self.live_conversation_mode = enable
        self.follow_conversation = enable
        self.orb.set_live_mode(enable)
        if enable:
            self.live_client.start()
            self.wake_listener.set_active_session(True)
            self.update_orb_state.emit("listening")
            self.show_response_signal.emit("🔴 Live Conversation Active (Always Listening)", "")
        else:
            self.wake_listener.set_active_session(False)
            self.update_orb_state.emit("idle")
            self.show_response_signal.emit("Live Conversation Paused", "")

    def on_wake_word_triggered(self, cmd: str):
        """Called when user says 'Hey Titanium' or speaks during an active session."""
        print(f"[TitaniumApp] Wake or voice received: '{cmd}'")
        lower = cmd.lower().strip() if cmd else ""

        # 1. Exit / Stop Live Conversation or active session
        if any(w in lower for w in [
            "stop live conversation", "disable live conversation", "turn off live conversation",
            "stop live mode", "disable live mode", "exit live mode", "exit_session", "stop listening", "bye", "shant"
        ]):
            self.set_live_conversation_mode(False)
            self.speak_with_pause("Live conversation mode disabled. Main normal wake word mode par switch ho gaya hoon.", next_state="idle")
            return

        # 2. Enable Live Conversation Mode
        if any(w in lower for w in [
            "start live conversation", "enable live conversation", "turn on live conversation",
            "start live mode", "enable live mode", "live conversation start", "live mode start", "live conversation enable"
        ]):
            self.set_live_conversation_mode(True)
            msg = "Live Conversation mode enabled! Ab main continuously sun raha hoon, bina 'Hey Titanium' bole direct baat kijiye."
            self.show_response_signal.emit(msg, cmd)
            self.speak_with_pause(msg, next_state="listening")
            return

        # 3. Follow conversation request (multi-turn follow when live mode is not enabled)
        if any(w in lower for w in [
            "follow the conversation", "follow conversation", "continue conversation", "please follow the conversation"
        ]):
            self.follow_conversation = True
            self.wake_listener.set_active_session(True)
            self.update_orb_state.emit("listening")
            msg = "Haanji Parth! Main conversation follow kar raha hoon. Boliye!"
            self.show_response_signal.emit(msg, cmd)
            self.speak_with_pause(msg, next_state="listening")
            return

        # Spoken ONLY ONCE when the app starts / initial wake trigger
        if not self.initial_greeting_done:
            self.initial_greeting_done = True
            self.wake_listener.set_active_session(True)
            greeting = "Haanji Parth, bataiye kya baat hai? Main hoon aapki help karne ke liye."
            self.show_response_signal.emit(greeting, "")
            self.speak_with_pause(greeting, next_state="listening" if self.live_conversation_mode else "idle")
            return

        if cmd and len(cmd.strip()) > 1:
            self.wake_listener.set_active_session(True)
            self.handle_user_prompt(cmd.strip())
        else:
            # Wake word triggered without trailing query: listen attentively
            self.wake_listener.set_active_session(True)
            self.update_orb_state.emit("listening")
            self.show_response_signal.emit("Listening...", "")

    def toggle_live_session(self):
        """Clicking the Orb toggles continuous Gemini Live conversation."""
        if self.live_conversation_mode:
            self.set_live_conversation_mode(False)
            self.speak_with_pause("Live conversation paused.", next_state="idle")
        elif self.wake_listener.in_active_session:
            self.wake_listener.set_active_session(False)
            self.follow_conversation = False
            self.update_orb_state.emit("idle")
            self.show_response_signal.emit("Paused", "")
        else:
            self.wake_listener.set_active_session(True)
            self.tts.play_wake_chime()
            self.update_orb_state.emit("listening")
            if not self.initial_greeting_done:
                self.initial_greeting_done = True
                greeting = "Haanji Parth, bataiye kya baat hai? Main hoon aapki help karne ke liye."
                self.show_response_signal.emit(greeting, "")
                self.speak_with_pause(greeting, next_state="listening")
            else:
                self.show_response_signal.emit("Listening...", "")

    def on_circle_crop_captured(self, png_bytes: bytes):
        """Handles captured crop from Circle to Search."""
        self.orb.set_state("thinking")
        
        def worker():
            explanation = self.router.analyze_image_crop(
                png_bytes,
                user_query="Is selected area ko dekhein aur bataiye kya hai. Explain crisp and concisely in 1-2 natural sentences."
            )
            # Display ultra-compact pill under orb
            self.show_response_signal.emit(explanation, "")
            self.speak_with_pause(explanation)

        threading.Thread(target=worker, daemon=True).start()

    def handle_user_prompt(self, prompt: str):
        """Processes a prompt from user dialog or voice."""
        self.orb.set_state("thinking")
        # Instantly show the user's spoken words in black Gemini dark-mode bubble shifted right!
        self.show_user_prompt_signal.emit(prompt)

        def worker():
            answer = self.router.handle_user_query(prompt)
            # Display conversation turn (user prompt + AI response)
            self.show_response_signal.emit(answer, prompt)

            # Determine whether mic stays continuously active (Live Mode) or returns to idle
            should_stay_listening = self.live_conversation_mode or self.follow_conversation
            next_st = "listening" if should_stay_listening else "idle"

            def on_done():
                if should_stay_listening:
                    self.wake_listener.set_active_session(True)
                    self.update_orb_state.emit("listening")
                else:
                    self.wake_listener.set_active_session(False)
                    self.update_orb_state.emit("idle")

            self.speak_with_pause(answer, on_done=on_done, next_state=next_st)

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

def enforce_single_instance():
    """Ensures strictly ONE Titanium process and ONE Orb exists on the desktop.
    If an existing or orphaned background process is running, terminates it cleanly
    so this interactive launch reliably takes over the screen.
    """
    import os
    import psutil

    my_pid = os.getpid()
    parent_pid = os.getppid()

    # Find and terminate any other Titanium instance
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = p.info['pid']
            if pid in (my_pid, parent_pid):
                continue
            pname = (p.info['name'] or '').lower()
            if pname in ('python.exe', 'pythonw.exe'):
                cmdline = ' '.join(p.info['cmdline'] or [])
                if 'main.py' in cmdline:
                    try:
                        p.kill()
                    except Exception:
                        pass
        except Exception:
            pass

    # Clean up any stale lock file
    lock_path = os.path.join(os.environ.get("TEMP", "."), "titanium_single_instance.lock")
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass

def main():
    import time
    from pathlib import Path

    try:
        enforce_single_instance()

        # Set Windows AppUserModelID so Windows taskbar & Start Menu associate the high-res icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Titanium.AI.Assistant")
        except Exception:
            pass

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False) # Keep running in system tray
        
        icon_path = Path(__file__).resolve().parent / "titanium.ico"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            app.setWindowIcon(QIcon(str(icon_path)))
        
        titanium_controller = TitaniumApp()
        
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        log_path = Path(__file__).resolve().parent / "titanium_runtime.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- Crash at {time.ctime()} ---\n")
            f.write(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
