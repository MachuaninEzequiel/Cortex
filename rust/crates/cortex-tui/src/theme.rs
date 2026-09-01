//! Única fuente de estilos del chrome TUI (spec §7.2).
//!
//! Regla del rediseño: ningún `Color::Rgb(...)` fuera de `theme.rs` y
//! `renderer.rs` (test de higiene en `tests/theme_hygiene.rs`). Los
//! colores se resuelven acá según `ColorMode` (truecolor / 16 / plain) y
//! se entregan como `Style` o `Block` ya listos para el render.
//!
//! Semántica (spec §7.1): el azul identifica selección/actividad; los
//! colores semánticos (success/warning/error) solo para estados, siempre
//! acompañados de símbolo y texto (no dependen solo del color).

use catppuccin::PALETTE;
use cortex_branding::ansi::ColorMode;
use ratatui::prelude::{Color, Modifier, Style};
use ratatui::widgets::{Block, BorderType, Borders};

/// Categoría de estado semántico (spec §7.4: símbolo + color siempre).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum StatusKind {
    /// Activo / en curso (identidad de marca).
    Active,
    /// Pendiente, neutro.
    Pending,
    /// Éxito.
    Success,
    /// Advertencia.
    Warning,
    /// Error.
    Error,
}

impl StatusKind {
    /// Glifo único por estado (vocabulario cerrado, spec §7.4).
    pub const fn glyph(self) -> &'static str {
        match self {
            StatusKind::Active => "●",
            StatusKind::Pending => "○",
            StatusKind::Success => "✓",
            StatusKind::Warning => "!",
            StatusKind::Error => "×",
        }
    }
}

/// Tema del chrome TUI centralizado en Catppuccin Mocha (spec §3).
#[derive(Clone, Copy, Debug)]
pub struct Theme {
    pub bg: Color,
    pub surface: Color,
    pub mantle: Color,
    pub crust: Color,
    pub text: Color,
    pub text_primary: Color,
    pub text_muted: Color,
    /// Énfasis suave (lavender).
    pub accent_soft: Color,
    /// Selección / indicadores activos (mauve).
    pub accent: Color,
    /// Acento fuerte (blue).
    pub accent_strong: Color,
    /// Foco activo (green).
    pub focus: Color,
    pub muted: Color,
    /// Borde sin foco (surface2).
    pub border_idle: Color,
    /// Borde con foco (green / accent).
    pub border_focus: Color,
    /// Fondo de selección.
    pub selection_bg: Color,
    pub success: Color,
    pub warning: Color,
    pub error: Color,
    /// 3D Wordmark Highlight (bisel superior/izquierdo, blanco hielo #C8F0DC)
    pub wordmark_highlight: Color,
    /// 3D Wordmark Face (cara frontal, sky #89DCEB)
    pub wordmark_face: Color,
    /// 3D Wordmark Shadow (extrusión 3D derecha/inferior, zafiro #04A5E5)
    pub wordmark_shadow: Color,
    /// 3D Wordmark Deep (esquinas y sombra lejana, navy #1E3A5F)
    pub wordmark_deep: Color,
}

impl Default for Theme {
    fn default() -> Self {
        let mocha = &PALETTE.mocha.colors;
        let bg = Color::from(mocha.base);
        let surface = Color::from(mocha.surface0);
        let mantle = Color::from(mocha.mantle);
        let crust = Color::from(mocha.crust);
        let text = Color::from(mocha.text);
        let text_muted = Color::from(mocha.subtext0);
        let accent = Color::from(mocha.mauve);
        let accent_soft = Color::from(mocha.lavender);
        let accent_strong = Color::from(mocha.blue);
        let focus = Color::from(mocha.mauve);
        let muted = Color::from(mocha.overlay0);
        let error = Color::from(mocha.red);
        let success = Color::from(mocha.green);
        let warning = Color::from(mocha.yellow);
        let border_idle = Color::from(mocha.surface2);
        let border_focus = Color::from(mocha.mauve);
        let selection_bg = Color::from(mocha.surface1);
        // Paleta fría del wordmark (no la menta del isotipo): hielo/sky/zafiro/navy.
        let wordmark_highlight = Color::Rgb(0xC8, 0xF0, 0xDC);
        let wordmark_face = Color::from(mocha.sky);
        let wordmark_shadow = Color::Rgb(0x04, 0xA5, 0xE5);
        let wordmark_deep = Color::Rgb(0x1E, 0x3A, 0x5F);

        Self {
            bg,
            surface,
            mantle,
            crust,
            text,
            text_primary: text,
            text_muted,
            accent_soft,
            accent,
            accent_strong,
            focus,
            muted,
            border_idle,
            border_focus,
            selection_bg,
            success,
            warning,
            error,
            wordmark_highlight,
            wordmark_face,
            wordmark_shadow,
            wordmark_deep,
        }
    }
}

impl Theme {
    pub fn new(mode: ColorMode) -> Self {
        match mode {
            ColorMode::Plain => {
                let mut t = Self::default();
                t.text_primary = Color::Reset;
                t.text = Color::Reset;
                t.selection_bg = Color::Reset;
                t.border_idle = Color::Reset;
                t.border_focus = Color::Reset;
                t
            }
            _ => Self::default(),
        }
    }

    /// Estilo de borde según estado de foco (spec §3 / §4).
    pub fn border(&self, focused: bool) -> Style {
        if focused {
            Style::default().fg(self.focus).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(self.muted)
        }
    }

    /// Color del estado semántico.
    pub fn status_color(&self, kind: StatusKind) -> Color {
        match kind {
            StatusKind::Active => self.accent,
            StatusKind::Pending => self.text_muted,
            StatusKind::Success => self.success,
            StatusKind::Warning => self.warning,
            StatusKind::Error => self.error,
        }
    }

    // ── estilos semánticos ──────────────────────────────────────────────

    pub fn title(&self) -> Style {
        Style::default()
            .fg(self.accent_soft)
            .add_modifier(Modifier::BOLD)
    }

    pub fn subtitle(&self) -> Style {
        Style::default().fg(self.text_muted)
    }

    pub fn body(&self) -> Style {
        Style::default().fg(self.text_primary)
    }

    pub fn muted(&self) -> Style {
        Style::default().fg(self.text_muted)
    }

    /// Tecla de atajo: cyan, sin negrita (spec §10: tecla en azul suave).
    pub fn shortcut_key(&self) -> Style {
        Style::default().fg(self.accent)
    }

    /// Descripción del atajo: muted.
    pub fn shortcut_label(&self) -> Style {
        Style::default().fg(self.text_muted)
    }

    /// Fila seleccionada: acento + negrita, con fondo sutil si hay color real.
    pub fn selected(&self) -> Style {
        let mut s = Style::default()
            .fg(self.accent)
            .add_modifier(Modifier::BOLD);
        if self.selection_bg != Color::Reset {
            s = s.bg(self.selection_bg);
        }
        s
    }

    /// Texto deshabilitado / no aplica.
    pub fn disabled(&self) -> Style {
        Style::default().fg(self.text_muted)
    }

    // ── bloques ─────────────────────────────────────────────────────────

    /// Panel principal: borde redondeado, idle/focus (spec §7.1: máximo dos
    /// estilos de borde; Rounded para paneles principales).
    pub fn panel_block<'a>(&self, title: &'a str, focused: bool) -> Block<'a> {
        Block::bordered()
            .border_type(BorderType::Rounded)
            .border_style(if focused {
                self.border_focus
            } else {
                self.border_idle
            })
            .title(title)
            .title_style(self.subtitle())
    }

    /// Subdivisión: borde plano mínimo (nunca compite con el panel principal).
    pub fn sub_block<'a>(&self, title: &'a str, focused: bool) -> Block<'a> {
        Block::bordered()
            .border_type(BorderType::Plain)
            .border_style(if focused {
                self.border_focus
            } else {
                self.border_idle
            })
            .title(title)
            .title_style(self.subtitle())
    }

    /// Modal de confirmación; `critical` usa borde doble (spec §7.1: Double
    /// solo para confirmaciones críticas).
    pub fn modal_block<'a>(&self, title: &'a str, critical: bool) -> Block<'a> {
        Block::bordered()
            .border_type(if critical {
                BorderType::Double
            } else {
                BorderType::Rounded
            })
            .border_style(self.border_focus)
            .title(title)
            .title_style(self.title())
    }

    /// Borde superior fino para tablas/streams (sin cajas anidadas).
    pub fn top_rule(&self) -> Block<'static> {
        Block::new()
            .borders(Borders::TOP)
            .border_style(self.border_idle)
    }
}

/// Texto de marca para headers angostos (spec §8: bajo el ancho del Mark se
/// oculta el isotipo y se muestra CORTEX como texto accesible).
pub fn brand_text(style: Style) -> ratatui::text::Line<'static> {
    ratatui::text::Line::from(ratatui::text::Span::styled(
        "CORTEX",
        style.add_modifier(Modifier::BOLD),
    ))
}

/// Ancho mínimo que necesita el Mark para ser legible (13 px) + 1 de aire
/// por lado. Debajo, el header usa texto "CORTEX".
pub const MARK_MIN_WIDTH: u16 = 15;
