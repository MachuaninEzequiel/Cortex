//! cortex-brain — asistente local nativo de Cortex (Obra 06, BRAIN-2/3).
//!
//! Estado (2026-08-24c): T-BRAIN PULIDO COMPLETO — router determinista 1:1
//! (`cortex/brain/router.py`), tools READ/SAFE_ACTION delegando en el CLI
//! `cortex`, protocolo TOOL con confirmación testeable desde la librería
//! (`chat::procesar_respuesta_modelo`) + `ScriptedBackend` como backend falso
//! scriptado para CI sin GGUF, i18n ES/EN del chrome (`i18n.rs`, convención
//! `ui.language`), samplers temp/seed y ventana multiplataforma (BRAIN-3).
//! Backend real: llama.cpp/GGUF LFM2.5 tras `--features llama` (--model).

pub mod chat;
pub mod download;
#[cfg(feature = "llama")]
pub mod llama;
pub mod paths;

pub mod i18n;
pub mod router;
pub mod tools;
pub mod window;
