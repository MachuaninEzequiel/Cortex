//! Puerto de `cortex/workitems` (P12A-2): models + trait provider +
//! WorkItemService (import/get/list/has_provider) usando el writer canónico
//! `cortex-setup::writers::build_note("hu")` (API estable de P8b — la
//! escritura byte-parity viene del golden hu_jira de writers).
//!
//! Espeja `tests/unit/workitems/test_service.py`: naming canónico
//! `HU-{external_id}.md` (routing.py DocType.HU) con fallback al slug legacy,
//! idempotencia por fingerprint y DuplicateDocumentError ante contenido
//! distinto.
//!
//! Divergencias documentadas:
//! - El reloj es explícito (`now: DateTime<Utc>` en import_item): los writers
//!   nativos de P8 ya hacen explícito el tiempo; Python lo toma de now().
//! - Los errores son Result<String> con los mensajes de Python como contrato.

use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use cortex_setup::writers::{build_note, NoteRequest};

use crate::episodic::{AppendParams, MemoryEntry, NativeEpisodicStore};
use crate::security::resolve_safe;
use crate::semantic::SemanticIndex;

// ── Models (cortex/workitems/models.py) ─────────────────────────────────────

/// `WorkItemSource` — por hoy sólo Jira (read-only).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkItemSource {
    Jira,
}

impl WorkItemSource {
    pub fn value(self) -> &'static str {
        match self {
            Self::Jira => "jira",
        }
    }
}

impl std::fmt::Display for WorkItemSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.value())
    }
}

/// `WorkItemKind`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkItemKind {
    Story,
    Task,
    Bug,
    Epic,
    Incident,
    Other,
}

impl WorkItemKind {
    pub fn value(self) -> &'static str {
        match self {
            Self::Story => "story",
            Self::Task => "task",
            Self::Bug => "bug",
            Self::Epic => "epic",
            Self::Incident => "incident",
            Self::Other => "other",
        }
    }

    pub fn parse(s: &str) -> Self {
        match s {
            "story" => Self::Story,
            "task" => Self::Task,
            "bug" => Self::Bug,
            "epic" => Self::Epic,
            "incident" => Self::Incident,
            _ => Self::Other,
        }
    }
}

impl std::fmt::Display for WorkItemKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.value())
    }
}

/// `TrackedItem` — representación interna canónica de un item importado.
#[derive(Debug, Clone)]
pub struct TrackedItem {
    pub id: String,
    pub external_id: String,
    pub source: WorkItemSource,
    pub kind: WorkItemKind,
    pub title: String,
    pub description: String,
    pub acceptance_criteria: Vec<String>,
    pub status: Option<String>,
    pub labels: Vec<String>,
    pub assignee: Option<String>,
    pub metadata: BTreeMap<String, serde_json::Value>,
    pub vault_path: Option<String>,
    pub external_url: Option<String>,
    /// ISO-8601 UTC (pydantic serializa con microsegundos + Z).
    pub sync_timestamp: Option<String>,
}

impl TrackedItem {
    pub fn new(id: impl Into<String>, source: WorkItemSource, title: impl Into<String>) -> Self {
        let id = id.into();
        Self {
            external_id: id.clone(),
            id,
            source,
            kind: WorkItemKind::Other,
            title: title.into(),
            description: String::new(),
            acceptance_criteria: Vec::new(),
            status: None,
            labels: Vec::new(),
            assignee: None,
            metadata: BTreeMap::new(),
            vault_path: None,
            external_url: None,
            sync_timestamp: None,
        }
    }
}

// ── Provider trait (providers/base.py) ──────────────────────────────────────

/// Puerto de `WorkItemProvider`.
pub trait WorkItemProvider {
    fn source_name(&self) -> &str;
    fn is_configured(&self) -> bool;
    /// Errores con mensaje de Python cuando aplique.
    fn get_item(&self, external_id: &str) -> Result<TrackedItem, String>;
}

// ── Puertos de dependencias (inyectables para tests/gates) ─────────────────

/// Puerto de `VaultReader.index_file` tal como lo consume el servicio.
pub trait SemanticIndexer {
    fn index_file(&mut self, rel_path: &str) -> bool;
}

/// Request de memoria episódica (campos de `_store_episodic` → `add`).
pub struct EpisodicMemoryRequest {
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub files: Vec<String>,
    pub extra_metadata: BTreeMap<String, serde_json::Value>,
}

/// Puerto de `EpisodicMemoryStore.add` para el resumen del item.
pub trait EpisodicSink {
    fn add_memory(&mut self, req: EpisodicMemoryRequest) -> Result<MemoryEntry, String>;
}

/// Adapter real sobre `SemanticIndex` + embedder ort.
pub struct LiveSemanticIndexer<'a> {
    pub vault: &'a Path,
    pub index: &'a mut SemanticIndex,
    pub embedder: &'a mut cortex_embed::onnx::OnnxEmbedder,
}

impl SemanticIndexer for LiveSemanticIndexer<'_> {
    fn index_file(&mut self, rel_path: &str) -> bool {
        let Self {
            vault,
            index,
            embedder,
        } = self;
        index
            .index_file(vault, rel_path, &mut |texts| {
                embedder.embed_batch(texts).map_err(|e| e.to_string())
            })
            .unwrap_or(false)
    }
}

/// Adapter real sobre `NativeEpisodicStore` + embedder ort (usa append P12A-1).
pub struct LiveEpisodicSink<'a> {
    pub store: &'a mut NativeEpisodicStore,
    pub embedder: &'a mut cortex_embed::onnx::OnnxEmbedder,
}

impl EpisodicSink for LiveEpisodicSink<'_> {
    fn add_memory(&mut self, req: EpisodicMemoryRequest) -> Result<MemoryEntry, String> {
        let embedder = &mut *self.embedder;
        self.store.append(
            AppendParams {
                content: req.content,
                memory_type: req.memory_type,
                tags: req.tags,
                files: req.files,
                extra_metadata: Some(req.extra_metadata.into_iter().collect()),
            },
            &mut |c: &str| {
                embedder
                    .embed_batch(std::slice::from_ref(&c.to_string()))
                    .map_err(|e| e.to_string())?
                    .into_iter()
                    .next()
                    .ok_or_else(|| "sin vector".to_string())
            },
        )
    }
}

// ── Service (service.py) ────────────────────────────────────────────────────

/// `_STATUS_MAP`: status legacy del provider → estado canónico del frontmatter.
fn status_canonico(legacy: &str) -> String {
    match legacy {
        "imported" => "backlog".into(),
        "in_progress" => "in-progress".into(),
        other => other.to_string(),
    }
}

/// `_slug` del fallback legacy.
fn slug(value: &str) -> String {
    let mut out = String::new();
    let mut prev_dash = true; // strip("-") inicial
    for c in value.trim().to_lowercase().chars() {
        if c.is_ascii_alphanumeric() || c == '_' || c == '-' {
            out.push(c);
            prev_dash = false;
        } else if !prev_dash {
            out.push('-');
            prev_dash = true;
        }
    }
    let out = out.trim_matches('-').to_string();
    if out.is_empty() {
        "item".to_string()
    } else {
        out
    }
}

pub struct WorkItemService<'a> {
    vault_path: PathBuf,
    providers: HashMap<String, Box<dyn WorkItemProvider>>,
    context_metadata: BTreeMap<String, serde_json::Value>,
    semantic: Option<&'a mut dyn SemanticIndexer>,
    episodic: Option<&'a mut dyn EpisodicSink>,
}

impl<'a> WorkItemService<'a> {
    pub fn new(
        vault_path: impl Into<PathBuf>,
        providers: HashMap<String, Box<dyn WorkItemProvider>>,
        semantic: Option<&'a mut dyn SemanticIndexer>,
        episodic: Option<&'a mut dyn EpisodicSink>,
    ) -> Self {
        Self {
            vault_path: vault_path.into(),
            providers,
            context_metadata: BTreeMap::new(),
            semantic,
            episodic,
        }
    }

    pub fn with_context_metadata(mut self, meta: BTreeMap<String, serde_json::Value>) -> Self {
        self.context_metadata = meta;
        self
    }

    /// Puerto de `import_item`. `now` alimenta al writer canónico
    /// (created_at/updated_at), igual que P8.
    pub fn import_item(
        &mut self,
        external_id: &str,
        provider: &str,
        remember: bool,
        now: DateTime<Utc>,
    ) -> Result<PathBuf, String> {
        // 1. Provider lookup + get_item (borrows inmutables acotados).
        let normalized = provider.trim().to_lowercase();
        let prov = self
            .providers
            .get(&normalized)
            .ok_or_else(|| format!("Unknown work item provider: {provider}"))?;
        if !prov.is_configured() {
            return Err(format!("Provider '{provider}' is not configured."));
        }
        let item = prov.get_item(external_id)?;

        // 2. Escribir la nota canónica (hu/HU-{external_id}.md).
        let path = self.write_item_note(&item, now)?;
        let rel_path = path
            .strip_prefix(&self.vault_path)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/");

        // 3. Reindexar semánticamente.
        if let Some(indexer) = self.semantic.as_deref_mut() {
            indexer.index_file(&rel_path);
        }

        // 4. Memoria episódica (remember=True por defecto en Python).
        if remember {
            if let Some(sink) = self.episodic.as_deref_mut() {
                sink.add_memory(Self::episodic_request(
                    &item,
                    &rel_path,
                    &self.context_metadata,
                ))?;
            }
        }
        Ok(path)
    }

    /// Puerto de `get_item_note`: naming canónico HU-{id}.md con fallback al
    /// slug legacy (bug #10). FileNotFoundError ⇒ Err con el mismo mensaje.
    pub fn get_item_note(&self, item_id: &str) -> Result<PathBuf, String> {
        let canonical = resolve_safe(
            &self.vault_path,
            &Path::new("hu").join(format!("HU-{item_id}.md")),
        )
        .map_err(|e| e.to_string())?;
        if canonical.exists() {
            return Ok(canonical);
        }
        let legacy = resolve_safe(
            &self.vault_path,
            &Path::new("hu").join(format!("{}.md", slug(item_id))),
        )
        .map_err(|e| e.to_string())?;
        if legacy.exists() {
            return Ok(legacy);
        }
        Err(format!("Tracked item not found in vault: {item_id}"))
    }

    /// Puerto de `list_item_notes`: hu/*.md ordenado.
    pub fn list_item_notes(&self) -> Vec<PathBuf> {
        let hu_dir = self.vault_path.join("hu");
        let Ok(rd) = std::fs::read_dir(&hu_dir) else {
            return Vec::new();
        };
        let mut out: Vec<PathBuf> = rd
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("md"))
            .collect();
        out.sort();
        out
    }

    /// Puerto de `has_provider`: lookup DIRECTO por clave, sin normalizar
    /// (la normalización trim+lower vive sólo en `_provider`/import_item).
    pub fn has_provider(&self, provider: &str) -> bool {
        self.providers
            .get(provider)
            .map(|p| p.is_configured())
            .unwrap_or(false)
    }

    // ── internals ──

    /// `_write_item_note`: tags/status/title + HUData → write_hu_note local
    /// sobre build_note("hu") + semántica de duplicados de _write_note.
    fn write_item_note(
        &mut self,
        item: &TrackedItem,
        now: DateTime<Utc>,
    ) -> Result<PathBuf, String> {
        let mut tags = vec![
            "hu".to_string(),
            item.source.value().to_string(),
            item.kind.value().to_string(),
        ];
        tags.extend(item.labels.iter().cloned());
        let title = format!("{}: {}", item.id, item.title);
        // Python: `item.status or "imported"` ⇒ None Y "" caen al default.
        let legacy_status = match item.status.as_deref() {
            Some(s) if !s.is_empty() => s.to_string(),
            _ => "imported".to_string(),
        };
        let status = status_canonico(&legacy_status);

        let mut fields: serde_json::Map<String, serde_json::Value> = serde_json::Map::new();
        fields.insert("title".into(), serde_json::Value::String(title));
        fields.insert("status".into(), serde_json::Value::String(status));
        fields.insert(
            "tags".into(),
            serde_json::to_value(&tags).unwrap_or_default(),
        );
        fields.insert(
            "external_id".into(),
            serde_json::Value::String(item.id.clone()),
        );
        fields.insert(
            "source".into(),
            serde_json::Value::String(item.source.value().to_string()),
        );
        fields.insert(
            "kind".into(),
            serde_json::Value::String(item.kind.value().to_string()),
        );
        fields.insert(
            "description".into(),
            serde_json::Value::String(item.description.clone()),
        );
        fields.insert(
            "acceptance_criteria".into(),
            serde_json::to_value(&item.acceptance_criteria).unwrap_or_default(),
        );
        fields.insert(
            "assignee".into(),
            item.assignee
                .clone()
                .map(serde_json::Value::String)
                .unwrap_or(serde_json::Value::Null),
        );
        fields.insert(
            "external_url".into(),
            item.external_url
                .clone()
                .map(serde_json::Value::String)
                .unwrap_or(serde_json::Value::Null),
        );
        fields.insert(
            "synced_at".into(),
            item.sync_timestamp
                .as_deref()
                .map(python_str_datetime)
                .map(serde_json::Value::String)
                .unwrap_or(serde_json::Value::Null),
        );

        let mut req = NoteRequest::from_json("hu", fields)?;

        // VaultLike mínimo: sólo path (index_file no-op) ⇒ scope local.
        let outcome = build_note(&mut req, &self.vault_path, "local", None, None, now)?;

        // Semántica de _write_note: duplicado con mismo fingerprint = no-op;
        // distinto = DuplicateDocumentError.
        if outcome.path.exists() {
            let existing = std::fs::read_to_string(&outcome.path)
                .map_err(|e| format!("{}: {e}", outcome.path.display()))?;
            let fp_nuevo = fingerprint_leniente(&outcome.content).unwrap_or_default();
            let fp_viejo = fingerprint_leniente(&existing).unwrap_or_default();
            if !fp_nuevo.is_empty() && fp_nuevo == fp_viejo {
                return Ok(outcome.path);
            }
            return Err(format!(
                "Document already exists with different content: {}. Pass overwrite=True to replace, or choose a different title.",
                outcome.path.display()
            ));
        }
        if let Some(parent) = outcome.path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        std::fs::write(&outcome.path, &outcome.content).map_err(|e| e.to_string())?;
        Ok(outcome.path)
    }

    /// `_store_episodic`: resumen multilínea + tags/files/context_metadata.
    fn episodic_request(
        item: &TrackedItem,
        rel_path: &str,
        context_metadata: &BTreeMap<String, serde_json::Value>,
    ) -> EpisodicMemoryRequest {
        let mut summary = vec![
            format!("Tracked item: {}", item.id),
            format!("Title: {}", item.title),
        ];
        if !item.description.is_empty() {
            let truncated: String = item.description.chars().take(300).collect();
            summary.push(format!("Description: {truncated}"));
        }
        if !item.acceptance_criteria.is_empty() {
            let first: Vec<&str> = item
                .acceptance_criteria
                .iter()
                .take(5)
                .map(String::as_str)
                .collect();
            summary.push(format!("Acceptance: {}", first.join("; ")));
        }
        EpisodicMemoryRequest {
            content: summary.join("\n"),
            memory_type: "hu".into(),
            tags: vec![
                "hu".into(),
                item.source.value().into(),
                item.kind.value().into(),
            ],
            files: vec![rel_path.to_string()],
            extra_metadata: context_metadata.clone(),
        }
    }
}

/// Extrae `fingerprint:` del frontmatter (parse_frontmatter_lenient mínimo).
fn fingerprint_leniente(md: &str) -> Option<String> {
    let rest = md.strip_prefix("---")?;
    let fin = rest.find("\n---")?;
    for line in rest[..fin].lines() {
        if let Some(v) = line.strip_prefix("fingerprint:") {
            return Some(v.trim().trim_matches('"').trim_matches('\'').to_string());
        }
    }
    None
}

/// `str(datetime)` de Python para un timestamp ISO del provider: los naive
/// se asumen UTC (el servicio hace `.replace(tzinfo=UTC)`), el formato usa
/// separador espacio y offset +00:00; los no parseables pasan crudos.
fn python_str_datetime(iso: &str) -> String {
    let parsed = DateTime::parse_from_rfc3339(iso)
        .or_else(|_| DateTime::parse_from_rfc3339(&iso.replacen(' ', "T", 1)));
    match parsed {
        Ok(dt) => {
            let utc = dt.with_timezone(&Utc);
            if utc.timestamp_subsec_nanos() == 0 {
                utc.format("%Y-%m-%d %H:%M:%S+00:00").to_string()
            } else {
                utc.format("%Y-%m-%d %H:%M:%S%.6f+00:00").to_string()
            }
        }
        Err(_) => iso.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FakeProvider {
        configurado: bool,
    }

    impl WorkItemProvider for FakeProvider {
        fn source_name(&self) -> &str {
            "fake"
        }
        fn is_configured(&self) -> bool {
            self.configurado
        }
        fn get_item(&self, external_id: &str) -> Result<TrackedItem, String> {
            let mut it = TrackedItem::new(
                external_id,
                WorkItemSource::Jira,
                format!("HU {external_id}"),
            );
            it.kind = WorkItemKind::Story;
            Ok(it)
        }
    }

    /// Sink que captura el request (espejo de _FakeEpisodic/_FakeSemantic).
    #[derive(Default)]
    struct CaptorSink {
        requests: Vec<EpisodicMemoryRequest>,
    }

    impl EpisodicSink for CaptorSink {
        fn add_memory(&mut self, req: EpisodicMemoryRequest) -> Result<MemoryEntry, String> {
            let entry = MemoryEntry {
                id: "mem_test0000".into(),
                content: req.content.clone(),
                memory_type: req.memory_type.clone(),
                tags: req.tags.clone(),
                files: req.files.clone(),
                timestamp: "2026-08-24T00:00:00+00:00".into(),
                metadata: BTreeMap::new(),
            };
            self.requests.push(req);
            Ok(entry)
        }
    }

    struct NoopIndexer {
        llamadas: Vec<String>,
    }

    impl SemanticIndexer for NoopIndexer {
        fn index_file(&mut self, rel_path: &str) -> bool {
            self.llamadas.push(rel_path.to_string());
            false
        }
    }

    fn providers(configurado: bool) -> HashMap<String, Box<dyn WorkItemProvider>> {
        HashMap::from([(
            "fake".to_string(),
            Box::new(FakeProvider { configurado }) as Box<_>,
        )])
    }

    fn fixed_now() -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
    }

    use chrono::TimeZone;

    #[test]
    fn import_escribe_y_get_encuentra_canonical() {
        let tmp = std::env::temp_dir().join(format!("wi_a_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        let mut indexer = NoopIndexer { llamadas: vec![] };
        let mut svc = WorkItemService::new(&vault, providers(true), Some(&mut indexer), None);

        let path = svc
            .import_item("COR-123", "fake", false, fixed_now())
            .unwrap();
        assert_eq!(path.file_name().unwrap(), "HU-COR-123.md");
        assert_eq!(path.parent().unwrap().file_name().unwrap(), "hu");

        let encontrado = svc.get_item_note("COR-123").unwrap();
        assert_eq!(encontrado, path);
        assert!(encontrado.starts_with(&vault));

        // La nota tiene frontmatter canónico con external_id/source/kind.
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("external_id: COR-123"), "{content}");
        assert!(content.contains("source: jira"));
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn import_indexa_semantico_y_guarda_episodico() {
        let tmp = std::env::temp_dir().join(format!("wi_b_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        let mut indexer = NoopIndexer { llamadas: vec![] };
        let mut sink = CaptorSink::default();
        {
            let mut svc =
                WorkItemService::new(&vault, providers(true), Some(&mut indexer), Some(&mut sink));
            let mut item_provider_items = providers(true);
            item_provider_items.clear();
            let _ = item_provider_items;
            svc.import_item("COR-9", "fake", true, fixed_now()).unwrap();
        }
        assert_eq!(indexer.llamadas, vec!["hu/HU-COR-9.md"]);
        assert_eq!(sink.requests.len(), 1);
        let r = &sink.requests[0];
        assert_eq!(r.memory_type, "hu");
        assert_eq!(r.tags, vec!["hu", "jira", "story"]);
        assert_eq!(r.files, vec!["hu/HU-COR-9.md"]);
        assert!(r
            .content
            .starts_with("Tracked item: COR-9\nTitle: HU COR-9"));
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn legacy_slug_sigue_resolviendo() {
        let tmp = std::env::temp_dir().join(format!("wi_c_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        let hu = vault.join("hu");
        std::fs::create_dir_all(&hu).unwrap();
        let legacy = hu.join("cor-999.md");
        std::fs::write(&legacy, "---\ntitle: x\n---\n").unwrap();

        let svc = WorkItemService::new(&vault, providers(true), None, None);
        assert_eq!(svc.get_item_note("COR-999").unwrap(), legacy);
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn no_existente_lanza_file_not_found() {
        let tmp = std::env::temp_dir().join(format!("wi_d_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        std::fs::create_dir_all(&vault).unwrap();
        let svc = WorkItemService::new(&vault, providers(true), None, None);
        let err = svc.get_item_note("NOPE-1").unwrap_err();
        assert_eq!(err, "Tracked item not found in vault: NOPE-1");
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn provider_desconocido_y_no_configurado() {
        let tmp = std::env::temp_dir().join(format!("wi_e_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        let mut svc = WorkItemService::new(&vault, providers(false), None, None);
        assert_eq!(
            svc.import_item("X-1", "nope", false, fixed_now())
                .unwrap_err(),
            "Unknown work item provider: nope"
        );
        assert_eq!(
            svc.import_item("X-1", "fake", false, fixed_now())
                .unwrap_err(),
            "Provider 'fake' is not configured."
        );
        assert!(!svc.has_provider("fake"));
        drop(svc);
        let svc2 = WorkItemService::new(&vault, providers(true), None, None);
        // Python NO normaliza en has_provider (golden S05: FAKE_normaliza=False).
        assert!(!svc2.has_provider("FAKE"));
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn list_item_notes_ordenado_y_duplicados() {
        let tmp = std::env::temp_dir().join(format!("wi_f_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let vault = tmp.join("vault");
        let mut indexer = NoopIndexer { llamadas: vec![] };
        {
            let mut svc = WorkItemService::new(&vault, providers(true), Some(&mut indexer), None);
            svc.import_item("B-2", "fake", false, fixed_now()).unwrap();
            svc.import_item("A-1", "fake", false, fixed_now()).unwrap();
            let notas = svc.list_item_notes();
            assert_eq!(notas.len(), 2);
            assert!(notas[0].ends_with("HU-A-1.md"));
            assert!(notas[1].ends_with("HU-B-2.md"));

            // Re-import del MISMO item: fingerprint igual ⇒ no-op success.
            let again = svc.import_item("A-1", "fake", false, fixed_now()).unwrap();
            assert_eq!(again.file_name().unwrap(), "HU-A-1.md");
        }
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn slug_edge_cases() {
        assert_eq!(slug("COR-999"), "cor-999");
        assert_eq!(slug("  X Y/Z "), "x-y-z");
        assert_eq!(slug("---"), "item");
    }
}
