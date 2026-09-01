//! Puerto de los helpers de frontmatter de `cortex.enterprise.knowledge_promotion`
//! (`_FRONTMATTER_RE`, `_split_frontmatter`, `_upsert_frontmatter`,
//! `_normalized_markdown_fingerprint`, `_doc_type_from_rel_path`).
//!
//! El splitter replica manualmente el regex `^---\s*\n(.*?)\n---\s*\n`
//! (DOTALL, lazy) sin dependencia nueva: mismo backtracking de `\s*` greedy
//! ante el `\n` literal (consume todo el whitespace y retrocede un paso si
//! el último carácter consumido es el `\n` que exige el patrón).

use cortex_setup::yaml::Yaml;
use sha2::{Digest, Sha256};

/// Espejo de `(dict, body, had)` de `_split_frontmatter`.
/// FM tolerante: YAML inválido o no-mapping ⇒ objeto vacío.
pub struct SplitFrontmatter {
    pub fm: serde_yaml::Value,
    pub body: String,
    pub had: bool,
}

/// Encuentra el fin del delimitador `^---\s*\n` desde `start` (que apunta
/// justo después de los tres `-`). Devuelve el índice tras el `\n` literal.
fn skip_open_delimiter(raw: &[u8], mut i: usize) -> Option<usize> {
    let start_ws = i;
    while i < raw.len() && (raw[i] as char).is_ascii_whitespace() {
        i += 1;
    }
    if i < raw.len() && raw[i] == b'\n' {
        return Some(i + 1);
    }
    // Backtrack: el último whitespace consumido era el '\n' literal.
    if i > start_ws && i <= raw.len() && raw[i - 1] == b'\n' {
        return Some(i);
    }
    None
}

/// Ancla `\n---\s*\n` desde posición `k` (donde raw[k] == '\n').
fn matches_close_delimiter(raw: &[u8], k: usize) -> Option<usize> {
    if raw.get(k) != Some(&b'\n') || raw.get(k + 1..=k + 3) != Some(b"---") {
        return None;
    }
    let mut i = k + 4;
    let start_ws = i;
    while i < raw.len() && (raw[i] as char).is_ascii_whitespace() {
        i += 1;
    }
    if i < raw.len() && raw[i] == b'\n' {
        return Some(i + 1);
    }
    if i > start_ws && raw[i - 1] == b'\n' {
        return Some(i);
    }
    None
}

/// `_split_frontmatter`: None si no hay delimitador de apertura.
pub fn split_frontmatter(raw: &str) -> Option<SplitFrontmatter> {
    let bytes = raw.as_bytes();
    if !bytes.starts_with(b"---") {
        return None;
    }
    let yaml_start = skip_open_delimiter(bytes, 3)?;

    // Lazy .*?: primera aparición del ancla de cierre.
    let mut yaml_end = bytes.len();
    let mut body_start = bytes.len();
    for k in yaml_start..bytes.len() {
        if let Some(end) = matches_close_delimiter(bytes, k) {
            yaml_end = k;
            body_start = end;
            break;
        }
    }

    let yaml_text = &raw[yaml_start..yaml_end];
    let parsed: Result<serde_yaml::Value, _> = serde_yaml::from_str(yaml_text);
    let fm = match parsed {
        Ok(v @ serde_yaml::Value::Mapping(_)) => v,
        _ => serde_yaml::Value::Mapping(Default::default()),
    };
    Some(SplitFrontmatter {
        fm,
        body: raw[body_start..].to_string(),
        had: true,
    })
}

/// Convierte serde_yaml::Value → Yaml del emisor PyYAML preservando el orden
/// del mapping (crítico: un desvío por serde_json::Map reordenaría claves).
pub fn yaml_value_to_node(value: &serde_yaml::Value) -> Yaml {
    match value {
        serde_yaml::Value::Null => Yaml::Null,
        serde_yaml::Value::Bool(b) => Yaml::Bool(*b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Int(i)
            } else if let Some(u) = n.as_u64() {
                Yaml::Int(i64::try_from(u).unwrap_or(i64::MAX))
            } else {
                Yaml::Float(n.as_f64().unwrap_or(0.0))
            }
        }
        serde_yaml::Value::String(s) => Yaml::Str(s.clone()),
        serde_yaml::Value::Sequence(items) => {
            Yaml::Seq(items.iter().map(yaml_value_to_node).collect())
        }
        serde_yaml::Value::Mapping(map) => Yaml::Map(
            map.iter()
                .map(|(k, v)| {
                    let key = match k {
                        serde_yaml::Value::String(s) => s.clone(),
                        other => serde_yaml::to_string(other)
                            .unwrap_or_default()
                            .trim()
                            .to_string(),
                    };
                    (key, yaml_value_to_node(v))
                })
                .collect(),
        ),
        serde_yaml::Value::Tagged(t) => yaml_value_to_node(&t.value),
    }
}

/// `_upsert_frontmatter`: mergea updates (salteando valores None), re-emite
/// con safe_dump(sort_keys=False, allow_unicode=True) y normaliza el cuerpo.
pub fn upsert_frontmatter(raw: &str, updates: Vec<(String, Option<serde_yaml::Value>)>) -> String {
    let mut node = split_frontmatter(raw).unwrap_or(SplitFrontmatter {
        fm: serde_yaml::Value::Mapping(Default::default()),
        body: raw.to_string(),
        had: false,
    });
    let mapping = match &mut node.fm {
        serde_yaml::Value::Mapping(map) => map,
        other => {
            *other = serde_yaml::Value::Mapping(Default::default());
            match other {
                serde_yaml::Value::Mapping(map) => map,
                _ => unreachable!(),
            }
        }
    };
    for (key, value) in updates {
        let Some(value) = value else { continue };
        mapping.insert(serde_yaml::Value::String(key), value);
    }
    let emitted = cortex_setup::yaml::dump_with(&yaml_value_to_node(&node.fm), true)
        .trim_end()
        .to_string();
    let block = format!("---\n{emitted}\n---\n\n");
    if node.had {
        format!("{block}{}", node.body.trim_start_matches('\n'))
    } else {
        format!("{block}{}", raw.trim_start_matches('\n'))
    }
}

/// `_normalized_markdown_fingerprint`: CRLF→LF, split, body.strip()+"\n",
/// SHA-256 hex.
pub fn normalized_markdown_fingerprint(raw: &str) -> String {
    let lf = raw.replace("\r\n", "\n");
    let body = split_frontmatter(&lf).map(|s| s.body).unwrap_or(lf.clone());
    let normalized = format!("{}\n", body.trim());
    let digest = Sha256::digest(normalized.as_bytes());
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

/// `_doc_type_from_rel_path`: familia por primer segmento; None si desconocida.
pub fn doc_type_from_rel_path(rel_path: &str) -> Option<&'static str> {
    let first = rel_path
        .split('/')
        .next()
        .unwrap_or("")
        .trim()
        .to_lowercase();
    match first.as_str() {
        "specs" => Some("spec"),
        "decisions" => Some("decision"),
        "runbooks" => Some("runbook"),
        "hu" => Some("hu"),
        "incidents" => Some("incident"),
        "sessions" => Some("session"),
        _ => None,
    }
}
