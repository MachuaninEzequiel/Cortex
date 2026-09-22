//! Cliente HTTP `POST /v1/systemone`. Retries cortos en 429/529; el resto fail-open.

use std::time::Duration;

use serde::Deserialize;
use serde_json::Value;

use crate::error::JudgementError;
use crate::purpose::Purpose;
use crate::request::{JudgementRequest, JudgementResponse, Usage};
use crate::JudgementClient;

pub const DEFAULT_BASE_URL: &str = "https://api.typesafe.ai";
pub const DEFAULT_MODEL: &str = "jev-1.13.0";
const MAX_RETRIES: u8 = 1;
const BACKOFF: Duration = Duration::from_millis(150);

#[derive(Debug, Clone)]
pub struct TypesafeClient {
    agent: ureq::Agent,
    endpoint: String,
    api_key: String,
    pub model: String,
    search_squeeze: bool,
    promotion: bool,
    context_pack: bool,
    utterance: bool,
    session_compact: bool,
    model_routing: bool,
}

impl TypesafeClient {
    pub fn new(
        base_url: &str,
        api_key: String,
        model: String,
        timeout_ms: u64,
        search_squeeze: bool,
        promotion: bool,
        context_pack: bool,
        utterance: bool,
        session_compact: bool,
        model_routing: bool,
    ) -> Self {
        let agent: ureq::Agent = ureq::Agent::config_builder()
            .timeout_global(Some(Duration::from_millis(timeout_ms.max(1))))
            .build()
            .into();
        let base = base_url.trim_end_matches('/');
        Self {
            agent,
            endpoint: format!("{base}/v1/systemone"),
            api_key,
            model,
            search_squeeze,
            promotion,
            context_pack,
            utterance,
            session_compact,
            model_routing,
        }
    }

    fn post_once(&self, body: &Value) -> Result<JudgementResponse, JudgementError> {
        let payload =
            serde_json::to_vec(body).map_err(|e| JudgementError::Validation(e.to_string()))?;
        let result = self
            .agent
            .post(&self.endpoint)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .send(payload);
        match result {
            Ok(resp) => {
                let text = resp
                    .into_body()
                    .read_to_string()
                    .map_err(|e| JudgementError::Transport(e.to_string()))?;
                parse_system_one(&text)
            }
            Err(ureq::Error::StatusCode(code)) => Err(JudgementError::Http(code)),
            Err(ureq::Error::Timeout(_)) => Err(JudgementError::Timeout),
            Err(e) => Err(JudgementError::Transport(e.to_string())),
        }
    }
}

impl JudgementClient for TypesafeClient {
    fn enabled(&self, purpose: Purpose) -> bool {
        match purpose {
            Purpose::SearchSqueeze => self.search_squeeze,
            Purpose::Promotion => self.promotion,
            Purpose::ContextPack => self.context_pack,
            Purpose::Utterance => self.utterance,
            Purpose::SessionCompact => self.session_compact,
            Purpose::ModelRouting => self.model_routing,
        }
    }

    fn evaluate(&self, request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        let mut last = self.post_once(&request.body);
        for _ in 0..MAX_RETRIES {
            match &last {
                Err(JudgementError::Http(429 | 529)) => {
                    std::thread::sleep(BACKOFF);
                    last = self.post_once(&request.body);
                }
                _ => break,
            }
        }
        last
    }
}

#[derive(Debug, Deserialize)]
struct WireResponse {
    #[serde(default)]
    model: String,
    #[serde(default)]
    answers: serde_json::Map<String, Value>,
    #[serde(default)]
    usage: WireUsage,
}

#[derive(Debug, Default, Deserialize)]
struct WireUsage {
    #[serde(default)]
    input_tokens: u64,
    #[serde(default)]
    output_tokens: u64,
}

fn parse_system_one(text: &str) -> Result<JudgementResponse, JudgementError> {
    let parsed: WireResponse =
        serde_json::from_str(text).map_err(|e| JudgementError::Validation(e.to_string()))?;
    Ok(JudgementResponse {
        model: parsed.model,
        answers: parsed.answers,
        usage: Usage {
            input_tokens: parsed.usage.input_tokens,
            output_tokens: parsed.usage.output_tokens,
        },
        backend: "typesafe".into(),
    })
}
