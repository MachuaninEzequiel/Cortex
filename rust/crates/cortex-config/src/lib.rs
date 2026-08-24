//! Porteo de la configuración de Cortex (`cortex/core.py`) a serde.
//!
//! Obra 07 fase P1. Contrato: **paridad-como-contrato** — para un mismo YAML,
//! el dump canónico de este crate debe ser byte-a-byte idéntico al del oráculo
//! Python (`bench/parity/config_dump.py`). Los goldens viven en
//! `bench/parity/golden_config/` y los fixtures en `bench/parity/fixtures_config/`.
//!
//! Detalles de paridad que NO se pueden romper sin revertir:
//! - Orden de campos JSON = orden de declaración de los structs (= Python).
//! - `per_language` se serializa SORTED por clave (canónico; acá BTreeMap).
//! - Texto del warning de migración legacy exacto (lo comparan los goldens).
//! - Validaciones: literales estrictos (backend/provider/modo), top_k ∈ [1,100],
//!   pesos > 0. Cualquier falla ⇒ `{"ok": false}` (sin detalle, decidido en P1).
//! - Claves desconocidas se IGNORAN (pydantic default).

#![forbid(unsafe_code)]

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

// ── Enums con literales estrictos ────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EmbeddingBackend {
    Onnx,
    Local,
    Openai,
    Fastembed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum NamespaceMode {
    #[default]
    Project,
    Branch,
    Custom,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum LanguageDetection {
    #[default]
    Off,
    Heuristic,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum LlmProvider {
    #[default]
    None,
    Openai,
    Anthropic,
    Ollama,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum DocumenterMode {
    #[default]
    Auto,
    Interactive,
}

// ── Bloques (orden de campos = orden de declaración Python) ─────────────────

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct EpisodicConfig {
    pub persist_dir: String,                 // "memory"
    pub collection_name: String,             // "cortex_episodic"
    pub embedding_model: String,             // "all-MiniLM-L6-v2"
    pub embedding_backend: EmbeddingBackend, // onnx
    pub namespace_mode: NamespaceMode,       // project
    pub namespace_value: String,             // ""
}

impl Default for EpisodicConfig {
    fn default() -> Self {
        Self {
            persist_dir: "memory".into(),
            collection_name: "cortex_episodic".into(),
            embedding_model: "all-MiniLM-L6-v2".into(),
            embedding_backend: EmbeddingBackend::Onnx,
            namespace_mode: NamespaceMode::Project,
            namespace_value: String::new(),
        }
    }
}

/// Defaults legacy tal cual los lee `_migrate_embedding_config`.
impl EpisodicConfig {
    const LEGACY_MODEL_DEFAULT: &'static str = "all-MiniLM-L6-v2";
    const LEGACY_BACKEND_DEFAULT: EmbeddingBackend = EmbeddingBackend::Onnx;
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct SemanticConfig {
    pub vault_path: String, // "vault"
}

impl Default for SemanticConfig {
    fn default() -> Self {
        Self {
            vault_path: "vault".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EmbeddingLanguageConfig {
    pub model: String,
    pub backend: Option<EmbeddingBackend>, // None = hereda backend efectivo
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct EmbeddingConfig {
    pub model: Option<String>,
    pub backend: Option<EmbeddingBackend>,
    pub language_detection: LanguageDetection, // off
    pub per_language: BTreeMap<String, EmbeddingLanguageConfig>,
}

impl EmbeddingConfig {
    /// True cuando el bloque selecciona modelos activamente (no solo detection).
    pub fn is_configured(&self) -> bool {
        self.model.is_some() || self.backend.is_some() || !self.per_language.is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct RetrievalConfig {
    #[serde(deserialize_with = "de_top_k")]
    pub top_k: i64, // 5, rango [1,100]
    #[serde(deserialize_with = "de_positive_f64")]
    pub episodic_weight: f64, // 1.0, > 0
    #[serde(deserialize_with = "de_positive_f64")]
    pub semantic_weight: f64, // 1.0, > 0
}

impl Default for RetrievalConfig {
    fn default() -> Self {
        Self {
            top_k: 5,
            episodic_weight: 1.0,
            semantic_weight: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct LlmConfig {
    pub provider: LlmProvider, // none
    pub model: String,         // ""
}

impl Default for LlmConfig {
    fn default() -> Self {
        Self {
            provider: LlmProvider::None,
            model: String::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct JiraIntegrationConfig {
    pub enabled: bool, // false
    pub base_url: String,
    pub email_env: String, // JIRA_EMAIL
    pub token_env: String, // JIRA_API_TOKEN
}

impl Default for JiraIntegrationConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            base_url: String::new(),
            email_env: "JIRA_EMAIL".into(),
            token_env: "JIRA_API_TOKEN".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct IntegrationsConfig {
    pub jira: JiraIntegrationConfig,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct DocumenterConfig {
    pub default_mode: DocumenterMode, // auto
}

impl Default for DocumenterConfig {
    fn default() -> Self {
        Self {
            default_mode: DocumenterMode::Auto,
        }
    }
}

// ── Raíz ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct CortexConfig {
    pub episodic: EpisodicConfig,
    pub semantic: SemanticConfig,
    pub retrieval: RetrievalConfig,
    pub llm: LlmConfig,
    pub integrations: IntegrationsConfig,
    pub documenter: DocumenterConfig,
    pub embedding: EmbeddingConfig,
}

/// Texto EXACTO del warning de migración (los goldens lo comparan byte-a-byte).
pub const WARNING_MIGRATION_EMBEDDING: &str = "Deprecated embedding config: both 'embedding:' (new) and 'episodic.embedding_model/embedding_backend' (legacy) are set. The new 'embedding:' block wins; move the legacy values into 'embedding: {model: ..., backend: ...}' to silence this warning.";

impl CortexConfig {
    /// Replica `_migrate_embedding_config`: warning cuando legacy Y bloque nuevo
    /// están ambos configurados; gana el bloque nuevo.
    pub fn migration_warnings(&self) -> Vec<String> {
        let mut out = Vec::new();
        if self.embedding.is_configured()
            && (self.episodic.embedding_model != EpisodicConfig::LEGACY_MODEL_DEFAULT
                || self.episodic.embedding_backend != EpisodicConfig::LEGACY_BACKEND_DEFAULT)
        {
            out.push(WARNING_MIGRATION_EMBEDDING.to_string());
        }
        out
    }

    /// La nueva sintaxis del bloque `embedding:` prevalece sobre la antigua.
    pub fn embedding_block_active(&self) -> bool {
        self.embedding.is_configured()
    }

    /// Resolución de `(model, backend)` — puerto 1:1 de `resolve_embedder`.
    pub fn resolve_embedder(&self, lang: Option<&str>) -> (String, String) {
        let emb = &self.embedding;
        if !emb.is_configured() {
            return (
                self.episodic.embedding_model.clone(),
                backend_str(self.episodic.embedding_backend),
            );
        }
        let eff_model = emb
            .model
            .clone()
            .unwrap_or_else(|| self.episodic.embedding_model.clone());
        let eff_backend = emb
            .backend
            .map(backend_str)
            .unwrap_or_else(|| backend_str(self.episodic.embedding_backend));

        if let Some(lang) = lang {
            if let Some(entry) = emb.per_language.get(lang.trim().to_lowercase().as_str()) {
                return (
                    entry.model.clone(),
                    entry
                        .backend
                        .map(backend_str)
                        .unwrap_or_else(|| eff_backend.clone()),
                );
            }
        }
        (eff_model, eff_backend)
    }
}

#[must_use]
pub fn backend_str(b: EmbeddingBackend) -> String {
    match b {
        EmbeddingBackend::Onnx => "onnx".into(),
        EmbeddingBackend::Local => "local".into(),
        EmbeddingBackend::Openai => "openai".into(),
        EmbeddingBackend::Fastembed => "fastembed".into(),
    }
}

// ── Entrada canónica (dump byte-parity con bench/parity/config_dump.py) ────

/// Resultado de parsear un config.yaml.
pub fn load_and_dump(yaml_str: &str) -> String {
    // Espeja el oráculo: YAML nulo/vacío ⇒ mapping vacío.
    let value: serde_yaml::Value =
        serde_yaml::from_str(yaml_str).unwrap_or(serde_yaml::Value::Null);
    let seed = if value.is_null() {
        "{}".to_string()
    } else {
        serde_yaml::to_string(&value).unwrap_or_default()
    };

    match serde_yaml::from_str::<CortexConfig>(&seed) {
        Ok(config) => {
            let warnings = config.migration_warnings();
            let out = DumpOut {
                ok: true,
                warnings: &warnings,
                config: &config,
                embedding_block_active: config.embedding_block_active(),
                resolved_embedder: ResolvedEmbedder {
                    dflt: config.resolve_embedder(None),
                    es: config.resolve_embedder(Some("es")),
                    en: config.resolve_embedder(Some("en")),
                    fr: config.resolve_embedder(Some("fr")),
                },
            };
            render(&out)
        }
        Err(_) => "{\n  \"ok\": false\n}\n".to_string(),
    }
}

#[derive(Serialize)]
struct DumpOut<'a> {
    ok: bool,
    warnings: &'a [String],
    config: &'a CortexConfig,
    embedding_block_active: bool,
    resolved_embedder: ResolvedEmbedder,
}

#[derive(Serialize)]
struct ResolvedEmbedder {
    #[serde(rename = "default")]
    dflt: (String, String),
    es: (String, String),
    en: (String, String),
    fr: (String, String),
}

fn render<T: Serialize>(value: &T) -> String {
    let mut s = serde_json::to_string_pretty(value).expect("serialización infalible");
    s.push('\n');
    s
}

// ── Validaciones de rango (pydantic Field ge/le/gt) ────────────────────────

fn de_top_k<'de, D>(d: D) -> Result<i64, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let v = i64::deserialize(d)?;
    if !(1..=100).contains(&v) {
        return Err(serde::de::Error::custom("top_k debe estar en [1, 100]"));
    }
    Ok(v)
}

fn de_positive_f64<'de, D>(d: D) -> Result<f64, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let v = f64::deserialize(d)?;
    if v <= 0.0 {
        return Err(serde::de::Error::custom("el peso debe ser > 0"));
    }
    Ok(v)
}
