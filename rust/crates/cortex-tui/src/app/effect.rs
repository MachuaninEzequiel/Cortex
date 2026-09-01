//! Efectos (spec §2/§5): el reducer puede devolver efectos pero NUNCA
//! ejecutarlos. El runtime (loop de la pantalla) los interpreta y devuelve
//! acciones tipadas (`SessionsLoaded`/`SessionsFailed`, más adelante
//! `TaskEvent`).

/// Trabajo externo descrito por el reducer.
#[derive(Clone, Debug, PartialEq)]
pub enum Effect {
    /// Cerrar la TUI (restauración RAII).
    Quit,
    /// Cargar el detalle de la sesión (ejecutado por el runtime; el
    /// resultado vuelve como `SessionDetailLoaded`).
    LoadSessionDetail { id: String },
    /// Ejecutar la acción propuesta en `index` (runner del ActionEngine,
    /// fuera del reducer; el resultado vuelve como `ActionFinished`).
    RunAction { index: usize },
    /// Buscar con el motor inyectado (`UiRequest::search`); el resultado
    /// vuelve como `SearchLoaded` / `SearchFailed`.
    Search { query: String },
    /// Marcar útil un hit episódico (persistido en feedback.jsonl).
    MarkUseful { memory_id: String },
    /// Copiar texto al portapapeles vía OSC 52 (compatible SSH/remoto).
    CopyToClipboard { text: String },
    /// No hay trabajo externo.
    None,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn efectos_son_comparables() {
        assert_eq!(Effect::Quit, Effect::Quit);
        assert_ne!(Effect::Quit, Effect::None);
    }
}
