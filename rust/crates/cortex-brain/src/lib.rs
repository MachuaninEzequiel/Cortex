//! cortex-brain — asistente local nativo de Cortex (Obra 06, BRAIN-2/3).
//!
//! Estado (2026-08-24b): núcleo determinista completo — router 1:1 con
//! `cortex/brain/router.py`, tools READ/SAFE_ACTION delegando en el CLI
//! `cortex` (los servicios session/actions siguen Python hasta Obra E),
//! loop de chat + slash commands + banner ≤80. Backend LLM vía trait
//! `LlmBackend`: hoy `DeterministicBackend` (--no-model); llama.cpp/GGUF
//! LFM2.5 queda scoped como siguiente incremento (HANDOFF §ESTADO-GATES).

pub mod chat;

#[cfg(feature = "llama")]
pub mod llama;

pub mod router;
pub mod tools;
pub mod window;
