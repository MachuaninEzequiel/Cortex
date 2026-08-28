//! Session primitive nativa (Obra 07 fase P4).
//!
//! Puerto de `cortex/session/` — modelos, storage YAML atómico e infer_mode.
//! Spec conductual: `tests/unit/session/*` (paridad-como-contrato).
//!
//! Paridad con Python:
//! - Los datetimes se persisten como strings ISO-8601 (pydantic mode="json").
//! - Validaciones portadas: session_id `YYYY-MM-DD_<slug>`, SHA 40-hex
//!   lowercase, timestamps con offset (UTC), invariantes OPEN vs terminal,
//!   patrón de Task `T\d+(\.\d+)*`, truncamiento de output 10_000 bytes.
//! - Storage: YAML `sort_keys=False, allow_unicode` ⇒ orden de declaración;
//!   escritura atómica tmp+rename; active pointer `.cortex/sessions/active`.
//! - `infer_mode`: BYO / CI_REVIEW / COMPOSED / MANAGED / OBSERVED idéntico.
//!
//! Submódulos: `verification` (runner de hooks), `quality_gates` (review
//! en dos etapas) y `service` (capa SessionService para ci/CLI, P11-ci) —
//! puertos de verification.py, quality_gates.py y service.py.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

pub const GITLESS_COMMIT_PLACEHOLDER: &str = "0000000000000000000000000000000000000000";
pub const MAX_VERIFICATION_OUTPUT_BYTES: usize = 10_000;

// ── Enums ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionStatus {
    Open,
    Closed,
    Handoff,
    Abandoned,
}

impl SessionStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Open => "open",
            Self::Closed => "closed",
            Self::Handoff => "handoff",
            Self::Abandoned => "abandoned",
        }
    }
    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Closed | Self::Handoff | Self::Abandoned)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionMode {
    Unknown,
    Managed,
    Observed,
    Byo,
    /// Modo COMPOSED (Obra 08 stream A): el middle es una cadena de skills
    /// externas que emiten checkpoints con `phase`; Cortex reconoce, registra
    /// y documenta sin orquestar.
    Composed,
    #[serde(rename = "ci-review")]
    CiReview,
}

/// Fase de un checkpoint COMPOSED (Obra 08 stream A).
///
/// Las skills user/model-invoked emiten checkpoints con `phase` para que
/// Cortex reconozca la cadena de fases sin orquestar (modo COMPOSED).
/// Campo opcional: los emisores legados no lo llevan y nada cambia para
/// ellos.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CheckpointPhase {
    Grill,
    Spec,
    Plan,
    Implement,
    Review,
    Close,
}

impl CheckpointPhase {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Grill => "grill",
            Self::Spec => "spec",
            Self::Plan => "plan",
            Self::Implement => "implement",
            Self::Review => "review",
            Self::Close => "close",
        }
    }

    /// Case-sensitive en minúsculas (igual que los demás parsers del repo);
    /// `None` para cualquier entrada inválida (patrón P6/P9: el servicio
    /// rechaza con mensaje claro, nunca silencio).
    pub fn parse(s: &str) -> Option<CheckpointPhase> {
        match s {
            "grill" => Some(Self::Grill),
            "spec" => Some(Self::Spec),
            "plan" => Some(Self::Plan),
            "implement" => Some(Self::Implement),
            "review" => Some(Self::Review),
            "close" => Some(Self::Close),
            _ => None,
        }
    }
}

impl std::str::FromStr for CheckpointPhase {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s).ok_or(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum CheckpointSource {
    #[serde(rename = "cortex-sync")]
    CortexSync,
    #[serde(rename = "cortex-SDDwork")]
    CortexSddwork,
    #[serde(rename = "cortex-code-explorer")]
    CortexCodeExplorer,
    #[serde(rename = "cortex-code-implementer")]
    CortexCodeImplementer,
    #[serde(rename = "cortex-code-designer")]
    CortexCodeDesigner,
    #[serde(rename = "user-skill")]
    UserSkill,
    #[serde(rename = "ide-hook")]
    IdeHook,
    #[serde(rename = "manual")]
    Manual,
    #[serde(rename = "ci-bot")]
    CiBot,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum TaskStatus {
    #[default]
    Pending,
    #[serde(rename = "in-progress")]
    InProgress,
    Done,
    Skipped,
    Blocked,
}

// ── Validación de patrones ───────────────────────────────────────────────────

fn valid_session_id(v: &str) -> bool {
    // ^\d{4}-\d{2}-\d{2}_[a-z0-9][a-z0-9-]*$
    let b = v.as_bytes();
    if b.len() < 11 || b[10] != b'_' {
        return false;
    }
    let date = &v[..10];
    let d: Vec<char> = date.chars().collect();
    let ok_date = d.len() == 10
        && d.iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == '-'
            } else {
                c.is_ascii_digit()
            }
        });
    ok_date
        && v[11..]
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && v[11..]
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

fn valid_sha(s: &str) -> bool {
    s.len() == 40
        && s.bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}

/// Valida ISO-8601 con offset (pydantic `_to_utc` rechaza naive).
fn validate_iso_utc(field: &str, s: &str) -> Result<(), String> {
    chrono::DateTime::parse_from_rfc3339(s)
        .map(|_| ())
        .map_err(|_| format!("{field} debe ser ISO-8601 con offset (naive no permitido): {s:?}"))
}

/// Puerto de `_truncate_output`: conserva la cola, avisa en la cabeza.
pub fn truncate_output(text: &str) -> String {
    let encoded = text.as_bytes();
    if encoded.len() <= MAX_VERIFICATION_OUTPUT_BYTES {
        return text.to_string();
    }
    let tail = &encoded[encoded.len() - MAX_VERIFICATION_OUTPUT_BYTES..];
    let decoded = String::from_utf8_lossy(tail);
    format!("[... truncated, kept last {MAX_VERIFICATION_OUTPUT_BYTES} bytes ...]\n{decoded}")
}

// ── Modelos ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Task {
    pub id: String,
    pub description: String,
    #[serde(default)]
    pub files_in_scope: Vec<String>,
    #[serde(default)]
    pub depends_on: Vec<String>,
    #[serde(default)]
    pub status: TaskStatus,
    #[serde(default)]
    pub completed_at: Option<String>,
    #[serde(default)]
    pub checkpoint_index: Option<u64>,
    #[serde(default)]
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Checkpoint {
    pub timestamp: String,
    pub source: CheckpointSource,
    #[serde(default)]
    pub verified_claims: Vec<String>,
    #[serde(default)]
    pub unverified_claims: Vec<String>,
    #[serde(default)]
    pub artifacts_touched: Vec<String>,
    #[serde(default)]
    pub note: String,
    /// Fase COMPOSED opcional (Obra 08 stream A). Ausente ⇒ emisor legado.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub phase: Option<CheckpointPhase>,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VerificationHook {
    pub name: String,
    pub command: String,
    #[serde(default = "yes")]
    pub required: bool,
    #[serde(default = "exit_zero")]
    pub success_criteria: String,
    #[serde(default = "default_timeout")]
    pub timeout_seconds: u64,
}

fn yes() -> bool {
    true
}
fn exit_zero() -> String {
    "exit code 0".into()
}
fn default_timeout() -> u64 {
    300
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VerificationHookResult {
    pub name: String,
    pub command: String,
    pub passed: bool,
    pub exit_code: i32,
    pub output: String,
    pub duration_ms: u64,
    pub run_at: String,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct SessionRecord {
    pub session_id: String,
    pub spec_path: String,
    pub spec_summary: String,
    pub start_commit: String,
    pub start_branch: String,
    pub opened_at: String,
    pub status: SessionStatus,
    pub mode: SessionMode,
    pub checkpoints: Vec<Checkpoint>,
    pub verification_results: Vec<VerificationHookResult>,
    pub tasks: Vec<Task>,
    pub closed_at: Option<String>,
    pub end_commit: Option<String>,
    pub documenter_decision: Option<SessionStatus>,
    pub session_note_path: Option<String>,
    pub adrs_created: Vec<String>,
}

impl Default for SessionRecord {
    fn default() -> Self {
        Self {
            session_id: String::new(),
            spec_path: String::new(),
            spec_summary: String::new(),
            start_commit: GITLESS_COMMIT_PLACEHOLDER.to_string(),
            start_branch: String::new(),
            opened_at: String::new(),
            status: SessionStatus::Open,
            mode: SessionMode::Unknown,
            checkpoints: vec![],
            verification_results: vec![],
            tasks: vec![],
            closed_at: None,
            end_commit: None,
            documenter_decision: None,
            session_note_path: None,
            adrs_created: vec![],
        }
    }
}

impl SessionRecord {
    /// Todas las validaciones pydantic, sobre el modelo ya deserializado.
    pub fn validate(&self) -> Result<(), String> {
        if !valid_session_id(&self.session_id) {
            return Err(format!(
                "session_id {:?} does not match required pattern 'YYYY-MM-DD_<slug>'",
                self.session_id
            ));
        }
        if !valid_sha(&self.start_commit) {
            return Err(format!(
                "start_commit must be a 40-character lowercase hex SHA, got {:?}",
                self.start_commit
            ));
        }
        if let Some(e) = &self.end_commit {
            if !valid_sha(e) {
                return Err(format!(
                    "end_commit must be a 40-character lowercase hex SHA, got {e:?}"
                ));
            }
        }
        validate_iso_utc("opened_at", &self.opened_at)?;
        if let Some(c) = &self.closed_at {
            validate_iso_utc("closed_at", c)?;
        }
        for cp in &self.checkpoints {
            validate_iso_utc("checkpoint.timestamp", &cp.timestamp)?;
        }
        for vr in &self.verification_results {
            validate_iso_utc("run_at", &vr.run_at)?;
        }
        let task_re = regex::Regex::new(r"^T\d+(\.\d+)*$").unwrap();
        for t in &self.tasks {
            if !task_re.is_match(&t.id) {
                return Err(format!("Task id {:?} inválido", t.id));
            }
            if t.id.is_empty() || t.id.len() > 64 {
                return Err(format!("Task id {:?} fuera de rango", t.id));
            }
            if t.description.is_empty() {
                return Err("Task description vacía".to_string());
            }
        }

        let is_terminal = self.status.is_terminal();
        let missing_or_set = [
            ("closed_at", self.closed_at.is_some()),
            ("end_commit", self.end_commit.is_some()),
            ("documenter_decision", self.documenter_decision.is_some()),
        ];
        if is_terminal {
            let missing: Vec<&str> = missing_or_set
                .iter()
                .filter(|(_, set)| !set)
                .map(|(k, _)| *k)
                .collect();
            if !missing.is_empty() {
                return Err(format!(
                    "Session in status {:?} requires non-null fields: {}",
                    self.status.as_str(),
                    missing.join(", ")
                ));
            }
        } else {
            let populated: Vec<&str> = missing_or_set
                .iter()
                .filter(|(_, set)| *set)
                .map(|(k, _)| *k)
                .collect();
            if !populated.is_empty() {
                return Err(format!(
                    "Session in status {:?} must not set close-time fields: {}",
                    self.status.as_str(),
                    populated.join(", ")
                ));
            }
        }
        Ok(())
    }

    pub fn is_gitless(&self) -> bool {
        self.start_commit == GITLESS_COMMIT_PLACEHOLDER
    }
}

// ── infer_mode ───────────────────────────────────────────────────────────────

pub fn infer_mode(checkpoints: &[Checkpoint]) -> SessionMode {
    if checkpoints.is_empty() {
        return SessionMode::Byo;
    }
    let all_ci = checkpoints
        .iter()
        .all(|c| c.source == CheckpointSource::CiBot);
    if all_ci {
        return SessionMode::CiReview;
    }
    // Regla 3 (spec 13 §4): si CUALQUIER checkpoint lleva fase, la sesión es
    // COMPOSED — el usuario compuso un flujo con fases visibles aunque haya
    // mezclado agentes Cortex e ide-hooks en el camino. Gana sobre MANAGED
    // y OBSERVED; CI_REVIEW (todo ci-bot) y BYO (vacío) ya retornaron antes.
    if checkpoints.iter().any(|c| c.phase.is_some()) {
        return SessionMode::Composed;
    }
    const CORTEX_SOURCES: [CheckpointSource; 5] = [
        CheckpointSource::CortexSync,
        CheckpointSource::CortexSddwork,
        CheckpointSource::CortexCodeExplorer,
        CheckpointSource::CortexCodeImplementer,
        CheckpointSource::CortexCodeDesigner,
    ];
    let all_cortex = checkpoints
        .iter()
        .all(|c| CORTEX_SOURCES.contains(&c.source));
    if all_cortex {
        SessionMode::Managed
    } else {
        SessionMode::Observed
    }
}

// ── Storage ──────────────────────────────────────────────────────────────────

pub mod quality_gates;
pub mod service;
pub mod verification;

pub struct SessionStorage {
    root: PathBuf,
}

impl SessionStorage {
    pub fn new(sessions_dir: PathBuf) -> Self {
        Self { root: sessions_dir }
    }

    pub fn from_workspace(workspace_root: &Path) -> Self {
        Self::new(workspace_root.join(".cortex").join("sessions"))
    }

    pub fn file_path(&self, session_id: &str) -> PathBuf {
        self.root.join(format!("{session_id}.yaml"))
    }

    pub fn active_pointer_path(&self) -> PathBuf {
        self.root.join("active.txt")
    }

    /// Escritura atómica tmp + rename (patrón del storage Python).
    pub fn save(&self, record: &SessionRecord) -> Result<PathBuf, String> {
        record
            .validate()
            .map_err(|e| format!("record inválido: {e}"))?;
        fs::create_dir_all(&self.root).map_err(|e| e.to_string())?;
        let final_p = self.file_path(&record.session_id);
        let tmp = self.root.join(format!(
            ".{}.yaml.tmp-{}",
            record.session_id,
            std::process::id()
        ));
        let yaml = serde_yaml::to_string(record).map_err(|e| e.to_string())?;
        fs::write(&tmp, yaml).map_err(|e| e.to_string())?;
        fs::rename(&tmp, &final_p).map_err(|e| e.to_string())?;
        Ok(final_p)
    }

    /// Carga + valida (los invariants corren también al leer).
    pub fn load(&self, session_id: &str) -> Result<SessionRecord, String> {
        let p = self.file_path(session_id);
        let text = fs::read_to_string(&p).map_err(|e| format!("{}: {e}", p.display()))?;
        let record: SessionRecord =
            serde_yaml::from_str(&text).map_err(|e| format!("YAML {}: {e}", p.display()))?;
        record.validate()?;
        Ok(record)
    }

    pub fn exists(&self, session_id: &str) -> bool {
        self.file_path(session_id).exists()
    }

    pub fn list_all(&self) -> Result<Vec<SessionRecord>, String> {
        let mut out = Vec::new();
        if !self.root.exists() {
            return Ok(out);
        }
        let mut files: Vec<PathBuf> = fs::read_dir(&self.root)
            .map_err(|e| e.to_string())?
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("yaml"))
            .collect();
        files.sort(); // determinista (Python lista por orden interno)
        for f in files {
            let Some(sid) = f.file_stem().map(|x| x.to_string_lossy().to_string()) else {
                continue;
            };
            out.push(self.load(&sid)?);
        }
        Ok(out)
    }

    pub fn get_active_session_id(&self) -> Option<String> {
        fs::read_to_string(self.active_pointer_path())
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
    }

    pub fn set_active_session_id(&self, session_id: Option<&str>) -> Result<(), String> {
        fs::create_dir_all(&self.root).map_err(|e| e.to_string())?;
        match session_id {
            Some(id) => {
                let tmp = self.root.join(".active.tmp");
                fs::write(&tmp, format!("{id}\n")).map_err(|e| e.to_string())?;
                fs::rename(tmp, self.active_pointer_path()).map_err(|e| e.to_string())
            }
            None => {
                let p = self.active_pointer_path();
                if p.exists() {
                    fs::remove_file(p).map_err(|e| e.to_string())
                } else {
                    Ok(())
                }
            }
        }
    }
}

/// Utilidad para dumps canónicos normalizados ({{TS}}, {{ROOT}}).
pub fn canonical_json_normalized(record: &SessionRecord, workspace_root: &str) -> String {
    let mut obj: BTreeMap<String, serde_json::Value> = BTreeMap::new();
    let norm = |s: &str| s.replace(workspace_root, "{{ROOT}}");
    let ts = "{{TS}}".to_string();

    obj.insert("session_id".into(), record.session_id.clone().into());
    obj.insert("spec_path".into(), norm(&record.spec_path).into());
    obj.insert(
        "spec_summary".into(),
        record
            .spec_summary
            .replace(workspace_root, "{{ROOT}}")
            .into(),
    );
    obj.insert("start_commit".into(), record.start_commit.clone().into());
    obj.insert("start_branch".into(), record.start_branch.clone().into());
    obj.insert("opened_at".into(), ts.clone().into());
    obj.insert("status".into(), record.status.as_str().to_string().into());
    let mode = serde_json::to_value(record.mode).unwrap_or_default();
    obj.insert("mode".into(), mode);
    let cps: Vec<serde_json::Value> = record
        .checkpoints
        .iter()
        .map(|c| {
            let mut obj = serde_json::Map::new();
            obj.insert("timestamp".into(), ts.clone().into());
            obj.insert(
                "source".into(),
                serde_json::to_value(c.source).unwrap_or_default(),
            );
            obj.insert(
                "verified_claims".into(),
                serde_json::to_value(&c.verified_claims).unwrap_or_default(),
            );
            obj.insert(
                "unverified_claims".into(),
                serde_json::to_value(&c.unverified_claims).unwrap_or_default(),
            );
            obj.insert(
                "artifacts_touched".into(),
                serde_json::to_value(&c.artifacts_touched).unwrap_or_default(),
            );
            obj.insert("note".into(), c.note.clone().into());
            // Ruling R6 (spec 13 §2.1): phase sobrevive el dump --json, solo
            // cuando Some ⇒ dumps sin fase byte-idénticos a los actuales.
            if let Some(p) = c.phase {
                obj.insert("phase".into(), serde_json::to_value(p).unwrap_or_default());
            }
            serde_json::Value::Object(obj)
        })
        .collect();
    obj.insert("checkpoints".into(), cps.into());
    let vrs: Vec<serde_json::Value> = record
        .verification_results
        .iter()
        .map(|v| {
            serde_json::json!({
                "name": v.name,
                "command": v.command,
                "passed": v.passed,
                "exit_code": v.exit_code,
                "output": truncate_output(&v.output),
                "duration_ms": v.duration_ms,
                "run_at": ts,
            })
        })
        .collect();
    obj.insert("verification_results".into(), vrs.into());
    let tasks: Vec<serde_json::Value> = record
        .tasks
        .iter()
        .map(|t| {
            serde_json::json!({
                "id": t.id, "description": t.description,
                "files_in_scope": t.files_in_scope, "depends_on": t.depends_on,
                "status": t.status, "completed_at": t.completed_at.as_deref().map(|_| ts.clone()),
                "checkpoint_index": t.checkpoint_index, "note": t.note,
            })
        })
        .collect();
    obj.insert("tasks".into(), tasks.into());
    obj.insert(
        "closed_at".into(),
        record.closed_at.as_ref().map(|_| ts.clone()).into(),
    );
    obj.insert("end_commit".into(), record.end_commit.clone().into());
    obj.insert(
        "documenter_decision".into(),
        record
            .documenter_decision
            .map(|s| serde_json::Value::String(s.as_str().into()))
            .into(),
    );
    obj.insert(
        "session_note_path".into(),
        record.session_note_path.as_deref().map(norm).into(),
    );
    obj.insert(
        "adrs_created".into(),
        record
            .adrs_created
            .iter()
            .map(|a| serde_json::Value::String(norm(a)))
            .collect::<Vec<_>>()
            .into(),
    );

    let mut s = serde_json::to_string_pretty(&obj).expect("dump");
    s.push('\n');
    s
}

// ── Tests: contrato de fases (Obra 08 stream A, G-A1a) ───────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn base_checkpoint() -> Checkpoint {
        Checkpoint {
            timestamp: "2026-08-28T00:00:00.000000Z".to_string(),
            source: CheckpointSource::UserSkill,
            verified_claims: Vec::new(),
            unverified_claims: Vec::new(),
            artifacts_touched: Vec::new(),
            note: String::new(),
            phase: None,
        }
    }

    const ALL_PHASES: [CheckpointPhase; 6] = [
        CheckpointPhase::Grill,
        CheckpointPhase::Spec,
        CheckpointPhase::Plan,
        CheckpointPhase::Implement,
        CheckpointPhase::Review,
        CheckpointPhase::Close,
    ];

    #[test]
    fn phase_roundtrip_yaml() {
        for p in ALL_PHASES {
            let mut cp = base_checkpoint();
            cp.phase = Some(p);
            let yaml = serde_yaml::to_string(&cp).unwrap();
            let back: Checkpoint = serde_yaml::from_str(&yaml).unwrap();
            assert_eq!(back.phase, Some(p), "roundtrip perdió fase {p:?}");
        }
    }

    #[test]
    fn phase_as_str_parse_roundtrip() {
        for p in ALL_PHASES {
            assert_eq!(p.as_str().parse::<CheckpointPhase>(), Ok(p));
            assert_eq!(CheckpointPhase::parse(p.as_str()), Some(p));
        }
    }

    #[test]
    fn no_phase_backward_compat() {
        // Checkpoint legado (formato real del storage YAML) SIN campo phase.
        let yaml = "\
timestamp: '2026-08-28T00:00:00.000000Z'\nsource: user-skill\nverified_claims: []\nunverified_claims: []\nartifacts_touched: []\nnote: ''\n";
        let cp: Checkpoint = serde_yaml::from_str(yaml).unwrap();
        assert_eq!(cp.phase, None);
        assert_eq!(cp.source, CheckpointSource::UserSkill);
    }

    #[test]
    fn invalid_phase_string_rejected() {
        assert_eq!(CheckpointPhase::parse("asdf"), None);
        assert_eq!(CheckpointPhase::parse(""), None);
        assert_eq!(CheckpointPhase::parse("Spec"), None); // case-sensitive
        assert_eq!(CheckpointPhase::parse("implement "), None); // sin trim
    }

    #[test]
    fn phase_omitted_in_yaml_when_none() {
        let cp = base_checkpoint();
        let yaml = serde_yaml::to_string(&cp).unwrap();
        assert!(
            !yaml.contains("phase"),
            "phase no debe serializarse en None"
        );
    }

    // ── infer_mode COMPOSED (G-A1b) ───────────────────────────────────────

    fn cp(source: CheckpointSource, phase: Option<CheckpointPhase>) -> Checkpoint {
        let mut c = base_checkpoint();
        c.source = source;
        c.phase = phase;
        c
    }

    #[test]
    fn infer_mode_composed_when_any_phase() {
        // mezcla: cortex-SDDwork sin phase + user-skill con phase + ide-hook
        let cps = vec![
            cp(CheckpointSource::CortexSddwork, None),
            cp(
                CheckpointSource::UserSkill,
                Some(CheckpointPhase::Implement),
            ),
            cp(CheckpointSource::IdeHook, None),
        ];
        assert_eq!(infer_mode(&cps), SessionMode::Composed);
    }

    #[test]
    fn infer_mode_composed_wins_over_all_cortex() {
        // todos cortex-* pero uno con phase → COMPOSED (no MANAGED)
        let cps = vec![
            cp(CheckpointSource::CortexSync, Some(CheckpointPhase::Spec)),
            cp(CheckpointSource::CortexSddwork, None),
        ];
        assert_eq!(infer_mode(&cps), SessionMode::Composed);
    }

    #[test]
    fn infer_mode_backward_compat_sin_phase() {
        // sin phase: las combinaciones actuales dan los modos actuales
        let all_cortex = vec![
            cp(CheckpointSource::CortexSync, None),
            cp(CheckpointSource::CortexSddwork, None),
        ];
        assert_eq!(infer_mode(&all_cortex), SessionMode::Managed);
        let mixed = vec![
            cp(CheckpointSource::CortexSddwork, None),
            cp(CheckpointSource::IdeHook, None),
        ];
        assert_eq!(infer_mode(&mixed), SessionMode::Observed);
        assert_eq!(infer_mode(&[]), SessionMode::Byo);
        let ci = vec![
            cp(CheckpointSource::CiBot, None),
            cp(CheckpointSource::CiBot, None),
        ];
        assert_eq!(infer_mode(&ci), SessionMode::CiReview);
    }

    // ── Ruling R6: dump canónico --json con phase (spec 13 §2.1) ──────────

    #[test]
    fn canonical_dump_omits_phase_when_none() {
        let rec = SessionRecord {
            checkpoints: vec![cp(CheckpointSource::UserSkill, None)],
            ..SessionRecord::default()
        };
        let s = canonical_json_normalized(&rec, "/ws");
        assert!(
            !s.contains("phase"),
            "dump sin fase no debe emitir la clave: {s}"
        );
    }

    #[test]
    fn canonical_dump_includes_phase_when_some() {
        let rec = SessionRecord {
            checkpoints: vec![cp(
                CheckpointSource::UserSkill,
                Some(CheckpointPhase::Review),
            )],
            ..SessionRecord::default()
        };
        let s = canonical_json_normalized(&rec, "/ws");
        assert_eq!(
            s.matches("\"phase\"").count(),
            1,
            "una sola clave phase: {s}"
        );
        assert!(s.contains("\"phase\": \"review\""), "{s}");
    }
}
