import re
import time
import threading
from typing import Callable, Optional, List
import numpy as np
from scipy import signal
import sounddevice as sd
import speech_recognition as sr

WAKE_KEYWORDS = [
    "hey titanium", "titanium", "hi titanium",
    "ok titanium", "hello titanium", "hey titan",
    "titaniam", "taitaniem", "titanyum", "ahey titanium"
]

SHUTDOWN_TRIGGERS = [
    "turn yourself off", "turn off yourself", "turn off titanium", "titanium turn off",
    "titanium turn yourself off", "shut yourself down", "shut down titanium", "shutdown titanium",
    "titanium shut down", "titanium shutdown", "turn yourself down", "shut down yourself",
    "band ho jao", "apne aap ko band karo", "apne aap ko band kar do", "titanium band ho jao",
    "close yourself", "quit yourself", "exit titanium", "quit titanium", "close titanium",
    "stop titanium", "power off titanium", "titanium power off"
]

EXIT_SESSION_PATTERNS = [
    r"\bbye\b", r"\bgoodbye\b", r"\balvida\b", r"\bshant\b", r"\bquiet\b",
    r"\bstop listening\b", r"\bexit session\b", r"\bstop conversation\b",
    r"^stop$", r"^exit$"
]


class WakeWordListener:
    """Always-on microphone listener equipped with digital signal processing (DSP)
    for mechanical typing noise rejection, acoustic bandpass filtering, and instant wake detection.
    """

    def __init__(
        self,
        on_wake: Callable[[str], None],
        on_wake_chime: Optional[Callable[[], None]] = None,
        on_listening_state: Optional[Callable[[bool], None]] = None,
        on_session_timeout: Optional[Callable[[], None]] = None,
        sample_rate: int = 16000
    ):
        self.on_wake = on_wake
        self.on_wake_chime = on_wake_chime
        self.on_listening_state = on_listening_state
        self.on_session_timeout = on_session_timeout
        self.sample_rate = sample_rate
        self.energy_threshold = 260.0

        # Precompute 4th-order Butterworth bandpass filter (300 Hz - 3400 Hz human vocal range)
        self._sos = signal.butter(4, [300, 3400], btype='bandpass', fs=self.sample_rate, output='sos')
        self._filter_zi = signal.sosfilt_zi(self._sos)

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 260
        self.recognizer.dynamic_energy_threshold = False

        self._running = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._speech_buffer: List[bytes] = []
        self._is_recording_speech = False
        self._silence_start_time = 0.0
        self._max_silence_duration = 0.65  # Natural pause tolerance before concluding utterance
        self._record_start_time = 0.0
        self._voiced_streak = 0
        self.is_paused = False
        self._resume_ignore_until = 0.0
        self.in_active_session = False
        self.persistent_session = False  # True only when user explicitly turns on Live Conversation Mode
        self.follow_up_timeout = 25.0    # Follow-up conversational window (seconds) after Titanium speaks
        self._last_active_time = time.time()

    def set_active_session(self, active: bool, persistent: Optional[bool] = None):
        """Toggles active conversational listening session (with optional idle timeout control)."""
        self.in_active_session = active
        if persistent is not None:
            self.persistent_session = persistent
        elif not active:
            self.persistent_session = False
        self._last_active_time = time.time()
        print(f"[WakeWordListener] Active session: {active} (persistent={self.persistent_session})", flush=True)

    def pause(self):
        """Mutes recognition temporarily while TTS speaks."""
        self.is_paused = True
        self._is_recording_speech = False
        self._speech_buffer = []
        self._voiced_streak = 0

    def resume(self):
        """Resumes listening with clean filter state and brief echo guard."""
        self._speech_buffer = []
        self._is_recording_speech = False
        self._voiced_streak = 0
        self._filter_zi = signal.sosfilt_zi(self._sos)
        self._resume_ignore_until = time.time() + 0.25
        self._last_active_time = time.time()
        self.is_paused = False

    def start(self):
        """Starts continuous microphone listening loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_listener, daemon=True)
        self._thread.start()
        print("[WakeWordListener] DSP Anti-Typing Microphone listening started...", flush=True)

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
        print("[WakeWordListener] Listening stopped.", flush=True)

    def _calibrate_noise(self):
        """Measures 500ms of quiet ambient microphone noise (never during TTS playback)."""
        while self.is_paused and self._running:
            time.sleep(0.08)
        if not self._running:
            return
        try:
            samples = sd.rec(int(self.sample_rate * 0.5), samplerate=self.sample_rate, channels=1, dtype='int16')
            sd.wait()
            raw = samples.flatten().astype(np.float32)
            self._filter_zi = signal.sosfilt_zi(self._sos)
            filtered, self._filter_zi = signal.sosfilt(self._sos, raw, zi=self._filter_zi)
            ambient_rms = np.sqrt(np.mean(filtered ** 2))
            # Clamp threshold safely so loud startup sound never deafens the microphone
            self.energy_threshold = min(750.0, max(200.0, float(ambient_rms * 1.45)))
            print(f"[WakeWordListener] Calibrated energy threshold: {self.energy_threshold:.1f}", flush=True)
        except Exception as e:
            print(f"[WakeWordListener] Calibration note: {e}", flush=True)

    def _run_listener(self):
        self._calibrate_noise()
        block_size = 1024  # ~64ms per block

        def audio_callback(indata, frames, time_info, status):
            if not self._running or self.is_paused or time.time() < self._resume_ignore_until:
                return

            raw_data = indata.flatten().astype(np.float32)
            filtered, self._filter_zi = signal.sosfilt(self._sos, raw_data, zi=self._filter_zi)

            rms = np.sqrt(np.mean(filtered ** 2))
            peak = np.max(np.abs(filtered))
            crest_factor = peak / (rms + 1e-5)

            # Impulsive mechanical keyclicks have very sharp crest (> 6.5) with low sustained energy
            is_click = (crest_factor > 6.5) or (peak > 22000 and rms < 1200)
            is_voiced = (rms > self.energy_threshold) and not is_click

            if is_voiced:
                self._voiced_streak += 1
            else:
                self._voiced_streak = max(0, self._voiced_streak - 1)

            if self._voiced_streak >= 2:
                if not self._is_recording_speech:
                    self._is_recording_speech = True
                    self._speech_buffer = []
                    self._record_start_time = time.time()
                    if self.on_listening_state:
                        self.on_listening_state(True)

                clean_int16 = np.clip(filtered, -32768, 32767).astype(np.int16)
                self._speech_buffer.append(clean_int16.tobytes())
                self._silence_start_time = time.time()

            elif self._is_recording_speech:
                clean_int16 = np.clip(filtered, -32768, 32767).astype(np.int16)
                self._speech_buffer.append(clean_int16.tobytes())

                if is_voiced:
                    self._silence_start_time = time.time()

                silence_duration = time.time() - self._silence_start_time
                total_duration = time.time() - self._record_start_time

                if silence_duration > self._max_silence_duration or total_duration > 10.0:
                    self._is_recording_speech = False
                    self._voiced_streak = 0
                    if self.on_listening_state:
                        self.on_listening_state(False)

                    full_audio_bytes = b"".join(self._speech_buffer)
                    self._speech_buffer = []

                    # Accept utterances >= 0.25s so crisp commands are never dropped
                    if len(full_audio_bytes) > (self.sample_rate * 2 * 0.25):
                        threading.Thread(
                            target=self._process_utterance,
                            args=(full_audio_bytes,),
                            daemon=True
                        ).start()
            else:
                # Adapt baseline threshold smoothly (bounded so noise bursts don't lock out speech)
                if not is_click:
                    self.energy_threshold = min(
                        850.0,
                        max(200.0, 0.98 * self.energy_threshold + 0.02 * (rms * 1.45))
                    )

        while self._running:
            try:
                device_idx = None
                try:
                    def_in = sd.default.device[0]
                    if def_in is not None and def_in >= 0:
                        device_idx = def_in
                except Exception:
                    pass

                with sd.InputStream(
                    device=device_idx,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocksize=block_size,
                    callback=audio_callback
                ) as stream:
                    self._stream = stream
                    while self._running:
                        time.sleep(0.1)
                        # Close non-persistent follow-up listening window cleanly after inactivity
                        if (
                            self.in_active_session
                            and not self.persistent_session
                            and not self.is_paused
                            and not self._is_recording_speech
                            and (time.time() - self._last_active_time) > self.follow_up_timeout
                        ):
                            self.in_active_session = False
                            print("[WakeWordListener] Follow-up listening window timed out -> idle.", flush=True)
                            if self.on_session_timeout:
                                self.on_session_timeout()
            except Exception as e:
                if not self._running:
                    break
                print(f"[WakeWordListener] Microphone note, reconnecting: {e}", flush=True)
                time.sleep(1.2)

    def _process_utterance(self, audio_bytes: bytes):
        """Transcribes filtered audio with multi-language fallback and handles continuous turns."""
        try:
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)

            transcript = None
            for lang in ["en-IN", "hi-IN"]:
                try:
                    transcript = self.recognizer.recognize_google(audio_data, language=lang)
                    if transcript:
                        break
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    print(f"[WakeWordListener] STT note ({lang}): {e}", flush=True)
                    break

            if not transcript:
                return

            text = transcript.lower().strip()
            print(f"[WakeWordListener] Captured: '{transcript}'", flush=True)

            # 0. Application shutdown commands (works in both normal and active session)
            if any(trig in text for trig in SHUTDOWN_TRIGGERS):
                print(f"[WakeWordListener] Shutdown command detected: '{text}'", flush=True)
                self.in_active_session = False
                self.persistent_session = False
                self.on_wake("shutdown_titanium")
                return

            # 1. Word-boundary session exit check (ignores substrings inside unrelated words)
            if self.in_active_session and not any(w in text for w in ["music", "gaana", "song"]):
                if any(re.search(pat, text) for pat in EXIT_SESSION_PATTERNS):
                    self.in_active_session = False
                    self.persistent_session = False
                    self.on_wake("exit_session")
                    return

            # 2. Check for wake keywords
            matched_kw = None
            for kw in WAKE_KEYWORDS:
                if kw in text:
                    matched_kw = kw
                    break

            if matched_kw:
                self.in_active_session = True
                self._last_active_time = time.time()
                if self.on_wake_chime:
                    self.on_wake_chime()

                parts = text.split(matched_kw, 1)
                trailing_cmd = parts[1].strip().lstrip(" ,.-") if len(parts) > 1 else ""
                print(f"[WakeWordListener] Wake word triggered! Query: '{trailing_cmd}'", flush=True)
                self.on_wake(trailing_cmd)

            elif self.in_active_session:
                self._last_active_time = time.time()
                print(f"[WakeWordListener] Conversational Turn: '{text}'", flush=True)
                self.on_wake(text)

        except Exception as e:
            print(f"[WakeWordListener] Utterance note: {e}", flush=True)
