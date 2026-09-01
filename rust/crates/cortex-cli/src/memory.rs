//! Glue nativo de memoria para los subcomandos CLI (Cierre T2) — espejo de
//! `cortex/cli/common.py::_load_memory` + `AgentMemory.retrieve`.
//!
//! Construye sobre crates ya gateados: WorkspaceLayout (P12B-1),
//! SemanticIndex (P2), NativeEpisodicStore (P3), kernel híbrido RRF+intent
//! (P7) y OnnxEmbedder (cache chroma, misma ruta que domain_detector P12A-7).

use std::path::{Path, PathBuf};

use cortex_app::context::hybrid::UnifiedHit;
use cortex_app::context::intent;
use cortex_app::episodic::{MemoryEntry, NativeEpisodicStore};
use cortex_app::semantic::{SemDoc, SemanticIndex};
use cortex_embed::onnx::OnnxEmbedder;
use cortex_workspace::WorkspaceLayout;

/// Error de apertura espejando el mensaje de `_load_memory`.
#[derive(Debug)]
pub enum MemoryOpenError {
    /// config.yaml inexistente ⇒ stderr + exit(1) en el caller.
    NoConfig {
        start: PathBuf,
        config_path: PathBuf,
    },
    Io(String),
}

impl MemoryOpenError {
    /// Mensaje exacto de common.py.
    pub fn message(&self) -> String {
        match self {
            MemoryOpenError::NoConfig { start, config_path } => format!(
                "❌ Cortex no está configurado en {}.\n   No encuentro \
                 `{}`.\n   Ejecutá `cortex setup full \
                 --non-interactive` para inicializar el workspace,\n   o pasá \
                 `--project-root <ruta>` apuntando a un repo ya configurado.",
                start.display(),
                config_path.display()
            ),
            MemoryOpenError::Io(m) => m.clone(),
        }
    }
}

fn read_config_yaml(config_path: &Path) -> serde_yaml::Value {
    serde_yaml::from_str(&std::fs::read_to_string(config_path).unwrap_or_default())
        .unwrap_or(serde_yaml::Value::Null)
}

fn yaml_str(v: Option<&serde_yaml::Value>, default: &str) -> String {
    match v.and_then(|x| x.as_str()) {
        Some(s) => s.to_string(),
        None => default.to_string(),
    }
}

/// Store episódico cargado del export JSONL (o vacío).
pub enum EpisodicLoad {
    Loaded(NativeEpisodicStore),
    Empty,
}

impl EpisodicLoad {
    fn load(layout: &WorkspaceLayout, cfg: &serde_yaml::Value) -> Self {
        let get = |key: &str, default: &str| -> String {
            cfg.get("episodic")
                .and_then(|m| m.get(key))
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_else(|| default.to_string())
        };
        let persist_s = get("persist_dir", "memory");
        let mode_s = get("namespace_mode", "project");
        let value_s = get("namespace_value", "");
        let ns = cortex_workspace::EpisodicNamespaceCfg::new(&persist_s, &mode_s, &value_s);
        let persist = cortex_workspace::resolve_episodic_persist_dir(&layout.workspace_root, &ns);
        for candidate in [
            persist.join("episodic_export.jsonl"),
            persist.join("memories.jsonl"),
        ] {
            if let Ok(store) = NativeEpisodicStore::load(&candidate) {
                return Self::Loaded(store);
            }
        }
        Self::Empty
    }

    pub fn store_mut(&mut self) -> Option<&mut NativeEpisodicStore> {
        self.store()
    }

    pub fn store(&mut self) -> Option<&mut NativeEpisodicStore> {
        match self {
            EpisodicLoad::Loaded(s) => Some(s),
            EpisodicLoad::Empty => None,
        }
    }

    pub fn count(&self) -> usize {
        match self {
            EpisodicLoad::Loaded(s) => s.count(),
            EpisodicLoad::Empty => 0,
        }
    }
}

impl NativeMemory {
    pub fn episodic_count(&self) -> usize {
        self.episodic.count()
    }

    pub fn vault_path_string(&self) -> String {
        self.vault_path.to_string_lossy().replace('\\', "/")
    }

    pub fn persist_dir_string(&self) -> String {
        self.persist_dir.to_string_lossy().replace('\\', "/")
    }

    /// `describe_enterprise_topology(config, repo_root)` — None cuando no
    /// hay org.yaml (mensaje canónico).
    pub fn enterprise_topology(&self) -> String {
        match cortex_enterprise::config::load_enterprise_config(
            &self.layout.repo_root,
            false,
            None,
            Some(&self.layout),
        ) {
            Ok(Some(cfg)) => cortex_enterprise::config::describe_enterprise_topology(
                Some(&cfg),
                Some(self.layout.repo_root.as_path()),
                Some(&self.layout),
            ),
            _ => "project-only (no .cortex/org.yaml)".to_string(),
        }
    }
}

/// Memoria nativa mínima para presentaciones CLI.
pub struct NativeMemory {
    pub layout: WorkspaceLayout,
    pub semantic: SemanticIndex,
    pub episodic: EpisodicLoad,
    pub embedder: Option<OnnxEmbedder>,
    /// Vault resuelto (`_vault_path_resolved` de AgentMemory).
    pub vault_path: PathBuf,
    /// Dir runtime del store episódico (`str(self.episodic.persist_dir)`).
    pub persist_dir: PathBuf,
}

/// Espejo completo de `RetrievalResult` (lo que consumen el texto y --json).
pub struct RetrievalResultMirror<'a> {
    pub query: String,
    /// (entry, score) con score = max(0, 1 - cosine_dist) ya aplicado.
    pub episodic_hits: Vec<(&'a MemoryEntry, f64)>,
    pub semantic_hits: Vec<(&'a SemDoc, f64)>,
    pub unified_hits: Vec<UnifiedHit<'a>>,
}

impl NativeMemory {
    /// Espejo de `_load_memory(project_root)` (common.py).
    pub fn open(project_root: Option<&Path>) -> Result<Self, MemoryOpenError> {
        Self::open_with_embeddings(project_root, true)
    }

    /// Variante sin embeddings para comandos que no hacen retrieve (`stats`,
    /// `forget`): NO abre el modelo ONNX ni adjunta vectores (B7 — evita
    /// ~90 MB de RSS y ~150 ms de carga del ort Session). SIEMPRE deja
    /// `embedder` en `None`; usar únicamente en comandos que no llaman a
    /// `retrieve` (si alguno lo hiciera, caería al path keyword-only).
    pub fn open_without_embeddings(project_root: Option<&Path>) -> Result<Self, MemoryOpenError> {
        Self::open_with_embeddings(project_root, false)
    }

    fn open_with_embeddings(
        project_root: Option<&Path>,
        want_embeddings: bool,
    ) -> Result<Self, MemoryOpenError> {
        let root_str: Option<String> = project_root.map(|p| p.to_string_lossy().into_owned());
        let start = crate::paths::resolve_project_root(root_str.as_deref());
        let layout = WorkspaceLayout::discover(&start);
        let config_path = layout.config_path();
        if !config_path.exists() {
            return Err(MemoryOpenError::NoConfig { start, config_path });
        }
        let cfg = read_config_yaml(&config_path);
        let configured_vault = yaml_str(
            cfg.get("semantic").and_then(|m| m.get("vault_path")),
            "vault",
        );
        let vault = layout.resolve_workspace_relative(Path::new(&configured_vault));
        let semantic = SemanticIndex::build(&vault)
            .map_err(|e| MemoryOpenError::Io(format!("semantic index: {e}")))?;
        let episodic = EpisodicLoad::load(&layout, &cfg);
        // B7 (desacople): el modelo ONNX se abre SOLO cuando el modo lo pide
        // y no se puede satisfacer desde el VectorStore persistido (C11).
        let mut semantic = semantic;
        let mut attached_from_store = false;
        if want_embeddings {
            let model_name = "all-MiniLM-L6-v2";
            let v_dir = if layout
                .workspace_root
                .join("vectors")
                .join("vectors.v3.bin")
                .exists()
            {
                layout.workspace_root.join("vectors")
            } else {
                layout.repo_root.join(".cortex").join("vectors")
            };
            if v_dir.join("vectors.v3.bin").exists() {
                if let Ok(store) = cortex_core::store::VectorStore::open(&v_dir, model_name) {
                    if let Ok(true) = semantic.attach_embeddings_from_store(&store, model_name) {
                        attached_from_store = true;
                    }
                }
            }
        }

        let mut embedder = if want_embeddings && !attached_from_store {
            crate::memory_cmds::default_model_dir().and_then(|dir| OnnxEmbedder::open(&dir).ok())
        } else {
            None
        };
        // Chunks+embeddings del vault con el MISMO modelo que el oráculo
        // (imprescindible para que los scores semánticos bit-matcheen).
        if want_embeddings && !attached_from_store {
            if let Some(emb) = embedder.as_mut() {
                let _ = semantic.attach_embeddings_with(emb);
            }
        }
        // Espejo de `self._runtime_episodic_dir` / `_vault_path_resolved`.
        let get = |key: &str, default: &'static str| -> String {
            cfg.get("episodic")
                .and_then(|m| m.get(key))
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_else(|| default.to_string())
        };
        let ps = get("persist_dir", "memory");
        let md = get("namespace_mode", "project");
        let nv = get("namespace_value", "");
        let ns = cortex_workspace::EpisodicNamespaceCfg::new(&ps, &md, &nv);
        let runtime_episodic =
            cortex_workspace::resolve_episodic_persist_dir(&layout.workspace_root, &ns);
        Ok(Self {
            layout,
            semantic,
            episodic,
            embedder,
            vault_path: vault,
            persist_dir: runtime_episodic,
        })
    }

    /// Espejo de `HybridSearch.search` + `AgentMemory.retrieve` (scope local,
    /// sin branch-namespacing activo en fixtures del gate).
    pub fn retrieve<'a>(
        &'a mut self,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> RetrievalResultMirror<'a> {
        if !use_embeddings || self.embedder.is_none() {
            // Keyword-only: episódico $contains score 1.0; semántico BM25.
            let ep: Vec<(&MemoryEntry, f64)> = match self.episodic.store() {
                Some(store) => store
                    .keyword_search(query, top_k * 3)
                    .into_iter()
                    .map(|e| (e, 1.0))
                    .collect(),
                None => vec![],
            };
            let sem: Vec<(&SemDoc, f64)> = self.semantic.bm25_search(query, top_k * 3);
            let unified = rrf_fuse(&ep, &sem, top_k, 1.0, 1.0);
            return RetrievalResultMirror {
                query: query.into(),
                episodic_hits: ep.into_iter().take(top_k).collect(),
                semantic_hits: sem.into_iter().take(top_k).collect(),
                unified_hits: unified,
            };
        }

        // Pesos adaptativos por intent (mismo detector que P7).
        let ir = intent::detect(query);
        let ep_w = ir.episodic_weight;
        let sem_w = ir.semantic_weight;

        let qvec = {
            let embedder = self.embedder.as_mut().expect("embedder checked");
            embedder
                .embed_batch(&[query.to_string()])
                .expect("embed query")
        };
        let Some(qv) = qvec.first() else {
            return RetrievalResultMirror {
                query: query.into(),
                episodic_hits: vec![],
                semantic_hits: vec![],
                unified_hits: vec![],
            };
        };

        let fetch_k = top_k * 3;
        let (ep, sem) = match self.episodic.store() {
            Some(store) => (
                store.vector_search(qv, fetch_k),
                self.semantic.semantic_search_vec(qv, fetch_k),
            ),
            None => (Vec::new(), self.semantic.semantic_search_vec(qv, fetch_k)),
        };

        let unified = rrf_fuse(&ep, &sem, top_k, ep_w, sem_w);
        RetrievalResultMirror {
            query: query.into(),
            episodic_hits: ep.into_iter().take(top_k).collect(),
            semantic_hits: sem.into_iter().take(top_k).collect(),
            unified_hits: unified,
        }
    }
}

/// `_rrf_fuse` de hybrid_search.py: claves "episodic:{id}" / "semantic:{path}",
/// suma por rank desde 1, sort estable descendente por score fusionado.
pub fn rrf_fuse<'a>(
    ep: &[(&'a MemoryEntry, f64)],
    sem: &[(&'a SemDoc, f64)],
    top_k: usize,
    ep_w: f64,
    sem_w: f64,
) -> Vec<UnifiedHit<'a>> {
    const RRF_K: f64 = 60.0;

    let mut keys: Vec<String> = Vec::new();
    let mut scores: Vec<f64> = Vec::new();
    let find_or_insert = |keys: &mut Vec<String>, key: String| -> usize {
        match keys.iter().position(|k| *k == key) {
            Some(i) => i,
            None => {
                keys.push(key);
                keys.len() - 1
            }
        }
    };

    for (rank, (e, _)) in ep.iter().enumerate() {
        let key = format!("episodic:{}", e.id);
        let i = find_or_insert(&mut keys, key);
        while scores.len() <= i {
            scores.push(0.0);
        }
        scores[i] += ep_w * (1.0 / (RRF_K + rank as f64 + 1.0));
    }
    for (rank, (d, _)) in sem.iter().enumerate() {
        let key = format!("semantic:{}", d.path);
        let i = find_or_insert(&mut keys, key);
        while scores.len() <= i {
            scores.push(0.0);
        }
        scores[i] += sem_w * (1.0 / (RRF_K + rank as f64 + 1.0));
    }

    let mut order: Vec<usize> = (0..keys.len()).collect();
    order.sort_by(|&a, &b| scores[b].total_cmp(&scores[a]));
    order.truncate(top_k);

    order
        .into_iter()
        .map(|i| {
            let key = &keys[i];
            if let Some(rest) = key.strip_prefix("episodic:") {
                UnifiedHit {
                    source: "episodic",
                    score: scores[i],
                    doc_score_raw: 0.0,
                    dropped: false,
                    entry: ep
                        .iter()
                        .find(|(e, _)| e.id == rest)
                        .map(|(e, _)| (*e).clone()),
                    doc: None,
                    matched_chunk_id: None,
                    matched_section_title: None,
                }
            } else {
                let path = key.strip_prefix("semantic:").unwrap_or(key);
                let found = sem.iter().find(|(d, _)| d.path == path);
                UnifiedHit {
                    source: "semantic",
                    score: scores[i],
                    // Espejo del quirk del oráculo: el item semántico lleva
                    // como score el RAW del doc (hit.doc.score).
                    doc_score_raw: found.map(|(_, s)| *s).unwrap_or(0.0),
                    dropped: false,
                    entry: None,
                    doc: found.map(|(d, _)| *d),
                    matched_chunk_id: None,
                    matched_section_title: None,
                }
            }
        })
        .collect()
}
