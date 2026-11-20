//! Native Windows 3D Siri Orb Widget in Rust (Win32 Layered Window)
//! High-performance per-pixel alpha blended window (WS_EX_LAYERED)
//! Running at 60 FPS with zero Electron or Qt overhead (<15 MB RAM).

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use windows::core::*;
use windows::Win32::Foundation::*;
use windows::Win32::Graphics::Gdi::*;
use windows::Win32::UI::WindowsAndMessaging::*;

const ORB_SIZE: i32 = 120;
const MARGIN_X: i32 = 18;
const MARGIN_Y: i32 = 18;

pub struct NativeOrb {
    hwnd: HWND,
    is_listening: Arc<AtomicBool>,
}

impl NativeOrb {
    pub fn create_and_show() -> anyhow::Result<Arc<Self>> {
        unsafe {
            let instance = GetModuleHandleW(None)?;
            let class_name = w!("TitaniumOrbClass");

            let wc = WNDCLASSW {
                style: CS_HREDRAW | CS_VREDRAW,
                lpfnWndProc: Some(Self::wnd_proc),
                hInstance: instance.into(),
                lpszClassName: class_name,
                hCursor: LoadCursorW(None, IDC_HAND)?,
                ..Default::default()
            };

            RegisterClassW(&wc);

            // Compute Top-Right Desktop Coordinates
            let screen_w = GetSystemMetrics(SM_CXSCREEN);
            let pos_x = screen_w - ORB_SIZE - MARGIN_X;
            let pos_y = MARGIN_Y;

            // Frameless, topmost, transparent layered tool window
            let hwnd = CreateWindowExW(
                WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
                class_name,
                w!("Titanium Siri Orb"),
                WS_POPUP | WS_VISIBLE,
                pos_x,
                pos_y,
                ORB_SIZE,
                ORB_SIZE,
                None,
                None,
                instance,
                None,
            )?;

            let orb = Arc::new(Self {
                hwnd,
                is_listening: Arc::new(AtomicBool::new(false)),
            });

            // Start 60 FPS render loop
            let render_orb = orb.clone();
            std::thread::Builder::new()
                .name("titanium-orb-renderer".to_string())
                .spawn(move || {
                    let mut phase: f32 = 0.0;
                    loop {
                        render_orb.render_frame(phase);
                        phase += 0.04;
                        std::thread::sleep(std::time::Duration::from_millis(16)); // ~60 FPS
                    }
                })?;

            Ok(orb)
        }
    }

    pub fn set_listening(&self, listening: bool) {
        self.is_listening.store(listening, Ordering::SeqCst);
    }

    fn render_frame(&self, phase: f32) {
        unsafe {
            let hdc_screen = GetDC(None);
            let hdc_mem = CreateCompatibleDC(hdc_screen);

            let mut bmi = BITMAPINFO {
                bmiHeader: BITMAPINFOHEADER {
                    biSize: std::mem::size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: ORB_SIZE,
                    biHeight: -ORB_SIZE, // Top-down DIB
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: BI_RGB.0,
                    ..Default::default()
                },
                ..Default::default()
            };

            let mut bits: *mut std::ffi::c_void = std::ptr::null_mut();
            let hbitmap = CreateDIBSection(
                hdc_mem,
                &bmi,
                DIB_RGB_COLORS,
                &mut bits,
                None,
                0,
            ).unwrap();

            let old_bitmap = SelectObject(hdc_mem, hbitmap);

            // Procedural Organic 3D Sphere Renderer (AmazingUI Palette)
            let pixel_buf = std::slice::from_raw_parts_mut(bits as *mut u32, (ORB_SIZE * ORB_SIZE) as usize);
            let cx = ORB_SIZE as f32 / 2.0;
            let cy = ORB_SIZE as f32 / 2.0;
            let radius = cx - 12.0;
            let is_listen = self.is_listening.load(Ordering::Relaxed);

            for y in 0..ORB_SIZE {
                for x in 0..ORB_SIZE {
                    let dx = x as f32 - cx;
                    let dy = y as f32 - cy;
                    let dist = (dx * dx + dy * dy).sqrt();

                    if dist <= radius {
                        let norm = dist / radius;
                        let angle = dy.atan2(dx);

                        // Organic plasma fluid harmonic waves
                        let wave = (angle * 3.0 + phase * 2.5).sin() * 0.25;
                        let lum = (1.0 - norm + wave).clamp(0.0, 1.0);

                        let (r, g, b) = if is_listen {
                            // Electric Cyan/Azure
                            ((67.0 * lum) as u32, (167.0 * lum) as u32, (223.0 * lum) as u32)
                        } else {
                            // Electric Deep Blue & Cosmic Magenta blend
                            let t = ((angle + phase).sin() + 1.0) * 0.5;
                            let r_val = 39.0 * (1.0 - t) + 203.0 * t;
                            let g_val = 28.0 * (1.0 - t) + 27.0 * t;
                            let b_val = 213.0 * (1.0 - t) + 193.0 * t;
                            ((r_val * lum) as u32, (g_val * lum) as u32, (b_val * lum) as u32)
                        };

                        // Smooth anti-aliased edge alpha
                        let alpha = if dist > radius - 2.5 {
                            ((radius - dist) / 2.5 * 255.0).clamp(0.0, 255.0) as u32
                        } else {
                            255u32
                        };

                        // Pre-multiplied 32-bit ARGB
                        let pre_r = (r * alpha) / 255;
                        let pre_g = (g * alpha) / 255;
                        let pre_b = (b * alpha) / 255;

                        pixel_buf[(y * ORB_SIZE + x) as usize] = (alpha << 24) | (pre_r << 16) | (pre_g << 8) | pre_b;
                    } else {
                        pixel_buf[(y * ORB_SIZE + x) as usize] = 0; // 100% transparent
                    }
                }
            }

            let mut blend = BLENDFUNCTION {
                BlendOp: AC_SRC_OVER as u8,
                BlendFlags: 0,
                SourceConstantAlpha: 255,
                AlphaFormat: AC_SRC_ALPHA as u8,
            };

            let pt_src = POINT { x: 0, y: 0 };
            let size = SIZE { cx: ORB_SIZE, cy: ORB_SIZE };

            let _ = UpdateLayeredWindow(
                self.hwnd,
                hdc_screen,
                None,
                Some(&size),
                hdc_mem,
                Some(&pt_src),
                COLORREF(0),
                Some(&blend),
                ULW_ALPHA,
            );

            SelectObject(hdc_mem, old_bitmap);
            DeleteObject(hbitmap);
            DeleteDC(hdc_mem);
            ReleaseDC(None, hdc_screen);
        }
    }

    unsafe extern "system" fn wnd_proc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        match msg {
            WM_LBUTTONDOWN => {
                // Drag the Orb freely across monitors on left mouse click
                ReleaseCapture().unwrap();
                SendMessageW(hwnd, WM_NCLBUTTONDOWN, WPARAM(HTCAPTION as usize), LPARAM(0));
                LRESULT(0)
            }
            WM_DESTROY => {
                PostQuitMessage(0);
                LRESULT(0)
            }
            _ => DefWindowProcW(hwnd, msg, wparam, lparam),
        }
    }
}
