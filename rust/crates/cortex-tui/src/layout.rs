//! Modos de layout del área disponible (spec §9).
//!
//! Un solo punto de decisión de breakpoints para las pantallas operativas;
//! el modo se DERIVA del área en cada render — nunca se guarda como estado
//! mutable independiente. La variante del isotipo (prompt §18,
//! `branding_mode`) sigue siendo la función de marca del logo; acá vive el
//! mapeo pantalla→logo del rediseño (spec §8: Compact en cabeceras amplias,
//! Mark en medianas/angostas, texto "CORTEX" bajo el ancho mínimo del Mark).

use crate::renderer::CortexLogo;
use crate::theme::{self, Theme};
use cortex_branding::logo::LogoVariant;
use ratatui::prelude::{Constraint, Layout, Rect};
use ratatui::widgets::Paragraph;
use ratatui::Frame;

/// Niveles de pantalla operativa (spec §9). Los umbrales son punto de
/// partida: se ajustan con snapshots reales.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum LayoutMode {
    /// ≥120×32: 3 zonas (navegación | contenido | inspector).
    Wide,
    /// ≥90×26: dos paneles.
    Standard,
    /// ≥68×20: un panel principal, sidebars como tabs.
    Compact,
    /// <68×20: flujo vertical único, logo Mark o texto.
    Minimal,
    /// Demasiado pequeño para interacción segura: pantalla estable.
    TooSmall,
}

/// Deriva el modo del área disponible (función pura del área).
pub fn layout_mode(area: Rect) -> LayoutMode {
    if area.width >= 120 && area.height >= 32 {
        LayoutMode::Wide
    } else if area.width >= 90 && area.height >= 26 {
        LayoutMode::Standard
    } else if area.width >= 68 && area.height >= 20 {
        LayoutMode::Compact
    } else if area.width >= 40 && area.height >= 12 {
        LayoutMode::Minimal
    } else {
        LayoutMode::TooSmall
    }
}

/// Variante del isotipo para cabeceras según modo y ancho; `None` = ocultar
/// el isotipo y usar "CORTEX" como texto (spec §8).
pub fn logo_for(mode: LayoutMode, area_width: u16) -> Option<LogoVariant> {
    match mode {
        LayoutMode::Wide | LayoutMode::Standard => Some(LogoVariant::Compact),
        LayoutMode::Compact => Some(LogoVariant::Mark),
        LayoutMode::Minimal if area_width >= theme::MARK_MIN_WIDTH => Some(LogoVariant::Mark),
        LayoutMode::Minimal | LayoutMode::TooSmall => None,
    }
}

/// Pantalla estable para terminales demasiado pequeñas (spec §9 TooSmall):
/// sin panic, sin bordes secundarios, permite resize y salir.
pub fn render_too_small(f: &mut Frame<'_>, lang: &'static str) {
    let area = f.area();
    let mode = crate::env_color_mode();
    let theme = Theme::new(mode);

    let [logo_area, body_area, hint_area] = Layout::vertical([
        Constraint::Length(3),
        Constraint::Min(3),
        Constraint::Length(1),
    ])
    .areas(area);

    // Isotipo Mark si cabe; si no, el nombre como texto (nunca nada dibujado
    // a lo ancho: la silueta identifica aunque falte color).
    if area.width >= theme::MARK_MIN_WIDTH {
        f.render_widget(
            CortexLogo::new(LogoVariant::Mark).with_mode(mode),
            logo_area,
        );
    } else {
        f.render_widget(
            Paragraph::new(theme::brand_text(theme.title()))
                .style(theme.body())
                .centered(),
            logo_area,
        );
    }

    let body = if lang == "en" {
        [
            "Terminal too small".to_string(),
            format!(
                "Minimum recommended: 40×12 · Current: {}×{}",
                area.width, area.height
            ),
        ]
        .to_vec()
    } else {
        [
            "Terminal demasiado pequeña".to_string(),
            format!(
                "Mínimo recomendado: 40×12 · Actual: {}×{}",
                area.width, area.height
            ),
        ]
        .to_vec()
    };
    let body_par = Paragraph::new(body.join("\n"))
        .style(theme.body())
        .centered()
        .block(ratatui::widgets::Block::new());
    f.render_widget(body_par, body_area);

    let hint = if lang == "en" {
        "q quit · resize to continue"
    } else {
        "q salir · redimensioná para continuar"
    };
    f.render_widget(
        Paragraph::new(hint).style(theme.muted()).centered(),
        hint_area,
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::prelude::Rect;

    #[test]
    fn umbrales_de_modo() {
        assert_eq!(layout_mode(Rect::new(0, 0, 120, 32)), LayoutMode::Wide);
        assert_eq!(layout_mode(Rect::new(0, 0, 119, 32)), LayoutMode::Standard);
        assert_eq!(layout_mode(Rect::new(0, 0, 90, 26)), LayoutMode::Standard);
        assert_eq!(layout_mode(Rect::new(0, 0, 89, 26)), LayoutMode::Compact);
        assert_eq!(layout_mode(Rect::new(0, 0, 68, 20)), LayoutMode::Compact);
        assert_eq!(layout_mode(Rect::new(0, 0, 67, 20)), LayoutMode::Minimal);
        assert_eq!(layout_mode(Rect::new(0, 0, 40, 12)), LayoutMode::Minimal);
        assert_eq!(layout_mode(Rect::new(0, 0, 39, 12)), LayoutMode::TooSmall);
        assert_eq!(layout_mode(Rect::new(0, 0, 1, 1)), LayoutMode::TooSmall);
    }

    #[test]
    fn logo_variante_por_modo_y_ancho() {
        assert_eq!(logo_for(LayoutMode::Wide, 10), Some(LogoVariant::Compact));
        assert_eq!(
            logo_for(LayoutMode::Standard, 10),
            Some(LogoVariant::Compact)
        );
        assert_eq!(logo_for(LayoutMode::Compact, 10), Some(LogoVariant::Mark));
        assert_eq!(logo_for(LayoutMode::Minimal, 20), Some(LogoVariant::Mark));
        assert_eq!(logo_for(LayoutMode::Minimal, 14), None);
        assert_eq!(logo_for(LayoutMode::TooSmall, 200), None);
    }
}
