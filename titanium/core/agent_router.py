import os
import re
import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from titanium.config import (
    GEMINI_API_KEY,
    FLASH_LITE_MODEL,
    FLASH_REASONING_MODEL,
    HINGLISH_SYSTEM_PROMPT
)
from titanium.memory.sqlite_memory import MemoryManager
from titanium.tools.app_launcher import WindowsAppLauncher
from titanium.tools.system_navigator import SystemNavigator
from titanium.tools.system_tools import lock_workstation, set_system_volume, get_system_info
from titanium.tools.music_player import TitaniumMusicPlayer
from titanium.core.wake_listener import SHUTDOWN_TRIGGERS

# Common desktop apps for zero-latency local dispatch
FAST_APP_NAMES = [
    "calculator", "calc", "spotify", "chrome", "notepad",
    "vscode", "code", "settings", "task manager", "taskmgr",
    "explorer", "file explorer", "cmd", "powershell", "edge", "camera"
]

class AgentRouter:
    """Intelligent Model Router with Zero-Latency Local Action Dispatch."""

    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()
        self.music_player = TitaniumMusicPlayer.get_instance()
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.chat = None
        self._init_chat()

    def _init_chat(self):
        """Initializes continuous chat session for conversational Gemini Live feel."""
        try:
            self.chat = self.client.chats.create(
                model=FLASH_LITE_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=self._build_system_instruction(),
                    temperature=0.6
                )
            )
        except Exception as e:
            print(f"[AgentRouter] Chat session init note: {e}")

    def _build_system_instruction(self) -> str:
        memory_context = self.memory.get_context_prompt()
        base = HINGLISH_SYSTEM_PROMPT + "\nKeep your spoken replies short, natural, and snappy (1 to 2 sentences) for real-time live conversation."
        if memory_context:
            return f"{base}\n\n{memory_context}"
        return base

    def handle_user_query(self, user_text: str) -> str:
        """Processes query with instant local app dispatch + Gemini Live conversational response."""
        self.memory.add_message("user", user_text)
        lower = user_text.lower().strip()

        # 0. Headless In-Process Music Controls (Zero External Apps / Windows)
        is_music_stop = any(w in lower for w in [
            "pause music", "stop music", "pause song", "stop song",
            "music pause", "music stop", "gaana roko", "music roko",
            "gaana pause", "music pause karo", "gaana band karo", "music band karo",
            "song band karo", "pause playback", "stop playback"
        ])
        if is_music_stop:
            if "pause" in lower:
                self.music_player.pause()
                reply = "Maine music pause kar diya hai."
            else:
                self.music_player.stop()
                reply = "Maine music band kar diya hai."
            self.memory.add_message("assistant", reply, model="music-player")
            return reply

        is_music_resume = any(w in lower for w in [
            "resume music", "continue music", "unpause music", "music resume",
            "music continue", "gaana wapas chalao", "gaana chalu karo", "music play karo"
        ])
        if is_music_resume:
            self.music_player.resume()
            reply = "Maine music resume kar diya hai."
            self.memory.add_message("assistant", reply, model="music-player")
            return reply

        if any(w in lower for w in ["music volume", "song volume", "playback volume"]):
            numbers = re.findall(r"\d+", lower)
            if numbers:
                target_vol = int(numbers[0])
                self.music_player.set_volume(target_vol)
                reply = f"Maine music volume {target_vol}% set kar diya hai."
                self.memory.add_message("assistant", reply, model="music-player")
                return reply

        # Check Play Music Intent
        is_music_play = (
            lower.startswith("play ")
            or any(w in lower for w in [
                "play music", "play a song", "play some music", "play song",
                "gaana bajao", "gaane bajao", "music bajao", "gaana chalao", "gaane chalao", "music chalao",
                "song play karo", "music play karo", "bajao", "gaana sunao"
            ])
        ) and not any(w in lower for w in ["close", "band karo", "shut", "exit"]) and not any(neg in lower for neg in ["don't", "dont", "mat chalao", "nahi"])

        if is_music_play:
            song_query = lower
            for phrase in [
                "play music", "play a song", "play some music", "play song", "play track", "play",
                "gaana bajao", "gaane bajao", "music bajao", "gaana chalao", "gaane chalao", "music chalao",
                "song play karo", "music play karo", "gaana sunao", "chalao", "bajao",
                "on spotify", "on youtube", "karo", "please", "for me", "in background"
            ]:
                song_query = re.sub(rf"\b{re.escape(phrase)}\b", "", song_query)

            song_query = re.sub(r"\s+", " ", song_query).strip(" ,.-")
            if not song_query or song_query.lower() in ["music", "song", "gaana", "songs"]:
                song_query = "lofi hip hop radio beats"
                display_name = "Lofi Chill Beats"
            else:
                display_name = song_query.title()

            self.music_player.play(song_query)
            reply = f"Haanji! Maine '{display_name}' play karna start kar diya hai."
            self.memory.add_message("assistant", reply, model="music-player")
            return reply

        # 0. Self-Shutdown Detection ("Titanium turn yourself off", "shut down", etc.)
        if any(w in lower for w in SHUTDOWN_TRIGGERS):
            return "SHUTDOWN_REQUESTED"

        # 1. Close Intent Detection (Apps, Tabs, Windows)
        is_close_intent = any(w in lower for w in [
            "close", "band karo", "band kar do", "shut", "kill", "terminate", "exit", "hata do", "hatao"
        ])
        if is_close_intent:
            # Check specific apps to close
            for app_name in FAST_APP_NAMES:
                if app_name in lower:
                    res = SystemNavigator.close_app(app_name)
                    clean_name = app_name.capitalize()
                    reply = f"Maine {clean_name} close kar diya hai."
                    self.memory.add_message("assistant", reply, model="local-fast-tool")
                    return reply

            # Check if active tab or window
            if "tab" in lower:
                SystemNavigator.close_active_window_or_tab(is_tab=True)
                reply = "Maine active tab close kar diya hai."
                self.memory.add_message("assistant", reply, model="local-fast-tool")
                return reply
            elif any(w in lower for w in ["window", "screen", "app"]):
                SystemNavigator.close_active_window_or_tab(is_tab=False)
                reply = "Maine window close kar diya hai."
                self.memory.add_message("assistant", reply, model="local-fast-tool")
                return reply

        # 2. Native Settings App Launcher (Windows, macOS, Linux)
        if any(w in lower for w in ["open settings", "settings kholo", "show settings", "launch settings", "system settings"]):
            res = SystemNavigator.open_settings()
            reply = "Haanji! Maine Settings app open kar diya hai."
            self.memory.add_message("assistant", reply, model="system-navigator")
            return reply

        # 3. Folder & File Explorer Navigation
        is_folder_intent = any(w in lower for w in [
            "folder", "directory", "downloads", "documents", "desktop",
            "pictures", "projects", "explorer", "finder", "files"
        ]) and any(w in lower for w in ["open", "kholo", "chalao", "show", "launch"]) and not is_close_intent
        
        if is_folder_intent:
            res = SystemNavigator.open_folder(lower)
            reply = f"Maine {res.get('message', 'folder open')} kar diya hai."
            self.memory.add_message("assistant", reply, model="system-navigator")
            return reply

        # 4. Open Specific File
        if any(w in lower for w in ["open file", "file kholo", "file open karo"]) and not is_close_intent:
            target_file = re.sub(r"(open file|file kholo|file open karo|please)", "", lower).strip()
            if target_file:
                res = SystemNavigator.open_file(target_file)
                reply = f"Maine {res.get('message', target_file)} handle kar diya hai."
                self.memory.add_message("assistant", reply, model="system-navigator")
                return reply

        # 5. Zero-Latency Cross-Platform App Launch Detection (< 10ms execution)
        is_launch_intent = (
            any(w in lower for w in ["open", "launch", "chalao", "kholo", "start", "run"])
            and not is_close_intent
            and not any(neg in lower for neg in ["don't", "dont", "didn't", "did not", "mat kholo", "nahi"])
        )
        if is_launch_intent:
            for app_name in FAST_APP_NAMES:
                if app_name in lower:
                    res = SystemNavigator.launch_app(app_name)
                    print(f"[AgentRouter] Fast launched: {app_name} -> {res}")
                    clean_name = app_name.capitalize()
                    reply = f"Haanji! Maine {clean_name} open kar diya hai."
                    self.memory.add_message("assistant", reply, model="local-fast-tool")
                    return reply

        # 6. Zero-Latency Windows System Controls
        if any(w in lower for w in ["lock pc", "lock computer", "lock screen", "pc lock karo"]):
            lock_workstation()
            reply = "Maine PC lock kar diya hai."
            self.memory.add_message("assistant", reply, model="local-fast-tool")
            return reply

        # 7. Conversational Live Response via Gemini Flash Lite (sub-second response)
        try:
            if not self.chat:
                self._init_chat()

            response = self.chat.send_message(user_text)
            answer = response.text or "Ji, main sun raha hoon."
            self.memory.add_message("assistant", answer, model=FLASH_LITE_MODEL)
            return answer
        except Exception as e:
            print(f"[AgentRouter] Chat error: {e}, falling back to single turn")

        # Fallback single generation
        try:
            res = self.client.models.generate_content(
                model=FLASH_LITE_MODEL,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=self._build_system_instruction(),
                    temperature=0.6
                )
            )
            ans = res.text or "Maine samajh liya hai."
            self.memory.add_message("assistant", ans, model=FLASH_LITE_MODEL)
            return ans
        except Exception as e:
            return f"Error: {e}"

    def analyze_image_crop(self, image_bytes: bytes, user_query: str = "Is image mein kya dikh raha hai?") -> str:
        """Circle to Search vision analysis using Gemini Flash."""
        try:
            part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            prompt = f"{user_query}\nAnswer in natural, clear Hinglish (2-3 sentences max). Highlight key elements found."
            response = self.client.models.generate_content(
                model=FLASH_REASONING_MODEL,
                contents=[part, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self._build_system_instruction(),
                    temperature=0.4
                )
            )
            res = response.text or "Maine image analyze kiya, lekin koi clear details nahi mili."
            self.memory.add_message("assistant", f"[Circle to Search]: {res}", model=FLASH_REASONING_MODEL)
            return res
        except Exception as e:
            # Fallback to flash-lite if flash 503
            try:
                part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                response = self.client.models.generate_content(
                    model=FLASH_LITE_MODEL,
                    contents=[part, user_query],
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_system_instruction(),
                        temperature=0.4
                    )
                )
                return response.text or "Image analyze ho gayi hai."
            except Exception as e2:
                return f"Vision error: {str(e2)}"
