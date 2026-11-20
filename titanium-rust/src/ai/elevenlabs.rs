//! Direct ElevenLabs Text-to-Speech Streaming Client in Rust
//! Streams Viraj voice audio with sub-second time-to-first-byte (TTFB)
//! and dispatches audio ducking signals to background music.

use reqwest::Client;
use serde_json::json;
use std::io::Cursor;
use rodio::{Decoder, OutputStream, Sink};
use tokio::sync::mpsc::UnboundedSender;

pub struct ElevenLabsTTS {
    api_key: String,
    voice_id: String,
    model_id: String,
    client: Client,
}

impl ElevenLabsTTS {
    pub fn new(api_key: String, voice_id: Option<String>) -> Self {
        Self {
            api_key,
            // Viraj standard ID or custom voice ID
            voice_id: voice_id.unwrap_or_else(|| "pNInz6obpgDQGcFmaJgB".to_string()),
            model_id: "eleven_multilingual_v2".to_string(),
            client: Client::builder().tcp_nodelay(true).build().unwrap_or_default(),
        }
    }

    pub async fn speak(
        &self,
        text: &str,
        duck_tx: Option<UnboundedSender<bool>>,
    ) -> anyhow::Result<()> {
        let url = format!(
            "https://api.elevenlabs.io/v1/text-to-speech/{}/stream",
            self.voice_id
        );

        let body = json!({
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            }
        });

        // Trigger audio ducking (lower background music to 15%)
        if let Some(ref tx) = duck_tx {
            let _ = tx.send(true);
        }

        let resp = self.client
            .post(&url)
            .header("xi-api-key", &self.api_key)
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await?;

        let audio_bytes = resp.bytes().await?;

        // In-process hardware-accelerated playback via rodio
        std::thread::spawn(move || {
            if let Ok((_stream, stream_handle)) = OutputStream::try_default() {
                if let Ok(sink) = Sink::try_new(&stream_handle) {
                    let cursor = Cursor::new(audio_bytes);
                    if let Ok(source) = Decoder::new(cursor) {
                        sink.append(source);
                        sink.sleep_until_end();
                    }
                }
            }
            // Restore background music volume
            if let Some(tx) = duck_tx {
                let _ = tx.send(false);
            }
        });

        Ok(())
    }
}
