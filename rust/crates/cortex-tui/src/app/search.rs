//! Búsqueda de la TUI (spec §12/§11): la pantalla orquesta el MISMO motor
//! que `cortex search` (NativeMemory, en cortex-cli) a través de un trait
//! — la TUI no depende de embeddings ni duplica lógica de retrieval.
//!
//! El CLI inyecta el provider en `UiRequest::search` (adapter lazy: los
//! modelos se cargan recién en la primera búsqueda, nunca en el arranque
//! del Home). El feedback explícito ("marcar útil") espera el port nativo
//! del FeedbackCollector — anotado.

/// Hit de vista (traducción del `UnifiedHit` del motor, como `SessionRow`
/// traduce `SessionRecord`: la TUI ve solo lo que muestra).
#[derive(Clone, Debug, PartialEq)]
pub struct SearchHit {
    pub source: String,
    /// Score de presentación (fiel al oráculo: RRF para episódico, score
    /// crudo del documento para semántico).
    pub score: f64,
    pub title: String,
    pub path: String,
    /// id del hit episódico para feedback explícito ("marcar útil"); los
    /// hits semánticos no tienen id (el oráculo tampoco los marcaba).
    pub memory_id: Option<String>,
}

/// Resultado de una búsqueda (query + hits).
#[derive(Clone, Debug, PartialEq)]
pub struct SearchData {
    pub query: String,
    pub hits: Vec<SearchHit>,
}

/// Motor de búsqueda inyectado por la capa de servicios (cortex-cli).
pub trait SearchProvider: Send + Sync {
    fn search(&self, query: &str, top_k: usize) -> Result<Vec<SearchHit>, String>;

    /// Marca útil un hit episódico (persistido en `.cortex/feedback.jsonl`,
    /// el formato que consume `cortex-actions::signals`). Default: el motor
    /// no lo soporta — la TUI avisa.
    fn mark_useful(&self, _memory_id: &str) -> Result<(), String> {
        Err("feedback no disponible en este motor".to_string())
    }
}
