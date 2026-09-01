//! Pantalla Actions del Companion (G-B3 UI): propuestas del Action Engine
//! con score/costo/reversibilidad; [Aprobar] por acción y [Aprobar lote
//! auto-ok] (solo reversibles de costo instant) — TODO pasa por el modal de
//! la máquina de estados (`run_guarded`, B2), con auditoría por ítem.
//!
//! Geometría COMPARTIDA con `hit_test` (consts de `app.rs`).

use std::time::Instant;

use ratatui::layout::{Position, Rect};
use ratatui::prelude::{Line, Style};
use ratatui::text::Span;
use ratatui::widgets::Paragraph;
use ratatui::Frame;


use crate::app::{
    ActionsData, ACTIONS_APPROVE_W, ACTIONS_APPROVE_X, ACTIONS_BATCH_BTN, ACTIONS_LIST_HEIGHT,
    ACTIONS_LIST_LEFT, ACTIONS_LIST_TOP, ACTIONS_LIST_WIDTH, ACTIONS_OUTCOME,
};
use crate::engine::ActionProposal;
use crate::widgets::{button, Button};

/// Áreas de Actions: lista de propuestas, botón lote, columna [Aprobar] y
/// salida — MISMA geometría que `hit_test`.
#[derive(Debug, Clone)]
pub struct ActionsAreas {
    pub list: Rect,
    pub batch_btn: Rect,
    /// Columna [Aprobar] de la lista (para pintar/hover por fila).
    pub approve_col: Rect,
    pub outcome: Rect,
    /// Posición del mouse para hover (el binario la setea antes de cada draw).
    pub hover_mouse: Option<(u16, u16)>,
}

/// Deriva las áreas desde las consts del hit-test (coherencia estructural).
pub fn actions_areas(_area: Rect) -> ActionsAreas {
    ActionsAreas {
        list: Rect::new(
            ACTIONS_LIST_LEFT,
            ACTIONS_LIST_TOP,
            ACTIONS_LIST_WIDTH,
            ACTIONS_LIST_HEIGHT,
        ),
        batch_btn: ACTIONS_BATCH_BTN,
        approve_col: Rect::new(
            ACTIONS_APPROVE_X,
            ACTIONS_LIST_TOP,
            ACTIONS_APPROVE_W,
            ACTIONS_LIST_HEIGHT,
        ),
        outcome: ACTIONS_OUTCOME,
        hover_mouse: None,
    }
}

/// Resultado del render (botones del frame + presupuesto medido).
#[derive(Debug, Clone)]
pub struct ActionsRenderInfo {
    pub buttons: Vec<Button>,
    pub spent_ms: f32,
}

fn accent_style() -> Style {
    Style::default().fg(crate::theme::accent())
}

fn muted_style() -> Style {
    Style::default().fg(crate::theme::text_muted())
}

/// El lote auto-ok solo agrupa reversibles de costo instant (spec 14 §3):
/// el botón se muestra pero queda deshabilitado si no hay ninguna.
fn has_batchable(data: &ActionsData) -> bool {
    data.proposals
        .iter()
        .any(|p| p.reversible && p.cost == "instant")
}

/// Fila de una propuesta: título, score, costo, reversibilidad y la columna
/// `[ Aprobar ]` alineada a la geometría de `hit_test` (ACTIONS_APPROVE_X).
/// El efecto completo NO se pinta acá: viaja al modal, donde el usuario lo
/// lee antes de aprobar (spec §5).
fn proposal_line(p: &ActionProposal, hovered_row: bool) -> Line<'static> {
    let title: String = p.title.chars().take(22).collect();
    let rev = if p.reversible { "rev" } else { "IRR" };
    let body = format!("  {title:<22}{:>7.2} · {:<8} · {:<3}", p.score, p.cost, rev);
    let pad = (ACTIONS_APPROVE_X as usize).saturating_sub(2 + body.chars().count());
    let row_style = if hovered_row {
        accent_style().add_modifier(ratatui::style::Modifier::BOLD)
    } else {
        Style::default()
    };
    let approve_style = if hovered_row {
        Style::default()
            .fg(crate::theme::success())
            .add_modifier(ratatui::style::Modifier::BOLD)
    } else {
        Style::default().fg(crate::theme::success())
    };
    Line::from(vec![
        Span::styled(format!("{body}{}", " ".repeat(pad)), row_style),
        Span::styled("[ Aprobar ]", approve_style),
    ])
}

/// Renderiza Actions (presupuesto <50 ms, patrón P10).
pub fn render_actions(
    f: &mut Frame<'_>,
    area: Rect,
    data: &ActionsData,
    scroll: u16,
    areas: &mut ActionsAreas,
) -> ActionsRenderInfo {
    let t0 = Instant::now();

    // Encabezado.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Cortex — acciones", accent_style()),
            Span::styled(
                "   (el motor propone; nada se ejecuta sin tu clic)",
                muted_style(),
            ),
        ])),
        Rect::new(area.x + 2, area.y, area.width.saturating_sub(4).max(1), 1),
    );

    // Error de carga del motor (P6/P9 visible).
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

    // Botón lote auto-ok (habilitado solo con batchables — misma regla que
    // hit_test).
    let batch = Button {
        id: "batch-approve",
        rect: areas.batch_btn,
        label: "Aprobar lote".into(),
        enabled: has_batchable(data),
    };
    let hovered_batch = batch.enabled
        && areas
            .hover_mouse
            .is_some_and(|(x, y)| areas.batch_btn.contains(Position::new(x, y)));
    button(f, &batch, hovered_batch);

    // Filas de propuestas (ventana por scroll).
    for i in 0..data.proposals.len() {
        let y = i32::from(areas.list.y) + i as i32 - i32::from(scroll);
        if y < i32::from(areas.list.y) || y >= i32::from(areas.list.y + areas.list.height) {
            continue;
        };
        let hovered_row = areas.hover_mouse.is_some_and(|(mx, my)| {
            my as i32 == y
                && (ACTIONS_APPROVE_X..ACTIONS_APPROVE_X + ACTIONS_APPROVE_W).contains(&mx)
        });
        f.render_widget(
            Paragraph::new(proposal_line(&data.proposals[i], hovered_row)),
            Rect::new(areas.list.x, y as u16, 76, 1),
        );
    }
    if data.proposals.is_empty() && data.error.is_none() {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "el motor no propone nada ahora — `cortex next --stats` para ver el porqué",
                muted_style(),
            ))),
            areas.list,
        );
    }

    // Salida de la última aprobación (ejecutado/denegado/fallo; por ítem en
    // los lotes).
    if let Some((msg, is_err)) = &data.outcome {
        let title = if *is_err {
            "resultado (error)"
        } else {
            "resultado"
        };
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                msg.clone(),
                if *is_err {
                    Style::default().fg(crate::theme::error())
                } else {
                    accent_style()
                },
            )))
            .block(
                ratatui::widgets::Block::default()
                    .borders(ratatui::widgets::Borders::ALL)
                    .title(Span::styled(title.to_string(), muted_style())),
            ),
            areas.outcome,
        );
    }

    ActionsRenderInfo {
        buttons: vec![batch],
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
