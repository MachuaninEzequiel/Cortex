//! Puerto de `cortex/context_enricher/doc_intent.py` + tabla
//! `retrieval_boost_per_intent` de `cortex/documentation/routing.py`.
//!
//! Dos capas ortogonales: QueryIntent (pesos RRF episodic-vs-semantic) y
//! DocIntent (multiplicador por doc_type dentro del vault).

use crate::semantic::routing::DocType;
use regex::Regex;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocIntent {
    Generic,
    Decision,
    Architecture,
    Runbook,
    Incident,
    Postmortem,
    History,
    Recent,
    Spec,
}

impl DocIntent {
    /// `.value` del str-enum de Python (clave del dict de boosts).
    pub fn value(self) -> &'static str {
        match self {
            DocIntent::Generic => "generic",
            DocIntent::Decision => "decision",
            DocIntent::Architecture => "architecture",
            DocIntent::Runbook => "runbook",
            DocIntent::Incident => "incident",
            DocIntent::Postmortem => "postmortem",
            DocIntent::History => "history",
            DocIntent::Recent => "recent",
            DocIntent::Spec => "spec",
        }
    }
}

struct Pat {
    re: Regex,
    label: &'static str,
}

fn pat(list: &[(&'static str, &'static str)]) -> Vec<Pat> {
    list.iter()
        .map(|(p, l)| Pat {
            // re.I de Python ⇒ case-insensitive.
            re: Regex::new(&format!("(?i){p}")).expect("regex doc_intent"),
            label: l,
        })
        .collect()
}

/// Lexicón ordenado por prioridad — el PRIMER intent con matches gana.
fn patterns() -> Vec<(DocIntent, Vec<Pat>)> {
    use DocIntent::*;
    vec![
        (
            Postmortem,
            pat(&[
                (r"\broot\s+cause\b", "root_cause"),
                (r"\bpostmortem\b", "postmortem_kw"),
                (r"\bpost[- ]?mortem\b", "postmortem_kw"),
                (r"\bwhat\s+went\s+wrong\b", "what_went_wrong"),
            ]),
        ),
        (
            Incident,
            pat(&[
                (r"\bincident\b", "incident_kw"),
                (r"\boutage\b", "outage_kw"),
                (r"\bcaida\b", "caida_kw"),
                (r"\bbroke\b", "broke_kw"),
                (r"\bfalla\b", "falla_kw"),
            ]),
        ),
        (
            Runbook,
            pat(&[
                (
                    r"\b(how\s+do\s+i|how\s+to)\s+(deploy|rollback|restart|start|stop)\b",
                    "how_to_op",
                ),
                (r"\brunbook\b", "runbook_kw"),
                (r"\bplaybook\b", "playbook_kw"),
                (r"\bprocedure\b", "procedure_kw"),
                (r"\b(deploy|rollback|provision)\b", "ops_verb"),
                (r"\bcomo\s+(arranco|despliego|reinici)", "como_op_es"),
            ]),
        ),
        (
            Decision,
            pat(&[
                (r"\bwhy\s+did\s+we\b", "why_did"),
                (r"\brationale\b", "rationale_kw"),
                (r"\bpor\s+qu[eé]\s+(decidim|elegim|optam)", "por_que_es"),
                (r"\bdecision\b", "decision_kw"),
                (r"\badr\b", "adr_kw"),
            ]),
        ),
        (
            Architecture,
            pat(&[
                (r"\barchitecture\b", "arch_kw"),
                (r"\barquitectura\b", "arch_es"),
                (r"\bdesign\b", "design_kw"),
                (r"\bdiagram\b", "diagram_kw"),
                (r"\bcomponents?\b", "components_kw"),
            ]),
        ),
        (
            Spec,
            pat(&[
                (r"\bspec(ification)?\b", "spec_kw"),
                (r"\brequirements?\b", "req_kw"),
                (r"\bacceptance\s+criteria\b", "ac_kw"),
                (r"\brequisitos\b", "req_es"),
            ]),
        ),
        (
            Recent,
            pat(&[
                (r"\b(latest|recent|today|yesterday)\b", "recent_kw"),
                (r"\b(ultim[oa]|reciente|hoy)\b", "recent_es"),
                (r"\bthis\s+(week|month)\b", "this_window"),
                (r"\besta\s+semana\b", "this_window_es"),
            ]),
        ),
        (
            History,
            pat(&[
                (r"\bwhat\s+did\s+we\b", "what_did"),
                (r"\bwhen\s+did\s+we\b", "when_did"),
                (r"\bque\s+hicimos\b", "que_hicimos"),
                (r"\blast\s+time\b", "last_time"),
                // El oráculo tiene r"\bhistor" SIN \b final (quirk fiel).
                (r"\bhistor", "history_kw"),
            ]),
        ),
    ]
}

#[derive(Debug, Clone)]
pub struct DocIntentResult {
    pub intent: DocIntent,
    pub matched_signals: Vec<&'static str>,
    pub confidence: f64,
}

/// Clasifica una query en un DocIntent vía lexicón (determinista).
pub fn detect_doc_intent(query: &str) -> DocIntentResult {
    let query = query.trim();
    if query.is_empty() {
        return DocIntentResult {
            intent: DocIntent::Generic,
            matched_signals: vec![],
            confidence: 0.0,
        };
    }
    for (intent, pats) in patterns() {
        let signals: Vec<&'static str> = pats
            .iter()
            .filter(|p| p.re.is_match(query))
            .map(|p| p.label)
            .collect();
        if !signals.is_empty() {
            let confidence = (0.5 + 0.25 * signals.len() as f64).min(1.0);
            return DocIntentResult {
                intent,
                matched_signals: signals,
                confidence: crate::context::pyjson::redondear(confidence, 3),
            };
        }
    }
    DocIntentResult {
        intent: DocIntent::Generic,
        matched_signals: vec![],
        confidence: 0.2,
    }
}

/// Tabla `retrieval_boost_per_intent` de DOC_TYPE_ROUTING — sólo los
/// intents que DocIntentDetector puede emitir (los demás valores del dict
/// Python son inalcanzables desde el enricher).
pub fn retrieval_boost(doc_type: DocType, intent: DocIntent) -> f64 {
    use crate::semantic::routing::DocType as DT;
    match (doc_type, intent) {
        (DT::Session, DocIntent::History) => 1.3,
        (DT::Session, DocIntent::Recent) => 1.5,
        // ("episodic" no es valor de DocIntent ⇒ inalcanzable)
        (DT::Handoff, DocIntent::Recent) => 2.0,
        (DT::Handoff, DocIntent::History) => 1.0,
        (DT::Spec, DocIntent::Spec) => 2.0,
        (DT::Adr, DocIntent::Decision) => 2.0,
        (DT::Adr, DocIntent::Architecture) => 1.5,
        (DT::Adr, DocIntent::History) => 1.2,
        (DT::Decision, DocIntent::Decision) => 1.5,
        (DT::Decision, DocIntent::History) => 1.2,
        (DT::Incident, DocIntent::Incident) => 2.5,
        (DT::Incident, DocIntent::Recent) => 2.0,
        (DT::Incident, DocIntent::History) => 1.5,
        (DT::Incident, DocIntent::Runbook) => 1.3,
        (DT::Postmortem, DocIntent::Postmortem) => 2.5,
        (DT::Postmortem, DocIntent::Incident) => 2.0,
        (DT::Postmortem, DocIntent::History) => 1.5,
        (DT::Runbook, DocIntent::Runbook) => 2.5,
        (DT::Runbook, DocIntent::Incident) => 1.3,
        (DT::Architecture, DocIntent::Architecture) => 2.5,
        (DT::Architecture, DocIntent::Decision) => 1.5,
        (DT::Design, DocIntent::Architecture) => 1.8,
        (DT::Design, DocIntent::Decision) => 1.5,
        _ => 0.0, // ausencia de clave en el dict → caller usa default 1.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::semantic::routing::DocType;

    #[test]
    fn prioridad_postmortem_primero() {
        let r = detect_doc_intent("what went wrong root cause analysis");
        assert_eq!(r.intent, DocIntent::Postmortem);
        assert!(r.matched_signals.contains(&"root_cause"));
        assert!(r.matched_signals.contains(&"what_went_wrong"));
        assert!((r.confidence - 1.0).abs() < 1e-9); // 0.5+0.25*2=1.0
    }

    #[test]
    fn runbook_y_decision() {
        assert_eq!(
            detect_doc_intent("how do I rollback the service").intent,
            DocIntent::Runbook
        );
        assert_eq!(
            detect_doc_intent("why did we choose RRF").intent,
            DocIntent::Decision
        );
        assert_eq!(
            detect_doc_intent("cuál fue la decisión del ADR").intent,
            DocIntent::Decision
        );
    }

    #[test]
    fn generic_vacio() {
        let r = detect_doc_intent("");
        assert_eq!(r.intent, DocIntent::Generic);
        assert!((r.confidence - 0.0).abs() < 1e-12);
        let r2 = detect_doc_intent("xyzzy plugh");
        assert_eq!(r2.intent, DocIntent::Generic);
        assert!((r2.confidence - 0.2).abs() < 1e-12);
    }

    #[test]
    fn boosts_de_la_tabla() {
        assert_eq!(retrieval_boost(DocType::Session, DocIntent::Recent), 1.5);
        assert_eq!(retrieval_boost(DocType::Adr, DocIntent::Decision), 2.0);
        assert_eq!(retrieval_boost(DocType::Runbook, DocIntent::Runbook), 2.5);
        assert_eq!(retrieval_boost(DocType::Glossary, DocIntent::History), 0.0);
    }
}
