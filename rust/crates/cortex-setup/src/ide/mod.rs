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
pub mod prompts;

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
