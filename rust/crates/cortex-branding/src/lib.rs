//! cortex-branding — identidad visual de Cortex, PURA (sin dependencias).
//!
//! Traducción terminal-native del logo aprobado (`docs/logo/cortex-logo.png`,
//! contrato estético en `docs/logo/prompt-logo.md`): half-block rendering,
//! máscaras de píxeles separadas del gradiente, paleta monocromática
//! azul/cyan fría. La integración como `Widget` de ratatui vive en
//! `cortex-tui`; acá solo hay lógica de identidad reutilizable por cualquier
//! binario (brain, cli, tui) sin arrastrar dependencias pesadas.
//!
//! ```no_run
//! use cortex_branding::{ansi, logo::LogoVariant};
//!
//! let banner = ansi::render_ansi(LogoVariant::Compact.pixel_map(), ansi::env_color_mode());
//! print!("{banner}");
//! ```

pub mod ansi;
pub mod gradient;
pub mod logo;
pub mod palette;
pub mod pixels;
pub mod wordmark;

pub use palette::Rgb;
pub use pixels::{PixelKind, PixelMap};
