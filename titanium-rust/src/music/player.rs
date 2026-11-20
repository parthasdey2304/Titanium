//! Headless Background Music Streaming & Audio Ducking Engine
//! Pure in-process audio playback with zero browser tabs or external app windows.

use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use rodio::{Decoder, OutputStream, Sink};
use std::io::Cursor;
use parking_lot::Mutex;

pub struct MusicPlayer {
    sink: Arc<Mutex<Option<Sink>>>,
    _stream: Arc<Mutex<Option<OutputStream>>>,
    normal_volume: AtomicU32,
    is_ducked: AtomicBool,
    is_playing: AtomicBool,
}

impl MusicPlayer {
    pub fn new() -> Self {
        let (stream, stream_handle) = OutputStream::try_default().expect("Failed to open audio output");
        let sink = Sink::try_new(&stream_handle).expect("Failed to create rodio sink");
        sink.set_volume(0.70); // 70% default

        Self {
            sink: Arc::new(Mutex::new(Some(sink))),
            _stream: Arc::new(Mutex::new(Some(stream))),
            normal_volume: AtomicU32::new(70),
            is_ducked: AtomicBool::new(false),
            is_playing: AtomicBool::new(false),
        }
    }

    pub fn set_volume(&self, vol: u32) {
        let clamped = vol.clamp(0, 100);
        self.normal_volume.store(clamped, Ordering::SeqCst);
        if !self.is_ducked.load(Ordering::Relaxed) {
            if let Some(ref sink) = *self.sink.lock() {
                sink.set_volume(clamped as f32 / 100.0);
            }
        }
    }

    pub fn duck(&self, should_duck: bool) {
        if should_duck {
            self.is_ducked.store(true, Ordering::SeqCst);
            if let Some(ref sink) = *self.sink.lock() {
                sink.set_volume(0.15); // Duck down to 15%
            }
        } else {
            self.is_ducked.store(false, Ordering::SeqCst);
            let target = self.normal_volume.load(Ordering::Relaxed) as f32 / 100.0;
            if let Some(ref sink) = *self.sink.lock() {
                sink.set_volume(target);
            }
        }
    }

    pub fn pause(&self) {
        if let Some(ref sink) = *self.sink.lock() {
            sink.pause();
            self.is_playing.store(false, Ordering::SeqCst);
        }
    }

    pub fn resume(&self) {
        if let Some(ref sink) = *self.sink.lock() {
            sink.play();
            self.is_playing.store(true, Ordering::SeqCst);
        }
    }

    pub fn stop(&self) {
        if let Some(ref sink) = *self.sink.lock() {
            sink.stop();
            self.is_playing.store(false, Ordering::SeqCst);
        }
    }

    pub fn play_stream_bytes(&self, bytes: Vec<u8>) -> anyhow::Result<()> {
        if let Some(ref sink) = *self.sink.lock() {
            sink.stop();
            let cursor = Cursor::new(bytes);
            let source = Decoder::new(cursor)?;
            sink.append(source);
            sink.play();
            self.is_playing.store(true, Ordering::SeqCst);
        }
        Ok(())
    }
}
