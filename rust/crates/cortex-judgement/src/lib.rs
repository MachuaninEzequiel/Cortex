//! Puerto de juicio TypeSafe/Jev. Opt-in, fail-open.
//!
//! No depende de cortex-app ni de UnifiedHit. Solo JSON + HTTP.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::sync::Arc;

mod auth;
mod catalog;
mod compact;
mod error;
mod null;
mod pack;
mod purpose;
mod utterance;
mod request;
mod routing;
mod squeeze;
mod typesafe;

pub use auth::{delete_api_key, key_configured, resolve_api_key, store_api_key};
pub use catalog::Catalog;
pub use compact::{
    evaluate_session_compact, CompactCandidate, CompactDecision, DEFAULT_PIN_LAST_N, KEEP_CALL,
    KEEP_RESULT, TRUNCATED_RESULT_MARKER,
};
pub use error::JudgementError;
pub use null::NullClient;
pub use pack::{
    pack_context, pack_context_with_edges, pack_fetch_k, ContextPack, PackEdge, PackPointer,
    KEEP_BODY, KEEP_PTR, MAX_CANONICAL, MAX_POINTERS, MAX_RELATED_POINTERS, VALID_PACK_RELATIONS,
};
pub use routing::{
    evaluate_adr_score, evaluate_model_routing, rebuild_specialist_menu, ModelRoutingDecision,
    ScoreDecision, SpecialistOption, SubagentRole, CONFIDENCE_THRESHOLD,
};
pub use utterance::{allow_remember, classify_utterance, UtteranceJudgement, WorkKind};
pub use purpose::Purpose;
pub use request::{JudgementRequest, JudgementResponse, Usage};
pub use squeeze::{rank_promotion, squeeze_fetch_k, squeeze_search, Candidate, ScoredCandidate};
pub use typesafe::{TypesafeClient, DEFAULT_BASE_URL, DEFAULT_MODEL};

// ── Aliases canónicos para la arquitectura SystemOne ──────────────────────────
pub type SystemOneClient = dyn JudgementClient;
pub type SystemOneHandle = JudgementHandle;
pub type SystemOneError = JudgementError;
pub type SystemOneStatus = JudgementStatus;
pub type SystemOneRequest = JudgementRequest;
pub type SystemOneResponse = JudgementResponse;

/// Cliente inyectable. `None` en el caller ≡ community (código actual).
pub trait JudgementClient: Send + Sync {
    fn enabled(&self, purpose: Purpose) -> bool;
    fn evaluate(&self, request: &JudgementRequest) -> Result<JudgementResponse, JudgementError>;
}

/// Opciones para construir el client. Las traduce el adapter desde CortexConfig.
#[derive(Debug, Clone)]
pub struct ClientOptions {
    pub enabled: bool,
    pub provider: String,
    pub model: String,
    pub timeout_ms: u64,
    pub api_key_env: String,
    pub search_squeeze: bool,
    pub promotion: bool,
    pub context_pack: bool,
    pub utterance: bool,
    pub session_compact: bool,
    pub model_routing: bool,
    pub base_url: Option<String>,
    pub questions_override: Option<PathBuf>,
}

impl Default for ClientOptions {
    fn default() -> Self {
        Self {
            enabled: false,
            provider: "none".into(),
            model: DEFAULT_MODEL.into(),
            timeout_ms: 2000,
            api_key_env: "TYPESAFE_API_KEY".into(),
            search_squeeze: false,
            promotion: false,
            context_pack: false,
            utterance: false,
            session_compact: false,
            model_routing: false,
            base_url: None,
            questions_override: None,
        }
    }
}

pub struct JudgementHandle {
    pub client: Arc<dyn JudgementClient>,
    pub catalog: Catalog,
}

impl Clone for JudgementHandle {
    fn clone(&self) -> Self {
        Self {
            client: Arc::clone(&self.client),
            catalog: self.catalog.clone(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JudgementStatus {
    Disabled,
    Typesafe,
    Degraded,
}

impl JudgementStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            JudgementStatus::Disabled => "disabled",
            JudgementStatus::Typesafe => "typesafe",
            JudgementStatus::Degraded => "degraded",
        }
    }
}

pub fn status(opts: &ClientOptions) -> JudgementStatus {
    if !opts.enabled || opts.provider != "typesafe" {
        return JudgementStatus::Disabled;
    }
    if resolve_api_key(&opts.api_key_env).is_some() {
        JudgementStatus::Typesafe
    } else {
        JudgementStatus::Degraded
    }
}

/// `None` si community / ningún purpose / sin key / catálogo corrupto.
pub fn build_handle(opts: &ClientOptions) -> Option<JudgementHandle> {
    if !opts.enabled || opts.provider != "typesafe" {
        return None;
    }
    if !opts.search_squeeze
        && !opts.promotion
        && !opts.context_pack
        && !opts.utterance
        && !opts.session_compact
        && !opts.model_routing
    {
        return None;
    }
    let key = resolve_api_key(&opts.api_key_env)?;
    let catalog = Catalog::load(opts.questions_override.as_deref()).ok()?;
    let base = opts.base_url.as_deref().unwrap_or(DEFAULT_BASE_URL);
    let client = TypesafeClient::new(
        base,
        key,
        opts.model.clone(),
        opts.timeout_ms,
        opts.search_squeeze,
        opts.promotion,
        opts.context_pack,
        opts.utterance,
        opts.session_compact,
        opts.model_routing,
    );
    Some(JudgementHandle {
        client: Arc::new(client),
        catalog,
    })
}
