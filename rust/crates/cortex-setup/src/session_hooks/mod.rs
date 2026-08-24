//! Porteo de `cortex/session/hooks/` (Obra 07 P8e).
//!
//! Infraestructura genérica de instalación de hooks de sesión por IDE:
//! cada adapter instala un artefacto IDE-nativo que, al dispararse por un
//! evento del IDE, invoca `cortex session checkpoint --source ide-hook ...`.
//!
//! - [`InstallResult`] / [`UninstallResult`] / [`HookStatus`]: dataclasses
//!   resultado (espejo de installer.py).
//! - [`HookInstaller`]: registry + dispatcher (install/uninstall/status).
//! - [`claude_code`]: entrada `_cortex_managed` en `.claude/settings.json`.
//! - [`cursor`]: bloque marcado en `.git/hooks/post-commit` (+exec bit).
//! - [`opencode`]: bloque marcado en `.opencode/hooks.md`.
//! - [`pi`]: recetas en el `justfile` del proyecto.
//!
//! Regla de paridad: mismo fixture + mismas operaciones ⇒ mismos archivos
//! y mismos mensajes byte-a-byte (los tests usan goldens capturados).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

// ---------------------------------------------------------------------------
// Resultados (espejo de los dataclasses congelados de Python)
// ---------------------------------------------------------------------------

/// Outcome de install.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallResult {
    pub ide: &'static str,
    pub installed: bool,
    pub modified_paths: Vec<PathBuf>,
    pub message: String,
}

/// Outcome de uninstall.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UninstallResult {
    pub ide: &'static str,
    pub uninstalled: bool,
    pub removed_paths: Vec<PathBuf>,
    pub message: String,
}

/// Estado de instalación de un adapter bajo un directorio objetivo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HookStatus {
    pub ide: &'static str,
    pub installed: bool,
    pub detail: String,
}

/// Protocolo que cumple cada adapter (espejo de `HookAdapter`).
///
/// Los adapters nunca fallan ante condiciones benignas: un segundo install
/// detecta la instalación existente y devuelve `installed=true` con mensaje
/// claro. Los fallos duros (no es repo git, JSON inválido) devuelven
/// `Err(String)` — espejo de las excepciones de Python.
pub trait HookAdapter {
    fn name(&self) -> &'static str;

    /// Si el adapter puede correr en esta máquina. Todos los incluidos
    /// gestionan archivos de texto/JSON: True incondicional como en Python.
    fn is_supported(&self) -> bool {
        true
    }

    fn install(&self, target_dir: &Path) -> Result<InstallResult, String>;
    fn uninstall(&self, target_dir: &Path) -> Result<UninstallResult, String>;
    fn status(&self, target_dir: &Path) -> HookStatus;
}

/// Registry + dispatcher (espejo de `HookInstaller`).
pub struct HookInstaller {
    adapters: BTreeMap<&'static str, Box<dyn HookAdapter>>,
}

impl HookInstaller {
    pub fn new(adapters: Vec<Box<dyn HookAdapter>>) -> Self {
        let map = adapters
            .into_iter()
            .map(|a| (a.name(), a))
            .collect::<BTreeMap<_, _>>();
        HookInstaller { adapters: map }
    }

    /// Nombres de todos los adapters conocidos (sorted, como Python).
    pub fn list_available_adapters(&self) -> Vec<&'static str> {
        self.adapters.keys().copied().collect()
    }

    /// Nombres de adapters soportados (sorted).
    pub fn list_supported(&self) -> Vec<&'static str> {
        self.adapters
            .iter()
            .filter(|(_, a)| a.is_supported())
            .map(|(name, _)| *name)
            .collect()
    }

    /// Adapter registrado bajo `ide` o error con los disponibles
    /// (espejo de `HookInstaller.get`, KeyError incluido en el mensaje).
    pub fn get(&self, ide: &str) -> Result<&dyn HookAdapter, String> {
        self.adapters.get(ide).map(|b| b.as_ref()).ok_or_else(|| {
            format!(
                "unknown IDE adapter {ide:?}; available: {}",
                self.list_available_adapters().join(", ")
            )
        })
    }

    pub fn install(&self, ide: &str, target_dir: &Path) -> Result<InstallResult, String> {
        self.get(ide)?.install(target_dir)
    }

    pub fn uninstall(&self, ide: &str, target_dir: &Path) -> Result<UninstallResult, String> {
        self.get(ide)?.uninstall(target_dir)
    }

    pub fn status(&self, ide: &str, target_dir: &Path) -> Result<HookStatus, String> {
        Ok(self.get(ide)?.status(target_dir))
    }

    /// Estado de todos los adapters (orden sorted por nombre).
    pub fn status_all(&self, target_dir: &Path) -> Vec<HookStatus> {
        self.list_available_adapters()
            .iter()
            .map(|name| self.adapters[*name].status(target_dir))
            .collect()
    }
}

/// Installer con los 4 adapters incluidos (orden de registro de Python:
/// claude-code, cursor, opencode, pi; el BTreeMap ordena igual para listados).
pub fn default_installer() -> HookInstaller {
    HookInstaller::new(vec![
        Box::new(claude_code::ClaudeCodeHookAdapter),
        Box::new(cursor::CursorGitHookAdapter),
        Box::new(opencode::OpencodeHookAdapter),
        Box::new(pi::PiHookAdapter),
    ])
}

// Marcadores compartidos (cursor/opencode/pi usan variantes del mismo par;
// claude_code usa clave JSON). Se exponen por módulo como en Python.

// ---------------------------------------------------------------------------
// Helpers de bloque marcado (compartidos por cursor/opencode/pi)
// ---------------------------------------------------------------------------

/// `_strip_block`: elimina líneas entre marcadores EXACTOS preservando el
/// resto byte-a-byte (`splitlines(keepends=True)` de Python →
/// `split_inclusive('\n')`; solo se recorta `\n` para comparar).
pub(crate) fn strip_block(content: &str, start_marker: &str, end_marker: &str) -> String {
    let mut kept = String::new();
    let mut in_block = false;
    for line in content.split_inclusive('\n') {
        let stripped = line.strip_suffix('\n').unwrap_or(line);
        if stripped == start_marker {
            in_block = true;
            continue;
        }
        if stripped == end_marker {
            in_block = false;
            continue;
        }
        if !in_block {
            kept.push_str(line);
        }
    }
    kept
}

/// `_read` de cursor/opencode/pi: contenido o "" si no existe
/// (`errors="replace"` de Python → lossy en Rust; fixtures son UTF-8 limpio).
pub(crate) fn read_or_empty(path: &Path) -> String {
    if !path.exists() {
        return String::new();
    }
    String::from_utf8_lossy(&std::fs::read(path).unwrap_or_default()).into_owned()
}

/// Escritura con `newline="\n"` explícito de Python (Rust ya escribe LF).
pub(crate) fn write_lf(path: &Path, content: &str) -> Result<(), String> {
    std::fs::write(path, content).map_err(|e| format!("write {}: {e}", path.display()))
}

pub mod claude_code;
pub mod cursor;
pub mod opencode;
pub mod pi;
