import os
import io
import time
import wave
import threading
from typing import Optional, Callable
import numpy as np
import requests
import pygame

from titanium.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_NAME, ELEVENLABS_MODEL_ID

# Initialize pygame audio mixer once globally
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
except Exception as e:
    print(f"[ElevenLabsTTS] Pygame mixer init warning: {e}")

# Exact community voice ID for "Viraj - Rich, Confident and Expressive"
VIRAJ_VOICE_ID = "3AMU7jXQuQa3oRvRqUmb"
# Default high-quality fallback voice present in user account
FALLBACK_VOICE_ID = "IKne3meq5aSn9XLyUdCD" # Charlie - Deep, Confident, Energetic

class ElevenLabsTTS:
    """Streams Hinglish speech via ElevenLabs API using in-process audio (zero console popups)."""

    def __init__(self, api_key: Optional[str] = None, voice_name: str = ELEVENLABS_VOICE_NAME):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.voice_name = voice_name
        self.model_id = ELEVENLABS_MODEL_ID or "eleven_multilingual_v2"
        self._voice_id: Optional[str] = None
        self._is_speaking = False
        self._fallback_mode = False
        self._cached_chime: Optional[pygame.mixer.Sound] = None
        self._init_chime()

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
        self._voice_id = None
        self._fallback_mode = False

    def resolve_voice_id(self) -> str:
        if self._voice_id:
            return self._voice_id
        if self._fallback_mode:
            return FALLBACK_VOICE_ID
        if not self.api_key:
            return FALLBACK_VOICE_ID

        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": self.api_key}
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                voices = resp.json().get("voices", [])
                for v in voices:
                    if "viraj" in v.get("name", "").lower():
                        self._voice_id = v.get("voice_id")
                        return self._voice_id
        except Exception:
            pass

        return VIRAJ_VOICE_ID

    def speak_text(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        """Asynchronously converts text to speech and plays it in-process with zero popups."""
        threading.Thread(
            target=self._speak_worker,
            args=(text, on_start, on_finish),
            daemon=True
        ).start()

    def _speak_worker(self, text: str, on_start, on_finish):
        if not text or not text.strip():
            return

        clean_text = self._sanitize_text(text)
        if not clean_text:
            return

        if not self.api_key:
            print("[ElevenLabsTTS] Notice: ELEVENLABS_API_KEY is not set.")
            return

        target_voice_id = self.resolve_voice_id()
        audio_data = self._request_tts_audio(clean_text, target_voice_id)

        # Fallback if community Viraj needs VoiceLab add
        if not audio_data and target_voice_id == VIRAJ_VOICE_ID:
            self._fallback_mode = True
            audio_data = self._request_tts_audio(clean_text, FALLBACK_VOICE_ID)

        if audio_data:
            try:
                self._is_speaking = True
                if on_start:
                    on_start()

                # Play in-memory with pygame (no temporary files, no powershell subprocess!)
                bio = io.BytesIO(audio_data)
                pygame.mixer.music.load(bio)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy() and self._is_speaking:
                    time.sleep(0.04)

            except Exception as e:
                print(f"[ElevenLabsTTS] In-process playback error: {e}")
            finally:
                self._is_speaking = False
                if on_finish:
                    on_finish()

    def _request_tts_audio(self, text: str, voice_id: str) -> Optional[bytes]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80
            }
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.content
            else:
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

    def stop_speaking(self):
        """Immediately interrupts speech."""
        self._is_speaking = False
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def is_speaking(self) -> bool:
        return self._is_speaking
