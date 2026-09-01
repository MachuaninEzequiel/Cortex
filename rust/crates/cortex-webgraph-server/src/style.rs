//! Estilos del WebGraph — porteo de `cortex/webgraph/style.py` +
//! `infer_doc_type_from_path` (doc_type.py Fase 13) + tabla webgraph_color/
//! shape de `cortex/documentation/routing.py`.

#![forbid(unsafe_code)]

use cortex_setup::doc_type::DocType;

pub const DEFAULT_NODE_COLOR: &str = "#cccccc";
pub const DEFAULT_NODE_SHAPE: &str = "ellipse";

/// Orden de declaración del enum DocType de Python (iteración del legend).
const DOC_TYPE_ORDER: &[&str] = &[
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NodeStyle {
    pub color: &'static str,
    pub shape: &'static str,
}

const EXTRA_EPISODIC: NodeStyle = NodeStyle {
    color: "#9b59b6",
    shape: "diamond",
};

/// Colores/formas webgraph por DocType (DOC_TYPE_ROUTING de routing.py).
fn route_style(doc_type: DocType) -> Option<NodeStyle> {
    Some(match doc_type {
        DocType::Session => NodeStyle {
            color: "#88aaff",
            shape: "rectangle",
        },
        DocType::Handoff => NodeStyle {
            color: "#ffaa44",
            shape: "diamond",
        },
        DocType::Spec => NodeStyle {
            color: "#88ddaa",
            shape: "rectangle",
        },
        DocType::Adr => NodeStyle {
            color: "#cc66ff",
            shape: "hexagon",
        },
        DocType::Decision => NodeStyle {
            color: "#aa88cc",
            shape: "hexagon",
        },
        DocType::Incident => NodeStyle {
            color: "#ff6666",
            shape: "diamond",
        },
        DocType::Postmortem => NodeStyle {
            color: "#aa4444",
            shape: "diamond",
        },
        DocType::Runbook => NodeStyle {
            color: "#66cccc",
            shape: "rectangle",
        },
        DocType::Architecture => NodeStyle {
            color: "#6688cc",
            shape: "rectangle",
        },
        DocType::Changelog => NodeStyle {
            color: "#999999",
            shape: "rectangle",
        },
        DocType::Hu => NodeStyle {
            color: "#ccaa66",
            shape: "ellipse",
        },
        DocType::Glossary => NodeStyle {
            color: "#cccc66",
            shape: "ellipse",
        },
        DocType::Design => NodeStyle {
            color: "#66aaee",
            shape: "rectangle",
        },
    })
}

/// style_for_doc_type: acepta slug str o None; desconocido ⇒ gris elipse.
pub fn style_for_doc_type(doc_type: Option<&str>) -> NodeStyle {
    let Some(slug) = doc_type else {
        return NodeStyle {
            color: DEFAULT_NODE_COLOR,
            shape: DEFAULT_NODE_SHAPE,
        };
    };
    if slug == "episodic" {
        return EXTRA_EPISODIC;
    }
    match DocType::parse(slug) {
        Some(dt) => route_style(dt).unwrap_or(NodeStyle {
            color: DEFAULT_NODE_COLOR,
            shape: DEFAULT_NODE_SHAPE,
        }),
        None => NodeStyle {
            color: DEFAULT_NODE_COLOR,
            shape: DEFAULT_NODE_SHAPE,
        },
    }
}

// ── edge types ──────────────────────────────────────────────────────────────

pub struct EdgeStyle {
    pub name: &'static str,
    pub color: &'static str,
    pub style: &'static str,
    pub label: &'static str,
}

/// EDGE_TYPES en orden de declaración (el legend conserva este orden).
pub const EDGE_TYPES: &[EdgeStyle] = &[
    EdgeStyle {
        name: "wiki_link",
        color: "#666666",
        style: "solid",
        label: "links to",
    },
    EdgeStyle {
        name: "co_occurrence",
        color: "#aaaaaa",
        style: "dashed",
        label: "co-occurs",
    },
    EdgeStyle {
        name: "imports",
        color: "#88aaff",
        style: "solid",
        label: "imports",
    },
    EdgeStyle {
        name: "tested_by",
        color: "#88dd88",
        style: "dotted",
        label: "tested by",
    },
    EdgeStyle {
        name: "supersedes",
        color: "#dd6666",
        style: "solid",
        label: "supersedes",
    },
    EdgeStyle {
        name: "superseded_by",
        color: "#9e9e9e",
        style: "dotted",
        label: "superseded by",
    },
    EdgeStyle {
        name: "promoted_from",
        color: "#aa66cc",
        style: "dashed",
        label: "promoted from",
    },
];

/// style_for_edge: desconocido ⇒ gris sólido con label=tipo.
pub fn style_for_edge(edge_type: &str) -> (String, String, String) {
    match EDGE_TYPES.iter().find(|e| e.name == edge_type) {
        Some(e) => (
            e.color.to_string(),
            e.style.to_string(),
            e.label.to_string(),
        ),
        None => (
            DEFAULT_NODE_COLOR.to_string(),
            "solid".to_string(),
            edge_type.to_string(),
        ),
    }
}

/// build_legend(): {"doc_types": [...], "edge_types": [...]}.
pub fn build_legend() -> serde_json::Value {
    use serde_json::{json, Map, Value};
    let mut doc_types: Vec<Value> = Vec::new();
    for entry in DOC_TYPE_ORDER {
        let style = style_for_doc_type(Some(entry));
        let mut m = Map::new();
        m.insert("type".into(), Value::String((*entry).into()));
        m.insert("color".into(), Value::String(style.color.into()));
        m.insert("shape".into(), Value::String(shape_shape(style.shape)));
        doc_types.push(Value::Object(m));
    }
    // Sintético episodic (Item #6).
    let mut m = Map::new();
    m.insert("type".into(), Value::String("episodic".into()));
    m.insert("color".into(), Value::String(EXTRA_EPISODIC.color.into()));
    m.insert("shape".into(), Value::String(EXTRA_EPISODIC.shape.into()));
    doc_types.push(Value::Object(m));

    let edge_entries: Vec<Value> = EDGE_TYPES
        .iter()
        .map(|e| json!({"type": e.name, "color": e.color, "style": e.style, "label": e.label}))
        .collect();

    let mut out = Map::new();
    out.insert("doc_types".into(), Value::Array(doc_types));
    out.insert("edge_types".into(), Value::Array(edge_entries));
    Value::Object(out)
}

fn shape_shape(s: &str) -> String {
    s.to_string()
}

// ── inferencia de DocType por ruta (Fase 13) ────────────────────────────────

/// infer_doc_type_from_path: normaliza backslashes y delega a las reglas
/// por subfolder. Devuelve el slug o None.
pub fn infer_doc_type_from_path(path: &str) -> Option<&'static str> {
    let normalized = path.replace('\\', "/");
    let parts: Vec<&str> = normalized.split('/').filter(|p| !p.is_empty()).collect();
    if parts.len() < 2 {
        return None;
    }
    // Primer segmento que sea subfolder conocido (excluyendo el filename).
    for part in &parts[..parts.len() - 1] {
        match *part {
            "sessions" => return Some("session"),
            "handoffs" => return Some("handoff"),
            "specs" => return Some("spec"),
            "decisions" => {
                let stem = parts[parts.len() - 1];
                let stem = stem.strip_suffix(".md").unwrap_or(stem);
                if is_adr_filename(stem) {
                    return Some("adr");
                }
                return Some("decision");
            }
            "incidents" => return Some("incident"),
            "postmortems" => return Some("postmortem"),
            "runbooks" => return Some("runbook"),
            "architecture" => return Some("architecture"),
            "changelog" => return Some("changelog"),
            "hu" => return Some("hu"),
            "glossary" => return Some("glossary"),
            "designs" => return Some("design"),
            _ => {}
        }
    }
    None
}

/// ^ADR-\d+ case-insensitive sobre el stem.
pub fn is_adr_filename(stem: &str) -> bool {
    let bytes = stem.as_bytes();
    if bytes.len() < 5 {
        return false;
    }
    let head = &stem[..3];
    if !head.eq_ignore_ascii_case("adr") {
        return false;
    }
    if stem.as_bytes()[3] != b'-' {
        return false;
    }
    stem[4..]
        .chars()
        .next()
        .map(|c| c.is_ascii_digit())
        .unwrap_or(false)
}
