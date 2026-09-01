//! Componentes visuales base del rediseño (spec §13): cada componente se
//! dibuja en su módulo; `ui.rs` compone (acá: las pantallas).

pub mod empty_state;
pub mod feedback;
pub mod header;
pub mod help;
pub mod list;
pub mod panel;
pub mod status_bar;

use unicode_width::UnicodeWidthStr;

/// Trunca por ancho VISUAL (no por bytes) y agrega `…` cuando corta
/// (spec §9/§13: "Truncar por ancho visual y agregar …").
pub fn truncate_visual(s: &str, max: usize) -> String {
    if UnicodeWidthStr::width(s) <= max {
        return s.to_string();
    }
    let mut out = String::new();
    let mut w = 0usize;
    for ch in s.chars() {
        let cw = UnicodeWidthStr::width(ch.to_string().as_str());
        if w + cw + 1 > max {
            break; // deja espacio para la elipsis
        }
        out.push(ch);
        w += cw;
    }
    out.push('…');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn truncado_por_ancho_visual() {
        assert_eq!(truncate_visual("hola", 10), "hola");
        let t = truncate_visual("una frase larga de prueba", 12);
        assert!(t.ends_with('…'));
        assert!(UnicodeWidthStr::width(t.as_str()) <= 13);
    }

    #[test]
    fn truncado_unicode_seguro() {
        // El corte nunca parte un char multi-byte.
        let t = truncate_visual("café olé olé", 6);
        assert!(UnicodeWidthStr::width(t.as_str()) <= 7);
    }
}
