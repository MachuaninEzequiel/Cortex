//! In-process setup profiles using `cortex_setup` detectors and templates.
use chrono::Utc;
use clap::Parser;
use cortex_setup::detector::ProjectContext;
use cortex_setup::ide::adapters::all_adapters;
use cortex_setup::ide::prompts::build_all_prompts;
use cortex_setup::ide::IdeCtx;
use cortex_setup::setup_templates as tpl;
use std::io::Write as _;
use std::path::{Path, PathBuf};

fn echo(s: &str) {
    let _ = writeln!(std::io::stdout(), "{s}");
}
fn err(s: &str) -> ! {
    let _ = writeln!(std::io::stderr(), "{s}");
    std::process::exit(1)
}
fn write(root: &Path, rel: &str, data: String) -> Result<(), String> {
    let p = root.join(rel);
    if let Some(d) = p.parent() {
        std::fs::create_dir_all(d).map_err(|e| e.to_string())?;
    }
    std::fs::write(p, data).map_err(|e| e.to_string())
}

fn dry(profile: &str, actions: &[String]) {
    echo(&format!(
        "🧠 Cortex — [dry-run] Setup {profile} profile (simulation)"
    ));
    echo("");
    for a in actions {
        echo(&format!("[dry-run] crearía: {a}"));
    }
    echo("");
    echo("✅ Dry-run complete — no changes were made.");
}

#[derive(Parser, Default)]
struct Common {
    #[arg(long)]
    dry_run: bool,
    #[arg(long)]
    non_interactive: bool,
    #[arg(long)]
    git_depth: Option<usize>,
    #[arg(long)]
    ide: Option<String>,
}
fn install_agent(root: &Path, ctx: &ProjectContext) -> Result<Vec<&'static str>, String> {
    write(root, ".cortex/workspace.yaml", tpl::render_workspace_yaml())?;
    write(root, ".cortex/config.yaml", tpl::render_config_yaml(ctx))?;
    write(
        root,
        ".cortex/org.yaml",
        tpl::render_org_yaml(&ctx.stack.project_name, "small-company", true, false)?,
    )?;
    write(
        root,
        ".cortex/vault/architecture.md",
        tpl::render_architecture_md(ctx),
    )?;
    write(
        root,
        ".cortex/vault/context.md",
        tpl::render_context_md(ctx),
    )?;
    write(
        root,
        ".cortex/vault/decisions/README.md",
        tpl::render_decisions_md(),
    )?;
    write(
        root,
        ".cortex/vault/runbooks/README.md",
        tpl::render_runbooks_md(ctx),
    )?;
    std::fs::create_dir_all(root.join(".cortex/memory")).map_err(|e| e.to_string())?;
    Ok(vec!["workspace", "config", "vault", "memory"])
}
fn install_pipeline(root: &Path, ctx: &ProjectContext) -> Result<Vec<&'static str>, String> {
    write(
        root,
        ".github/workflows/ci-feature.yml",
        tpl::render_ci_feature(ctx),
    )?;
    write(
        root,
        ".github/workflows/ci-pull-request.yml",
        tpl::render_ci_pull_request(ctx),
    )?;
    write(
        root,
        ".github/workflows/cd-deploy.yml",
        tpl::render_cd_deploy(ctx),
    )?;
    write(
        root,
        "scripts/devsecdocops.sh",
        cortex_setup::setup_templates_gen::DEVSECDOCSOPS_SCRIPT.to_string(),
    )?;
    Ok(vec!["workflows", "scripts"])
}
fn summary(profile: &str, items: &[&str]) {
    echo(&format!("✅ Cortex setup {profile} complete"));
    for i in items {
        echo(&format!("  ✓ {i}"));
    }
}

/// Porteo de `cortex.ide.inject(ide, project_root)`: inyecta perfiles y
/// config MCP del adapter nativo en modo real (el oráculo Python lo hace
/// en `SetupOrchestrator._install_ide` para agent/full con `--ide`).
fn install_ide(root: &Path, ide: &str) -> Result<Vec<String>, String> {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| root.to_path_buf());
    let ctx = IdeCtx {
        project_root: root,
        home: &home,
        now: Utc::now(),
    };
    let adapter = all_adapters()
        .into_iter()
        .find(|a| a.name() == ide)
        .ok_or_else(|| format!("Unknown IDE '{ide}'"))?;
    let prompts = build_all_prompts(&ctx);
    let mut made = adapter.inject_profiles(&ctx, &prompts)?;
    made.extend(adapter.inject_mcp(&ctx)?);
    Ok(made)
}
fn common(argv: &[String], profile: &str) -> bool {
    let a = match Common::try_parse_from(
        std::iter::once(profile.to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => err(&e.to_string()),
    };
    if !a.non_interactive && !a.dry_run {
        err("Interactive setup is not available in the native CLI; pass --non-interactive.");
    }
    let mut actions: Vec<String> = match profile {
        "agent" => vec![
            ".cortex/ workspace directories",
            "config.yaml (project config)",
            ".cortex/org.yaml (enterprise org config)",
            "vault docs (architecture.md, context.md, decisions.md, runbooks/)",
            "enterprise vault structure",
            "agent guidelines + skills install",
            "memory init (git history indexing)",
        ],
        "pipeline" => vec![
            ".github/workflows/ CI workflows (ci-feature, ci-pull-request, cd-deploy)",
            "scripts/ DevSecDocOps pipeline script",
            "config.yaml (project config)",
            "enterprise vault structure (CI/CD docs)",
        ],
        _ => vec![
            ".cortex/ workspace directories",
            "config.yaml (project config)",
            ".cortex/org.yaml (enterprise org config)",
            "vault docs (architecture.md, context.md, decisions.md, runbooks/)",
            "enterprise vault structure",
            ".github/workflows/ CI workflows + scripts/ DevSecDocOps script",
            "agent guidelines + skills install",
            "webgraph visualization module (.cortex/webgraph/)",
            "memory init (git history indexing) + .gitignore update",
        ],
    }
    .into_iter()
    .map(str::to_string)
    .collect();
    if let Some(ide) = &a.ide {
        actions.push(format!("IDE config for '{ide}'"));
    }
    if a.dry_run {
        dry(profile, &actions);
        return true;
    }
    let root = std::env::current_dir().unwrap_or_default();
    let ctx = ProjectContext::detect(&root);
    let result = (|| {
        let mut made: Vec<String> = Vec::new();
        if profile != "pipeline" {
            made.extend(install_agent(&root, &ctx)?.into_iter().map(str::to_string));
        }
        if profile != "agent" {
            made.extend(
                install_pipeline(&root, &ctx)?
                    .into_iter()
                    .map(str::to_string),
            );
        }
        if profile == "full" {
            write(
                &root,
                ".cortex/webgraph/workspace.yaml",
                "projects:\n  - path: .\n".into(),
            )?;
            made.push("webgraph".into());
        }
        if let Some(ide) = &a.ide {
            // Mismo orden que el oráculo: `_install_ide()` es el último paso
            // de agent/full. E2E requiere `--non-interactive --ide <name>`
            // para que el IDE quede configurado de verdad.
            made.push(format!("IDE profiles injected ({ide})"));
            made.extend(install_ide(&root, ide)?);
        }
        Ok::<_, String>(made)
    })();
    match result {
        Ok(m) => {
            let items: Vec<&str> = m.iter().map(String::as_str).collect();
            summary(profile, &items);
        }
        Err(e) => err(&e),
    };
    true
}

#[derive(Parser)]
struct Web {
    #[arg(long)]
    dry_run: bool,
    #[arg(long)]
    attach_project_root: Option<String>,
    #[arg(long)]
    non_interactive: bool,
}
fn web(argv: &[String]) -> bool {
    let a =
        match Web::try_parse_from(std::iter::once("webgraph".into()).chain(argv.iter().cloned())) {
            Ok(a) => a,
            Err(e) => err(&e.to_string()),
        };
    if a.dry_run {
        dry(
            "webgraph",
            &[
                "webgraph module files under .cortex/webgraph/".into(),
                ".cortex/webgraph/workspace.yaml".into(),
            ],
        );
        return true;
    }
    let root = std::env::current_dir().unwrap_or_default();
    let attached = a.attach_project_root.unwrap_or_else(|| ".".into());
    match write(
        &root,
        ".cortex/webgraph/workspace.yaml",
        format!("projects:\n  - path: {attached}\n"),
    ) {
        Ok(()) => summary("webgraph", &["webgraph"]),
        Err(e) => err(&e),
    };
    true
}

#[derive(Parser)]
struct Enterprise {
    #[arg(long)]
    preset: Option<String>,
    #[arg(long)]
    org_config: Option<String>,
    #[arg(long)]
    dry_run: bool,
    #[arg(long)]
    non_interactive: bool,
    #[arg(long)]
    json: bool,
}
fn enterprise(argv: &[String]) -> bool {
    let a = match Enterprise::try_parse_from(
        std::iter::once("enterprise".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => err(&e.to_string()),
    };
    if a.non_interactive && a.preset.is_none() && a.org_config.is_none() {
        err("Non-interactive mode requires --preset or --org-config.");
    }
    if a.preset.as_deref() == Some("custom") && a.org_config.is_none() {
        err("Preset 'custom' requires --org-config.");
    }
    if a.dry_run {
        dry(
            "enterprise",
            &[
                ".cortex/org.yaml (enterprise org config)".into(),
                "enterprise vault structure".into(),
            ],
        );
        return true;
    }
    let root = std::env::current_dir().unwrap_or_default();
    let ctx = ProjectContext::detect(&root);
    let preset = a.preset.as_deref().unwrap_or("small-company");
    let yaml = match tpl::render_org_yaml(&ctx.stack.project_name, preset, true, false) {
        Ok(y) => y,
        Err(e) => err(&e),
    };
    if let Err(e) = write(&root, ".cortex/org.yaml", yaml) {
        err(&e)
    }
    if a.json {
        echo(&format!(
            r#"{{"preset": "{preset}", "org_config": ".cortex/org.yaml"}}"#
        ))
    } else {
        summary("enterprise", &["org config"])
    }
    true
}

/// `cortex init` — alias nativo de `setup agent` (oráculo main.py:796-806:
/// único flag `--non-interactive`). Sin `--non-interactive` el oráculo entra
/// en modo interactivo; el nativo no tiene TUI ⇒ error como `setup agent`.
#[derive(Parser)]
struct Init {
    #[arg(long)]
    non_interactive: bool,
}

pub fn run_init(argv: &[String]) -> bool {
    let _a =
        match Init::try_parse_from(std::iter::once("init".to_string()).chain(argv.iter().cloned()))
        {
            Ok(a) => a,
            Err(e) => err(&e.to_string()),
        };
    // Dispara `setup agent` con el mismo argv (sólo acepta --non-interactive,
    // igual que el oráculo `init`).
    common(argv, "agent")
}

/// `cortex setup composed` (Obra 08 A11): instala la familia COMPOSED en
/// `.cortex/skills/composed/` + la tríada thin+craft en `.cortex/skills/`
/// (bundle embebido, byte-exacta por construcción — patrón install-skills)
/// y escribe el bloque `## Agent skills` en CLAUDE.md/AGENTS.md (upsert con
/// marcadores, precedente codex).
#[derive(Parser)]
struct Composed {
    #[arg(long)]
    dry_run: bool,
    #[arg(long)]
    non_interactive: bool,
    #[arg(long)]
    project_root: Option<String>,
}

fn composed(argv: &[String]) -> bool {
    let a = match Composed::try_parse_from(
        std::iter::once("composed".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => err(&e.to_string()),
    };
    if !a.non_interactive && !a.dry_run {
        err("Interactive setup is not available in the native CLI; pass --non-interactive.");
    }
    let root = match &a.project_root {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().unwrap_or_default(),
    };
    if a.dry_run {
        dry(
            "composed",
            &[
                ".cortex/skills/composed/ (8 skills + INSTALL-COMPOSED.md)".into(),
                ".cortex/skills/ (triada thin + craft on-demand)".into(),
                "bloque ## Agent skills en CLAUDE.md/AGENTS.md".into(),
            ],
        );
        return true;
    }
    let result = (|| -> Result<Vec<String>, String> {
        let mut made: Vec<String> = Vec::new();
        let fam = cortex_setup::skills_bundle::install_composed_family(
            &root.join(".cortex/skills/composed"),
        );
        made.extend(fam.into_iter().map(|n| format!("composed/{n}")));
        let tri = cortex_setup::skills_bundle::install_triad_skills(&root.join(".cortex/skills"));
        made.extend(tri);
        let block = cortex_setup::skills_bundle::agent_skills_block();
        let mut docs: Vec<String> = Vec::new();
        for name in ["CLAUDE.md", "AGENTS.md"] {
            let p = root.join(name);
            if !p.exists() {
                continue;
            }
            let content = std::fs::read_to_string(&p).map_err(|e| format!("read {name}: {e}"))?;
            let updated = cortex_setup::ide::base::upsert_marker_block(&content, &block);
            std::fs::write(&p, updated).map_err(|e| format!("write {name}: {e}"))?;
            docs.push(name.to_string());
        }
        if docs.is_empty() {
            write(&root, "AGENTS.md", format!("{block}\n"))?;
            docs.push("AGENTS.md (created)".into());
        }
        made.push(format!("Agent skills block en {}", docs.join(", ")));
        Ok(made)
    })();
    match result {
        Ok(m) => {
            let items: Vec<&str> = m.iter().map(String::as_str).collect();
            summary("composed", &items);
        }
        Err(e) => err(&e),
    };
    true
}

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("agent") => common(&argv[1..], "agent"),
        Some("pipeline") => common(&argv[1..], "pipeline"),
        Some("full") => common(&argv[1..], "full"),
        Some("composed") => composed(&argv[1..]),
        Some("webgraph") => web(&argv[1..]),
        Some("enterprise") => enterprise(&argv[1..]),
        Some(first) => {
            eprintln!("No such command '{first}'.");
            std::process::exit(2);
        }
        None => {
            eprintln!(
                "cortex setup: se requiere un perfil (agent|pipeline|full|composed|webgraph|enterprise)"
            );
            std::process::exit(2);
        }
    }
}
