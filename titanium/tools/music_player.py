import os
import sys
import time
import queue
import threading
from typing import Optional, Dict, Any, Callable

try:
    import pythoncom
    import win32com.client
    HAS_COM = True
except ImportError:
    HAS_COM = False

try:
    from yt_dlp import YoutubeDL
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False


class TitaniumMusicPlayer:
    """Headless background in-process music player for Titanium.
    Streams and plays audio natively via Windows Media Player COM (WMPlayer.OCX)
    without opening any browser tabs, Spotify, or external GUI windows.
    Supports voice-controlled playback, pausing, resuming, volume control,
    and automatic audio ducking during ElevenLabs TTS speech.
    """

    _instance: Optional["TitaniumMusicPlayer"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TitaniumMusicPlayer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = TitaniumMusicPlayer()
            return cls._instance

    def __init__(self):
        self.cmd_queue = queue.Queue()
        self.current_title: Optional[str] = None
        self.current_url: Optional[str] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.volume: int = 70
        self._saved_volume: Optional[int] = None
        self.on_track_change: Optional[Callable[[str], None]] = None

        self._worker_thread = threading.Thread(target=self._player_loop, daemon=True)
        self._worker_thread.start()

    def _player_loop(self):
        """Dedicated thread with COM Single-Threaded Apartment (STA) for WMPlayer."""
        player = None
        if HAS_COM:
            try:
                pythoncom.CoInitialize()
                player = win32com.client.Dispatch("WMPlayer.OCX")
                player.settings.volume = self.volume
                print("[MusicPlayer] Headless WMPlayer.OCX initialized successfully.")
            except Exception as e:
                print(f"[MusicPlayer] COM initialization error: {e}")

        while True:
            try:
                item = self.cmd_queue.get()
                if item is None:
                    break

                action = item.get("action")
                payload = item.get("payload")

                if not player:
                    print("[MusicPlayer] Player COM object unavailable.")
                    self.cmd_queue.task_done()
                    continue

                if action == "play_stream":
                    url = payload.get("url")
                    title = payload.get("title", "Audio Stream")
                    self.current_title = title
                    self.current_url = url
                    try:
                        player.URL = url
                        player.controls.play()
                        self.is_playing = True
                        self.is_paused = False
                        print(f"[MusicPlayer] Now playing natively: {title}")
                        if self.on_track_change:
                            try:
                                self.on_track_change(title)
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"[MusicPlayer] Playback error: {e}")
                        self.is_playing = False

                elif action == "pause":
                    try:
                        player.controls.pause()
                        self.is_paused = True
                        self.is_playing = False
                        print("[MusicPlayer] Music paused.")
                    except Exception as e:
                        print(f"[MusicPlayer] Pause error: {e}")

                elif action == "resume":
                    try:
                        player.controls.play()
                        self.is_playing = True
                        self.is_paused = False
                        print("[MusicPlayer] Music resumed.")
                    except Exception as e:
                        print(f"[MusicPlayer] Resume error: {e}")

                elif action == "stop":
                    try:
                        player.controls.stop()
                        self.is_playing = False
                        self.is_paused = False
                        self.current_title = None
                        print("[MusicPlayer] Music stopped.")
                    except Exception as e:
                        print(f"[MusicPlayer] Stop error: {e}")

                elif action == "set_volume":
                    vol = max(0, min(100, int(payload)))
                    self.volume = vol
                    try:
                        player.settings.volume = vol
                    except Exception as e:
                        print(f"[MusicPlayer] Volume error: {e}")

                elif action == "duck":
                    # Lower volume during TTS speech
                    duck_vol = max(5, min(100, int(payload or 18)))
                    if self._saved_volume is None:
                        self._saved_volume = self.volume
                    try:
                        player.settings.volume = duck_vol
                    except Exception:
                        pass

                elif action == "restore":
                    # Restore volume after TTS speech ends
                    if self._saved_volume is not None:
                        target = self._saved_volume
                        self._saved_volume = None
                        try:
                            player.settings.volume = target
                        except Exception:
                            pass

                self.cmd_queue.task_done()
            except Exception as e:
                print(f"[MusicPlayer] Worker loop exception: {e}")

    def play(self, query: str, on_resolved: Optional[Callable[[bool, str], None]] = None) -> str:
        """Asynchronously extracts stream and starts headless audio playback.
        Returns immediate confirmation title/query.
        """
        clean_query = query.strip()
        if not clean_query or clean_query.lower() in ["music", "song", "gaana", "songs"]:
            search_query = "lofi hip hop radio beats to relax"
            display_title = "Lofi Chill Beats"
        else:
            search_query = clean_query
            display_title = clean_query.title()

        def extract_and_play():
            if not HAS_YTDLP:
                print("[MusicPlayer] yt-dlp is not installed.")
                if on_resolved:
                    on_resolved(False, "yt-dlp is not installed")
                return

            print(f"[MusicPlayer] Searching audio stream for '{search_query}'...")
            
            # Primary fast extraction using YouTube & SoundCloud
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
                'socket_timeout': 8,
                'retries': 2,
            }

            stream_url = None
            song_title = display_title

            # Try YouTube extraction
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    if info:
                        entry = info['entries'][0] if 'entries' in info and info['entries'] else info
                        stream_url = entry.get('url')
                        song_title = entry.get('title', song_title)
            except Exception as e:
                print(f"[MusicPlayer] YouTube extraction error: {e}")

            # Fallback to SoundCloud if YouTube failed or format unavailable
            if not stream_url:
                try:
                    sc_opts = {
                        'format': 'bestaudio',
                        'noplaylist': True,
                        'quiet': True,
                        'no_warnings': True,
                        'default_search': 'scsearch1',
                        'socket_timeout': 6,
                    }
                    with YoutubeDL(sc_opts) as ydl:
                        info = ydl.extract_info(search_query, download=False)
                        if info:
                            entry = info['entries'][0] if 'entries' in info and info['entries'] else info
                            stream_url = entry.get('url')
                            song_title = entry.get('title', song_title)
                except Exception as sc_e:
                    print(f"[MusicPlayer] SoundCloud extraction fallback note: {sc_e}")

            if stream_url:
                self.cmd_queue.put({
                    "action": "play_stream",
                    "payload": {
                        "url": stream_url,
                        "title": song_title
                    }
                })
                if on_resolved:
                    on_resolved(True, song_title)
            else:
                print(f"[MusicPlayer] Could not extract stream for '{search_query}'")
                if on_resolved:
                    on_resolved(False, f"Song '{search_query}' nahi mila.")

        threading.Thread(target=extract_and_play, daemon=True).start()
        return display_title

    def pause(self) -> str:
        """Pauses currently playing audio."""
        self.cmd_queue.put({"action": "pause", "payload": None})
        return "Music paused."

    def resume(self) -> str:
        """Resumes paused audio."""
        self.cmd_queue.put({"action": "resume", "payload": None})
        return "Music resumed."

    def stop(self) -> str:
        """Stops audio completely."""
        self.cmd_queue.put({"action": "stop", "payload": None})
        return "Music stopped."

    def set_volume(self, vol: int) -> int:
        """Adjusts music volume (0 - 100)."""
        vol = max(0, min(100, int(vol)))
        self.cmd_queue.put({"action": "set_volume", "payload": vol})
        return vol

    def duck_volume(self, level: int = 15):
        """Temporarily drops music volume so TTS or user voice is crystal clear."""
        if self.is_playing:
            self.cmd_queue.put({"action": "duck", "payload": level})

    def restore_volume(self):
        """Restores normal music volume after TTS finishes speaking."""
        if self.is_playing or self._saved_volume is not None:
            self.cmd_queue.put({"action": "restore", "payload": None})

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_track": self.current_title,
            "volume": self.volume
        }
