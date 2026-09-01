//! Pantalla Menu del Companion (G-B2c): el catálogo anti-olvido.
//!
//! Render puro sobre `flat_rows()` (menu.rs): secciones por dominio + una
//! fila por capacidad. Click en una entrada la ejecuta (lecturas directas;
//! mutantes piden aprobación en el runtime). El panel de salida muestra el
//! resultado (`--json` para las familias integradas, error P6/P9 honesto
//! con el comando exacto para las que aún no lo están).
//!
//! Geometría COMPARTIDA con `hit_test` (app.rs): las consts de filas/botón
//! son las mismas por estructura, no pueden divergir.

use std::time::Instant;

use ratatui::layout::Rect;
use ratatui::prelude::{Color, Line, Style};
use ratatui::text::Span;
use ratatui::widgets::Paragraph;
use ratatui::Frame;


use crate::app::{
    MENU_BACK_BTN, MENU_LIST_HEIGHT, MENU_LIST_LEFT, MENU_LIST_TOP, MENU_LIST_WIDTH,
    MENU_OUTPUT_HEIGHT, MENU_OUTPUT_TOP,
};
use crate::menu::{flat_rows, FlatRow, MenuOutput};
use crate::widgets::{button, Button};

/// Áreas del Menu: lista (filas del catálogo), panel de salida y botón
/// volver — MISMO geometría que `hit_test` (consts de `app.rs`).
#[derive(Debug, Clone)]
pub struct MenuAreas {
    pub list: Rect,
    pub output: Rect,
    pub back_btn: Rect,
    /// Posición del mouse para hover (el binario la setea antes de cada draw).
    pub hover_mouse: Option<(u16, u16)>,
}

/// Deriva las áreas desde las consts del hit-test (coherencia estructural).
pub fn menu_areas(area: Rect) -> MenuAreas {
    let width = area.width.min(80).saturating_sub(4).max(1);
    MenuAreas {
        list: Rect::new(
            MENU_LIST_LEFT,
            MENU_LIST_TOP,
            MENU_LIST_WIDTH,
            MENU_LIST_HEIGHT,
        ),
        output: Rect::new(2, MENU_OUTPUT_TOP, width, MENU_OUTPUT_HEIGHT),
        back_btn: MENU_BACK_BTN,
        hover_mouse: None,
    }
}

fn muted_style() -> Style {
    Style::default().fg(crate::theme::text_muted())
}

fn accent_style() -> Style {
    Style::default().fg(crate::theme::accent())
}

/// Args legibles de una entrada (" family arg1 arg2" o "").
fn args_suffix(args: &[&str]) -> String {
    if args.is_empty() {
        String::new()
    } else {
        let mut s = String::from(" ");
        s.push_str(&args.join(" "));
        s
    }
}

/// Recorta el texto de salida a `max` líneas de `width` columnas.
fn fit_lines(text: &str, width: usize, max: usize) -> Vec<Line<'static>> {
    let mut out = Vec::new();
    for raw in text.lines().take(max) {
        let mut line = raw.to_string();
        let n = line.chars().count();
        if n > width {
            line = line.chars().take(width).collect();
        }
        out.push(Line::raw(line));
    }
    out
}

/// Renderiza el Menu completo (presupuesto <50 ms, patrón P10).
pub fn render_menu(
    f: &mut Frame<'_>,
    area: Rect,
    output: Option<&MenuOutput>,
    scroll: u16,
    areas: &mut MenuAreas,
) -> AppRenderInfo {
    let t0 = Instant::now();

    // Encabezado: título + hint.
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Cortex — capacidades", accent_style()),
            Span::styled(
                "   (clic ejecuta · mutantes piden aprobación)",
                muted_style(),
            ),
        ])),
        Rect::new(area.x + 2, area.y, area.width.saturating_sub(4).max(1), 1),
    );

    // Botón volver (misma rect que el hit-test).
    let back_btn = Button {
        id: "menu-back",
        rect: areas.back_btn,
        label: "‹ Volver".into(),
        enabled: true,
    };
    let hovered_back = areas.hover_mouse.is_some_and(|(x, y)| {
        areas
            .back_btn
            .contains(ratatui::layout::Position::new(x, y))
    });
    button(f, &back_btn, hovered_back);

    // Lista: secciones por dominio + entradas (ventana por scroll).
    let rows = flat_rows();
    let hover_row = areas.hover_mouse.and_then(|(_, y)| {
        let flat = usize::from(y.saturating_sub(MENU_LIST_TOP)) + usize::from(scroll);
        (flat < rows.len()).then_some(flat)
    });
    for (flat, row) in rows.iter().enumerate() {
        let y = i32::from(areas.list.y) + flat as i32 - i32::from(scroll);
        if y < i32::from(areas.list.y) || y >= i32::from(areas.list.y + areas.list.height) {
            continue;
        }
        let line = match row {
            FlatRow::Header(d) => Line::from(vec![Span::styled(
                format!("▸ {}", d.label()),
                Style::default()
                    .fg(crate::theme::accent())
                    .add_modifier(ratatui::style::Modifier::BOLD),
            )]),
            FlatRow::Entry(e) => {
                let is_hover = hover_row == Some(flat);
                let text = format!(
                    "  {:<26}  cortex {}{}",
                    e.title,
                    e.family,
                    args_suffix(e.args)
                );
                if is_hover {
                    Line::from(vec![Span::styled(
                        text,
                        accent_style().add_modifier(ratatui::style::Modifier::BOLD),
                    )])
                } else {
                    Line::from(text)
                }
            }
        };
        f.render_widget(
            Paragraph::new(line),
            Rect::new(areas.list.x, y as u16, areas.list.width, 1),
        );
    }

    // Panel de salida: resultado del último comando (o hint inicial).
    let title = if output.is_some_and(|o| o.is_error) {
        "salida (error)".to_string()
    } else {
        "salida".to_string()
    };
    let (lines, title_color): (Vec<Line<'static>>, Color) = match output {
        Some(o) => {
            let prefix = if o.is_error { "⚠ " } else { "" };
            let text = format!("{prefix}{}", o.text);
            (
                fit_lines(&text, areas.output.width.saturating_sub(4) as usize, areas.output.height as usize),
                if o.is_error { crate::theme::error() } else { crate::theme::success() },
            )
        }
        None => (
            vec![Line::from("Sesiones · Memoria · Búsqueda · Docs · CI · Setup · Enterprise — todo Cortex, un solo lugar.")],
            crate::theme::text_muted(),
        ),
    };
    f.render_widget(
        Paragraph::new(lines).block(
            ratatui::widgets::Block::default()
                .borders(ratatui::widgets::Borders::ALL)
                .title(Span::styled(title, Style::default().fg(title_color))),
        ),
        areas.output,
    );

    AppRenderInfo {
        buttons: vec![back_btn],
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}

/// Resultado del render (mismo contrato que Home).
#[derive(Debug, Clone)]
pub struct AppRenderInfo {
    pub buttons: Vec<Button>,
    pub spent_ms: f32,
}
