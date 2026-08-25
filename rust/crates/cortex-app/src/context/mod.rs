//! Puerto del ContextEnricher (`cortex/context_enricher/enricher.py`,
//! Obra 07 fase P7 — stream A).
//!
//! Pipeline multi-estrategia sobre las nativas episódica (P3) y semántica
//! (P2b): búsquedas por topic/files/keywords/pr_title vía RRF híbrido
//! adaptativo + búsqueda por entidades; dedup por source_id conservando el
//! mayor score; multi-match boost; expansión por co-ocurrencia naive y
//! tipada; decay temporal; feedback implícito; DocIntent boost; umbral y
//! presupuesto. Fuente única de finalize (sync = async en el oráculo).
//!
//! Alcance P7 (documentado): sin filtros estructurales ni observer de
//! telemetría; vault-fixture con tipos sin chunking ⇒ matched_chunk_id
//! siempre null (la ruta chunked ya está gateada en P2b).

pub mod budget_resolver;
pub mod cooccurrence;
pub mod decay;
pub mod doc_intent;
pub mod feedback;
pub mod hybrid;
pub mod intent;
pub mod models;
pub mod pyjson;

use std::collections::HashMap;

use chrono::{DateTime, Utc};
use cortex_embed::onnx::OnnxEmbedder;

use crate::context::cooccurrence::{
    build_co_occurrence, co_occurrence_score, TypedCooccurrenceGraph,
};
use crate::context::decay::{calculate_decay_factor, DecayConfig};
use crate::context::doc_intent::{detect_doc_intent, retrieval_boost, DocIntent};
use crate::context::feedback::procesar_feedback_implicito;
use crate::context::hybrid::{search_hybrid, UnifiedHit};
use crate::context::models::{EnrichedBundle, EnrichedItem, WorkContext};
use crate::episodic::NativeEpisodicStore;
use crate::semantic::{routing, SemanticIndex};

/// Configuración del enricher — espejo de ContextEnricherConfig defaults.
#[derive(Debug, Clone)]
pub struct ContextEnricherConfig {
    pub min_score: f64,
    pub domain_confidence: f64,
    pub max_items: usize,
    pub max_chars: usize,
    pub multi_match_boost: f64,
    pub co_occurrence_boost: f64,
    pub topic: bool,
    pub files: bool,
    pub keywords: bool,
    pub pr_title: bool,
    pub graph_expansion: bool,
    pub entity_search: bool,
    pub typed_graph: bool,
    pub memory_decay: bool,
    pub decay_half_life_hours: f64,
    pub decay_floor: f64,
    pub feedback_loop: bool,
    pub implicit_boost: f64,
}

impl Default for ContextEnricherConfig {
    fn default() -> Self {
        Self {
            min_score: 0.1,
            domain_confidence: 0.5,
            max_items: 8,
            max_chars: 2000,
            multi_match_boost: 1.5,
            co_occurrence_boost: 0.3,
            topic: true,
            files: true,
            keywords: true,
            pr_title: true,
            graph_expansion: true,
            entity_search: true,
            typed_graph: true,
            memory_decay: true,
            decay_half_life_hours: 168.0,
            decay_floor: 0.10,
            feedback_loop: true,
            implicit_boost: 0.15,
        }
    }
}

pub struct ContextEnricher<'a> {
    pub episodic: &'a NativeEpisodicStore,
    pub semantic: &'a SemanticIndex,
    pub config: ContextEnricherConfig,
}

impl<'a> ContextEnricher<'a> {
    /// Espejo de ContextEnricher.enrich(work, top_k=…, filters=None).
    ///
    /// ``now`` inyecta el reloj para decay/recencia (el oráculo usa now();
    /// los fixtures usan timestamps viejos/permanentes para ser
    /// deterministas para siempre, así que cualquier now sirve al gate).
    pub fn enrich(
        &self,
        work: &WorkContext,
        embedder: &mut OnnxEmbedder,
        top_k: Option<usize>,
        now: DateTime<Utc>,
    ) -> EnrichedBundle {
        let max_items = top_k.unwrap_or(self.config.max_items);
        let queries = &work.search_queries;
        let fetch_k = max_items * 2; // over-fetch para RRF

        // ── Phase 1: estrategias, EN ORDEN de inserción del dict Python ──
        let mut strategy_results: Vec<(&'static str, Vec<UnifiedHit>)> = Vec::new();

        if self.config.topic && !queries.is_empty() {
            let hits = self.search_hybrid_for(queries[0].clone(), fetch_k, embedder);
            strategy_results.push(("topic_search", hits));
        }
        if self.config.files && queries.len() >= 2 {
            let hits = self.search_hybrid_for(queries[1].clone(), fetch_k, embedder);
            strategy_results.push(("file_search", hits));
        }
        if self.config.keywords && queries.len() >= 3 {
            let hits = self.search_hybrid_for(queries[2].clone(), fetch_k, embedder);
            strategy_results.push(("keyword_search", hits));
        }
        if self.config.pr_title && queries.len() >= 4 {
            let hits = self.search_hybrid_for(queries[3].clone(), fetch_k, embedder);
            strategy_results.push(("pr_title_search", hits));
        }

        // Entity search (comprehensive): fuentes y cotas del oráculo.
        if self.config.entity_search
            && (!work.function_names.is_empty()
                || !work.class_names.is_empty()
                || !work.keywords.is_empty())
        {
            let sources: [(&str, &[String], usize); 4] = [
                ("function", slice_up_to(&work.function_names, 5), 3),
                ("class", slice_up_to(&work.class_names, 3), 2),
                ("function", slice_up_to(&work.imports, 5), 2),
                ("class", slice_up_to(&work.keywords, 3), 1),
            ];
            let mut entity_hits: Vec<crate::episodic::MemoryEntry> = Vec::new();
            let mut entity_scores: Vec<f64> = Vec::new();
            for (search_type, values, max_results) in sources {
                for value in values {
                    if value.is_empty() || value.chars().count() < 2 {
                        continue;
                    }
                    for (entry, score) in
                        self.episodic
                            .entity_search(search_type, value, max_results, now)
                    {
                        entity_hits.push(entry);
                        entity_scores.push(score);
                    }
                }
            }
            // Dedup por entry.id preservando el mayor score (> estricto).
            let mut seen: HashMap<String, usize> = HashMap::new();
            let mut dedup_idx: Vec<usize> = Vec::new();
            for (i, hit) in entity_hits.iter().enumerate() {
                match seen.get(&hit.id) {
                    Some(&j) => {
                        if entity_scores[i] > entity_scores[j] {
                            entity_scores[j] = entity_scores[i];
                            // El contenido reemplazado es la MISMA entrada.
                        }
                    }
                    None => {
                        seen.insert(hit.id.clone(), i);
                        dedup_idx.push(i);
                    }
                }
            }
            if !dedup_idx.is_empty() {
                let mut pairs: Vec<(crate::episodic::MemoryEntry, f64)> = dedup_idx
                    .into_iter()
                    .map(|i| (entity_hits[i].clone(), entity_scores[i]))
                    .collect();
                pairs.sort_by(|a, b| b.1.total_cmp(&a.1));
                let hits = pairs
                    .into_iter()
                    .map(|(entry, score)| UnifiedHit {
                        source: "episodic",
                        score,
                        doc_score_raw: 0.0,
                        dropped: true, // EpisodicHit ⇒ descartado en finalize
                        entry: Some(entry),
                        doc: None,
                        matched_chunk_id: None,
                        matched_section_title: None,
                    })
                    .collect();
                strategy_results.push(("entity_search", hits));
            }
        }

        self.finalize_items(strategy_results, work, max_items, now)
    }

    fn search_hybrid_for(
        &'a self,
        query: String,
        fetch_k: usize,
        embedder: &mut OnnxEmbedder,
    ) -> Vec<UnifiedHit<'a>> {
        let (hits, _intent) = search_hybrid(
            self.episodic,
            self.semantic,
            embedder,
            &query,
            fetch_k,
            true,
        );
        hits
    }

    // ── Phases 2–6 (fuente única de finalize, espejo de _finalize_items) ──

    #[allow(clippy::too_many_lines)]
    fn finalize_items(
        &self,
        strategy_results: Vec<(&'static str, Vec<UnifiedHit>)>,
        work: &WorkContext,
        max_items: usize,
        now: DateTime<Utc>,
    ) -> EnrichedBundle {
        let queries = &work.search_queries;
        let total_raw_hits: usize = strategy_results.iter().map(|(_, v)| v.len()).sum();

        // Phase 2: conversión + merge por source_id (mayor score gana).
        let mut all_items: Vec<EnrichedItem> = Vec::new(); // orden de inserción
        let mut item_strategies: HashMap<String, Vec<&'static str>> = HashMap::new();

        for (strategy_name, hits) in &strategy_results {
            for hit in hits {
                // Espejo de `_hit_to_enriched_item`: los EpisodicHit de la
                // estrategia entity_search no convierten (ni UnifiedHit ni
                // tupla) ⇒ se descartan silenciosamente.
                if hit.dropped {
                    continue;
                }
                let Some(item) = unified_to_enriched_item(hit, strategy_name) else {
                    continue;
                };
                item_strategies
                    .entry(item.source_id.clone())
                    .or_default()
                    .push(strategy_name);
                match all_items
                    .iter_mut()
                    .find(|it| it.source_id == item.source_id)
                {
                    Some(existing) => {
                        if item.score > existing.score {
                            *existing = item;
                        }
                    }
                    None => all_items.push(item),
                }
            }
        }

        // Phase 3: multi-match boost.
        // NOTA DE NORMALIZACIÓN: el oráculo hace list(set(...)) cuyo orden es
        // dependiente de hash; el contrato P7 ordena matched_by en AMBOS
        // lados (ver context_golden_p7.py).
        for item in &mut all_items {
            let mut unique = item_strategies[&item.source_id].clone();
            unique.sort_unstable();
            unique.dedup();
            item.matched_by = unique.iter().map(|s| s.to_string()).collect();
            let boost_factor = if unique.len() > 1 {
                self.config
                    .multi_match_boost
                    .powi((unique.len() - 1) as i32)
            } else {
                1.0
            };
            item.enriched_score = item.score * boost_factor;
        }

        // Phase 4: co-ocurrencia naive.
        if self.config.graph_expansion && !work.changed_files.is_empty() {
            let entries_files: Vec<Vec<String>> = self
                .episodic
                .rows
                .iter()
                .map(|r| r.entry.files.clone())
                .collect();
            let co = build_co_occurrence(&entries_files);
            for item in &mut all_items {
                let co_score = co_occurrence_score(&work.changed_files, &item.files_mentioned, &co);
                item.enriched_score += co_score * self.config.co_occurrence_boost;
            }
        }

        // Phase 4b: grafo tipado.
        if self.config.typed_graph && !work.changed_files.is_empty() {
            let entries_files: Vec<Vec<String>> = self
                .episodic
                .rows
                .iter()
                .map(|r| r.entry.files.clone())
                .collect();
            let graph = TypedCooccurrenceGraph::build_from_memories(&entries_files);
            for item in &mut all_items {
                if !item.files_mentioned.is_empty() {
                    let typed_score = graph
                        .calculate_relationship_score(&work.changed_files, &item.files_mentioned);
                    item.enriched_score += typed_score * self.config.co_occurrence_boost * 0.5;
                }
            }
        }

        // Phase 4c: decay temporal (solo episódicas con fecha).
        if self.config.memory_decay {
            let decay_config =
                DecayConfig::new(self.config.decay_half_life_hours, self.config.decay_floor);
            for item in &mut all_items {
                if item.source == "episodic" {
                    if let Some(date) = &item.date {
                        let factor =
                            calculate_decay_factor("general", &item.tags, date, &decay_config, now);
                        item.enriched_score *= factor;
                    }
                }
            }
        }

        // Phase 4d: feedback implícito.
        if self.config.feedback_loop && !work.changed_files.is_empty() {
            let keywords10: Vec<String> = work.keywords.iter().take(10).cloned().collect();
            let mut entities = work.function_names.clone();
            entities.extend(work.class_names.iter().cloned());
            let items_as_dicts: Vec<(String, String, String, Vec<String>)> = all_items
                .iter()
                .map(|it| {
                    (
                        it.source_id.clone(),
                        it.content.clone(),
                        it.title.clone(),
                        it.files_mentioned.clone(),
                    )
                })
                .collect();
            let mut scores: Vec<f64> = all_items.iter().map(|it| it.enriched_score).collect();
            procesar_feedback_implicito(
                &keywords10,
                &work.changed_files,
                &entities,
                &items_as_dicts,
                self.config.implicit_boost,
                &mut scores,
            );
            for (item, s) in all_items.iter_mut().zip(scores) {
                item.enriched_score = s;
            }
        }

        // Phase 4.6: DocIntent boost (Fase 08 del oráculo; corre siempre que
        // haya queries). Filtros estructurales (4.5) fuera de alcance P7.
        if !queries.is_empty() {
            let detected = detect_doc_intent(&queries[0]);
            if detected.intent != DocIntent::Generic {
                for item in &mut all_items {
                    let Some(slug) = &item.doc_type else { continue };
                    let Ok(dt) = parse_doc_slug(slug) else {
                        continue;
                    };
                    let mut boost = retrieval_boost(dt, detected.intent);
                    if boost == 0.0 {
                        boost = 1.0; // clave ausente en el dict del oráculo
                    }
                    if boost != 1.0 {
                        item.enriched_score *= boost;
                    }
                }
            }
        }

        // Phase 5: umbral + sort estable descendente.
        let mut filtered: Vec<EnrichedItem> = all_items
            .into_iter()
            .filter(|it| it.enriched_score >= self.config.min_score)
            .collect();
        filtered.sort_by(|a, b| b.enriched_score.total_cmp(&a.enriched_score));

        // Phase 6: presupuesto (max items + max chars).
        let mut budget_items: Vec<EnrichedItem> = Vec::new();
        let mut total_chars = 0usize;
        for item in filtered {
            let item_chars = item.content.chars().count() + item.title.chars().count() + 50;
            if budget_items.len() >= max_items {
                break;
            }
            if total_chars + item_chars > self.config.max_chars && !budget_items.is_empty() {
                break;
            }
            budget_items.push(item);
            total_chars += item_chars;
        }

        EnrichedBundle {
            work: work.clone(),
            items: budget_items,
            total_searches: strategy_count(&strategy_results),
            total_raw_hits,
            total_chars,
        }
    }
}

fn strategy_count(v: &[(&'static str, Vec<UnifiedHit>)]) -> usize {
    v.len()
}

fn slice_up_to(v: &[String], n: usize) -> &[String] {
    if v.len() > n {
        &v[..n]
    } else {
        v
    }
}

/// Espejo de `_unified_hit_to_enriched` (+ helpers `_doc_type_from_doc` /
/// `_status_from_doc`: SemanticDocument no expone frontmatter ⇒ inferencia
/// por ruta; status siempre None).
fn unified_to_enriched_item(hit: &UnifiedHit, strategy: &str) -> Option<EnrichedItem> {
    match hit.source {
        "episodic" => {
            let entry = hit.entry.as_ref()?;
            Some(EnrichedItem {
                source: "episodic",
                source_id: entry.id.clone(),
                title: format!(
                    "[{}] {}",
                    entry.memory_type,
                    content_prefix(&entry.content, 100)
                ),
                content: entry.content.clone(),
                score: hit.score,
                enriched_score: hit.score,
                matched_by: vec![strategy.to_string()],
                files_mentioned: entry.files.clone(),
                date: Some(entry.timestamp.clone()),
                tags: entry.tags.clone(),
                doc_type: None,
                status: None,
                vault_scope: "local".to_string(),
                origin_project_id: None,
                matched_chunk_id: None,
                matched_section_title: None,
            })
        }
        "semantic" => {
            // Quirk fiel del oráculo: el item semántico lleva el score CRUDO
            // del documento (`hit.doc.score`), no el fusionado RRF.
            let doc = hit.doc?;
            Some(EnrichedItem {
                source: "semantic",
                source_id: doc.path.clone(),
                title: doc.title.clone(),
                content: doc.content.clone(),
                score: hit.doc_score_raw,
                enriched_score: hit.doc_score_raw,
                matched_by: vec![strategy.to_string()],
                files_mentioned: vec![],
                date: None,
                tags: doc.tags.clone(),
                doc_type: infer_doc_type_from_path(&doc.path),
                status: None,
                vault_scope: "local".to_string(),
                origin_project_id: None,
                matched_chunk_id: hit.matched_chunk_id.clone(),
                matched_section_title: hit.matched_section_title.clone(),
            })
        }
        _ => None,
    }
}

fn content_prefix(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// Puerto de `doc_type_from_path` (infer_doc_type_from_path): escanea TODOS
/// los segmentos menos el filename buscando el primer subfolder conocido;
/// `decisions/ADR-*` (case-insensitive) ⇒ Adr.
pub fn infer_doc_type_from_path(path: &str) -> Option<String> {
    let norm = path.replace('\\', "/");
    let parts: Vec<&str> = norm.split('/').filter(|p| !p.is_empty()).collect();
    if parts.len() < 2 {
        return None;
    }
    const SUBFOLDERS: [(&str, &str); 11] = [
        ("sessions", "session"),
        ("handoffs", "handoff"),
        ("specs", "spec"),
        ("incidents", "incident"),
        ("postmortems", "postmortem"),
        ("runbooks", "runbook"),
        ("architecture", "architecture"),
        ("changelog", "changelog"),
        ("hu", "hu"),
        ("glossary", "glossary"),
        ("designs", "design"),
    ];
    let mut subfolder: Option<&str> = None;
    for part in &parts[..parts.len() - 1] {
        if SUBFOLDERS.iter().any(|(k, _)| k == part) || *part == "decisions" {
            subfolder = Some(part);
            break;
        }
    }
    let sf = subfolder?;
    if sf == "decisions" {
        let name = parts[parts.len() - 1];
        let stem = match name.rfind('.') {
            Some(i) if i > 0 => &name[..i],
            _ => name,
        };
        return if adr_re(stem) {
            Some("adr".to_string())
        } else {
            Some("decision".to_string())
        };
    }
    SUBFOLDERS
        .iter()
        .find(|(k, _)| *k == sf)
        .map(|(_, slug)| slug.to_string())
}

/// ^ADR-\d+ case-insensitive.
fn adr_re(stem: &str) -> bool {
    let bytes = stem.as_bytes();
    stem.len() >= 5
        && stem[..3].eq_ignore_ascii_case("adr")
        && bytes[3] == b'-'
        && bytes[4].is_ascii_digit()
}

fn parse_doc_slug(slug: &str) -> Result<routing::DocType, ()> {
    use routing::DocType::*;
    Ok(match slug {
        "session" => Session,
        "handoff" => Handoff,
        "spec" => Spec,
        "adr" => Adr,
        "decision" => Decision,
        "incident" => Incident,
        "postmortem" => Postmortem,
        "runbook" => Runbook,
        "architecture" => Architecture,
        "changelog" => Changelog,
        "hu" => Hu,
        "glossary" => Glossary,
        "design" => Design,
        _ => return Err(()),
    })
}

#[cfg(test)]
mod tests {
    //! Espejos de tests/unit/context_enricher/test_enricher.py usando datos
    //! sintéticos sobre `_finalize_items` (las estrategias de búsqueda con
    //! modelo ya están gateadas por el golden P7).
    use super::*;
    use crate::context::models::WorkContext;
    use chrono::TimeZone;

    fn store_vacio() -> NativeEpisodicStore {
        NativeEpisodicStore {
            rows: vec![],
            src: std::path::PathBuf::new(),
        }
    }

    fn sem_vacio() -> SemanticIndex {
        // Índice sin docs: finalize no consulta semantic (los hits vienen
        // como datos); sólo se necesita para construir el enricher.
        let dir = std::env::temp_dir().join(format!(
            "ctx-sem-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(dir.join("vault")).unwrap();
        let idx = SemanticIndex::build(&dir.join("vault")).expect("índice vacío");
        std::fs::remove_dir_all(dir).ok();
        idx
    }

    fn hit_episodico(
        id: &str,
        score: f64,
        files: Vec<String>,
        tags: Vec<String>,
    ) -> UnifiedHit<'static> {
        UnifiedHit {
            source: "episodic",
            score,
            doc_score_raw: 0.0,
            dropped: false,
            entry: Some(crate::episodic::MemoryEntry {
                id: id.into(),
                content: format!("contenido de {id}"),
                memory_type: "note".into(),
                tags,
                files,
                timestamp: "2020-01-01T00:00:00+00:00".into(), // viejo ⇒ decay floor
                metadata: Default::default(),
            }),
            doc: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }

    fn now_fija() -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 8, 24, 12, 0, 0).unwrap()
    }

    /// TestEnricherMultiStrategy/TestEnricherBoost: un item matched por dos
    /// estrategias recibe boost multi_match^(n-1) y matched_by ordenado.
    #[test]
    fn multi_match_boost_y_matched_by() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config: ContextEnricherConfig {
                memory_decay: false,
                feedback_loop: false,
                ..Default::default()
            },
        };
        let strategies = vec![
            (
                "topic_search",
                vec![hit_episodico("mem_1", 0.5, vec![], vec![])],
            ),
            (
                "file_search",
                vec![hit_episodico("mem_1", 0.5, vec![], vec![])],
            ),
        ];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 8, now_fija());
        assert_eq!(bundle.total_raw_hits, 2);
        assert_eq!(bundle.items.len(), 1);
        let it = &bundle.items[0];
        assert_eq!(it.matched_by, vec!["file_search", "topic_search"]); // ordenado
        assert!((it.enriched_score - 0.5 * 1.5).abs() < 1e-12);
    }

    /// TestEnricherDedup: duplicado por source_id conserva el MAYOR score.
    #[test]
    fn dedup_conserva_mayor_score() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config: ContextEnricherConfig {
                memory_decay: false,
                feedback_loop: false,
                ..Default::default()
            },
        };
        let strategies = vec![
            (
                "topic_search",
                vec![hit_episodico("mem_x", 0.2, vec![], vec![])],
            ),
            (
                "file_search",
                vec![hit_episodico("mem_x", 0.7, vec![], vec![])],
            ),
        ];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 8, now_fija());
        assert_eq!(bundle.items.len(), 1);
        assert!((bundle.items[0].score - 0.7).abs() < 1e-12);
    }

    /// TestEnricherThreshold + budget: umbral min_score filtra y el
    /// presupuesto corta por cantidad y caracteres.
    #[test]
    fn umbral_y_presupuesto() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let config = ContextEnricherConfig {
            memory_decay: false,
            feedback_loop: false,
            graph_expansion: false,
            typed_graph: false,
            min_score: 0.3,
            max_items: 2,
            ..Default::default()
        };
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config,
        };
        let strategies = vec![(
            "topic_search",
            vec![
                hit_episodico("alto", 0.9, vec![], vec![]),
                hit_episodico("bajo", 0.1, vec![], vec![]), // < min_score ⇒ fuera
                hit_episodico("medio", 0.4, vec![], vec![]),
            ],
        )];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 2, now_fija());
        assert_eq!(bundle.items.len(), 2);
        assert_eq!(bundle.items[0].source_id, "alto");
        assert_eq!(bundle.items[1].source_id, "medio");
    }

    /// El primer item entra aunque exceda max_chars (regla del oráculo:
    /// `… and budget_items:` ⇒ sólo corta si YA hay algo).
    #[test]
    fn presupuesto_primer_item_siempre_entra() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let config = ContextEnricherConfig {
            memory_decay: false,
            feedback_loop: false,
            graph_expansion: false,
            typed_graph: false,
            max_chars: 60, // contenido+title+50 lo excede
            ..Default::default()
        };
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config,
        };
        let strategies = vec![(
            "topic_search",
            vec![hit_episodico("largo", 0.9, vec![], vec![])],
        )];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 5, now_fija());
        assert_eq!(bundle.items.len(), 1);
        assert!(bundle.total_chars > 60);
        assert!(!bundle.within_budget(60));
    }

    /// Decay: item episódico con timestamp viejo cae al floor; tag
    /// permanente queda en 1.0.
    #[test]
    fn decay_floor_y_permamente() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config: ContextEnricherConfig {
                feedback_loop: false,
                graph_expansion: false,
                typed_graph: false,
                ..Default::default()
            },
        };
        let strategies = vec![(
            "topic_search",
            vec![
                hit_episodico("viejo", 1.0, vec![], vec![]),
                hit_episodico("permanente", 1.0, vec![], vec!["decision".to_string()]),
            ],
        )];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 8, now_fija());
        let by_id = |id: &str| {
            bundle
                .items
                .iter()
                .find(|i| i.source_id == id)
                .unwrap_or_else(|| panic!("falta {id}"))
        };
        assert!((by_id("viejo").enriched_score - 0.10).abs() < 1e-12);
        assert!((by_id("permanente").enriched_score - 1.0).abs() < 1e-12);
    }

    /// Entity strategy: hits descartados (EpisodicHit en el oráculo) pero
    /// contando en total_raw_hits.
    #[test]
    fn entity_hits_solo_cuentan_raw() {
        let store = store_vacio();
        let semantic = sem_vacio();
        let enricher = ContextEnricher {
            episodic: &store,
            semantic: &semantic,
            config: ContextEnricherConfig {
                memory_decay: false,
                feedback_loop: false,
                graph_expansion: false,
                typed_graph: false,
                ..Default::default()
            },
        };
        let mut h = hit_episodico("mem_e", 0.9, vec![], vec![]);
        h.dropped = true;
        let strategies = vec![("entity_search", vec![h])];
        let work = WorkContext::manual(vec!["q"], vec![], vec![]);
        let bundle = enricher.finalize_items(strategies, &work, 8, now_fija());
        assert_eq!(bundle.total_raw_hits, 1);
        assert_eq!(bundle.total_searches, 1);
        assert!(bundle.items.is_empty());
    }
}
