import time
import math
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

class WakeWordListener:
    """Always-on microphone listener equipped with digital signal processing (DSP)
    for mechanical typing noise rejection, acoustic bandpass filtering, and instant wake detection.
    """

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
        self.energy_threshold = 280.0

        # Precompute 4th-order Butterworth bandpass filter (300 Hz - 3400 Hz human vocal range)
        # Rejects desk vibration rumbles (< 300 Hz) and keycap snap transients (> 3400 Hz)
        self._sos = signal.butter(4, [300, 3400], btype='bandpass', fs=self.sample_rate, output='sos')
        self._filter_zi = signal.sosfilt_zi(self._sos)

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 280
        self.recognizer.dynamic_energy_threshold = False

        self._running = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._speech_buffer: List[bytes] = []
        self._is_recording_speech = False
        self._silence_start_time = 0.0
        self._max_silence_duration = 0.38 # Snappy silence threshold to conclude speech turn
        self._record_start_time = 0.0
        self._voiced_streak = 0
        self.is_paused = False
        self.in_active_session = False
        self._last_active_time = time.time()

    def set_active_session(self, active: bool):
        """Toggles continuous Gemini Live conversational session."""
        self.in_active_session = active
        self._last_active_time = time.time()
        print(f"[WakeWordListener] Continuous Live session: {active}", flush=True)

    def pause(self):
        """Mutes recognition temporarily while TTS speaks."""
        self.is_paused = True

    def resume(self):
        """Resumes listening."""
        self.is_paused = False
        self._speech_buffer = []
        self._is_recording_speech = False
        self._voiced_streak = 0

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
        """Measures 500ms of ambient microphone noise to set dynamic threshold."""
        try:
            samples = sd.rec(int(self.sample_rate * 0.5), samplerate=self.sample_rate, channels=1, dtype='int16')
            sd.wait()
            raw = samples.flatten().astype(np.float32)
            filtered, _ = signal.sosfilt(self._sos, raw, zi=self._filter_zi)
            ambient_rms = np.sqrt(np.mean(filtered ** 2))
            self.energy_threshold = max(260.0, float(ambient_rms * 1.6))
            print(f"[WakeWordListener] Calibrated energy threshold: {self.energy_threshold:.1f}", flush=True)
        except Exception as e:
            print(f"[WakeWordListener] Calibration note: {e}", flush=True)

    def _run_listener(self):
        self._calibrate_noise()
        block_size = 1024 # ~64ms per block for sub-100ms responsiveness

        def audio_callback(indata, frames, time_info, status):
            if not self._running or self.is_paused:
                return

            raw_data = indata.flatten().astype(np.float32)
            filtered, self._filter_zi = signal.sosfilt(self._sos, raw_data, zi=self._filter_zi)

            rms = np.sqrt(np.mean(filtered ** 2))
            peak = np.max(np.abs(filtered))
            crest_factor = peak / (rms + 1e-5)

            # Typing / key clicks have impulsive crest factor (> 5.2) and short duration
            is_click = (crest_factor > 5.0) or (peak > 18000 and rms < 1500)
            is_voiced = (rms > self.energy_threshold) and not is_click

            if is_voiced:
                self._voiced_streak += 1
            else:
                self._voiced_streak = max(0, self._voiced_streak - 1)

            # Require sustained voicing (at least 2 consecutive blocks ~128ms) to start speech
            # This completely filters out isolated keystrokes even at 90+ WPM!
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

                # If it's a keystroke, DO NOT reset silence_start_time!
                # Only real voice resets the silence timer.
                if is_voiced:
                    self._silence_start_time = time.time()

                silence_duration = time.time() - self._silence_start_time
                total_duration = time.time() - self._record_start_time

                # Conclude utterance when speech pauses for 0.65s OR max buffer duration (5.0s) reached
                if silence_duration > self._max_silence_duration or total_duration > 5.0:
                    self._is_recording_speech = False
                    self._voiced_streak = 0
                    if self.on_listening_state:
                        self.on_listening_state(False)

                    full_audio_bytes = b"".join(self._speech_buffer)
                    self._speech_buffer = []

                    if len(full_audio_bytes) > (self.sample_rate * 2 * 0.45):
                        threading.Thread(
                            target=self._process_utterance,
                            args=(full_audio_bytes,),
                            daemon=True
                        ).start()
            else:
                # Slowly adapt baseline threshold to room acoustics
                if not is_click:
                    self.energy_threshold = max(240.0, 0.98 * self.energy_threshold + 0.02 * (rms * 1.5))

        while self._running:
            try:
                # Resolve active input device safely
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
                        time.sleep(0.05)
            except Exception as e:
                if not self._running:
                    break
                print(f"[WakeWordListener] Microphone note, reconnecting: {e}", flush=True)
                time.sleep(1.2)

    def _process_utterance(self, audio_bytes: bytes):
        """Transcribes filtered audio with multi-language fallback and handles continuous turns."""
        try:
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
            
            # Fast recognition: Indian English primary, Hindi fallback
            transcript = None
            for lang in ["en-IN", "hi-IN"]:
                try:
                    transcript = self.recognizer.recognize_google(audio_data, language=lang)
                    if transcript:
                        break
                except sr.UnknownValueError:
                    continue
                except Exception:
                    break

            if not transcript:
                return

            text = transcript.lower().strip()
            print(f"[WakeWordListener] Captured: '{transcript}'", flush=True)

            # 1. Check for session exit commands
            if self.in_active_session and any(w in text for w in ["bye", "stop", "shant", "quiet", "alvida", "exit", "band karo"]):
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
                # Wake word detected
                self.in_active_session = True
                self._last_active_time = time.time()
                if self.on_wake_chime:
                    self.on_wake_chime()

                parts = text.split(matched_kw, 1)
                trailing_cmd = parts[1].strip() if len(parts) > 1 else ""
                trailing_cmd = trailing_cmd.lstrip(" ,.-")
                print(f"[WakeWordListener] Wake word triggered! Query: '{trailing_cmd}'", flush=True)
                self.on_wake(trailing_cmd)

            elif self.in_active_session:
                # In active continuous conversational session (Gemini Live)
                self._last_active_time = time.time()
                print(f"[WakeWordListener] Conversational Turn: '{text}'", flush=True)
                self.on_wake(text)

        except Exception as e:
            print(f"[WakeWordListener] Utterance note: {e}", flush=True)
