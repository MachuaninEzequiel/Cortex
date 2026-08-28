//! Splash de Cortex (prompt-logo.md §43): isotipo + wordmark + tagline.
//!
//! Composición centrada que respira (§42); el fondo NUNCA se pinta (§26):
//! el splash respeta la terminal del usuario. La tagline es un componente
//! separado del logo (§14).

use crate::renderer::{render_pixel_map, CortexLogo};
use crate::theme::Theme;
use crate::{branding_mode, lang, BrandingMode};
use cortex_branding::ansi::ColorMode;
use cortex_branding::wordmark::wordmark;
use ratatui::prelude::{Constraint, Layout, Rect};
use ratatui::widgets::{Paragraph, Widget};
use ratatui::Frame;

/// Tagline por idioma (componente separado del logo, prompt §14).
pub fn tagline(lang: &str) -> &'static str {
    match lang {
        "en" => "Memory · Governance · Context",
        _ => "Memoria · Gobernanza · Contexto",
    }
}

/// Renderiza el splash completo en el área del frame.
pub fn render(f: &mut Frame<'_>, mode: ColorMode) {
    let area = f.area();
    match branding_mode(area) {
        BrandingMode::Full => render_full(f, area, mode),
        BrandingMode::Compact => render_compact(f, area, mode),
        BrandingMode::Minimal => render_minimal(f, area, mode),
    }
}

fn render_full(f: &mut Frame<'_>, area: Rect, mode: ColorMode) {
    // isotipo (17 filas) + wordmark (4 filas) + tagline (1 fila), con aire.
    let [logo_area, word_area, tag_area] = Layout::vertical([
        Constraint::Length(19),
        Constraint::Length(5),
        Constraint::Length(2),
    ])
    .areas(area);
    f.render_widget(
        CortexLogo::new(crate::LogoVariant::Full).with_mode(mode),
        logo_area,
    );
    render_pixel_map(wordmark(), mode, word_area, f.buffer_mut());
    render_tagline(f, tag_area);
}

fn render_compact(f: &mut Frame<'_>, area: Rect, mode: ColorMode) {
    let [logo_area, word_area, tag_area] = Layout::vertical([
        Constraint::Length(11),
        Constraint::Length(2),
        Constraint::Length(2),
    ])
    .areas(area);
    f.render_widget(
        CortexLogo::new(crate::LogoVariant::Compact).with_mode(mode),
        logo_area,
    );
    render_wordmark_text(f, word_area);
    render_tagline(f, tag_area);
}

fn render_minimal(f: &mut Frame<'_>, area: Rect, mode: ColorMode) {
    let [logo_area, word_area] =
        Layout::vertical([Constraint::Length(6), Constraint::Length(2)]).areas(area);
    f.render_widget(
        CortexLogo::new(crate::LogoVariant::Mark).with_mode(mode),
        logo_area,
    );
    render_wordmark_text(f, word_area);
}

fn render_wordmark_text(f: &mut Frame<'_>, area: Rect) {
    let theme = Theme::new(crate::env_color_mode());
    Paragraph::new("C O R T E X")
        .style(theme.title())
        .centered()
        .render(area, f.buffer_mut());
}

fn render_tagline(f: &mut Frame<'_>, area: Rect) {
    let theme = Theme::new(crate::env_color_mode());
    Paragraph::new(tagline(lang()))
        .style(theme.muted())
        .centered()
        .render(area, f.buffer_mut());
}
