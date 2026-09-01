//! Geometría del isotipo Cortex Voxel 3D Isométrico.
//!
//! Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`.
//! - Bloques superiores blancos/menta ('H' -> ICE, '#' -> TEXT)
//! - Núcleo brillante ('X' -> CYAN menta)
//! - Estantes inferiores esmeralda ('L' -> BLUE/CYAN)
//! - Sombras 3D ('S' -> DEEP sombra)

use crate::pixels::PixelMap;
use std::sync::OnceLock;

/// Variante del isotipo.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum LogoVariant {
    /// Splash/onboarding/empty states grandes: 44×34 px -> 44 cols x 17 filas.
    Full,
    /// Pantallas con menos espacio: 28×20 px -> 28 cols x 10 filas.
    Compact,
    /// Headers y sidebar: 13×10 px -> 13 cols x 5 filas.
    Mark,
}

pub(crate) const FULL_ROWS: &[&str] = &[
    "               HHHHHHHHHH                   ",
    "             HHHHHHHHHHHHHH                 ",
    "            HHHHHHHHHHHHHHHH                ",
    "             #################              ",
    "              #################             ",
    "               #################            ",
    "                #################           ",
    "                 #################          ",
    "                  #################         ",
    "                   #################        ",
    "                    #################       ",
    "                     #################      ",
    "                      #################     ",
    "                       #################    ",
    "  LLLLLLLLLLLL          #################   ",
    " LLLLLLLLLLLLLL          #################  ",
    "LLLLLLLLLLLLLLLL         XXXX############## ",
    "LLLLLLLLLLLLLLLL        XXXXXX############# ",
    " LLLLLLLLLLLLLL        XXXXXXXX###########  ",
    "  LLLLLLLLLLLL         XXXXXXXXX#########   ",
    "                       XXXXXXXXXX#######    ",
    " LLLLLLLLLLLLLL         XXXXXXXXXX#####     ",
    "LLLLLLLLLLLLLLLL         #########HH        ",
    "LLLLLLLLLLLLLLLL          ######HH          ",
    " LLLLLLLLLLLLLL            ####HH           ",
    "                            ##HH            ",
    "LLLLLLLLLLLLLLLLLL           HH             ",
    "LLLLLLLLLLLLLLLLLLL          HH             ",
    "LLLLLLLLLLLLLLLLLLLL         HH             ",
    " LLLLLLLLLLLLLLLLLL          HH             ",
    "  LLLLLLLLLLLLLLLL           HH             ",
    "   LLLLLLLLLLLLLL                           ",
    "     LLLLLLLLLL                             ",
    "       LLLLLL                               ",
];

pub(crate) const COMPACT_ROWS: &[&str] = &[
    "            HHHHHHHH        ",
    "          HHHHHHHHHHHH      ",
    "         HHHHHHHHHHHHHH     ",
    "          ##############    ",
    "           ##############   ",
    "            ##############  ",
    "             ############## ",
    "              ##############",
    " LLLLLLL       XXXXX########",
    "LLLLLLLLL     XXXXXXX###### ",
    "LLLLLLLLL      XXXXXXX####  ",
    " LLLLLLL        ####HHHH    ",
    "                 ##HH       ",
    "LLLLLLLLLL        HH        ",
    "LLLLLLLLLLL       HH        ",
    "LLLLLLLLLLLL      HH        ",
    " LLLLLLLLLL       HH        ",
    "  LLLLLLLL                  ",
    "    LLLL                    ",
    "     LL                     ",
];

pub(crate) const MARK_ROWS: &[&str] = &[
    "   HHHHH     ",
    "    #####    ",
    "     ####    ",
    "      ####   ",
    " LLL  XXXX   ",
    " LLL  XXXX#  ",
    "LLLLLL  ###  ",
    " LLLLL  ##   ",
    "  LLL   ##   ",
    "   L    ##   ",
];

/// Isotipo Full con glow periférico.
pub fn full() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| {
        let mut map = PixelMap::parse(FULL_ROWS);
        map.dilate_exterior_shadow();
        map
    })
}

/// Isotipo Compact.
pub fn compact() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| PixelMap::parse(COMPACT_ROWS))
}

/// Isotipo Mark.
pub fn mark() -> &'static PixelMap {
    static MASK: OnceLock<PixelMap> = OnceLock::new();
    MASK.get_or_init(|| PixelMap::parse(MARK_ROWS))
}

impl LogoVariant {
    pub fn pixel_map(self) -> &'static PixelMap {
        match self {
            LogoVariant::Full => full(),
            LogoVariant::Compact => compact(),
            LogoVariant::Mark => mark(),
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            LogoVariant::Full => "full",
            LogoVariant::Compact => "compact",
            LogoVariant::Mark => "mark",
        }
    }
}
