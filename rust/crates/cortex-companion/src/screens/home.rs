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
use cortex_branding::logo;
use cortex_branding::pixels::PixelKind;
use cortex_branding::wordmark;
use cortex_branding::Rgb;

use crate::app::{
    HOME_ACTIONS_BTN, HOME_BRAIN_BTN, HOME_MENU_BTN, HOME_OPEN_SESSION_BTN, HOME_SESSIONS_BTN,
};
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
    /// Prompt copiable del HUD (doc 17). Vacío ⇒ `hud_prompt` lo deriva.
    pub prompt: String,
    /// Higiene que el HUD puede aprobar (nunca ciclo de sesión).
    pub hygiene: Option<ActionProposal>,
    /// Etiqueta del agente adyacente ("pi idle") o vacío.
    pub agent_label: String,
    /// Texto en el campo de consulta del HUD.
    pub ask: String,
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
    /// Acceso a Brain en el footer (rect de hit-test del span pintado por
    /// `render_home`; NO es un `Button` con bordes: el footer mide 1 fila y
    /// `Borders::ALL` se comería la etiqueta — lección de geometría B7).
    pub brain_btn: Rect,
    pub header: Rect,
    pub body: Rect,
    pub footer: Rect,
    pub hovered_mouse: Option<(u16, u16)>,
}

/// Rects canónicas del Home (ver doc de cada campo).
pub fn home_areas(area: Rect) -> HomeAreas {
    if area.width < 50 {
        let [header, body, footer] = Layout::vertical([
            Constraint::Length(12),
            Constraint::Min(4),
            Constraint::Length(1),
        ])
        .areas(area);
        let btn_w = (area.width.saturating_sub(6) / 2).max(10);
        let sessions_btn = Rect::new(area.x + 2, area.y + 5, btn_w, 3);
        let actions_btn = Rect::new(area.x + 3 + btn_w, area.y + 5, btn_w, 3);
        let menu_btn = Rect::new(area.x + 2, area.y + 8, btn_w, 3);
        let open_session_btn = Some(Rect::new(area.x + 3 + btn_w, area.y + 8, btn_w, 3));
        let brain_btn = Rect::new(area.x + 2, footer.y, area.width.saturating_sub(4), 1);
        HomeAreas {
            sessions_btn,
            actions_btn,
            open_session_btn,
            menu_btn,
            brain_btn,
            header,
            body,
            footer,
            hovered_mouse: None,
        }
    } else {
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
            brain_btn: HOME_BRAIN_BTN,
            header,
            body,
            footer,
            hovered_mouse: None,
        }
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

fn paint_half_block(cell: &mut ratatui::buffer::Cell, c_top: Option<Rgb>, c_bottom: Option<Rgb>) {
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

/// Pinta el Logo Voxel Isométrico a la izquierda y el Wordmark "CORTEX" en 3D
/// con caras iluminadas (ICE), cuerpo esmeralda (CYAN) y sombra 3D (DEEP).
fn blit_brand_header(buf: &mut Buffer, area: Rect) {
    let mark = logo::mark();
    let (mw, mh) = (mark.w() as u16, mark.h() as u16);
    let cells_m = (mh as usize).div_ceil(2);
    for cy in 0..cells_m.min(area.height as usize) {
        let py_top = cy * 2;
        let py_bottom = py_top + 1;
        for px in 0..mw.min(area.width) {
            let top = mark.get(px as usize, py_top);
            let bottom = if py_bottom < mh as usize {
                mark.get(px as usize, py_bottom)
            } else {
                PixelKind::Transparent
            };
            let c_top = color_for(top, py_top, mh as usize);
            let c_bottom = color_for(bottom, py_bottom, mh as usize);
            let cell = buf.cell_mut((area.x + px, area.y + cy as u16));
            let Some(cell) = cell else { continue };
            paint_half_block(cell, c_top, c_bottom);
        }
    }

    let wm_x = area.x + mw + 2;
    if area.width > (mw + 4) {
        let wm = wordmark::wordmark();
        let (ww, wh) = (wm.w() as u16, wm.h() as u16);
        let cells_w = (wh as usize).div_ceil(2);
        for cy in 0..cells_w.min(area.height as usize) {
            let py_top = cy * 2;
            let py_bottom = py_top + 1;
            for px in 0..ww.min(area.width.saturating_sub(mw + 2)) {
                let top = wm.get(px as usize, py_top);
                let bottom = if py_bottom < wh as usize {
                    wm.get(px as usize, py_bottom)
                } else {
                    PixelKind::Transparent
                };
                let c_top = color_for(top, py_top, wh as usize);
                let c_bottom = color_for(bottom, py_bottom, wh as usize);
                let cell = buf.cell_mut((wm_x + px, area.y + cy as u16));
                let Some(cell) = cell else { continue };
                paint_half_block(cell, c_top, c_bottom);
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
    let buttons = home_buttons(data, areas);
    let hovered = hovered_button_id(&buttons, areas.hovered_mouse);

    if area.width < 50 {
        // Header con Logo Voxel 3D Isométrico + "CORTEX"
        blit_brand_header(
            f.buffer_mut(),
            Rect::new(area.x + 2, area.y, area.width.saturating_sub(4), 3),
        );
        let info_line = format!(
            "{} {}",
            data.project,
            data.branch
                .as_deref()
                .map(|b| format!("· {b}"))
                .unwrap_or_default()
        );
        f.render_widget(
            ratatui::widgets::Paragraph::new(Line::from(vec![Span::styled(
                info_line,
                muted_style(),
            )])),
            Rect::new(
                area.x + 2,
                area.y + 3,
                area.width.saturating_sub(4).max(1),
                1,
            ),
        );

        for b in &buttons {
            button(f, b, hovered == Some(b.id));
        }

        // Body: paneles apilados verticalmente
        let [p_session, p_action, p_health, p_mem, _] = Layout::vertical([
            Constraint::Length(4),
            Constraint::Length(4),
            Constraint::Length(4),
            Constraint::Length(4),
            Constraint::Min(0),
        ])
        .areas(areas.body);

        panel(
            f,
            &Panel {
                title: "sesión".into(),
                rect: p_session,
            },
            session_lines(data),
            accent(),
        );
        panel(
            f,
            &Panel {
                title: "próxima acción".into(),
                rect: p_action,
            },
            next_action_lines(data),
            accent(),
        );
        panel(
            f,
            &Panel {
                title: "salud".into(),
                rect: p_health,
            },
            doctor_lines(&data.doctor),
            accent(),
        );
        panel(
            f,
            &Panel {
                title: "memoria".into(),
                rect: p_mem,
            },
            stats_lines(&data.stats),
            accent(),
        );
    } else {
        // Header: Logo Voxel + Wordmark 3D + botones nav + línea de contexto
        blit_brand_header(f.buffer_mut(), Rect::new(area.x + 2, area.y, 50, 4));
        let info_line = format!(
            "{}  {}",
            data.project,
            data.branch
                .as_deref()
                .map(|b| format!("· {b}"))
                .unwrap_or_default()
        );
        f.render_widget(
            ratatui::widgets::Paragraph::new(Line::from(vec![Span::styled(
                info_line,
                muted_style(),
            )])),
            Rect::new(
                area.x + 2,
                area.y + 7,
                area.width.saturating_sub(4).max(1),
                1,
            ),
        );

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
            Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)])
                .areas(row1);
        let [left2, right2] =
            Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)])
                .areas(row2);

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
    }

    // Footer: acceso a Brain (clic/Tab) + hints. El span del acceso es lo
    // que pisa el ratón dentro de `HOME_BRAIN_BTN` (misma geometría que
    // `hit_test`).
    let brain_hovered = areas.hovered_mouse.is_some_and(|(mx, my)| {
        areas
            .brain_btn
            .contains(ratatui::layout::Position::new(mx, my))
    });
    f.render_widget(
        ratatui::widgets::Paragraph::new(Line::from(vec![
            Span::styled(
                "▸ brain (clic o Tab)",
                accent_style().add_modifier(if brain_hovered {
                    ratatui::style::Modifier::BOLD
                } else {
                    ratatui::style::Modifier::empty()
                }),
            ),
            Span::styled(
                "  ·  clic navega · rueda scrollea · q/Ctrl+C salir · / buscar",
                muted_style(),
            ),
        ])),
        areas.footer,
    );

    AppRenderInfo {
        buttons,
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
