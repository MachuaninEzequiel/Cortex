//! Model Router inteligente (Spec 10, Purpose::ModelRouting).
//!
//! Despacha roles de subagentes (Designer, Implementer, Documenter, Auditor)
//! hacia el modelo óptimo según complejidad, costo y velocidad.
//! Fail-open: si el purpose está off o hay timeout/429, devuelve None.

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::catalog::Catalog;
use crate::purpose::Purpose;
use crate::request::JudgementRequest;
use crate::JudgementClient;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SubagentRole {
    Architect,
    Implementer,
    Documenter,
    Auditor,
}

impl SubagentRole {
    pub fn as_str(&self) -> &'static str {
        match self {
            SubagentRole::Architect => "architect",
            SubagentRole::Implementer => "implementer",
            SubagentRole::Documenter => "documenter",
            SubagentRole::Auditor => "auditor",
        }
    }
}

pub const CONFIDENCE_THRESHOLD: f64 = 0.85;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelRoutingDecision {
    pub role: SubagentRole,
    pub selected_model: String,
    pub confidence: f64,
    pub reason: String,
}

impl ModelRoutingDecision {
    pub fn is_confident(&self) -> bool {
        self.confidence >= CONFIDENCE_THRESHOLD
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpecialistOption {
    pub role: SubagentRole,
    pub subagent_name: String,
    pub description: String,
    pub eligible: bool,
    pub recommended: bool,
    pub reason: String,
}

/// "Rebuild the Menu": Genera el menú dinámico de especialistas elegibles
/// según el estado vivo de la sesión.
pub fn rebuild_specialist_menu(
    checkpoint_count: usize,
    has_unverified_claims: bool,
    has_pending_tasks: bool,
    is_closing: bool,
) -> Vec<SpecialistOption> {
    if is_closing || (!has_pending_tasks && !has_unverified_claims && checkpoint_count > 0) {
        vec![
            SpecialistOption {
                role: SubagentRole::Documenter,
                subagent_name: "cortex-documenter".into(),
                description: "Generar notas de sesión, ADRs y changelogs para el cierre canónico.".into(),
                eligible: true,
                recommended: true,
                reason: "Tareas completas y claims verificados; listo para documentar y cerrar.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Auditor,
                subagent_name: "review_checkpoint".into(),
                description: "Auditoría final y revisión de consistencia previa al cierre.".into(),
                eligible: true,
                recommended: false,
                reason: "Opcional para doble verificación antes del cierre final.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Implementer,
                subagent_name: "cortex-code-implementer".into(),
                description: "Implementador de código y refactorización.".into(),
                eligible: false,
                recommended: false,
                reason: "No hay tareas de implementación pendientes.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Architect,
                subagent_name: "cortex-code-designer".into(),
                description: "Diseñador de arquitectura y contratos.".into(),
                eligible: false,
                recommended: false,
                reason: "Fase de arquitectura ya concluida en esta sesión.".into(),
            },
        ]
    } else if has_unverified_claims {
        vec![
            SpecialistOption {
                role: SubagentRole::Auditor,
                subagent_name: "review_checkpoint".into(),
                description: "Auditoría de diffs y verificación objetiva de claims.".into(),
                eligible: true,
                recommended: true,
                reason: "Existen claims no verificados en los checkpoints recientes.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Implementer,
                subagent_name: "cortex-code-implementer".into(),
                description: "Agregar tests o ajustar código para respaldar claims.".into(),
                eligible: true,
                recommended: false,
                reason: "Permitido para corregir o agregar evidencia de tests.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Architect,
                subagent_name: "cortex-code-designer".into(),
                description: "Revisión arquitectónica si los claims fallidos exigen rediseño.".into(),
                eligible: true,
                recommended: false,
                reason: "Disponible si la discrepancia arquitectónica lo amerita.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Documenter,
                subagent_name: "cortex-documenter".into(),
                description: "Documentación de sesión.".into(),
                eligible: false,
                recommended: false,
                reason: "Bloqueado: claims no verificados impiden la documentación final.".into(),
            },
        ]
    } else if checkpoint_count == 0 {
        vec![
            SpecialistOption {
                role: SubagentRole::Architect,
                subagent_name: "cortex-code-designer".into(),
                description: "Diseñar especificación, definir contratos y redactar ADR inicial.".into(),
                eligible: true,
                recommended: true,
                reason: "Sesión recién abierta; se recomienda diseño y delimitación de alcance.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Implementer,
                subagent_name: "cortex-SDDwork".into(),
                description: "Iniciar implementación guiada por tests directamente.".into(),
                eligible: true,
                recommended: false,
                reason: "Válido si la tarea ya tiene especificación clara.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Auditor,
                subagent_name: "review_checkpoint".into(),
                description: "Auditor de claims y calidad.".into(),
                eligible: false,
                recommended: false,
                reason: "No hay checkpoints ni diffs generados aún.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Documenter,
                subagent_name: "cortex-documenter".into(),
                description: "Documentador de sesión.".into(),
                eligible: false,
                recommended: false,
                reason: "No hay avances para documentar al inicio de la sesión.".into(),
            },
        ]
    } else {
        vec![
            SpecialistOption {
                role: SubagentRole::Implementer,
                subagent_name: "cortex-code-implementer".into(),
                description: "Continuar implementación de tareas pendientes y tests.".into(),
                eligible: true,
                recommended: true,
                reason: "Sesión en curso con tareas pendientes en progreso.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Auditor,
                subagent_name: "review_checkpoint".into(),
                description: "Auditar checkpoints parciales y asegurar calidad.".into(),
                eligible: true,
                recommended: false,
                reason: "Disponible para validación intermedia de tests.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Architect,
                subagent_name: "cortex-code-designer".into(),
                description: "Refinar diseño si surgen bloqueos de arquitectura.".into(),
                eligible: true,
                recommended: false,
                reason: "Disponible para ajustes a la especificación viva.".into(),
            },
            SpecialistOption {
                role: SubagentRole::Documenter,
                subagent_name: "cortex-documenter".into(),
                description: "Documentador de sesión.".into(),
                eligible: false,
                recommended: false,
                reason: "Tareas aún en progreso; esperar antes de cerrar.".into(),
            },
        ]
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScoreDecision {
    pub score: f64,
    pub confidence: f64,
    pub reason: String,
}

impl ScoreDecision {
    pub fn is_confident(&self) -> bool {
        self.confidence >= CONFIDENCE_THRESHOLD
    }
}

/// Primitiva Score (escala 0.0..2.0) para evaluar el impacto arquitectónico de un cambio/ADR.
pub fn evaluate_adr_score(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    decision_summary: &str,
) -> Option<ScoreDecision> {
    if !client.enabled(Purpose::ModelRouting) {
        return None;
    }

    let state = serde_json::json!({
        "decision": decision_summary,
    });
    let questions = catalog.adr_score_question(decision_summary);
    let req = JudgementRequest::system_one(state, &catalog.model, questions);

    let resp = client.evaluate(&req).ok()?;
    let ans = resp.answers.get("adr_impact")?;
    let score = ans.get("score").and_then(Value::as_f64).unwrap_or(1.0);
    let confidence = ans.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
    let reason = ans
        .get("reason")
        .and_then(Value::as_str)
        .unwrap_or("Evaluated by SystemOne")
        .to_string();

    Some(ScoreDecision {
        score: score.clamp(0.0, 2.0),
        confidence,
        reason,
    })
}

/// Evalúa qué modelo de la lista de candidatos debe resolver la tarea para el rol dado.
/// Fail-open: devuelve None si Purpose::ModelRouting está off, lista vacía o error HTTP.
pub fn evaluate_model_routing(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    role: SubagentRole,
    task_description: &str,
    candidates: &[String],
) -> Option<ModelRoutingDecision> {
    if candidates.is_empty() {
        return None;
    }
    if !client.enabled(Purpose::ModelRouting) {
        return None;
    }

    // Si solo hay un candidato permitido por política, se devuelve directo
    if candidates.len() == 1 {
        return Some(ModelRoutingDecision {
            role,
            selected_model: candidates[0].clone(),
            confidence: 1.0,
            reason: "Single candidate available for active host".into(),
        });
    }

    let state = serde_json::json!({
        "role": role.as_str(),
        "task": task_description,
        "candidates": candidates,
    });

    let questions = catalog.model_routing_questions(role.as_str(), task_description, candidates);
    let req = JudgementRequest::system_one(state, &catalog.model, questions);

    let resp = client.evaluate(&req).ok()?;
    let ans = resp.answers.get("selected_model")?;
    let choice = ans.get("choice")?.as_str()?;
    let confidence = ans.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);

    Some(ModelRoutingDecision {
        role,
        selected_model: choice.to_string(),
        confidence,
        reason: format!("SystemOne routed with confidence {confidence:.2}"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::JudgementError;
    use crate::request::JudgementResponse;
    use std::sync::atomic::{AtomicUsize, Ordering};

    struct MockClient {
        enabled: bool,
        eval_fn: Box<dyn Fn(&JudgementRequest) -> Result<JudgementResponse, JudgementError> + Send + Sync>,
        calls: AtomicUsize,
    }

    impl JudgementClient for MockClient {
        fn enabled(&self, purpose: Purpose) -> bool {
            self.enabled && matches!(purpose, Purpose::ModelRouting)
        }

        fn evaluate(&self, req: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
            self.calls.fetch_add(1, Ordering::SeqCst);
            (self.eval_fn)(req)
        }
    }

    #[test]
    fn single_candidate_returns_without_http() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|_| unreachable!()),
            calls: AtomicUsize::new(0),
        };

        let decision = evaluate_model_routing(
            &client,
            &catalog,
            SubagentRole::Documenter,
            "Cerrar sesión y documentar ADR",
            &["google:gemini-2.5-flash".into()],
        )
        .unwrap();

        assert_eq!(decision.selected_model, "google:gemini-2.5-flash");
        assert_eq!(client.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn routes_between_multiple_candidates() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|_| {
                let mut answers = serde_json::Map::new();
                answers.insert(
                    "selected_model".into(),
                    serde_json::json!({
                        "choice": "google:gemini-2.5-flash",
                        "confidence": 0.94
                    }),
                );
                Ok(JudgementResponse {
                    model: "jev-1.13.0".into(),
                    answers,
                    usage: Default::default(),
                    backend: "typesafe".into(),
                })
            }),
            calls: AtomicUsize::new(0),
        };

        let candidates = vec![
            "google:gemini-2.5-pro".to_string(),
            "google:gemini-2.5-flash".to_string(),
        ];

        let decision = evaluate_model_routing(
            &client,
            &catalog,
            SubagentRole::Documenter,
            "Generar changelog conciso",
            &candidates,
        )
        .unwrap();

        assert_eq!(decision.selected_model, "google:gemini-2.5-flash");
        assert_eq!(decision.confidence, 0.94);
        assert!(decision.is_confident());
        assert_eq!(client.calls.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn rebuild_specialist_menu_lifecycle() {
        // 1. Fresh session (0 checkpoints) -> Architect recommended
        let menu_fresh = rebuild_specialist_menu(0, false, false, false);
        let arch = menu_fresh.iter().find(|s| s.role == SubagentRole::Architect).unwrap();
        assert!(arch.eligible);
        assert!(arch.recommended);
        let doc = menu_fresh.iter().find(|s| s.role == SubagentRole::Documenter).unwrap();
        assert!(!doc.eligible);

        // 2. Ongoing tasks -> Implementer recommended
        let menu_tasks = rebuild_specialist_menu(2, false, true, false);
        let impl_opt = menu_tasks.iter().find(|s| s.role == SubagentRole::Implementer).unwrap();
        assert!(impl_opt.eligible);
        assert!(impl_opt.recommended);

        // 3. Unverified claims -> Auditor recommended, Documenter blocked
        let menu_claims = rebuild_specialist_menu(3, true, true, false);
        let auditor = menu_claims.iter().find(|s| s.role == SubagentRole::Auditor).unwrap();
        assert!(auditor.eligible);
        assert!(auditor.recommended);
        let doc = menu_claims.iter().find(|s| s.role == SubagentRole::Documenter).unwrap();
        assert!(!doc.eligible);

        // 4. All done, ready to close -> Documenter recommended
        let menu_close = rebuild_specialist_menu(4, false, false, true);
        let doc = menu_close.iter().find(|s| s.role == SubagentRole::Documenter).unwrap();
        assert!(doc.eligible);
        assert!(doc.recommended);
    }

    #[test]
    fn score_primitive_evaluation() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|_| {
                let mut answers = serde_json::Map::new();
                answers.insert(
                    "adr_impact".into(),
                    serde_json::json!({
                        "score": 1.8,
                        "confidence": 0.92,
                        "reason": "Foundational architectural change in session runtime"
                    }),
                );
                Ok(JudgementResponse {
                    model: "jev-1.13.0".into(),
                    answers,
                    usage: Default::default(),
                    backend: "typesafe".into(),
                })
            }),
            calls: AtomicUsize::new(0),
        };

        let decision = evaluate_adr_score(
            &client,
            &catalog,
            "Reemplazar motor de persistencia SQLite por rocksdb inmutable",
        )
        .unwrap();

        assert_eq!(decision.score, 1.8);
        assert_eq!(decision.confidence, 0.92);
        assert!(decision.is_confident());
        assert_eq!(decision.reason, "Foundational architectural change in session runtime");
        assert_eq!(client.calls.load(Ordering::SeqCst), 1);
    }
}

