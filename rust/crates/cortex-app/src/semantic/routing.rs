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

// ---------------------------------------------------------------------------
// RouteSpec serializable — `cortex docs routing-table` (MITAD B, ruta 1)
//
// Porte completo de `cortex/documentation/routing.py::RouteSpec` + la tabla
// canónica DOC_TYPE_ROUTING con los writers ya vinculados en
// `cortex/documentation/__init__.py` (Fase 03/04 + Phase 09.B). Campos
// exactos del oráculo para byte-parity del CLI.
// ---------------------------------------------------------------------------

/// Spec canónico por DocType (espejo del dataclass `RouteSpec`).
#[derive(Debug, Clone)]
pub struct RouteSpec {
    pub doc_type: DocType,
    pub subfolder: &'static str,
    pub filename_template: &'static str,
    /// `str(template_path)`: espejo de `TEMPLATES_DIR / f"{value}.md.j2"`
    /// resuelto en el repo Python (ruta absoluta de compilación).
    pub template_path: String,
    /// Nombre de la función writer (`getattr(writer, "__name__", …)`);
    /// en la tabla vinculada todos los doc_types tienen writer.
    pub writer: &'static str,
    pub indexer: &'static str,
    pub promotable: bool,
    pub promotion_mode: &'static str,
    pub enterprise_subfolder: Option<&'static str>,
    pub retrieval_boost_per_intent: Vec<(&'static str, f64)>,
    pub chunking_enabled: bool,
    pub chunking_min_words: usize,
    pub chunking_boundary: &'static str,
    pub webgraph_color: &'static str,
    pub webgraph_shape: &'static str,
    pub requires_review_before_publish: bool,
    pub auto_expire_days: usize,
}

/// Raíz del repo Cortex (3 ancestros del manifest de cortex-app).
fn repo_root() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| std::path::PathBuf::from("."))
}

fn template_path(value: &str) -> String {
    repo_root()
        .join("cortex")
        .join("documentation")
        .join("templates")
        .join(format!("{value}.md.j2"))
        .to_string_lossy()
        .into_owned()
}

fn boost(items: &[(&'static str, f64)]) -> Vec<(&'static str, f64)> {
    items.to_vec()
}

/// Tabla canónica DOC_TYPE_ROUTING completa, orden de declaración del
/// oráculo (orden del enum DocType = orden de `list_all_routes`).
pub fn route_spec(dt: DocType) -> RouteSpec {
    use DocType::*;
    let value = dt.value();
    match dt {
        Session => RouteSpec {
            doc_type: dt,
            subfolder: "sessions",
            filename_template: "{session_id}_{slug}.md",
            template_path: template_path(value),
            writer: "write_session_note_canonical",
            indexer: "auto",
            promotable: true,
            promotion_mode: "summarize",
            enterprise_subfolder: Some("sessions/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("history", 1.3),
                ("recent", 1.5),
                ("episodic", 1.4),
            ]),
            chunking_enabled: false,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#88aaff",
            webgraph_shape: "rectangle",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Handoff => RouteSpec {
            doc_type: dt,
            subfolder: "handoffs",
            filename_template: "{date}_{slug}.md",
            template_path: template_path(value),
            writer: "write_handoff_note",
            indexer: "auto",
            promotable: false,
            promotion_mode: "as-is",
            enterprise_subfolder: None,
            retrieval_boost_per_intent: boost(&[("recent", 2.0), ("history", 1.0)]),
            chunking_enabled: false,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#ffaa44",
            webgraph_shape: "diamond",
            requires_review_before_publish: false,
            auto_expire_days: 14,
        },
        Spec => RouteSpec {
            doc_type: dt,
            subfolder: "specs",
            filename_template: "{date}_{slug}.md",
            template_path: template_path(value),
            writer: "write_spec_note_canonical",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("specs/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("spec", 2.0),
                ("requirements", 1.8),
                ("implementation", 1.4),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#88ddaa",
            webgraph_shape: "rectangle",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Adr => RouteSpec {
            doc_type: dt,
            subfolder: "decisions",
            filename_template: "ADR-{number:03d}-{slug}.md",
            template_path: template_path(value),
            writer: "write_adr_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("decisions/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("decision", 2.0),
                ("architecture", 1.5),
                ("history", 1.2),
                ("rationale", 1.8),
            ]),
            chunking_enabled: true,
            chunking_min_words: 400,
            chunking_boundary: "h2",
            webgraph_color: "#cc66ff",
            webgraph_shape: "hexagon",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Decision => RouteSpec {
            doc_type: dt,
            subfolder: "decisions",
            filename_template: "DEC-{date}-{slug}.md",
            template_path: template_path(value),
            writer: "write_decision_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("decisions/{project_id}"),
            retrieval_boost_per_intent: boost(&[("decision", 1.5), ("history", 1.2)]),
            chunking_enabled: false,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#aa88cc",
            webgraph_shape: "hexagon",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Incident => RouteSpec {
            doc_type: dt,
            subfolder: "incidents",
            filename_template: "INC-{number:03d}-{date}-{slug}.md",
            template_path: template_path(value),
            writer: "write_incident_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("incidents/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("incident", 2.5),
                ("recent", 2.0),
                ("history", 1.5),
                ("runbook", 1.3),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#ff6666",
            webgraph_shape: "diamond",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Postmortem => RouteSpec {
            doc_type: dt,
            subfolder: "postmortems",
            filename_template: "PM-{incident_number:03d}-{slug}.md",
            template_path: template_path(value),
            writer: "write_postmortem_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("postmortems/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("postmortem", 2.5),
                ("incident", 2.0),
                ("root-cause", 2.2),
                ("history", 1.5),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#aa4444",
            webgraph_shape: "diamond",
            requires_review_before_publish: true,
            auto_expire_days: 0,
        },
        Runbook => RouteSpec {
            doc_type: dt,
            subfolder: "runbooks",
            filename_template: "RB-{slug}.md",
            template_path: template_path(value),
            writer: "write_runbook_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "review-required",
            enterprise_subfolder: Some("runbooks/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("runbook", 2.5),
                ("procedure", 2.0),
                ("deploy", 1.8),
                ("rollback", 1.8),
                ("operations", 1.5),
            ]),
            chunking_enabled: true,
            chunking_min_words: 400,
            chunking_boundary: "h2",
            webgraph_color: "#66cccc",
            webgraph_shape: "rectangle",
            requires_review_before_publish: true,
            auto_expire_days: 180,
        },
        Architecture => RouteSpec {
            doc_type: dt,
            subfolder: "architecture",
            filename_template: "{slug}.md",
            template_path: template_path(value),
            writer: "write_architecture_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("architecture/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("architecture", 2.5),
                ("design", 2.0),
                ("decision", 1.5),
                ("overview", 1.5),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#6688cc",
            webgraph_shape: "rectangle",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Changelog => RouteSpec {
            doc_type: dt,
            subfolder: "changelog",
            filename_template: "{version}.md",
            template_path: template_path(value),
            writer: "write_changelog_note",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("changelog/{project_id}"),
            retrieval_boost_per_intent: boost(&[
                ("changelog", 1.5),
                ("release", 1.5),
                ("version", 1.5),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#999999",
            webgraph_shape: "rectangle",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Hu => RouteSpec {
            doc_type: dt,
            subfolder: "hu",
            filename_template: "HU-{external_id}.md",
            template_path: template_path(value),
            writer: "write_hu_note",
            indexer: "auto",
            promotable: false,
            promotion_mode: "as-is",
            enterprise_subfolder: None,
            retrieval_boost_per_intent: boost(&[
                ("task", 1.3),
                ("requirements", 1.4),
                ("current-work", 1.5),
            ]),
            chunking_enabled: false,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#ccaa66",
            webgraph_shape: "ellipse",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Glossary => RouteSpec {
            doc_type: dt,
            subfolder: "glossary",
            filename_template: "{term_slug}.md",
            template_path: template_path(value),
            writer: "write_glossary_entry",
            indexer: "auto",
            promotable: true,
            promotion_mode: "as-is",
            enterprise_subfolder: Some("glossary"),
            retrieval_boost_per_intent: boost(&[
                ("glossary", 2.0),
                ("definition", 2.5),
                ("term", 2.5),
            ]),
            chunking_enabled: false,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#cccc66",
            webgraph_shape: "ellipse",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
        Design => RouteSpec {
            doc_type: dt,
            subfolder: "designs",
            filename_template: "{session_id}.md",
            template_path: template_path(value),
            writer: "write_design_note",
            indexer: "auto",
            promotable: false,
            promotion_mode: "as-is",
            enterprise_subfolder: None,
            retrieval_boost_per_intent: boost(&[
                ("design", 2.5),
                ("architecture", 1.8),
                ("decision", 1.5),
            ]),
            chunking_enabled: true,
            chunking_min_words: 500,
            chunking_boundary: "h2",
            webgraph_color: "#66aaee",
            webgraph_shape: "rectangle",
            requires_review_before_publish: false,
            auto_expire_days: 0,
        },
    }
}

/// `list_all_routes()` del oráculo (orden de declaración).
pub fn list_all_routes() -> Vec<RouteSpec> {
    use DocType::*;
    [
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
    ]
    .iter()
    .map(|d| route_spec(*d))
    .collect()
}

/// `DocType(slug)` de Python: parse de un valor de slug conocido.
pub fn parse_doc_type(raw: &str) -> Option<DocType> {
    use DocType::*;
    match raw {
        "session" => Some(Session),
        "handoff" => Some(Handoff),
        "spec" => Some(Spec),
        "adr" => Some(Adr),
        "decision" => Some(Decision),
        "incident" => Some(Incident),
        "postmortem" => Some(Postmortem),
        "runbook" => Some(Runbook),
        "architecture" => Some(Architecture),
        "changelog" => Some(Changelog),
        "hu" => Some(Hu),
        "glossary" => Some(Glossary),
        "design" => Some(Design),
        _ => None,
    }
}

/// Los 13 slugs válidos en orden del enum (para el mensaje de error).
pub const DOC_TYPE_VALID_SLUGS: [&str; 13] = [
    "session",
    "handoff",
    "spec",
    "adr",
    "decision",
    "incident",
    "postmortem",
    "runbook",
    "architecture",
    "changelog",
    "hu",
    "glossary",
    "design",
];
