//! Memoria episódica nativa (Obra 07 fase P3).
//!
//! Puerto de `cortex/episodic/memory_store.py` sobre formato neutro JSONL
//! (exportado por `bench/parity/episodic_golden.py` desde ChromaDB):
//!   {"id","document","meta":{…flattened…},"embedding":[f64]}
//!
//! Semántica replicada:
//! - búsqueda vectorial: score = max(0, coseno) (chroma cosine-space dist)
//! - keyword bypass: substring case-sensitive, score 1.0 (FIX P3: el path
//!   viejo con where_document puro lanzaba ValueError en chromadb moderno)
//! - deserialize de metadata flattenada (tags/files/metadata_json/entities)
//!
//! Persistencia destino definitiva (store propio append-only) se activa en
//! P12; acá el foco es paridad de datos y ranking sobre el export neutro.

use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Clone, PartialEq)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub files: Vec<String>,
    /// ISO-8601 tal cual persiste Python (se preserva en round-trip).
    pub timestamp: String,
    pub metadata: BTreeMap<String, serde_json::Value>,
}

/// Fila del export neutro.
#[derive(Debug, Clone)]
pub struct EpisodicRow {
    pub entry: MemoryEntry,
    /// Meta flattenada original (flags entity_* para el where-filter).
    pub raw_meta: serde_json::Map<String, serde_json::Value>,
    pub embedding: Vec<f64>,
}

fn meta_str(meta: &serde_json::Map<String, serde_json::Value>, key: &str) -> String {
    match meta.get(key) {
        Some(serde_json::Value::String(s)) => s.clone(),
        Some(v) if !v.is_null() => v.to_string(),
        _ => String::new(),
    }
}

fn meta_vec(meta: &serde_json::Map<String, serde_json::Value>, key: &str) -> Vec<String> {
    match meta.get(key) {
        Some(serde_json::Value::String(s)) => {
            serde_json::from_str::<Vec<String>>(s).unwrap_or_default()
        }
        Some(serde_json::Value::Array(a)) => a
            .iter()
            .filter_map(|x| x.as_str().map(String::from))
            .collect(),
        _ => Vec::new(),
    }
}

/// Puerto de `_deserialize_metadata` (sin la parte "now()" para timestamps
/// ausentes: el export siempre trae timestamp).
pub fn deserialize_row(
    id_fallback: &str,
    document: &str,
    meta: &serde_json::Map<String, serde_json::Value>,
) -> MemoryEntry {
    let id = meta_str(meta, "id");
    let id = if id.is_empty() {
        id_fallback.to_string()
    } else {
        id
    };
    let mut metadata: BTreeMap<String, serde_json::Value> = match meta.get("metadata_json") {
        Some(serde_json::Value::String(s)) => {
            serde_json::from_str::<BTreeMap<String, serde_json::Value>>(s).unwrap_or_default()
        }
        _ => BTreeMap::new(),
    };
    if metadata.is_empty() {
        // Puerto de `_extract_metadata_from_flat_fields` (flags entity_*).
        let mut entities: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for (k, v) in meta {
            if let (Some(rest), true) = (
                k.strip_prefix("entity_"),
                v == &serde_json::Value::Bool(true),
            ) {
                if let Some((etype, evalue)) = rest.split_once('_') {
                    entities
                        .entry(etype.to_string())
                        .or_default()
                        .push(evalue.to_string());
                }
            }
        }
        if !entities.is_empty() {
            metadata.insert(
                "entities".into(),
                serde_json::to_value(&entities).unwrap_or_default(),
            );
        }
    }
    MemoryEntry {
        id,
        content: document.to_string(),
        memory_type: {
            let t = meta_str(meta, "memory_type");
            if t.is_empty() {
                "general".into()
            } else {
                t
            }
        },
        tags: meta_vec(meta, "tags"),
        files: meta_vec(meta, "files"),
        timestamp: meta_str(meta, "timestamp"),
        metadata,
    }
}

/// Store episódico nativo cargado desde el export neutro.
pub struct NativeEpisodicStore {
    pub rows: Vec<EpisodicRow>,
}

impl NativeEpisodicStore {
    pub fn load(jsonl: &Path) -> Result<Self, String> {
        let text =
            std::fs::read_to_string(jsonl).map_err(|e| format!("{}: {e}", jsonl.display()))?;
        let mut rows = Vec::new();
        for (i, line) in text.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let v: serde_json::Value =
                serde_json::from_str(line).map_err(|e| format!("línea {}: {e}", i + 1))?;
            let obj = v.as_object().ok_or("fila no es objeto")?;
            let embedding = match obj.get("embedding").and_then(|e| e.as_array()) {
                Some(a) => a.iter().filter_map(|x| x.as_f64()).collect::<Vec<f64>>(),
                None => return Err(format!("línea {} sin embedding", i + 1)),
            };
            let raw_meta = obj
                .get("meta")
                .and_then(|m| m.as_object())
                .cloned()
                .unwrap_or_default();
            let entry = deserialize_row(
                obj.get("id").and_then(|x| x.as_str()).unwrap_or(""),
                obj.get("document").and_then(|x| x.as_str()).unwrap_or(""),
                &raw_meta,
            );
            rows.push(EpisodicRow {
                entry,
                raw_meta,
                embedding,
            });
        }
        // Orden canónico por id (los goldens también ordenan por id).
        rows.sort_by(|a, b| a.entry.id.cmp(&b.entry.id));
        Ok(Self { rows })
    }

    pub fn count(&self) -> usize {
        self.rows.len()
    }

    /// Entradas ordenadas por id (canónico de comparación con el oráculo).
    pub fn entries_sorted_by_id(&self) -> Vec<&MemoryEntry> {
        self.rows.iter().map(|r| &r.entry).collect()
    }

    /// Búsqueda vectorial: score = max(0, coseno), orden estable desc.
    pub fn vector_search(&self, query_vec: &[f64], top_k: usize) -> Vec<(&MemoryEntry, f64)> {
        let mut scored: Vec<(&MemoryEntry, f64)> = self
            .rows
            .iter()
            .map(|r| (&r.entry, cosine_max0(query_vec, &r.embedding)))
            .collect();
        scored.sort_by(|a, b| b.1.total_cmp(&a.1));
        scored.truncate(top_k);
        scored
    }

    /// Keyword bypass: substring case-sensitive, score 1.0, orden canónico.
    pub fn keyword_search(&self, needle: &str, top_k: usize) -> Vec<&MemoryEntry> {
        self.rows
            .iter()
            .filter(|r| r.entry.content.contains(needle))
            .map(|r| &r.entry)
            .take(top_k)
            .collect()
    }

    /// Puerto de `_entity_filter_key` + where-filter: flag
    /// `entity_{tipo}_{valor}` en la meta flattenada. Orden por id
    /// (determinista; el orden interno de chroma.get es indefinido).
    pub fn entity_ids(&self, entity_type: &str, entity_value: &str) -> Vec<String> {
        let key = entity_filter_key(entity_type, entity_value);
        let mut ids: Vec<String> = self
            .rows
            .iter()
            .filter(|r| matches!(r.raw_meta.get(&key), Some(serde_json::Value::Bool(true))))
            .map(|r| r.entry.id.clone())
            .collect();
        ids.sort();
        ids
    }

    /// Puerto de `search_by_entity`: candidatos por flag + score de match
    /// (`_entity_match_score`, con recencia dependiente de ``now``), sort
    /// estable desc y truncate a top_k.
    pub fn entity_search(
        &self,
        entity_type: &str,
        entity_value: &str,
        top_k: usize,
        now: chrono::DateTime<chrono::Utc>,
    ) -> Vec<(MemoryEntry, f64)> {
        let key = entity_filter_key(entity_type, entity_value);
        let mut hits: Vec<(MemoryEntry, f64)> = self
            .rows
            .iter()
            .filter(|r| matches!(r.raw_meta.get(&key), Some(serde_json::Value::Bool(true))))
            .map(|r| {
                let score = entity_match_score(&r.entry, entity_type, entity_value, now);
                (r.entry.clone(), score)
            })
            .collect();
        hits.sort_by(|a, b| b.1.total_cmp(&a.1));
        hits.truncate(top_k);
        hits
    }
}

/// Puerto de `_entity_match_score`: frecuencia del valor normalizado +
/// recencia (<24h +0.2 · >168h −0.1) con techo 1.0.
pub fn entity_match_score(
    entry: &MemoryEntry,
    entity_type: &str,
    entity_value: &str,
    now: chrono::DateTime<chrono::Utc>,
) -> f64 {
    let empty = serde_json::Map::new();
    let entities = entry
        .metadata
        .get("entities")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let values = entities
        .get(entity_type)
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let normalized_target = entity_value.trim().to_lowercase();
    let entity_count = values
        .iter()
        .filter(|v| {
            v.as_str()
                .map(|s| s.trim().to_lowercase() == normalized_target)
                .unwrap_or(false)
        })
        .count();
    let frequency_boost = ((entity_count as f64 - 1.0).max(0.0) * 0.1).min(0.3);

    // try/except ⇒ recency_boost 0.0 ante timestamps ilegibles.
    let ts = parse_ts_utc(&entry.timestamp).map(|t| t.with_timezone(&chrono::Utc));
    let recency_boost = match ts {
        None => 0.0,
        Some(t) => {
            let hours_old = (now - t).num_seconds() as f64 / 3600.0;
            if hours_old < 24.0 {
                0.2
            } else if hours_old > 168.0 {
                -0.1
            } else {
                0.0
            }
        }
    };

    (1.0 + frequency_boost + recency_boost).min(1.0)
}

fn parse_ts_utc(s: &str) -> Option<chrono::DateTime<chrono::Utc>> {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&chrono::Utc));
    }
    for fmt in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%d %H:%M:%S"] {
        if let Ok(dt) = chrono::DateTime::parse_from_str(s, fmt) {
            return Some(dt.with_timezone(&chrono::Utc));
        }
    }
    None
}

/// `_entity_filter_key`: normalizar tipo/valor y componer el flag.
pub fn entity_filter_key(entity_type: &str, entity_value: &str) -> String {
    fn norm(s: &str) -> String {
        s.trim()
            .chars()
            .map(|c| {
                if c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' {
                    c
                } else if c.is_ascii_uppercase() {
                    c.to_ascii_lowercase()
                } else {
                    '_'
                }
            })
            .collect::<String>()
            .trim_matches('_')
            .to_string()
    }
    format!("entity_{}_{}", norm(entity_type), norm(entity_value))
        .trim_matches('_')
        .to_string()
}

/// Coseno naive espejo de la ruta default de VaultReader/episódico.
pub fn cosine_max0(a: &[f64], b: &[f64]) -> f64 {
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let na: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let nb: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if na == 0.0 || nb == 0.0 {
        return 0.0;
    }
    let cos = dot / (na * nb);
    if cos < 0.0 {
        0.0
    } else {
        cos
    }
}
