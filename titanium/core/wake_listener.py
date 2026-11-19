import time
import math
import threading
from typing import Callable, Optional, List
import numpy as np
import sounddevice as sd
import speech_recognition as sr

WAKE_KEYWORDS = [
    "hey titanium", "titanium", "hi titanium",
    "ok titanium", "hello titanium", "hey titan",
    "titaniam", "taitaniem", "titanyum", "ahey titanium"
]

class WakeWordListener:
    """Always-on microphone listener with automatic noise calibration and instant wake detection."""

    def __init__(
        self,
        on_wake: Callable[[str], None],
        on_wake_chime: Optional[Callable[[], None]] = None,
        on_listening_state: Optional[Callable[[bool], None]] = None,
        sample_rate: int = 16000
    ):
        self.on_wake = on_wake
        self.on_wake_chime = on_wake_chime
        self.on_listening_state = on_listening_state
        self.sample_rate = sample_rate
        self.energy_threshold = 220.0 # Adaptive default

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = False # We control calibration directly

        self._running = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._speech_buffer: List[bytes] = []
        self._is_recording_speech = False
        self._silence_start_time = 0.0
        self._max_silence_duration = 0.7 # seconds of silence to conclude utterance
        self.is_paused = False
        self.in_active_session = False
        self._last_active_time = time.time()

    def set_active_session(self, active: bool):
        """Toggles continuous Gemini Live conversational session."""
        self.in_active_session = active
        self._last_active_time = time.time()
        print(f"[WakeWordListener] Continuous Live session: {active}")

    def pause(self):
        """Mutes recognition temporarily while TTS speaks."""
        self.is_paused = True

    def resume(self):
        """Resumes listening."""
        self.is_paused = False
        self._speech_buffer = []
        self._is_recording_speech = False

    def start(self):
        """Starts continuous microphone listening loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_listener, daemon=True)
        self._thread.start()
        print("[WakeWordListener] Always-on listening started for 'Hey Titanium'...")

    def stop(self):
        """Stops microphone listening."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        print("[WakeWordListener] Listening stopped.")

    def _calibrate_noise(self):
        """Measures 400ms of ambient microphone noise to set dynamic threshold."""
        try:
            samples = sd.rec(int(self.sample_rate * 0.4), samplerate=self.sample_rate, channels=1, dtype='int16')
            sd.wait()
            ambient_rms = np.sqrt(np.mean(samples.flatten().astype(np.float32) ** 2))
            self.energy_threshold = max(180.0, float(ambient_rms * 1.5))
            print(f"[WakeWordListener] Ambient noise calibrated. Energy threshold set to: {self.energy_threshold:.1f}")
        except Exception as e:
            print(f"[WakeWordListener] Noise calibration note: {e}")

    def _run_listener(self):
        self._calibrate_noise()
        block_size = 2048 # ~128ms per block

        def audio_callback(indata, frames, time_info, status):
            if not self._running or self.is_paused:
                return

            audio_data = indata.flatten()
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

            if rms > self.energy_threshold:
                if not self._is_recording_speech:
                    self._is_recording_speech = True
                    self._speech_buffer = []
                    if self.on_listening_state:
                        self.on_listening_state(True)
                self._speech_buffer.append(indata.tobytes())
                self._silence_start_time = time.time()
            elif self._is_recording_speech:
                self._speech_buffer.append(indata.tobytes())
                if time.time() - self._silence_start_time > self._max_silence_duration:
                    self._is_recording_speech = False
                    if self.on_listening_state:
                        self.on_listening_state(False)

                    full_audio_bytes = b"".join(self._speech_buffer)
                    self._speech_buffer = []

                    if len(full_audio_bytes) > (self.sample_rate * 2 * 0.5): # at least 0.5s audio
                        threading.Thread(
                            target=self._process_utterance,
                            args=(full_audio_bytes,),
                            daemon=True
                        ).start()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=block_size,
                callback=audio_callback
            ) as stream:
                self._stream = stream
                while self._running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[WakeWordListener] Microphone error: {e}")
            self._running = False

    def _process_utterance(self, audio_bytes: bytes):
        """Transcribes speech and handles continuous conversational turns like Gemini Live."""
        try:
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
            transcript = self.recognizer.recognize_google(audio_data, language="en-IN")
            text = transcript.lower().strip()
            print(f"[WakeWordListener] Captured: '{transcript}'")

            # 1. Check for exit commands in continuous mode
            if self.in_active_session and any(w in text for w in ["bye", "stop", "shant", "quiet", "alvida", "exit"]):
                self.in_active_session = False
                self.on_wake("exit_session")
                return

            # 2. Check for wake keywords
            matched_kw = None
            for kw in WAKE_KEYWORDS:
                if kw in text:
                    matched_kw = kw
                    break

            if matched_kw:
                # Enter continuous session
                self.in_active_session = True
                self._last_active_time = time.time()
                if self.on_wake_chime:
                    self.on_wake_chime()

                parts = text.split(matched_kw, 1)
                trailing_cmd = parts[1].strip() if len(parts) > 1 else ""
                trailing_cmd = trailing_cmd.lstrip(" ,.-")
                print(f"[WakeWordListener] Wake word triggered! Command: '{trailing_cmd}'")
                self.on_wake(trailing_cmd)
            elif self.in_active_session:
                # In active continuous Gemini Live session: process speech directly!
                self._last_active_time = time.time()
                print(f"[WakeWordListener] Live conversational turn: '{text}'")
                self.on_wake(text)

        except sr.UnknownValueError:
            pass # Ambient noise
        except Exception as e:
            print(f"[WakeWordListener] Recognition error: {e}")
