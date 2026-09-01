//! Home de Cortex en ratatui — espejo de `cortex/tui/core.py` (Obra 05 Fase D).
//!
//! `HomeState` replica campo a campo el snapshot barato del Home Python; el
//! cableado a servicios reales (sessions/acciones/vault vía cortex-app)
//! llega con F4 del rediseño. Mientras tanto `demo_state()` provee datos
//! de muestra para el gate P10: snapshot render + latencia <50ms.
//!
//! Rediseño F2: todo el estilo pasa por `Theme` (sin `Color::Rgb` sueltos);
//! el ámbar ad-hoc de avisos se reemplazó por el token semántico WARNING.

use crate::app::state::Notification;
use crate::components::status_bar::StatusBar;
use crate::layout::{layout_mode, LayoutMode};
use crate::renderer::CortexLogo;
use crate::theme::{brand_text, StatusKind, Theme};
use crate::{env_color_mode, lang, LogoVariant};
use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::scheduler::Scheduler;
use cortex_actions::store::PreferencesStore;
use cortex_app::session::service::SessionService;
use ratatui::prelude::{Constraint, Layout, Style};
use ratatui::widgets::Paragraph;
use ratatui::Frame;
use std::path::Path;
use std::time::Instant;

/// Presupuesto de render del Home (gate P10: "Home <50ms").
pub const RENDER_BUDGET_MS: u128 = 50;

/// Estado del Home — espejo de `HomeState` en cortex/tui/core.py.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct HomeState {
    pub proyecto: String,
    pub rama: Option<String>,
    pub sesion_line: Option<String>,
    pub acciones_pendientes: usize,
    pub vault_notas: usize,
    pub doctor_items: Vec<(String, String)>,
    pub errores: Vec<String>,
    pub elapsed_ms: u16,
    pub lang: &'static str,
}

/// Estado de muestra para demos, snapshots y el test de latencia.
pub fn demo_state() -> HomeState {
    HomeState {
        proyecto: "cortex".into(),
        rama: Some("feature/transformacion-2026-08".into()),
        sesion_line: Some("ses-2026-08-24 · OPEN · 3 checkpoints".into()),
        acciones_pendientes: 2,
        vault_notas: 42,
        doctor_items: vec![
            ("mcp".into(), "ok".into()),
            ("vault".into(), "ok".into()),
            ("embeddings".into(), "ok".into()),
        ],
        errores: vec![],
        elapsed_ms: 12,
        lang: lang(),
    }
}

// ── snapshot REAL (espejo de `snapshot_home` en cortex/tui/core.py) ────────

/// Snapshot barato del Home nativo: rama (HEAD), sesión activa, cuenta de
/// acciones del motor, conteo del vault y doctor-lite. Sin ChromaDB ni
/// servicios pesados (el oráculo lo gatea <300ms; acá es ~µs-ms).
pub fn snapshot(ctx: &ActionContext, service: Option<&SessionService>) -> HomeState {
    let t0 = Instant::now();
    let mut errores: Vec<String> = Vec::new();

    let proyecto = ctx
        .repo_root
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "cortex".to_string());
    let rama = branch_from_head(&ctx.repo_root);

    let sesion_line = active_session_line(ctx, service);
    let acciones_pendientes = match propose_count(ctx) {
        Ok(n) => n,
        Err(e) => {
            errores.push(format!("action engine: {e}"));
            0
        }
    };
    let vault_notas = count_markdown(&ctx.vault_path());

    let config_ok = ctx.config_existe();
    let mut doctor_items: Vec<(String, String)> = vec![
        (
            "config".into(),
            if config_ok {
                "✓".into()
            } else {
                "✗".into()
            },
        ),
        (
            "git".into(),
            if ctx.repo_root.join(".git").exists() {
                "✓".into()
            } else {
                "—".into()
            },
        ),
        (
            "vault".into(),
            if ctx.vault_path().is_dir() {
                "✓".into()
            } else {
                "—".into()
            },
        ),
    ];
    if !config_ok {
        doctor_items.push(("init".into(), "pendiente — corré `cortex init`".into()));
    }

    HomeState {
        proyecto,
        rama,
        sesion_line,
        acciones_pendientes,
        vault_notas,
        doctor_items,
        errores,
        elapsed_ms: t0.elapsed().as_millis() as u16,
        lang: lang(),
    }
}

/// Línea de sesión activa: la sesión abierta más reciente (como el oráculo:
/// `{id} · OPEN · N checkpoints`).
fn active_session_line(ctx: &ActionContext, service: Option<&SessionService>) -> Option<String> {
    let active = match service {
        Some(s) => s.get_active(),
        None => ctx.sesiones_abiertas().into_iter().next(),
    };
    active.map(|r| {
        format!(
            "{} · {} · {} checkpoints",
            r.session_id,
            r.status.as_str().to_uppercase(),
            r.checkpoints.len()
        )
    })
}

/// Cuenta de acciones que el scheduler propondría (misma pipeline que
/// `cortex next`; las precondiciones shallow corren, sin deep checks).
fn propose_count(ctx: &ActionContext) -> Result<usize, String> {
    let registry = build_default_registry(ctx);
    let prefs = PreferencesStore::new(&ctx.dot_cortex());
    let scheduler = Scheduler::new(&prefs);
    // El scheduler no pide config; el Home muestra el error de config en
    // el doctor-lite. Propose vacío ⇒ 0 pendientes.
    Ok(scheduler.propose(&registry, false).len())
}

/// Rama actual leyendo `.git/HEAD` (sin subprocess — el oráculo usaba git).
pub fn branch_from_head(repo_root: &Path) -> Option<String> {
    let head = repo_root.join(".git").join("HEAD");
    let text = std::fs::read_to_string(head).ok()?;
    let t = text.trim();
    t.strip_prefix("ref: refs/heads/")
        .map(|rest| rest.to_string()) // detached: no mostramos un hash crudo
}

/// Cuenta archivos .md bajo `dir` (recursivo, sin deps).
pub fn count_markdown(dir: &Path) -> usize {
    fn walk(d: &Path, acc: &mut usize) {
        let Ok(rd) = std::fs::read_dir(d) else {
            return;
        };
        for e in rd.flatten() {
            let p = e.path();
            if p.is_dir() {
                walk(&p, acc);
            } else if p.extension().is_some_and(|x| x == "md") {
                *acc += 1;
            }
        }
    }
    let mut n = 0;
    walk(dir, &mut n);
    n
}

/// Etiquetas del chrome (i18n ES/EN, espejo de action_engine etiquetas).
fn etiquetas(lang: &str) -> [(&'static str, &'static str); 4] {
    match lang {
        "en" => [
            ("session", "session"),
            ("pending", "pending"),
            ("vault", "vault"),
            ("health", "health"),
        ],
        _ => [
            ("sesión", "sesión"),
            ("pendiente", "pendiente"),
            ("vault", "vault"),
            ("salud", "salud"),
        ],
    }
}

fn hints(lang: &str) -> Vec<(&'static str, &'static str)> {
    match lang {
        "en" => vec![
            ("a", "actions"),
            ("s", "session"),
            ("/", "search"),
            ("?", "help"),
            ("q", "quit"),
        ],
        _ => vec![
            ("a", "acciones"),
            ("s", "sesión"),
            ("/", "buscar"),
            ("?", "ayuda"),
            ("q", "salir"),
        ],
    }
}

/// Latencia del snapshot como mensaje efímero de la status bar.
fn snapshot_notification(elapsed_ms: u16) -> Notification {
    Notification {
        text: format!("snapshot {elapsed_ms}ms"),
        kind: StatusKind::Pending,
        expires_at_tick: 0,
    }
}

/// Renderiza el Home completo (header con mark + panel de estado + hints).
pub fn render(f: &mut Frame<'_>, state: &HomeState) {
    let area = f.area();
    if layout_mode(area) == LayoutMode::TooSmall {
        crate::layout::render_too_small(f, state.lang);
        return;
    }
    let theme = Theme::new(env_color_mode());

    let [header, body, footer] = Layout::vertical([
        Constraint::Length(6),
        Constraint::Min(3),
        Constraint::Length(1),
    ])
    .areas(area);

    render_header(f, header, &theme);

    let et = etiquetas(state.lang);
    let mut lines: Vec<ratatui::text::Line<'_>> = Vec::new();
    let kv = |k: &str, v: String| {
        ratatui::text::Line::from(vec![
            ratatui::text::Span::styled(format!("{k:<11}"), theme.shortcut_key()),
            ratatui::text::Span::styled(v, theme.body()),
        ])
    };
    lines.push(kv(
        et[0].0,
        state
            .sesion_line
            .clone()
            .unwrap_or_else(|| ninguno(state.lang).into()),
    ));
    lines.push(kv(
        et[1].0,
        if state.acciones_pendientes > 0 {
            format!("{} {}", state.acciones_pendientes, acciones_txt(state.lang))
        } else {
            sin_pendiente(state.lang).into()
        },
    ));
    lines.push(kv(
        et[2].0,
        format!("{} {}", state.vault_notas, notas_txt(state.lang)),
    ));
    lines.push(kv(
        et[3].0,
        state
            .doctor_items
            .iter()
            .map(|(k, v)| format!("{k}: {v}"))
            .collect::<Vec<_>>()
            .join("  "),
    ));
    for e in &state.errores {
        // Semántico: WARNING con glifo ! (spec §7.4: símbolo + texto).
        lines.push(ratatui::text::Line::from(vec![
            ratatui::text::Span::styled("AVISO      ", theme.shortcut_key()),
            ratatui::text::Span::styled(format!("! {e}"), Style::default().fg(theme.warning)),
        ]));
    }

    let title = match &state.rama {
        Some(rama) => format!(" Cortex · {} · {} ", state.proyecto, rama),
        None => format!(" Cortex · {} ", state.proyecto),
    };
    let panel = Paragraph::new(lines).block(theme.panel_block(&title, true));
    f.render_widget(panel, body);

    let hints = hints(state.lang);
    let info = snapshot_notification(state.elapsed_ms);
    f.render_widget(
        StatusBar {
            hints: &hints,
            position: None,
            message: Some(&info),
            theme: &theme,
        },
        footer,
    );
}

fn render_header(f: &mut Frame<'_>, area: ratatui::prelude::Rect, theme: &Theme) {
    // Isotipo Mark si entra (spec §8); si no, "CORTEX" como texto accesible.
    let use_mark = area.width >= crate::theme::MARK_MIN_WIDTH;
    let [logo_area, _rest] =
        Layout::horizontal([Constraint::Length(15), Constraint::Min(0)]).areas(area);
    if use_mark {
        f.render_widget(
            CortexLogo::new(LogoVariant::Mark).with_mode(env_color_mode()),
            logo_area,
        );
    } else {
        f.render_widget(
            Paragraph::new(brand_text(theme.title())).style(theme.body()),
            logo_area,
        );
    }
}

fn ninguno(lang: &str) -> &'static str {
    match lang {
        "en" => "none",
        _ => "ninguna",
    }
}

fn acciones_txt(lang: &str) -> &'static str {
    match lang {
        "en" => "suggested actions",
        _ => "acciones sugeridas",
    }
}

fn sin_pendiente(lang: &str) -> &'static str {
    match lang {
        "en" => "nothing pending",
        _ => "sin pendientes",
    }
}

fn notas_txt(lang: &str) -> &'static str {
    match lang {
        "en" => "notes",
        _ => "notas",
    }
}
