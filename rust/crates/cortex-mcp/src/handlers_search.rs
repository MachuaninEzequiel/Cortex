//! Handlers MCP in-process de la familia search/context/sync_ticket —
//! porte de `cortex/mcp/tools/search.py` (Cierre Obra 07 T1).
//!
//! Los handlers consumen un [`SearchBackend`] inyectable: en producción es
//! una implementación nativa sobre `cortex-app` (`SemanticIndex` +
//! `NativeEpisodicStore` + `ContextEnricher`); en los gates, stubs
//! deterministas que reproducen los contratos ya gateados de P2/P3/P7.
//!
//! Wire-format exacto: las presentaciones `RetrievalResult.to_prompt()` y
//! `EnrichedContext.to_prompt_format()` se replican byte-a-byte sobre espejos
//! planos (truncamientos por CARACTERES como Python 3, scores `{:.4f}` /
//! `{:.2f}`, fechas `%Y-%m-%d`).
//!
//! Divergencias documentadas: ninguna a nivel de texto emitido; la selección
//! de resultados es responsabilidad del backend (gateado en sus fases).

use serde_json::Value;

// ---------------------------------------------------------------------------
// Espejos planos (lo mínimo que consumen las presentaciones)
// ---------------------------------------------------------------------------

/// Espejo de `MemoryEntry` reducido a lo que usa `to_prompt`.
#[derive(Debug, Clone, Default)]
pub struct REntry {
    pub id: String,
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub files: Vec<String>,
    /// verified | asserted | contradicted | None
    pub confidence: Option<String>,
}

/// Espejo de `SemanticDocument` reducido a lo que usa `to_prompt`.
#[derive(Debug, Clone, Default)]
pub struct RDoc {
    pub path: String,
    pub title: String,
    pub content: String,
}

/// Espejo de `UnifiedHit` (RRF): episódico o semántico con score fusionado.
#[derive(Debug, Clone, Default)]
pub struct RHit {
    /// "episodic" | "semantic"
    pub source: String,
    pub score: f64,
    pub entry: Option<REntry>,
    pub doc: Option<RDoc>,
}

/// Espejo de `RetrievalResult` (AgentMemory.retrieve).
#[derive(Debug, Clone, Default)]
pub struct RetrievalMirror {
    pub query: String,
    pub episodic_hits: Vec<(REntry, f64)>,
    pub semantic_hits: Vec<(RDoc, f64)>,
    pub unified_hits: Vec<RHit>,
}

/// Espejo de `EnrichedItem` reducido a lo que usa `to_prompt_format`.
#[derive(Debug, Clone, Default)]
pub struct EnrichedItemMirror {
    /// "episodic" | "semantic"
    pub source: String,
    pub title: String,
    pub content: String,
    pub files_mentioned: Vec<String>,
    /// ISO local; el formato `%Y-%m-%d` son los primeros 10 caracteres.
    pub date_iso: Option<String>,
    pub matched_by: Vec<String>,
    pub tags: Vec<String>,
    pub confidence: Option<String>,
}

/// Espejo de `EnrichedContext` para `to_prompt_format`.
#[derive(Debug, Clone, Default)]
pub struct EnrichedMirror {
    pub items: Vec<EnrichedItemMirror>,
    pub total_items: usize,
}

// ---------------------------------------------------------------------------
// Backend inyectable
// ---------------------------------------------------------------------------

pub trait SearchBackend {
    /// Espejo de `AgentMemory.retrieve(query, top_k=…, use_embeddings=…)`.
    fn retrieve(
        &mut self,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> Result<RetrievalMirror, String>;

    /// Espejo de `AgentMemory.enrich(changed_files, keywords, pr_title, top_k)`.
    fn enrich(
        &mut self,
        changed_files: Vec<String>,
        keywords: Vec<String>,
        pr_title: Option<String>,
        top_k: Option<usize>,
    ) -> Result<EnrichedMirror, String>;

    /// Ruta estructural de `_search_text_dispatch`: construye filtros CLI y
    /// corre el ContextEnricher. `Err(StructuralError::Filter)` equivale al
    /// ValueError de Python (el handler lo formatea como texto
    /// "cortex_search: invalid filter — …"); `Runtime` sube al dispatcher.
    #[allow(clippy::too_many_arguments)]
    fn enrich_structural(
        &mut self,
        query: &str,
        top_k: usize,
        scope: &str,
        doc_type: Vec<String>,
        exclude_doc_type: Vec<String>,
        status: Vec<String>,
        tag: Vec<String>,
        tag_any: Vec<String>,
        max_age_days: Option<i64>,
        project_id: Vec<String>,
        strict: bool,
    ) -> Result<EnrichedMirror, StructuralError>;
}

/// Errores de la ruta estructural (espejo del try/except ValueError).
#[derive(Debug, Clone)]
pub enum StructuralError {
    /// ValueError del builder de filtros → texto de tool.
    Filter(String),
    /// Otras excepciones → dispatcher.
    Runtime(String),
}

// ---------------------------------------------------------------------------
// Presentaciones byte-parity (cortex/models.py)
// ---------------------------------------------------------------------------

/// Slicing por caracteres estilo Python `s[:n]`.
fn char_take(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// `f"{x:.4f}"` / `f"{x:.2f}"`: Rust {:.prec} redondea igual que CPython
/// (conversión decimal correctamente redondeada del double).
impl RetrievalMirror {
    /// `RetrievalResult.to_prompt(max_chars=4000)`.
    pub fn to_prompt(&self, max_chars: usize) -> String {
        let mut parts: Vec<String> = vec![format!("## Context for: '{}'\n", self.query)];

        if !self.unified_hits.is_empty() {
            for u in &self.unified_hits {
                if u.source == "episodic" {
                    if let Some(e) = &u.entry {
                        let conf_label = match &e.confidence {
                            Some(c) => format!(" [{c}]"),
                            None => String::new(),
                        };
                        parts.push(format!(
                            "- [EPISODIC:{}{}] {}  (files: {}, score: {:.4})",
                            e.memory_type,
                            conf_label,
                            e.content,
                            if e.files.is_empty() {
                                "none".to_string()
                            } else {
                                e.files.join(", ")
                            },
                            u.score
                        ));
                    }
                } else if u.source == "semantic" {
                    if let Some(d) = &u.doc {
                        parts.push(format!("- [SEMANTIC] **{}** ({})", d.title, d.path));
                        let excerpt = char_take(&d.content, 300).replace('\n', " ");
                        parts.push(format!("  > {excerpt}…"));
                    }
                }
            }
        } else {
            if !self.episodic_hits.is_empty() {
                parts.push("### Episodic Memory (past experiences)".to_string());
                for (e, score) in &self.episodic_hits {
                    let conf_label = match &e.confidence {
                        Some(c) => format!(" [{c}]"),
                        None => String::new(),
                    };
                    parts.push(format!(
                        "- [{}{}] {}  (files: {}, score: {:.2})",
                        e.memory_type,
                        conf_label,
                        e.content,
                        if e.files.is_empty() {
                            "none".to_string()
                        } else {
                            e.files.join(", ")
                        },
                        score
                    ));
                }
            }
            if !self.semantic_hits.is_empty() {
                parts.push("\n### Semantic Knowledge (docs / notes)".to_string());
                for (doc, _s) in &self.semantic_hits {
                    parts.push(format!("- **{}** ({})", doc.title, doc.path));
                    let excerpt = char_take(&doc.content, 300).replace('\n', " ");
                    parts.push(format!("  > {excerpt}…"));
                }
            }
        }

        let result = parts.join("\n");
        char_take(&result, max_chars)
    }
}

impl EnrichedMirror {
    /// `EnrichedContext.to_prompt_format()` (modo full; MCP nunca pasa
    /// compact/expand).
    pub fn to_prompt_format(&self) -> String {
        if self.items.is_empty() {
            return "🧠 Cortex Context — No related memories found.".to_string();
        }

        let mut parts: Vec<String> = vec![format!(
            "🧠 Cortex Context — Found {} related memories\n",
            self.total_items
        )];
        for item in &self.items {
            let source_tag = if item.source == "episodic" {
                "EPISODIC"
            } else {
                "SEMANTIC"
            };
            let conf_tag = match &item.confidence {
                Some(c) => format!(" [{c}]"),
                None => String::new(),
            };
            parts.push(format!("### [{source_tag}{conf_tag}] {}", item.title));

            let mut meta_parts: Vec<String> = Vec::new();
            if let Some(iso) = &item.date_iso {
                // strftime("%Y-%m-%d") sobre el valor almacenado.
                meta_parts.push(char_take(iso, 10));
            }
            if !item.files_mentioned.is_empty() {
                meta_parts.push(item.files_mentioned.join(", "));
            }
            if !item.tags.is_empty() {
                meta_parts.push(item.tags.join(", "));
            }
            if !meta_parts.is_empty() {
                parts.push(format!("  {}", meta_parts.join(" • ")));
            }
            parts.push(format!("  {}…", char_take(&item.content, 150)));
            if !item.matched_by.is_empty() {
                parts.push(format!("  Matched by: {}", item.matched_by.join(", ")));
            }
            parts.push(String::new());
        }
        parts.push("Run `cortex context --expand` for full details".to_string());
        parts.join("\n")
    }
}

// ---------------------------------------------------------------------------
// Helpers del mixín (porte fiel)
// ---------------------------------------------------------------------------

/// `_extract_query_keywords`: keywords livianas desde una query libre.
pub fn extract_query_keywords(query: &str) -> Vec<String> {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    let re = RE.get_or_init(|| regex::Regex::new(r"\b[a-zA-Z][\w./-]{2,}\b").expect("kw re"));
    let lower = query.to_lowercase();
    let mut out: Vec<String> = Vec::new();
    for m in re.find_iter(&lower) {
        let w = m.as_str().to_string();
        if !out.contains(&w) {
            out.push(w);
        }
    }
    out.into_iter().take(10).collect()
}

/// `_normalize_string_list`: tolera None / str CSV / lista de strings.
pub fn normalize_string_list(values: Option<&Value>) -> Vec<String> {
    match values {
        None | Some(Value::Null) => Vec::new(),
        Some(Value::String(s)) => s
            .split(',')
            .map(str::trim)
            .filter(|t| !t.is_empty())
            .map(str::to_string)
            .collect(),
        Some(Value::Array(arr)) => arr
            .iter()
            .map(|v| match v {
                Value::String(s) => s.clone(),
                other => other.to_string(),
            })
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty())
            .collect(),
        _ => Vec::new(),
    }
}

/// `_extract_candidate_files`: rutas con extensión mencionadas en la query,
/// resueltas contra project_root con `resolve_safe` (P12A-1).
pub fn extract_candidate_files(query: &str, project_root: &std::path::Path) -> Vec<String> {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    let re = RE.get_or_init(|| {
        regex::Regex::new(r"\b[\w./\\-]+\.[A-Za-z0-9]+\b").expect("candidate files re")
    });
    use cortex_app::security::{resolve_safe, PathSecurityError};
    let root = match project_root.canonicalize() {
        Ok(p) => p,
        Err(_) => project_root.to_path_buf(),
    };
    let mut candidates: Vec<String> = Vec::new();
    for m in re.find_iter(query) {
        let normalized = m.as_str().trim().replace('\\', "/");
        match resolve_safe(&root, std::path::Path::new(&normalized)) {
            Err(PathSecurityError(_)) => continue,
            Ok(candidate) => {
                if candidate.is_file() && !candidates.contains(&normalized) {
                    candidates.push(normalized);
                }
            }
        }
    }
    candidates
}

/// Truthiness de Python para `any(arguments.get(k))`.
fn python_truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_f64().map(|f| f != 0.0).unwrap_or(false),
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

/// `int(arguments.get(key, default) or default)` de Python: acepta números
/// JSON y strings numéricos; falsy (0/null/"") cae al default.
fn int_arg_or(args: &Value, key: &str, default: usize) -> usize {
    let raw = args.get(key);
    let falsy = match raw {
        None | Some(Value::Null) => true,
        Some(Value::Bool(b)) => !*b,
        Some(Value::Number(n)) => n.as_f64().map(|f| f == 0.0).unwrap_or(true),
        Some(Value::String(s)) => s.is_empty(),
        _ => false,
    };
    if falsy {
        return default;
    }
    match raw {
        Some(Value::Number(n)) => n.as_f64().map(|f| f as i64).unwrap_or(default as i64) as usize,
        Some(Value::String(s)) => s.trim().parse::<usize>().unwrap_or(default),
        _ => default,
    }
}

// ---------------------------------------------------------------------------
// Handlers (formatos espejo exactos de search.py)
// ---------------------------------------------------------------------------

const STRUCTURAL_KEYS: &[&str] = &[
    "doc_type",
    "exclude_doc_type",
    "status",
    "tag",
    "tag_any",
    "max_age_days",
    "project_id",
    "strict",
];

fn strings_list(args: &Value, key: &str) -> Vec<String> {
    args.get(key)
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

/// `_search_text(query, limit)` → `retrieve(...).to_prompt()`.
fn search_text(b: &mut dyn SearchBackend, query: &str, limit: usize) -> Result<String, String> {
    let results = b.retrieve(query, limit, false)?;
    Ok(results.to_prompt(4000))
}

/// Handler `cortex_search_vector`: fuerza el camino vectorial
/// (`use_embeddings=True`, nunca cae al modo estructural).
pub fn search_vector_text(b: &mut dyn SearchBackend, args: &Value) -> Result<String, String> {
    let raw_query = args.get("query").and_then(Value::as_str).unwrap_or("");
    let query = if raw_query == "null" { "" } else { raw_query };
    let limit = int_arg_or(args, "limit", 5);
    let results = b.retrieve(query, limit, true)?;
    Ok(results.to_prompt(4000))
}

/// Handler `cortex_search`: ruta legacy RRF o estructural según filtros.
pub fn search_text_dispatch(b: &mut dyn SearchBackend, args: &Value) -> Result<String, String> {
    let query = args.get("query").and_then(Value::as_str).unwrap_or("");
    let limit = int_arg_or(args, "limit", 5);

    let scope_raw = args.get("scope").and_then(Value::as_str).unwrap_or("local");
    let scope = if scope_raw.is_empty() {
        "local"
    } else {
        scope_raw
    };

    let structural = STRUCTURAL_KEYS.iter().any(|k| python_truthy(args.get(k))) || scope != "local";
    if !structural {
        return search_text(b, query, limit);
    }

    let mirror = match b.enrich_structural(
        query,
        limit,
        scope,
        strings_list(args, "doc_type"),
        strings_list(args, "exclude_doc_type"),
        strings_list(args, "status"),
        strings_list(args, "tag"),
        strings_list(args, "tag_any"),
        args.get("max_age_days").and_then(Value::as_i64),
        strings_list(args, "project_id"),
        python_truthy(args.get("strict")),
    ) {
        Ok(m) => m,
        Err(StructuralError::Filter(exc)) => {
            return Ok(format!("cortex_search: invalid filter — {exc}"));
        }
        Err(StructuralError::Runtime(m)) => return Err(m),
    };
    Ok(mirror.to_prompt_format())
}

/// Handler `cortex_context` → `_enrich_context(...).to_prompt_format()`.
pub fn context_text(b: &mut dyn SearchBackend, args: &Value) -> Result<String, String> {
    let mirror = enrich_context(b, args)?;
    Ok(mirror.to_prompt_format())
}

/// `_enrich_context`: convierte argumentos MCP en un request de enriquecido
/// (task_type dimensiona top_k vía budget resolver P12B-5).
pub fn enrich_context(
    b: &mut dyn SearchBackend,
    arguments: &Value,
) -> Result<EnrichedMirror, String> {
    let query = arguments
        .get("query")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string();
    let changed_files = normalize_string_list(arguments.get("changed_files"));
    let mut keywords = normalize_string_list(arguments.get("keywords"));

    if keywords.is_empty() && !query.is_empty() {
        keywords = extract_query_keywords(&query);
    }

    let pr_title_raw = arguments
        .get("pr_title")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string();
    let pr_title = if !pr_title_raw.is_empty() {
        Some(pr_title_raw)
    } else if !query.is_empty() {
        Some(query)
    } else {
        None
    };

    let strip_opt = |key: &str| -> Option<String> {
        match arguments.get(key) {
            None | Some(Value::Null) => None,
            Some(Value::String(s)) if s.is_empty() => None,
            Some(Value::String(s)) => Some(s.trim().to_string()),
            Some(other) => Some(value_to_trimmed_string(other)),
        }
    };
    let task_type = strip_opt("task_type");
    let complexity = strip_opt("complexity");

    let top_k: Option<usize> = task_type.as_deref().map(|tt| {
        use cortex_app::context::budget_resolver::resolve_budget_profile;
        resolve_budget_profile(Some(tt), complexity.as_deref()).top_k
    });

    b.enrich(changed_files, keywords, pr_title, top_k)
}

/// `str(v)` de Python para valores no-string (números/bools).
fn value_to_trimmed_string(v: &Value) -> String {
    match v {
        Value::Bool(true) => "True".to_string(),
        Value::Bool(false) => "False".to_string(),
        other => other.to_string(),
    }
}

/// Handler `cortex_sync_ticket`: contexto de ticket con retrieval +
/// enriquecido. ValueError de Python ⇒ Err (el dispatcher formatea
/// "Error ejecutando …").
pub fn build_sync_ticket_context(
    b: &mut dyn SearchBackend,
    arguments: &Value,
    project_root: &std::path::Path,
) -> Result<String, String> {
    let user_request = arguments
        .get("user_request")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string();
    if user_request.is_empty() {
        return Err("user_request es obligatorio para cortex_sync_ticket.".into());
    }

    let mut changed_files = normalize_string_list(arguments.get("changed_files"));
    if changed_files.is_empty() {
        changed_files = extract_candidate_files(&user_request, project_root);
    }

    let mut keywords = normalize_string_list(arguments.get("keywords"));
    if keywords.is_empty() {
        keywords = extract_query_keywords(&user_request);
    }

    let title_hint_raw = arguments
        .get("title_hint")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string();
    let title_hint = if title_hint_raw.is_empty() {
        user_request.clone()
    } else {
        title_hint_raw
    };
    let top_k = int_arg_or(arguments, "top_k", 5);

    let related = b.retrieve(&user_request, top_k, false)?;
    let enriched = b.enrich(
        changed_files.clone(),
        keywords.clone(),
        Some(title_hint),
        Some(top_k),
    )?;

    let changed_files_text = if changed_files.is_empty() {
        "(sin archivos inferidos)".to_string()
    } else {
        changed_files.join(", ")
    };
    let keywords_text = if keywords.is_empty() {
        "(sin keywords)".to_string()
    } else {
        keywords.join(", ")
    };

    let sections = [
        "## Ticket actual".to_string(),
        user_request,
        String::new(),
        "## Scope detectado".to_string(),
        changed_files_text,
        String::new(),
        "## Keywords".to_string(),
        keywords_text,
        String::new(),
        "## Contexto historico similar (Vault + memoria episodica)".to_string(),
        related.to_prompt(4000),
        String::new(),
        "## Contexto enriquecido del proyecto".to_string(),
        enriched.to_prompt_format(),
    ];
    Ok(sections.join("\n"))
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Stub;
    impl SearchBackend for Stub {
        fn retrieve(&mut self, q: &str, _k: usize, _emb: bool) -> Result<RetrievalMirror, String> {
            Ok(RetrievalMirror {
                query: q.to_string(),
                unified_hits: vec![RHit {
                    source: "semantic".into(),
                    score: 0.032_786_885_245_901_64,
                    entry: None,
                    doc: Some(RDoc {
                        path: "specs/auth.md".into(),
                        title: "Auth".into(),
                        content: "line1\nline2".into(),
                    }),
                }],
                ..Default::default()
            })
        }
        fn enrich(
            &mut self,
            _: Vec<String>,
            _: Vec<String>,
            _: Option<String>,
            _: Option<usize>,
        ) -> Result<EnrichedMirror, String> {
            Ok(EnrichedMirror::default())
        }
        fn enrich_structural(
            &mut self,
            _: &str,
            _: usize,
            _: &str,
            _: Vec<String>,
            _: Vec<String>,
            _: Vec<String>,
            _: Vec<String>,
            _: Vec<String>,
            _: Option<i64>,
            _: Vec<String>,
            _: bool,
        ) -> Result<EnrichedMirror, StructuralError> {
            Err(StructuralError::Runtime("invalid filter".into()))
        }
    }

    #[test]
    fn to_prompt_semantico_bytes_python() {
        let m = Stub.retrieve("q", 5, false).unwrap();
        assert_eq!(
            m.to_prompt(4000),
            "## Context for: 'q'\n\n- [SEMANTIC] **Auth** (specs/auth.md)\n  > line1 line2…"
        );
    }

    #[test]
    fn to_prompt_format_vacio() {
        assert_eq!(
            EnrichedMirror::default().to_prompt_format(),
            "🧠 Cortex Context — No related memories found."
        );
    }

    #[test]
    fn keywords_dedup_cap10() {
        let kws = extract_query_keywords("Fix auth Auth AUTH flow flow x");
        assert_eq!(kws, vec!["fix", "auth", "flow"]);
    }

    #[test]
    fn csv_y_lista_normalizados() {
        let v = serde_json::json!("a, b ,,c");
        assert_eq!(normalize_string_list(Some(&v)), vec!["a", "b", "c"]);
        let v = serde_json::json!(["x ", "", "y"]);
        assert_eq!(normalize_string_list(Some(&v)), vec!["x", "y"]);
        assert_eq!(normalize_string_list(None), Vec::<String>::new());
    }

    #[test]
    fn sync_ticket_sin_request_es_valueerror() {
        let mut b = Stub;
        let err =
            build_sync_ticket_context(&mut b, &serde_json::json!({}), std::path::Path::new("."))
                .unwrap_err();
        assert_eq!(err, "user_request es obligatorio para cortex_sync_ticket.");
    }
}
