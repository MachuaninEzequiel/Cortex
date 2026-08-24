//! Geometría del isotipo Cortex (prompt-logo.md §1-2, §30).
//!
//! Las máscaras son la FUENTE DE VERDAD del branding TUI: derivadas del PNG
//! aprobado (`docs/logo/cortex-logo.png`), curadas a mano y congeladas acá.
//! El PNG jamás se carga en runtime (prompt §35).
//!
//! Jerarquía visual al recortar (prompt §39): silueta C > X > layers >
//! gradiente > highlights > glow. `Mark` conserva C+X+insinuación de capas.

use crate::pixels::PixelMap;
use std::sync::OnceLock;

/// Variante del isotipo (prompt §13).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum LogoVariant {
    /// Splash/onboarding/empty states grandes: 44×34 px → 44 cols × 17 filas.
    Full,
    /// Pantallas con menos espacio: 28×20 px → 28 cols × 10 filas.
    Compact,
    /// Headers: 13×10 px → 13 cols × 5 filas.
    Mark,
}

// Generado desde docs/logo/cortex-logo.png (script desechable + curación a mano).
// '#'=Mark 'X'=Cross 'L'=Layer 'H'=Highlight. Filas cortas = padding transparente.
pub(crate) const FULL_ROWS: &[&str] = &[
    "                   HHHHHHHHHHHHHHHH",
    "                 ####################",
    "               ########################",
    "             ############################",
    "            ##########       ###########",
    "           #########            #########",
    "          ########                 #######",
    "         #######                      ###HH",
    "        ######                           HHH",
    " LLLLL  #####",
    "LLL     #####",
    "L       #####      XXXXX             XXXXX",
    "      LL#####      XXXXXXX         XXXXXXX",
    "   LLLLL#####      XXXXXXXX       XXXXXXXX",
    " LLLLL  #####        XXXXXXXX   XXXXXXXX",
    "LLL     #####          XXXXXXXXXXXXXXX",
    "L     LL#####            XXXXXXXXXXX",
    "   LLLLL#####             XXXXXXXXX",
    " LLLLL  #####            XXXXXXXXXXX",
    "LLL     #####          XXXXXXXXXXXXXXX",
    "L       #####        XXXXXXXX   XXXXXXXX",
    "      LL#####      XXXXXXXX       XXXXXXXX",
    "   LLLLL#####      XXXXXXX         XXXXXXX",
    " LLLLL  #####      XXXXX             XXXXX",
    "LLL     #####",
    "L       ######                           HHH",
    "         #######                      ##HHH",
    "          ########                 #######",
    "           #########            #########",
    "            ##########       ###########",
    "             ############################",
    "               ########################",
    "                 ####################",
    "                   ################",
];

pub(crate) const COMPACT_ROWS: &[&str] = &[
    "            HHHHHHHHHHH",
    "          ###############",
    "        ######    #######",
    "       #####        ######",
    "      ####            #####",
    "LLLLL###                ####",
    "     ###    XXX         XXX",
    "     ###    XXXXX     XXXXX",
    "LLLLL###     XXXXXX XXXXXX",
    "     ###       XXXXXXXXX",
    "     ###         XXXXX",
    "LLLLL###       XXXXXXXXX",
    "     ###     XXXXXX XXXXXX",
    "     ###    XXXXX     XXXXX",
    "LLLLL###    XXX         ####",
    "      ####            #####",
    "       #####        ######",
    "        ######    #######",
    "          ###############",
    "            ###########",
];

pub(crate) const MARK_ROWS: &[&str] = &[
    "    #######",
    "  ##########",
    " ## XX XX #",
    "L##  XXXX   #",
    "LL#   XX",
    "L##   XX",
    "L##  XXXX   #",
    "L## XX XX #",
    "  ##########",
    "    #######",
];

/// Isotipo Full con glow periférico (prompt §22), computado una sola vez.
pub fn full() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| {
        let mut map = PixelMap::parse(FULL_ROWS);
        map.dilate_exterior_shadow();
        map
    })
}

/// Isotipo Compact: sin glow (el espacio es apretado, prompt §16).
pub fn compact() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| PixelMap::parse(COMPACT_ROWS))
}

/// Isotipo Mark: C + X + una insinuación de capas (prompt §17).
pub fn mark() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| PixelMap::parse(MARK_ROWS))
}

impl LogoVariant {
    /// Máscara de píxeles de la variante.
    pub fn pixel_map(self) -> &'static PixelMap {
        match self {
            LogoVariant::Full => full(),
            LogoVariant::Compact => compact(),
            LogoVariant::Mark => mark(),
        }
    }

    /// Etiqueta estable para tests y métricas.
    pub fn label(self) -> &'static str {
        match self {
            LogoVariant::Full => "full",
            LogoVariant::Compact => "compact",
            LogoVariant::Mark => "mark",
        }
    }
}
