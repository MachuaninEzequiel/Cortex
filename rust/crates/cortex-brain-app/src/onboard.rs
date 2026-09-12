//! Instalación visual de Cortex desde Brain: preview/apply in-process.
//!
//! No llama al CLI (`cortex-cli` hace `process::exit`). Usa `cortex-setup`.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

use cortex_setup::detector::ProjectContext;
use cortex_setup::ide::{adapters::all_adapters, prompts::build_all_prompts, IdeCtx};
use cortex_setup::setup_templates as tpl;
use cortex_setup::skills_bundle;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SetupAction {
    Agent,
    Full,
    Pipeline,
    Enterprise,
    Composed,
    Ide,
    IdeRemove,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlannedFile {
    pub path: String,
    pub op: String,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApplyResult {
    pub ok: bool,
    pub files: Vec<String>,
    pub log: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IdeStatus {
    pub name: String,
    pub display_name: String,
    pub tier: String,
    pub uninstall_supported: bool,
    pub injected: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SetupTarget {
    pub path: String,
    pub exists: bool,
    pub has_cortex: bool,
    pub has_org_yaml: bool,
    pub doctor_healthy: Option<bool>,
    pub doctor_checks: usize,
    pub ides: Vec<IdeStatus>,
}

pub fn preview_setup(
    root: &Path,
    action: SetupAction,
    ide: Option<&str>,
    _preset: Option<&str>,
) -> Result<Vec<PlannedFile>, String> {
    let root = resolve_root(root)?;
    if action == SetupAction::Ide || action == SetupAction::IdeRemove {
        let name = ide.ok_or_else(|| "Falta el IDE".to_string())?;
        if !all_adapters().iter().any(|a| a.name() == name) {
            return Err(format!("IDE desconocido: {name}"));
        }
    }
    Ok(plan_files(&root, action, ide))
}

pub fn apply_setup(
    root: &Path,
    action: SetupAction,
    ide: Option<&str>,
    preset: Option<&str>,
) -> Result<ApplyResult, String> {
    let root = resolve_root(root)?;
    match action {
        SetupAction::Agent => apply_agent(&root),
        SetupAction::Pipeline => apply_pipeline(&root),
        SetupAction::Full => {
            let mut r = apply_agent(&root)?;
            let p = apply_pipeline(&root)?;
            r.files.extend(p.files);
            r.log.extend(p.log);
            let wg = write_rel(
                &root,
                ".cortex/webgraph/workspace.yaml",
                "projects:\n  - path: .\n",
            )?;
            r.files.push(wg);
            r.log.push("webgraph".into());
            Ok(r)
        }
        SetupAction::Enterprise => apply_enterprise(&root, preset.unwrap_or("small-company")),
        SetupAction::Composed => apply_composed(&root),
        SetupAction::Ide => apply_ide(&root, ide),
        SetupAction::IdeRemove => apply_ide_remove(&root, ide),
    }
}

pub fn inspect_setup_target(root: &Path) -> Result<SetupTarget, String> {
    let root = resolve_root(root)?;
    let has_cortex = root.join(".cortex").is_dir();
    let has_org_yaml = root.join(".cortex").join("org.yaml").is_file();
    let (doctor_healthy, doctor_checks) = if has_cortex {
        let doc = crate::graph::inspect_doctor_health(&root);
        (Some(doc.is_healthy), doc.checks.len())
    } else {
        (None, 0)
    };
    Ok(SetupTarget {
        path: root.to_string_lossy().into_owned(),
        exists: true,
        has_cortex,
        has_org_yaml,
        doctor_healthy,
        doctor_checks,
        ides: list_ides_for(&root),
    })
}

pub fn list_ides() -> Vec<IdeStatus> {
    list_ides_for(Path::new("/"))
}

fn ide_tier(name: &str) -> &'static str {
    match name {
        "claude_code" | "opencode" | "pi" | "codex" => "target",
        "zed" | "antigravity" | "hermes" => "experimental",
        _ => "community",
    }
}

fn user_home() -> Option<PathBuf> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
}

fn list_ides_for(root: &Path) -> Vec<IdeStatus> {
    let home = user_home().unwrap_or_else(|| root.to_path_buf());
    let ctx = IdeCtx {
        project_root: root,
        home: &home,
        now: chrono::Utc::now(),
    };
    all_adapters()
        .iter()
        .map(|a| {
            let injected = a.config_paths(&ctx).iter().any(|(_, p)| p.exists());
            IdeStatus {
                name: a.name().to_string(),
                display_name: a.display_name().to_string(),
                tier: ide_tier(a.name()).to_string(),
                uninstall_supported: true,
                injected,
            }
        })
        .collect()
}

fn agent_rels() -> &'static [&'static str] {
    &[
        ".cortex/workspace.yaml",
        ".cortex/config.yaml",
        ".cortex/org.yaml",
        ".cortex/vault/architecture.md",
        ".cortex/vault/context.md",
        ".cortex/vault/decisions/README.md",
        ".cortex/vault/runbooks/README.md",
        ".cortex/memory",
    ]
}

fn pipeline_rels() -> &'static [&'static str] {
    &[
        ".github/workflows/ci-feature.yml",
        ".github/workflows/ci-pull-request.yml",
        ".github/workflows/cd-deploy.yml",
        "scripts/devsecdocops.sh",
    ]
}

fn plan_entry(root: &Path, rel: &str, note: &str) -> PlannedFile {
    let full = root.join(rel);
    PlannedFile {
        path: rel.replace('\\', "/"),
        op: if full.exists() {
            "update".into()
        } else {
            "create".into()
        },
        note: note.into(),
    }
}

fn plan_files(root: &Path, action: SetupAction, ide: Option<&str>) -> Vec<PlannedFile> {
    let mut out = Vec::new();
    match action {
        SetupAction::Agent => {
            for rel in agent_rels() {
                out.push(plan_entry(root, rel, "setup agent"));
            }
        }
        SetupAction::Pipeline => {
            for rel in pipeline_rels() {
                out.push(plan_entry(root, rel, "setup pipeline"));
            }
        }
        SetupAction::Full => {
            for rel in agent_rels() {
                out.push(plan_entry(root, rel, "setup full"));
            }
            for rel in pipeline_rels() {
                out.push(plan_entry(root, rel, "setup full"));
            }
            out.push(plan_entry(
                root,
                ".cortex/webgraph/workspace.yaml",
                "webgraph",
            ));
        }
        SetupAction::Enterprise => {
            out.push(plan_entry(root, ".cortex/org.yaml", "enterprise org.yaml"));
        }
        SetupAction::Composed => {
            out.push(plan_entry(
                root,
                ".cortex/skills/composed",
                "familia composed",
            ));
            out.push(plan_entry(root, ".cortex/skills", "tríada thin+craft"));
            out.push(plan_entry(root, "AGENTS.md", "bloque Agent skills"));
        }
        SetupAction::Ide | SetupAction::IdeRemove => {
            if let Some(name) = ide {
                let adapters = all_adapters();
                if let Some(adapter) = adapters.iter().find(|a| a.name() == name) {
                    let home = user_home().unwrap_or_else(|| root.to_path_buf());
                    let ctx = IdeCtx {
                        project_root: root,
                        home: &home,
                        now: chrono::Utc::now(),
                    };
                    for (key, path) in adapter.config_paths(&ctx) {
                        let rel = path
                            .strip_prefix(root)
                            .map(|p| p.display().to_string())
                            .unwrap_or_else(|_| path.display().to_string());
                        out.push(plan_entry(root, &rel, &format!("IDE {key}")));
                    }
                }
            }
        }
    }
    out
}

fn write_rel(root: &Path, rel: &str, data: impl AsRef<[u8]>) -> Result<String, String> {
    let p = root.join(rel);
    if let Some(d) = p.parent() {
        std::fs::create_dir_all(d).map_err(|e| format!("No pude crear {}: {e}", d.display()))?;
    }
    std::fs::write(&p, data).map_err(|e| format!("No pude escribir {rel}: {e}"))?;
    Ok(rel.replace('\\', "/"))
}

fn apply_agent(root: &Path) -> Result<ApplyResult, String> {
    let ctx = ProjectContext::detect(root);
    let mut files = Vec::new();
    files.push(write_rel(
        root,
        ".cortex/workspace.yaml",
        tpl::render_workspace_yaml(),
    )?);
    files.push(write_rel(
        root,
        ".cortex/config.yaml",
        tpl::render_config_yaml(&ctx),
    )?);
    files.push(write_rel(
        root,
        ".cortex/org.yaml",
        tpl::render_org_yaml(&ctx.stack.project_name, "small-company", true, false)?,
    )?);
    files.push(write_rel(
        root,
        ".cortex/vault/architecture.md",
        tpl::render_architecture_md(&ctx),
    )?);
    files.push(write_rel(
        root,
        ".cortex/vault/context.md",
        tpl::render_context_md(&ctx),
    )?);
    files.push(write_rel(
        root,
        ".cortex/vault/decisions/README.md",
        tpl::render_decisions_md(),
    )?);
    files.push(write_rel(
        root,
        ".cortex/vault/runbooks/README.md",
        tpl::render_runbooks_md(&ctx),
    )?);
    std::fs::create_dir_all(root.join(".cortex/memory"))
        .map_err(|e| format!("No pude crear .cortex/memory: {e}"))?;
    files.push(".cortex/memory".into());
    Ok(ApplyResult {
        ok: true,
        log: vec!["setup agent complete".into()],
        files,
    })
}

fn apply_pipeline(root: &Path) -> Result<ApplyResult, String> {
    let ctx = ProjectContext::detect(root);
    let mut files = Vec::new();
    files.push(write_rel(
        root,
        ".github/workflows/ci-feature.yml",
        tpl::render_ci_feature(&ctx),
    )?);
    files.push(write_rel(
        root,
        ".github/workflows/ci-pull-request.yml",
        tpl::render_ci_pull_request(&ctx),
    )?);
    files.push(write_rel(
        root,
        ".github/workflows/cd-deploy.yml",
        tpl::render_cd_deploy(&ctx),
    )?);
    files.push(write_rel(
        root,
        "scripts/devsecdocops.sh",
        cortex_setup::setup_templates_gen::DEVSECDOCSOPS_SCRIPT,
    )?);
    Ok(ApplyResult {
        ok: true,
        log: vec!["setup pipeline complete".into()],
        files,
    })
}

fn apply_enterprise(root: &Path, preset: &str) -> Result<ApplyResult, String> {
    let ctx = ProjectContext::detect(root);
    let yaml = tpl::render_org_yaml(&ctx.stack.project_name, preset, true, false)?;
    let file = write_rel(root, ".cortex/org.yaml", yaml)?;
    Ok(ApplyResult {
        ok: true,
        files: vec![file],
        log: vec![format!("enterprise preset {preset}")],
    })
}

fn apply_composed(root: &Path) -> Result<ApplyResult, String> {
    let mut files = Vec::new();
    let fam = skills_bundle::install_composed_family(&root.join(".cortex/skills/composed"));
    files.extend(
        fam.into_iter()
            .map(|n| format!(".cortex/skills/composed/{n}")),
    );
    let tri = skills_bundle::install_triad_skills(&root.join(".cortex/skills"));
    files.extend(tri.into_iter().map(|n| format!(".cortex/skills/{n}")));
    let block = skills_bundle::agent_skills_block();
    let agents = root.join("AGENTS.md");
    if agents.exists() {
        let content = std::fs::read_to_string(&agents).map_err(|e| e.to_string())?;
        let updated = cortex_setup::ide::base::upsert_marker_block_with(
            &content,
            &block,
            skills_bundle::COMPOSED_MARKER_OPEN,
            skills_bundle::COMPOSED_MARKER_CLOSE,
        );
        std::fs::write(&agents, updated).map_err(|e| e.to_string())?;
    } else {
        write_rel(root, "AGENTS.md", format!("{block}\n"))?;
    }
    files.push("AGENTS.md".into());
    Ok(ApplyResult {
        ok: true,
        files,
        log: vec!["setup composed complete".into()],
    })
}

/// Ruta del `cortex-cli` que Brain debe inyectar en el MCP: sidecar del
/// bundle, sibling de este binario, o el nombre pelado.
pub fn resolve_bundled_cortex_cli() -> PathBuf {
    if let Ok(p) = std::env::var("CORTEX_CLI_BIN") {
        let pb = PathBuf::from(p.trim());
        if pb.is_file() {
            return pb;
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let direct = dir.join("cortex-cli");
            if direct.is_file() {
                return direct;
            }
            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let s = entry.file_name().to_string_lossy().into_owned();
                    if s == "cortex-cli" || s == "cortex-cli.exe" || s.starts_with("cortex-cli-") {
                        return entry.path();
                    }
                }
            }
        }
    }
    PathBuf::from("cortex-cli")
}

fn with_resolved_cli_bin<T>(f: impl FnOnce() -> T) -> T {
    let cli = resolve_bundled_cortex_cli();
    if !cli.is_absolute() {
        return f();
    }
    let prev = std::env::var("CORTEX_CLI_BIN").ok();
    std::env::set_var("CORTEX_CLI_BIN", &cli);
    let out = f();
    match prev {
        Some(p) => std::env::set_var("CORTEX_CLI_BIN", p),
        None => std::env::remove_var("CORTEX_CLI_BIN"),
    }
    out
}

fn apply_ide(root: &Path, ide: Option<&str>) -> Result<ApplyResult, String> {
    with_resolved_cli_bin(|| {
        let ide = ide.ok_or_else(|| "Falta el IDE a instalar".to_string())?;
        let adapters = all_adapters();
        let adapter = adapters
            .iter()
            .find(|a| a.name() == ide)
            .ok_or_else(|| format!("IDE desconocido: {ide}"))?;
        let home = user_home().unwrap_or_else(|| root.to_path_buf());
        let ctx = IdeCtx {
            project_root: root,
            home: &home,
            now: chrono::Utc::now(),
        };
        let prompts = build_all_prompts(&ctx);
        let mut files = adapter.inject_profiles(&ctx, &prompts)?;
        files.extend(adapter.inject_mcp(&ctx)?);
        let mut log = vec![format!("IDE {} listo", adapter.display_name())];
        let cli = resolve_bundled_cortex_cli();
        if cli.is_absolute() {
            log.push(format!("MCP command: {}", cli.display()));
        }
        Ok(ApplyResult {
            ok: true,
            log,
            files,
        })
    })
}

fn apply_ide_remove(root: &Path, ide: Option<&str>) -> Result<ApplyResult, String> {
    let ide = ide.ok_or_else(|| "Falta el IDE a quitar".to_string())?;
    let adapters = all_adapters();
    let adapter = adapters
        .iter()
        .find(|a| a.name() == ide)
        .ok_or_else(|| format!("IDE desconocido: {ide}"))?;
    let home = user_home().unwrap_or_else(|| root.to_path_buf());
    let ctx = IdeCtx {
        project_root: root,
        home: &home,
        now: chrono::Utc::now(),
    };
    let files = adapter.uninstall(&ctx);
    Ok(ApplyResult {
        ok: true,
        log: vec![format!("IDE {} quitado", adapter.display_name())],
        files,
    })
}

/// Convierte lo que devuelve el diálogo nativo (path o `file://`) a PathBuf.
pub fn normalize_picked_path(raw: &str) -> Result<PathBuf, String> {
    let raw = raw.trim();
    if raw.is_empty() {
        return Err("Carpeta vacía".into());
    }
    if let Some(rest) = raw.strip_prefix("file://") {
        let rest = percent_decode_unreserved(rest);
        // file:///C:/Users/...  o  file:///home/...
        if rest.starts_with('/') {
            if cfg!(windows) && rest.len() >= 3 && rest.as_bytes().get(2) == Some(&b':') {
                // "/C:/Users" → "C:/Users"
                return Ok(PathBuf::from(&rest[1..]));
            }
            return Ok(PathBuf::from(rest));
        }
        return Ok(PathBuf::from(rest));
    }
    Ok(PathBuf::from(raw))
}

fn percent_decode_unreserved(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let bytes = s.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let (Ok(h), Ok(l)) = (
                u8::from_str_radix(std::str::from_utf8(&bytes[i + 1..i + 2]).unwrap_or(""), 16),
                u8::from_str_radix(std::str::from_utf8(&bytes[i + 2..i + 3]).unwrap_or(""), 16),
            ) {
                out.push(char::from((h << 4) | l));
                i += 3;
                continue;
            }
        }
        out.push(bytes[i] as char);
        i += 1;
    }
    out
}

fn resolve_root(root: &Path) -> Result<PathBuf, String> {
    if !root.is_absolute() {
        return Err("La carpeta debe ser una ruta absoluta".into());
    }
    if !root.is_dir() {
        return Err(format!("No existe la carpeta {}", root.display()));
    }
    Ok(root.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn normalize_picked_path_acepta_file_url_unix() {
        let p = normalize_picked_path("file:///tmp/proyecto").unwrap();
        assert_eq!(p, PathBuf::from("/tmp/proyecto"));
    }

    #[test]
    fn normalize_picked_path_rechaza_vacio() {
        assert!(normalize_picked_path("   ").is_err());
    }

    #[test]
    fn inspect_con_file_url_de_carpeta_real() {
        let tmp = TempDir::new().unwrap();
        let url = format!("file://{}", tmp.path().display());
        let path = normalize_picked_path(&url).unwrap();
        let snap = inspect_setup_target(&path).expect("inspect");
        assert!(snap.exists);
        assert!(!snap.has_cortex);
    }

    #[test]
    fn preview_agent_lista_archivos_y_no_escribe() {
        let tmp = TempDir::new().unwrap();
        let plan =
            preview_setup(tmp.path(), SetupAction::Agent, None, None).expect("preview agent");
        assert!(
            plan.iter().any(|p| p.path.contains("org.yaml")),
            "plan: {plan:?}"
        );
        assert!(
            plan.iter().any(|p| p.path.contains("config.yaml")),
            "plan: {plan:?}"
        );
        assert!(!tmp.path().join(".cortex").exists(), "preview no escribe");
    }

    #[test]
    fn apply_agent_crea_y_es_idempotente() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        let first = apply_setup(root, SetupAction::Agent, None, None).expect("apply 1");
        assert!(first.ok);
        assert!(root.join(".cortex/config.yaml").is_file());
        assert!(root.join(".cortex/org.yaml").is_file());
        assert!(root.join(".cortex/vault/architecture.md").is_file());
        assert!(root.join(".cortex/memory").is_dir());

        let second = apply_setup(root, SetupAction::Agent, None, None).expect("apply 2");
        assert!(second.ok);
        assert!(root.join(".cortex/config.yaml").is_file());
    }

    #[test]
    fn apply_full_incluye_pipeline_y_webgraph() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        apply_setup(root, SetupAction::Full, None, None).expect("full");
        assert!(root.join(".github/workflows/ci-feature.yml").is_file());
        assert!(root.join(".cortex/webgraph/workspace.yaml").is_file());
    }

    #[test]
    fn apply_enterprise_escribe_org_yaml() {
        let tmp = TempDir::new().unwrap();
        apply_setup(
            tmp.path(),
            SetupAction::Enterprise,
            None,
            Some("small-company"),
        )
        .expect("enterprise");
        let raw = std::fs::read_to_string(tmp.path().join(".cortex/org.yaml")).unwrap();
        assert!(raw.contains("small-company") || raw.contains("organization"));
    }

    #[test]
    fn apply_composed_instala_skills() {
        let tmp = TempDir::new().unwrap();
        apply_setup(tmp.path(), SetupAction::Composed, None, None).expect("composed");
        assert!(tmp.path().join(".cortex/skills/composed").is_dir());
        assert!(tmp.path().join("AGENTS.md").is_file());
    }

    #[test]
    fn ide_desconocido_no_escribe() {
        let tmp = TempDir::new().unwrap();
        let err = apply_setup(tmp.path(), SetupAction::Ide, Some("no-existe"), None)
            .expect_err("ide fantasma");
        assert!(err.contains("no-existe"), "{err}");
        assert!(tmp.path().read_dir().unwrap().next().is_none());
    }

    #[test]
    fn resolve_bundled_honra_cortex_cli_bin() {
        let tmp = TempDir::new().unwrap();
        let bin = tmp.path().join("cortex-cli");
        std::fs::write(&bin, b"x").unwrap();
        std::env::set_var("CORTEX_CLI_BIN", &bin);
        assert_eq!(resolve_bundled_cortex_cli(), bin);
        std::env::remove_var("CORTEX_CLI_BIN");
    }

    #[test]
    fn inspect_distingue_vacio_de_inicializado() {
        let tmp = TempDir::new().unwrap();
        let empty = inspect_setup_target(tmp.path()).expect("inspect vacío");
        assert!(empty.exists);
        assert!(!empty.has_cortex);

        apply_setup(tmp.path(), SetupAction::Agent, None, None).unwrap();
        let ready = inspect_setup_target(tmp.path()).expect("inspect listo");
        assert!(ready.has_cortex);
        assert!(ready.has_org_yaml);
    }
}
