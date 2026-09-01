//! Observador persistente de telemetría — réplica de
//! `cortex/context_enricher/telemetry.py` (P12A-7).
//!
//! Log JSONL append-only de eventos enrichment/citation en
//! `.cortex/enrichment-events.jsonl` con rotación a `.1.jsonl` a 5 MB.
//! Los fallos de persistencia nunca abortan el pipeline.

use std::path::{Path, PathBuf};

use chrono::Utc;
use regex::Regex;

use super::models::{EnrichedBundle, EnrichedItem};
use serde_json::Value;

use super::pyjson::{dumps_compact, Pj};

const WIKI_LINK_RE: &str = r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]";
const MD_LINK_RE: &str = r"\]\(([^)]+\.md)(?:#[^)]*)?\)";

/// Evento de enriquecimiento serializado (dict JSONL).
pub struct EnrichmentEvent {
    pub event_type: String,
    pub run_id: String,
    pub timestamp: String,
    pub latency_ms: Option<u64>,
    pub total_searches: usize,
    pub total_raw_hits: usize,
    pub total_items: usize,
    pub total_chars: usize,
    pub within_budget: bool,
    pub items_offered: Vec<Pj>,
}

impl EnrichmentEvent {
    /// Orden de claves = `dataclass.__dict__` de Python.
    pub fn to_pj(&self) -> Pj {
        Pj::Obj(vec![
            ("event_type".into(), Pj::Str(self.event_type.clone())),
            ("run_id".into(), Pj::Str(self.run_id.clone())),
            ("timestamp".into(), Pj::Str(self.timestamp.clone())),
            (
                "latency_ms".into(),
                match self.latency_ms {
                    Some(l) => Pj::U64(l),
                    None => Pj::Null,
                },
            ),
            ("total_searches".into(), Pj::U64(self.total_searches as u64)),
            ("total_raw_hits".into(), Pj::U64(self.total_raw_hits as u64)),
            ("total_items".into(), Pj::U64(self.total_items as u64)),
            ("total_chars".into(), Pj::U64(self.total_chars as u64)),
            ("within_budget".into(), Pj::Bool(self.within_budget)),
            ("items_offered".into(), Pj::Arr(self.items_offered.clone())),
        ])
    }

    pub fn to_json_line(&self) -> String {
        dumps_compact(&self.to_pj())
    }
}

/// Evento de citación serializado.
pub struct CitationEvent {
    pub event_type: String,
    pub run_id: String,
    pub timestamp: String,
    pub source_id: String,
}

impl CitationEvent {
    pub fn to_json_line(&self) -> String {
        dumps_compact(&Pj::Obj(vec![
            ("event_type".into(), Pj::Str(self.event_type.clone())),
            ("run_id".into(), Pj::Str(self.run_id.clone())),
            ("timestamp".into(), Pj::Str(self.timestamp.clone())),
            ("source_id".into(), Pj::Str(self.source_id.clone())),
        ]))
    }
}

/// items_offered canónicos para un ítem enriquecido.
pub fn offered_of(item: &EnrichedItem) -> Pj {
    Pj::Obj(vec![
        ("source_id".into(), Pj::Str(item.source_id.clone())),
        ("source".into(), Pj::Str(item.source.to_string())),
        ("score".into(), Pj::F64(item.score)),
        ("enriched_score".into(), Pj::F64(item.enriched_score)),
        (
            "matched_by".into(),
            Pj::Arr(item.matched_by.iter().map(|m| Pj::Str(m.clone())).collect()),
        ),
        (
            "tags".into(),
            Pj::Arr(item.tags.iter().map(|t| Pj::Str(t.clone())).collect()),
        ),
        (
            "files_mentioned".into(),
            Pj::Arr(
                item.files_mentioned
                    .iter()
                    .map(|f| Pj::Str(f.clone()))
                    .collect(),
            ),
        ),
    ])
}

/// Conversión Value→Pj preservando el ORDEN CANÓNICO de los eventos del
/// writer (los dict de Python re-cargados mantienen orden de documento; el
/// único writer es este módulo ⇒ orden fijo por schema).
fn value_to_pj_canonical(v: &serde_json::Value) -> Pj {
    const ENRICHMENT_KEYS: &[&str] = &[
        "event_type",
        "run_id",
        "timestamp",
        "latency_ms",
        "total_searches",
        "total_raw_hits",
        "total_items",
        "total_chars",
        "within_budget",
        "items_offered",
    ];
    const CITATION_KEYS: &[&str] = &["event_type", "run_id", "timestamp", "source_id"];
    const OFFERED_KEYS: &[&str] = &[
        "source_id",
        "source",
        "score",
        "enriched_score",
        "matched_by",
        "tags",
        "files_mentioned",
    ];
    let empty = serde_json::Map::new();
    let map = v.as_object().unwrap_or(&empty);
    let is_enrichment = map.get("items_offered").is_some_and(|x| x.is_array());
    let order: &[&str] = if is_enrichment {
        ENRICHMENT_KEYS
    } else if map.contains_key("source_id") && map.len() <= 4 {
        CITATION_KEYS
    } else if map.contains_key("enriched_score") {
        OFFERED_KEYS
    } else {
        // Fallback determinista.
        return raw_value_to_pj(v);
    };
    let mut fields: Vec<(String, Pj)> = vec![];
    for k in order {
        if let Some(val) = map.get(*k) {
            // Los ítems de items_offered también llevan orden canónico.
            let pj = if *k == "items_offered" {
                let empty_arr = Vec::new();
                let arr = val.as_array().unwrap_or(&empty_arr);
                Pj::Arr(arr.iter().map(value_to_pj_canonical).collect())
            } else {
                raw_value_to_pj(val)
            };
            fields.push(((*k).to_string(), pj));
        }
    }
    Pj::Obj(fields)
}

fn raw_value_to_pj(v: &serde_json::Value) -> Pj {
    use serde_json::Value as V;
    match v {
        V::Null => Pj::Null,
        V::Bool(b) => Pj::Bool(*b),
        V::Number(n) => {
            if let Some(i) = n.as_i64() {
                Pj::I64(i)
            } else if let Some(u) = n.as_u64() {
                Pj::U64(u)
            } else {
                Pj::F64(n.as_f64().unwrap_or(0.0))
            }
        }
        V::String(s) => Pj::Str(s.clone()),
        V::Array(items) => Pj::Arr(items.iter().map(raw_value_to_pj).collect()),
        V::Object(m) => {
            // Orden alfabético sólo para schemas desconocidos (no ocurre en gates).
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort();
            Pj::Obj(
                keys.into_iter()
                    .map(|k| (k.clone(), raw_value_to_pj(&m[k])))
                    .collect(),
            )
        }
    }
}

/// Observer persistente append-only.
pub struct PersistentObserver {
    path: PathBuf,
    enabled: bool,
}

impl PersistentObserver {
    pub fn new(telemetry_path: PathBuf, enabled: bool) -> Self {
        if enabled {
            if let Some(parent) = telemetry_path.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
        }
        Self {
            path: telemetry_path,
            enabled,
        }
    }

    pub fn enabled(&self) -> bool {
        self.enabled
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Registra un evento de enriquecimiento; devuelve el nuevo run_id
    /// ("" si disabled). `max_chars` define within_budget como el modelo.
    pub fn record_enrichment(
        &self,
        ctx: &EnrichedBundle,
        max_chars: usize,
        latency_ms: Option<u64>,
        run_id: &str,
        now_iso: &str,
    ) -> String {
        if !self.enabled {
            return String::new();
        }
        let run_id = if run_id.is_empty() {
            uuid_v4_hex12()
        } else {
            run_id.to_string()
        };
        let event = EnrichmentEvent {
            event_type: "enrichment".into(),
            run_id: run_id.clone(),
            timestamp: now_iso.to_string(),
            latency_ms,
            total_searches: ctx.total_searches,
            total_raw_hits: ctx.total_raw_hits,
            total_items: ctx.items.len(),
            total_chars: ctx.total_chars,
            within_budget: ctx.within_budget(max_chars),
            items_offered: ctx.items.iter().map(offered_of).collect(),
        };
        self.append(&event.to_json_line());
        run_id
    }

    /// Registra una citación (no-op si disabled o run_id vacío).
    pub fn record_citation(&self, run_id: &str, source_id: &str, now_iso: &str) {
        if !self.enabled || run_id.is_empty() {
            return;
        }
        let event = CitationEvent {
            event_type: "citation".into(),
            run_id: run_id.to_string(),
            timestamp: now_iso.to_string(),
            source_id: source_id.to_string(),
        };
        self.append(&event.to_json_line());
    }

    /// Todos los eventos (rotada primero, luego vivo); líneas malas se saltan.
    pub fn iter_events(&self) -> Vec<Value> {
        if !self.enabled {
            return vec![];
        }
        let mut events: Vec<Value> = vec![];
        let rotado = rotated_path(&self.path);
        for ruta in [rotado, self.path.clone()] {
            if !ruta.exists() {
                continue;
            }
            let Ok(content) = std::fs::read_to_string(&ruta) else {
                continue;
            };
            for line in content.lines() {
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                // Malformed ⇒ skip (logger.warning en Python).
                if let Ok(v) = serde_json::from_str::<Value>(line) {
                    events.push(v);
                }
            }
        }
        events
    }

    /// {"enrichment": <event>, "citations": [...]} para un run (JSON compacto).
    pub fn events_for_run(&self, run_id: &str) -> String {
        let mut enrichment: Option<Pj> = None;
        let mut citations: Vec<Pj> = vec![];
        for ev in self.iter_events() {
            if ev.get("run_id").and_then(Value::as_str) != Some(run_id) {
                continue;
            }
            match ev.get("event_type").and_then(Value::as_str) {
                Some("enrichment") => enrichment = Some(value_to_pj_canonical(&ev)),
                Some("citation") => citations.push(value_to_pj_canonical(&ev)),
                _ => {}
            }
        }
        dumps_compact(&Pj::Obj(vec![
            (
                "enrichment".into(),
                enrichment.unwrap_or_else(|| Pj::Obj(vec![])),
            ),
            ("citations".into(), Pj::Arr(citations)),
        ]))
    }

    /// Agregado estilo memory-report (JSON compacto con orden de dict de
    /// Python). `now` inyectable para ventanas deterministas.
    pub fn aggregate_json_at(&self, since_days: Option<i64>, now: chrono::DateTime<Utc>) -> String {
        dumps_compact(&self.aggregate_pj(since_days, now))
    }

    fn aggregate_pj(&self, since_days: Option<i64>, now: chrono::DateTime<Utc>) -> Pj {
        let events = self.iter_events();
        let cutoff = since_days.map(|d| now.naive_utc() - chrono::Duration::days(d));

        let mut enrichments: Vec<&Value> = vec![];
        let mut citations: Vec<&Value> = vec![];
        for ev in &events {
            let ts = ev
                .get("timestamp")
                .and_then(Value::as_str)
                .and_then(parse_ts_naive_utc);
            if let (Some(cut), Some(t)) = (cutoff, ts) {
                if t < cut {
                    continue;
                }
            }
            match ev.get("event_type").and_then(Value::as_str) {
                Some("enrichment") => enrichments.push(ev),
                Some("citation") => citations.push(ev),
                _ => {}
            }
        }

        // Citaciones indexadas por (run_id → [source_id] en orden).
        let mut cited_by_run: std::collections::HashMap<String, Vec<String>> =
            std::collections::HashMap::new();
        for c in &citations {
            let run = c.get("run_id").and_then(Value::as_str).unwrap_or_default();
            let sid = c
                .get("source_id")
                .and_then(Value::as_str)
                .unwrap_or_default();
            let entry = cited_by_run.entry(run.to_string()).or_default();
            if !entry.contains(&sid.to_string()) {
                entry.push(sid.to_string());
            }
        }

        let mut total_offered = 0usize;
        let mut total_used = 0usize;
        // Orden de estrategias = primer aparecimiento (= Counter de Python).
        let mut strategies: Vec<String> = vec![];
        let mut by_strategy_offered: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        let mut by_strategy_used: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        let mut latencies_ms: Vec<i64> = vec![];

        for ev in &enrichments {
            let run_id = ev.get("run_id").and_then(Value::as_str).unwrap_or_default();
            let empty = vec![];
            let offered = ev
                .get("items_offered")
                .and_then(Value::as_array)
                .unwrap_or(&empty);
            total_offered += offered.len();
            let used_in_run = cited_by_run.get(run_id);
            total_used += used_in_run.map(Vec::len).unwrap_or(0);
            for item in offered {
                let sid = item.get("source_id").and_then(Value::as_str).unwrap_or("");
                let is_used = used_in_run.is_some_and(|u| u.contains(&sid.to_string()));
                let matched_empty = vec![];
                let matched = item
                    .get("matched_by")
                    .and_then(Value::as_array)
                    .unwrap_or(&matched_empty);
                for strategy in matched {
                    let s = strategy.as_str().unwrap_or_default().to_string();
                    if !strategies.contains(&s) {
                        strategies.push(s.clone());
                    }
                    *by_strategy_offered.entry(s.clone()).or_insert(0) += 1;
                    if is_used {
                        *by_strategy_used.entry(s).or_insert(0) += 1;
                    }
                }
            }
            if let Some(lat) = ev.get("latency_ms") {
                if !lat.is_null() {
                    latencies_ms.push(lat.as_i64().unwrap_or(0));
                }
            }
        }

        latencies_ms.sort_unstable();

        let latency_pj = if latencies_ms.is_empty() {
            Pj::Obj(vec![])
        } else {
            Pj::Obj(vec![
                ("p50_ms".into(), Pj::F64(statistics_median(&latencies_ms))),
                (
                    "p95_ms".into(),
                    Pj::F64(percentile_sorted(&latencies_ms, 0.95)),
                ),
                (
                    "p99_ms".into(),
                    Pj::F64(percentile_sorted(&latencies_ms, 0.99)),
                ),
            ])
        };

        let by_strategy_fields: Vec<(String, Pj)> = strategies
            .iter()
            .map(|s| {
                let offered_n = by_strategy_offered.get(s).copied().unwrap_or(0);
                let used_n = by_strategy_used.get(s).copied().unwrap_or(0);
                (
                    s.clone(),
                    Pj::Obj(vec![
                        ("offered".into(), Pj::U64(offered_n as u64)),
                        ("used".into(), Pj::U64(used_n as u64)),
                        (
                            "hit_rate".into(),
                            Pj::F64(if offered_n > 0 {
                                used_n as f64 / offered_n as f64
                            } else {
                                0.0
                            }),
                        ),
                    ]),
                )
            })
            .collect();

        Pj::Obj(vec![
            (
                "window_days".into(),
                match since_days {
                    Some(d) => Pj::I64(d),
                    None => Pj::Null,
                },
            ),
            ("enrichments".into(), Pj::U64(enrichments.len() as u64)),
            ("citations".into(), Pj::U64(citations.len() as u64)),
            ("items_offered".into(), Pj::U64(total_offered as u64)),
            ("items_used".into(), Pj::U64(total_used as u64)),
            (
                "hit_rate".into(),
                Pj::F64(if total_offered > 0 {
                    total_used as f64 / total_offered as f64
                } else {
                    0.0
                }),
            ),
            ("by_strategy".into(), Pj::Obj(by_strategy_fields)),
            ("latency".into(), latency_pj),
        ])
    }

    pub fn aggregate_json(&self, since_days: Option<i64>) -> String {
        self.aggregate_json_at(since_days, Utc::now())
    }

    fn append(&self, line: &str) {
        // _rotate_if_needed + open("a").
        self.rotate_if_needed();
        use std::io::Write;
        if let Ok(mut fh) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
        {
            let _ = writeln!(fh, "{line}");
        }
    }

    const MAX_BYTES: u64 = 5 * 1024 * 1024;

    fn rotate_if_needed(&self) {
        let Ok(meta) = std::fs::metadata(&self.path) else {
            return;
        };
        if meta.len() < Self::MAX_BYTES {
            return;
        }
        let rotado = rotated_path(&self.path);
        if rotado.exists() {
            let _ = std::fs::remove_file(&rotado);
        }
        let _ = std::fs::rename(&self.path, rotado);
    }
}

fn rotated_path(path: &Path) -> PathBuf {
    // Path.with_suffix(".1.jsonl"): reemplaza la ÚLTIMA extensión completa.
    // events.jsonl → events.1.jsonl
    let stem = path
        .file_stem()
        .map(|s| s.to_os_string())
        .unwrap_or_default();
    path.with_file_name(format!("{}.1.jsonl", stem.to_string_lossy()))
}

/// Nuevo run_id (hex12 de uuid4) — público para el CLI (Cierre T2).
pub fn new_run_id() -> String {
    uuid_v4_hex12()
}

fn uuid_v4_hex12() -> String {
    uuid::Uuid::new_v4().simple().to_string()[..12].to_string()
}

/// ISO → naive UTC (acepta Z y offsets; None si no parsea).
fn parse_ts_naive_utc(value: &str) -> Option<chrono::NaiveDateTime> {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(value) {
        return Some(dt.with_timezone(&Utc).naive_utc());
    }
    chrono::NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%S%.f").ok()
}

fn statistics_median(values: &[i64]) -> f64 {
    let n = values.len();
    if n == 0 {
        return 0.0;
    }
    if n % 2 == 1 {
        values[n / 2] as f64
    } else {
        (values[n / 2 - 1] as f64 + values[n / 2] as f64) / 2.0
    }
}

/// Interpolación lineal igual que `_percentile` de Python sobre lista sorted.
fn percentile_sorted(sorted: &[i64], pct: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    if sorted.len() == 1 {
        return sorted[0] as f64;
    }
    let k = (sorted.len() - 1) as f64 * pct;
    let lo = k as usize;
    let hi = (lo + 1).min(sorted.len() - 1);
    let frac = k - lo as f64;
    sorted[lo] as f64 + (sorted[hi] - sorted[lo]) as f64 * frac
}

// ---------------------------------------------------------------------------
// Detección de citas
// ---------------------------------------------------------------------------

/// Detecta cuáles ítems ofrecidos fueron citados en el body de la sesión.
pub fn detect_citations(body: &str, items_offered: &[Value]) -> Vec<String> {
    if body.is_empty() || items_offered.is_empty() {
        return vec![];
    }
    let wiki_re = Regex::new(WIKI_LINK_RE).unwrap();
    let md_re = Regex::new(MD_LINK_RE).unwrap();
    let mut wiki_targets: Vec<String> = vec![];
    for c in wiki_re.captures_iter(body) {
        let t = c[1].trim().to_string();
        if !wiki_targets.contains(&t) {
            wiki_targets.push(t);
        }
    }
    let mut md_targets: Vec<String> = vec![];
    for c in md_re.captures_iter(body) {
        let t = c[1].trim().to_string();
        if !md_targets.contains(&t) {
            md_targets.push(t);
        }
    }

    let mut cited: Vec<String> = vec![];
    for item in items_offered {
        let Some(sid) = item.get("source_id").and_then(Value::as_str) else {
            continue;
        };
        if cited.contains(&sid.to_string()) {
            continue;
        }
        let path = Path::new(sid);
        let stem = path
            .file_stem()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default();
        let name = path
            .file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_else(|| sid.to_string());
        let posix_full = sid.replace('\\', "/");
        let posix_no_ext = posix_full
            .strip_suffix(".md")
            .unwrap_or(&posix_full)
            .to_string();
        let candidates = [sid.to_string(), stem, name, posix_full, posix_no_ext];
        let hit = candidates
            .iter()
            .any(|c| wiki_targets.contains(c) || md_targets.contains(c));
        if hit {
            cited.push(sid.to_string());
        }
    }
    cited
}

/// Réplica de `make_observer`: resuelve path y enabled desde config.
/// `config`: dict parseado de config.yaml (retrieval.telemetry.*).
pub fn make_observer(
    base: &Path,
    enabled_override: Option<bool>,
    config: Option<&Value>,
) -> PersistentObserver {
    let mut cfg_enabled = true;
    let mut cfg_path = ".cortex/enrichment-events.jsonl".to_string();
    if let Some(cfg) = config {
        if let Some(retrieval) = cfg.get("retrieval") {
            let telemetry_cfg = retrieval.get("telemetry").cloned().unwrap_or(Value::Null);
            // Python: `{} or {}` ⇒ falsy (None/dict vacío) → defaults.
            if telemetry_cfg.is_object() && !telemetry_cfg.as_object().unwrap().is_empty() {
                cfg_enabled = telemetry_cfg
                    .get("enabled")
                    .and_then(Value::as_bool)
                    .unwrap_or(cfg_enabled);
                if let Some(p) = telemetry_cfg.get("path").and_then(Value::as_str) {
                    if !p.is_empty() {
                        cfg_path = p.to_string();
                    }
                }
            }
        }
    }
    let enabled = enabled_override.unwrap_or(cfg_enabled);
    let telemetry_path = base.join(&cfg_path);
    // Python hace .resolve(); normalizamos lexically.
    let telemetry_path = normalize_path(&telemetry_path);
    PersistentObserver::new(telemetry_path, enabled)
}

fn normalize_path(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for comp in p.components() {
        use std::path::Component;
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bundle(n: usize) -> EnrichedBundle {
        EnrichedBundle {
            work: crate::context::models::WorkContext::default(),
            items: (0..n)
                .map(|i| EnrichedItem {
                    source_id: format!("item-{i}"),
                    tags: vec!["test".into()],
                    ..test_item()
                })
                .collect(),
            total_searches: 1,
            total_raw_hits: n,
            total_chars: n * 100,
            within_budget_override: None,
        }
    }

    fn test_item() -> EnrichedItem {
        EnrichedItem {
            source: "episodic",
            source_id: String::new(),
            title: "t".into(),
            content: "c".into(),
            score: 0.5,
            enriched_score: 0.6,
            matched_by: vec!["topic_search".into()],
            files_mentioned: vec![],
            date: None,
            tags: vec![],
            doc_type: None,
            status: None,
            vault_scope: "local".into(),
            origin_project_id: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }

    #[test]
    fn jsonl_linea_en_orden_canonico() {
        let obs_dir = std::env::temp_dir().join(format!("tl_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&obs_dir);
        let path = obs_dir.join("events.jsonl");
        let obs = PersistentObserver::new(path.clone(), true);
        let run = obs.record_enrichment(
            &bundle(2),
            10_000,
            Some(50),
            "",
            "2026-06-01T00:00:00+00:00",
        );
        obs.record_citation(&run, "item-0", "2026-06-01T00:00:01+00:00");
        let text = std::fs::read_to_string(&path).unwrap();
        let mut lines = text.lines();
        let l1 = lines.next().unwrap();
        assert!(l1.starts_with("{\"event_type\": \"enrichment\", \"run_id\": "));
        assert!(l1.contains("\"latency_ms\": 50"));
        let l2 = lines.next().unwrap();
        assert!(l2.starts_with("{\"event_type\": \"citation\""));
        std::fs::remove_dir_all(obs_dir).ok();
    }

    #[test]
    fn disabled_no_escribe_nada() {
        let dir = std::env::temp_dir().join(format!("tld_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        let path = dir.join("events.jsonl");
        let obs = PersistentObserver::new(path.clone(), false);
        assert_eq!(obs.record_enrichment(&bundle(1), 100, None, "", "x"), "");
        obs.record_citation("run", "s", "x");
        assert!(!path.exists());
        assert!(obs.iter_events().is_empty());
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn citas_wiki_md_alias_anchor() {
        use serde_json::json;
        let offered = vec![json!({"source_id": "decisions/ADR-007.md"})];
        assert_eq!(
            detect_citations("[[ADR-007#sección]]", &offered),
            vec!["decisions/ADR-007.md"]
        );
        assert_eq!(
            detect_citations("[t](decisions/ADR-007.md)", &offered),
            vec!["decisions/ADR-007.md"]
        );
        assert!(detect_citations("[[otra]]", &offered).is_empty());
    }

    #[test]
    fn percentiles_interpolan() {
        assert_eq!(percentile_sorted(&[100], 0.95), 100.0);
        assert_eq!(percentile_sorted(&[100, 200], 0.95), 195.0);
        assert_eq!(statistics_median(&[100, 200, 300]), 200.0);
        assert_eq!(statistics_median(&[100, 200]), 150.0);
    }
}
