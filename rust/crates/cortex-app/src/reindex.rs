//! Reindex nativo del vault semántico (Obra 18 / C1).
//!
//! Orquesta el parseo de documentos del vault, cálculo de embeddings
//! con OnnxEmbedder, backup con rollback y persistencia en `VectorStore`.

use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

pub const CACHE_SCHEMA_VERSION: &str = "2";

/// Fingerprint canónico: sha256(model \x00 schema \x00 embedding_text)
pub fn cache_fingerprint(model_name: &str, embedding_text: &str) -> String {
    let payload = format!(
        "{model_name}\x00{}\x00{embedding_text}",
        CACHE_SCHEMA_VERSION
    );
    let mut h = Sha256::new();
    h.update(payload.as_bytes());
    format!("{:x}", h.finalize())
}

/// Resultado de una re-indexación exitosa del vault.
#[derive(Debug, Clone)]
pub struct ReindexOutcome {
    pub n_chunks: usize,
    pub dim: usize,
    pub vectors_dir: PathBuf,
    pub backup_dir: Option<PathBuf>,
}

#[derive(Debug)]
pub enum ReindexError {
    UnsupportedModel { model: String },
    ModelMissing { hint: String },
    Config(String),
    Semantic(String),
    Embed(String),
    Store(String),
}

impl std::fmt::Display for ReindexError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnsupportedModel { model } => write!(
                f,
                "reindex nativo solo embebe all-MiniLM-L6-v2 (configurado: {model})"
            ),
            Self::ModelMissing { hint } => write!(
                f,
                "modelo ONNX no encontrado en {hint}: instalalo y reintentá"
            ),
            Self::Config(e) => write!(f, "config: {e}"),
            Self::Semantic(e) => write!(f, "semantic index: {e}"),
            Self::Embed(e) => write!(f, "embedder: {e}"),
            Self::Store(e) => write!(f, "vector store: {e}"),
        }
    }
}

impl std::error::Error for ReindexError {}

/// Path único del directorio de vectores bajo .cortex.
pub fn vectors_dir(dot_cortex: &Path) -> PathBuf {
    dot_cortex.join("vectors")
}

/// Resuelve el modelo de embedding desde `config.yaml` usando `CortexConfig::resolve_embedder`.
pub fn resolve_reindex_model(config_path: &Path) -> Result<String, ReindexError> {
    if !config_path.exists() {
        return Err(ReindexError::Config(format!(
            "No Cortex config found at `{}`.",
            config_path.display()
        )));
    }
    let raw_text = std::fs::read_to_string(config_path)
        .map_err(|e| ReindexError::Config(format!("cannot read {}: {e}", config_path.display())))?;
    let config: cortex_config::CortexConfig = serde_yaml::from_str(&raw_text).map_err(|e| {
        ReindexError::Config(format!("Invalid config in {}: {e}", config_path.display()))
    })?;
    let (model, _backend) = config.resolve_embedder(None);
    Ok(model)
}

/// Rebuild real del vector cache con backup y rollback integrado.
pub fn reindex_vault(
    vault: &Path,
    vectors_dir: &Path,
    model: &str,
    model_dir: Option<&Path>,
) -> Result<ReindexOutcome, ReindexError> {
    if model != "all-MiniLM-L6-v2" {
        return Err(ReindexError::UnsupportedModel {
            model: model.to_string(),
        });
    }

    let Some(model_dir) = model_dir else {
        let cache_hint = std::env::var_os("HOME")
            .map(|h| {
                format!(
                    "{}/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx",
                    h.to_string_lossy()
                )
            })
            .unwrap_or_default();
        return Err(ReindexError::ModelMissing { hint: cache_hint });
    };

    // 1. Parse + BM25 + chunks
    let mut semantic = crate::semantic::SemanticIndex::build(vault)
        .map_err(|e| ReindexError::Semantic(e.to_string()))?;

    // 2. Embeddings de todos los chunks
    let mut embedder = cortex_embed::onnx::OnnxEmbedder::open(model_dir)
        .map_err(|e| ReindexError::Embed(e.to_string()))?;

    let n_chunks = semantic
        .attach_embeddings_with(&mut embedder)
        .map_err(|e| ReindexError::Embed(e.to_string()))?;

    if n_chunks == 0 {
        return Ok(ReindexOutcome {
            n_chunks: 0,
            dim: 0,
            vectors_dir: vectors_dir.to_path_buf(),
            backup_dir: None,
        });
    }

    let dim = semantic.chunks[0].embedding.len();
    if dim == 0 {
        return Err(ReindexError::Embed(
            "embeddings vacíos (modelo?)".to_string(),
        ));
    }

    // 3. Backup del cache existente si existe
    let ts = chrono::Utc::now().format("%Y%m%d-%H%M%S");
    let backup_dir = vectors_dir.with_file_name(format!("vectors.backup-{ts}"));
    let had_cache = vectors_dir.exists();
    if had_cache {
        std::fs::rename(vectors_dir, &backup_dir)
            .map_err(|e| ReindexError::Store(format!("backup de {vectors_dir:?} falló: {e}")))?;
    }

    // 4. Persistencia en VectorStore
    let mut store = match cortex_core::store::VectorStore::open(vectors_dir, model) {
        Ok(st) => st,
        Err(e) => {
            if had_cache {
                let _ = std::fs::rename(&backup_dir, vectors_dir);
            }
            return Err(ReindexError::Store(e.to_string()));
        }
    };

    let fps: Vec<String> = semantic
        .chunks
        .iter()
        .map(|c| cache_fingerprint(model, &c.info.embedding_text()))
        .collect();
    let ids: Vec<String> = semantic
        .chunks
        .iter()
        .map(|c| c.info.chunk_id.clone())
        .collect();
    let mut flat: Vec<f32> = Vec::with_capacity(n_chunks * dim);
    for c in &semantic.chunks {
        flat.extend(c.embedding.iter().map(|v| *v as f32));
    }
    if let Err(e) = store.put_many(&fps, &ids, &flat, dim) {
        if had_cache {
            let _ = std::fs::rename(&backup_dir, vectors_dir);
        }
        return Err(ReindexError::Store(e.to_string()));
    }
    let _ = store.compact();

    Ok(ReindexOutcome {
        n_chunks,
        dim,
        vectors_dir: vectors_dir.to_path_buf(),
        backup_dir: if had_cache { Some(backup_dir) } else { None },
    })
}
