import asyncio
import threading
from typing import Optional, Callable
from google import genai
from google.genai import types

from titanium.config import GEMINI_API_KEY, LIVE_MODEL, HINGLISH_SYSTEM_PROMPT
from titanium.core.screen_streamer import ScreenStreamer
from titanium.core.elevenlabs_tts import ElevenLabsTTS

class GeminiLiveClient:
    """Manages real-time bidirectional WebSocket session with Gemini 3.8 Live:
    - Streams mic audio / text to Gemini Live
    - Streams screen frames (1 FPS) when screen share is toggled
    - Speaks response using ElevenLabs 'Viraj' voice (or native audio)
    """

    def __init__(self, tts: Optional[ElevenLabsTTS] = None):
        self.tts = tts or ElevenLabsTTS()
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.screen_streamer = ScreenStreamer(fps=1.0)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session = None
        self._is_connected = False
        self._worker_thread: Optional[threading.Thread] = None
        self.on_state_change: Optional[Callable[[str], None]] = None # 'idle', 'listening', 'thinking', 'speaking'

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
            response_modalities=[types.Modality.TEXT], # We use ElevenLabs Viraj for TTS
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
                print("[GeminiLiveClient] Connected to Gemini 3.8 Live.")
                if self.on_state_change:
                    self.on_state_change("listening")

                # Receive loop
                accumulated_text = []
                async for response in session.receive():
                    server_content = response.server_content
                    if server_content is not None and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if part.text:
                                accumulated_text.append(part.text)

                    if server_content and server_content.turn_complete:
                        full_reply = "".join(accumulated_text).strip()
                        accumulated_text = []
                        if full_reply:
                            print(f"[GeminiLive] {full_reply}")
                            # Speak with ElevenLabs Viraj voice
                            self.tts.speak_text(
                                full_reply,
                                on_start=lambda: self.on_state_change("speaking") if self.on_state_change else None,
                                on_finish=lambda: self.on_state_change("listening") if self.on_state_change else None
                            )

        except Exception as e:
            print(f"[GeminiLiveClient] Live connection error: {e}")
        finally:
            self._is_connected = False
            self._session = None
            if self.on_state_change:
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
