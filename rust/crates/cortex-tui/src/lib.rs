//! cortex-tui — TUI nativa de Cortex sobre ratatui (Obra 07 P10).
//!
//! Identidad visual (`cortex-branding`) renderizada como `Widget` de ratatui,
//! pantalla splash y layout del Home. El Home espeja la arquitectura de
//! información de `cortex/tui/core.py` (HomeState) con datos demo: el
//! cableado a servicios reales (sessions/acciones/vault) llega cuando
//! cortex-app los exponga (P4-P6 del plan 08).
//!
//! ```no_run
//! use cortex_tui::{CortexLogo, LogoVariant};
//! use ratatui::Frame;
//!
//! fn splash(f: &mut Frame<'_>) {
//!     f.render_widget(CortexLogo::new(LogoVariant::Full), f.area());
//! }
//! ```

pub mod home;
pub mod renderer;
pub mod sessions;
pub mod splash;

pub use cortex_branding::ansi::ColorMode;
pub use cortex_branding::logo::LogoVariant;
pub use renderer::CortexLogo;

/// Modo de branding según el tamaño de la pantalla (prompt-logo.md §18).
/// Decisión centralizada: jamás hardcodear breakpoints por pantalla.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum BrandingMode {
    /// Pantalla grande: isotipo completo.
    Full,
    /// Pantalla mediana: isotipo compacto.
    Compact,
    /// Pantalla chica: solo el mark.
    Minimal,
}

/// Breakpoints de referencia del prompt §18:
/// ≥90×28 → Full · ≥55×18 → Compact · resto → Minimal.
pub fn branding_mode(area: ratatui::prelude::Rect) -> BrandingMode {
    if area.width >= 90 && area.height >= 28 {
        BrandingMode::Full
    } else if area.width >= 55 && area.height >= 18 {
        BrandingMode::Compact
    } else {
        BrandingMode::Minimal
    }
}

impl BrandingMode {
    /// Variante del isotipo que corresponde a este modo.
    pub fn variant(self) -> LogoVariant {
        match self {
            BrandingMode::Full => LogoVariant::Full,
            BrandingMode::Compact => LogoVariant::Compact,
            BrandingMode::Minimal => LogoVariant::Mark,
        }
    }
}

/// Idioma del chrome TUI (misma convención que action_engine/i18n.py:
/// CORTEX_LANG > default "es").
pub fn lang() -> &'static str {
    match std::env::var("CORTEX_LANG").as_deref() {
        Ok("en") => "en",
        _ => "es",
    }
}

/// Modo de color del entorno (misma detección que el branding ANSI).
pub fn env_color_mode() -> ColorMode {
    cortex_branding::ansi::env_color_mode()
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::prelude::Rect;

    #[test]
    fn breakpoints_del_prompt() {
        assert_eq!(branding_mode(Rect::new(0, 0, 90, 28)), BrandingMode::Full);
        assert_eq!(branding_mode(Rect::new(0, 0, 120, 40)), BrandingMode::Full);
        assert_eq!(
            branding_mode(Rect::new(0, 0, 89, 28)),
            BrandingMode::Compact
        );
        assert_eq!(
            branding_mode(Rect::new(0, 0, 55, 18)),
            BrandingMode::Compact
        );
        assert_eq!(
            branding_mode(Rect::new(0, 0, 54, 18)),
            BrandingMode::Minimal
        );
        assert_eq!(
            branding_mode(Rect::new(0, 0, 80, 17)),
            BrandingMode::Minimal
        );
    }

    #[test]
    fn modo_mapea_a_variante() {
        assert_eq!(BrandingMode::Full.variant(), LogoVariant::Full);
        assert_eq!(BrandingMode::Compact.variant(), LogoVariant::Compact);
        assert_eq!(BrandingMode::Minimal.variant(), LogoVariant::Mark);
    }
}
