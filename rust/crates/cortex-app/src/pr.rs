//! Puerto de `cortex.pr_capture` + `cortex.models.PRContext` +
//! `cortex.services.pr_service.PRService` (P12A-3).
//!
//! Espeja `tests/unit/pr/test_pr_context.py`. La serialización JSON replica
//! `PRContext.model_dump_json(indent=2)` de pydantic v2 (orden de declaración
//! de campos, nulls explícitos, indent 2, UTF-8 crudo) para que
//! save_context/capture_from_json sean byte-parity con el oráculo.
//!
//! Divergencias documentadas:
//! - `capture_from_github` con `PR_NUMBER` no numérico: Python lanza
//!   ValueError; acá cae a 0 (estrictamente más tolerante).
//! - `hu_references` devuelve el MISMO CONJUNTO pero el orden no es
//!   contrato: Python hace `list(set(refs))` (orden no determinista); los
//!   gates comparan como conjunto ordenado.
//! - La presentación typer (`cli/pr_context.py`) la wirea el CLI nativo del
//!   stream B (§7.1.3 doc 09); acá vive la capa de servicio.
//!
//! `generate_pr_docs`/`write_pr_docs` entran en P12A-4 junto con el porte de
//! `doc_generator` (dependencia declarada del servicio).

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::process::Command;

use regex::RegexBuilder;

use crate::workitems::{EpisodicMemoryRequest, EpisodicSink};

// ── PRContext (cortex/models.py) ────────────────────────────────────────────

/// Orden de campos = orden de declaración pydantic (contrato JSON).
#[derive(Debug, Clone, PartialEq)]
pub struct PRContext {
    pub pr_number: i64,
    pub title: String,
    pub body: String,
    pub author: String,
    pub source_branch: String,
    pub target_branch: String,
    pub commit_sha: String,
    pub files_changed: Vec<String>,
    pub diff_summary: String,
    pub db_migrations: Vec<String>,
    pub api_changes: Vec<String>,
    pub labels: Vec<String>,
    pub lint_result: Option<String>,
    pub audit_result: Option<String>,
    pub test_result: Option<String>,
}

impl Default for PRContext {
    fn default() -> Self {
        Self {
            pr_number: 0,
            title: String::new(),
            body: String::new(),
            author: String::new(),
            source_branch: String::new(),
            target_branch: "main".to_string(),
            commit_sha: String::new(),
            files_changed: Vec::new(),
            diff_summary: String::new(),
            db_migrations: Vec::new(),
            api_changes: Vec::new(),
            labels: Vec::new(),
            lint_result: None,
            audit_result: None,
            test_result: None,
        }
    }
}

impl PRContext {
    /// `hu_references`: los 4 patrones en orden, IGNORECASE, prefijos según
    /// patrón, dedup por conjunto (el orden NO es contrato — ver header).
    pub fn hu_references(&self) -> Vec<String> {
        let mut refs: Vec<String> = Vec::new();
        let pat = |pattern: &str| {
            RegexBuilder::new(pattern)
                .case_insensitive(true)
                .build()
                .expect("regex válida")
        };
        // r"\b([A-Z][A-Z0-9]+-\d+)\b" → str(match).upper()
        if let Ok(re) = RegexBuilder::new(r"\b([A-Z][A-Z0-9]+-\d+)\b")
            .case_insensitive(true)
            .build()
        {
            for cap in re.captures_iter(&self.body) {
                if let Some(m) = cap.get(1) {
                    refs.push(m.as_str().to_uppercase());
                }
            }
        }
        for pattern in [
            r"HU[-_]?(\d+)",
            r"(?:user[\s-]?story|us)[-\s](\d+)",
            r"#(\d+)",
        ] {
            let re = pat(pattern);
            for cap in re.captures_iter(&self.body) {
                if let Some(m) = cap.get(1) {
                    refs.push(format!("HU-{}", m.as_str()));
                }
            }
        }
        let uniq: BTreeSet<String> = refs.into_iter().collect();
        uniq.into_iter().collect()
    }

    pub fn has_db_changes(&self) -> bool {
        !self.db_migrations.is_empty()
            || self
                .files_changed
                .iter()
                .any(|f| f.contains("migration") || f.contains("schema") || f.ends_with(".sql"))
    }

    pub fn has_api_changes(&self) -> bool {
        !self.api_changes.is_empty()
            || self
                .files_changed
                .iter()
                .any(|f| f.contains("route") || f.contains("controller") || f.contains("endpoint"))
    }

    pub fn has_adr_label(&self) -> bool {
        self.labels.iter().any(|lbl| {
            lbl.to_lowercase().contains("adr") || lbl.to_lowercase().contains("decision")
        })
    }

    /// Serialización estilo pydantic v2 `model_dump_json(indent=2)`.
    pub fn to_pydantic_json(&self) -> String {
        let mut out = String::new();
        let mut campos: Vec<(&str, JVal)> = Vec::new();
        macro_rules! push {
            ($k:expr, $v:expr) => {
                campos.push(($k, $v))
            };
        }
        push!("pr_number", JVal::Int(self.pr_number));
        push!("title", JVal::Str(&self.title));
        push!("body", JVal::Str(&self.body));
        push!("author", JVal::Str(&self.author));
        push!("source_branch", JVal::Str(&self.source_branch));
        push!("target_branch", JVal::Str(&self.target_branch));
        push!("commit_sha", JVal::Str(&self.commit_sha));
        push!("files_changed", JVal::StrList(&self.files_changed));
        push!("diff_summary", JVal::Str(&self.diff_summary));
        push!("db_migrations", JVal::StrList(&self.db_migrations));
        push!("api_changes", JVal::StrList(&self.api_changes));
        push!("labels", JVal::StrList(&self.labels));
        push!("lint_result", JVal::OptStr(self.lint_result.as_deref()));
        push!("audit_result", JVal::OptStr(self.audit_result.as_deref()));
        push!("test_result", JVal::OptStr(self.test_result.as_deref()));

        out.push_str("{\n");
        for (i, (k, v)) in campos.iter().enumerate() {
            if i > 0 {
                out.push_str(",\n");
            }
            out.push_str("  ");
            out.push_str(&json_escape(k));
            out.push_str(": ");
            v.emit(1, &mut out);
        }
        out.push_str("\n}");
        out
    }

    /// Deserialización tolerante (todos los campos tienen default salvo los
    /// requeridos title/author/source_branch/commit_sha, que fallan igual
    /// que pydantic si faltan).
    pub fn from_json_value(data: &serde_json::Value) -> Result<Self, String> {
        let obj = data
            .as_object()
            .ok_or_else(|| "Input should be a valid dictionary".to_string())?;
        let s = |k: &str| -> String {
            obj.get(k)
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_default()
        };
        let req = |k: &str| -> Result<String, String> {
            match obj.get(k) {
                Some(serde_json::Value::String(v)) => Ok(v.clone()),
                _ => Err(format!(
                    "Field required [{k}]\nFor further information visit https://errors.pydantic.dev"
                )),
            }
        };
        let list = |k: &str| -> Vec<String> {
            obj.get(k)
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default()
        };
        Ok(Self {
            pr_number: obj.get("pr_number").and_then(|v| v.as_i64()).unwrap_or(0),
            title: req("title")?,
            body: s("body"),
            author: req("author")?,
            source_branch: req("source_branch")?,
            target_branch: {
                let t = s("target_branch");
                if t.is_empty() {
                    "main".to_string()
                } else {
                    t
                }
            },
            commit_sha: req("commit_sha")?,
            files_changed: list("files_changed"),
            diff_summary: s("diff_summary"),
            db_migrations: list("db_migrations"),
            api_changes: list("api_changes"),
            labels: list("labels"),
            lint_result: obj
                .get("lint_result")
                .and_then(|v| v.as_str())
                .map(String::from),
            audit_result: obj
                .get("audit_result")
                .and_then(|v| v.as_str())
                .map(String::from),
            test_result: obj
                .get("test_result")
                .and_then(|v| v.as_str())
                .map(String::from),
        })
    }
}

enum JVal<'a> {
    Int(i64),
    Str(&'a str),
    StrList(&'a [String]),
    OptStr(Option<&'a str>),
}

fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

impl JVal<'_> {
    fn emit(&self, nivel: usize, out: &mut String) {
        let pad = "  ".repeat(nivel);
        match self {
            JVal::Int(n) => out.push_str(&n.to_string()),
            JVal::Str(s) => out.push_str(&json_escape(s)),
            JVal::OptStr(None) => out.push_str("null"),
            JVal::OptStr(Some(s)) => out.push_str(&json_escape(s)),
            JVal::StrList(items) => {
                if items.is_empty() {
                    out.push_str("[]");
                    return;
                }
                out.push_str("[\n");
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push_str(",\n");
                    }
                    out.push_str(&pad);
                    out.push_str("  ");
                    out.push_str(&json_escape(item));
                }
                out.push('\n');
                out.push_str(&pad);
                out.push(']');
            }
        }
    }
}

// ── pr_capture.py ───────────────────────────────────────────────────────────

/// `_run_git`: stdout strip; errores ⇒ vacío (subprocess.run sin check).
fn run_git(args: &[&str], cwd: Option<&Path>) -> String {
    let mut cmd = Command::new("git");
    cmd.args(args);
    if let Some(dir) = cwd {
        cmd.current_dir(dir);
    }
    match cmd.output() {
        Ok(out) => String::from_utf8_lossy(&out.stdout).trim().to_string(),
        Err(_) => String::new(),
    }
}

/// `_get_files_changed` con fallback origin/base.
pub fn get_files_changed(base: &str, head: &str) -> Vec<String> {
    get_files_changed_in(base, head, None)
}

pub fn get_files_changed_in(base: &str, head: &str, cwd: Option<&Path>) -> Vec<String> {
    let mut output = run_git(&["diff", "--name-only", &format!("{base}...{head}")], cwd);
    if output.is_empty() {
        output = run_git(
            &["diff", "--name-only", &format!("origin/{base}...{head}")],
            cwd,
        );
    }
    output
        .split('\n')
        .filter(|f| !f.is_empty())
        .map(String::from)
        .collect()
}

/// `_get_diff_summary`.
pub fn get_diff_summary(base: &str, head: &str) -> String {
    get_diff_summary_in(base, head, None)
}

pub fn get_diff_summary_in(base: &str, head: &str, cwd: Option<&Path>) -> String {
    let mut output = run_git(&["diff", "--stat", &format!("{base}...{head}")], cwd);
    if output.is_empty() {
        output = run_git(&["diff", "--stat", &format!("origin/{base}...{head}")], cwd);
    }
    output
}

const DB_INDICATORS: &[&str] = &[
    "migration",
    "schema",
    "alembic",
    "flyway",
    "liquibase",
    ".sql",
    "prisma",
    "sequelize",
    "typeorm",
    "knex",
];

const API_INDICATORS: &[&str] = &[
    "route",
    "controller",
    "endpoint",
    "api/",
    "handler",
    "view",
    "resource",
    "rest",
];

/// `_detect_db_migrations`.
pub fn detect_db_migrations(files_changed: &[String]) -> Vec<String> {
    files_changed
        .iter()
        .filter(|f| {
            DB_INDICATORS
                .iter()
                .any(|ind| f.to_lowercase().contains(ind))
        })
        .cloned()
        .collect()
}

/// `_detect_api_changes`.
pub fn detect_api_changes(files_changed: &[String]) -> Vec<String> {
    files_changed
        .iter()
        .filter(|f| {
            API_INDICATORS
                .iter()
                .any(|ind| f.to_lowercase().contains(ind))
        })
        .cloned()
        .collect()
}

/// `capture_from_github` sobre env explícito (inyectable para tests/gate).
pub fn capture_from_env(getenv: &dyn Fn(&str) -> Option<String>) -> PRContext {
    let getenv_default = |k: &str, d: &str| getenv(k).unwrap_or_else(|| d.to_string());
    let pr_number = getenv("PR_NUMBER")
        .and_then(|v| v.parse::<i64>().ok())
        .unwrap_or(0);
    let title = getenv_default("PR_TITLE", "Untitled PR");
    let body = getenv_default("PR_BODY", "");
    let author = getenv_default("PR_AUTHOR", "unknown");
    let source_branch = match getenv("PR_BRANCH") {
        Some(b) => b,
        None => getenv("GITHUB_HEAD_REF").unwrap_or_default(),
    };
    let target_branch = match getenv("TARGET_BRANCH") {
        Some(b) => b,
        None => getenv("GITHUB_BASE_REF").unwrap_or_else(|| "main".into()),
    };
    let commit_sha = match getenv("PR_COMMIT") {
        Some(c) => c,
        None => getenv("GITHUB_SHA").unwrap_or_default(),
    };
    let labels_raw = getenv("PR_LABELS").unwrap_or_default();
    let labels: Vec<String> = if labels_raw.is_empty() {
        Vec::new()
    } else {
        labels_raw
            .split(',')
            .map(str::trim)
            .filter(|l| !l.is_empty())
            .map(String::from)
            .collect()
    };

    let files_changed = get_files_changed(&target_branch, &commit_sha);
    let diff_summary = get_diff_summary(&target_branch, &commit_sha);
    PRContext {
        pr_number,
        title,
        body,
        author,
        source_branch,
        target_branch,
        commit_sha,
        files_changed: files_changed.clone(),
        diff_summary,
        db_migrations: detect_db_migrations(&files_changed),
        api_changes: detect_api_changes(&files_changed),
        labels,
        lint_result: None,
        audit_result: None,
        test_result: None,
    }
}

/// `capture_from_github()` real (variables de entorno del proceso).
pub fn capture_from_github() -> PRContext {
    capture_from_env(&|k: &str| std::env::var(k).ok())
}

/// Args de `capture_manual` (keyword-only en Python).
pub struct CaptureManualArgs {
    pub title: String,
    pub author: String,
    pub branch: String,
    pub commit: String,
    pub body: String,
    pub pr_number: i64,
    pub target_branch: String,
    pub labels: Vec<String>,
}

impl Default for CaptureManualArgs {
    fn default() -> Self {
        Self {
            title: String::new(),
            author: String::new(),
            branch: String::new(),
            commit: String::new(),
            body: String::new(),
            pr_number: 0,
            target_branch: "main".to_string(),
            labels: Vec::new(),
        }
    }
}

pub fn capture_manual(args: CaptureManualArgs) -> PRContext {
    capture_manual_in(args, None)
}

/// Variante con cwd explícito (tests/gates corren fuera de repo).
pub fn capture_manual_in(args: CaptureManualArgs, cwd: Option<&Path>) -> PRContext {
    let CaptureManualArgs {
        title,
        author,
        branch,
        commit,
        body,
        pr_number,
        target_branch,
        labels,
    } = args;
    let files_changed = get_files_changed_in(&target_branch, &commit, cwd);
    let diff_summary = get_diff_summary_in(&target_branch, &commit, cwd);
    PRContext {
        pr_number,
        title,
        body,
        author,
        source_branch: branch,
        target_branch,
        commit_sha: commit,
        files_changed: files_changed.clone(),
        diff_summary,
        db_migrations: detect_db_migrations(&files_changed),
        api_changes: detect_api_changes(&files_changed),
        labels,
        lint_result: None,
        audit_result: None,
        test_result: None,
    }
}

/// `capture_from_json`.
pub fn capture_from_json(path: &Path) -> Result<PRContext, String> {
    let raw = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
    let data: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    PRContext::from_json_value(&data)
}

/// `save_context`: escribe `model_dump_json(indent=2)` SIN newline final.
pub fn save_context(ctx: &PRContext, path: &Path) -> Result<PathBuf, String> {
    std::fs::write(path, ctx.to_pydantic_json()).map_err(|e| e.to_string())?;
    Ok(path.to_path_buf())
}

/// `enrich_with_pipeline`: copia inmutable, sólo pisa los provistos.
pub fn enrich_with_pipeline(
    ctx: &PRContext,
    lint_result: Option<&str>,
    audit_result: Option<&str>,
    test_result: Option<&str>,
) -> PRContext {
    let mut enriched = ctx.clone();
    if let Some(v) = lint_result {
        enriched.lint_result = Some(v.to_string());
    }
    if let Some(v) = audit_result {
        enriched.audit_result = Some(v.to_string());
    }
    if let Some(v) = test_result {
        enriched.test_result = Some(v.to_string());
    }
    enriched
}

// ── services/pr_service.py ─────────────────────────────────────────────────

/// Puerto de `PRService.store_pr_context` (la parte de docs entra P12A-4).
pub struct PRService<'a> {
    vault_path: PathBuf,
    episodic: Option<&'a mut dyn EpisodicSink>,
    context_metadata: std::collections::BTreeMap<String, serde_json::Value>,
}

impl<'a> PRService<'a> {
    pub fn new(vault_path: impl Into<PathBuf>, episodic: Option<&'a mut dyn EpisodicSink>) -> Self {
        Self {
            vault_path: vault_path.into(),
            episodic,
            context_metadata: Default::default(),
        }
    }

    pub fn with_context_metadata(
        mut self,
        meta: std::collections::BTreeMap<String, serde_json::Value>,
    ) -> Self {
        self.context_metadata = meta;
        self
    }

    #[allow(dead_code)]
    pub fn vault_path(&self) -> &Path {
        &self.vault_path
    }

    /// `store_pr_context`: enrich + resumen multilínea + add episódico.
    pub fn store_pr_context(
        &mut self,
        ctx: &PRContext,
        lint_result: Option<&str>,
        audit_result: Option<&str>,
        test_result: Option<&str>,
    ) -> Result<crate::episodic::MemoryEntry, String> {
        let ctx = enrich_with_pipeline(ctx, lint_result, audit_result, test_result);
        let sink = self
            .episodic
            .as_deref_mut()
            .ok_or_else(|| "episodic store no configurado".to_string())?;

        let summary = format!(
            "PR #{}: {} by {} ({} -> {})",
            ctx.pr_number, ctx.title, ctx.author, ctx.source_branch, ctx.target_branch
        );
        let mut content_parts = vec![summary];
        if !ctx.body.is_empty() {
            let truncated: String = ctx.body.chars().take(500).collect();
            content_parts.push(format!("\nDescription: {truncated}"));
        }
        if !ctx.diff_summary.is_empty() {
            content_parts.push(format!("\nDiff:\n{}", ctx.diff_summary));
        }
        let lint = ctx.lint_result.clone().unwrap_or_else(|| "n/a".into());
        let audit = ctx.audit_result.clone().unwrap_or_else(|| "n/a".into());
        let tests = ctx.test_result.clone().unwrap_or_else(|| "n/a".into());
        content_parts.push(format!("\nLint: {lint}"));
        content_parts.push(format!("\nAudit: {audit}"));
        content_parts.push(format!("\nTests: {tests}"));

        let mut tags = vec!["pr".to_string(), ctx.author.clone()];
        tags.extend(ctx.labels.iter().cloned());

        sink.add_memory(EpisodicMemoryRequest {
            content: content_parts.join("\n"),
            memory_type: "pr".to_string(),
            tags,
            files: ctx.files_changed.iter().take(20).cloned().collect(),
            extra_metadata: self.context_metadata.clone(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ctx_base() -> PRContext {
        PRContext {
            title: "Fix login bug".into(),
            author: "dev1".into(),
            source_branch: "fix/login".into(),
            commit_sha: "abc123".into(),
            ..Default::default()
        }
    }

    #[test]
    fn defaults_como_pydantic() {
        let ctx = ctx_base();
        assert_eq!(ctx.target_branch, "main");
        assert_eq!(ctx.pr_number, 0);
        assert_eq!(ctx.files_changed.len(), 0);
        assert_eq!(ctx.labels.len(), 0);
        assert_eq!(ctx.lint_result, None);
    }

    #[test]
    fn hu_references_conjunto() {
        let mut ctx = ctx_base();
        ctx.body =
            "This PR addresses HU-42 and also references HU-100. Also related to #200.".into();
        let refs = ctx.hu_references();
        assert!(refs.contains(&"HU-42".to_string()));
        assert!(refs.contains(&"HU-100".to_string()));
        assert!(refs.contains(&"HU-200".to_string()));
    }

    #[test]
    fn has_db_api_adr() {
        let mut ctx = ctx_base();
        ctx.files_changed = vec!["migrations/001_add_users.sql".into(), "src/app.js".into()];
        assert!(ctx.has_db_changes());
        ctx.files_changed = vec!["README.md".into()];
        assert!(!ctx.has_db_changes());

        ctx.files_changed = vec![
            "src/routes/users.js".into(),
            "src/controllers/users.js".into(),
        ];
        assert!(ctx.has_api_changes());
        ctx.files_changed = vec!["src/styles/main.css".into()];
        assert!(!ctx.has_api_changes());

        ctx.labels = vec!["adr".into(), "breaking".into()];
        assert!(ctx.has_adr_label());
        ctx.labels = vec!["bugfix".into()];
        assert!(!ctx.has_adr_label());
    }

    #[test]
    fn json_roundtrip_byte_parity_interno() {
        let ctx = ctx_base();
        let json = ctx.to_pydantic_json();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        let re = PRContext::from_json_value(&parsed).unwrap();
        assert_eq!(re, ctx);
        assert_eq!(re.to_pydantic_json(), json);
    }

    #[test]
    fn detectores_directos() {
        let files: Vec<String> = vec![
            "migrations/001.sql".into(),
            "src/app.js".into(),
            "schema.sql".into(),
        ];
        let migrations = detect_db_migrations(&files);
        assert!(migrations.contains(&"migrations/001.sql".to_string()));
        assert!(migrations.contains(&"schema.sql".to_string()));
        assert!(!migrations.contains(&"src/app.js".to_string()));

        let files: Vec<String> = vec![
            "src/routes/users.js".into(),
            "src/controllers/auth.js".into(),
            "README.md".into(),
        ];
        let api = detect_api_changes(&files);
        assert!(api.contains(&"src/routes/users.js".to_string()));
        assert!(api.contains(&"src/controllers/auth.js".to_string()));
        assert!(!api.contains(&"README.md".to_string()));
    }

    #[test]
    fn capture_manual_sin_repo_da_vacio() {
        let tmp = std::env::temp_dir().join(format!("pr_a_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let ctx = capture_manual_in(
            CaptureManualArgs {
                title: "Test PR".into(),
                author: "dev1".into(),
                branch: "test".into(),
                commit: "abc123".into(),
                body: "Fixed the refresh token issue".into(),
                ..Default::default()
            },
            Some(&tmp),
        );
        assert_eq!(ctx.title, "Test PR");
        assert_eq!(ctx.source_branch, "test");
        assert_eq!(ctx.body, "Fixed the refresh token issue");
        assert!(ctx.files_changed.is_empty());
        assert!(ctx.diff_summary.is_empty());
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn enrich_no_muta_original() {
        let ctx = ctx_base();
        let enriched = enrich_with_pipeline(
            &ctx,
            Some("pass"),
            Some("fail: 2 high vulnerabilities"),
            Some("pass"),
        );
        assert_eq!(enriched.lint_result.as_deref(), Some("pass"));
        assert!(enriched.audit_result.unwrap().contains("fail"));
        assert_eq!(enriched.test_result.as_deref(), Some("pass"));
        assert_eq!(ctx.lint_result, None);
    }

    /// Sink captor para el payload del servicio.
    #[derive(Default)]
    struct CaptorSink {
        requests: Vec<EpisodicMemoryRequest>,
    }

    impl EpisodicSink for CaptorSink {
        fn add_memory(
            &mut self,
            req: EpisodicMemoryRequest,
        ) -> Result<crate::episodic::MemoryEntry, String> {
            let entry = crate::episodic::MemoryEntry {
                id: "mem_pr00000".into(),
                content: req.content.clone(),
                memory_type: req.memory_type.clone(),
                tags: req.tags.clone(),
                files: req.files.clone(),
                timestamp: "2026-08-25T00:00:00+00:00".into(),
                metadata: Default::default(),
            };
            self.requests.push(req);
            Ok(entry)
        }
    }

    #[test]
    fn store_pr_context_payload() {
        let tmp = std::env::temp_dir().join(format!("pr_b_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let mut sink = CaptorSink::default();
        {
            let mut svc = PRService::new(&tmp, Some(&mut sink as &mut dyn EpisodicSink));
            let mut ctx = PRContext {
                pr_number: 42,
                title: "Fix login bug".into(),
                body: "refresh token".into(),
                author: "dev1".into(),
                source_branch: "fix/login".into(),
                commit_sha: "abc123def456".into(),
                diff_summary: " src/main.py | 2 +-\n 1 file changed".into(),
                files_changed: vec!["src/main.py".into()],
                labels: vec!["bugfix".into()],
                ..Default::default()
            };
            ctx.files_changed = (0..30).map(|i| format!("f{i}.py")).collect();
            svc.store_pr_context(&ctx, Some("pass"), None, Some("pass"))
                .unwrap();
        }
        assert_eq!(sink.requests.len(), 1);
        let r = &sink.requests[0];
        assert_eq!(r.memory_type, "pr");
        assert_eq!(r.tags, vec!["pr", "dev1", "bugfix"]);
        // files truncados a 20
        assert_eq!(r.files.len(), 20);
        assert!(r
            .content
            .starts_with("PR #42: Fix login bug by dev1 (fix/login -> main)"));
        assert!(r.content.contains("\nDescription: refresh token"));
        assert!(r.content.contains("\nDiff:\n src/main.py | 2 +-"));
        assert!(r.content.contains("\nLint: pass"));
        assert!(r.content.contains("\nAudit: n/a"));
        assert!(r.content.ends_with("\nTests: pass"));
        std::fs::remove_dir_all(&tmp).ok();
    }
}
