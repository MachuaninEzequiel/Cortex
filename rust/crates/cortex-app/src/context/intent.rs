//! Puerto de `cortex/retrieval/intent.py` — QueryIntentDetector para pesos
//! RRF adaptativos. Lexicón regex-only, determinista, sub-milisegundo.

use regex::Regex;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QueryIntent {
    Episodic,
    Semantic,
    Mixed,
}

impl QueryIntent {
    /// (episodic_weight, semantic_weight).
    pub fn weights(self) -> (f64, f64) {
        match self {
            QueryIntent::Episodic => (2.0, 0.6),
            QueryIntent::Semantic => (0.6, 2.0),
            QueryIntent::Mixed => (1.0, 1.0),
        }
    }
}

#[derive(Debug, Clone)]
pub struct IntentResult {
    pub intent: QueryIntent,
    pub episodic_weight: f64,
    pub semantic_weight: f64,
    pub confidence: f64,
    pub matched_signals: Vec<String>,
}

struct Signal {
    pattern: Regex,
    label: &'static str,
}

fn signals(list: &[(&'static str, &'static str)]) -> Vec<Signal> {
    list.iter()
        .map(|(pat, label)| Signal {
            // re.I de Python ⇒ case-insensitive.
            pattern: Regex::new(&format!("(?i){pat}")).expect("regex del lexicón"),
            label,
        })
        .collect()
}

/// Señales episódicas (temporal/change/PR/decisión/error/autor).
fn episodicas() -> Vec<Signal> {
    signals(&[
        (
            r"\b(last|previous|past|before|yesterday|ago|recently|when we)\b",
            "temporal_ref",
        ),
        (
            r"\b(fixed|broke|bugfix|patch|hotfix|resolved|introduced|changed|refactor)\b",
            "change_ref",
        ),
        (
            r"\b(pr|pull request|commit|sha|merge|branch|#\d+)\b",
            "pr_ref",
        ),
        (
            r"\b(decided|decision|chose|choice|why did|rationale|reasoning)\b",
            "decision_ref",
        ),
        (
            r"\b(error|exception|incident|outage|crash|failure|broke|failed)\b",
            "incident_ref",
        ),
        (
            r"\b(implemented by|authored by|written by|who wrote|who fixed)\b",
            "author_ref",
        ),
    ])
}

/// Señales semánticas (conceptual/arquitectura/runbook/spec/concepto).
fn semanticas() -> Vec<Signal> {
    signals(&[
        (
            r"\b(how does|how to|what is|explain|describe|overview|summary)\b",
            "conceptual_q",
        ),
        (
            r"\b(architecture|design|diagram|schema|spec|contract|api|interface)\b",
            "arch_ref",
        ),
        (
            r"\b(runbook|procedure|playbook|guide|tutorial|steps|deploy|setup)\b",
            "runbook_ref",
        ),
        (
            r"\b(requirement|specification|acceptance criteria|definition of done|adr)\b",
            "spec_ref",
        ),
        (
            r"\b(concept|pattern|principle|convention|standard|best practice|best practices)\b",
            "concept_ref",
        ),
    ])
}

/// Detecta la intención de una query para pesos adaptativos de RRF.
///
/// Umbrales default: episodic_threshold=1, semantic_threshold=1.
pub fn detect(query: &str) -> IntentResult {
    detect_with_thresholds(query, 1, 1)
}

pub fn detect_with_thresholds(query: &str, ep_thr: usize, sem_thr: usize) -> IntentResult {
    let query = query.trim();
    let mut ep_signals: Vec<String> = Vec::new();
    let mut sem_signals: Vec<String> = Vec::new();

    for s in episodicas() {
        if s.pattern.is_match(query) {
            ep_signals.push(s.label.to_string());
        }
    }
    for s in semanticas() {
        if s.pattern.is_match(query) {
            sem_signals.push(s.label.to_string());
        }
    }

    let ep_count = ep_signals.len();
    let sem_count = sem_signals.len();
    let total = ep_count + sem_count;

    let (intent, confidence) = if ep_count >= ep_thr && ep_count > sem_count {
        (QueryIntent::Episodic, ep_count as f64 / total.max(1) as f64)
    } else if sem_count >= sem_thr && sem_count > ep_count {
        (
            QueryIntent::Semantic,
            sem_count as f64 / total.max(1) as f64,
        )
    } else {
        (QueryIntent::Mixed, if total > 0 { 0.5 } else { 0.3 })
    };

    let (ep_w, sem_w) = intent.weights();
    let mut matched = ep_signals;
    matched.extend(sem_signals);

    // Python: round(confidence, 3)
    let confidence = crate::context::pyjson::redondear(confidence, 3);

    IntentResult {
        intent,
        episodic_weight: ep_w,
        semantic_weight: sem_w,
        confidence,
        matched_signals: matched,
    }
}
