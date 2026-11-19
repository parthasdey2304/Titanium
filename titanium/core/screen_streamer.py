import io
import time
import threading
from typing import Callable, Optional
import mss
from PIL import Image

class ScreenStreamer:
    """Captures desktop screen frames at 1 FPS for Gemini Live multimodal vision."""

    def __init__(self, fps: float = 1.0, quality: int = 70):
        self.interval = 1.0 / max(0.2, fps)
        self.quality = quality
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_callback: Optional[Callable[[bytes], None]] = None

    def start(self, frame_callback: Callable[[bytes], None]):
        """Starts background screen capture loop."""
        if self._running:
            return
        self._frame_callback = frame_callback
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("[ScreenStreamer] Screen sharing started at ~1 FPS.")

    def stop(self):
        """Stops screen capture."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        print("[ScreenStreamer] Screen sharing stopped.")

    def is_running(self) -> bool:
        return self._running

    def _capture_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Primary display
            while self._running:
                start_time = time.time()
                try:
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    # Resize to 1280x720 max for low latency & memory
                    img.thumbnail((1280, 720))
                    
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=self.quality, optimize=True)
                    jpeg_bytes = buf.getvalue()

                    if self._frame_callback and self._running:
                        self._frame_callback(jpeg_bytes)
                except Exception as e:
                    print(f"[ScreenStreamer] Capture error: {e}")

                elapsed = time.time() - start_time
                sleep_time = max(0.05, self.interval - elapsed)
                time.sleep(sleep_time)

    @staticmethod
    def capture_fullscreen() -> bytes:
        """Captures a single full-resolution screenshot (PNG bytes) for Circle to Search."""
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
