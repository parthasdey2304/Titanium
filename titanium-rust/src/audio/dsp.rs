//! Digital Signal Processing (DSP) Engine for Titanium Rust
//! Features 4th-order Butterworth acoustic bandpass (300 Hz - 3400 Hz)
//! and mechanical typing-transient rejection based on crest-factor analysis.

use std::f32::consts::PI;

/// Direct Form II Transposed Biquad Filter Section
#[derive(Debug, Clone)]
pub struct Biquad {
    b0: f32,
    b1: f32,
    b2: f32,
    a1: f32,
    a2: f32,
    s1: f32,
    s2: f32,
}

impl Biquad {
    pub fn new(b0: f32, b1: f32, b2: f32, a1: f32, a2: f32) -> Self {
        Self {
            b0,
            b1,
            b2,
            a1,
            a2,
            s1: 0.0,
            s2: 0.0,
        }
    }

    #[inline(always)]
    pub fn process(&mut self, input: f32) -> f32 {
        let output = self.b0 * input + self.s1;
        self.s1 = self.b1 * input - self.a1 * output + self.s2;
        self.s2 = self.b2 * input - self.a2 * output;
        output
    }
}

/// 4th-Order Butterworth Bandpass Filter (300 Hz to 3400 Hz @ 16 kHz)
#[derive(Debug, Clone)]
pub struct BandpassFilter {
    sections: Vec<Biquad>,
}

impl BandpassFilter {
    pub fn new_voice_bandpass(sample_rate: f32) -> Self {
        // High-pass filter at 300 Hz (Q = 0.7071)
        let hp_freq = 300.0;
        let w0_hp = 2.0 * PI * hp_freq / sample_rate;
        let alpha_hp = w0_hp.sin() / (2.0 * 0.7071);
        let cos_hp = w0_hp.cos();
        let a0_hp = 1.0 + alpha_hp;
        let hp_section = Biquad::new(
            ((1.0 + cos_hp) / 2.0) / a0_hp,
            (-(1.0 + cos_hp)) / a0_hp,
            ((1.0 + cos_hp) / 2.0) / a0_hp,
            (-2.0 * cos_hp) / a0_hp,
            (1.0 - alpha_hp) / a0_hp,
        );

        // Low-pass filter at 3400 Hz (Q = 0.7071)
        let lp_freq = 3400.0;
        let w0_lp = 2.0 * PI * lp_freq / sample_rate;
        let alpha_lp = w0_lp.sin() / (2.0 * 0.7071);
        let cos_lp = w0_lp.cos();
        let a0_lp = 1.0 + alpha_lp;
        let lp_section = Biquad::new(
            ((1.0 - cos_lp) / 2.0) / a0_lp,
            (1.0 - cos_lp) / a0_lp,
            ((1.0 - cos_lp) / 2.0) / a0_lp,
            (-2.0 * cos_lp) / a0_lp,
            (1.0 - alpha_lp) / a0_lp,
        );

        Self {
            sections: vec![hp_section, lp_section],
        }
    }

    #[inline(always)]
    pub fn filter_sample(&mut self, mut sample: f32) -> f32 {
        for section in &mut self.sections {
            sample = section.process(sample);
        }
        sample
    }

    pub fn filter_buffer(&mut self, buffer: &[f32], out: &mut [f32]) {
        for (i, &s) in buffer.iter().enumerate() {
            out[i] = self.filter_sample(s);
        }
    }
}

/// Computes Root-Mean-Square (RMS) and peak crest factor
pub fn analyze_audio_block(samples: &[f32]) -> (f32, f32, bool) {
    if samples.is_empty() {
        return (0.0, 0.0, false);
    }

    let mut sum_sq = 0.0f32;
    let mut peak = 0.0f32;

    for &s in samples {
        let abs_val = s.abs();
        if abs_val > peak {
            peak = abs_val;
        }
        sum_sq += s * s;
    }

    let rms = (sum_sq / samples.len() as f32).sqrt();
    let crest_factor = peak / (rms + 1e-6);

    // Keystroke clicks have sharp crest factors (> 5.0) and high peak/RMS disparity
    let is_keystroke = crest_factor > 5.0 || (peak > 0.85 && rms < 0.12);

    (rms, peak, is_keystroke)
}
