//! Puerto de `cortex.autopilot.detectors`: protocolo, resolución §7.1.2 y
//! los 8 detectores built-in.

use cortex_enterprise::error::EnterpriseError;

use crate::models::{DetectionRequest, DetectionResult};

pub mod ambiguous;
pub mod default;

pub use ambiguous::AmbiguousRequestDetector;
pub use default::{
    CodeChangeDetector, DocsOnlyDetector, LargeRefactorDetector, NoopDetector,
    QuestionOnlyDetector, SecuritySensitiveDetector,
};

pub trait AutopilotDetector {
    fn name(&self) -> &'static str;
    fn detect(&self, request: &DetectionRequest) -> Result<DetectionResult, EnterpriseError>;
}

/// `default_detectors()` en el orden canónico de Python.
pub fn default_detectors() -> Vec<Box<dyn AutopilotDetector>> {
    vec![
        Box::new(AmbiguousRequestDetector),
        Box::new(QuestionOnlyDetector),
        Box::new(DocsOnlyDetector),
        Box::new(SecuritySensitiveDetector),
        Box::new(LargeRefactorDetector),
        Box::new(CodeChangeDetector),
        Box::new(NoopDetector),
    ]
}

const COMPLEXITY_RANK: &[(&str, i32)] = &[("deep", 3), ("fast", 2), ("none", 1)];

fn complexity_rank(c: &str) -> i32 {
    COMPLEXITY_RANK
        .iter()
        .find(|(k, _)| *k == c)
        .map(|(_, v)| *v)
        .unwrap_or(0)
}

/// `resolve_detectors` (§7.1.2):
/// 1. ejecutar todos (detectores rotos se ignoran);
/// 2. filtrar confidence > 0.3;
/// 3. security_sensitive con >0.5 gana;
/// 4. ambiguous_request con >0.6 bloquea;
/// 5. mayor confidence; 6. empate → complejidad más conservadora.
pub fn resolve_detectors(
    detectors: &[Box<dyn AutopilotDetector>],
    request: &DetectionRequest,
) -> DetectionResult {
    let mut results: Vec<(&str, DetectionResult)> = Vec::new();
    for det in detectors {
        if let Ok(res) = det.detect(request) {
            results.push((det.name(), res));
        }
    }

    let candidates: Vec<(&str, DetectionResult)> = results
        .iter()
        .filter(|(_, r)| r.confidence > 0.3)
        .cloned()
        .collect();

    if candidates.is_empty() {
        return match results
            .iter()
            .max_by(|a, b| a.1.confidence.total_cmp(&b.1.confidence))
        {
            Some((_, r)) => r.clone(),
            None => DetectionResult::noop("No detectors returned results"),
        };
    }

    // Step 3 — security override.
    if let Some((_, r)) = candidates
        .iter()
        .find(|(n, r)| *n == "security_sensitive" && r.confidence > 0.5)
    {
        return r.clone();
    }
    // Step 4 — ambiguous override.
    if let Some((_, r)) = candidates
        .iter()
        .find(|(n, r)| *n == "ambiguous_request" && r.confidence > 0.6)
    {
        return r.clone();
    }
    // Step 5/6 — mayor confianza; empate → más conservador.
    candidates
        .iter()
        .max_by(|a, b| {
            let ka = (a.1.confidence, complexity_rank(&a.1.suggested_complexity));
            let kb = (b.1.confidence, complexity_rank(&b.1.suggested_complexity));
            ka.partial_cmp(&kb).unwrap_or(std::cmp::Ordering::Equal)
        })
        .map(|(_, r)| r.clone())
        .unwrap_or_else(|| DetectionResult::noop("No detectors returned results"))
}
