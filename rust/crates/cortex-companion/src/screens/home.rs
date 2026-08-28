//! Pantalla Home del Companion (G-B2b): sesión activa, próxima acción,
//! doctor-lite y conteos de memoria sobre la identidad `cortex-branding`.
//!
//! El Home es snapshot barato (gate P10 <50ms): render puro sobre `HomeData`
//! que el binario carga de los backends. El render NUNCA muta estado.

use std::time::Instant;

use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::prelude::{Buffer, Color};
use ratatui::style::Style;
use ratatui::text::{Line, Span};
use ratatui::Frame;

use cortex_branding::gradient::color_for;
use cortex_branding::pixels::PixelKind;
use cortex_branding::wordmark;

use crate::app::{HOME_ACTIONS_BTN, HOME_MENU_BTN, HOME_OPEN_SESSION_BTN, HOME_SESSIONS_BTN};
use crate::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary};
use crate::widgets::{accent, button, panel, to_color, Button, Panel};

/// Datos que Home muestra (los cargan los backends en el binario).
#[derive(Debug, Clone, Default)]
pub struct HomeData {
    pub project: String,
    pub branch: Option<String>,
    pub session: Option<SessionSummary>,
    pub top_action: Option<ActionProposal>,
    pub doctor: Option<DoctorSummary>,
    pub stats: Option<StatsSummary>,
    /// Error global de carga (p. ej. proyecto sin config.yaml): se muestra en
    /// el panel de acciones para nunca fallar en silencio (patrón P6/P9).
    pub error: Option<String>,
}

/// Áreas del Home: botones hit-testables (consts de `app.rs`, idénticas a la
/// del `hit_test`) + layout derivado del área disponible + posición del mouse
/// para hover (el binario la setea antes de cada draw).
#[derive(Debug, Clone)]
pub struct HomeAreas {
    pub sessions_btn: Rect,
    pub actions_btn: Rect,
    pub open_session_btn: Option<Rect>,
    pub menu_btn: Rect,
    pub header: Rect,
    pub body: Rect,
    pub footer: Rect,
    pub hovered_mouse: Option<(u16, u16)>,
}

/// Rects canónicas del Home (ver doc de cada campo).
pub fn home_areas(area: Rect) -> HomeAreas {
    let [header, body, footer] = Layout::vertical([
        Constraint::Length(8),
        Constraint::Min(4),
        Constraint::Length(1),
    ])
    .areas(area);
    HomeAreas {
        sessions_btn: HOME_SESSIONS_BTN,
        actions_btn: HOME_ACTIONS_BTN,
        open_session_btn: Some(HOME_OPEN_SESSION_BTN),
        menu_btn: HOME_MENU_BTN,
        header,
        body,
        footer,
        hovered_mouse: None,
    }
}

/// Resultado del render: botones registrados (para el hit-test del frame) y
/// presupuesto medido.
#[derive(Debug, Clone)]
pub struct AppRenderInfo {
    pub buttons: Vec<Button>,
    pub spent_ms: f32,
}

/// Marca de branding (seam del plan; los pixel-maps son estáticos del crate).
#[derive(Debug, Clone, Copy, Default)]
pub struct BrandAssets;

impl BrandAssets {
    pub fn load() -> Self {
        Self
    }
}

fn rgb_eq(a: cortex_branding::palette::Rgb, b: cortex_branding::palette::Rgb) -> bool {
    a.0 == b.0 && a.1 == b.1 && a.2 == b.2
}

/// Pinta el wordmark con half-blocks directamente al Buffer (mismo algoritmo
/// que `ansi::render_ansi`: '▀' fg=top / '▄' fg=bottom / '█' fg=bg-igual,
/// siempre con la paleta oficial vía `gradient::color_for`).
fn blit_wordmark(buf: &mut Buffer, area: Rect) {
    let wm = wordmark::wordmark();
    let (w, h) = (wm.w() as u16, wm.h() as u16);
    let cells = (h as usize).div_ceil(2);
    for cy in 0..cells.min(area.height as usize) {
        let py_top = cy * 2;
        let py_bottom = py_top + 1;
        for px in 0..w.min(area.width) {
            let top = wm.get(px as usize, py_top);
            let bottom = if py_bottom < h as usize {
                wm.get(px as usize, py_bottom)
            } else {
                PixelKind::Transparent
            };
            let c_top = color_for(top, py_top, h as usize);
            let c_bottom = color_for(bottom, py_bottom, h as usize);
            let cell = buf.cell_mut((area.x + px, area.y + cy as u16));
            let Some(cell) = cell else { continue };
            match (c_top, c_bottom) {
                (None, None) => {}
                (Some(t), None) => {
                    cell.set_symbol("▀");
                    cell.set_fg(to_color(t));
                }
                (None, Some(b)) => {
                    cell.set_symbol("▄");
                    cell.set_fg(to_color(b));
                }
                (Some(t), Some(b)) if rgb_eq(t, b) => {
                    cell.set_symbol("█");
                    cell.set_fg(to_color(t));
                }
                (Some(t), Some(b)) => {
                    cell.set_symbol("▀");
                    cell.set_fg(to_color(t));
                    cell.set_bg(to_color(b));
                }
            }
        }
    }
}

/// Línea de estado de la sesión con color según status.
fn session_lines(data: &HomeData) -> Vec<Line<'static>> {
    match &data.session {
        Some(s) => vec![Line::from(vec![
            Span::styled(
                "id:  ",
                Style::default().fg(to_color(cortex_branding::palette::MUTED)),
            ),
            Span::styled(s.id.clone(), accent_style()),
            Span::raw("  "),
            Span::styled(s.status.clone(), status_color(&s.status)),
            Span::raw("  mode: "),
            Span::styled(s.mode.clone(), accent_style()),
        ])],
        None => vec![Line::from(
            "No hay sesión activa — abrí una desde Sesiones.",
        )],
    }
}

fn accent_style() -> Style {
    Style::default().fg(to_color(cortex_branding::palette::CYAN))
}

fn status_color(status: &str) -> Style {
    if status.eq_ignore_ascii_case("open") {
        Style::default().fg(to_color(cortex_branding::palette::ICE))
    } else {
        Style::default().fg(to_color(cortex_branding::palette::MUTED))
    }
}

fn next_action_lines(data: &HomeData) -> Vec<Line<'static>> {
    if let Some(err) = &data.error {
        return vec![Line::from(vec![Span::styled(
            format!("⚠ {err}"),
            Style::default().fg(Color::Red),
        )])];
    }
    match &data.top_action {
        Some(a) => vec![Line::from(vec![
            Span::styled(a.title.clone(), accent_style()),
            Span::raw("  "),
            Span::styled(format!("score {:.2} · {}", a.score, a.cost), muted_style()),
        ])],
        None => vec![Line::from(
            "Sin propuestas — corré `cortex next` para ver el motor.",
        )],
    }
}

fn muted_style() -> Style {
    Style::default().fg(to_color(cortex_branding::palette::MUTED))
}

fn verdict_style(v: &str) -> Style {
    match v {
        "ok" => Style::default().fg(Color::Green),
        "fail" => Style::default().fg(Color::Red),
        _ => Style::default().fg(Color::Yellow),
    }
}

fn doctor_lines(doctor: &Option<DoctorSummary>) -> Vec<Line<'static>> {
    match doctor {
        Some(d) if !d.checks.is_empty() => d
            .checks
            .iter()
            .map(|(name, verdict)| {
                Line::from(vec![
                    Span::raw(format!("{name}: ")),
                    Span::styled(
                        format!("[{}]", verdict.to_uppercase()),
                        verdict_style(verdict),
                    ),
                ])
            })
            .collect(),
        _ => vec![Line::from(
            "doctor: sin checks locales (proyecto sin config?)",
        )],
    }
}

fn stats_lines(stats: &Option<StatsSummary>) -> Vec<Line<'static>> {
    match stats {
        Some(s) => vec![Line::from(vec![
            Span::styled(format!("episódica {}", s.episodic), accent_style()),
            Span::raw("  ·  "),
            Span::styled(format!("semántica {}", s.semantic), accent_style()),
            Span::raw(format!("  ·  {}", s.vault_path)),
        ])],
        None => vec![Line::from("memoria: sín indices cargados")],
    }
}

/// Botones del Home, coherentes con `hit_test` (mismas consts).
fn home_buttons(data: &HomeData, areas: &HomeAreas) -> Vec<Button> {
    let mut buttons = vec![
        Button {
            id: "sessions",
            rect: areas.sessions_btn,
            label: "Sesiones".into(),
            enabled: true,
        },
        Button {
            id: "view-actions",
            rect: areas.actions_btn,
            label: "Ver acciones".into(),
            enabled: true,
        },
        Button {
            id: "menu-nav",
            rect: areas.menu_btn,
            label: "Menú".into(),
            enabled: true,
        },
    ];
    if data.session.is_none() {
        if let Some(rect) = areas.open_session_btn {
            buttons.push(Button {
                id: "open-session",
                rect,
                label: "Abrir sesión".into(),
                enabled: true,
            });
        }
    }
    buttons
}

fn hovered_button_id(buttons: &[Button], mouse: Option<(u16, u16)>) -> Option<&'static str> {
    let (x, y) = mouse?;
    buttons
        .iter()
        .find(|b| b.rect.contains(ratatui::layout::Position::new(x, y)))
        .map(|b| b.id)
}

/// Renderiza el Home completo. Presupuesto: <50 ms (gate P10 pattern).
pub fn render_home(
    f: &mut Frame<'_>,
    area: Rect,
    data: &HomeData,
    _brand: &BrandAssets,
    areas: &mut HomeAreas,
) -> AppRenderInfo {
    let t0 = Instant::now();

    // Header: wordmark + botones nav (renglón 4-6) + línea de contexto
    // (renglón 7, plana — un panel de h1 se lo comen los bordes).
    blit_wordmark(f.buffer_mut(), Rect::new(area.x + 2, area.y, 35, 4));
    let info_line = format!(
        "{}  {}",
        data.project,
        data.branch
            .as_deref()
            .map(|b| format!("· {b}"))
            .unwrap_or_default()
    );
    f.render_widget(
        ratatui::widgets::Paragraph::new(Line::from(vec![Span::styled(info_line, muted_style())])),
        Rect::new(
            area.x + 2,
            area.y + 7,
            area.width.saturating_sub(4).max(1),
            1,
        ),
    );

    let buttons = home_buttons(data, areas);
    let hovered = hovered_button_id(&buttons, areas.hovered_mouse);
    for b in &buttons {
        button(f, b, hovered == Some(b.id));
    }

    // Body: 2×2 de paneles (sesión/acción, salud/memoria).
    let [row1, row2, _rest] = Layout::vertical([
        Constraint::Length(5),
        Constraint::Length(5),
        Constraint::Min(1),
    ])
    .areas(areas.body);
    let [left1, right1] =
        Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)]).areas(row1);
    let [left2, right2] =
        Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)]).areas(row2);

    panel(
        f,
        &Panel {
            title: "sesión".into(),
            rect: left1,
        },
        session_lines(data),
        accent(),
    );
    panel(
        f,
        &Panel {
            title: "próxima acción".into(),
            rect: right1,
        },
        next_action_lines(data),
        accent(),
    );
    panel(
        f,
        &Panel {
            title: "salud".into(),
            rect: left2,
        },
        doctor_lines(&data.doctor),
        accent(),
    );
    panel(
        f,
        &Panel {
            title: "memoria".into(),
            rect: right2,
        },
        stats_lines(&data.stats),
        accent(),
    );

    // Footer: hints.
    f.render_widget(
        ratatui::widgets::Paragraph::new(Line::from(Span::styled(
            "mouse: clic navega · rueda scrollea · q/Ctrl+C salir · / buscar",
            muted_style(),
        ))),
        areas.footer,
    );

    AppRenderInfo {
        buttons,
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
