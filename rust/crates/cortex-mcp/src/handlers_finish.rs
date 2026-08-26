//! Handlers MCP in-process de finish_session / documenter_briefing — porte
//! de `cortex/mcp/tools/documenter.py` (Cierre Obra 07 T1).
//!
//! El backend ([`FinishBackend`]) reproduce el par reconstructor/persister
//! (producción: cortex-app::documenter P5 + services; gates: stubs). La
//! serialización `_serialize_reconstruction` vive acá porque es parte del
//! wire-format del tool (`json.dumps(..., ensure_ascii=False)`, orden de
//! claves del dict literal de Python, `required` derivado por nombre del
//! hook con default True).

use serde_json::{json, Value};

/// Espejo de un `VerificationHook` del spec.
#[derive(Debug, Clone, Default)]
pub struct SpecHookMirror {
    pub name: String,
    pub command: String,
    pub required: bool,
    pub success_criteria: String,
    pub timeout_seconds: i64,
}

#[derive(Debug, Clone, Default)]
pub struct SpecInfoMirror {
    /// Path POSIX.
    pub path: String,
    pub title: String,
    pub goal: String,
    pub files_in_scope: Vec<String>,
    pub constraints: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub verification_hooks: Vec<SpecHookMirror>,
}

#[derive(Debug, Clone, Default)]
pub struct DiffEntryMirror {
    pub action: String,
    pub path: String,
}

#[derive(Debug, Clone, Default)]
pub struct VerifResultMirror {
    pub name: String,
    pub command: String,
    pub passed: bool,
    pub exit_code: i64,
    pub output: String,
    pub duration_ms: i64,
    /// ISO del run_at.
    pub run_at: String,
}

#[derive(Debug, Clone, Default)]
pub struct ContradictionMirror {
    pub prior_record: String,
    pub current_claim: String,
    pub evidence: Vec<String>,
    pub severity: String,
}

#[derive(Debug, Clone, Default)]
pub struct AdrSuggestionMirror {
    pub title: String,
    pub rationale: String,
    pub source_checkpoint_index: Option<i64>,
    pub evidence: Vec<String>,
    pub confidence: f64,
}

#[derive(Debug, Clone, Default)]
pub struct RawCheckpointMirror {
    pub timestamp: String,
    pub source: String,
    pub verified_claims: Vec<String>,
    pub unverified_claims: Vec<String>,
    pub artifacts_touched: Vec<String>,
    pub note: String,
}

/// Espejo tipado de `ReconstructionOutput` reducido a lo que serializa el
/// tool.
#[derive(Debug, Clone, Default)]
pub struct ReconstructionMirror {
    pub session_id: String,
    pub spec: SpecInfoMirror,
    pub diff_text: String,
    pub diff_entries: Vec<DiffEntryMirror>,
    pub files_touched: Vec<String>,
    pub files_verified_by_git: Vec<String>,
    pub files_declared_only: Vec<String>,
    pub in_scope_files: Vec<String>,
    pub out_of_scope_files: Vec<String>,
    pub unimplemented_files: Vec<String>,
    pub verification_results: Vec<VerifResultMirror>,
    pub contradictions: Vec<ContradictionMirror>,
    pub suggested_status: String,
    pub suggested_adrs: Vec<AdrSuggestionMirror>,
    pub raw_checkpoints: Vec<RawCheckpointMirror>,
    pub end_commit: String,
    pub gitless: bool,
}

/// Espejo del resultado del persister (`DocumenterPersister.finalize`).
#[derive(Debug, Clone, Default)]
pub struct FinishResultMirror {
    pub session_id: String,
    pub final_status: String,
    pub session_note_path: Option<String>,
    pub adrs_created: Vec<String>,
    pub summary_text: String,
    pub already_closed: bool,
}

pub trait FinishBackend {
    fn get_active_session_id(&mut self) -> Result<Option<String>, String>;
    /// Estado de la sesión ("open" | "closed" | "handoff" | "abandoned");
    /// Err cuando la sesión no existe (excepción Python ⇒ dispatcher).
    fn get_session_status(&mut self, session_id: &str) -> Result<String, String>;
    fn reconstruct(
        &mut self,
        session_id: &str,
        run_hooks: bool,
    ) -> Result<ReconstructionMirror, String>;
    fn finalize(
        &mut self,
        session_id: &str,
        forced_status: Option<&str>,
    ) -> Result<FinishResultMirror, String>;
}

// ---------------------------------------------------------------------------
// Serialización byte-parity (_serialize_reconstruction)
// ---------------------------------------------------------------------------

pub fn serialize_reconstruction(out: &ReconstructionMirror) -> Value {
    // required por nombre del hook del spec; default True conservador.
    let required_by_name: std::collections::HashMap<&str, bool> = out
        .spec
        .verification_hooks
        .iter()
        .map(|h| (h.name.as_str(), h.required))
        .collect();

    json!({
        "session_id": out.session_id,
        "spec": {
            "path": out.spec.path,
            "title": out.spec.title,
            "goal": out.spec.goal,
            "files_in_scope": out.spec.files_in_scope,
            "constraints": out.spec.constraints,
            "acceptance_criteria": out.spec.acceptance_criteria,
            "verification_hooks": out.spec.verification_hooks.iter().map(|h| json!({
                "name": h.name,
                "command": h.command,
                "required": h.required,
                "success_criteria": h.success_criteria,
                "timeout_seconds": h.timeout_seconds,
            })).collect::<Vec<_>>(),
        },
        "diff_text": out.diff_text,
        "diff_entries": out.diff_entries.iter().map(|e| json!({
            "action": e.action,
            "path": e.path,
        })).collect::<Vec<_>>(),
        "files_touched": out.files_touched,
        "files_verified_by_git": out.files_verified_by_git,
        "files_declared_only": out.files_declared_only,
        "in_scope_files": out.in_scope_files,
        "out_of_scope_files": out.out_of_scope_files,
        "unimplemented_files": out.unimplemented_files,
        "verification_results": out.verification_results.iter().map(|r| {
            let required = required_by_name.get(r.name.as_str()).copied().unwrap_or(true);
            json!({
                "name": r.name,
                "command": r.command,
                "passed": r.passed,
                "exit_code": r.exit_code,
                "output": r.output,
                "duration_ms": r.duration_ms,
                "run_at": r.run_at,
                "required": required,
            })
        }).collect::<Vec<_>>(),
        "contradictions": out.contradictions.iter().map(|c| json!({
            "prior_record": c.prior_record,
            "current_claim": c.current_claim,
            "evidence": c.evidence,
            "severity": c.severity,
        })).collect::<Vec<_>>(),
        "suggested_status": out.suggested_status,
        "suggested_adrs": out.suggested_adrs.iter().map(|a| json!({
            "title": a.title,
            "rationale": a.rationale,
            "source_checkpoint_index": a.source_checkpoint_index,
            "evidence": a.evidence,
            "confidence": a.confidence,
        })).collect::<Vec<_>>(),
        "raw_checkpoints": out.raw_checkpoints.iter().map(|cp| json!({
            "timestamp": cp.timestamp,
            "source": cp.source,
            "verified_claims": cp.verified_claims,
            "unverified_claims": cp.unverified_claims,
            "artifacts_touched": cp.artifacts_touched,
            "note": cp.note,
        })).collect::<Vec<_>>(),
        "end_commit": out.end_commit,
        "gitless": out.gitless,
    })
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

fn truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_f64().map(|f| f != 0.0).unwrap_or(false),
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

/// Resolución de session_id estilo Python:
/// `raw_id is None or not str(raw_id).strip()` ⇒ activo o error estándar
/// (el error es TEXTO de tool en Python, no excepción).
fn resolve_from_args(
    b: &mut dyn FinishBackend,
    args: &Value,
) -> Result<Result<String, String>, String> {
    let raw: Option<String> = match args.get("session_id") {
        None | Some(Value::Null) => None,
        Some(v) => Some(py_str_value(Some(v))),
    };
    match raw.as_deref().map(str::trim) {
        None | Some("") => match b.get_active_session_id()? {
            Some(id) => Ok(Ok(id)),
            None => Ok(Err(
                "❌ No active session. Pass session_id explicitly.".to_string()
            )),
        },
        Some(id) => Ok(Ok(id.to_string())),
    }
}

/// `str(v)` de Python sobre un JSON Value.
fn py_str_value(v: Option<&Value>) -> String {
    match v {
        None | Some(Value::Null) => "None".to_string(),
        Some(Value::String(s)) => s.clone(),
        Some(Value::Bool(true)) => "True".to_string(),
        Some(Value::Bool(false)) => "False".to_string(),
        Some(other) => other.to_string(),
    }
}

/// Tool `cortex_finish_session`: pipeline auto (el modo interactivo es
/// CLI-only por diseño del protocolo).
pub fn finish_session_text(b: &mut dyn FinishBackend, arguments: &Value) -> Result<String, String> {
    if truthy(arguments.get("interactive")) {
        return Ok("❌ The interactive documenter mode is CLI-only. Run `cortex finish-session --interactive` instead, or omit `interactive` from this tool call.".into());
    }

    // `intent = str(arguments.get("intent") or "auto").strip()`: los valores
    // falsy caen a "auto"; los truthy no-string se strinifican como Python.
    let intent = if truthy(arguments.get("intent")) {
        py_str_value(arguments.get("intent")).trim().to_string()
    } else {
        "auto".to_string()
    };
    let reason = if truthy(arguments.get("reason")) {
        py_str_value(arguments.get("reason")).trim().to_string()
    } else {
        String::new()
    };

    if !crate::handlers_spec::VALID_FINISH_INTENTS.contains(&intent.as_str()) {
        return Ok(format!(
            "❌ Invalid intent '{}'. Must be one of: {}",
            intent,
            crate::handlers_spec::VALID_FINISH_INTENTS.join(", ")
        ));
    }
    if intent != "auto" && reason.is_empty() {
        return Ok(format!(
            "❌ 'reason' is required when intent is '{intent}'."
        ));
    }

    let session_id = match resolve_from_args(b, arguments)? {
        Ok(id) => id,
        Err(msg) => return Ok(msg),
    };

    let status = b.get_session_status(&session_id)?;
    if status != "open" {
        return Ok(format!(
            "❌ Session '{}' is already in status '{}'; nothing to finish.",
            session_id, status
        ));
    }

    let forced_status = match intent.as_str() {
        "abandon" => Some("abandoned"),
        "handoff" => Some("handoff"),
        _ => None,
    };

    let result = b.finalize(&session_id, forced_status)?;
    let payload = json!({
        "session_id": result.session_id,
        "final_status": result.final_status,
        "session_note_path": result.session_note_path,
        "adrs_created": result.adrs_created,
        "summary_text": result.summary_text,
        "already_closed": result.already_closed,
    });
    Ok(crate::handlers_sessions::to_string_ensure_ascii_false(
        &payload,
    ))
}

/// Tool `cortex_documenter_briefing`: reconstrucción read-only completa.
pub fn documenter_briefing_text(
    b: &mut dyn FinishBackend,
    arguments: &Value,
) -> Result<String, String> {
    let session_id = match resolve_from_args(b, arguments)? {
        Ok(id) => id,
        Err(msg) => return Ok(msg),
    };
    let run_hooks = truthy(arguments.get("run_hooks"));
    let out = b.reconstruct(&session_id, run_hooks)?;
    Ok(crate::handlers_sessions::to_string_ensure_ascii_false(
        &serialize_reconstruction(&out),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn intent_invalido() {
        struct NB;
        impl FinishBackend for NB {
            fn get_active_session_id(&mut self) -> Result<Option<String>, String> {
                Ok(None)
            }
            fn get_session_status(&mut self, _: &str) -> Result<String, String> {
                unreachable!()
            }
            fn reconstruct(&mut self, _: &str, _: bool) -> Result<ReconstructionMirror, String> {
                unreachable!()
            }
            fn finalize(&mut self, _: &str, _: Option<&str>) -> Result<FinishResultMirror, String> {
                unreachable!()
            }
        }
        let out = finish_session_text(&mut NB, &serde_json::json!({"intent": "bogus"})).unwrap();
        assert_eq!(
            out,
            "❌ Invalid intent 'bogus'. Must be one of: auto, handoff, abandon"
        );
        let out = finish_session_text(&mut NB, &serde_json::json!({"intent": "handoff"})).unwrap();
        assert_eq!(out, "❌ 'reason' is required when intent is 'handoff'.");
        let out = finish_session_text(&mut NB, &serde_json::json!({})).unwrap();
        assert_eq!(out, "❌ No active session. Pass session_id explicitly.");
    }

    #[test]
    fn serializacion_orden_pydict() {
        let out = ReconstructionMirror {
            session_id: "2026-05-16_demo".into(),
            gitless: true,
            ..Default::default()
        };
        let v = serialize_reconstruction(&out);
        assert_eq!(
            crate::handlers_sessions::to_string_ensure_ascii_false(&v),
            "{\"session_id\": \"2026-05-16_demo\", \"spec\": {\"path\": \"\", \"title\": \"\", \"goal\": \"\", \"files_in_scope\": [], \"constraints\": [], \"acceptance_criteria\": [], \"verification_hooks\": []}, \"diff_text\": \"\", \"diff_entries\": [], \"files_touched\": [], \"files_verified_by_git\": [], \"files_declared_only\": [], \"in_scope_files\": [], \"out_of_scope_files\": [], \"unimplemented_files\": [], \"verification_results\": [], \"contradictions\": [], \"suggested_status\": \"\", \"suggested_adrs\": [], \"raw_checkpoints\": [], \"end_commit\": \"\", \"gitless\": true}"
        );
    }
}
