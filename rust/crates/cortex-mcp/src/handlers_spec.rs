//! Handlers MCP in-process de la familia spec/proposal/self-review — porte
//! de `cortex/mcp/tools/documenter.py` (Cierre Obra 07 T1).
//!
//! Incluye:
//! - `cortex_emit_proposal`: validación pydantic-fiel de `Proposal`
//!   (mensajes de ValidationError byte-a-byte, incluido el truncado de
//!   `input_value` de pydantic-core: repr > 50 ⇒ primeros 25 + "..." +
//!   últimos 24) y `format_proposal_card`.
//! - `cortex_create_spec`: guard de gobernanza (`called_tools`) + gap
//!   mínimo 2.0s entre proposal y confirmación (reloj inyectado por el
//!   server) + [`SpecBackend`] inyectable (producción: SpecService
//!   P12A-5).
//! - `cortex_self_review_note`: inspección pura (tokens placeholder +
//!   claims huecos). Los fixtures del gate usan UN solo token por caso,
//!   así el orden de iteración del frozenset Python es irrelevante.

use std::collections::BTreeSet;

use serde_json::{Map, Value};

use crate::handlers_sessions::to_string_ensure_ascii_false;

// ---------------------------------------------------------------------------
// Mensajes canónicos (NO duplicar: contrato único testeado)
// ---------------------------------------------------------------------------

pub const GOVERNANCE_VIOLATION_MESSAGE: &str = concat!(
    "❌ **VIOLACIÓN DE GOBERNANZA**: cortex_create_spec fue llamado sin ",
    "ejecutar primero cortex_sync_ticket.\n\n",
    "Según las reglas de Cortex v2.0, cortex-sync DEBE llamar a ",
    "cortex_sync_ticket como PRIMER paso para inyectar contexto histórico ",
    "vía ONNX/hybrid retrieval antes de crear cualquier spec.\n\n",
    "Por favor, corrige el flujo:\n",
    "1. Llama a cortex_sync_ticket con el pedido del usuario\n",
    "2. Luego llama a cortex_create_spec"
);

pub const PROPOSAL_MIN_GAP_SECONDS: f64 = 2.0;

const PLACEHOLDER_TOKENS: &[&str] = &[
    "tbd",
    "todo",
    "fixme",
    "xxx",
    "???",
    "fill me",
    "[pendiente]",
];

const SUCCESS_CLAIM_PATTERNS: &[&str] = &[
    "tests pass",
    "test passed",
    "tests passed",
    "build exitoso",
    "build successful",
    "linter clean",
    "lint passed",
    "checks pass",
    "ci passed",
];

pub const VALID_FINISH_INTENTS: &[&str] = &["auto", "handoff", "abandon"];

// ---------------------------------------------------------------------------
// Backend inyectable de specs
// ---------------------------------------------------------------------------

/// Espejo de `SpecCreationResult` (path + sesión auto-abierta opcional).
#[derive(Debug, Clone)]
pub struct SpecResultMirror {
    pub path: String,
    /// `session.is_gitless` cuando hay sesión; None si el doble de test
    /// devuelve un Path pelado (Python lo tolera).
    pub session_gitless: Option<bool>,
}

#[derive(Debug, Clone)]
pub enum SpecError {
    /// ValueError → `"❌ {msg}"`.
    Value(String),
    /// DuplicateDocumentError → mensaje ℹ️ multilínea (no marca degraded).
    DuplicateDocument(String),
}

/// Request de creación (espejo del kwargs de memory.create_spec_note).
#[derive(Debug, Clone, Default)]
pub struct SpecCreateRequest {
    pub title: String,
    pub goal: String,
    pub requirements: Vec<String>,
    pub files_in_scope: Vec<String>,
    pub constraints: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub tags: Vec<String>,
    /// Hooks tal cual llegan (lista de objetos); la normalización vive en
    /// SpecService (gateada en P12A-5).
    pub verification_hooks: Vec<Value>,
    pub sync_vault: bool,
    pub proposal_mode: String,
    pub proposal_confirmed: bool,
}

pub trait SpecBackend {
    fn create_spec_note(&mut self, req: &SpecCreateRequest) -> Result<SpecResultMirror, SpecError>;
}

/// Estado transversal del server que la familia spec consume/muta.
#[derive(Debug, Default)]
pub struct SpecServerState {
    /// Espejo de `_called_tools` (guard de gobernanza).
    pub called_tools: BTreeSet<String>,
    /// Epoch seconds del último `cortex_emit_proposal` (gap required).
    pub last_proposal_emitted_epoch: Option<f64>,
}

// ---------------------------------------------------------------------------
// repr de Python para valores JSON (mensajes de error)
// ---------------------------------------------------------------------------

/// `repr(v)` de Python para strings/numeros/bools/null/listas/dicts planos.
pub fn python_repr(v: &Value) -> String {
    match v {
        Value::String(s) => python_repr_str(s),
        Value::Bool(true) => "True".into(),
        Value::Bool(false) => "False".into(),
        Value::Null => "None".into(),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.to_string()
            } else if let Some(f) = n.as_f64() {
                crate::pyjson::py_float_repr(f)
            } else {
                n.to_string()
            }
        }
        Value::Array(items) => {
            let inner: Vec<String> = items.iter().map(python_repr).collect();
            format!("[{}]", inner.join(", "))
        }
        Value::Object(map) => {
            let inner: Vec<String> = map
                .iter()
                .map(|(k, val)| format!("{}: {}", python_repr_str(k), python_repr(val)))
                .collect();
            format!("{{{}}}", inner.join(", "))
        }
    }
}

/// repr de un string Python: comillas simples, `'` escapada, unicode crudo.
fn python_repr_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('\'');
    for c in s.chars() {
        match c {
            '\'' => out.push_str("\\'"),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('\'');
    out
}

/// Truncado de `input_value` de pydantic-core: si el repr supera 50
/// caracteres ⇒ primeros 25 + "..." + últimos 24 (total 52; medido contra
/// pydantic 2.13.4 real).
fn truncate_repr(repr: String) -> String {
    if repr.chars().count() > 50 {
        let chars: Vec<char> = repr.chars().collect();
        let head: String = chars[..25].iter().collect();
        let tail: String = chars[chars.len() - 24..].iter().collect();
        format!("{head}...{tail}")
    } else {
        repr
    }
}

/// Nombre de tipo Python para input_type.
fn python_input_type(v: &Value) -> &'static str {
    match v {
        Value::Null => "NoneType",
        Value::Bool(_) => "bool",
        Value::Number(n) if n.is_i64() || n.is_u64() => "int",
        Value::Number(_) => "float",
        Value::String(_) => "str",
        Value::Array(_) => "list",
        Value::Object(_) => "dict",
    }
}

// ---------------------------------------------------------------------------
// Réplica de ValidationError de pydantic v2
// ---------------------------------------------------------------------------

struct ErrEntry {
    loc: String,
    msg: String,
    kind: &'static str,
    input_repr: String,
    input_type: &'static str,
}

/// Constructor de errores acumulados con el formato exacto de pydantic
/// 2.13.4 (verificado empíricamente):
///
/// ```text
/// {n} validation error{s} for Proposal
/// {loc}                       ← línea ausente si loc vacío
///   {msg} [type={kind}, input_value={repr}, input_type={t}]
///     For further information visit https://errors.pydantic.dev/2.13/v/{kind}
/// ```
struct ValidationCollector {
    entries: Vec<ErrEntry>,
}

impl ValidationCollector {
    fn new() -> Self {
        ValidationCollector {
            entries: Vec::new(),
        }
    }
    fn add(&mut self, loc: &str, msg: String, kind: &'static str, input: &Value) {
        self.entries.push(ErrEntry {
            loc: loc.to_string(),
            msg,
            kind,
            input_repr: truncate_repr(python_repr(input)),
            input_type: python_input_type(input),
        });
    }
    fn add_raw(
        &mut self,
        loc: &str,
        msg: String,
        kind: &'static str,
        input_repr: String,
        input_type: &'static str,
    ) {
        self.entries.push(ErrEntry {
            loc: loc.to_string(),
            msg,
            kind,
            input_repr,
            input_type,
        });
    }
    fn render(self) -> String {
        let n = self.entries.len();
        let mut out = format!(
            "{} validation error{} for Proposal\n",
            n,
            if n == 1 { "" } else { "s" }
        );
        for e in &self.entries {
            if !e.loc.is_empty() {
                out.push_str(&e.loc);
                out.push('\n');
            }
            out.push_str(&format!(
                "  {} [type={}, input_value={}, input_type={}]\n",
                e.msg, e.kind, e.input_repr, e.input_type
            ));
            out.push_str(&format!(
                "    For further information visit https://errors.pydantic.dev/2.13/v/{}\n",
                e.kind
            ));
        }
        // pydantic NO agrega \n final al str(exc).
        out.trim_end_matches('\n').to_string()
    }
}

/// Chequeo de campo string con min/max (errores string_too_short/long).
fn validate_str_field(
    col: &mut ValidationCollector,
    loc: &str,
    v: &Value,
    min: usize,
    max: usize,
) -> Option<String> {
    match v {
        Value::String(s) => {
            let len = s.chars().count();
            if len < min {
                col.add(
                    loc,
                    format!(
                        "String should have at least {min} character{}",
                        if min == 1 { "" } else { "s" }
                    ),
                    "string_too_short",
                    v,
                );
                None
            } else if len > max {
                col.add(
                    loc,
                    format!("String should have at most {max} characters"),
                    "string_too_long",
                    v,
                );
                None
            } else {
                Some(s.clone())
            }
        }
        other => {
            col.add(
                loc,
                "Input should be a valid string".to_string(),
                "string_type",
                other,
            );
            None
        }
    }
}

/// Validación de un ítem Alternative (loc prefijo `alternatives.{i}`).
/// Devuelve (id, description, rejected_reason) cuando es válido.
fn validate_alternative(
    col: &mut ValidationCollector,
    idx: usize,
    v: &Value,
) -> Option<(String, String, String)> {
    let obj = match v {
        Value::Object(m) => m,
        other => {
            col.add(
                &format!("alternatives.{idx}"),
                "Input should be a valid dictionary or instance of Alternative".to_string(),
                "model_type",
                other,
            );
            return None;
        }
    };
    // extra="forbid": claves desconocidas.
    for (k, ev) in obj.iter() {
        if !["id", "description", "rejected_reason"].contains(&k.as_str()) {
            col.add(
                &format!("alternatives.{idx}.{k}"),
                "Extra inputs are not permitted".to_string(),
                "extra_forbidden",
                ev,
            );
        }
    }
    let id = match obj.get("id") {
        None => {
            col.add(
                &format!("alternatives.{idx}.id"),
                "Field required".to_string(),
                "missing",
                v,
            );
            None
        }
        Some(iv) => validate_str_field(col, &format!("alternatives.{idx}.id"), iv, 1, 16),
    };
    let description = match obj.get("description") {
        None => {
            col.add(
                &format!("alternatives.{idx}.description"),
                "Field required".to_string(),
                "missing",
                v,
            );
            None
        }
        Some(iv) => {
            validate_str_field(col, &format!("alternatives.{idx}.description"), iv, 1, 1500)
        }
    };
    let rejected_reason = match obj.get("rejected_reason") {
        None => Some(String::new()),
        Some(Value::Null) => Some(String::new()),
        Some(iv) => validate_str_field(
            col,
            &format!("alternatives.{idx}.rejected_reason"),
            iv,
            0,
            1500,
        ),
    };
    // field_validator("id"): patrón ALTERNATIVE_ID_PATTERN.
    let id_checked = id.map(|id| {
        let ok = {
            let b = id.as_bytes();
            !b.is_empty()
                && (b[0].is_ascii_uppercase() || b[0].is_ascii_digit())
                && b[1..]
                    .iter()
                    .all(|c| c.is_ascii_alphanumeric() || *c == b'_' || *c == b'-')
                && id.chars().count() <= 16
        };
        if !ok {
            col.add_raw(
                &format!("alternatives.{idx}.id"),
                format!(
                    "Value error, Alternative id '{}' must match ^[A-Z0-9][A-Z0-9_-]{{0,15}}$",
                    id
                ),
                "value_error",
                truncate_repr(python_repr(&Value::String(id.clone()))),
                "str",
            );
        }
        id
    });
    match (id_checked, description, rejected_reason) {
        (Some(i), Some(d), Some(r)) => Some((i, d, r)),
        _ => None,
    }
}

/// Espejo de `Proposal.model_validate(payload)` → Ok(card ya construida se
/// hace aparte) | Err(texto ValidationError).
pub fn validate_proposal(payload: &Value) -> Result<ProposalData, String> {
    let mut col = ValidationCollector::new();

    let empty = Map::new();
    let map: &Map<String, Value> = payload.as_object().unwrap_or(&empty);

    // extra="forbid" a nivel Proposal.
    for (k, ev) in map.iter() {
        if !["summary", "alternatives", "recommendation_id", "risks"].contains(&k.as_str()) {
            col.add(
                k,
                "Extra inputs are not permitted".to_string(),
                "extra_forbidden",
                ev,
            );
        }
    }

    // summary: str, 1..=1000.
    let summary_missing = !map.contains_key("summary");
    let summary = if summary_missing {
        col.add("summary", "Field required".to_string(), "missing", payload);
        None
    } else {
        map.get("summary")
            .and_then(|v| validate_str_field(&mut col, "summary", v, 1, 1000))
    };

    // alternatives: lista de 2..=5 Alternatives.
    let alternatives: Option<Vec<(String, String, String)>> = match map.get("alternatives") {
        None => {
            col.add(
                "alternatives",
                "Field required".to_string(),
                "missing",
                payload,
            );
            None
        }
        Some(Value::Array(items)) => {
            let parsed: Vec<Option<(String, String, String)>> = items
                .iter()
                .enumerate()
                .map(|(i, it)| validate_alternative(&mut col, i, it))
                .collect();
            if items.len() < 2 {
                col.add(
                    "alternatives",
                    format!(
                        "List should have at least 2 items after validation, not {}",
                        items.len()
                    ),
                    "too_short",
                    &Value::Array(items.clone()),
                );
            } else if items.len() > 5 {
                col.add(
                    "alternatives",
                    format!(
                        "List should have at most 5 items after validation, not {}",
                        items.len()
                    ),
                    "too_long",
                    &Value::Array(items.clone()),
                );
            }
            let ok: Vec<_> = parsed.into_iter().flatten().collect();
            Some(ok)
        }
        Some(other) => {
            col.add(
                "alternatives",
                "Input should be a valid list".to_string(),
                "list_type",
                other,
            );
            None
        }
    };

    // recommendation_id: str, 1..=16.
    let rec_missing = !map.contains_key("recommendation_id");
    let recommendation_id = if rec_missing {
        col.add(
            "recommendation_id",
            "Field required".to_string(),
            "missing",
            payload,
        );
        None
    } else {
        map.get("recommendation_id")
            .and_then(|v| validate_str_field(&mut col, "recommendation_id", v, 1, 16))
    };

    // risks: lista de str ≤10; validator limpia vacíos y exige ≤300 chars.
    let risks: Vec<String> = match map.get("risks") {
        None | Some(Value::Null) => Vec::new(),
        Some(Value::Array(items)) => {
            if items.len() > 10 {
                col.add(
                    "risks",
                    format!(
                        "List should have at most 10 items after validation, not {}",
                        items.len()
                    ),
                    "too_long",
                    &Value::Array(items.clone()),
                );
            }
            let mut cleaned: Vec<String> = Vec::new();
            let mut too_long = false;
            for r in items {
                match r {
                    Value::String(rs) => {
                        let t = rs.trim();
                        if t.is_empty() {
                            continue;
                        }
                        if t.chars().count() > 300 {
                            too_long = true;
                        }
                        cleaned.push(t.to_string());
                    }
                    other => {
                        col.add(
                            "risks",
                            "Input should be a valid string".to_string(),
                            "string_type",
                            other,
                        );
                    }
                }
            }
            if too_long {
                // El ValueError del validator lleva como input_value la
                // LISTA limpia completa (input_type=list).
                col.add_raw(
                    "risks",
                    "Value error, Each risk must be <= 300 characters.".to_string(),
                    "value_error",
                    truncate_repr(python_repr(&Value::Array(
                        cleaned.iter().map(|s| Value::String(s.clone())).collect(),
                    ))),
                    "list",
                );
            }
            cleaned
        }
        Some(other) => {
            col.add(
                "risks",
                "Input should be a valid list".to_string(),
                "list_type",
                other,
            );
            Vec::new()
        }
    };

    if !col.entries.is_empty() {
        return Err(col.render());
    }

    // model_validator(mode="after"): consistencia recommendation/alernativas.
    // En pydantic corre una sola vez con TODOS los campos presentes; acá
    // llegamos sólo si no hubo errores de campo.
    let alts = alternatives.unwrap_or_default();
    let rec = recommendation_id.unwrap_or_default();
    let ids: Vec<&str> = alts.iter().map(|a| a.0.as_str()).collect();
    let mut dup_sorted: Vec<String> = {
        let mut dups: Vec<String> = Vec::new();
        for (i, id) in ids.iter().enumerate() {
            if ids.iter().skip(i + 1).any(|o| o == id) && !dups.contains(&id.to_string()) {
                dups.push(id.to_string());
            }
        }
        dups.sort();
        dups
    };
    dup_sorted.sort();
    if !dup_sorted.is_empty() {
        return Err(model_error(
            format!(
                "Alternative ids must be unique; duplicates: [{}]",
                dup_sorted
                    .iter()
                    .map(|d| format!("'{d}'"))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            payload,
        ));
    }
    if !ids.contains(&rec.as_str()) {
        return Err(model_error(
            format!(
                "recommendation_id '{}' does not match any alternative id (have: [{}])",
                rec,
                ids.iter()
                    .map(|i| format!("'{i}'"))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            payload,
        ));
    }
    let chosen = alts.iter().find(|a| a.0 == rec).expect("rec existe");
    if !chosen.2.trim().is_empty() {
        return Err(model_error(
            format!(
                "The recommended alternative ('{}') must have an empty rejected_reason; got: '{}'",
                chosen.0, chosen.2
            ),
            payload,
        ));
    }
    for alt in &alts {
        if alt.0 == rec {
            continue;
        }
        if alt.2.trim().is_empty() {
            return Err(model_error(
                format!(
                    "Non-recommended alternative '{}' must include a non-empty rejected_reason.",
                    alt.0
                ),
                payload,
            ));
        }
    }

    Ok(ProposalData {
        summary: summary.unwrap_or_default(),
        alternatives: alts,
        recommendation_id: rec,
        risks,
    })
}

/// Error de model_validator: loc vacío, input_value = todo el payload.
fn model_error(msg: String, payload: &Value) -> String {
    let mut col = ValidationCollector::new();
    col.add_raw(
        "",
        format!("Value error, {msg}"),
        "value_error",
        truncate_repr(python_repr(payload)),
        "dict",
    );
    col.render()
}

/// Datos validados de la propuesta (para la card).
#[derive(Debug, Clone)]
pub struct ProposalData {
    pub summary: String,
    /// (id, description, rejected_reason)
    pub alternatives: Vec<(String, String, String)>,
    pub recommendation_id: String,
    pub risks: Vec<String>,
}

/// `format_proposal_card(proposal)` byte-a-byte.
pub fn format_proposal_card(p: &ProposalData) -> String {
    let mut lines: Vec<String> = vec![
        "### 🎯 PROPUESTA — necesito tu confirmación".to_string(),
        String::new(),
        "**Resumen:**".to_string(),
        p.summary.trim().to_string(),
        String::new(),
        "**Alternativas consideradas:**".to_string(),
    ];
    for alt in &p.alternatives {
        let marker = if alt.0 == p.recommendation_id {
            "✅"
        } else {
            "❌"
        };
        lines.push(format!("- {} **[{}]** {}", marker, alt.0, alt.1.trim()));
        if alt.0 == p.recommendation_id {
            lines.push("    - *(esta es la que recomiendo)*".to_string());
        } else {
            lines.push(format!("    - Descartada porque: {}", alt.2.trim()));
        }
    }
    if !p.risks.is_empty() {
        lines.push(String::new());
        lines.push("**Riesgos / supuestos:**".to_string());
        for r in &p.risks {
            lines.push(format!("- {r}"));
        }
    }
    lines.push(String::new());
    lines.push("---".to_string());
    lines.push(format!(
        "⏸ **Esperando confirmación.** Respondé `ok` (o silencio) para proceder con **[{}]**, o indicame qué cambiar / cuál elegís en su lugar.",
        p.recommendation_id
    ));
    lines.join("\n")
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// Helper: truthiness Python sobre Value.
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

/// Tool `cortex_emit_proposal`. `now_epoch` lo provee el server (stamp del
/// gap). Devuelve la card o el error de validación pydantic.
pub fn emit_proposal_text(
    state: &mut SpecServerState,
    arguments: &Value,
    now_epoch: f64,
) -> Result<String, String> {
    let payload = serde_json::json!({
        "summary": arguments.get("summary").cloned().unwrap_or(Value::String(String::new())),
        "alternatives": arguments.get("alternatives").cloned().unwrap_or(Value::Array(vec![])),
        "recommendation_id": arguments.get("recommendation_id").cloned().unwrap_or(Value::String(String::new())),
        "risks": arguments.get("risks").cloned().unwrap_or(Value::Array(vec![])),
    });
    match validate_proposal(&payload) {
        Err(exc) => Ok(format!("❌ cortex_emit_proposal payload invalid: {exc}")),
        Ok(proposal) => {
            state.last_proposal_emitted_epoch = Some(now_epoch);
            Ok(format_proposal_card(&proposal))
        }
    }
}

/// `_validate_proposal_gap`: error si no hubo emit previo o si el gap es
/// menor al mínimo. `now_epoch` inyectado.
pub fn validate_proposal_gap(state: &SpecServerState, now_epoch: f64) -> Option<String> {
    match state.last_proposal_emitted_epoch {
        None => Some(
            "proposal_mode='required' requires a prior cortex_emit_proposal call. Emit the \
             proposal first, end your turn, and only after the user replies should you call \
             cortex_create_spec with proposal_confirmed=True."
                .to_string(),
        ),
        Some(emitted) => {
            let delta = now_epoch - emitted;
            if delta < PROPOSAL_MIN_GAP_SECONDS {
                Some(format!(
                    "proposal emitted {delta:.2}s ago — too recent to count as user-confirmed. \
                     The user has not had time to respond yet. End your turn after \
                     cortex_emit_proposal and wait for an explicit reply before calling \
                     cortex_create_spec. (minimum gap: {}s)",
                    crate::pyjson::py_float_repr(PROPOSAL_MIN_GAP_SECONDS)
                ))
            } else {
                None
            }
        }
    }
}

/// Tool `cortex_create_spec`.
pub fn create_spec_text(
    state: &mut SpecServerState,
    b: &mut dyn SpecBackend,
    arguments: &Value,
    now_epoch: f64,
) -> Result<String, String> {
    if !state.called_tools.contains("cortex_sync_ticket") {
        let sorted: Vec<String> = state.called_tools.iter().cloned().collect();
        return Ok(format!(
            "{GOVERNANCE_VIOLATION_MESSAGE}\n\nHerramientas llamadas en esta sesión: {}",
            sorted.join(", ")
        ));
    }

    let proposal_mode = arguments
        .get("proposal_mode")
        .and_then(Value::as_str)
        .unwrap_or("optional")
        .to_string();
    let proposal_confirmed = truthy(arguments.get("proposal_confirmed"));

    if proposal_mode == "required" && proposal_confirmed {
        if let Some(gap_error) = validate_proposal_gap(state, now_epoch) {
            return Ok(format!("❌ {gap_error}"));
        }
    }

    let strs = |key: &str| -> Vec<String> {
        arguments
            .get(key)
            .and_then(Value::as_array)
            .map(|arr| {
                arr.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default()
    };

    let req = SpecCreateRequest {
        title: arguments
            .get("title")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string(),
        goal: arguments
            .get("goal")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string(),
        requirements: strs("requirements"),
        files_in_scope: strs("files_in_scope"),
        constraints: strs("constraints"),
        acceptance_criteria: strs("acceptance_criteria"),
        tags: strs("tags"),
        verification_hooks: arguments
            .get("verification_hooks")
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default(),
        sync_vault: !truthy(arguments.get("no_sync")),
        proposal_mode,
        proposal_confirmed,
    };

    match b.create_spec_note(&req) {
        Err(SpecError::Value(exc)) => Ok(format!("❌ {exc}")),
        Err(SpecError::DuplicateDocument(exc)) => Ok(format!(
            "ℹ️  Spec ya existe con contenido distinto.\n\n{exc}\n\nOpciones:\n  • Cambiá el título para generar un slug distinto.\n  • O abrí sesión sobre la spec existente con cortex_session_open."
        )),
        Ok(result) => {
            let mut message = format!("Specification saved -> {}", result.path);
            if result.session_gitless == Some(true) {
                message += "\n\n⚠️  No git repository detected. Session opened in degraded mode:\n   • cortex finish-session will skip git diff reconstruction\n   • documenter will rely exclusively on checkpoints\n   • To enable full session capabilities later, run:\n       git init && git add -A && git commit -m \"initial\"";
            }
            Ok(message)
        }
    }
}

/// Tool `cortex_self_review_note`: inspección pura del draft.
pub fn self_review_note_text(arguments: &Value) -> Result<String, String> {
    let body = arguments
        .get("body")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    let hooks_passed = truthy(arguments.get("verification_hooks_passed"));

    let mut warnings: Vec<String> = Vec::new();
    let body_lower = body.to_lowercase();
    for token in PLACEHOLDER_TOKENS {
        if body_lower.contains(token) {
            warnings.push(format!("Placeholder token detected: '{}'", token));
        }
    }
    if !hooks_passed {
        for pattern in SUCCESS_CLAIM_PATTERNS {
            if body_lower.contains(pattern) {
                warnings.push(format!(
                    "Hollow claim '{pattern}' — no verification hook actually passed; either remove the claim or run the test/build that proves it."
                ));
            }
        }
    }
    let passed = warnings.is_empty();
    Ok(to_string_ensure_ascii_false(
        &serde_json::json!({ "warnings": warnings, "passed": passed }),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_ok() -> Value {
        serde_json::json!({
            "summary": "s",
            "alternatives": [
                {"id": "A", "description": "hacer X"},
                {"id": "B", "description": "hacer Y", "rejected_reason": "más caro"}
            ],
            "recommendation_id": "A"
        })
    }

    #[test]
    fn card_valida_bytes() {
        let p = validate_proposal(&base_ok()).unwrap();
        let card = format_proposal_card(&p);
        assert!(card.starts_with("### 🎯 PROPUESTA — necesito tu confirmación\n"));
        assert!(card.contains("- ✅ **[A]** hacer X\n    - *(esta es la que recomiendo)*"));
        assert!(card.ends_with("**[A]**, o indicame qué cambiar / cuál elegís en su lugar."));
    }

    #[test]
    fn pydantic_summary_vacio() {
        let mut v = base_ok();
        v["summary"] = serde_json::json!("");
        let err = validate_proposal(&v).unwrap_err();
        assert_eq!(
            err,
            "1 validation error for Proposal\nsummary\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short"
        );
    }

    #[test]
    fn pydantic_id_malo() {
        let mut v = base_ok();
        v["alternatives"][0]["id"] = serde_json::json!("a b");
        let err = validate_proposal(&v).unwrap_err();
        assert!(err.starts_with("1 validation error for Proposal\nalternatives.0.id\n  Value error, Alternative id 'a b' must match ^[A-Z0-9][A-Z0-9_-]{0,15}$ [type=value_error, input_value='a b', input_type=str]\n"));
    }

    #[test]
    fn pydantic_rec_no_existe_trunca_dict() {
        let err = validate_proposal(&serde_json::json!({
            "summary":"s","alternatives":[{"id":"A","description":"d"},{"id":"B","description":"e","rejected_reason":"r"}],
            "recommendation_id":"Z"
        }))
        .unwrap_err();
        assert!(err.contains("[type=value_error, input_value={'summary': 's', 'alterna...recommendation_id': 'Z'}, input_type=dict]\n"), "{err}");
    }

    #[test]
    fn governance_sin_sync() {
        let mut state = SpecServerState::default();
        state.called_tools.insert("cortex_ping".into());
        struct NB;
        impl SpecBackend for NB {
            fn create_spec_note(
                &mut self,
                _: &SpecCreateRequest,
            ) -> Result<SpecResultMirror, SpecError> {
                unreachable!()
            }
        }
        let out =
            create_spec_text(&mut state, &mut NB, &serde_json::json!({"title": "T"}), 0.0).unwrap();
        assert!(out.starts_with("❌ **VIOLACIÓN DE GOBERNANZA**"));
        assert!(out.ends_with("Herramientas llamadas en esta sesión: cortex_ping"));
    }

    #[test]
    fn self_review_placeholder_y_claim() {
        let out = self_review_note_text(&serde_json::json!({
            "body": "This is TBD for now.",
            "verification_hooks_passed": false
        }))
        .unwrap();
        assert_eq!(
            out,
            "{\"warnings\": [\"Placeholder token detected: 'tbd'\"], \"passed\": false}"
        );
    }
}
