//! Pantalla Co-Pilot Dual (Opción 3) — interacción en vivo con el agente adyacente.

use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::prelude::{Buffer, Color, Frame, Line, Span, Style};
use ratatui::widgets::{Block, Borders, Paragraph};
use std::time::Instant;

use crate::herdr::HerdrAgentInfo;
use crate::screens::home::{AppRenderInfo, HomeData};
use crate::widgets::{button, panel, to_color, Button, Panel};
use cortex_branding::logo;
use cortex_branding::palette::{CYAN, DEEP, ICE, LIGHT, MUTED, SHADOW};
use cortex_branding::pixels::PixelKind;
use cortex_branding::Rgb;

#[derive(Debug, Clone)]
pub struct CopilotAreas {
    pub inject_btn: Rect,
    pub approve_btn: Rect,
    pub sync_btn: Rect,
    pub sessions_btn: Rect,
    pub brain_btn: Rect,
    pub menu_btn: Rect,
    pub header: Rect,
    pub body: Rect,
    pub footer: Rect,
    pub hovered_mouse: Option<(u16, u16)>,
}

pub fn copilot_areas(area: Rect) -> CopilotAreas {
    let [header, body, footer] = Layout::vertical([
        Constraint::Length(8),
        Constraint::Min(8),
        Constraint::Length(1),
    ])
    .areas(area);

    let inject_btn = Rect::new(area.x + 2, area.y + 4, area.width.saturating_sub(4), 3);

    let [b_r1, b_r2] = Layout::vertical([Constraint::Length(3), Constraint::Length(3)]).areas(
        Rect::new(area.x + 2, area.y + 7, area.width.saturating_sub(4), 6),
    );

    let btn_w = (area.width.saturating_sub(6) / 2).max(10);
    let approve_btn = Rect::new(area.x + 2, b_r1.y, btn_w, 3);
    let sync_btn = Rect::new(area.x + 3 + btn_w, b_r1.y, btn_w, 3);
    let sessions_btn = Rect::new(area.x + 2, b_r2.y, btn_w, 3);
    let brain_btn = Rect::new(area.x + 3 + btn_w, b_r2.y, btn_w, 3);
    let menu_btn = Rect::new(area.x + 2, footer.y, area.width.saturating_sub(4), 1);

    CopilotAreas {
        inject_btn,
        approve_btn,
        sync_btn,
        sessions_btn,
        brain_btn,
        menu_btn,
        header,
        body,
        footer,
        hovered_mouse: None,
    }
}

pub fn render_copilot(
    f: &mut Frame<'_>,
    area: Rect,
    data: &HomeData,
    agent_info: &Option<HerdrAgentInfo>,
    areas: &mut CopilotAreas,
) -> AppRenderInfo {
    let t0 = Instant::now();

    // 1. Header con Logo Voxel 3D e información de conexión
    blit_mini_voxel_logo(f.buffer_mut(), Rect::new(area.x + 2, area.y, 8, 4));

    let title_line = Line::from(vec![
        Span::styled(
            " CORTEX CO-PILOT",
            Style::default()
                .fg(to_color(CYAN))
                .add_modifier(ratatui::style::Modifier::BOLD),
        ),
        Span::raw(" "),
        Span::styled("· DUAL RUNTIME", Style::default().fg(to_color(MUTED))),
    ]);
    f.render_widget(
        Paragraph::new(title_line),
        Rect::new(area.x + 11, area.y, area.width.saturating_sub(13).max(1), 1),
    );

    let agent_line = match agent_info {
        Some(a) => Line::from(vec![
            Span::styled("● VINCULADO: ", Style::default().fg(Color::Green)),
            Span::styled(
                format!(
                    "{} ({})",
                    a.agent.as_deref().unwrap_or("terminal"),
                    a.pane_id
                ),
                Style::default()
                    .fg(to_color(ICE))
                    .add_modifier(ratatui::style::Modifier::BOLD),
            ),
            Span::styled(
                format!(" [{}]", data.project),
                Style::default().fg(to_color(MUTED)),
            ),
        ]),
        None => Line::from(vec![
            Span::styled("○ AGENTE: ", Style::default().fg(to_color(MUTED))),
            Span::styled(
                "Standalone (sin agente adyacente)",
                Style::default().fg(to_color(MUTED)),
            ),
        ]),
    };
    f.render_widget(
        Paragraph::new(agent_line),
        Rect::new(
            area.x + 11,
            area.y + 1,
            area.width.saturating_sub(13).max(1),
            1,
        ),
    );

    // 2. Barra de fases
    let phase_line = Line::from(vec![
        Span::styled("FASES: ", Style::default().fg(to_color(MUTED))),
        Span::styled("1.SPEC", Style::default().fg(to_color(MUTED))),
        Span::styled(" ➔ ", Style::default().fg(to_color(MUTED))),
        Span::styled("2.PLAN", Style::default().fg(to_color(MUTED))),
        Span::styled(" ➔ ", Style::default().fg(to_color(MUTED))),
        Span::styled(
            "▶ 3.IMPLEMENTACIÓN",
            Style::default()
                .fg(to_color(CYAN))
                .add_modifier(ratatui::style::Modifier::BOLD),
        ),
        Span::styled(" ➔ ", Style::default().fg(to_color(MUTED))),
        Span::styled("4.VERIFICACIÓN", Style::default().fg(to_color(MUTED))),
    ]);
    f.render_widget(
        Paragraph::new(phase_line),
        Rect::new(
            area.x + 2,
            area.y + 3,
            area.width.saturating_sub(4).max(1),
            1,
        ),
    );

    // 3. Botón de Inyección
    let is_inject_hovered = areas.hovered_mouse.is_some_and(|(mx, my)| {
        areas
            .inject_btn
            .contains(ratatui::layout::Position::new(mx, my))
    });

    let inject_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(if is_inject_hovered {
            to_color(ICE)
        } else {
            to_color(CYAN)
        }));

    let inject_label = Line::from(vec![Span::styled(
        "  [ENTER] Copiar prompt para el agente ",
        Style::default()
            .fg(if is_inject_hovered {
                to_color(ICE)
            } else {
                to_color(CYAN)
            })
            .add_modifier(ratatui::style::Modifier::BOLD),
    )]);
    f.render_widget(
        Paragraph::new(inject_label).block(inject_block),
        areas.inject_btn,
    );

    // 4. Paneles de datos
    let [p_prompt, p_action, p_session, _] = Layout::vertical([
        Constraint::Length(5),
        Constraint::Length(4),
        Constraint::Length(4),
        Constraint::Min(0),
    ])
    .areas(areas.body);

    let prompt_text = data
        .top_action
        .as_ref()
        .map(|a| format!("Ejecutar acción: {}", a.title))
        .unwrap_or_else(|| "Esperando propuesta de cortex next...".into());

    panel(
        f,
        &Panel {
            title: "instrucción sugerida".into(),
            rect: p_prompt,
        },
        vec![
            Line::from(vec![Span::styled(
                format!("\"{}\"", prompt_text),
                Style::default().fg(to_color(ICE)),
            )]),
            Line::from(vec![Span::styled(
                "Presioná Enter para copiar. Nunca se pega al agente.",
                Style::default().fg(to_color(MUTED)),
            )]),
        ],
        to_color(CYAN),
    );

    panel(
        f,
        &Panel {
            title: "próxima acción".into(),
            rect: p_action,
        },
        vec![Line::from(vec![Span::styled(
            data.top_action
                .as_ref()
                .map(|a| a.title.as_str())
                .unwrap_or("Sin acciones pendientes"),
            Style::default().fg(to_color(CYAN)),
        )])],
        to_color(CYAN),
    );

    panel(
        f,
        &Panel {
            title: "sesión & telemetría".into(),
            rect: p_session,
        },
        vec![Line::from(vec![
            Span::raw("id: "),
            Span::styled(
                data.session
                    .as_ref()
                    .map(|s| s.id.as_str())
                    .unwrap_or("ninguna"),
                Style::default().fg(to_color(ICE)),
            ),
            Span::raw("  ·  doctor: "),
            Span::styled("OK", Style::default().fg(Color::Green)),
        ])],
        to_color(CYAN),
    );

    // 5. Botones secundarios
    let buttons = vec![
        Button {
            id: "inject-prompt",
            rect: areas.inject_btn,
            label: "Copiar prompt".into(),
            enabled: true,
        },
        Button {
            id: "copilot-approve",
            rect: areas.approve_btn,
            label: "⚡ Aprobar (A)".into(),
            enabled: data.top_action.is_some(),
        },
        Button {
            id: "copilot-sync",
            rect: areas.sync_btn,
            label: "🔄 Sincronizar (S)".into(),
            enabled: true,
        },
        Button {
            id: "sessions",
            rect: areas.sessions_btn,
            label: "Sesiones (1)".into(),
            enabled: true,
        },
        Button {
            id: "brain",
            rect: areas.brain_btn,
            label: "Brain (B)".into(),
            enabled: true,
        },
    ];

    let hovered = areas.hovered_mouse.and_then(|(mx, my)| {
        buttons
            .iter()
            .find(|b| b.rect.contains(ratatui::layout::Position::new(mx, my)))
            .map(|b| b.id)
    });

    for b in &buttons[1..] {
        button(f, b, hovered == Some(b.id));
    }

    // 6. Footer
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("▸ Brain (Tab)", Style::default().fg(to_color(CYAN))),
            Span::styled(
                "  ·  Enter copia el prompt  ·  A Aprobar  ·  q salir",
                Style::default().fg(to_color(MUTED)),
            ),
        ])),
        areas.footer,
    );

    AppRenderInfo {
        buttons,
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}

fn blit_mini_voxel_logo(buf: &mut Buffer, area: Rect) {
    let mark = logo::mark();
    let (mw, mh) = (mark.w() as u16, mark.h() as u16);
    let cells = (mh as usize).div_ceil(2);
    for cy in 0..cells.min(area.height as usize) {
        let py_top = cy * 2;
        let py_bottom = py_top + 1;
        for px in 0..mw.min(area.width) {
            let top = mark.get(px as usize, py_top);
            let bottom = if py_bottom < mh as usize {
                mark.get(px as usize, py_bottom)
            } else {
                PixelKind::Transparent
            };
            let c_top = color_for_kind(top);
            let c_bottom = color_for_kind(bottom);
            let cell = buf.cell_mut((area.x + px, area.y + cy as u16));
            let Some(cell) = cell else { continue };
            paint_half_block(cell, c_top, c_bottom);
        }
    }
}

fn color_for_kind(k: PixelKind) -> Option<Rgb> {
    match k {
        PixelKind::Highlight => Some(ICE),
        PixelKind::Cross => Some(LIGHT),
        PixelKind::Mark => Some(CYAN),
        PixelKind::Layer => Some(DEEP),
        PixelKind::Shadow => Some(SHADOW),
        PixelKind::Transparent => None,
    }
}

fn paint_half_block(cell: &mut ratatui::buffer::Cell, top: Option<Rgb>, bottom: Option<Rgb>) {
    match (top, bottom) {
        (None, None) => {}
        (Some(t), None) => {
            cell.set_symbol("▀");
            cell.set_fg(to_color(t));
        }
        (None, Some(b)) => {
            cell.set_symbol("▄");
            cell.set_fg(to_color(b));
        }
        (Some(t), Some(b)) if t == b => {
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
