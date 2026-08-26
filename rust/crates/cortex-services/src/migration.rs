//! Migrador de bóvedas legacy → esquema canónico.
//!
//! Réplica de `cortex/documentation/migration.py` (P12A-6, stream A).
//!
//! Lee cada `.md` de la bóveda (ordenado), infiere el `doc_type` desde la
//! ruta, construye frontmatter canónico y reporta el diff (dry-run) o
//! reescribe el archivo (`apply`). Idempotente: archivos con
//! `schema_version: 1` y `doc_type` string se saltan salvo `force`.
//! Campos legacy fuera del esquema se preservan con prefijo `legacy_`.
//!
//! Divergencias documentadas:
//! - El parser YAML es `serde_yaml`, no PyYAML ⇒ los mensajes de error de
//!   YAML inválido difieren; los gates los normalizan ({{YAML_ERR}}).
//! - Timestamps YAML "planos" (sin comillas): PyYAML los resuelve a objetos
//!   `datetime`; serde_yaml los entrega como string. Los fixtures del gate
//!   escriben fechas vía `yaml.safe_dump` de strings (con comillas), por lo
//!   que ambos lados siguen la rama string.
//! - `create_backup` delega en `tar czf` CLI (disponible en Linux/macOS y
//!   Windows 10+); el contenido exacto del .tar.gz no es contrato, sólo su
//!   existencia/nombre.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::process::Command;

use chrono::{DateTime, NaiveDate, NaiveDateTime, Utc};
use cortex_setup::slug::slugify;
use cortex_setup::yaml::Yaml;
use cortex_setup::{doc_type::DocType, fingerprint::compute_fingerprint};
use regex::Regex;
use serde_yaml::{Mapping, Value as YV};

// ---------------------------------------------------------------------------
// Conjuntos de claves (frozensets de Python)
// ---------------------------------------------------------------------------

const CANONICAL_TOP_LEVEL: &[&str] = &[
    "schema_version",
    "doc_type",
    "title",
    "created_at",
    "updated_at",
    "tags",
    "status",
    "links",
    "vault_scope",
    "fingerprint",
    "owner",
    "team",
    "classification",
    "retention_days",
    "audit_trail",
];

const LEGACY_MAPPED: &[&str] = &["date", "title", "tags", "status"];

const TYPE_SPECIFIC_FIELDS: &[&str] = &[
    // ADR / Decision
    "adr_number",
    "supersedes",
    "superseded_by",
    "alternatives_considered",
    "acceptance_criteria_met",
    "reversible_within_days",
    // Incident / Postmortem
    "incident_number",
    "severity",
    "opened_at",
    "closed_at",
    "affected_services",
    "root_cause_postmortem",
    "incident_path",
    // Runbook
    "runbook_kind",
    "applies_to",
    "estimated_duration_minutes",
    "last_verified_at",
    // Architecture
    "related_adrs",
    // Changelog
    "version",
    "release_date",
    // HU
    "external_id",
    "source",
    "kind",
    "assignee",
    "external_url",
    "synced_at",
    // Session / Handoff
    "session_id",
    "pr",
    "branch",
    "commit",
    "cortex_telemetry",
    "parent_session_id",
    // Glossary
    "term",
    "domain",
    "related_terms",
];

fn in_set(set: &[&str], key: &str) -> bool {
    set.contains(&key)
}

// ---------------------------------------------------------------------------
// Result types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct NoteDiff {
    pub path: PathBuf,
    /// "migrate" | "skip" | "unclassifiable" | "error"
    pub action: &'static str,
    pub doc_type: Option<DocType>,
    pub legacy_fm: Mapping,
    pub new_fm: Mapping,
    pub reason: String,
}

#[derive(Debug, Default)]
pub struct MigrationResult {
    pub total_scanned: usize,
    pub migrated: Vec<NoteDiff>,
    pub already_migrated: Vec<NoteDiff>,
    pub unclassifiable: Vec<NoteDiff>,
    pub errors: Vec<NoteDiff>,
    pub backup_path: Option<PathBuf>,
    pub applied: bool,
}

/// Opciones de `migrate_vault` (kwargs de Python).
#[derive(Debug, Clone)]
pub struct MigrateOpts {
    pub apply: bool,
    pub force: bool,
    pub path_filter: Option<PathBuf>,
    pub preserve_legacy: bool,
    pub create_backup_archive: bool,
    pub now: DateTime<Utc>,
}

impl Default for MigrateOpts {
    fn default() -> Self {
        Self {
            apply: false,
            force: false,
            path_filter: None,
            preserve_legacy: true,
            create_backup_archive: true,
            now: Utc::now(),
        }
    }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

pub fn migrate_vault(vault_path: &Path, opts: &MigrateOpts) -> MigrationResult {
    let mut result = MigrationResult {
        applied: opts.apply,
        ..Default::default()
    };

    if !vault_path.exists() {
        return result;
    }

    let scan_root: PathBuf = opts
        .path_filter
        .clone()
        .unwrap_or_else(|| vault_path.to_path_buf());
    let backups_dir = vault_path.join(".cortex").join("backups");

    let md_files = collect_md_sorted(&scan_root);

    let mut diffs: Vec<NoteDiff> = Vec::new();
    for md in md_files {
        if md.starts_with(&backups_dir) {
            continue;
        }
        if md.components().any(|c| c.as_os_str() == "_archived") {
            continue;
        }
        result.total_scanned += 1;
        let diff = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            compute_diff(&md, vault_path, opts)
        })) {
            Ok(d) => d,
            Err(_) => NoteDiff {
                path: md.clone(),
                action: "error",
                doc_type: None,
                legacy_fm: Mapping::new(),
                new_fm: Mapping::new(),
                reason: "unexpected failure".into(),
            },
        };
        if diff.action == "error" {
            result.errors.push(diff);
            continue;
        }
        diffs.push(diff);
    }

    if opts.apply && opts.create_backup_archive {
        result.backup_path = create_backup(vault_path).ok();
    }

    for diff in diffs {
        match diff.action {
            "migrate" => {
                if opts.apply {
                    let _ = apply_diff(&diff);
                }
                result.migrated.push(diff);
            }
            "skip" => result.already_migrated.push(diff),
            "unclassifiable" => result.unclassifiable.push(diff),
            _ => {}
        }
    }

    result
}

/// Payload de `validate_vault` con orden de claves estable.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ValidatePayload {
    #[serde(rename = "vault_path")]
    pub vault_path_str: String,
    pub total: usize,
    pub valid: usize,
    pub invalid: usize,
    pub no_frontmatter: usize,
    /// (ruta relativa posix, mensaje)
    pub issues: Vec<(String, String)>,
}

impl ValidatePayload {
    /// JSON con orden de inserción idéntico al dict de Python.
    pub fn to_json(&self) -> String {
        use std::fmt::Write;
        let mut out = String::from("{");
        let _ = write!(
            out,
            "\"vault_path\": {}, \"total\": {}, \"valid\": {}, \"invalid\": {}, \"no_frontmatter\": {}, \"issues\": ",
            py_json_string(&self.vault_path_str),
            self.total,
            self.valid,
            self.invalid,
            self.no_frontmatter
        );
        out.push('[');
        for (i, (p, e)) in self.issues.iter().enumerate() {
            if i > 0 {
                out.push_str(", ");
            }
            out.push_str(&format!(
                "{{\"path\": {}, \"error\": {}}}",
                py_json_string(p),
                py_json_string(e)
            ));
        }
        out.push_str("]}");
        out
    }
}

/// JSON estilo Python para strings (comillas dobles + escapes mínimos).
fn py_json_string(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn validate_vault(vault_path: &Path) -> ValidatePayload {
    let mut out = ValidatePayload {
        vault_path_str: str_of(vault_path),
        total: 0,
        valid: 0,
        invalid: 0,
        no_frontmatter: 0,
        issues: vec![],
    };
    if !vault_path.exists() {
        return out;
    }
    for md in collect_md_sorted(vault_path) {
        if md.components().any(|c| c.as_os_str() == "_archived") {
            continue;
        }
        out.total += 1;
        match structural_validate(&md, vault_path) {
            Ok(()) => out.valid += 1,
            Err(err) => {
                out.invalid += 1;
                let rel = rel_posix(&md, vault_path);
                out.issues.push((rel, err));
            }
        }
    }
    out.no_frontmatter = out.total.saturating_sub(out.valid + out.invalid);
    out
}

pub fn format_report(result: &MigrationResult) -> String {
    let mut lines: Vec<String> = vec![];
    let mode = if result.applied { "APPLY" } else { "DRY-RUN" };
    lines.push(format!("# Migration Report ({mode})"));
    lines.push(String::new());
    lines.push(format!("- Total scanned: {}", result.total_scanned));
    lines.push(format!("- Migrated: {}", result.migrated.len()));
    lines.push(format!(
        "- Already migrated (skipped): {}",
        result.already_migrated.len()
    ));
    lines.push(format!("- Unclassifiable: {}", result.unclassifiable.len()));
    lines.push(format!("- Errors: {}", result.errors.len()));
    if let Some(bp) = &result.backup_path {
        lines.push(format!("- Backup: {}", bp.display()));
    }
    if !result.unclassifiable.is_empty() {
        lines.push(String::new());
        lines.push("## Unclassifiable notes".into());
        for diff in &result.unclassifiable {
            lines.push(format!("- {} ({})", diff.path.display(), diff.reason));
        }
    }
    if !result.errors.is_empty() {
        lines.push(String::new());
        lines.push("## Errors".into());
        for diff in &result.errors {
            lines.push(format!("- {}: {}", diff.path.display(), diff.reason));
        }
    }
    lines.join("\n")
}

// ---------------------------------------------------------------------------
// Internal: diff computation
// ---------------------------------------------------------------------------

fn compute_diff(md_path: &Path, vault_root: &Path, opts: &MigrateOpts) -> NoteDiff {
    let empty = Mapping::new();
    let legacy_fm = parse_frontmatter_lenient(md_path).unwrap_or_else(|| empty.clone());
    let legacy_ref = &legacy_fm;

    if !opts.force
        && get(legacy_ref, "schema_version") == Some(&YV::Number(1.into()))
        && matches!(get(legacy_ref, "doc_type"), Some(YV::String(_)))
    {
        return NoteDiff {
            path: md_path.to_path_buf(),
            action: "skip",
            doc_type: None,
            legacy_fm,
            new_fm: Mapping::new(),
            reason: "schema_version=1 already present".into(),
        };
    }

    let relative = match md_path.strip_prefix(vault_root) {
        Ok(r) => r.to_path_buf(),
        Err(_) => {
            return NoteDiff {
                path: md_path.to_path_buf(),
                action: "unclassifiable",
                doc_type: None,
                legacy_fm,
                new_fm: Mapping::new(),
                reason: "path outside vault root".into(),
            };
        }
    };

    let inferred = doc_type_from_path(&relative);
    let inferred = match inferred {
        Some(dt) => dt,
        None => {
            return NoteDiff {
                path: md_path.to_path_buf(),
                action: "unclassifiable",
                doc_type: None,
                legacy_fm,
                new_fm: Mapping::new(),
                reason: format!("unable to infer doc_type from path '{}'", posix(&relative)),
            };
        }
    };

    let new_fm = build_new_frontmatter(
        md_path,
        legacy_ref,
        inferred,
        opts.preserve_legacy,
        opts.now,
    );
    NoteDiff {
        path: md_path.to_path_buf(),
        action: "migrate",
        doc_type: Some(inferred),
        legacy_fm,
        new_fm,
        reason: String::new(),
    }
}

fn build_new_frontmatter(
    md_path: &Path,
    legacy: &Mapping,
    doc_type: DocType,
    preserve_legacy: bool,
    now: DateTime<Utc>,
) -> Mapping {
    let created_src = first_truthy_or(legacy, &["created_at", "date"]);
    let created_at = resolve_datetime(created_src, md_path, now);
    let updated_src = legacy.get(YV::String("updated_at".into()));
    let mut updated_at = resolve_datetime(updated_src, md_path, now);
    if updated_at.naive < created_at.naive {
        updated_at = created_at.clone();
    }

    let body = read_body(md_path);
    let fingerprint = compute_fingerprint(&body);

    let title = match legacy.get(YV::String("title".into())) {
        Some(YV::String(s)) if !s.is_empty() => s.clone(),
        _ => python_title(
            &md_path
                .file_stem()
                .unwrap_or_default()
                .to_string_lossy()
                .replace('_', " "),
        ),
    };

    let mut new = Mapping::new();
    new.insert(YV::String("schema_version".into()), YV::Number(1.into()));
    new.insert(
        YV::String("doc_type".into()),
        YV::String(doc_type.as_str().into()),
    );
    new.insert(YV::String("title".into()), YV::String(title));
    new.insert(
        YV::String("created_at".into()),
        YV::String(created_at.iso_format()),
    );
    new.insert(
        YV::String("updated_at".into()),
        YV::String(updated_at.iso_format()),
    );
    new.insert(
        YV::String("tags".into()),
        YV::Sequence(resolve_tags(legacy.get(YV::String("tags".into())))),
    );
    new.insert(
        YV::String("status".into()),
        YV::String(resolve_status(
            legacy.get(YV::String("status".into())),
            doc_type,
        )),
    );
    new.insert(
        YV::String("links".into()),
        YV::Sequence(
            extract_wiki_links(&body)
                .into_iter()
                .map(YV::String)
                .collect(),
        ),
    );
    new.insert(YV::String("vault_scope".into()), YV::String("local".into()));
    new.insert(YV::String("fingerprint".into()), YV::String(fingerprint));

    for (k, v) in type_specific_for(doc_type, md_path, legacy) {
        new.insert(YV::String(k), v);
    }

    if preserve_legacy {
        for (key, value) in legacy.iter() {
            let key_str = match key.as_str() {
                Some(s) => s.to_string(),
                None => continue,
            };
            if in_set(CANONICAL_TOP_LEVEL, &key_str)
                || in_set(LEGACY_MAPPED, &key_str)
                || in_set(TYPE_SPECIFIC_FIELDS, &key_str)
            {
                continue;
            }
            new.insert(YV::String(format!("legacy_{key_str}")), value.clone());
        }
    }

    new
}

fn apply_diff(diff: &NoteDiff) -> std::io::Result<()> {
    let body = read_body(&diff.path);
    let yaml = dump_mapping(&diff.new_fm);
    std::fs::write(&diff.path, format!("---\n{yaml}---\n\n{body}"))
}

// ---------------------------------------------------------------------------
// Internal: field resolvers
// ---------------------------------------------------------------------------

fn read_body(md_path: &Path) -> String {
    let raw = std::fs::read_to_string(md_path).unwrap_or_default();
    let (_, body) = split_frontmatter_and_body(&raw);
    body.trim_start_matches('\n').to_string()
}

/// Réplica de `_resolve_tags`: None→[], str→[s], list→[str(t)], otro→[].
fn resolve_tags(value: Option<&YV>) -> Vec<YV> {
    match value {
        None | Some(YV::Null) => vec![],
        Some(YV::String(s)) => vec![YV::String(s.clone())],
        Some(YV::Sequence(items)) => items.iter().map(|t| YV::String(py_str(t))).collect(),
        Some(_) => vec![],
    }
}

/// `str()` de Python sobre un escalar/lista YAML (repr simple).
fn py_str(v: &YV) -> String {
    match v {
        YV::Null => "None".into(),
        YV::Bool(true) => "True".into(),
        YV::Bool(false) => "False".into(),
        YV::Number(n) => n.to_string(),
        YV::String(s) => s.clone(),
        other => serde_yaml::to_string(other)
            .unwrap_or_default()
            .trim_end()
            .to_string(),
    }
}

fn first_truthy_or<'a>(m: &'a Mapping, keys: &[&str]) -> Option<&'a YV> {
    for k in keys {
        if let Some(v) = m.get(YV::String((*k).into())) {
            if is_truthy(v) {
                return Some(v);
            }
        }
    }
    None
}

fn is_truthy(v: &YV) -> bool {
    match v {
        YV::Null => false,
        YV::Bool(b) => *b,
        YV::Number(n) => n.as_i64().map(|i| i != 0).unwrap_or(true),
        YV::String(s) => !s.is_empty(),
        YV::Sequence(s) => !s.is_empty(),
        YV::Mapping(m) => !m.is_empty(),
        YV::Tagged(t) => is_truthy(&t.value),
    }
}

fn resolve_status(value: Option<&YV>, doc_type: DocType) -> String {
    let valid = doc_type.valid_statuses();
    if let Some(YV::String(s)) = value {
        if valid.contains(&s.as_str()) {
            return s.clone();
        }
        let normalized = s.to_lowercase().replace([' ', '-'], "_");
        let mapped = match doc_type {
            DocType::Session => match normalized.as_str() {
                "generated" => Some("completed"),
                "fallback" => Some("fallback"),
                _ => None,
            },
            DocType::Hu => match normalized.as_str() {
                "imported" => Some("backlog"),
                "in_progress" => Some("in-progress"),
                _ => None,
            },
            _ => None,
        };
        if let Some(m) = mapped {
            if valid.contains(&m) {
                return m.into();
            }
        }
    }
    valid.first().map(|s| (*s).to_string()).unwrap_or_default()
}

/// Instantáneo resuelto conservando si era naive (para isoformat fiel).
#[derive(Debug, Clone)]
struct ResolvedDt {
    naive: NaiveDateTime,
    /// None = naive; Some(offset) = aware con ese offset textual.
    offset: Option<String>,
}

impl ResolvedDt {
    fn iso_format(&self) -> String {
        let base = self.naive.format("%Y-%m-%dT%H:%M:%S").to_string();
        match &self.offset {
            Some(off) => format!("{base}{off}"),
            None => base,
        }
    }
}

fn resolve_datetime(value: Option<&YV>, path: &Path, now: DateTime<Utc>) -> ResolvedDt {
    if let Some(YV::String(s)) = value {
        if let Some(mut dt) = parse_iso_like(s) {
            // Rama string de Python: naive ⇒ dt.replace(tzinfo=UTC) ⇒ SIEMPRE
            // aware con +00:00.
            if dt.offset.is_none() {
                dt.offset = Some("+00:00".into());
            }
            return dt;
        }
    }
    // Fallback: file mtime (aware UTC).
    if let Ok(meta) = path.metadata() {
        if let Ok(modified) = meta.modified() {
            let dt: DateTime<Utc> = modified.into();
            return ResolvedDt {
                naive: dt.naive_utc(),
                offset: Some("+00:00".into()),
            };
        }
    }
    ResolvedDt {
        naive: now.naive_utc(),
        offset: Some("+00:00".into()),
    }
}

/// Parser ISO-like: acepta "YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS[.fff]" con
/// offset "+HH:MM"/"Z" opcional. Equivalencia razonable de
/// `datetime.fromisoformat(value.replace("Z","+00:00"))`.
fn parse_iso_like(s: &str) -> Option<ResolvedDt> {
    let trimmed = s.trim();
    // Separar fecha/hora/offset.
    let (main, offset) = if let Some(stripped) = trimmed.strip_suffix('Z') {
        (stripped, Some("+00:00".to_string()))
    } else if let Some(pos) = trimmed.rfind(['+', '-']) {
        // El '-' de la fecha está antes de posición 10; offsets van después.
        if pos > 10 {
            (&trimmed[..pos], Some(trimmed[pos..].to_string()))
        } else {
            (trimmed, None)
        }
    } else {
        (trimmed, None)
    };
    if let Ok(nd) = NaiveDate::parse_from_str(main, "%Y-%m-%d") {
        let ndt = nd.and_hms_opt(0, 0, 0)?;
        return Some(ResolvedDt { naive: ndt, offset });
    }
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%.f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ] {
        if let Ok(ndt) = NaiveDateTime::parse_from_str(main, fmt) {
            return Some(ResolvedDt { naive: ndt, offset });
        }
    }
    None
}

fn extract_wiki_links(body: &str) -> Vec<String> {
    if body.is_empty() {
        return vec![];
    }
    let re = Regex::new(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]").unwrap();
    let set: BTreeSet<String> = re.captures_iter(body).map(|c| c[1].to_string()).collect();
    set.into_iter().collect()
}

fn type_specific_for(doc_type: DocType, md_path: &Path, legacy: &Mapping) -> Vec<(String, YV)> {
    let stem = md_path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let get = |k: &str| legacy.get(YV::String(k.into()));
    let list_of = |k: &str| -> YV {
        match get(k) {
            Some(YV::Sequence(s)) => YV::Sequence(s.clone()),
            _ => YV::Sequence(vec![]),
        }
    };
    let int_or = |k: &str, default: i64| -> i64 {
        match get(k) {
            Some(YV::Number(n)) => n.as_i64().unwrap_or(default),
            _ => default,
        }
    };
    let str_or_none = |k: &str| -> YV {
        match get(k) {
            Some(v @ YV::String(_)) => v.clone(),
            _ => YV::Null,
        }
    };
    let str_or = |k: &str, default: &str| -> YV {
        match get(k) {
            Some(YV::String(s)) if !s.is_empty() => YV::String(s.clone()),
            _ => YV::String(default.into()),
        }
    };
    let bool_or_false = |k: &str| -> YV {
        match get(k) {
            Some(YV::Bool(b)) => YV::Bool(*b),
            _ => YV::Bool(false),
        }
    };
    match doc_type {
        DocType::Adr => {
            let re = Regex::new(r"^ADR-(\d+)").unwrap();
            // int(m.group(1)) si hay match en el stem; si no
            // int(legacy.get("adr_number") or 1).
            let n = match re.captures(&stem) {
                Some(c) => c[1].parse::<i64>().unwrap_or(1),
                None => match get("adr_number") {
                    Some(YV::Number(x)) if x.as_i64().unwrap_or(0) != 0 => x.as_i64().unwrap_or(1),
                    _ => 1,
                },
            };
            vec![
                ("adr_number".into(), YV::Number(n.into())),
                ("supersedes".into(), list_of("supersedes")),
                ("superseded_by".into(), str_or_none("superseded_by")),
                (
                    "alternatives_considered".into(),
                    list_of("alternatives_considered"),
                ),
                (
                    "acceptance_criteria_met".into(),
                    bool_or_false("acceptance_criteria_met"),
                ),
            ]
        }
        DocType::Incident => {
            let re = Regex::new(r"^INC-(\d+)").unwrap();
            let num = match re.captures(&stem) {
                Some(c) => c[1].parse::<i64>().unwrap_or(1),
                None => match get("incident_number") {
                    Some(YV::Number(x)) if x.as_i64() != Some(0) => x.as_i64().unwrap_or(1),
                    _ => 1,
                },
            };
            let opened_src = if is_truthy_opt(get("opened_at")) {
                get("opened_at")
            } else {
                get("date")
            };
            // Python usa datetime.now(UTC) como fallback aquí (¡no el clock
            // inyectado!). Réplica exacta:
            let opened_now = Utc::now();
            let opened = resolve_datetime(opened_src, md_path, opened_now);
            vec![
                ("incident_number".into(), YV::Number(num.into())),
                ("severity".into(), str_or("severity", "medium")),
                ("opened_at".into(), YV::String(opened.iso_format())),
                ("closed_at".into(), str_or_none("closed_at")),
                ("affected_services".into(), list_of("affected_services")),
                (
                    "root_cause_postmortem".into(),
                    str_or_none("root_cause_postmortem"),
                ),
            ]
        }
        DocType::Postmortem => {
            let re = Regex::new(r"^PM-(\d+)").unwrap();
            let num = match re.captures(&stem) {
                Some(c) => c[1].parse::<i64>().unwrap_or(1),
                None => match get("incident_number") {
                    Some(YV::Number(x)) if x.as_i64() != Some(0) => x.as_i64().unwrap_or(1),
                    _ => 1,
                },
            };
            vec![
                ("incident_number".into(), YV::Number(num.into())),
                ("incident_path".into(), str_or("incident_path", "")),
                ("severity".into(), str_or("severity", "medium")),
            ]
        }
        DocType::Runbook => vec![
            ("runbook_kind".into(), str_or("runbook_kind", "operational")),
            ("applies_to".into(), list_of("applies_to")),
            (
                "estimated_duration_minutes".into(),
                YV::Number(int_or("estimated_duration_minutes", 0).into()),
            ),
            ("last_verified_at".into(), str_or_none("last_verified_at")),
        ],
        DocType::Session => {
            let sid = match get("session_id") {
                Some(YV::String(s)) if !s.is_empty() => YV::String(s.clone()),
                _ => YV::String(derive_session_id(md_path)),
            };
            vec![
                ("session_id".into(), sid),
                ("pr".into(), str_or_none("pr")),
                ("branch".into(), str_or_none("branch")),
                ("commit".into(), str_or_none("commit")),
                ("cortex_telemetry".into(), str_or_none("cortex_telemetry")),
            ]
        }
        DocType::Handoff => vec![(
            "parent_session_id".into(),
            match get("parent_session_id") {
                Some(YV::String(s)) if !s.is_empty() => YV::String(s.clone()),
                _ => YV::String("unknown".into()),
            },
        )],
        DocType::Hu => vec![
            ("external_id".into(), str_or("external_id", &stem)),
            ("source".into(), str_or("source", "unknown")),
            ("kind".into(), str_or("kind", "story")),
            ("assignee".into(), str_or_none("assignee")),
            ("external_url".into(), str_or_none("external_url")),
            ("synced_at".into(), str_or_none("synced_at")),
        ],
        DocType::Glossary => {
            let term = match get("term") {
                Some(YV::String(s)) if !s.is_empty() => s.clone(),
                _ => python_title(&stem.replace('-', " ")),
            };
            vec![
                ("term".into(), YV::String(term)),
                ("domain".into(), str_or_none("domain")),
                ("related_terms".into(), list_of("related_terms")),
            ]
        }
        DocType::Changelog => vec![
            ("version".into(), str_or("version", &stem)),
            ("release_date".into(), str_or_none("release_date")),
        ],
        DocType::Decision => vec![(
            "reversible_within_days".into(),
            YV::Number(int_or("reversible_within_days", 0).into()),
        )],
        DocType::Architecture => vec![("related_adrs".into(), list_of("related_adrs"))],
        DocType::Spec | DocType::Design => vec![],
    }
}

fn is_truthy_opt(v: Option<&YV>) -> bool {
    v.map(is_truthy).unwrap_or(false)
}

fn derive_session_id(path: &Path) -> String {
    let stem = path.file_stem().unwrap_or_default().to_string_lossy();
    let re = Regex::new(r"(?i)\d{4}-\d{2}-\d{2}_([a-f0-9]{6,})").unwrap();
    if let Some(c) = re.captures(&stem) {
        let g = c[1].to_string();
        return g.chars().take(12).collect();
    }
    let slug = slugify(&stem);
    if slug.is_empty() {
        "unknown00000".into()
    } else {
        slug.chars().take(12).collect()
    }
}

/// Réplica de `str.title()` de CPython sobre ASCII.
pub fn python_title(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut upper_next = true;
    for ch in s.chars() {
        if ch.is_alphabetic() {
            if upper_next {
                out.extend(ch.to_uppercase());
            } else {
                out.extend(ch.to_lowercase());
            }
            upper_next = false;
        } else {
            upper_next = true;
            out.push(ch);
        }
    }
    out
}

// ---------------------------------------------------------------------------
// doc_type inference (réplica de doc_type.doc_type_from_path)
// ---------------------------------------------------------------------------

const SUBFOLDERS: &[(&str, DocType)] = &[
    ("sessions", DocType::Session),
    ("handoffs", DocType::Handoff),
    ("specs", DocType::Spec),
    ("incidents", DocType::Incident),
    ("postmortems", DocType::Postmortem),
    ("runbooks", DocType::Runbook),
    ("architecture", DocType::Architecture),
    ("changelog", DocType::Changelog),
    ("hu", DocType::Hu),
    ("glossary", DocType::Glossary),
    ("designs", DocType::Design),
];

pub fn doc_type_from_path(relative: &Path) -> Option<DocType> {
    let parts: Vec<String> = relative
        .components()
        .map(|c| c.as_os_str().to_string_lossy().to_string())
        .collect();
    if parts.len() < 2 {
        return None;
    }
    let subfolder = parts[..parts.len() - 1]
        .iter()
        .find(|p| SUBFOLDERS.iter().any(|(s, _)| s == p) || p.as_str() == "decisions")?;
    if subfolder == "decisions" {
        let stem = relative.file_stem().unwrap_or_default().to_string_lossy();
        let re = Regex::new(r"(?i)^ADR-\d+").unwrap();
        if re.is_match(&stem) {
            return Some(DocType::Adr);
        }
        return Some(DocType::Decision);
    }
    SUBFOLDERS
        .iter()
        .find(|(s, _)| s == subfolder)
        .map(|(_, dt)| *dt)
}

// ---------------------------------------------------------------------------
// Helpers de filesystem / split / parse
// ---------------------------------------------------------------------------

fn str_of(p: &Path) -> String {
    p.to_string_lossy().to_string()
}

fn posix(p: &Path) -> String {
    p.components()
        .map(|c| c.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

fn rel_posix(md: &Path, root: &Path) -> String {
    md.strip_prefix(root)
        .map(posix)
        .unwrap_or_else(|_| posix(md))
}

/// rglob("*.md") ordenado como Python (comparación lexicográfica de rutas).
fn collect_md_sorted(scan_root: &Path) -> Vec<PathBuf> {
    let mut out: Vec<(String, PathBuf)> = Vec::new();
    fn walk(dir: &Path, out: &mut Vec<(String, PathBuf)>) {
        let Ok(rd) = std::fs::read_dir(dir) else {
            return;
        };
        let mut entries: Vec<PathBuf> = rd.flatten().map(|e| e.path()).collect();
        entries.sort_by_key(|p| str_of(p).clone());
        for p in entries {
            if p.is_dir() {
                walk(&p, out);
            } else if p.extension().and_then(|e| e.to_str()) == Some("md") {
                out.push((posix(&p), p));
            }
        }
    }
    walk(scan_root, &mut out);
    out.sort_by(|a, b| a.0.cmp(&b.0));
    out.into_iter().map(|(_, p)| p).collect()
}

/// Split estilo `_FRONTMATTER_RE = ^---\s*\n(.*?)\n---\s*\n?` (DOTALL):
/// consume TODO el whitespace tras el cierre (incluye saltos y espacios).
pub fn split_frontmatter_and_body(content: &str) -> (Option<String>, String) {
    if !content.starts_with("---") {
        return (None, content.to_string());
    }
    let after_open = &content[3..];
    let Some(after_open) = after_open
        .trim_start_matches([' ', '\t'])
        .strip_prefix('\n')
    else {
        return (None, content.to_string());
    };
    // Buscar cierre "\n---" en columna.
    let bytes = after_open.as_bytes();
    let mut close_pos: Option<usize> = None;
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'\n' && bytes.get(i + 1..i + 4) == Some(b"---") {
            close_pos = Some(i);
            break;
        }
        i += 1;
    }
    let close = match close_pos {
        Some(c) => c,
        None => return (None, content.to_string()),
    };
    let fm = after_open[..close].to_string();
    let rest = &after_open[close + 4..]; // salta "\n---"
                                         // \s*\n? ⇒ consume todo el whitespace restante.
    let body_start = rest
        .find(|c: char| !c.is_whitespace())
        .unwrap_or(rest.len());
    (Some(fm), rest[body_start..].to_string())
}

/// `parse_frontmatter_lenient`: `{}` ante cualquier fallo.
fn parse_frontmatter_lenient(path: &Path) -> Option<Mapping> {
    let content = std::fs::read_to_string(path).ok()?;
    let (fm, _) = split_frontmatter_and_body(&content);
    let fm = fm?;
    if fm.trim().is_empty() {
        return Some(Mapping::new());
    }
    let parsed: serde_yaml::Value = serde_yaml::from_str(&fm).ok()?;
    match parsed {
        YV::Mapping(m) => Some(m),
        YV::Null => Some(Mapping::new()),
        _ => None,
    }
}

fn get<'a>(m: &'a Mapping, k: &str) -> Option<&'a YV> {
    m.get(YV::String(k.into()))
}

/// Conversión Mapping → texto vía el dumper byte-compatible de cortex-setup.
fn dump_mapping(m: &Mapping) -> String {
    let y = yv_to_yaml(&YV::Mapping(m.clone()));
    cortex_setup::yaml::dump(&y)
}

fn yv_to_yaml(v: &YV) -> Yaml {
    match v {
        YV::Null => Yaml::Null,
        YV::Bool(b) => Yaml::Bool(*b),
        YV::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Int(i)
            } else {
                Yaml::Float(n.as_f64().unwrap_or(0.0))
            }
        }
        YV::String(s) => Yaml::Str(s.clone()),
        YV::Sequence(items) => Yaml::Seq(items.iter().map(yv_to_yaml).collect()),
        YV::Mapping(m) => Yaml::Map(
            m.iter()
                .map(|(k, val)| {
                    let ks = k
                        .as_str()
                        .map(str::to_string)
                        .unwrap_or_else(|| panic!("clave YAML no-string no soportada: {k:?}"));
                    (ks, yv_to_yaml(val))
                })
                .collect(),
        ),
        YV::Tagged(t) => yv_to_yaml(&t.value),
    }
}

// ---------------------------------------------------------------------------
// Backup (shell-out a tar; el contenido del archivo no es contrato)
// ---------------------------------------------------------------------------

pub fn create_backup(vault_path: &Path) -> Result<PathBuf, String> {
    if !vault_path.exists() {
        return Err(format!("vault path not found: {}", vault_path.display()));
    }
    let target_dir = vault_path
        .parent()
        .unwrap_or(Path::new("."))
        .join(".cortex")
        .join("backups");
    std::fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;
    let timestamp = Utc::now().format("%Y-%m-%dT%H%M%SZ");
    let name = format!("vault-{timestamp}");
    let backup_path = target_dir.join(format!("{name}.tar.gz"));
    let status = Command::new("tar")
        .arg("-czf")
        .arg(&backup_path)
        .arg("-C")
        .arg(vault_path.parent().unwrap_or(Path::new(".")))
        .arg(vault_path.file_name().unwrap_or_default())
        .status()
        .map_err(|e| format!("tar failed: {e}"))?;
    if !status.success() {
        return Err("tar exited non-zero".into());
    }
    Ok(backup_path)
}

/// `cortex.documentation.backup.list_backups`: backups en `backups_dir`
/// (globo `vault-*.tar.gz`) ordenados por nombre (timestamp asc).
/// Espejo de `sorted(backups_dir.glob("vault-*" + ".tar.gz"))`.
pub fn list_backups(backups_dir: &Path) -> Vec<PathBuf> {
    if !backups_dir.exists() {
        return Vec::new();
    }
    let mut out: Vec<PathBuf> = match std::fs::read_dir(backups_dir) {
        Ok(rd) => rd
            .flatten()
            .map(|e| e.path())
            .filter(|p| {
                p.is_file()
                    && p.file_name()
                        .and_then(|n| n.to_str())
                        .map(|n| n.starts_with("vault-") && n.ends_with(".tar.gz"))
                        .unwrap_or(false)
            })
            .collect(),
        Err(_) => Vec::new(),
    };
    out.sort();
    out
}

/// `cortex.documentation.backup.restore_backup(backup_path, target_parent)`.
///
/// Extrae el tar.gz con `tar xzf` (mismo patrón shell-out que
/// [`create_backup`]) y devuelve la raíz restaurada
/// `target_parent / top`, donde `top` es el nombre del primer miembro del
/// archivo (la carpeta original del vault).
///
/// Seguridad tar-slip espejo del oráculo: se rechaza cualquier miembro que
/// resuelva fuera de `target_parent`. Errores exactos del oráculo:
/// `backup not found: {path}` y `empty backup: {path}`.
pub fn restore_backup(backup_path: &Path, target_parent: &Path) -> Result<PathBuf, String> {
    if !backup_path.exists() {
        return Err(format!("backup not found: {}", backup_path.display()));
    }
    // Listar miembros con `tar tzf` (validación + resolución del top).
    let listing = Command::new("tar")
        .arg("-tzf")
        .arg(backup_path)
        .output()
        .map_err(|e| format!("tar failed: {e}"))?;
    if !listing.status.success() {
        return Err("tar exited non-zero".into());
    }
    let members: Vec<String> = String::from_utf8_lossy(&listing.stdout)
        .lines()
        .map(str::to_string)
        .filter(|l| !l.is_empty())
        .collect();
    if members.is_empty() {
        return Err(format!("empty backup: {}", backup_path.display()));
    }
    let top = members[0].split('/').next().unwrap_or("").to_string();
    if top.is_empty() {
        return Err(format!("empty backup: {}", backup_path.display()));
    }
    // Tar-slip: espejo de `(target_parent / member).resolve().is_relative_to(
    // resolved_target)` — rechaza absolutos, ".." y escapes del target.
    for member in &members {
        if member.starts_with('/') || member.split('/').any(|c| c == "..") {
            return Err(format!("unsafe member in backup archive: {member:?}"));
        }
    }
    std::fs::create_dir_all(target_parent).map_err(|e| e.to_string())?;
    let status = Command::new("tar")
        .arg("-xzf")
        .arg(backup_path)
        .arg("-C")
        .arg(target_parent)
        .status()
        .map_err(|e| format!("tar failed: {e}"))?;
    if !status.success() {
        return Err("tar exited non-zero".into());
    }
    Ok(target_parent.join(top))
}

// ---------------------------------------------------------------------------
// Validación estructural (validate_vault)
//
// Clases de error EXACTAS (validation.py):
// - "No frontmatter in {path}"
// - "Invalid YAML: {e}"          (normalizado {{YAML_ERR}} en gates)
// - "doc_type field is required in frontmatter"
// - f"doc_type must be a string, got {pytype}"
// - f"Unknown doc_type: {raw!r}"
// - f"vault_scope must be 'local' or 'enterprise', got {scope!r}"
//
// Fallos de schema pydantic (campos requeridos, patrones, tz-awareness,
// orden de fechas, status válido) se colapsan a
// "Frontmatter validation failed for {dt}: {{SCHEMA_ERR}}" — el volcado de
// errores de pydantic NO es contrato.
// ---------------------------------------------------------------------------

/// Campos type-specific REQUERIDOS (sin default) por schema pydantic.
fn required_specific(dt: DocType) -> &'static [&'static str] {
    match dt {
        DocType::Adr => &["adr_number"],
        DocType::Changelog => &["version"],
        DocType::Design => &["session_id", "spec_path"],
        DocType::Glossary => &["term"],
        DocType::Handoff => &["parent_session_id"],
        DocType::Hu => &["external_id", "source"],
        DocType::Incident => &["incident_number", "severity", "opened_at"],
        DocType::Postmortem => &["incident_number", "incident_path", "severity"],
        DocType::Session => &["session_id"],
        _ => &[],
    }
}

fn py_type_name(v: &YV) -> &'static str {
    match v {
        YV::Null => "NoneType",
        YV::Bool(_) => "bool",
        YV::Number(n) if n.is_i64() || n.is_u64() => "int",
        YV::Number(_) => "float",
        YV::String(_) => "str",
        YV::Sequence(_) => "list",
        YV::Mapping(_) => "dict",
        YV::Tagged(t) => py_type_name(&t.value),
    }
}

fn structural_validate(md: &Path, _vault_root: &Path) -> Result<(), String> {
    let content = std::fs::read_to_string(md).map_err(|e| e.to_string())?;
    let (fm_raw, _) = split_frontmatter_and_body(&content);
    let Some(fm) = fm_raw else {
        return Err(format!("No frontmatter in {}", str_of(md)));
    };
    let parsed: serde_yaml::Value =
        serde_yaml::from_str(&fm).map_err(|_| "{{YAML_ERR}}".to_string())?;
    // Nota: el oracle emite "Invalid YAML: <py>" — el gate normaliza ambos.
    let parsed = match parsed {
        YV::Mapping(m) => m,
        YV::Null => {
            return Err("doc_type field is required in frontmatter".into());
        }
        _ => {
            return Err("doc_type field is required in frontmatter".into());
        }
    };
    let Some(YV::String(raw_dt)) = get(&parsed, "doc_type") else {
        if let Some(v) = get(&parsed, "doc_type") {
            return Err(format!(
                "doc_type must be a string, got {}",
                py_type_name(v)
            ));
        }
        return Err("doc_type field is required in frontmatter".into());
    };
    let Some(doc_type) = DocType::parse(raw_dt) else {
        return Err(format!("Unknown doc_type: '{raw_dt}'"));
    };
    let scope = match get(&parsed, "vault_scope") {
        Some(YV::String(s)) => s.clone(),
        Some(other) => {
            return Err(format!(
                "vault_scope must be 'local' or 'enterprise', got {}",
                python_repr_scalar(other)
            ));
        }
        None => "local".to_string(),
    };
    if scope != "local" && scope != "enterprise" {
        return Err(format!(
            "vault_scope must be 'local' or 'enterprise', got '{scope}'"
        ));
    }

    // ---- Schema checks (colapsados a texto normalizado) -------------------
    let fail = || {
        Err(format!(
            "Frontmatter validation failed for {}: {{SCHEMA_ERR}}",
            doc_type.as_str()
        ))
    };

    let title_ok = matches!(get(&parsed, "title"), Some(YV::String(s)) if !s.is_empty());
    let created_ok = matches!(get(&parsed, "created_at"), Some(YV::String(s)) if is_aware_iso(s));
    let updated_ok = matches!(get(&parsed, "updated_at"), Some(YV::String(s)) if is_aware_iso(s));
    let status_ok = match get(&parsed, "status") {
        Some(YV::String(s)) => doc_type.valid_statuses().contains(&s.as_str()),
        _ => false,
    };
    let fp_re = Regex::new(r"^[a-f0-9]{64}$").unwrap();
    let fp_ok = matches!(get(&parsed, "fingerprint"), Some(YV::String(s)) if fp_re.is_match(s));
    let order_ok = match (get(&parsed, "created_at"), get(&parsed, "updated_at")) {
        (Some(YV::String(a)), Some(YV::String(b))) => {
            match (parse_iso_like(a), parse_iso_like(b)) {
                (Some(x), Some(y)) => y.naive >= x.naive,
                _ => false,
            }
        }
        _ => false,
    };
    let specific_ok = required_specific(doc_type)
        .iter()
        .all(|k| is_truthy_opt(get(&parsed, k)));
    // adr/incident/postmortem numbers deben ser int >= 1 cuando presentes.
    let numbers_ok = [
        ("adr_number", DocType::Adr),
        ("incident_number", DocType::Incident),
    ]
    .iter()
    .all(|(k, dt)| {
        *dt != doc_type
            || match get(&parsed, k) {
                Some(YV::Number(n)) => n.as_i64().map(|x| x >= 1).unwrap_or(false),
                _ => false,
            }
    });
    // estimated_duration_minutes/reversible_within_days: int >= 0 con default.
    let ge0_ok = [("reversible_within_days", DocType::Decision)]
        .iter()
        .all(|(k, dt)| {
            *dt != doc_type
                || match get(&parsed, k) {
                    None => true,
                    Some(YV::Number(n)) => n.as_i64().map(|x| x >= 0).unwrap_or(false),
                    Some(_) => false,
                }
        });

    if title_ok
        && created_ok
        && updated_ok
        && status_ok
        && fp_ok
        && order_ok
        && specific_ok
        && numbers_ok
        && ge0_ok
    {
        Ok(())
    } else {
        fail()
    }
}

fn is_aware_iso(s: &str) -> bool {
    match parse_iso_like(s) {
        Some(dt) => dt.offset.is_some(),
        None => false,
    }
}

/// repr() de Python para escalares simples (usado en mensajes de scope).
fn python_repr_scalar(v: &YV) -> String {
    match v {
        YV::Null => "None".into(),
        YV::Bool(true) => "True".into(),
        YV::Bool(false) => "False".into(),
        YV::Number(n) => n.to_string(),
        YV::String(s) => format!("'{s}'"),
        other => serde_yaml::to_string(other)
            .unwrap_or_default()
            .trim()
            .to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_title_estilo_cpython() {
        assert_eq!(python_title("my cool note"), "My Cool Note");
        assert_eq!(python_title("multi word term"), "Multi Word Term");
        assert_eq!(python_title("ADR-007"), "Adr-007");
        assert_eq!(python_title("2.0.0"), "2.0.0");
        assert_eq!(python_title("hola MUNDO"), "Hola Mundo");
    }

    #[test]
    fn split_frontmatter_estilos() {
        let (fm, body) = split_frontmatter_and_body("---\na: 1\n---\n\nbody\n");
        assert_eq!(fm.as_deref(), Some("a: 1"));
        assert_eq!(body, "body\n");
        let (fm2, b2) = split_frontmatter_and_body("sin frontmatter");
        assert_eq!(fm2, None);
        assert_eq!(b2, "sin frontmatter");
        let (fm3, _) = split_frontmatter_and_body("---\nsin cierre");
        assert_eq!(fm3, None);
        // El regex consume todo el whitespace tras el cierre.
        let (_, b4) = split_frontmatter_and_body("---\na: 1\n---\n\n\n  x");
        assert_eq!(b4, "x");
    }

    #[test]
    fn inferencia_por_ruta() {
        assert_eq!(
            doc_type_from_path(Path::new("sessions/2026-01-01_ab.md")),
            Some(DocType::Session)
        );
        assert_eq!(
            doc_type_from_path(Path::new("decisions/ADR-001-x.md")),
            Some(DocType::Adr)
        );
        assert_eq!(
            doc_type_from_path(Path::new("decisions/DEC-1-y.md")),
            Some(DocType::Decision)
        );
        assert_eq!(
            doc_type_from_path(Path::new("decisions/adr-002-z.md")),
            Some(DocType::Adr) // IGNORECASE
        );
        assert_eq!(doc_type_from_path(Path::new("random/x.md")), None);
        assert_eq!(doc_type_from_path(Path::new("soloarchivo.md")), None);
        assert_eq!(
            doc_type_from_path(Path::new("deep/nested/specs/a.md")),
            Some(DocType::Spec)
        );
    }

    #[test]
    fn status_mappings_y_defaults() {
        assert_eq!(
            resolve_status(Some(&YV::String("generated".into())), DocType::Session),
            "completed"
        );
        assert_eq!(
            resolve_status(Some(&YV::String("imported".into())), DocType::Hu),
            "backlog"
        );
        assert_eq!(
            resolve_status(Some(&YV::String("proposed".into())), DocType::Adr),
            "proposed"
        );
        // Inválido ⇒ primero de los válidos ordenados.
        assert_eq!(
            resolve_status(Some(&YV::String("weird".into())), DocType::Decision),
            "active"
        );
        assert_eq!(resolve_status(None, DocType::Session), "auto-draft");
    }

    #[test]
    fn derivacion_de_session_id() {
        let p = Path::new("/v/sessions/2026-04-14_abc123def456_titulo.md");
        assert_eq!(derive_session_id(p), "abc123def456");
        let q = Path::new("/v/sessions/session-no-id.md");
        assert_eq!(derive_session_id(q), "session-no-i");
        let r = Path::new("/v/sessions/zzz.md");
        assert_eq!(derive_session_id(r), "zzz");
    }

    #[test]
    fn tags_legacy() {
        assert!(resolve_tags(None).is_empty());
        assert_eq!(
            resolve_tags(Some(&YV::String("uno".into()))),
            vec![YV::String("uno".into())]
        );
        assert_eq!(
            resolve_tags(Some(&YV::Sequence(vec![
                YV::String("a".into()),
                YV::Number(1.into()),
                YV::Bool(true),
            ]))),
            vec![
                YV::String("a".into()),
                YV::String("1".into()),
                YV::String("True".into()),
            ]
        );
        assert!(resolve_tags(Some(&YV::Bool(true))).is_empty());
    }
}
