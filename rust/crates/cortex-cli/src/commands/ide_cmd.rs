//! `cortex ide` nativo (MITAD B, ruta 1) — list/setup/remove/status.
//!
//! Porte glue de `cortex/cli/ide.py` (376 líneas) sobre los nativos
//! `cortex_setup::ide` (adapters, prompts, IdeCtx) + `HookInstaller`
//! (lado hooks de `collect_status`). Strings de salida y errores EXACTOS
//! del oráculo. NO instala hooks en setup — el oráculo `run_setup` solo
//! inyecta perfiles + MCP (`cortex.ide.inject`); el gate de paridad lo
//! verifica byte-a-byte contra el CLI Python real.

use chrono::Utc;
use clap::Parser;
use cortex_setup::ide::adapters::all_adapters;
use cortex_setup::ide::prompts::build_all_prompts;
use cortex_setup::ide::{IdeAdapter, IdeCtx};
use cortex_setup::session_hooks::{default_installer, HookInstaller};
use std::io::Write as _;
use std::path::{Path, PathBuf};
use unicode_width::UnicodeWidthChar;

fn echo(s: &str) {
    let _ = writeln!(std::io::stdout(), "{s}");
}
fn eecho(s: &str) {
    let _ = writeln!(std::io::stderr(), "{s}");
}

/// `_fail(message, code)`: `typer.echo(f"Error: {message}", err=True)`.
fn fail(message: &str, code: i32) -> ! {
    eecho(&format!("Error: {message}"));
    std::process::exit(code);
}

// ---------------------------------------------------------------------------
// Registry (espejo de cortex/ide/registry.py)
// ---------------------------------------------------------------------------

const TARGET_IDES: [&str; 4] = ["claude_code", "codex", "opencode", "pi"];
const COMMUNITY_IDES: [&str; 4] = ["claude_desktop", "cursor", "vscode", "windsurf"];
const EXPERIMENTAL_IDES: [&str; 3] = ["antigravity", "hermes", "zed"];
const VALIDATED_IDES: [&str; 5] = ["claude_code", "cursor", "opencode", "pi", "codex"];

/// `_ALIASES` de registry.py.
const ALIASES: &[(&str, &str)] = &[
    ("claude", "claude_code"),
    ("claude-code", "claude_code"),
    ("claude-desktop", "claude_desktop"),
    ("code", "vscode"),
    ("visual-studio-code", "vscode"),
    ("vs-code", "vscode"),
    ("openai-codex", "codex"),
    ("codex-cli", "codex"),
];

fn normalize_ide(raw: &str) -> String {
    let n = raw.trim().to_lowercase();
    ALIASES
        .iter()
        .find(|(a, _)| **a == n)
        .map(|(_, canon)| canon.to_string())
        .unwrap_or(n)
}

fn tier_of(name: &str) -> &'static str {
    if TARGET_IDES.contains(&name) {
        "target"
    } else if EXPERIMENTAL_IDES.contains(&name) {
        "experimental"
    } else {
        "community"
    }
}

fn validated_of(name: &str) -> bool {
    VALIDATED_IDES.contains(&name)
}

/// `registry.get_adapter`: normaliza + resuelve alias; error EXACTO del
/// oráculo (KeyError ⇒ `str(exc)` = repr del mensaje: comillas + `\n`
/// literales, una sola línea).
fn resolve_adapter<'a>(
    name: &str,
    adapters: &'a [Box<dyn IdeAdapter>],
) -> Option<&'a dyn IdeAdapter> {
    let normalized = normalize_ide(name);
    adapters
        .iter()
        .find(|a| a.name() == normalized)
        .map(|b| b.as_ref())
}

fn unknown_ide_message(name: &str) -> String {
    let mut target_sorted: Vec<&str> = TARGET_IDES.to_vec();
    target_sorted.sort_unstable();
    let mut community_sorted: Vec<&str> = COMMUNITY_IDES.to_vec();
    community_sorted.sort_unstable();
    let mut experimental_sorted: Vec<&str> = EXPERIMENTAL_IDES.to_vec();
    experimental_sorted.sort_unstable();
    let msg = format!(
        "Unknown IDE: '{name}'.\n  Target (officially supported): {}\n  Community (best-effort):       {}\n  Experimental:                  {}",
        target_sorted.join(", "),
        community_sorted.join(", "),
        experimental_sorted.join(", ")
    );
    // repr de Python para el string del KeyError: comillas + escapes.
    let mut out = String::from("\"");
    for c in msg.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// `_require_ide`: error de --ide faltante con tiers disponibles (rc 2).
fn require_ide(ide: Option<String>, action: &str) -> String {
    if let Some(ide) = ide {
        return ide;
    }
    let mut target_sorted: Vec<&str> = TARGET_IDES.to_vec();
    target_sorted.sort_unstable();
    let mut community_sorted: Vec<&str> = COMMUNITY_IDES.to_vec();
    community_sorted.sort_unstable();
    let mut experimental_sorted: Vec<&str> = EXPERIMENTAL_IDES.to_vec();
    experimental_sorted.sort_unstable();
    fail(
        &format!(
            "--ide is required for `cortex ide {action}` (no interactive prompt on this surface). Available IDEs:\n  target:       {}\n  community:    {}\n  experimental: {}",
            target_sorted.join(", "),
            community_sorted.join(", "),
            experimental_sorted.join(", ")
        ),
        2,
    )
}

/// `_get_adapter_or_exit` (código 2) — resuelto inline por `resolve_adapter`
/// en cada subcomando.

// ---------------------------------------------------------------------------
// Argumentos (espejo de los Options de typer)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "list",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct ListArgs {
    #[arg(long)]
    json: bool,
}

#[derive(Parser, Debug)]
#[command(
    name = "setup",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct SetupArgs {
    #[arg(long)]
    ide: Option<String>,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    dry_run: bool,
    #[arg(long = "sync-canonical", overrides_with = "no_sync")]
    sync_canonical: bool,
    #[arg(long = "no-sync-canonical")]
    no_sync: bool,
}

#[derive(Parser, Debug)]
#[command(
    name = "remove",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct RemoveArgs {
    #[arg(long)]
    ide: Option<String>,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    dry_run: bool,
}

#[derive(Parser, Debug)]
#[command(
    name = "status",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct StatusArgs {
    #[arg(long)]
    ide: Option<String>,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    json: bool,
}

// ---------------------------------------------------------------------------
// Helpers compartidos
// ---------------------------------------------------------------------------

fn resolve_root(project_root: Option<String>) -> PathBuf {
    crate::paths::resolve_project_root(project_root.as_deref())
}

/// Contexto de inyección con HOME/reloj reales (los adapters son
/// project-scoped o read-only salvo setup/remove).
fn home_path(root: &Path) -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| root.to_path_buf())
}

fn ctx_for<'a>(root: &'a Path, home: &'a Path) -> IdeCtx<'a> {
    IdeCtx {
        project_root: root,
        home,
        now: Utc::now(),
    }
}

/// `_absolute(path, root)` del oráculo.
fn absolute(path: &Path, root: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        root.join(path)
    }
}

/// `_uninstall_supported`: todos los adapters nativos sobreescriben
/// `uninstall` (espejo de los 11 adapters Python).
fn uninstall_supported(_adapter: &dyn IdeAdapter) -> bool {
    true
}

/// `_hook_lookup`: `hook_name = adapter_name.replace("_", "-")`; si el
/// installer no lo tiene ⇒ None (KeyError atrapado).
fn hook_lookup<'a>(
    installer: &'a HookInstaller,
    adapter_name: &str,
) -> Option<&'a dyn cortex_setup::session_hooks::HookAdapter> {
    let hook_name = adapter_name.replace('_', "-");
    installer.get(&hook_name).ok()
}

// ---------------------------------------------------------------------------
// Subcomandos
// ---------------------------------------------------------------------------

fn run_list(argv: &[String]) -> bool {
    let args = match ListArgs::try_parse_from(
        std::iter::once("list".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string(), 2),
    };
    let adapters = all_adapters();
    // get_all_adapters(include_experimental=True) ⇒ sorted por nombre.
    let mut sorted: Vec<&dyn IdeAdapter> = adapters.iter().map(|b| b.as_ref()).collect();
    sorted.sort_by(|a, b| a.name().cmp(b.name()));
    if args.json {
        let rows: Vec<crate::pyjson::PyVal> = sorted
            .iter()
            .map(|a| {
                crate::pyjson::PyVal::obj(vec![
                    ("name", crate::pyjson::PyVal::s(a.name())),
                    ("display_name", crate::pyjson::PyVal::s(a.display_name())),
                    ("tier", crate::pyjson::PyVal::s(tier_of(a.name()))),
                    (
                        "uninstall_supported",
                        crate::pyjson::PyVal::Bool(uninstall_supported(*a)),
                    ),
                    (
                        "validated",
                        crate::pyjson::PyVal::Bool(validated_of(a.name())),
                    ),
                ])
            })
            .collect();
        echo(&crate::pyjson::stdlib_dumps_compact_array(&rows));
        return true;
    }
    // Tabla rich byte-parity.
    let headers = ["IDE", "DISPLAY NAME", "TIER", "UNINSTALL", "VALIDATED"];
    let rows: Vec<Vec<String>> = sorted
        .iter()
        .map(|a| {
            vec![
                a.name().to_string(),
                a.display_name().to_string(),
                tier_of(a.name()).to_string(),
                if uninstall_supported(*a) {
                    "✓"
                } else {
                    "—"
                }
                .to_string(),
                if validated_of(a.name()) { "✓" } else { "—" }.to_string(),
            ]
        })
        .collect();
    echo(&render_table(&headers, &rows, &[3, 4]));
    true
}

fn run_setup(argv: &[String]) -> bool {
    let args = match SetupArgs::try_parse_from(
        std::iter::once("setup".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string(), 2),
    };
    let ide = require_ide(args.ide, "setup");
    let root = resolve_root(args.project_root);
    let adapters = all_adapters();
    let adapter = match resolve_adapter(&ide, &adapters) {
        Some(a) => a,
        None => fail(&unknown_ide_message(&ide), 2),
    };
    let display = adapter.display_name();
    if args.dry_run {
        echo(&format!(
            "[DRY-RUN] Would set up {display} ({}) in {}:",
            adapter.name(),
            root.display()
        ));
        echo("  - inject agent profiles (from .cortex/skills/ and .cortex/subagents/)");
        echo("  - inject MCP server configuration");
        let home = home_path(&root);
        let ctx = ctx_for(&root, &home);
        let mut paths: Vec<(String, PathBuf)> = adapter.config_paths(&ctx);
        paths.sort_by(|a, b| a.0.cmp(&b.0));
        for (key, path) in &paths {
            echo(&format!(
                "  - target [{key}]: {}",
                absolute(path, &root).display()
            ));
        }
        echo("Dry-run: no changes were written.");
        return true;
    }
    // `cortex_ide.inject`: inyectar perfiles + MCP (mismo orden que
    // install_ide de setup_cmd; pi NO usa prompts).
    let home = home_path(&root);
    let ctx = ctx_for(&root, &home);
    let prompts = build_all_prompts(&ctx);
    let mut files = match adapter.inject_profiles(&ctx, &prompts) {
        Ok(f) => f,
        Err(e) => fail(&e, 1),
    };
    match adapter.inject_mcp(&ctx) {
        Ok(mut m) => files.append(&mut m),
        Err(e) => fail(&e, 1),
    }
    echo(&format!("[Cortex IDE] Injecting profiles for {display}..."));
    for f in &files {
        echo(&format!("  [OK] {f}"));
    }
    echo(&format!(
        "\n✅ Setup complete for {display}. Setup is idempotent; re-run `cortex ide setup --ide {}` anytime to re-sync.",
        adapter.name()
    ));
    true
}

fn run_remove(argv: &[String]) -> bool {
    let args = match RemoveArgs::try_parse_from(
        std::iter::once("remove".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string(), 2),
    };
    let ide = require_ide(args.ide, "remove");
    let root = resolve_root(args.project_root);
    let adapters = all_adapters();
    let adapter = match resolve_adapter(&ide, &adapters) {
        Some(a) => a,
        None => fail(&unknown_ide_message(&ide), 2),
    };
    let display = adapter.display_name();
    let home = home_path(&root);
    let ctx = ctx_for(&root, &home);
    if args.dry_run {
        echo(&format!(
            "[DRY-RUN] Would remove Cortex content from {display} ({}) in {}:",
            adapter.name(),
            root.display()
        ));
        let mut paths: Vec<(String, PathBuf)> = adapter.config_paths(&ctx);
        paths.sort_by(|a, b| a.0.cmp(&b.0));
        let candidates: Vec<(String, PathBuf)> = paths
            .into_iter()
            .filter(|(_, p)| absolute(p, &root).exists())
            .collect();
        if candidates.is_empty() {
            echo("  - nothing found: no managed Cortex paths exist yet");
        } else {
            for (key, path) in &candidates {
                let state = if absolute(path, &root).is_file() {
                    "clean Cortex blocks / keys"
                } else {
                    "prune Cortex entries"
                };
                echo(&format!(
                    "  - [{key}] {} ({state})",
                    absolute(path, &root).display()
                ));
            }
        }
        echo("Dry-run: nothing was removed.");
        return true;
    }
    echo(&format!("[Cortex IDE] Removing Cortex from {display}..."));
    let report = adapter.uninstall(&ctx);
    let mut removed = 0usize;
    for entry in &report {
        echo(&format!("  [REMOVED] {entry}"));
        removed += 1;
    }
    let still_present: Vec<PathBuf> = adapter
        .config_paths(&ctx)
        .into_iter()
        .map(|(_, p)| absolute(&p, &root))
        .filter(|p| p.exists())
        .collect();
    let mut skipped = 0usize;
    for path in &still_present {
        echo(&format!(
            "  [SKIPPED] {} still present (user-owned or shared file)",
            path.display()
        ));
        skipped += 1;
    }
    echo(&format!(
        "Remove complete for {display}: {removed} entradas procesadas, {skipped} paths restantes."
    ));
    true
}

fn run_status(argv: &[String]) -> bool {
    let args = match StatusArgs::try_parse_from(
        std::iter::once("status".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string(), 2),
    };
    let root = resolve_root(args.project_root);
    let installer = default_installer();
    let adapters = all_adapters();
    let selected: Vec<&dyn IdeAdapter> = match &args.ide {
        Some(ide) => match resolve_adapter(ide, &adapters) {
            Some(a) => vec![a],
            None => fail(&unknown_ide_message(ide), 2),
        },
        None => adapters.iter().map(|b| b.as_ref()).collect(),
    };
    // Orden de get_all_adapters (sorted por nombre) para el caso "all".
    let mut selected = selected;
    if args.ide.is_none() {
        selected.sort_by(|a, b| a.name().cmp(b.name()));
    }
    if args.json {
        let payload: Vec<crate::pyjson::PyVal> = selected
            .iter()
            .map(|a| status_payload(*a, &root, &installer))
            .collect();
        echo(&crate::pyjson::stdlib_dumps_compact_array(&payload));
        return true;
    }
    let headers = ["IDE", "TIER", "CONFIG", "MCP", "HOOKS", "DETAIL"];
    let rows: Vec<Vec<String>> = selected
        .iter()
        .map(|a| {
            let p = status_row(*a, &root, &installer);
            vec![
                p.0,
                p.1,
                if p.2 { "✓" } else { "✗" }.to_string(),
                match p.3 {
                    Some(true) => "✓".to_string(),
                    Some(false) => "✗".to_string(),
                    None => "—".to_string(),
                },
                match p.4 {
                    Some(true) => "✓".to_string(),
                    Some(false) => "✗".to_string(),
                    None => "—".to_string(),
                },
                p.5,
            ]
        })
        .collect();
    echo(&render_table(&headers, &rows, &[2, 3, 4]));
    true
}

/// Payload JSON de `collect_status` (orden de claves del dict Python).
fn status_payload(
    adapter: &dyn IdeAdapter,
    root: &Path,
    installer: &HookInstaller,
) -> crate::pyjson::PyVal {
    let home = home_path(root);
    let ctx = ctx_for(root, &home);
    let config = adapter.config_paths(&ctx);
    let checks: Vec<(String, bool)> = config
        .iter()
        .map(|(name, path)| (name.clone(), absolute(path, root).exists()))
        .collect();
    let expected_config_present = checks.iter().any(|(_, present)| *present);
    let mcp_key = config
        .iter()
        .find(|(name, _)| name.to_lowercase().contains("mcp"))
        .map(|(name, _)| name.clone());
    let mcp_path = mcp_key.as_ref().and_then(|k| {
        config
            .iter()
            .find(|(name, _)| name == k)
            .map(|(_, p)| absolute(p, root))
    });
    let mcp_configured = mcp_path.as_ref().map(|p| p.exists());
    let hooks = hook_lookup(installer, adapter.name());
    let (hooks_installed, hooks_detail): (Option<bool>, String) = match hooks {
        Some(h) => {
            let status = h.status(root);
            (Some(status.installed), status.detail.clone())
        }
        None => (None, String::new()),
    };
    crate::pyjson::PyVal::obj(vec![
        ("ide", crate::pyjson::PyVal::s(adapter.name())),
        (
            "display_name",
            crate::pyjson::PyVal::s(adapter.display_name()),
        ),
        ("tier", crate::pyjson::PyVal::s(tier_of(adapter.name()))),
        (
            "validated",
            crate::pyjson::PyVal::Bool(validated_of(adapter.name())),
        ),
        (
            "expected_config_present",
            crate::pyjson::PyVal::Bool(expected_config_present),
        ),
        (
            "config_checks",
            crate::pyjson::PyVal::Obj(
                checks
                    .into_iter()
                    .map(|(k, v)| (k.clone(), crate::pyjson::PyVal::Bool(v)))
                    .collect(),
            ),
        ),
        (
            "mcp_configured",
            match mcp_configured {
                Some(b) => crate::pyjson::PyVal::Bool(b),
                None => crate::pyjson::PyVal::Null,
            },
        ),
        (
            "mcp_path",
            match &mcp_path {
                Some(p) => crate::pyjson::PyVal::s(p.to_string_lossy().to_string()),
                None => crate::pyjson::PyVal::Null,
            },
        ),
        (
            "hooks_installed",
            match hooks_installed {
                Some(b) => crate::pyjson::PyVal::Bool(b),
                None => crate::pyjson::PyVal::Null,
            },
        ),
        ("hooks_detail", crate::pyjson::PyVal::s(hooks_detail)),
    ])
}

/// Fila texto del status (ide, tier, config, mcp, hooks, detail).
fn status_row(
    adapter: &dyn IdeAdapter,
    root: &Path,
    installer: &HookInstaller,
) -> (String, String, bool, Option<bool>, Option<bool>, String) {
    let home = home_path(root);
    let ctx = ctx_for(root, &home);
    let config = adapter.config_paths(&ctx);
    let expected_config_present = config.iter().any(|(_, p)| absolute(p, root).exists());
    let mcp_key = config
        .iter()
        .find(|(name, _)| name.to_lowercase().contains("mcp"))
        .map(|(_, p)| absolute(p, root));
    let mcp_configured = mcp_key.as_ref().map(|p| p.exists());
    let hooks = hook_lookup(installer, adapter.name());
    let (hooks_installed, hooks_detail) = match hooks {
        Some(h) => {
            let status = h.status(root);
            (Some(status.installed), status.detail.clone())
        }
        None => (None, String::new()),
    };
    // Tabla texto: detail = hooks_detail o "n/a" cuando no hay adapter de
    // hooks (mismo or None de `p["hooks_installed"] is None`).
    let detail_text = if hooks_detail.is_empty() {
        if hooks_installed.is_none() {
            "n/a".to_string()
        } else {
            String::new()
        }
    } else {
        hooks_detail.clone()
    };
    (
        adapter.name().to_string(),
        tier_of(adapter.name()).to_string(),
        expected_config_present,
        mcp_configured,
        hooks_installed,
        detail_text,
    )
}

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("list") => run_list(&argv[1..]),
        Some("setup") => run_setup(&argv[1..]),
        Some("remove") => run_remove(&argv[1..]),
        Some("status") => run_status(&argv[1..]),
        // Baja física (sin passthrough a Python): subcomando desconocido ⇒
        // rechazo nativo Typer-like (rc 2); sin subcomando ⇒ `ide` solo.
        Some(first) => {
            eprintln!("No such command '{first}'.");
            std::process::exit(2);
        }
        None => {
            eprintln!("cortex ide: se requiere un subcomando (list|setup|remove|status)");
            std::process::exit(2);
        }
    }
}

// ---------------------------------------------------------------------------
// Tabla rich byte-parity (consola no-TTY de 80 columnas)
//
// Porte empírico del algoritmo de rich.table.Table (HEAVY_HEAD, padding
// (0,1), overflow ellipsis) verificado byte-a-byte contra el CLI real en
// el gate cierre_leaves_b_golden.py:
//   - widths por columna = medida natural (header+cells, +2 padding) con
//     colapso proporcional cuando excede 80-(n+1) bordes;
//   - celdas: word-wrap greedy (sin cortar palabras), y cada línea que
//     excede el ancho interior se recorta a width-1 + "…";
//   - justify left (default) o center por columna.
// ---------------------------------------------------------------------------

fn cell_width(s: &str) -> usize {
    s.chars().map(|c| c.width().unwrap_or(0)).sum()
}

/// measure del oráculo: min = palabra más larga, max = línea más larga.
fn measure(text: &str) -> (usize, usize) {
    let lines: Vec<&str> = text.lines().collect();
    let max_line = lines.iter().map(|l| cell_width(l)).max().unwrap_or(0);
    let words: Vec<&str> = text.split_whitespace().collect();
    let max_word = if words.is_empty() {
        max_line
    } else {
        words.iter().map(|w| cell_width(w)).max().unwrap_or(0)
    };
    (max_word, max_line)
}

fn wrap_words(text: &str, width: usize) -> Vec<String> {
    if width == 0 {
        return vec![String::new()];
    }
    let mut out: Vec<String> = Vec::new();
    for source in text.split('\n') {
        let mut cur = String::new();
        let mut used = 0usize;
        for word in source.split(' ').filter(|w| !w.is_empty()) {
            let w = cell_width(word);
            if used > 0 && used + 1 + w > width {
                out.push(std::mem::take(&mut cur));
                used = 0;
            }
            if used > 0 {
                cur.push(' ');
                used += 1;
            }
            cur.push_str(word);
            used += w;
        }
        out.push(cur);
    }
    out
}

/// Elipsis rich: línea cuya celda-ancho excede `width` ⇒ width-1 + "…".
fn ellipsize(line: &str, width: usize) -> String {
    let w = cell_width(line);
    if w <= width {
        return line.to_string();
    }
    let keep = width.saturating_sub(1);
    let mut out = String::new();
    let mut used = 0usize;
    for c in line.chars() {
        let cw = c.width().unwrap_or(0);
        if used + cw > keep {
            break;
        }
        out.push(c);
        used += cw;
    }
    out.push('…');
    out
}

fn pad_to(line: &str, cells: usize) -> String {
    let mut out = String::from(line);
    let current = cell_width(&out);
    for _ in current..cells {
        out.push(' ');
    }
    out
}

/// Render de una celda (ya medida) → líneas con justify.
fn render_cell(text: &str, width: usize, center: bool) -> Vec<String> {
    let inner = width.saturating_sub(2);
    let mut lines: Vec<String> = Vec::new();
    for wrapped in wrap_words(text, inner) {
        let line = ellipsize(&wrapped, inner);
        if center {
            let w = cell_width(&line);
            let pad = inner.saturating_sub(w);
            let left = pad / 2;
            let right = pad - left;
            lines.push(format!("{}{}{}", " ".repeat(left), line, " ".repeat(right)));
        } else {
            lines.push(pad_to(&line, inner));
        }
    }
    if lines.is_empty() {
        lines.push(" ".repeat(inner));
    }
    lines
}

/// widths (incl. padding) del algoritmo rich a 80 columnas.
fn rich_widths(headers: &[&str], rows: &[Vec<String>]) -> Vec<usize> {
    let n = headers.len();
    // max natural por columna (incl. padding 2).
    let mut maxes: Vec<usize> = vec![0; n];
    for i in 0..n {
        let mut m = 0usize;
        let mut push = |text: &str| {
            let (_, max_line) = measure(text);
            m = m.max(max_line);
        };
        push(headers[i]);
        for r in rows {
            push(&r[i]);
        }
        maxes[i] = m + 2;
    }
    let max_width = 80usize.saturating_sub(n + 1);
    let mut widths = maxes.clone();
    if widths.iter().sum::<usize>() > max_width {
        // _collapse_widths de rich: reduce la(s) columna(s) más ancha(s).
        while widths.iter().sum::<usize>() > max_width {
            let max_col = widths.iter().copied().max().unwrap_or(1);
            let second = widths
                .iter()
                .copied()
                .filter(|w| *w != max_col)
                .max()
                .unwrap_or(0);
            let diff = max_col.saturating_sub(second);
            if diff == 0 {
                break;
            }
            let excess = widths.iter().sum::<usize>() - max_width;
            let reduce = excess.min(diff);
            // solo la columna más ancha se reduce (ratios 1:0).
            let mut hit = false;
            for w in widths.iter_mut() {
                if !hit && *w == max_col {
                    let distributed = reduce.min(*w);
                    *w -= distributed;
                    hit = true;
                }
            }
        }
        // remeasure: cada columna acotada a su width colapsado.
        for (w, m) in widths.iter_mut().zip(maxes.iter()) {
            *w = (*w).min(*m);
        }
    }
    widths
}

/// `rich.table.Table` (HEAVY_HEAD) byte-parity para las tablas de `ide`.
fn render_table(headers: &[&str], rows: &[Vec<String>], center_cols: &[usize]) -> String {
    let n = headers.len();
    let widths = rich_widths(headers, rows);
    let border = |left: char, mid: char, right: char, fill: char| -> String {
        let mut s = String::new();
        s.push(left);
        for (i, w) in widths.iter().enumerate() {
            s.extend(std::iter::repeat_n(fill, *w));
            if i + 1 < n {
                s.push(mid);
            }
        }
        s.push(right);
        s
    };
    let mut out = String::new();
    out.push_str(&border('┏', '┳', '┓', '━'));
    out.push('\n');
    // Header.
    let header_strings: Vec<String> = headers.iter().map(|h| h.to_string()).collect();
    out.push_str(&render_row(&header_strings, &widths, center_cols, true));
    out.push('\n');
    out.push_str(&border('┡', '╇', '┩', '━'));
    out.push('\n');
    for r in rows {
        out.push_str(&render_row(r, &widths, center_cols, false));
        out.push('\n');
    }
    out.push_str(&border('└', '┴', '┘', '─'));
    out
}

fn render_row(cells: &[String], widths: &[usize], center_cols: &[usize], header: bool) -> String {
    let rendered: Vec<Vec<String>> = cells
        .iter()
        .enumerate()
        .map(|(i, c)| render_cell(c, widths[i], (!header) && center_cols.contains(&i)))
        .collect();
    let height = rendered.iter().map(Vec::len).max().unwrap_or(1);
    let edge = if header { "┃" } else { "│" };
    let mut out = String::new();
    for row in 0..height {
        out.push_str(edge);
        for (i, lines) in rendered.iter().enumerate() {
            let inner = widths[i].saturating_sub(2);
            let line = lines.get(row).map(String::as_str).unwrap_or("");
            out.push(' ');
            out.push_str(&pad_to(line, inner));
            out.push(' ');
            out.push_str(edge);
        }
        if row + 1 < height {
            out.push('\n');
        }
    }
    out
}
