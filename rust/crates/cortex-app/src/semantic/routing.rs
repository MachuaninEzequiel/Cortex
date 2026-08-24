//! Puerto de la resolución de DocType + tabla de routing de retrieval.
//!
//! Fuentes de verdad: `cortex/documentation/doc_type.py` (valores),
//! `cortex/documentation/routing.py` (RouteSpec) y
//! `cortex/semantic/vault_reader.py::_resolve_doc_type` (heurística por
//! primer segmento de directorio + regla ADR-*).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocType {
    Session,
    Handoff,
    Spec,
    Adr,
    Decision,
    Incident,
    Postmortem,
    Runbook,
    Architecture,
    Changelog,
    Hu,
    Glossary,
    Design,
}

impl DocType {
    /// `.value` del enum Python (entra al embedding_text).
    pub fn value(self) -> &'static str {
        match self {
            Self::Session => "session",
            Self::Handoff => "handoff",
            Self::Spec => "spec",
            Self::Adr => "adr",
            Self::Decision => "decision",
            Self::Incident => "incident",
            Self::Postmortem => "postmortem",
            Self::Runbook => "runbook",
            Self::Architecture => "architecture",
            Self::Changelog => "changelog",
            Self::Hu => "hu",
            Self::Glossary => "glossary",
            Self::Design => "design",
        }
    }
}

/// Parámetros de retrieval del RouteSpec (lo único que el indexador usa).
#[derive(Debug, Clone, Copy)]
pub struct Route {
    pub chunking_enabled: bool,
    pub min_words: usize,
    pub boundary_h3: bool,
}

/// Tabla canónica DOC_TYPE_ROUTING — sólo campos de retrieval.
pub fn route(dt: DocType) -> Route {
    use DocType::*;
    match dt {
        Session => Route {
            chunking_enabled: false,
            min_words: 0,
            boundary_h3: false,
        },
        Handoff => Route {
            chunking_enabled: false,
            min_words: 0,
            boundary_h3: false,
        },
        Spec => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
        Adr => Route {
            chunking_enabled: true,
            min_words: 400,
            boundary_h3: false,
        },
        Decision => Route {
            chunking_enabled: false,
            min_words: 0,
            boundary_h3: false,
        },
        Incident => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
        Postmortem => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
        Runbook => Route {
            chunking_enabled: true,
            min_words: 400,
            boundary_h3: false,
        },
        Architecture => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
        Changelog => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
        Hu => Route {
            chunking_enabled: false,
            min_words: 0,
            boundary_h3: false,
        },
        Glossary => Route {
            chunking_enabled: false,
            min_words: 0,
            boundary_h3: false,
        },
        Design => Route {
            chunking_enabled: true,
            min_words: 500,
            boundary_h3: false,
        },
    }
}

/// Puerto de `_resolve_doc_type`: primer directorio + regla ADR-*.
/// Devuelve None para archivos en la raíz o directorios desconocidos
/// (el llamador cae a single-chunk GLOSSARY, igual que Python).
pub fn doc_type_from_rel(rel: &str) -> Option<DocType> {
    let mut parts = rel.split('/');
    let first = parts.next()?;
    let file = parts.next()?;
    if parts.next().is_some() {
        // >2 niveles: el mapeo de Python sólo mira el primer segmento; los
        // sub-niveles profundos no están en el mapping ⇒ None.
        // (Python: mapping.get(first) sobre len(parts)>=2 — igual resultado.)
    }
    use DocType::*;
    match first {
        "sessions" => Some(Session),
        "handoffs" => Some(Handoff),
        "specs" => Some(Spec),
        "decisions" => {
            let stem = file.strip_suffix(".md").unwrap_or(file);
            if stem.to_uppercase().starts_with("ADR-") {
                Some(Adr)
            } else {
                Some(Decision)
            }
        }
        "incidents" => Some(Incident),
        "postmortems" => Some(Postmortem),
        "runbooks" => Some(Runbook),
        "architecture" => Some(Architecture),
        "changelog" => Some(Changelog),
        "hu" => Some(Hu),
        "glossary" => Some(Glossary),
        _ => None,
    }
}
