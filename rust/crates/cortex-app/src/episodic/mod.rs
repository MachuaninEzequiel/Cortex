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

pub mod entities;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

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
    /// Ruta del JSONL de origen; `append` escribe la nueva fila acá.
    pub src: PathBuf,
}

/// Parámetros del puerto de `EpisodicMemoryStore.add`.
pub struct AppendParams {
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub files: Vec<String>,
    pub extra_metadata: Option<serde_json::Map<String, serde_json::Value>>,
}

impl AppendParams {
    pub fn new(content: impl Into<String>) -> Self {
        Self {
            content: content.into(),
            memory_type: "general".into(),
            tags: Vec::new(),
            files: Vec::new(),
            extra_metadata: None,
        }
    }
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
        Ok(Self {
            rows,
            src: jsonl.to_path_buf(),
        })
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

    /// Puerto de `EpisodicMemoryStore.add` sobre el store nativo JSONL
    /// (P12A-1): genera id (`mem_{hex8}`) y timestamp (ahora, ISO-8601 con
    /// microsegundos como `datetime.isoformat()`), extrae entidades del
    /// contenido y las mergea en metadata (la extracción pisa "entities" si
    /// hay, igual que en Python), serializa la meta flattenada con el mismo
    /// orden de claves de `_serialize_metadata`, calcula el embedding con el
    /// embedder provisto y agrega la fila al JSONL en modo append-only (las
    /// líneas previas quedan byte-idénticas) y al vec in-memory manteniendo
    /// el orden canónico por id.
    pub fn append(
        &mut self,
        params: AppendParams,
        embed: &mut dyn FnMut(&str) -> Result<Vec<f64>, String>,
    ) -> Result<MemoryEntry, String> {
        let extracted = entities::extract_entities(&params.content);
        let mut metadata: BTreeMap<String, serde_json::Value> = params
            .extra_metadata
            .clone()
            .map(|m| m.into_iter().collect())
            .unwrap_or_default();
        if !extracted.is_empty() {
            let obj: serde_json::Map<String, serde_json::Value> = extracted
                .iter()
                .map(|(t, vs)| {
                    (
                        t.clone(),
                        serde_json::Value::Array(
                            vs.iter().cloned().map(serde_json::Value::String).collect(),
                        ),
                    )
                })
                .collect();
            metadata.insert("entities".into(), serde_json::Value::Object(obj));
        }
        let entry = MemoryEntry {
            id: new_memory_id(),
            content: params.content,
            memory_type: if params.memory_type.is_empty() {
                "general".into()
            } else {
                params.memory_type
            },
            tags: params.tags,
            files: params.files,
            timestamp: now_isoformat(),
            metadata,
        };
        let embedding = embed(&entry.content)?;
        let meta_flat = serialize_metadata(&entry);
        self.append_row(EpisodicRow {
            entry: entry.clone(),
            raw_meta: meta_flat.into_iter().collect(),
            embedding,
        })?;
        Ok(entry)
    }

    /// Escribe la fila al JSONL (una línea, formato export neutro) y la
    /// inserta en `rows` en su posición por id.
    fn append_row(&mut self, row: EpisodicRow) -> Result<(), String> {
        use std::io::Write;
        let line = row_to_jsonl_line(&row);
        let mut f = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.src)
            .map_err(|e| format!("{}: {e}", self.src.display()))?;
        f.write_all(line.as_bytes())
            .map_err(|e| format!("{}: {e}", self.src.display()))?;
        let pos = self.rows.partition_point(|r| r.entry.id < row.entry.id);
        self.rows.insert(pos, row);
        Ok(())
    }

    /// Puerto de `EpisodicMemoryStore.delete` (CLI `cortex forget`): borra la
    /// entrada `mem_*` del JSONL de origen y del vec in-memory.
    ///
    /// Ok(true) si el id existía; Ok(false) si no (el archivo queda
    /// intacto). El resto de las líneas se preserva BYTE-idéntico (se
    /// reescribe el archivo filtrando solo la fila borrada, sin
    /// re-serialización del resto).
    pub fn delete(&mut self, id: &str) -> Result<bool, String> {
        let text = std::fs::read_to_string(&self.src)
            .map_err(|e| format!("{}: {e}", self.src.display()))?;
        let mut kept = String::new();
        let mut removed = false;
        for line in text.lines() {
            if line.trim().is_empty() {
                continue;
            }
            let matches = match serde_json::from_str::<serde_json::Value>(line) {
                Ok(v) => v.get("id").and_then(|i| i.as_str()) == Some(id),
                // Línea ilegible: preservarla tal cual (nunca perder datos).
                Err(_) => false,
            };
            if matches {
                removed = true;
            } else {
                kept.push_str(line);
                kept.push('\n');
            }
        }
        if !removed {
            return Ok(false);
        }
        std::fs::write(&self.src, kept).map_err(|e| format!("{}: {e}", self.src.display()))?;
        self.rows.retain(|r| r.entry.id != id);
        Ok(true)
    }
}

// ── Escritura (P12A-1): serialización estilo Python ────────────────────────

/// Espejo del repr de float de CPython (shortest round-trip, ".0" forzado).
fn py_float_repr(x: f64) -> String {
    let s = format!("{x}");
    if s.contains('.') || s.contains('e') || s.contains('E') {
        s
    } else {
        format!("{s}.0")
    }
}

/// Escape JSON de Python (`json.dumps(..., ensure_ascii=False)`): unicode
/// crudo, `\b`/`\f`/`\n`/`\r`/`\t` nombrados, resto <0x20 como \u00XX.
fn py_json_string(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// `json.dumps(v, ensure_ascii=False)` compacto (separadores ", "/": "),
/// floats con repr de CPython. Los objetos iteran en orden del Map
/// (BTreeMap = orden lexicográfico, equivalente al sort_keys=True). Con
/// `sort_keys=false` se preserva igual el orden del Map (serde_json sin
/// preserve_order no retiene orden de inserción).
pub fn py_dumps_compact(v: &serde_json::Value, sort_keys: bool) -> String {
    let mut out = String::new();
    py_emit(v, sort_keys, &mut out);
    out
}

fn py_emit(v: &serde_json::Value, sort_keys: bool, out: &mut String) {
    match v {
        serde_json::Value::Null => out.push_str("null"),
        serde_json::Value::Bool(b) => {
            out.push_str(if *b { "true" } else { "false" });
        }
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                out.push_str(&i.to_string());
            } else if let Some(u) = n.as_u64() {
                out.push_str(&u.to_string());
            } else if let Some(f) = n.as_f64() {
                out.push_str(&py_float_repr(f));
            }
        }
        serde_json::Value::String(s) => out.push_str(&py_json_string(s)),
        serde_json::Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                py_emit(item, sort_keys, out);
            }
            out.push(']');
        }
        serde_json::Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            if sort_keys {
                keys.sort();
            }
            out.push('{');
            for (i, k) in keys.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                out.push_str(&py_json_string(k));
                out.push_str(": ");
                py_emit(&map[*k], sort_keys, out);
            }
            out.push('}');
        }
    }
}

/// Puerto de `_serialize_metadata`: aplana MemoryEntry a metadata ChromaDB
/// compatible, con el MISMO orden de claves que Python (id, memory_type,
/// tags, files, timestamp, metadata_json y después los flags entity_*).
pub fn serialize_metadata(entry: &MemoryEntry) -> Vec<(String, serde_json::Value)> {
    let mut out: Vec<(String, serde_json::Value)> = vec![
        ("id".into(), serde_json::Value::String(entry.id.clone())),
        (
            "memory_type".into(),
            serde_json::Value::String(entry.memory_type.clone()),
        ),
        (
            "tags".into(),
            serde_json::Value::String(py_dumps_compact(
                &serde_json::to_value(&entry.tags).unwrap_or_default(),
                false,
            )),
        ),
        (
            "files".into(),
            serde_json::Value::String(py_dumps_compact(
                &serde_json::to_value(&entry.files).unwrap_or_default(),
                false,
            )),
        ),
        (
            "timestamp".into(),
            serde_json::Value::String(entry.timestamp.clone()),
        ),
        (
            "metadata_json".into(),
            serde_json::Value::String(py_dumps_compact(
                &serde_json::to_value(&entry.metadata).unwrap_or_default(),
                true,
            )),
        ),
    ];
    if let Some(serde_json::Value::Object(entities)) = entry.metadata.get("entities") {
        for (etype, values) in entities {
            let Some(vals) = values.as_array() else {
                continue;
            };
            for value in vals {
                let Some(s) = value.as_str() else { continue };
                out.push((entity_filter_key(etype, s), serde_json::Value::Bool(true)));
            }
        }
    }
    out
}

/// Línea JSONL formato export neutro para una fila:
/// `{"id": …, "document": …, "meta": {…}, "embedding": [...]}` — espejo de
/// `json.dumps(row, ensure_ascii=False)` del exportador P3.
fn row_to_jsonl_line(row: &EpisodicRow) -> String {
    let mut out = String::new();
    out.push_str("{\"id\": ");
    out.push_str(&py_json_string(&row.entry.id));
    out.push_str(", \"document\": ");
    out.push_str(&py_json_string(&row.entry.content));
    out.push_str(", \"meta\": {");
    for (i, (k, v)) in serialize_metadata(&row.entry).iter().enumerate() {
        if i > 0 {
            out.push_str(", ");
        }
        out.push_str(&py_json_string(k));
        out.push_str(": ");
        out.push_str(&py_dumps_compact(v, false));
    }
    out.push_str("}, \"embedding\": [");
    for (i, x) in row.embedding.iter().enumerate() {
        if i > 0 {
            out.push_str(", ");
        }
        out.push_str(&py_float_repr(*x));
    }
    out.push_str("]}\n");
    out
}

/// `f"mem_{uuid4().hex[:8]}"` (default_factory de MemoryEntry).
fn new_memory_id() -> String {
    format!("mem_{}", &uuid::Uuid::new_v4().simple().to_string()[..8])
}

/// `datetime.now(UTC).isoformat()` — microsegundos y offset +00:00.
fn now_isoformat() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, false)
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

#[cfg(test)]
mod append_tests {
    use super::*;

    fn jsonl_tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cortex_epi_{tag}_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d.join("memories.jsonl")
    }

    /// Embedder fake determinista: [len, primer_byte, último_byte] como f64.
    fn fake_embed() -> impl FnMut(&str) -> Result<Vec<f64>, String> {
        |c: &str| {
            let b = c.as_bytes();
            Ok(vec![
                b.len() as f64,
                *b.first().unwrap_or(&0) as f64,
                *b.last().unwrap_or(&0) as f64,
            ])
        }
    }

    fn fila_base(id: &str, doc: &str, mtype: &str, ts: &str) -> String {
        format!(
            "{{\"id\": \"{id}\", \"document\": \"{doc}\", \"meta\": {{\"id\": \"{id}\", \"memory_type\": \"{mtype}\", \"tags\": \"[]\", \"files\": \"[]\", \"timestamp\": \"{ts}\", \"metadata_json\": \"{{}}\"}}, \"embedding\": [0.1, 0.2, 0.3]}}\n"
        )
    }

    #[test]
    fn append_round_trip_y_busqueda() {
        let path = jsonl_tmp("rt");
        let base1 = fila_base(
            "mem_aaaa1111",
            "Se arregló authenticate_user.",
            "bugfix",
            "2026-05-10T12:00:00+00:00",
        );
        let base2 = fila_base(
            "mem_bbbb2222",
            "Nota sin entidades.",
            "note",
            "2026-05-11T12:00:00+00:00",
        );
        std::fs::write(&path, format!("{base1}{base2}")).unwrap();
        let bytes_pre = std::fs::read(&path).unwrap();

        let mut store = NativeEpisodicStore::load(&path).unwrap();
        assert_eq!(store.count(), 2);

        let entry = store
            .append(
                AppendParams {
                    content: "Se actualizó la función authenticate_user en auth.py; class FeedbackStore persiste feedback.jsonl".into(),
                    memory_type: "refactor".into(),
                    tags: vec!["vault".into()],
                    files: vec![],
                    extra_metadata: None,
                },
                &mut fake_embed(),
            )
            .unwrap();

        // id/timestamp formato Python.
        assert!(
            entry.id.starts_with("mem_") && entry.id.len() == 12,
            "{}",
            entry.id
        );
        assert!(entry.timestamp.ends_with("+00:00"));
        assert_eq!(
            entry.metadata["entities"]["class"],
            serde_json::json!(["FeedbackStore"])
        );

        // In-memory mantiene orden por id e incluye la nueva fila.
        assert_eq!(store.count(), 3);
        let ids: Vec<&str> = store.rows.iter().map(|r| r.entry.id.as_str()).collect();
        let mut ordenado = ids.clone();
        ordenado.sort();
        assert_eq!(ids, ordenado);

        // Keyword search encuentra lo recién agregado tras recargar.
        drop(store);
        let store2 = NativeEpisodicStore::load(&path).unwrap();
        assert_eq!(store2.count(), 3);
        let hits = store2.keyword_search("FeedbackStore", 5);
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].memory_type, "refactor");

        // Las líneas previas quedaron byte-idénticas (append-only).
        let bytes_post = std::fs::read(&path).unwrap();
        assert!(bytes_post.starts_with(&bytes_pre));
        let texto_post = String::from_utf8(bytes_post).unwrap();
        assert!(texto_post.ends_with('\n'));

        // La línea nueva parsea como export neutro con las claves esperadas.
        let ultima = texto_post.lines().last().unwrap();
        let v: serde_json::Value = serde_json::from_str(ultima).unwrap();
        for k in ["id", "document", "meta", "embedding"] {
            assert!(v.get(k).is_some(), "falta {k}");
        }
        let meta_keys: Vec<&str> = v["meta"]
            .as_object()
            .unwrap()
            .keys()
            .map(|s| s.as_str())
            .collect();
        for esperada in [
            "id",
            "memory_type",
            "tags",
            "files",
            "timestamp",
            "metadata_json",
            "entity_class_feedbackstore", // _entity_filter_key normaliza a minúsculas
        ] {
            assert!(
                meta_keys.contains(&esperada),
                "meta sin {esperada}: {meta_keys:?}"
            );
        }
        // tags/files serializados estilo Python (", " separador) como string JSON.
        assert_eq!(v["meta"]["tags"], serde_json::json!("[\"vault\"]"));
    }

    #[test]
    fn append_extra_metadata_y_entities_pisa() {
        let path = jsonl_tmp("extra");
        std::fs::write(&path, "").unwrap();
        let mut store = NativeEpisodicStore::load(&path).unwrap();
        let mut extra = serde_json::Map::new();
        extra.insert("origen".into(), serde_json::Value::String("prueba".into()));
        extra.insert("entities".into(), serde_json::json!({"class": ["VIEJA"]}));
        let entry = store
            .append(
                AppendParams {
                    content: "class Nueva hace algo.".into(),
                    memory_type: "general".into(),
                    tags: vec![],
                    files: vec!["src/lib.py".into()],
                    extra_metadata: Some(extra),
                },
                &mut fake_embed(),
            )
            .unwrap();
        // La extracción pisa "entities" del extra (semántica add()).
        assert_eq!(
            entry.metadata["entities"]["class"],
            serde_json::json!(["Nueva"])
        );
        assert_eq!(entry.metadata["origen"], serde_json::json!("prueba"));
    }

    /// Puerto de `EpisodicMemoryStore.delete` (CLI `cortex forget`): borra la
    /// entrada del JSONL y del vec in-memory; Ok(false) si no existe.
    #[test]
    fn delete_remueve_la_fila_y_preserva_el_resto() {
        let path = jsonl_tmp("del");
        let linea1 = fila_base(
            "mem_aaaa1111",
            "Se arregló authenticate_user.",
            "bugfix",
            "2026-05-10T12:00:00+00:00",
        );
        let linea2 = fila_base(
            "mem_bbbb2222",
            "Nota sin entidades.",
            "note",
            "2026-05-11T12:00:00+00:00",
        );
        std::fs::write(&path, format!("{linea1}{linea2}")).unwrap();
        let bytes_antes = std::fs::read(&path).unwrap();

        let mut store = NativeEpisodicStore::load(&path).unwrap();
        assert_eq!(store.count(), 2);

        // Id inexistente: Ok(false) y archivo intacto.
        assert!(!store.delete("mem_zzzz9999").unwrap());
        assert_eq!(std::fs::read(&path).unwrap(), bytes_antes);
        assert_eq!(store.count(), 2);

        // Id existente: Ok(true), la línea desaparece y el resto sigue igual.
        assert!(store.delete("mem_aaaa1111").unwrap());
        assert_eq!(store.count(), 1);
        let texto = std::fs::read_to_string(&path).unwrap();
        assert_eq!(texto, linea2, "resto byte-idéntico");
        assert!(!texto.contains("mem_aaaa1111"));
        assert!(texto.ends_with('\n'));

        // Recargar desde disco confirma la persistencia.
        let store2 = NativeEpisodicStore::load(&path).unwrap();
        assert_eq!(store2.count(), 1);
        assert_eq!(store2.rows[0].entry.id, "mem_bbbb2222");

        // El borrado no rompe append posteriores.
        let mut store3 = store;
        store3
            .append(
                AppendParams::new("nueva memoria tras el delete"),
                &mut fake_embed(),
            )
            .unwrap();
        assert_eq!(store3.count(), 2);
        assert_eq!(store3.keyword_search("nueva memoria", 5).len(), 1);
    }
}
