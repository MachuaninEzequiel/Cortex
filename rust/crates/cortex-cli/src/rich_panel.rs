//! Réplica del `rich.panel.Panel` tal como lo imprime el CLI Python pipado
//! (`cortex hint`): width=80, box ROUNDED, padding=(1, 2), título centrado
//! en el borde superior, sin ANSI.
//!
//! Geometría derivada empíricamente del oráculo (ver tests con bytes
//! congelados): borde `╭ ─ ╮ │ ╰ ╯`, contenido ≤74 celdas entre 2 espacios
//! de padding, título como `" {title} "` con guiones restantes repartidos
//! floor a la izquierda / resto a la derecha.

use unicode_width::UnicodeWidthChar;

/// Ancho de consola no-tty de rich (contrato del gate: siempre pipado).
pub const PANEL_WIDTH: usize = 80;
const CONTENT_WIDTH: usize = PANEL_WIDTH - 2 - 4; // bordes + padding (1,2)

/// Ancho en celdas de terminal de un string (emoji/cjk = 2).
fn display_width(s: &str) -> usize {
    s.chars().map(|c| c.width().unwrap_or(0)).sum()
}

/// Rellena `line` con espacios hasta ocupar `cells` celdas.
fn pad_to(line: &str, cells: usize) -> String {
    let mut out = String::from(line);
    let current = display_width(line);
    for _ in current..cells {
        out.push(' ');
    }
    out
}

/// Wrap greedy por palabras al ancho `max` celdas, respetando `\n`
/// explícitos y la indentación original de la primera fila (misma
/// semántica de flow que rich para texto plano).
fn wrap_line(line: &str, max: usize) -> Vec<String> {
    if display_width(line) <= max {
        return vec![line.to_string()];
    }
    let indent = line.len() - line.trim_start_matches(' ').len();
    let indent_str = " ".repeat(indent);
    let mut rows: Vec<String> = Vec::new();
    let mut current = indent_str.clone();
    let mut current_cells = indent;
    let mut first = true;
    for word in line.split(' ').filter(|w| !w.is_empty()) {
        let word_cells = display_width(word);
        if first && current_cells + word_cells <= max {
            current.push_str(word);
            current_cells += word_cells;
            first = false;
            continue;
        }
        first = false;
        if current_cells + 1 + word_cells <= max {
            current.push(' ');
            current.push_str(word);
            current_cells += 1 + word_cells;
        } else {
            rows.push(std::mem::take(&mut current));
            current = word.to_string();
            current_cells = word_cells;
        }
    }
    rows.push(current);
    rows
}

/// Renderiza el panel completo (con newlines finales por fila, sin las
/// líneas en blanco que el comando agrega alrededor).
pub fn render(title: &str, content: &str) -> String {
    let dash = "\u{2500}"; // ─
    let title_text = format!(" {title} ");
    let title_cells = display_width(&title_text);
    let remaining = PANEL_WIDTH - 2 - title_cells;
    let left = remaining / 2;
    let right = remaining - left;

    let mut out = String::new();
    out.push('\u{256D}'); // ╭
    for _ in 0..left {
        out.push_str(dash);
    }
    out.push_str(&title_text);
    for _ in 0..right {
        out.push_str(dash);
    }
    out.push_str("\u{256E}\n"); // ╮

    let blank_row = format!("\u{2502}{}\u{2502}\n", pad_to("", PANEL_WIDTH - 2));
    out.push_str(&blank_row); // padding vertical superior

    for source_line in content.split('\n') {
        for row in wrap_line(source_line, CONTENT_WIDTH) {
            out.push('\u{2502}'); // │
            out.push_str("  ");
            out.push_str(&pad_to(&row, CONTENT_WIDTH));
            out.push_str("  ");
            out.push('\u{2502}');
            out.push('\n');
        }
    }

    out.push_str(&blank_row); // padding vertical inferior
    out.push('\u{2570}'); // ╰
    for _ in 0..PANEL_WIDTH - 2 {
        out.push_str(dash);
    }
    out.push_str("\u{256F}\n"); // ╯
    out
}
