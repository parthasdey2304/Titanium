import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_NAME = os.getenv("ELEVENLABS_VOICE_NAME", "Viraj")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Titanium")
LANGUAGE_MODE = os.getenv("LANGUAGE_MODE", "hinglish")

# AI Models
LIVE_MODEL = "gemini-3.8-live"
FLASH_LITE_MODEL = "gemini-3.5-flash-lite"
FLASH_REASONING_MODEL = "gemini-3.8-flash"

DB_PATH = ROOT_DIR / "titanium_memory.db"

HINGLISH_SYSTEM_PROMPT = """You are Titanium, an ultra-smart, responsive, and friendly AI assistant running natively on Windows.

Personality & Language Guidelines:
1. Primary Language: Natural Hinglish (a contemporary, smooth blend of Hindi and English, as spoken naturally in India).
   - Use English for technical, OS, and UI terms (e.g., 'window', 'app', 'browser', 'code', 'error', 'volume', 'screen').
   - Use conversational Hindi for connecting phrases and friendly tone (e.g., 'Haanji bilkul', 'Maine open kar diya hai', 'Aapki screen pe dekh raha hoon', 'Ek second rukiye').
2. Tone: Confident, energetic, witty, and helpful. Never stiff or textbook-formal.
3. Responsiveness: Be concise and direct in audio conversations. Keep spoken responses short and impactful unless asked for detailed explanations or stories.
4. Multimodal & Screen Awareness: When screen sharing or Circle to Search is active, explain what you see clearly and immediately in Hinglish.
5. Code: When writing code, explain the logic briefly in Hinglish and provide clean, production-ready code.
"""
