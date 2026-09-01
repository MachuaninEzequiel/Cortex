//! Puerto de `cortex.tutor.engine`: menú y navegación. Render plano
//! (divergencia cosmética documentada).

use crate::hint::ProjectState;
use crate::topics::get_all_topics;

/// Menú principal en texto plano (contenido idéntico al capturado).
pub fn render_menu() -> String {
    include_str!("../content/menu.txt").to_string()
}

/// `show_topic_by_slug`.
pub fn show_topic_by_slug(slug: &str) -> Option<String> {
    let slug_lower = slug.trim().to_lowercase();
    get_all_topics()
        .into_iter()
        .find(|t| t.slug == slug_lower)
        .map(|t| t.body.to_string())
}

/// Estado del proyecto reexportado para CLI futuro.
pub type State = ProjectState;
