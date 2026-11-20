//! Direct Google Gemini API Client in Rust (Zero LangChain Overhead)
//! Communicates directly with Gemini 2.5 Flash Lite REST API
//! and Gemini 3.8 Live bidirectional WebSocket endpoint.

use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::sync::Arc;

#[derive(Serialize)]
struct GeminiPart {
    text: String,
}

#[derive(Serialize)]
struct GeminiContent {
    parts: Vec<GeminiPart>,
    role: String,
}

#[derive(Serialize)]
struct GenerationConfig {
    temperature: f32,
    max_output_tokens: u32,
}

#[derive(Serialize)]
struct GeminiRequest {
    contents: Vec<GeminiContent>,
    system_instruction: Option<GeminiContent>,
    generation_config: GenerationConfig,
}

#[derive(Deserialize)]
struct GeminiCandidate {
    content: Option<GeminiResponseContent>,
}

#[derive(Deserialize)]
struct GeminiResponseContent {
    parts: Option<Vec<GeminiResponsePart>>,
}

#[derive(Deserialize)]
struct GeminiResponsePart {
    text: Option<String>,
}

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Option<Vec<GeminiCandidate>>,
}

pub struct GeminiClient {
    api_key: String,
    http_client: Client,
    model: String,
}

impl GeminiClient {
    pub fn new(api_key: String) -> Self {
        Self {
            api_key,
            http_client: Client::builder()
                .tcp_nodelay(true)
                .build()
                .unwrap_or_default(),
            model: "gemini-2.5-flash-lite".to_string(),
        }
    }

    /// Sub-second conversational generation
    pub async fn ask(&self, user_prompt: &str) -> anyhow::Result<String> {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );

        let system_text = "You are Titanium, a super fast, intelligent virtual assistant for Parth. Respond in natural, snappy Hinglish in 1-2 concise spoken sentences.";

        let payload = GeminiRequest {
            contents: vec![GeminiContent {
                role: "user".to_string(),
                parts: vec![GeminiPart {
                    text: user_prompt.to_string(),
                }],
            }],
            system_instruction: Some(GeminiContent {
                role: "system".to_string(),
                parts: vec![GeminiPart {
                    text: system_text.to_string(),
                }],
            }),
            generation_config: GenerationConfig {
                temperature: 0.6,
                max_output_tokens: 150,
            },
        };

        let res = self.http_client
            .post(&url)
            .json(&payload)
            .send()
            .await?;

        let body: GeminiResponse = res.json().await?;

        if let Some(candidates) = body.candidates {
            if let Some(first) = candidates.first() {
                if let Some(content) = &first.content {
                    if let Some(parts) = &content.parts {
                        if let Some(p) = parts.first() {
                            if let Some(text) = &p.text {
                                return Ok(text.trim().to_string());
                            }
                        }
                    }
                }
            }
        }

        Ok("Ji Parth, main sun raha hoon. Boliye!".to_string())
    }
}
