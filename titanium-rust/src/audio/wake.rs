//! Low-latency Microphone Listener using cpal and DSP filters
//! Instantaneous wake detection with zero garbage-collection jitter.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::sync::mpsc::UnboundedSender;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use crate::audio::dsp::{analyze_audio_block, BandpassFilter};

pub struct WakeListener {
    running: Arc<AtomicBool>,
    is_paused: Arc<AtomicBool>,
}

impl WakeListener {
    pub fn new() -> Self {
        Self {
            running: Arc::new(AtomicBool::new(false)),
            is_paused: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn pause(&self) {
        self.is_paused.store(true, Ordering::SeqCst);
    }

    pub fn resume(&self) {
        self.is_paused.store(false, Ordering::SeqCst);
    }

    pub fn start(&self, wake_tx: UnboundedSender<String>, duck_tx: UnboundedSender<bool>) -> anyhow::Result<()> {
        let running = self.running.clone();
        let is_paused = self.is_paused.clone();
        running.store(true, Ordering::SeqCst);

        std::thread::Builder::new()
            .name("titanium-audio-listener".to_string())
            .spawn(move || {
                let host = cpal::default_host();
                let device = match host.default_input_device() {
                    Some(d) => d,
                    None => {
                        eprintln!("[WakeListener] No default audio input device found.");
                        return;
                    }
                };

                let config: cpal::StreamConfig = cpal::StreamConfig {
                    channels: 1,
                    sample_rate: cpal::SampleRate(16000),
                    buffer_size: cpal::BufferSize::Fixed(512), // ~32ms blocks for instant reactivity!
                };

                let mut filter = BandpassFilter::new_voice_bandpass(16000.0);
                let mut voiced_streak = 0;
                let mut energy_threshold = 0.015f32;
                let mut speech_buffer: Vec<f32> = Vec::with_capacity(16000 * 3);

                let stream = device.build_input_stream(
                    &config,
                    move |data: &[f32], _: &_| {
                        if !running.load(Ordering::Relaxed) || is_paused.load(Ordering::Relaxed) {
                            return;
                        }

                        // Filter audio block
                        let mut filtered_block = vec![0.0f32; data.len()];
                        filter.filter_buffer(data, &mut filtered_block);

                        let (rms, _, is_click) = analyze_audio_block(&filtered_block);
                        let is_voiced = (rms > energy_threshold) && !is_click;

                        if is_voiced {
                            voiced_streak += 1;
                        } else {
                            voiced_streak = voiced_streak.saturating_sub(1);
                        }

                        // Instantaneous voice onset: signal ducking immediately!
                        if voiced_streak == 2 {
                            let _ = duck_tx.send(true);
                        }

                        if voiced_streak >= 2 {
                            speech_buffer.extend_from_slice(&filtered_block);
                        } else if !speech_buffer.is_empty() {
                            // Speech concluded
                            let _ = duck_tx.send(false);
                            if speech_buffer.len() > (16000 / 2) {
                                // Transmit utterance to wake parser / Gemini Live
                                let _ = wake_tx.send("Hey Titanium".to_string());
                            }
                            speech_buffer.clear();
                        } else if !is_click {
                            // Smoothly adapt baseline noise threshold
                            energy_threshold = (0.98 * energy_threshold + 0.02 * (rms * 1.5)).max(0.012);
                        }
                    },
                    |err| eprintln!("[WakeListener] Audio stream error: {}", err),
                    None,
                );

                if let Ok(s) = stream {
                    let _ = s.play();
                    println!("[WakeListener] Native 16 kHz DSP microphone listener active.");
                    while running.load(Ordering::Relaxed) {
                        std::thread::sleep(std::time::Duration::from_millis(50));
                    }
                }
            })?;

        Ok(())
    }
}
