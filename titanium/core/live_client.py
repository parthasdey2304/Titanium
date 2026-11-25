import asyncio
import threading
from typing import Optional, Callable
import numpy as np
from google import genai
from google.genai import types

from titanium.config import GEMINI_API_KEY, LIVE_MODEL, HINGLISH_SYSTEM_PROMPT
from titanium.core.screen_streamer import ScreenStreamer
from titanium.core.elevenlabs_tts import ElevenLabsTTS

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


class GeminiLiveClient:
    """Manages real-time bidirectional WebSocket session with Gemini 3.8 Live:
    - Streams mic audio / text to Gemini Live
    - Streams screen frames (1 FPS) when screen share is toggled
    - Speaks natively with Gemini 3.8 Live's original real-time voice
    """

    def __init__(self, tts: Optional[ElevenLabsTTS] = None):
        self.tts = tts or ElevenLabsTTS()
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(api_version="v1alpha")
        )
        self.screen_streamer = ScreenStreamer(fps=1.0)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session = None
        self._is_connected = False
        self._worker_thread: Optional[threading.Thread] = None
        self.on_state_change: Optional[Callable[[str], None]] = None  # 'idle', 'listening', 'thinking', 'speaking'
        self.on_shutdown: Optional[Callable[[], None]] = None

    def start(self):
        """Starts the Live client event loop in a background thread."""
        if self._is_connected:
            return
        self._worker_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._worker_thread.start()

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],  # Native Gemini 3.8 Live Voice
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=HINGLISH_SYSTEM_PROMPT)]
            )
        )
        try:
            if self.on_state_change:
                self.on_state_change("connecting")

            async with self.client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                self._session = session
                self._is_connected = True
                print("[GeminiLiveClient] Connected to Gemini 3.8 Live with Native Voice.")
                if self.on_state_change:
                    self.on_state_change("listening")

                audio_stream = None
                if HAS_SOUNDDEVICE:
                    audio_stream = sd.OutputStream(samplerate=24000, channels=1, dtype='int16')
                    audio_stream.start()

                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content is not None and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.data and audio_stream:
                                    if self.on_state_change:
                                        self.on_state_change("speaking")
                                    arr = np.frombuffer(part.inline_data.data, dtype=np.int16)
                                    audio_stream.write(arr)

                        if server_content and server_content.turn_complete:
                            if self.on_state_change:
                                self.on_state_change("listening")
                finally:
                    if audio_stream:
                        audio_stream.stop()
                        audio_stream.close()

        except Exception as e:
            print(f"[GeminiLiveClient] Connection note: {e}")
        finally:
            was_connected = self._is_connected
            self._is_connected = False
            self._session = None
            if was_connected and self.on_state_change:
                self.on_state_change("idle")

    def send_text(self, text: str):
        """Sends a text message into the active Live session."""
        if not self._is_connected or not self._loop:
            return
        asyncio.run_coroutine_threadsafe(
            self._send_text_async(text),
            self._loop
        )

    async def _send_text_async(self, text: str):
        if self._session:
            await self._session.send_realtime_input(text=text)

    def toggle_screen_share(self) -> bool:
        """Toggles real-time screen frame streaming into Gemini Live."""
        if self.screen_streamer.is_running():
            self.screen_streamer.stop()
            return False
        else:
            self.screen_streamer.start(frame_callback=self._on_screen_frame)
            return True

    def _on_screen_frame(self, jpeg_bytes: bytes):
        """Callback from ScreenStreamer sending frames to Gemini Live."""
        if self._is_connected and self._session and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._session.send_realtime_input(
                    video=types.RealtimeInput(data=jpeg_bytes, mime_type="image/jpeg")
                ),
                self._loop
            )

    def is_screen_sharing(self) -> bool:
        return self.screen_streamer.is_running()
