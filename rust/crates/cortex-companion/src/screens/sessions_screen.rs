//! Pantalla Sessions del Companion (G-B3 UI): lista en vivo de sesiones,
//! click en fila ⇒ detalle (checkpoints/tasks), y [Cerrar sesión] que SIEMPRE
//! pasa por el modal de aprobación (`run_guarded`, B2). El render es puro
//! sobre `SessionsData`; la carga de datos la hace el runtime.
//!
//! Geometría COMPARTIDA con `hit_test` (consts de `app.rs`): render y
//! hit-test no pueden divergir.

use std::time::Instant;

use ratatui::layout::{Position, Rect};
use ratatui::prelude::{Line, Style};
use ratatui::text::Span;
use ratatui::widgets::Paragraph;
use ratatui::Frame;


use crate::app::{
    SessionsData, SESSIONS_CLOSE_BTN, SESSIONS_DETAIL, SESSIONS_LIST_HEIGHT, SESSIONS_LIST_LEFT,
    SESSIONS_LIST_TOP, SESSIONS_LIST_WIDTH, SESSIONS_OUTCOME,
};
use crate::widgets::{button, Button};

/// Áreas de Sessions: lista, botón cerrar, detalle y salida — MISMA
/// geometría que `hit_test`.
#[derive(Debug, Clone)]
pub struct SessionsAreas {
    pub list: Rect,
    pub close_btn: Rect,
    pub detail: Rect,
    pub outcome: Rect,
    /// Posición del mouse para hover (el binario la setea antes de cada draw).
    pub hover_mouse: Option<(u16, u16)>,
}

/// Deriva las áreas desde las consts del hit-test (coherencia estructural).
pub fn sessions_areas(_area: Rect) -> SessionsAreas {
    SessionsAreas {
        list: Rect::new(
            SESSIONS_LIST_LEFT,
            SESSIONS_LIST_TOP,
            SESSIONS_LIST_WIDTH,
            SESSIONS_LIST_HEIGHT,
        ),
        close_btn: SESSIONS_CLOSE_BTN,
        detail: SESSIONS_DETAIL,
        outcome: SESSIONS_OUTCOME,
        hover_mouse: None,
    }
}

/// Resultado del render (botones del frame + presupuesto medido).
#[derive(Debug, Clone)]
pub struct SessionsRenderInfo {
    pub buttons: Vec<Button>,
    pub spent_ms: f32,
}

fn accent_style() -> Style {
    Style::default().fg(crate::theme::accent())
}

fn muted_style_raw() -> Style {
    Style::default().fg(crate::theme::text_muted())
}

fn status_style(status: &str) -> Style {
    if status.eq_ignore_ascii_case("open") {
        Style::default().fg(crate::theme::success())
    } else {
        Style::default().fg(crate::theme::text_muted())
    }
}

/// Una fila por sesión visible (ventana por scroll); la seleccionada va en
/// acento bold. `id` recortado a 44 columnas para no pisar la columna status.
fn session_line(data: &SessionsData, i: usize) -> Line<'static> {
    let s = &data.sessions[i];
    let selected = data.selected == Some(i);
    let id = s.id.chars().take(44).collect::<String>();
    let style = if selected {
        accent_style().add_modifier(ratatui::style::Modifier::BOLD)
    } else {
        Style::default()
    };
    Line::from(vec![
        Span::styled(format!("  {id:<44} "), style),
        Span::styled(format!("{:<10} ", s.status), status_style(&s.status)),
        Span::styled(format!("{:<9} ", s.mode), muted_style_raw()),
        Span::styled(s.opened_at.clone(), muted_style_raw()),
    ])
}

/// Renderiza Sessions (presupuesto <50 ms, patrón P10).
pub fn render_sessions(
    f: &mut Frame<'_>,
    area: Rect,
    data: &SessionsData,
    scroll: u16,
    areas: &mut SessionsAreas,
) -> SessionsRenderInfo {
    let t0 = Instant::now();

    // Encabezado.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Cortex — sesiones", accent_style()),
            Span::styled(
                "   (clic selecciona · cerrar pide aprobación)",
                muted_style_raw(),
            ),
        ])),
        Rect::new(area.x + 2, area.y, area.width.saturating_sub(4).max(1), 1),
    );

    // Error de carga visible, nunca silencio (P6/P9).
    if let Some(err) = &data.error {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                format!("⚠ {err}"),
                Style::default().fg(crate::theme::error()),
            ))),
            Rect::new(
                area.x + 2,
                area.y + 1,
                area.width.saturating_sub(4).max(1),
                1,
            ),
        );
    }

    // Lista de sesiones (ventana por scroll).
    for i in 0..data.sessions.len() {
        let y = i32::from(areas.list.y) + i as i32 - i32::from(scroll);
        if y < i32::from(areas.list.y) || y >= i32::from(areas.list.y + areas.list.height) {
            continue;
        }
        f.render_widget(
            Paragraph::new(session_line(data, i)),
            Rect::new(areas.list.x, y as u16, areas.list.width, 1),
        );
    }
    if data.sessions.is_empty() && data.error.is_none() {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "sin sesiones — `cortex create-spec` abre la primera",
                muted_style_raw(),
            ))),
            areas.list,
        );
    }

    // Botón [Cerrar sesión]: habilitado solo con selección (misma regla que
    // hit_test). Hover por el mouse actual.
    let enabled = data.selected.is_some();
    let close_btn = Button {
        id: "close-session",
        rect: areas.close_btn,
        label: "Cerrar sesión".into(),
        enabled,
    };
    let hovered = enabled
        && areas
            .hover_mouse
            .is_some_and(|(x, y)| areas.close_btn.contains(Position::new(x, y)));
    button(f, &close_btn, hovered);

    // Panel de detalle (checkpoints/tasks de la sesión seleccionada).
    let (detail_lines, detail_title) = match &data.detail {
        Some((id, lines)) => {
            let mut ls: Vec<Line<'static>> = lines.iter().map(|l| Line::raw(l.clone())).collect();
            if ls.len() > (areas.detail.height.saturating_sub(2)) as usize {
                ls.truncate((areas.detail.height.saturating_sub(2)) as usize);
            }
            (ls, format!("detalle: {id}"))
        }
        None => (
            vec![Line::from(Span::styled(
                "seleccioná una fila para ver checkpoints y tasks",
                muted_style_raw(),
            ))],
            "detalle".to_string(),
        ),
    };
    f.render_widget(
        Paragraph::new(detail_lines).block(
            ratatui::widgets::Block::default()
                .borders(ratatui::widgets::Borders::ALL)
                .title(Span::styled(detail_title, accent_style())),
        ),
        areas.detail,
    );

    // Salida de la última mutación resuelta (ejecutado/denegado/fallo).
    if let Some((msg, is_err)) = &data.outcome {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                msg.clone(),
                if *is_err {
                    Style::default().fg(crate::theme::error())
                } else {
                    accent_style()
                },
            ))),
            areas.outcome,
        );
    }

    SessionsRenderInfo {
        buttons: vec![close_btn],
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
