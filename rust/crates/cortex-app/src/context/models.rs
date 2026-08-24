//! Puerto de los modelos del ContextEnricher (`cortex/models.py` §Context
//! Enricher + `context_enricher/presenter.py::to_json`).
//!
//! El bundle `--json` es el CONTRATO de paridad P7: mismas claves, mismo
//! orden, mismos valores (floats normalizados a 1e-6 por ruido FFI de
//! chroma-f32 — ver context_golden_p7.py).

/// Espejo de WorkContext (sólo los campos que el enricher y el presenter
/// consumen; el resto son passthrough no usados en P7).
#[derive(Debug, Clone, Default)]
pub struct WorkContext {
    /// "git_diff" | "pr" | "manual"
    pub source: String,
    pub changed_files: Vec<String>,
    pub keywords: Vec<String>,
    pub imports: Vec<String>,
    pub function_names: Vec<String>,
    pub class_names: Vec<String>,
    pub detected_domain: Option<String>,
    pub domain_confidence: f64,
    pub search_queries: Vec<String>,
}

impl WorkContext {
    pub fn manual(
        search_queries: Vec<&str>,
        changed_files: Vec<&str>,
        keywords: Vec<&str>,
    ) -> Self {
        Self {
            source: "manual".into(),
            changed_files: changed_files.into_iter().map(String::from).collect(),
            keywords: keywords.into_iter().map(String::from).collect(),
            search_queries: search_queries.into_iter().map(String::from).collect(),
            ..Default::default()
        }
    }
}

/// Item enriquecido (espejo de EnrichedItem).
#[derive(Debug, Clone)]
pub struct EnrichedItem {
    /// "episodic" | "semantic"
    pub source: &'static str,
    pub source_id: String,
    pub title: String,
    pub content: String,
    pub score: f64,
    pub enriched_score: f64,
    pub matched_by: Vec<String>,
    pub files_mentioned: Vec<String>,
    /// ISO-8601 canónico tal cual (None para semantic).
    pub date: Option<String>,
    pub tags: Vec<String>,
    pub doc_type: Option<String>,
    pub status: Option<String>,
    pub vault_scope: String,
    pub origin_project_id: Option<String>,
    pub matched_chunk_id: Option<String>,
    pub matched_section_title: Option<String>,
}

/// Bundle final (espejo de EnrichedContext sin telemetría).
pub struct EnrichedBundle {
    pub work: WorkContext,
    pub items: Vec<EnrichedItem>,
    pub total_searches: usize,
    pub total_raw_hits: usize,
    pub total_chars: usize,
}

impl EnrichedBundle {
    pub fn within_budget(&self, max_chars: usize) -> bool {
        self.total_chars <= max_chars
    }

    /// Espejo byte-parity de `ContextPresenter.to_json(ctx)`.
    pub fn to_json(&self, max_chars: usize) -> String {
        use super::pyjson::Pj;
        let v = Pj::Obj(vec![
            ("has_context".into(), Pj::Bool(!self.items.is_empty())),
            ("total_searches".into(), Pj::U64(self.total_searches as u64)),
            ("total_raw_hits".into(), Pj::U64(self.total_raw_hits as u64)),
            ("total_items".into(), Pj::U64(self.items.len() as u64)),
            ("total_chars".into(), Pj::U64(self.total_chars as u64)),
            (
                "within_budget".into(),
                Pj::Bool(self.within_budget(max_chars)),
            ),
            (
                "work".into(),
                Pj::Obj(vec![
                    ("source".into(), Pj::Str(self.work.source.clone())),
                    (
                        "changed_files".into(),
                        Pj::Arr(
                            self.work
                                .changed_files
                                .iter()
                                .map(|f| Pj::Str(f.clone()))
                                .collect(),
                        ),
                    ),
                    (
                        "detected_domain".into(),
                        match &self.work.detected_domain {
                            Some(d) => Pj::Str(d.clone()),
                            None => Pj::Null,
                        },
                    ),
                    (
                        "domain_confidence".into(),
                        Pj::F64(self.work.domain_confidence),
                    ),
                    (
                        "search_queries".into(),
                        Pj::Arr(
                            self.work
                                .search_queries
                                .iter()
                                .map(|q| Pj::Str(q.clone()))
                                .collect(),
                        ),
                    ),
                ]),
            ),
            (
                "items".into(),
                Pj::Arr(self.items.iter().map(item_to_pj).collect()),
            ),
        ]);
        super::pyjson::dumps(&v)
    }
}

fn opt_str_pj(v: &Option<String>) -> crate::context::pyjson::Pj {
    match v {
        Some(s) => crate::context::pyjson::Pj::Str(s.clone()),
        None => crate::context::pyjson::Pj::Null,
    }
}

fn item_to_pj(it: &EnrichedItem) -> crate::context::pyjson::Pj {
    use crate::context::pyjson::Pj;
    Pj::Obj(vec![
        ("source".into(), Pj::Str(it.source.into())),
        ("source_id".into(), Pj::Str(it.source_id.clone())),
        ("title".into(), Pj::Str(it.title.clone())),
        ("content".into(), Pj::Str(it.content.clone())),
        ("score".into(), Pj::F64(it.score)),
        ("enriched_score".into(), Pj::F64(it.enriched_score)),
        (
            "matched_by".into(),
            Pj::Arr(it.matched_by.iter().map(|m| Pj::Str(m.clone())).collect()),
        ),
        (
            "files_mentioned".into(),
            Pj::Arr(
                it.files_mentioned
                    .iter()
                    .map(|f| Pj::Str(f.clone()))
                    .collect(),
            ),
        ),
        (
            "date".into(),
            match &it.date {
                Some(d) => Pj::Str(d.clone()),
                None => Pj::Null,
            },
        ),
        (
            "tags".into(),
            Pj::Arr(it.tags.iter().map(|t| Pj::Str(t.clone())).collect()),
        ),
        ("doc_type".into(), opt_str_pj(&it.doc_type)),
        ("status".into(), opt_str_pj(&it.status)),
        ("vault_scope".into(), Pj::Str(it.vault_scope.clone())),
        (
            "origin_project_id".into(),
            opt_str_pj(&it.origin_project_id),
        ),
        ("matched_chunk_id".into(), opt_str_pj(&it.matched_chunk_id)),
        (
            "matched_section_title".into(),
            opt_str_pj(&it.matched_section_title),
        ),
    ])
}
