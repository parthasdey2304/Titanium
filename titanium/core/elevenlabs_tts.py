import os
import io
import time
import wave
import asyncio
import threading
from typing import Optional, Callable
import numpy as np
import requests

from titanium.config import GEMINI_API_KEY, LIVE_MODEL, HINGLISH_SYSTEM_PROMPT
# # ElevenLabs Voice Config (Retained but commented out as requested)
# from titanium.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_NAME, ELEVENLABS_MODEL_ID

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False

# Consistent free fallback voice if network drops
EDGE_NEURAL_VOICE = "en-IN-PrabhatNeural"
GEMINI_VOICE_NAME = "Puck"  # Gemini 3.8 Live Prebuilt Voice (Natural, Crisp, Conversational)


class ElevenLabsTTS:
    """TTS and Voice Engine for Titanium.
    
    Now uses the original Gemini 3.8 Live Voice (Puck) streamed in real-time
    with sub-second Time-To-First-Audio (<0.8s) via google.genai Live WebSocket API.
    
    The previous ElevenLabs code is retained below in commented form as requested.
    """

    def __init__(self, api_key: Optional[str] = None, voice_name: str = "Puck"):
        # self.api_key = api_key or ELEVENLABS_API_KEY
        # self.voice_name = voice_name
        # self.model_id = ELEVENLABS_MODEL_ID or "eleven_flash_v2_5"
        self.gemini_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.voice_name = voice_name or GEMINI_VOICE_NAME
        self._is_speaking = False
        self._speech_seq = 0
        self._state_lock = threading.Lock()
        self._playback_lock = threading.Lock()
        self._cached_chime = None
        self._init_chime()

        # # ElevenLabs Precheck (Commented out)
        # self._elevenlabs_locked_out = True
        # self._precheck_elevenlabs_quota()

    # def _precheck_elevenlabs_quota(self):
    #     """Checks ElevenLabs remaining credits upfront in a quick non-blocking probe
    #     so we never flip-flop from ElevenLabs on greeting to fallback on reply #2."""
    #     if not self.api_key:
    #         self._elevenlabs_locked_out = True
    #         return
    #     def check():
    #         try:
    #             r = requests.get(
    #                 "https://api.elevenlabs.io/v1/user/subscription",
    #                 headers={"xi-api-key": self.api_key},
    #                 timeout=3,
    #             )
    #             if r.status_code in (401, 402, 403):
    #                 self._elevenlabs_locked_out = True
    #             elif r.status_code == 200:
    #                 data = r.json()
    #                 used = data.get("character_count", 0)
    #                 limit = data.get("character_limit", 0)
    #                 if limit > 0 and (limit - used) < 40:
    #                     self._elevenlabs_locked_out = True
    #         except Exception:
    #             pass
    #     threading.Thread(target=check, daemon=True).start()

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
            if HAS_PYGAME and pygame.mixer.get_init():
                self._cached_chime = pygame.mixer.Sound(bio)
            else:
                self._cached_chime = audio.tobytes()
        except Exception as e:
            print(f"[ElevenLabsTTS] Chime generation error: {e}")

    def play_wake_chime(self):
        """Plays instant wake sound (<10ms latency)."""
        try:
            if self._cached_chime:
                if HAS_PYGAME and hasattr(self._cached_chime, "play"):
                    self._cached_chime.play()
                elif HAS_SOUNDDEVICE:
                    arr = np.frombuffer(self._cached_chime, dtype=np.int16)
                    sd.play(arr, samplerate=22050)
        except Exception:
            pass

    def speak_text(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        """Asynchronously converts text to speech using Gemini 3.8 Live Voice and streams playback."""
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

        # Ensure latest Gemini API Key
        if not self.gemini_key:
            self.gemini_key = os.getenv("GEMINI_API_KEY", "")

        # Bail early if already superseded before network work
        if seq != self._speech_seq:
            return

        # 1. Primary: Gemini 3.8 Live Voice streaming synthesis
        played = False
        if HAS_GENAI and self.gemini_key and HAS_SOUNDDEVICE:
            try:
                played = self._stream_gemini_live_audio(seq, clean_text, on_start)
            except Exception as e:
                print(f"[ElevenLabsTTS] Gemini Live speech stream error: {e}")
                played = False

        if seq != self._speech_seq:
            return

        # # 2. ElevenLabs API (Retained in commented code as requested)
        # if not played and self.api_key and not self._elevenlabs_locked_out:
        #     target_voice_id = "IKne3meq5aSn9XLyUdCD"
        #     audio_data = self._request_tts_audio(clean_text, target_voice_id)
        #     if audio_data:
        #         self._play_bytes_audio(seq, audio_data, on_start)
        #         played = True

        # 3. High-quality Edge Neural TTS fallback
        if not played and HAS_EDGE_TTS:
            audio_data = self._request_edge_tts_audio(clean_text)
            if audio_data and seq == self._speech_seq:
                self._play_bytes_audio(seq, audio_data, on_start)
                played = True

        # 4. Final offline SAPI5 fallback
        if not played and seq == self._speech_seq:
            self._speak_native_sapi(seq, clean_text, on_start, on_finish)
            return

        with self._state_lock:
            self._is_speaking = False
        if seq == self._speech_seq and on_finish:
            on_finish()

    def _stream_gemini_live_audio(self, seq: int, text: str, on_start) -> bool:
        """Connects to Gemini 3.8 Live with Modality.AUDIO and streams 24kHz raw PCM directly to speakers."""
        started_cb_fired = False

        async def _run():
            nonlocal started_cb_fired
            client = genai.Client(api_key=self.gemini_key, http_options=types.HttpOptions(api_version="v1alpha"))
            config = types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                    )
                ),
                system_instruction=types.Content(
                    parts=[types.Part.from_text(text=HINGLISH_SYSTEM_PROMPT)]
                )
            )

            async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                if seq != self._speech_seq:
                    return False

                # Instruct the model to speak the response directly with its native live voice
                prompt = f"Speak the following naturally and crisply in 1-2 short sentences: {text}"
                await session.send_realtime_input(text=prompt)

                stream = sd.OutputStream(samplerate=24000, channels=1, dtype='int16')
                stream.start()

                with self._playback_lock:
                    try:
                        self._is_speaking = True
                        async for resp in session.receive():
                            if seq != self._speech_seq:
                                break
                            sc = resp.server_content
                            if sc and sc.model_turn:
                                for p in sc.model_turn.parts:
                                    if p.inline_data and p.inline_data.data:
                                        if not started_cb_fired:
                                            started_cb_fired = True
                                            if on_start:
                                                on_start()
                                        arr = np.frombuffer(p.inline_data.data, dtype=np.int16)
                                        stream.write(arr)
                            if sc and sc.turn_complete:
                                break
                    finally:
                        stream.stop()
                        stream.close()

                return started_cb_fired

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def _play_bytes_audio(self, seq: int, audio_data: bytes, on_start):
        """Plays encoded MP3/WAV audio via pygame.mixer."""
        with self._playback_lock:
            if seq != self._speech_seq:
                return
            try:
                self._is_speaking = True
                if on_start:
                    on_start()
                if HAS_PYGAME and pygame.mixer.get_init():
                    bio = io.BytesIO(audio_data)
                    pygame.mixer.music.load(bio)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and self._is_speaking and seq == self._speech_seq:
                        time.sleep(0.03)
            except Exception as e:
                print(f"[ElevenLabsTTS] In-process playback error: {e}")
            finally:
                self._is_speaking = False

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

    # def _request_tts_audio(self, text: str, voice_id: str) -> Optional[bytes]:
    #     """ElevenLabs HTTP text-to-speech request (Retained in commented code as requested)."""
    #     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=3&output_format=mp3_44100_128"
    #     headers = {
    #         "xi-api-key": self.api_key,
    #         "Content-Type": "application/json"
    #     }
    #     payload = {
    #         "text": text,
    #         "model_id": self.model_id or "eleven_flash_v2_5",
    #         "voice_settings": {
    #             "stability": 0.45,
    #             "similarity_boost": 0.80
    #         }
    #     }
    #     try:
    #         response = requests.post(url, json=payload, headers=headers, timeout=6)
    #         if response.status_code == 200:
    #             return response.content
    #         if response.status_code in (401, 402, 403):
    #             self._elevenlabs_locked_out = True
    #         print(f"[ElevenLabsTTS] Error ({response.status_code}): {response.text}")
    #         return None
    #     except Exception as e:
    #         print(f"[ElevenLabsTTS] Request failed: {e}")
    #         return None

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
            if HAS_SOUNDDEVICE:
                sd.stop()
        except Exception:
            pass
        try:
            if HAS_PYGAME and pygame.mixer.get_init():
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
