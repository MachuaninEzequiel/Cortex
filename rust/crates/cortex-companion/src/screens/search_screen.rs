//! Pantalla Search del Companion (G-B2d): input por teclado + hits de la
//! MISMA pipeline híbrida que el CLI (vía `Backend::search`, top-k 5) +
//! botón [Útil] por hit episódico que persiste feedback en
//! `.cortex/feedback.jsonl` (formato del oráculo, `crate::feedback`).
//!
//! Geometría COMPARTIDA con `hit_test` (consts de `app.rs`), presupuesto de
//! render <50 ms (patrón P10), y salida de feedback visible (nunca silencio).

use std::time::Instant;

use ratatui::layout::Rect;
use ratatui::prelude::{Color, Line, Style};
use ratatui::text::Span;
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Frame;

use cortex_branding::palette;

use crate::app::{
    OutcomeLine, SEARCH_DETAIL, SEARCH_INPUT, SEARCH_LIST_HEIGHT, SEARCH_LIST_LEFT,
    SEARCH_LIST_TOP, SEARCH_LIST_WIDTH, SEARCH_STATUS, SEARCH_USEFUL_W, SEARCH_USEFUL_X,
};
use crate::engine::SearchHit;
use crate::widgets::to_color;

/// Datos de la pantalla Search (query, hits, selección, marcas de esta
/// sesión y resultado del último feedback).
#[derive(Debug, Clone, Default)]
pub struct SearchData {
    pub query: String,
    pub hits: Vec<SearchHit>,
    pub selected: Option<usize>,
    /// memory_ids ya marcadas [Útil] en esta sesión (✓ en la fila; la
    /// idempotencia real la garantiza el escaneo del archivo en `feedback`).
    pub marked: Vec<String>,
    pub outcome: Option<OutcomeLine>,
    pub error: Option<String>,
}

/// Áreas de Search: input, lista (con columna [Útil]) y detalle — MISMA
/// geometría que `hit_test`.
#[derive(Debug, Clone)]
pub struct SearchAreas {
    pub input: Rect,
    pub status: Rect,
    pub list: Rect,
    /// Columna [Útil] (para pintar/hover por fila).
    pub useful_col: Rect,
    pub detail: Rect,
    pub hover_mouse: Option<(u16, u16)>,
}

/// Deriva las áreas desde las consts del hit-test (coherencia estructural).
pub fn search_areas(_area: Rect) -> SearchAreas {
    SearchAreas {
        input: SEARCH_INPUT,
        status: SEARCH_STATUS,
        list: Rect::new(
            SEARCH_LIST_LEFT,
            SEARCH_LIST_TOP,
            SEARCH_LIST_WIDTH,
            SEARCH_LIST_HEIGHT,
        ),
        useful_col: Rect::new(
            SEARCH_USEFUL_X,
            SEARCH_LIST_TOP,
            SEARCH_USEFUL_W,
            SEARCH_LIST_HEIGHT,
        ),
        detail: SEARCH_DETAIL,
        hover_mouse: None,
    }
}

/// Resultado del render (presupuesto medido).
#[derive(Debug, Clone)]
pub struct SearchRenderInfo {
    pub spent_ms: f32,
}

fn accent_style() -> Style {
    Style::default().fg(to_color(palette::CYAN))
}

fn muted_style() -> Style {
    Style::default().fg(to_color(palette::MUTED))
}

/// Fila de un hit: badge de fuente, título, score y la columna [Útil]/✓
/// alineada a la geometría de `hit_test` (SEARCH_USEFUL_X). Los hits
/// semánticos no tienen botón (sin memory_id — core.py:274).
fn hit_line(h: &SearchHit, marked: bool, selected: bool, hovered: bool) -> Line<'static> {
    let badge = if h.source == "episodic" {
        "EPIS"
    } else {
        "SEM "
    };
    let title: String = h.title.chars().take(34).collect();
    let pad =
        (SEARCH_USEFUL_X as usize).saturating_sub(4 + badge.len() + title.chars().count() + 7);
    let row_style = if selected {
        accent_style().add_modifier(ratatui::style::Modifier::BOLD)
    } else if hovered {
        Style::default().add_modifier(ratatui::style::Modifier::BOLD)
    } else {
        Style::default()
    };
    let right = if !marked && h.id.is_some() {
        Span::styled(
            "[ Útil ]",
            Style::default().fg(Color::Green).add_modifier(if hovered {
                ratatui::style::Modifier::BOLD
            } else {
                ratatui::style::Modifier::empty()
            }),
        )
    } else if marked {
        Span::styled("✓ útil ", Style::default().fg(Color::Yellow))
    } else {
        Span::raw("       ")
    };
    Line::from(vec![
        Span::styled(
            format!("  [{badge}] {title}{}{:>6.2}", " ".repeat(pad), h.score),
            row_style,
        ),
        right,
    ])
}

/// Renderiza Search (presupuesto <50 ms, patrón P10).
pub fn render_search(
    f: &mut Frame<'_>,
    area: Rect,
    data: &SearchData,
    scroll: u16,
    areas: &mut SearchAreas,
) -> SearchRenderInfo {
    let t0 = Instant::now();

    // Encabezado.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Cortex — búsqueda", accent_style()),
            Span::styled("   (híbrida: episódica + semántica)", muted_style()),
        ])),
        Rect::new(area.x + 2, area.y, area.width.saturating_sub(4).max(1), 1),
    );

    // Status: resultado del último feedback o del filtro (línea 1).
    if let Some((msg, is_err)) = &data.outcome {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                msg.clone(),
                if *is_err {
                    Style::default().fg(Color::Red)
                } else {
                    Style::default().fg(Color::Yellow)
                },
            ))),
            areas.status,
        );
    } else if let Some(err) = &data.error {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                format!("⚠ {err}"),
                Style::default().fg(Color::Red),
            ))),
            areas.status,
        );
    }

    // Input (línea 2): `/` desde cualquier pantalla salta acá; Enter busca.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("consulta: ", muted_style()),
            Span::styled(format!("{}▌", data.query), accent_style()),
        ]))
        .block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(Color::DarkGray)),
        ),
        areas.input,
    );

    // Filas de hits (ventana por scroll).
    for i in 0..data.hits.len() {
        let y = i32::from(areas.list.y) + i as i32 - i32::from(scroll);
        if y < i32::from(areas.list.y) || y >= i32::from(areas.list.y + areas.list.height) {
            continue;
        }
        let hovered = areas.hover_mouse.is_some_and(|(mx, my)| {
            my as i32 == y && (SEARCH_USEFUL_X..SEARCH_USEFUL_X + SEARCH_USEFUL_W).contains(&mx)
        });
        let selected = data.selected == Some(i);
        let marked = data.hits[i]
            .id
            .as_ref()
            .is_some_and(|id| data.marked.contains(id));
        f.render_widget(
            Paragraph::new(hit_line(&data.hits[i], marked, selected, hovered)),
            Rect::new(areas.list.x, y as u16, SEARCH_LIST_WIDTH, 1),
        );
    }
    if data.hits.is_empty() {
        let hint = if data.query.trim().is_empty() {
            "escribí una consulta (Enter busca · `/` desde cualquier pantalla · Esc vuelve)"
                .to_string()
        } else {
            format!("sin resultados para «{}»", data.query.trim())
        };
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(hint, muted_style()))),
            areas.list,
        );
    }

    // Detalle del seleccionado (snippet recortado, panel inferior).
    if let Some(i) = data.selected {
        if let Some(h) = data.hits.get(i) {
            f.render_widget(
                Paragraph::new(h.snippet.clone())
                    .block(
                        Block::default()
                            .borders(Borders::ALL)
                            .title(Span::styled(h.path.clone(), muted_style())),
                    )
                    .scroll((usize::from(scroll) as u16, 0)),
                areas.detail,
            );
        }
    }

    SearchRenderInfo {
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
