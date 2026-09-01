//! `AmbiguousRequestDetector`.

use super::AutopilotDetector;
use crate::models::{DetectionRequest, DetectionResult};

pub struct AmbiguousRequestDetector;
impl AutopilotDetector for AmbiguousRequestDetector {
    fn name(&self) -> &'static str {
        "ambiguous_request"
    }
    fn detect(
        &self,
        request: &DetectionRequest,
    ) -> Result<DetectionResult, cortex_enterprise::error::EnterpriseError> {
        const VAGUE_VERBS: &[&str] = &[
            "mejorar",
            "arreglar",
            "cambiar",
            "actualizar",
            "fixear",
            "improve",
            "fix",
            "change",
            "update",
            "refactor",
        ];
        const MIN_WORDS: usize = 8;
        const FILE_EXTS: &[&str] = &["py", "ts", "js", "md", "yaml", "json"];

        let Some(req) = &request.user_request else {
            return Ok(DetectionResult {
                task_type: "ambiguous".into(),
                confidence: 0.9,
                reason: "No user request provided".into(),
                suggested_complexity: "none".into(),
            });
        };
        let words: Vec<String> = req
            .to_lowercase()
            .split_whitespace()
            .map(String::from)
            .collect();
        let has_vague_verb = words.iter().any(|w| VAGUE_VERBS.contains(&w.as_str()));
        let is_short = words.len() < MIN_WORDS;
        let has_file_ref = words
            .iter()
            .any(|w| w.contains('.') && FILE_EXTS.contains(&w.rsplit('.').next().unwrap_or("")));

        Ok(if is_short && has_vague_verb && !has_file_ref {
            DetectionResult {
                task_type: "ambiguous".into(),
                confidence: 0.7,
                reason: format!(
                    "Short request ({} words) with vague verb, no file references",
                    words.len()
                ),
                suggested_complexity: "none".into(),
            }
        } else {
            DetectionResult::noop("Request appears sufficiently specific")
        })
    }
}
