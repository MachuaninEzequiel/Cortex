//! Capa IDE — inyección de perfiles de agente y config MCP por IDE.
//!
//! Contrato Rust del porteo de `cortex/ide/` (Obra 07 P8d):
//!
//! - [`IdeCtx`] reemplaza los globals de Python: `project_root`, `home`
//!   (Path.home() redirigible para fixtures) y `now` (reloj congelable).
//! - [`base`] porta los helpers compartidos de `cortex/ide/base.py`.
//! - Cada adapter vive en `adapters/<ide>.rs` e implementa [`IdeAdapter`].
//!
//! Regla de paridad: mismo fixture + mismo ctx ⇒ mismos archivos
//! byte-a-byte (los tests usan goldens capturados con reloj congelado).

pub mod adapters;
pub mod base;
pub mod canonical_tools;
pub mod cli_discovery;
pub mod host_detector;
pub mod prompts;

pub use cli_discovery::{discover_all_cli_models, discover_models_for_host, ProviderModelInfo};
pub use host_detector::{detect_host, HostEnvironment};

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};

/// Contexto de inyección compartido por todos los adapters.
#[derive(Debug, Clone)]
pub struct IdeCtx<'a> {
    pub project_root: &'a Path,
    /// Path.home() de Python (redirigible en fixtures).
    pub home: &'a Path,
    /// Reloj para headers "Last sync" y nombres de backup.
    pub now: DateTime<Utc>,
}

impl<'a> IdeCtx<'a> {
    /// skills_dir según WorkspaceLayout de Python: en AMBOS layouts la ruta
    /// efectiva es ``project_root/.cortex/skills`` (legacy: repo/.cortex/skills;
    /// nuevo: workspace_root==repo/.cortex → workspace_root/skills).
    pub fn skills_dir(&self) -> PathBuf {
        self.project_root.join(".cortex").join("skills")
    }

    pub fn subagents_dir(&self) -> PathBuf {
        self.project_root.join(".cortex").join("subagents")
    }
}

/// Prompts SSoT leídos del workspace (`build_all_prompts`).
pub type Prompts = BTreeMap<String, String>;

/// Contrato de adapter (espejo de `IDEAdapter` ABC).
pub trait IdeAdapter {
    fn name(&self) -> &'static str;
    fn display_name(&self) -> &'static str;

    /// `(nombre_lógico, ruta)` — puede depender de ctx (home/project_root).
    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)>;

    /// Inyecta perfiles; devuelve la lista de archivos escritos (str(ruta)).
    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String>;

    /// Inyecta configuración MCP.
    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String>;

    /// Elimina lo inyectado. Default no-op como en Python.
    fn uninstall(&self, _ctx: &IdeCtx) -> Vec<String> {
        Vec::new()
    }

    /// Escudo WSL (solo opencode lo pide hoy).
    fn needs_wsl_shielding(&self) -> bool {
        false
    }
}

/// Aliases reconocidos para normalizar nombres de IDE.
pub const ALIASES: &[(&str, &str)] = &[
    ("claude", "claude_code"),
    ("claude-code", "claude_code"),
    ("claude-desktop", "claude_desktop"),
    ("code", "vscode"),
    ("visual-studio-code", "vscode"),
    ("vs-code", "vscode"),
    ("openai-codex", "codex"),
    ("codex-cli", "codex"),
    ("gemini", "antigravity"),
    ("gemini-cli", "antigravity"),
    ("gemini_cli", "antigravity"),
    ("agy", "antigravity"),
];

/// Normaliza un nombre o alias de IDE al nombre canónico de su adaptador.
pub fn normalize_ide(raw: &str) -> String {
    let n = raw.trim().to_lowercase();
    ALIASES
        .iter()
        .find(|(a, _)| **a == n)
        .map(|(_, canon)| canon.to_string())
        .unwrap_or(n)
}
