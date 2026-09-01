//! Capa `app` del crate (spec §2/§5): estado + acciones semánticas +
//! reducer puro + efectos. El render nunca inicia procesos ni muta el
//! dominio; el runtime ejecuta los efectos y devuelve acciones tipadas.
//!
//! En F2 la única pantalla operativa es Sesiones; el `AppState` ya tiene
//! la forma final (screen, overlay, foco, selección con scroll, notifs,
//! should_quit) para que F4 agregue Home/Acciones/Búsqueda sin reescribir.

pub mod action;
pub mod effect;
pub mod runtime;
pub mod search;
pub mod state;
pub mod update;

pub use action::Action;
pub use effect::Effect;
pub use runtime::{run, snapshot, UiRequest};
pub use search::{SearchData, SearchHit, SearchProvider};
pub use state::{AppState, LoadState, Notification, Overlay, Screen};
pub use update::{copy_selection, update};
