//! Home de Cortex en ratatui — espejo de `cortex/tui/core.py` (Obra 05 Fase D).
//!
//! `HomeState` replica campo a campo el snapshot barato del Home Python; el
//! cableado a servicios reales (sessions/acciones/vault vía cortex-app)
//! llega con P4-P6 del plan 08. Mientras tanto `demo_state()` provee datos
//! de muestra para el gate P10: snapshot render + latencia <50ms.

use crate::renderer::CortexLogo;
use crate::{env_color_mode, lang, LogoVariant};
use cortex_branding::palette;
use ratatui::prelude::{Color, Constraint, Layout, Rect, Style};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;

/// Presupuesto de render del Home (gate P10: "Home <50ms").
pub const RENDER_BUDGET_MS: u128 = 50;

/// Estado del Home — espejo de `HomeState` en cortex/tui/core.py.
#[derive(Clone, Debug, Default)]
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

fn hints(lang: &str) -> &'static str {
    match lang {
        "en" => "a=actions  s=session  /=search  q=quit",
        _ => "a=acciones  s=sesión  /=buscar  q=salir",
    }
}

/// Renderiza el Home completo (header con mark + panel de estado + hints).
pub fn render(f: &mut Frame<'_>, state: &HomeState) {
    let area = f.area();
    let [header, body, footer] = Layout::vertical([
        Constraint::Length(6),
        Constraint::Min(3),
        Constraint::Length(1),
    ])
    .areas(area);

    render_header(f, header, state);

    let et = etiquetas(state.lang);
    let cyan = palette_color(palette::CYAN);
    let muted = palette_color(palette::MUTED);
    let text = palette_color(palette::TEXT);
    let warn = Color::Rgb(0xF0, 0xD9, 0x62); // ámbar solo para avisos (fuera de paleta de marca)

    let mut lines: Vec<ratatui::text::Line<'_>> = Vec::new();
    let kv = |k: &str, v: String| {
        ratatui::text::Line::from(vec![
            ratatui::text::Span::styled(format!("{k:<11}"), Style::default().fg(cyan)),
            ratatui::text::Span::styled(v, Style::default().fg(text)),
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
        lines.push(kv("AVISO", e.clone()).style(Style::default().fg(warn)));
    }

    let title = match &state.rama {
        Some(rama) => format!(" Cortex · {} · {} ", state.proyecto, rama),
        None => format!(" Cortex · {} ", state.proyecto),
    };
    let panel = Paragraph::new(lines).block(
        Block::bordered()
            .title(title)
            .border_style(Style::default().fg(cyan)),
    );
    f.render_widget(panel, body);

    let footer_line = ratatui::text::Line::from(vec![
        ratatui::text::Span::styled(hints(state.lang), Style::default().fg(muted)),
        ratatui::text::Span::styled(
            format!("  · snapshot {}ms", state.elapsed_ms),
            Style::default().fg(muted),
        ),
    ]);
    f.render_widget(Paragraph::new(footer_line), footer);
}

fn render_header(f: &mut Frame<'_>, area: Rect, state: &HomeState) {
    let [logo_area, _rest] =
        Layout::horizontal([Constraint::Length(15), Constraint::Min(0)]).areas(area);
    f.render_widget(
        CortexLogo::new(LogoVariant::Mark).with_mode(env_color_mode()),
        logo_area,
    );
    // El título del panel ya identifica proyecto/rama; el mark da identidad.
    let _ = state;
}

fn palette_color(c: palette::Rgb) -> Color {
    crate::renderer::to_ratatui(c, env_color_mode())
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
