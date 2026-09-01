//! Widgets mínimos del Companion (G-B2b): Panel, Button y List con estados
//! hover/active via borde.
//!
//! Duplicación ACOTADA de widgets de cortex-tui (documento 14 §2.1): el
//! Companion no depende de cortex-tui (WIP con goldens congelados). Refactor
//! a reuso cuando el TUI se estabilice (post-cierre, fuera de alcance).

use ratatui::layout::Rect;
use ratatui::prelude::Color;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};
use ratatui::Frame;

use crate::theme;
use cortex_branding::palette;

/// Convierte un color de la paleta de branding a un `Color` de ratatui.
/// (Solo para el ISOTIPO menta; el chrome pasa por `crate::theme`.)
pub(crate) fn to_color(c: palette::Rgb) -> Color {
    Color::Rgb(c.0, c.1, c.2)
}

/// Acento de marca del rediseño (mauve Catppuccin, igual que cortex-tui).
pub(crate) fn accent() -> Color {
    theme::accent()
}

/// Botón mínimo: rect + etiqueta + estado. Hover se pinta en el borde y la
/// etiqueta (estilo "hover/active via borde" del plan).
#[derive(Debug, Clone)]
pub struct Button {
    pub id: &'static str,
    pub rect: Rect,
    pub label: String,
    pub enabled: bool,
}

impl Button {
    fn color(&self, hovered: bool) -> Color {
        if !self.enabled {
            theme::overlay0()
        } else if hovered {
            theme::accent()
        } else {
            theme::surface2()
        }
    }
}

/// Dibuja un botón (borde redondeado + etiqueta centrada + hover interactivo).
pub fn button(f: &mut Frame<'_>, b: &Button, hovered: bool) {
    let color = b.color(hovered);
    let border_style = if hovered && b.enabled {
        Style::default().fg(color).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(color)
    };
    let block = Block::default()
        .border_type(BorderType::Rounded)
        .borders(Borders::ALL)
        .border_style(border_style);
    let text_style = if hovered && b.enabled {
        Style::default().fg(theme::text()).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(color)
    };
    let para = Paragraph::new(Line::from(vec![Span::styled(
        b.label.clone(),
        text_style,
    )]))
    .block(block);
    f.render_widget(para, b.rect);
}

/// Panel con bordes redondeados, título y contenido de líneas estiladas.
#[derive(Debug, Clone)]
pub struct Panel {
    pub title: String,
    pub rect: Rect,
}

pub fn panel(f: &mut Frame<'_>, p: &Panel, lines: Vec<Line<'_>>, title_color: Color) {
    let block = Block::default()
        .border_type(BorderType::Rounded)
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme::border_idle()))
        .title(Span::styled(
            p.title.clone(),
            Style::default().fg(title_color).add_modifier(Modifier::BOLD),
        ));
    f.render_widget(Paragraph::new(lines).block(block), p.rect);
}

/// Lista simple con ítem seleccionado resaltado (Sessions/Search/Brain las
/// consumen en B6+; el widget queda listo acá por contrato del plan).
#[derive(Debug, Clone)]
pub struct List {
    pub rect: Rect,
    pub items: Vec<String>,
    pub selected: Option<usize>,
}

pub fn list(f: &mut Frame<'_>, l: &List) {
    let block = Block::default()
        .border_type(BorderType::Rounded)
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme::border_idle()));
    let lines: Vec<Line<'_>> = l
        .items
        .iter()
        .enumerate()
        .map(|(i, it)| {
            if Some(i) == l.selected {
                Line::from(vec![Span::styled(
                    it.as_str(),
                    Style::default().fg(accent()).add_modifier(Modifier::BOLD),
                )])
            } else {
                Line::from(it.as_str())
            }
        })
        .collect();
    f.render_widget(Paragraph::new(lines).block(block), l.rect);
}
