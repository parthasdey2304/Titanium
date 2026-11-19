# 🌌 Titanium — Autonomous Agentic Virtual Assistant

**Titanium** is an ultra-lightweight, hardware-accelerated desktop assistant featuring an animated Siri-like floating orb, Google Gemini AI intelligence, real-time screen vision, ElevenLabs speech synthesis in natural **Hinglish** (Viraj voice), always-on microphone with **"Hey Titanium"** wake word detection, continuous conversational sessions, and instant **Circle to Search**.

---

## ✨ Key Features

- **Bottom-Left Siri Orb UI (`PySide6`)**:
  - Transparent, frameless circular widget docked at the bottom-left of the screen (keeping the Windows Action Center completely clear).
  - 4 distinct animated states with organic plasma & specular glass:
    1. **Listening**: Dynamic acoustic shockwaves & electric cyan-azure pulses.
    2. **Thinking**: Swirling dual-vortex cosmic nebula.
    3. **Speaking**: Voice-amplitude reactive coral & amber bounce.
    4. **Seeing (Vision)**: Cyber emerald scanner eye with targeting reticle during Screen Share and Circle to Search.
  - Fully draggable anywhere on your multi-monitor setup.
  - Left-click to instantly toggle live listening.
- **Always-On Device Microphone & Wake Word ("Hey Titanium")**:
  - Continuously listens in a low-power background thread (<1% CPU, ~0% idle).
  - Dynamic noise-floor calibration auto-tunes to your laptop's microphone array.
  - Futuristic rising audio chime confirms wake-word detection (<10ms).
- **Continuous Live Sessions (Google Gemini Live Style)**:
  - Once activated, enjoy back-to-back continuous dialogue without repeating "Hey Titanium" before every request.
  - Say *"bye"*, *"stop"*, or click the Orb to finish a session.
- **ElevenLabs Speech Synthesis**:
  - Voice configured to **Viraj** (*Rich, Confident and Expressive — Hindi Standard*) via `eleven_multilingual_v2`.
  - In-process hardware-accelerated audio streaming via `pygame.mixer` (zero console popups).
  - Built-in graceful fallback to account voices.
- **Universal Cross-Platform System Navigator (Windows, macOS, Linux)**:
  - **Native Settings Launcher**: Opens Windows Settings (`ms-settings:`), macOS System Settings, or Linux control center.
  - **Explorer & Folder Navigation**: Directly opens Downloads, Documents, Desktop, Pictures, and Projects in native file managers.
  - **Smart File Opener**: Finds and opens requested files using the system default handler.
  - **Zero-Latency App Launching**: Sub-10ms launching of desktop apps (*Calculator, Spotify, Chrome, VS Code, Notepad, etc.*).
- **Circle to Search (`Ctrl + Shift + S`)**:
  - Translucent sniper overlay allowing rectangular or lasso selection of any screen region.
  - Immediately analyzes images, charts, code errors, or text with Gemini Vision.
- **Real-Time Screen Share (Gemini 3.8 Live)**:
  - Streams your screen at 1 FPS into Gemini Live for real-time visual assistance.
- **Ultra-Low Memory Footprint**:
  - **~58 MB active RAM** with zero electron bloat.
  - Persistent SQLite memory (`titanium_memory.db`) for preferences and conversation context.
- **Windows System Integration**:
  - Windows Start Menu shortcut (search "Titanium" to launch).
  - Task Manager Startup integration (starts automatically with your PC).

---

## 🚀 Quick Start

### 1. Installation
Clone the repository:
```bash
git clone https://github.com/parthasdey2304/Titanium.git
cd Titanium
```

Setup virtual environment and install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your API keys:
```ini
# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# ElevenLabs Voice Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_NAME=Viraj
ELEVENLABS_MODEL_ID=eleven_multilingual_v2

# Assistant Personality & Language
ASSISTANT_NAME=Titanium
LANGUAGE_MODE=hinglish
```

### 3. Running Titanium
Double-click:
- **`run_titanium.bat`**: Runs silently in the background with the Siri Orb and system tray icon.
- **`run_titanium_console.bat`**: Runs with terminal output for debugging.

To install Titanium into Windows Start Menu and Task Manager Startup, double-click **`install_titanium.bat`** (or right-click the Orb and select *"Install to System"*).

---

## 🎮 Controls & Shortcuts

| Action | Shortcut / Trigger |
| :--- | :--- |
| **Wake Assistant** | Speak *"Hey Titanium"* or Left-Click the Orb |
| **Circle to Search** | <kbd>Ctrl + Shift + S</kbd> or Double-Click the Orb |
| **Move Orb** | Click and Drag with Left Mouse Button |
| **Quick Actions Menu** | Right-Click the Orb (Screen Share, Ask, Install, Reset) |
| **End Live Session** | Speak *"bye"*, *"stop"*, or Left-Click the Orb |

---

## 📄 License
Apache License 2.0. See [LICENSE](LICENSE) for details.
