//! Tema del Companion: los MISMOS tokens Catppuccin Mocha de `cortex-tui`
//! (spec §3 del rediseño), resueltos vía el crate `catppuccin`.
//!
//! Regla de higiene idéntica a la TUI: ningún `Color::Rgb(...)` de chrome
//! fuera de `theme.rs` (los tokens fríos del wordmark viven en
//! `cortex_branding::wordmark`). El verde menta de `cortex_branding::palette`
//! queda SOLO para el isotipo del logo; todo el chrome usa mauve/sky/lavender.

use catppuccin::PALETTE;
use ratatui::prelude::Color;

macro_rules! token {
    ($name:ident, $field:ident, $doc:expr) => {
        #[doc = $doc]
        pub fn $name() -> Color {
            Color::from(PALETTE.mocha.colors.$field)
        }
    };
}

token!(bg, base, "Fondo base (#1E1E2E).");
token!(mantle, mantle, "Barra de estado / pop-down.");
token!(crust, crust, "Fondo más profundo.");
token!(surface, surface0, "Superficie de paneles (#313244).");
token!(surface1, surface1, "Selección sutil.");
token!(surface2, surface2, "Borde inactivo (#585B70).");
token!(overlay0, overlay0, "Deshabilitado.");
token!(text, text, "Texto principal (#CDD6F4).");
token!(text_muted, subtext0, "Texto secundario (#A6ADC8).");
token!(accent, mauve, "Acento de marca / selección (#CBA6F7).");
token!(accent_soft, lavender, "Énfasis suave (#B4BEFE).");
token!(accent_strong, blue, "Acento fuerte (#89B4FA).");
token!(sky, sky, "Cielo del wordmark (#89DCEB).");
token!(success, green, "Éxito.");
token!(warning, yellow, "Advertencia.");
token!(error, red, "Error.");

/// Borde de panel inactivo.
pub fn border_idle() -> Color {
    surface2()
}
/// Borde de panel enfocado/hover (mauve).
pub fn border_focus() -> Color {
    accent()
}
/// Fondo de selección sutil.
pub fn selection_bg() -> Color {
    surface1()
}
