//! Handlers MCP in-process de la familia workspace/docs/HU — porte de
//! `cortex/mcp/tools/workspace.py` (Cierre Obra 07 T1).
//!
//! Los handlers consumen un [`DocsBackend`] inyectable (producción: writers
//! canónicos P8b vía cortex-setup + WorkItemService P12A-2; gates: stubs
//! deterministas). La validación de contrato del tool (doc_type desconocido,
//! payload no-objeto, required fields por tipo y el filtrado de campos
//! desconocidos del payload) vive acá, igual que en Python.
//!
//! Wire-format exacto: `json.dumps({...}, ensure_ascii=False)` con orden de
//! inserción; mensajes ❌ byte-a-byte (incluye repr Python `'…'`).

use serde_json::{Map, Value};

// ---------------------------------------------------------------------------
// Tablas del dispatch (espejo de _DOC_TYPE_DISPATCH / _REQUIRED_BY_DOC_TYPE)
// ---------------------------------------------------------------------------

/// Los 11 doc_types routables por `cortex_write_doc` (orden alfabético, tal
/// cual lo emite `', '.join(sorted(...))` del mensaje de error).
pub const DOC_TYPES_SORTED: &[&str] = &[
    "adr",
    "architecture",
    "changelog",
    "decision",
    "glossary",
    "handoff",
    "hu",
    "incident",
    "postmortem",
    "runbook",
    "session",
];

/// Campos requeridos por tipo (fail-fast del handler; espejo exacto).
fn required_by_doc_type(doc_type: &str) -> &'static [&'static str] {
    match doc_type {
        "session" => &["title", "spec_summary", "session_id"],
        "handoff" => &["title", "parent_session_id"],
        "adr" => &["title", "context", "decision"],
        "decision" => &["title", "context", "decision"],
        "incident" => &["title", "short_description", "severity"],
        "postmortem" => &["title", "incident_path", "incident_number", "root_cause"],
        "runbook" => &["title", "runbook_kind", "procedure"],
        "architecture" => &["title", "summary"],
        "changelog" => &["title", "version"],
        "glossary" => &["title", "term", "definition"],
        "hu" => &["title", "external_id", "source"],
        _ => &[],
    }
}

/// Campos comunes de CommonWriteData.
const COMMON_FIELDS: &[&str] = &[
    "title",
    "tags",
    "links",
    "status",
    "owner",
    "team",
    "classification",
    "retention_days",
];

/// Campos de cada dataclass `*Data` (cortex/documentation/data.py): el
/// payload LLM se filtra contra esta tabla antes del writer.
fn dataclass_fields(doc_type: &str) -> Vec<&'static str> {
    let specific: &[&'static str] = match doc_type {
        "session" => &[
            "session_id",
            "spec_summary",
            "changes_made",
            "files_touched",
            "key_decisions",
            "next_steps",
            "pr",
            "branch",
            "commit",
            "verified_state",
            "unverified_claims",
            "blockers",
            "suggested_skills",
            "cortex_telemetry",
            "task_type",
            "tasks",
            "tasks_total",
            "tasks_done",
            "tasks_skipped",
            "gitless",
        ],
        "handoff" => &[
            "parent_session_id",
            "next_session_needs",
            "blockers",
            "verified_state",
            "unverified_claims",
            "suggested_skills",
            "context_required",
        ],
        "adr" => &[
            "context",
            "decision",
            "alternatives_considered",
            "consequences",
            "adr_number",
            "supersedes",
            "superseded_by",
            "acceptance_criteria_met",
        ],
        "decision" => &[
            "context",
            "decision",
            "alternative_rejected",
            "reason",
            "reversible_within_days",
        ],
        "incident" => &[
            "incident_number",
            "severity",
            "opened_at",
            "closed_at",
            "affected_services",
            "timeline",
            "impact",
            "short_description",
            "root_cause_postmortem",
        ],
        "postmortem" => &[
            "incident_number",
            "incident_path",
            "root_cause",
            "contributing_factors",
            "what_went_well",
            "what_went_wrong",
            "action_items",
            "timeline",
            "severity",
        ],
        "runbook" => &[
            "runbook_kind",
            "description",
            "prerequisites",
            "procedure",
            "rollback_procedure",
            "verification",
            "applies_to",
            "estimated_duration_minutes",
            "last_verified_at",
        ],
        "architecture" => &[
            "summary",
            "components",
            "diagrams",
            "contracts",
            "rationale",
            "related_adrs",
        ],
        "changelog" => &[
            "version",
            "release_date",
            "added",
            "changed",
            "deprecated",
            "removed",
            "fixed",
            "security",
        ],
        "glossary" => &["term", "definition", "examples", "related_terms", "domain"],
        "hu" => &[
            "external_id",
            "source",
            "kind",
            "description",
            "acceptance_criteria",
            "assignee",
            "external_url",
            "synced_at",
        ],
        _ => &[],
    };
    let mut all = COMMON_FIELDS.to_vec();
    all.extend_from_slice(specific);
    all
}

// ---------------------------------------------------------------------------
// Backend inyectable
// ---------------------------------------------------------------------------

/// Errores diferenciados del backend de escritura:
/// - `Schema`: SchemaValidationError → `"❌ {msg}"`.
/// - `Type`: TypeError → `"❌ Invalid payload for doc_type='{t}': {msg}"`.
/// - `Runtime`: cualquier otra excepción Python (DuplicateDocumentError,
///   OSError…) → sube al dispatcher (`"Error ejecutando …"`).
#[derive(Debug, Clone)]
pub enum DocsError {
    Schema(String),
    Type(String),
    Runtime(String),
}

pub trait DocsBackend {
    /// Espejo de `writer(data, vault=vault, vault_scope=…, overwrite=…)`.
    /// Recibe el payload ya filtrado a campos válidos del dataclass.
    fn write_doc(
        &mut self,
        doc_type: &str,
        clean_payload: Map<String, Value>,
        vault_scope: &str,
        overwrite: bool,
    ) -> Result<String, DocsError>;

    /// Espejo de `write_design_note_canonical(data, vault=vault)`
    /// (local-only por defecto; sin vault_scope/overwrite desde el tool).
    fn write_design_note(&mut self, data: DesignDocInput) -> Result<String, DocsError>;

    /// Espejo de `memory.import_work_item(external_id, provider=…, remember=…)`.
    fn import_hu(
        &mut self,
        external_id: &str,
        provider: &str,
        remember: bool,
    ) -> Result<String, String>;

    /// Espejo de `memory.get_work_item_note(item_id)`.
    fn get_hu(&mut self, item_id: &str) -> Result<String, String>;
}

/// Espejo de `DesignDocData` construido por el handler (defaults aplicados).
#[derive(Debug, Clone, Default)]
pub struct DesignDocInput {
    pub title: String,
    pub tags: Vec<String>,
    pub status: String,
    pub session_id: String,
    pub spec_path: String,
    pub architecture_decision: String,
    pub data_model_changes: Vec<String>,
    pub api_contracts: Vec<String>,
    pub test_plan: Vec<String>,
    pub risks: Vec<String>,
}

// ---------------------------------------------------------------------------
// Handlers (formatos espejo exactos de workspace.py)
// ---------------------------------------------------------------------------

fn s(args: &Value, key: &str) -> String {
    args.get(key)
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string()
}

fn strings(args: &Value, key: &str) -> Vec<String> {
    match args.get(key) {
        Some(Value::Array(arr)) => arr
            .iter()
            .filter_map(Value::as_str)
            .map(str::to_string)
            .collect(),
        _ => Vec::new(),
    }
}

/// `json.dumps(payload, ensure_ascii=False)` compacto con orden de
/// inserción (reuso del emisor canónico P12A-9).
use crate::handlers_sessions::to_string_ensure_ascii_false;

/// Tool `write_design_note_canonical`.
pub fn write_design_note_text(
    b: &mut dyn DocsBackend,
    arguments: &Value,
) -> Result<String, String> {
    let title = s(arguments, "title");
    let session_id = s(arguments, "session_id");
    let spec_path = s(arguments, "spec_path");
    if session_id.is_empty() {
        return Ok("❌ session_id is required for write_design_note_canonical.".into());
    }
    if spec_path.is_empty() {
        return Ok("❌ spec_path is required for write_design_note_canonical.".into());
    }

    let status_raw = arguments
        .get("status")
        .and_then(Value::as_str)
        .map(str::to_string)
        .unwrap_or_else(|| "draft".to_string());

    let data = DesignDocInput {
        title: if title.is_empty() {
            format!("Design for {session_id}")
        } else {
            title
        },
        tags: strings(arguments, "tags"),
        status: status_raw,
        session_id,
        spec_path,
        architecture_decision: arguments
            .get("architecture_decision")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string(),
        data_model_changes: strings(arguments, "data_model_changes"),
        api_contracts: strings(arguments, "api_contracts"),
        test_plan: strings(arguments, "test_plan"),
        risks: strings(arguments, "risks"),
    };

    match b.write_design_note(data) {
        Ok(path) => Ok(to_string_ensure_ascii_false(
            &serde_json::json!({ "path": path }),
        )),
        Err(DocsError::Schema(m)) => Ok(format!("❌ {m}")),
        Err(DocsError::Type(m)) => Ok(format!("❌ Invalid payload for design: {m}")),
        Err(DocsError::Runtime(m)) => Err(m),
    }
}

/// Tool `cortex_write_doc`: dispatch sobre los 11 writers canónicos.
pub fn write_doc_text(b: &mut dyn DocsBackend, arguments: &Value) -> Result<String, String> {
    let doc_type = s(arguments, "doc_type");
    if !DOC_TYPES_SORTED.contains(&doc_type.as_str()) {
        return Ok(format!(
            "❌ Unknown doc_type '{}'. Must be one of: {}.",
            doc_type,
            DOC_TYPES_SORTED.join(", ")
        ));
    }

    // `payload = arguments.get("payload") or {}`: los valores falsy ({},
    // null, "", 0, False) caen al dict vacío; los truthy no-objeto fallan.
    let is_truthy = |v: &Value| -> bool {
        match v {
            Value::Null => false,
            Value::Bool(b) => *b,
            Value::Number(n) => n.as_f64().map(|f| f != 0.0).unwrap_or(false),
            Value::String(s) => !s.is_empty(),
            Value::Array(a) => !a.is_empty(),
            Value::Object(o) => !o.is_empty(),
        }
    };
    let payload: Map<String, Value> = match arguments.get("payload") {
        None | Some(Value::Null) => Map::new(),
        Some(v) if !is_truthy(v) => Map::new(),
        Some(Value::Object(m)) => m.clone(),
        Some(_) => return Ok("❌ 'payload' must be an object.".into()),
    };

    // Fail-fast de campos requeridos (truthiness de Python).
    let mut missing: Vec<String> = Vec::new();
    for f in required_by_doc_type(&doc_type) {
        let truthy = payload
            .get(*f)
            .map(|x| python_truthy(Some(x)))
            .unwrap_or(false);
        if !truthy {
            missing.push((*f).to_string());
        }
    }
    if !missing.is_empty() {
        return Ok(format!(
            "❌ payload for doc_type='{}' is missing required field(s): {}. See the tool description for the full per-type contract.",
            doc_type,
            missing.join(", ")
        ));
    }

    let vault_scope = match arguments.get("vault_scope") {
        None | Some(Value::Null) => "local".to_string(),
        Some(Value::String(vs)) => vs.clone(),
        Some(other) => other.to_string(),
    };
    let overwrite = python_truthy(arguments.get("overwrite"));

    // Filtrado de campos desconocidos (dataclass **clean_payload).
    let valid = dataclass_fields(&doc_type);
    let clean: Map<String, Value> = payload
        .into_iter()
        .filter(|(k, _)| valid.contains(&k.as_str()))
        .collect();

    match b.write_doc(&doc_type, clean, &vault_scope, overwrite) {
        Ok(path) => Ok(to_string_ensure_ascii_false(
            &serde_json::json!({ "path": path, "doc_type": doc_type }),
        )),
        Err(DocsError::Schema(m)) => Ok(format!("❌ {m}")),
        Err(DocsError::Type(m)) => Ok(format!(
            "❌ Invalid payload for doc_type='{}': {}",
            doc_type, m
        )),
        Err(DocsError::Runtime(m)) => Err(m),
    }
}

/// Truthiness de Python (compartido conceptualmente con handlers_search).
fn python_truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_f64().map(|f| f != 0.0).unwrap_or(false),
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

/// Tool `cortex_import_hu`.
pub fn import_hu_text(b: &mut dyn DocsBackend, arguments: &Value) -> Result<String, String> {
    let external_id = match arguments.get("external_id") {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(s)) => s.clone(),
        Some(Value::Number(n)) => n.to_string(),
        _ => String::new(),
    };
    let provider = match arguments.get("provider") {
        None | Some(Value::Null) => "jira".to_string(),
        Some(Value::String(s)) if s.is_empty() => "jira".to_string(),
        Some(Value::String(s)) => s.clone(),
        _ => "jira".to_string(),
    };
    let no_remember = python_truthy(arguments.get("no_remember"));
    let path = b.import_hu(&external_id, &provider, !no_remember)?;
    Ok(format!("Tracked item imported -> {path}"))
}

/// Tool `cortex_get_hu`.
pub fn get_hu_text(b: &mut dyn DocsBackend, arguments: &Value) -> Result<String, String> {
    let item_id = match arguments.get("item_id") {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(s)) => s.clone(),
        Some(Value::Number(n)) => n.to_string(),
        _ => String::new(),
    };
    let path = b.get_hu(&item_id)?;
    Ok(format!("Tracked item note -> {path}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doc_type_desconocido_lista_sorted() {
        struct N;
        impl DocsBackend for N {
            fn write_doc(
                &mut self,
                _: &str,
                _: Map<String, Value>,
                _: &str,
                _: bool,
            ) -> Result<String, DocsError> {
                unreachable!()
            }
            fn write_design_note(&mut self, _: DesignDocInput) -> Result<String, DocsError> {
                unreachable!()
            }
            fn import_hu(&mut self, _: &str, _: &str, _: bool) -> Result<String, String> {
                unreachable!()
            }
            fn get_hu(&mut self, _: &str) -> Result<String, String> {
                unreachable!()
            }
        }
        let out = write_doc_text(&mut N, &serde_json::json!({"doc_type": "zzz"})).unwrap();
        assert_eq!(
            out,
            "❌ Unknown doc_type 'zzz'. Must be one of: adr, architecture, changelog, decision, glossary, handoff, hu, incident, postmortem, runbook, session."
        );
    }

    #[test]
    fn payload_no_objeto() {
        struct N;
        impl DocsBackend for N {
            fn write_doc(
                &mut self,
                _: &str,
                _: Map<String, Value>,
                _: &str,
                _: bool,
            ) -> Result<String, DocsError> {
                unreachable!()
            }
            fn write_design_note(&mut self, _: DesignDocInput) -> Result<String, DocsError> {
                unreachable!()
            }
            fn import_hu(&mut self, _: &str, _: &str, _: bool) -> Result<String, String> {
                unreachable!()
            }
            fn get_hu(&mut self, _: &str) -> Result<String, String> {
                unreachable!()
            }
        }
        let out = write_doc_text(
            &mut N,
            &serde_json::json!({"doc_type": "adr", "payload": [1]}),
        )
        .unwrap();
        assert_eq!(out, "❌ 'payload' must be an object.");
    }

    #[test]
    fn required_fields_faltantes() {
        struct N;
        impl DocsBackend for N {
            fn write_doc(
                &mut self,
                _: &str,
                _: Map<String, Value>,
                _: &str,
                _: bool,
            ) -> Result<String, DocsError> {
                unreachable!()
            }
            fn write_design_note(&mut self, _: DesignDocInput) -> Result<String, DocsError> {
                unreachable!()
            }
            fn import_hu(&mut self, _: &str, _: &str, _: bool) -> Result<String, String> {
                unreachable!()
            }
            fn get_hu(&mut self, _: &str) -> Result<String, String> {
                unreachable!()
            }
        }
        let out = write_doc_text(
            &mut N,
            &serde_json::json!({"doc_type": "changelog", "payload": {"version": ""}}),
        )
        .unwrap();
        assert_eq!(
            out,
            "❌ payload for doc_type='changelog' is missing required field(s): title, version. See the tool description for the full per-type contract."
        );
    }
}
