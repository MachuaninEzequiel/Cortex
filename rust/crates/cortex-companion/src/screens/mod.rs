//! Pantallas del Companion (G-B2b+): cada una renderiza sobre datos puros
//! y devuelve `AppRenderInfo` con los botones del frame (para el hit-test
//! del siguiente). El binario inyecta los backends; los render no tocan I/O.

pub mod home;
pub mod menu_screen;

pub use home::{render_home, AppRenderInfo as HomeRenderInfo, BrandAssets, HomeAreas, HomeData};
pub use menu_screen::{menu_areas, render_menu, AppRenderInfo as MenuRenderInfo, MenuAreas};
