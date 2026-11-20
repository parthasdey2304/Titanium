//! Titanium Virtual Assistant — Native Rust Port
//! Ultra-lightweight, sub-30MB RAM footprint, instantaneous wake times,
//! and native Win32 transparent 3D Siri Orb.

mod audio;
mod ai;
mod music;
mod ui;

use std::net::TcpListener;
use std::sync::Arc;
use tokio::sync::mpsc;

use audio::wake::WakeListener;
use ai::gemini::GeminiClient;
use ai::elevenlabs::ElevenLabsTTS;
use music::player::MusicPlayer;
use ui::orb::NativeOrb;

const SINGLE_INSTANCE_PORT: u16 = 48123;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    dotenvy::dotenv().ok();

    println!("==================================================");
    println!("🌌 Titanium Virtual Assistant (Native Rust Port)");
    println!("==================================================");

    // 1. Single-Instance Port Lock
    let _instance_lock = match TcpListener::bind(("127.0.0.1", SINGLE_INSTANCE_PORT)) {
        Ok(l) => l,
        Err(_) => {
            println!("[Titanium-RS] Another instance is already running. Exiting cleanly.");
            return Ok(());
        }
    };

    println!("[Titanium-RS] Single-instance lock acquired on port {}.", SINGLE_INSTANCE_PORT);

    // 2. Initialize Hardware-Accelerated Win32 Transparent Siri Orb
    let orb = NativeOrb::create_and_show()?;
    println!("[Titanium-RS] 60 FPS Win32 Layered Orb docked at Top-Right.");

    // 3. Initialize AI & Media Services
    let gemini_key = std::env::var("GEMINI_API_KEY").unwrap_or_else(|_| "test_key".to_string());
    let eleven_key = std::env::var("ELEVENLABS_API_KEY").unwrap_or_else(|_| "test_key".to_string());

    let gemini = Arc::new(GeminiClient::new(gemini_key));
    let tts = Arc::new(ElevenLabsTTS::new(eleven_key, None));
    let music_player = Arc::new(MusicPlayer::new());

    // 4. Communication Channels
    let (wake_tx, mut wake_rx) = mpsc::unbounded_channel::<String>();
    let (duck_tx, mut duck_rx) = mpsc::unbounded_channel::<bool>();

    // Audio Ducking Dispatcher
    let player_duck = music_player.clone();
    tokio::spawn(async move {
        while let Some(should_duck) = duck_rx.recv().await {
            player_duck.duck(should_duck);
        }
    });

    // 5. Start DSP Microphone Wake Listener
    let listener = Arc::new(WakeListener::new());
    if let Err(e) = listener.start(wake_tx.clone(), duck_tx.clone()) {
        eprintln!("[Titanium-RS] Note on microphone listener: {}", e);
    }

    // 6. Conversational Event Loop
    let orb_event = orb.clone();
    let gemini_event = gemini.clone();
    let tts_event = tts.clone();
    let duck_tts_tx = duck_tx.clone();

    tokio::spawn(async move {
        while let Some(query) = wake_rx.recv().await {
            println!("[Titanium-RS] Wake event triggered: '{}'", query);
            orb_event.set_listening(true);

            let answer = match gemini_event.ask(&query).await {
                Ok(ans) => ans,
                Err(e) => {
                    eprintln!("[Titanium-RS] Gemini error: {}", e);
                    "Haanji Parth, main sun raha hoon!".to_string()
                }
            };

            println!("[Titanium-RS] Gemini response: '{}'", answer);
            let _ = tts_event.speak(&answer, Some(duck_tts_tx.clone())).await;
            orb_event.set_listening(false);
        }
    });

    // 7. Initial Greeting (Spoken ONCE on launch)
    let init_tts = tts.clone();
    let init_duck = duck_tx.clone();
    tokio::spawn(async move {
        let greeting = "Haanji Parth, bataiye kya baat hai? Main hoon aapki help karne ke liye.";
        let _ = init_tts.speak(greeting, Some(init_duck)).await;
    });

    // 8. Native Windows Message Loop
    unsafe {
        let mut msg = windows::Win32::UI::WindowsAndMessaging::MSG::default();
        while windows::Win32::UI::WindowsAndMessaging::GetMessageW(&mut msg, None, 0, 0).into() {
            windows::Win32::UI::WindowsAndMessaging::TranslateMessage(&msg);
            windows::Win32::UI::WindowsAndMessaging::DispatchMessageW(&msg);
        }
    }

    Ok(())
}
