//! Request/response JSON. El crate habla system_one, no UnifiedHit.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Debug, Clone)]
pub struct JudgementRequest {
    /// Body que se POSTea a /v1/systemone: `{state, model, questions}`.
    pub body: Value,
}

impl JudgementRequest {
    pub fn system_one(state: Value, model: &str, questions: Value) -> Self {
        Self {
            body: json!({
                "state": state,
                "model": model,
                "questions": questions,
            }),
        }
    }
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Usage {
    #[serde(default)]
    pub input_tokens: u64,
    #[serde(default)]
    pub output_tokens: u64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct JudgementResponse {
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub answers: serde_json::Map<String, Value>,
    #[serde(default)]
    pub usage: Usage,
    #[serde(default = "backend_typesafe")]
    pub backend: String,
}

fn backend_typesafe() -> String {
    "typesafe".into()
}
