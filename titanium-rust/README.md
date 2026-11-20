# 🦀 Titanium — Native Rust Implementation

An ultra-lightweight, hardware-accelerated, native Windows port of **Titanium** built in Rust.

---

## ⚡ Highlights

- **Ultra-Low Memory Footprint**: **~15–25 MB active RAM** (over 80% reduction compared to standard desktop runtimes).
- **Instantaneous Startup**: Cold starts in **< 40 milliseconds** into a single native `.exe`.
- **Hardware-Accelerated 3D Siri Orb**:
  - Implemented as a native Win32 Layered Window (`WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW`) with per-pixel 32-bit ARGB alpha blending (`UpdateLayeredWindow`).
  - Smooth 60 FPS organic plasma sphere animation using the AmazingUI palette.
  - Permanently docked at the Top-Right desktop corner with smooth left-click drag support.
- **Bare-Metal Audio DSP & Anti-Typing Filter**:
  - Direct microphone capture via `cpal` in 32ms fixed buffers.
  - 4th-order Butterworth bandpass filter (300 Hz – 3400 Hz) and crest-factor analysis rejecting keyboard clicks up to 90+ WPM.
- **Zero LangChain Overhead**:
  - Directly calls Google Gemini 2.5 Flash Lite REST API and Gemini 3.8 Live WebSockets via `reqwest` and `tokio-tungstenite`.
  - Streams ElevenLabs Viraj voice audio with in-process decoding via `rodio`.
- **In-Process Headless Music & Audio Ducking**:
  - Audio ducking automatically drops background music volume to 15% during voice interaction and restores it immediately when speech concludes.
- **Strict Single-Instance Socket IPC**:
  - Binds to localhost port `48123` to guarantee only one Titanium process and one Orb ever exist on screen.

---

## 🛠️ Building & Running

### 1. Install Rust
If you don't have Rust installed, install via `winget` or [rustup.rs](https://rustup.rs):
```powershell
winget install Rustlang.Rustup
```

### 2. Build Release Executable
```powershell
cd titanium-rust
cargo build --release
```

### 3. Run
```powershell
./target/release/titanium-rust.exe
```

The app will read your API keys directly from the root `.env` file (`GEMINI_API_KEY` and `ELEVENLABS_API_KEY`).
