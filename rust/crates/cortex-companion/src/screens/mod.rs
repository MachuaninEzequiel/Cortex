//! Pantallas del Companion (G-B2b+): cada una renderiza sobre datos puros
//! y devuelve `AppRenderInfo` con los botones del frame (para el hit-test
//! del siguiente). El binario inyecta los backends; los render no tocan I/O.

pub mod home;

pub use home::{render_home, AppRenderInfo, BrandAssets, HomeAreas, HomeData};
