//! Puerto de `cortex.doctor` (P12B-4): checks nativos completos para todo lo
//! filesystem/config/git/gitignore/vault/enterprise, y stubs contractuales
//! (patrón P6/P9) para backends Python aún no porteños.
//!
//! Contrato de stubs (congelado; el oráculo normaliza por nombre):
//! `ok=false · severity=warn|fail según check · detail="backend no nativo
//! aún (<módulo python>)"`.

use std::path::{Path, PathBuf};

use cortex_app::doc_validator::DocValidator;
use cortex_enterprise::config::{describe_enterprise_topology, load_enterprise_config};
use cortex_workspace::runtime_context::{
    detect_git_branch, detect_git_repo_path, resolve_episodic_persist_dir, EpisodicNamespaceCfg,
};
use cortex_workspace::{
    git_policy, WorkspaceLayout, LEGACY_GITIGNORE_PATTERNS, NEW_LAYOUT_GITIGNORE_PATTERNS,
};

use crate::checks::{DoctorCheck, DoctorReport};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DoctorScope {
    Project,
    Enterprise,
    All,
}

/// Texto contractual de los stubs.
fn stub(name: &str, module: &str, severity: &'static str) -> DoctorCheck {
    DoctorCheck {
        name: name.to_string(),
        ok: false,
        severity: severity.to_string(),
        detail: format!("backend no nativo aún ({module})"),
    }
}

fn is_writable(path: &Path) -> bool {
    let probe = path.join(".doctor_write_probe");
    match std::fs::write(&probe, "x") {
        Ok(()) => {
            let _ = std::fs::remove_file(&probe);
            true
        }
        Err(_) => false,
    }
}

pub type EnterpriseErrorLike = cortex_enterprise::error::EnterpriseError;

/// `run_doctor`.
pub fn run_doctor(
    project_root: &Path,
    scope: DoctorScope,
) -> Result<DoctorReport, EnterpriseErrorLike> {
    run_doctor_inner(project_root, scope)
}

fn run_doctor_inner(
    project_root: &Path,
    scope: DoctorScope,
) -> Result<DoctorReport, EnterpriseErrorLike> {
    let root = crate::native::python_resolve(project_root);
    let layout = WorkspaceLayout::discover(&root);
    let is_new = layout.is_new_layout;

    let mut checks: Vec<DoctorCheck> = vec![
        DoctorCheck::new(
            "project_root",
            root.exists(),
            "fail",
            root.display().to_string(),
        ),
        DoctorCheck::new(
            "layout_mode",
            true,
            "info",
            format!(
                "{} (workspace_root={})",
                if is_new { "new" } else { "legacy" },
                layout.workspace_root.display()
            ),
        ),
    ];
    if !root.exists() {
        return Ok(DoctorReport {
            project_root: root,
            checks,
        });
    }

    // ── Config ──────────────────────────────────────────────────────
    let config_path = layout.config_path();
    checks.push(DoctorCheck::new(
        "config_yaml",
        config_path.exists(),
        "fail",
        config_path.display().to_string(),
    ));

    let mut raw_config: serde_yaml::Value = serde_yaml::Value::Mapping(Default::default());
    if config_path.exists() {
        let text = std::fs::read_to_string(&config_path)?;
        match serde_yaml::from_str::<serde_yaml::Value>(&text) {
            Ok(v @ serde_yaml::Value::Mapping(_)) => raw_config = v,
            _ => raw_config = serde_yaml::Value::Mapping(Default::default()),
        }
        match serde_json::to_value(yaml_to_json(&raw_config))
            .map_err(|e| EnterpriseErrorLike::Validation(e.to_string()))
            .and_then(|j| {
                serde_json::from_value::<cortex_config::CortexConfig>(j)
                    .map_err(|e| EnterpriseErrorLike::Validation(e.to_string()))
                    .or(Err(EnterpriseErrorLike::Validation("invalid".into())))
            }) {
            Ok(_) => checks.push(DoctorCheck::new(
                "config_validation",
                true,
                "info",
                format!(
                    "{} is valid",
                    config_path.file_name().unwrap_or_default().display()
                ),
            )),
            Err(e) => checks.push(DoctorCheck::new(
                "config_validation",
                false,
                "fail",
                e.to_string(),
            )),
        }
    }

    // ── Vault ───────────────────────────────────────────────────────
    let vault_path = layout.vault_path();
    checks.push(DoctorCheck::new(
        "vault_dir",
        vault_path.exists(),
        "fail",
        vault_path.display().to_string(),
    ));

    // ── Episodic memory ────────────────────────────────────────────
    let episodic_cfg_str = |key: &str, default: &'static str| -> String {
        raw_config
            .get("episodic")
            .and_then(|m| m.get(key))
            .map(|v| match v {
                serde_yaml::Value::String(s) => s.clone(),
                other => serde_yaml::to_string(other)
                    .unwrap_or_default()
                    .trim()
                    .to_string(),
            })
            .unwrap_or_else(|| default.to_string())
    };
    let runtime_persist_dir = if config_path.exists() {
        resolve_episodic_persist_dir(
            &layout.workspace_root,
            &EpisodicNamespaceCfg::new(
                &episodic_cfg_str("persist_dir", "memory"),
                &episodic_cfg_str("namespace_mode", "project"),
                &episodic_cfg_str("namespace_value", ""),
            ),
        )
    } else {
        layout.episodic_memory_path().join("chroma")
    };
    let is_ci = std::env::var("GITHUB_ACTIONS").as_deref() == Ok("true");
    checks.push(DoctorCheck::new(
        "episodic_store",
        runtime_persist_dir.exists(),
        if is_ci { "warn" } else { "fail" },
        runtime_persist_dir.display().to_string(),
    ));

    // ── Cortex workspace ──────────────────────────────────────────
    checks.push(DoctorCheck::new(
        "cortex_workspace",
        layout.workspace_root.exists(),
        "warn",
        layout.workspace_root.display().to_string(),
    ));
    checks.push(DoctorCheck::new(
        "agent_guidelines",
        layout.agent_guidelines_path().exists(),
        "warn",
        layout.agent_guidelines_path().display().to_string(),
    ));

    // ── Workspace version ─────────────────────────────────────────
    let ws_yaml = layout.workspace_yaml_path();
    if ws_yaml.exists() {
        match std::fs::read_to_string(&ws_yaml)
            .ok()
            .and_then(|t| serde_yaml::from_str::<serde_yaml::Value>(&t).ok())
        {
            Some(data) => {
                let ver = data
                    .get("layout_version")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(1);
                checks.push(DoctorCheck::new(
                    "workspace_layout_version",
                    true,
                    "info",
                    format!("layout_version={ver}"),
                ));
            }
            None => checks.push(DoctorCheck::new(
                "workspace_layout_version",
                false,
                "warn",
                ws_yaml.display().to_string(),
            )),
        }
    } else {
        checks.push(DoctorCheck::new(
            "workspace_yaml",
            false,
            if is_new { "warn" } else { "info" },
            format!("Missing: {}", ws_yaml.display()),
        ));
    }

    // ── Git ────────────────────────────────────────────────────────
    let repo_root = detect_git_repo_path(&root);
    let git_available = repo_root != root || root.join(".git").exists();
    checks.push(DoctorCheck::new(
        "git_repository",
        git_available,
        "warn",
        repo_root.display().to_string(),
    ));
    let branch = detect_git_branch(&root);
    checks.push(DoctorCheck::new(
        "git_branch",
        branch != "no-git-branch",
        "warn",
        branch,
    ));

    // ── Gitignore (layout-aware) ──────────────────────────────────
    let patterns = if is_new {
        NEW_LAYOUT_GITIGNORE_PATTERNS
    } else {
        LEGACY_GITIGNORE_PATTERNS
    };
    for pattern in patterns {
        let severity: &'static str = if pattern.contains("memory") || pattern.ends_with(".chroma/")
        {
            "fail"
        } else {
            "warn"
        };
        checks.push(DoctorCheck::new(
            format!("gitignore:{pattern}"),
            git_policy::gitignore_contains(&root, pattern),
            severity,
            *pattern,
        ));
    }

    // ── WebGraph (stub contractual) ───────────────────────────────
    checks.push(stub(
        "webgraph_dependencies",
        "cortex.webgraph.setup",
        "warn",
    ));

    // ── Vault validation ──────────────────────────────────────────
    if vault_path.exists() {
        checks.extend(validate_vault(&vault_path, "vault"));
    }

    // ── Sessions ──────────────────────────────────────────────────
    checks.extend(validate_sessions(&layout));

    // ── Autopilot policy (stub; real en P12B-5) ───────────────────
    checks.push(stub(
        "autopilot_policy",
        "cortex.autopilot.policies",
        "warn",
    ));

    // ── Session hooks (stub) ──────────────────────────────────────
    checks.push(stub(
        "session_hooks_installed",
        "cortex.session.hooks",
        "warn",
    ));

    // ── Pluggable Middle health ───────────────────────────────────
    checks.extend(pluggable_middle_health(&layout));

    // ── Enterprise ────────────────────────────────────────────────
    if matches!(scope, DoctorScope::Enterprise | DoctorScope::All) {
        checks.extend(validate_enterprise(
            &root,
            &layout,
            scope == DoctorScope::Enterprise,
        )?);
    }

    Ok(DoctorReport {
        project_root: root,
        checks,
    })
}

/// `_validate_vault` / `_validate_enterprise_vault` (compartidas).
fn validate_vault(vault_path: &Path, family: &str) -> Vec<DoctorCheck> {
    let mut md_files = Vec::new();
    collect_md(vault_path, &mut md_files);
    md_files.sort();
    if md_files.is_empty() {
        return vec![DoctorCheck::new(
            format!("{family}_markdown"),
            false,
            "warn",
            format!(
                "No markdown files found under {}/",
                if family == "vault" {
                    "vault"
                } else {
                    "vault-enterprise"
                }
            ),
        )];
    }

    let validator = DocValidator::new(vault_path);
    let results = validator.validate_batch(&md_files);
    let error_count = results.iter().map(|r| r.errors().len()).sum::<usize>();
    let warning_count = results.iter().map(|r| r.warnings().len()).sum::<usize>();
    vec![
        DoctorCheck::new(
            format!("{family}_validation_errors"),
            error_count == 0,
            "fail",
            format!(
                "{error_count} error(s) across {} markdown file(s)",
                md_files.len()
            ),
        ),
        DoctorCheck::new(
            format!("{family}_validation_warnings"),
            warning_count == 0,
            "warn",
            format!(
                "{warning_count} warning(s) across {} markdown file(s)",
                md_files.len()
            ),
        ),
    ]
}

/// `_validate_sessions`: existencia/writability nativos + stub profundo.
fn validate_sessions(layout: &WorkspaceLayout) -> Vec<DoctorCheck> {
    let sessions_dir = layout.sessions_dir();
    if !sessions_dir.exists() {
        return vec![DoctorCheck::new(
            "sessions_dir",
            false,
            "warn",
            format!(
                "Missing: {} — run `cortex setup agent`.",
                sessions_dir.display()
            ),
        )];
    }
    let writable = is_writable(&sessions_dir);
    let mut checks = vec![DoctorCheck::new(
        "sessions_dir",
        writable,
        if !writable { "fail" } else { "info" },
        sessions_dir.display().to_string(),
    )];
    checks.push(stub(
        "sessions_active_pointer",
        "cortex.session.storage",
        "warn",
    ));
    checks.push(stub("sessions_parsed", "cortex.session.storage", "warn"));
    checks
}

/// `_validate_pluggable_middle_health`: portables + stubs.
fn pluggable_middle_health(layout: &WorkspaceLayout) -> Vec<DoctorCheck> {
    let mut checks = vec![DoctorCheck::new(
        "pm_workspace_layout_v2",
        layout.is_new_layout,
        if layout.is_new_layout { "info" } else { "warn" },
        if layout.is_new_layout {
            "layout v2 active"
        } else {
            "running on legacy layout"
        },
    )];

    checks.push(stub("pm_documenter_module", "cortex.documenter", "fail"));
    checks.push(stub(
        "pm_documenter_interactive",
        "cortex.documenter.interactive",
        "warn",
    ));

    // documenter.default_mode — lectura YAML portable.
    let config_path = layout.config_path();
    let mode = std::fs::read_to_string(&config_path)
        .ok()
        .and_then(|t| serde_yaml::from_str::<serde_yaml::Value>(&t).ok())
        .and_then(|v| {
            v.get("documenter")
                .and_then(|d| d.get("default_mode"))
                .and_then(|m| match m {
                    serde_yaml::Value::String(s) => Some(s.clone()),
                    other => serde_yaml::to_string(other)
                        .ok()
                        .map(|s| s.trim().to_string()),
                })
        })
        .unwrap_or_else(|| "auto".to_string());
    if mode == "auto" || mode == "interactive" {
        checks.push(DoctorCheck::new(
            "pm_documenter_default_mode",
            true,
            "info",
            format!("documenter.default_mode = {mode}"),
        ));
    } else {
        checks.push(DoctorCheck::new(
            "pm_documenter_default_mode",
            false,
            "warn",
            format!(
                "documenter.default_mode '{mode}' is not 'auto' or 'interactive'; the CLI will treat anything else as 'auto'."
            ),
        ));
    }

    checks.push(stub(
        "pm_verification_runner",
        "cortex.session.verification",
        "warn",
    ));
    checks.push(stub("pm_mcp_tools_registered", "cortex.mcp.server", "warn"));

    // pm_git_available — informativo, no fallo.
    if cortex_workspace::runtime_context::detect_git_repo_path(&layout.repo_root)
        != layout.repo_root
        || layout.repo_root.join(".git").exists()
    {
        checks.push(DoctorCheck::new(
            "pm_git_available",
            true,
            "info",
            "git repository detected — full documenter fidelity",
        ));
    } else {
        checks.push(DoctorCheck::new(
            "pm_git_available",
            false,
            "info",
            "no git repository at workspace root — sessions will open in gitless mode (documenter relies on checkpoints only)",
        ));
    }
    checks
}

/// `_validate_enterprise` completa (nativa vía cortex-enterprise).
fn validate_enterprise(
    project_root: &Path,
    layout: &WorkspaceLayout,
    required: bool,
) -> Result<Vec<DoctorCheck>, EnterpriseErrorLike> {
    use cortex_enterprise::models::RetrievalScope;

    let mut checks = Vec::new();
    let org_path = layout.org_config_path();
    checks.push(DoctorCheck::new(
        "enterprise_config",
        org_path.exists(),
        if required { "fail" } else { "warn" },
        org_path.display().to_string(),
    ));
    if !org_path.exists() {
        return Ok(checks);
    }

    let config = match load_enterprise_config(project_root, true, None, Some(layout))? {
        Some(c) => c,
        None => {
            checks.push(DoctorCheck::new(
                "enterprise_config_validation",
                false,
                "fail",
                "missing".to_string(),
            ));
            return Ok(checks);
        }
    };

    checks.push(DoctorCheck::new(
        "enterprise_config_validation",
        true,
        "info",
        "Enterprise org config is valid",
    ));
    checks.push(DoctorCheck::new(
        "enterprise_topology",
        true,
        "info",
        describe_enterprise_topology(Some(&config), Some(project_root), Some(layout)),
    ));

    let workspace_root = layout.workspace_root.clone();
    let enterprise_vault =
        config.resolve_enterprise_vault_path(project_root, Some(&workspace_root));
    if let Some(vault) = &enterprise_vault {
        checks.push(DoctorCheck::new(
            "enterprise_vault_dir",
            vault.exists(),
            if required { "fail" } else { "warn" },
            vault.display().to_string(),
        ));
        if vault.exists() {
            checks.extend(validate_vault(vault, "enterprise_vault"));
            checks.extend(validate_enterprise_promotion(&config, vault));
        }
    }

    let enterprise_memory =
        config.resolve_enterprise_memory_path(project_root, Some(&workspace_root));
    if let Some(memory) = &enterprise_memory {
        checks.push(DoctorCheck::new(
            "enterprise_memory_dir",
            memory.exists(),
            "warn",
            memory.display().to_string(),
        ));
    }

    // Alineación branch isolation (config.yaml vs org.yaml).
    let namespace_mode = {
        // raw_config no llega aquí; Python lo lee de config.yaml global.
        // Releemos config.yaml localmente (misma semántica).
        let cfg_path = layout.config_path();
        std::fs::read_to_string(&cfg_path)
            .ok()
            .and_then(|t| serde_yaml::from_str::<serde_yaml::Value>(&t).ok())
            .and_then(|v| {
                v.get("episodic")
                    .and_then(|e| e.get("namespace_mode"))
                    .and_then(|m| match m {
                        serde_yaml::Value::String(s) => Some(s.clone()),
                        other => serde_yaml::to_string(other)
                            .ok()
                            .map(|s| s.trim().to_string()),
                    })
            })
            .unwrap_or_else(|| "project".to_string())
            .trim()
            .to_lowercase()
    };
    let branch_expected = namespace_mode == "branch";
    let branch_matches = branch_expected == config.memory.branch_isolation_enabled;
    checks.push(DoctorCheck::new(
        "enterprise_branch_isolation_alignment",
        branch_matches,
        "warn",
        format!(
            "config.yaml namespace_mode={namespace_mode}, org.yaml branch_isolation_enabled={}",
            pybool(config.memory.branch_isolation_enabled)
        ),
    ));

    let expected_scope = if config.memory.enterprise_semantic_enabled {
        RetrievalScope::All
    } else {
        RetrievalScope::Local
    };
    let scope_matches = config.memory.retrieval_default_scope == expected_scope
        || config.memory.retrieval_default_scope == RetrievalScope::Local;
    checks.push(DoctorCheck::new(
        "enterprise_retrieval_scope",
        scope_matches,
        "warn",
        format!(
            "default_scope={}, enterprise_semantic_enabled={}",
            config.memory.retrieval_default_scope,
            pybool(config.memory.enterprise_semantic_enabled)
        ),
    ));

    Ok(checks)
}

fn validate_enterprise_promotion(
    config: &cortex_enterprise::models::EnterpriseOrgConfig,
    enterprise_vault: &Path,
) -> Vec<DoctorCheck> {
    let mut checks = Vec::new();
    if !config.promotion.enabled {
        return checks;
    }

    let allowed = &config.promotion.allowed_doc_types;
    checks.push(DoctorCheck::new(
        "enterprise_promotion_allowed_doc_types",
        !allowed.is_empty(),
        "fail",
        "promotion.allowed_doc_types must be non-empty when promotion is enabled",
    ));

    let promo_dir = enterprise_vault.join(".cortex").join("promotion");
    let (ok, detail) = match std::fs::create_dir_all(&promo_dir) {
        Ok(()) => (true, promo_dir.display().to_string()),
        Err(exc) => (false, format!("{} ({exc})", promo_dir.display())),
    };
    checks.push(DoctorCheck::new(
        "enterprise_promotion_dir",
        ok,
        "fail",
        detail,
    ));

    let records = promo_dir.join("records.jsonl");
    checks.push(DoctorCheck::new(
        "enterprise_promotion_records_presence",
        records.exists(),
        "warn",
        records.display().to_string(),
    ));
    checks
}

fn yaml_to_json(value: &serde_yaml::Value) -> serde_json::Value {
    match value {
        serde_yaml::Value::Null => serde_json::Value::Null,
        serde_yaml::Value::Bool(b) => serde_json::Value::Bool(*b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                serde_json::json!(i)
            } else if let Some(u) = n.as_u64() {
                serde_json::json!(u)
            } else {
                serde_json::json!(n.as_f64().unwrap_or(0.0))
            }
        }
        serde_yaml::Value::String(s) => serde_json::json!(s),
        serde_yaml::Value::Sequence(items) => {
            serde_json::Value::Array(items.iter().map(yaml_to_json).collect())
        }
        serde_yaml::Value::Mapping(map) => {
            let mut out = serde_json::Map::new();
            for (k, v) in map {
                let key = match k {
                    serde_yaml::Value::String(s) => s.clone(),
                    other => serde_yaml::to_string(other)
                        .unwrap_or_default()
                        .trim()
                        .to_string(),
                };
                out.insert(key, yaml_to_json(v));
            }
            serde_json::Value::Object(out)
        }
        serde_yaml::Value::Tagged(t) => yaml_to_json(&t.value),
    }
}

/// str(bool) de Python: True/False capitalizados.
fn pybool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

fn collect_md(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_md(&path, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(path);
        }
    }
}
