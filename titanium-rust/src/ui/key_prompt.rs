//! Native Win32 On-Screen API Key Setup Dialog
//! Appears directly on the user's screen with zero terminal/console popups.
//! Includes live Gemini API validation, status messages, and auto-saves to .env.

use std::fs;
use std::path::PathBuf;
use std::os::windows::process::CommandExt;
use windows::core::{w, PCWSTR};
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    CreateWindowExW, DefWindowProcW, DispatchMessageW, GetMessageW,
    PostQuitMessage, RegisterClassW, SendMessageW, SetWindowTextW,
    ShowWindow, CW_USEDEFAULT, MSG, SW_SHOW, WM_COMMAND, WM_DESTROY,
    WNDCLASSW, WS_CHILD, WS_OVERLAPPEDWINDOW, WS_VISIBLE,
    MessageBoxW, MB_ICONERROR, MB_ICONINFORMATION, MB_OK
};
use windows::Win32::Graphics::Gdi::{CreateSolidBrush, COLORREF};
use crate::ai::gemini::GeminiClient;

pub struct NativeKeyPrompt;

impl NativeKeyPrompt {
    /// Prompts the user on-screen for their Gemini API key if missing,
    /// validates the key live against the Gemini API endpoint, and persists it to .env.
    pub async fn ensure_api_key() -> anyhow::Result<String> {
        // 1. Check if already present in environment or .env
        if let Ok(key) = std::env::var("GEMINI_API_KEY") {
            if !key.trim().is_empty() && key.trim() != "test_key" && key.trim() != "your_gemini_api_key_here" {
                return Ok(key.trim().to_string());
            }
        }

        // 2. Read from local .env beside current executable
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_else(|| PathBuf::from("."));
        let env_path = exe_dir.join(".env");

        if env_path.exists() {
            if let Ok(content) = fs::read_to_string(&env_path) {
                for line in content.lines() {
                    if let Some(stripped) = line.strip_prefix("GEMINI_API_KEY=") {
                        let k = stripped.trim().to_string();
                        if !k.is_empty() && k != "your_gemini_api_key_here" {
                            std::env::set_var("GEMINI_API_KEY", &k);
                            return Ok(k);
                        }
                    }
                }
            }
        }

        // 3. Prompt user via native graphical input dialog
        let prompt_result = Self::show_gui_prompt()?;
        if prompt_result.trim().is_empty() {
            anyhow::bail!("No API key provided by user.");
        }

        // 4. Live validate with Gemini API
        let is_valid = GeminiClient::validate_key(&prompt_result).await.unwrap_or(false);
        if !is_valid {
            unsafe {
                MessageBoxW(
                    HWND(0),
                    w!("The provided Gemini API Key failed verification. Please check your key at aistudio.google.com and retry."),
                    w!("Titanium - Invalid API Key"),
                    MB_OK | MB_ICONERROR,
                );
            }
            anyhow::bail!("Invalid Gemini API Key");
        }

        // 5. Save to .env beside executable
        let env_content = format!("GEMINI_API_KEY={}\nASSISTANT_NAME=Titanium\nLANGUAGE_MODE=hinglish\n", prompt_result.trim());
        let _ = fs::write(&env_path, env_content);
        std::env::set_var("GEMINI_API_KEY", prompt_result.trim());

        unsafe {
            MessageBoxW(
                HWND(0),
                w!("Gemini API Key successfully verified and connected! Launching Titanium..."),
                w!("Titanium - Connection Successful"),
                MB_OK | MB_ICONINFORMATION,
            );
        }

        Ok(prompt_result.trim().to_string())
    }

    /// Invokes native on-screen graphical input using Windows VBScript/MSHTA input dialog
    /// without spawning any visible console or PowerShell window.
    fn show_gui_prompt() -> anyhow::Result<String> {
        let vbs_code = "Dim key\nkey = InputBox(\"Welcome to Titanium!\" & vbCrLf & vbCrLf & \"Please paste your Google Gemini API Key below to activate Titanium on your system:\" & vbCrLf & \"(You can get a free key at aistudio.google.com/app/apikey)\", \"Titanium - Gemini API Key Setup\", \"\")\nWScript.StdOut.Write key";
        
        let output = std::process::Command::new("cscript")
            .args(&["//Nologo", "//E:VBScript"])
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .spawn()
            .and_then(|mut child| {
                use std::io::Write;
                if let Some(mut stdin) = child.stdin.take() {
                    let _ = stdin.write_all(vbs_code.as_bytes());
                }
                child.wait_with_output()
            });

        match output {
            Ok(out) => Ok(String::from_utf8_lossy(&out.stdout).trim().to_string()),
            Err(e) => anyhow::bail!("Failed to launch native UI prompt: {}", e),
        }
    }
}
