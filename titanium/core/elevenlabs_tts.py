import os
import io
import time
import wave
import asyncio
import threading
from typing import Optional, Callable
import numpy as np
import requests
import pygame

from titanium.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_NAME, ELEVENLABS_MODEL_ID

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

# Initialize pygame audio mixer once globally
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
except Exception as e:
    print(f"[ElevenLabsTTS] Pygame mixer init warning: {e}")

# High-quality premade voice available on all tiers (Charlie - Deep, Confident, Energetic)
DEFAULT_VOICE_ID = "IKne3meq5aSn9XLyUdCD"
FALLBACK_VOICE_ID = "IKne3meq5aSn9XLyUdCD"
# Consistent free neural voice used whenever ElevenLabs key is absent or quota is exhausted
EDGE_NEURAL_VOICE = "en-IN-PrabhatNeural"


class ElevenLabsTTS:
    """Streams Hinglish speech consistently via ElevenLabs API or Edge Neural TTS (never flip-flops voices mid-session)."""

    def __init__(self, api_key: Optional[str] = None, voice_name: str = ELEVENLABS_VOICE_NAME):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.voice_name = voice_name
        self.model_id = ELEVENLABS_MODEL_ID or "eleven_flash_v2_5"
        self._voice_id: Optional[str] = DEFAULT_VOICE_ID
        self._is_speaking = False
        # Latched once per session on 401/402/403/quota_exceeded so voice stays 100% consistent
        self._elevenlabs_locked_out = False
        self._speech_seq = 0
        self._state_lock = threading.Lock()
        self._playback_lock = threading.Lock()
        self._cached_chime: Optional[pygame.mixer.Sound] = None
        self._init_chime()
        self._precheck_elevenlabs_quota()

    def _precheck_elevenlabs_quota(self):
        """Checks ElevenLabs remaining credits upfront in a quick non-blocking probe
        so we never flip-flop from ElevenLabs on greeting to fallback on reply #2."""
        if not self.api_key:
            self._elevenlabs_locked_out = True
            return

        def check():
            try:
                r = requests.get(
                    "https://api.elevenlabs.io/v1/user/subscription",
                    headers={"xi-api-key": self.api_key},
                    timeout=3,
                )
                if r.status_code in (401, 402, 403):
                    self._elevenlabs_locked_out = True
                    print("[ElevenLabsTTS] API key rejected during precheck; locking to consistent Neural voice.")
                elif r.status_code == 200:
                    data = r.json()
                    used = data.get("character_count", 0)
                    limit = data.get("character_limit", 0)
                    if limit > 0 and (limit - used) < 40:
                        self._elevenlabs_locked_out = True
                        print(f"[ElevenLabsTTS] ElevenLabs quota exhausted ({used}/{limit}); locking to consistent Neural voice.")
            except Exception:
                pass

        threading.Thread(target=check, daemon=True).start()

    def _init_chime(self):
        """Generates a pleasant 2-tone futuristic rising chime in memory."""
        try:
            fs = 22050
            t1 = np.linspace(0, 0.08, int(fs * 0.08), False)
            t2 = np.linspace(0, 0.12, int(fs * 0.12), False)
            tone1 = np.sin(2 * np.pi * 587.33 * t1) * np.linspace(0.8, 1.0, len(t1))
            tone2 = np.sin(2 * np.pi * 880.00 * t2) * np.linspace(1.0, 0.0, len(t2))
            tone = np.concatenate([tone1, tone2])
            audio = (tone * 0.35 * 32767).astype(np.int16)

            bio = io.BytesIO()
            with wave.open(bio, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(fs)
                wf.writeframes(audio.tobytes())
            bio.seek(0)
            self._cached_chime = pygame.mixer.Sound(bio)
        except Exception as e:
            print(f"[ElevenLabsTTS] Chime generation error: {e}")

    def play_wake_chime(self):
        """Plays instant wake sound (<10ms latency)."""
        if self._cached_chime:
            try:
                self._cached_chime.play()
            except Exception:
                pass

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._voice_id = DEFAULT_VOICE_ID
        self._elevenlabs_locked_out = not bool(api_key)
        self._precheck_elevenlabs_quota()

    def resolve_voice_id(self) -> str:
        if self._voice_id:
            return self._voice_id
        return DEFAULT_VOICE_ID

    def speak_text(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        """Asynchronously converts text to speech and plays it in-process without overlap."""
        with self._state_lock:
            self._speech_seq += 1
            seq = self._speech_seq
            self._stop_active_audio_only()

        threading.Thread(
            target=self._speak_worker,
            args=(seq, text, on_start, on_finish),
            daemon=True
        ).start()

    def _speak_worker(self, seq: int, text: str, on_start, on_finish):
        if not text or not text.strip():
            if on_finish:
                on_finish()
            return

        clean_text = self._sanitize_text(text)
        if not clean_text:
            if on_finish:
                on_finish()
            return

        if not self.api_key:
            self.api_key = os.getenv("ELEVENLABS_API_KEY", "")

        # Bail early if already superseded before network work
        if seq != self._speech_seq:
            return

        audio_data = None
        if self.api_key and not self._elevenlabs_locked_out:
            target_voice_id = self.resolve_voice_id()
            audio_data = self._request_tts_audio(clean_text, target_voice_id)

            if not audio_data and not self._elevenlabs_locked_out and target_voice_id != FALLBACK_VOICE_ID:
                self._voice_id = FALLBACK_VOICE_ID
                audio_data = self._request_tts_audio(clean_text, FALLBACK_VOICE_ID)

        if seq != self._speech_seq:
            return

        # Consistent high-quality Edge Neural TTS when ElevenLabs is unconfigured or out of quota
        if not audio_data and HAS_EDGE_TTS:
            audio_data = self._request_edge_tts_audio(clean_text)

        if seq != self._speech_seq:
            return

        if audio_data:
            with self._playback_lock:
                if seq != self._speech_seq:
                    return
                try:
                    self._is_speaking = True
                    if on_start:
                        on_start()

                    bio = io.BytesIO(audio_data)
                    pygame.mixer.music.load(bio)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy() and self._is_speaking and seq == self._speech_seq:
                        time.sleep(0.03)
                except Exception as e:
                    print(f"[ElevenLabsTTS] In-process playback error: {e}")
                finally:
                    self._is_speaking = False
                    if seq == self._speech_seq and on_finish:
                        on_finish()
        else:
            # Final offline fallback (Windows SAPI5) if completely disconnected
            with self._playback_lock:
                if seq != self._speech_seq:
                    return
                self._speak_native_sapi(seq, clean_text, on_start, on_finish)

    def _request_edge_tts_audio(self, text: str) -> Optional[bytes]:
        """Synthesizes consistent warm Indian English / Hinglish speech via Edge Neural TTS."""
        try:
            async def _synth():
                comm = edge_tts.Communicate(text, EDGE_NEURAL_VOICE)
                chunks = []
                async for chunk in comm.stream():
                    if chunk.get("type") == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)

            loop = asyncio.new_event_loop()
            try:
                audio = loop.run_until_complete(_synth())
            finally:
                loop.close()
            return audio if audio else None
        except Exception as e:
            print(f"[ElevenLabsTTS] Edge Neural TTS failed: {e}")
            return None

    def _speak_native_sapi(self, seq: int, text: str, on_start, on_finish):
        """Offline zero-dependency Windows TTS fallback."""
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self._is_speaking = True
            if on_start:
                on_start()
            if seq == self._speech_seq:
                speaker.Speak(text, 0)
        except Exception as e:
            print(f"[ElevenLabsTTS] SAPI fallback error: {e}")
        finally:
            self._is_speaking = False
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
            if seq == self._speech_seq and on_finish:
                on_finish()

    def _request_tts_audio(self, text: str, voice_id: str) -> Optional[bytes]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=3&output_format=mp3_44100_128"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": self.model_id or "eleven_flash_v2_5",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80
            }
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=6)
            if response.status_code == 200:
                return response.content
            if response.status_code in (401, 402, 403):
                # Lock out for session so voice never alternates mid-conversation
                self._elevenlabs_locked_out = True
            print(f"[ElevenLabsTTS] Error ({response.status_code}): {response.text}")
            return None
        except Exception as e:
            print(f"[ElevenLabsTTS] Request failed: {e}")
            return None

    def _sanitize_text(self, text: str) -> str:
        """Removes code blocks and excessive markdown before sending to TTS."""
        import re
        cleaned = re.sub(r"```[\s\S]*?```", " maine code block screen par display kar diya hai. ", text)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = cleaned.replace("*", "").replace("#", "")
        if len(cleaned) > 350:
            cleaned = cleaned[:350] + "... baaki details maine screen par show kar di hain."
        return cleaned.strip()

    def _stop_active_audio_only(self):
        self._is_speaking = False
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak("", 2)  # SVSFPurgeBeforeSpeak
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def stop_speaking(self):
        """Immediately interrupts active speech and cancels pending playback."""
        with self._state_lock:
            self._speech_seq += 1
            self._stop_active_audio_only()

    def is_speaking(self) -> bool:
        return self._is_speaking
