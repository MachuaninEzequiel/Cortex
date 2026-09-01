//! Pantalla Brain del Companion (G-B4): chat con el agente local.
//!
//! Muestra el historial (usuario/brain/propuestas), el input con cursor y
//! el botón [Ejecutar] por propuesta. La geometría es COMPARTIDA con
//! `hit_test` (consts de `app.rs`); presupuesto de render <50 ms (patrón
//! P10). El render NUNCA muta estado ni ejecuta nada: las propuestas se
//! resuelven por la máquina de estados (modal → `run_guarded`).

use std::time::Instant;

use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Frame;

use crate::app::{
    BRAIN_EXEC_W, BRAIN_EXEC_X, BRAIN_INPUT, BRAIN_LIST_HEIGHT, BRAIN_LIST_LEFT, BRAIN_LIST_TOP,
    BRAIN_LIST_WIDTH, BRAIN_STATUS,
};
use crate::brain_panel::{BrainMode, BrainPanel};

/// Áreas del Brain: status, input (alto 2 — lección B7), lista de filas y
/// columna [Ejecutar]. MISMA geometría que `hit_test`.
#[derive(Debug, Clone)]
pub struct BrainAreas {
    pub status: Rect,
    pub input: Rect,
    pub list: Rect,
    pub exec_col: Rect,
    pub hover_mouse: Option<(u16, u16)>,
}

pub fn brain_areas(_area: Rect) -> BrainAreas {
    BrainAreas {
        status: BRAIN_STATUS,
        input: BRAIN_INPUT,
        list: Rect::new(
            BRAIN_LIST_LEFT,
            BRAIN_LIST_TOP,
            BRAIN_LIST_WIDTH,
            BRAIN_LIST_HEIGHT,
        ),
        exec_col: Rect::new(
            BRAIN_EXEC_X,
            BRAIN_LIST_TOP,
            BRAIN_EXEC_W,
            BRAIN_LIST_HEIGHT,
        ),
        hover_mouse: None,
    }
}

/// Fila expandida del chat: un mensaje Brain multilínea ocupa N filas (el
/// historial se lee como terminal). `hit_test` y `render_brain` consumen
/// EXACTAMENTE este mapeo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrainRow {
    User(String),
    Brain(String),
    Proposal { command: String, audit_key: String },
}

/// Expande los mensajes del panel a filas visibles (orden estable).
#[must_use]
pub fn brain_rows(panel: &BrainPanel) -> Vec<BrainRow> {
    let mut rows = Vec::new();
    for m in &panel.messages {
        match m {
            crate::brain_panel::BrainMsg::User(t) => rows.push(BrainRow::User(t.clone())),
            crate::brain_panel::BrainMsg::Brain(t) => {
                if t.lines().count() == 0 {
                    rows.push(BrainRow::Brain(String::new()));
                }
                for line in t.lines() {
                    rows.push(BrainRow::Brain(line.to_string()));
                }
            }
            crate::brain_panel::BrainMsg::Proposal { command, audit_key } => {
                rows.push(BrainRow::Proposal {
                    command: command.clone(),
                    audit_key: audit_key.clone(),
                });
            }
        }
    }
    rows
}

/// Resultado del render (presupuesto medido).
#[derive(Debug, Clone)]
pub struct BrainRenderInfo {
    pub spent_ms: f32,
}

fn accent_style() -> Style {
    Style::default().fg(crate::theme::accent())
}

fn muted_style() -> Style {
    Style::default().fg(crate::theme::text_muted())
}

fn mode_label(mode: BrainMode) -> &'static str {
    match mode {
        BrainMode::Deterministic => "modo: determinista (0 tokens · sin modelo)",
        BrainMode::Llm => "modo: LLM local",
    }
}

/// Línea de una propuesta: comando (recortado) + [Ejecutar] alineado a la
/// columna del hit-test (misma técnica de padding que las filas de Search).
fn proposal_line(command: &str, hovered: bool) -> Line<'static> {
    let shown: String = command.chars().take(58).collect();
    let btn_style = Style::default().fg(crate::theme::success()).add_modifier(if hovered {
        Modifier::BOLD
    } else {
        Modifier::empty()
    });
    Line::from(vec![
        Span::styled(shown, Style::default().fg(crate::theme::warning())),
        Span::raw("  "),
        Span::styled("[Ejecutar]", btn_style),
    ])
}

/// Renderiza Brain (presupuesto <50 ms).
pub fn render_brain(
    f: &mut Frame<'_>,
    area: Rect,
    panel: &BrainPanel,
    scroll: u16,
    areas: &mut BrainAreas,
) -> BrainRenderInfo {
    let t0 = Instant::now();

    // Encabezado.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Cortex — brain", accent_style()),
            Span::styled(
                "   (agente local · lee directo, muta con aprobación)",
                muted_style(),
            ),
        ])),
        Rect::new(area.x + 2, area.y, area.width.saturating_sub(4).max(1), 1),
    );

    // Status: resultado de la última ejecución guardada; si no, el modo.
    if let Some((msg, is_err)) = &panel.outcome {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                msg.clone(),
                if *is_err {
                    Style::default().fg(crate::theme::error())
                } else {
                    Style::default().fg(crate::theme::warning())
                },
            ))),
            areas.status,
        );
    } else {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                mode_label(panel.mode),
                muted_style(),
            ))),
            areas.status,
        );
    }

    // Input (alto 2: Borders::BOTTOM consume una fila — fix B7).
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("pregunta: ", muted_style()),
            Span::styled(format!("{}▌", panel.input), accent_style()),
        ]))
        .block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(crate::theme::overlay0())),
        ),
        areas.input,
    );

    // Filas expandidas (ventana por scroll).
    let rows = brain_rows(panel);
    for (i, row) in rows.iter().enumerate() {
        let y = i32::from(areas.list.y) + i as i32 - i32::from(scroll);
        if y < i32::from(areas.list.y) || y >= i32::from(areas.list.y + areas.list.height) {
            continue;
        }
        let line = match row {
            BrainRow::User(t) => Line::from(vec![
                Span::styled("→ ", muted_style()),
                Span::styled(t.clone(), accent_style().add_modifier(Modifier::BOLD)),
            ]),
            BrainRow::Brain(t) => Line::from(Span::raw(t.clone())),
            BrainRow::Proposal { command, .. } => {
                let hovered = areas.hover_mouse.is_some_and(|(mx, my)| {
                    my as i32 == y && (BRAIN_EXEC_X..BRAIN_EXEC_X + BRAIN_EXEC_W).contains(&mx)
                });
                proposal_line(command, hovered)
            }
        };
        f.render_widget(
            Paragraph::new(line),
            Rect::new(areas.list.x, y as u16, BRAIN_LIST_WIDTH, 1),
        );
    }
    if rows.is_empty() {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "preguntá: «session» · «busca docs sobre X» · «¿qué hago ahora?» · /help",
                muted_style(),
            ))),
            areas.list,
        );
    }

    BrainRenderInfo {
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
