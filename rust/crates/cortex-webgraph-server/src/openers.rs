//! Porteo de `cortex/webgraph/openers.py`.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};
use std::process::Command;

use cortex_workspace::layout::resolve_lexical;

/// resolve_safe_vault_path: rechaza paths fuera del vault y archivos
/// inexistentes. Errores como Result (Python lanza ValueError/FileNotFoundError).
pub fn resolve_safe_vault_path(vault_root: &Path, relative_path: &str) -> Result<PathBuf, String> {
    let candidate = resolve_lexical(&vault_root.join(relative_path));
    let root = resolve_lexical(vault_root);
    if candidate != root && !candidate.starts_with(&root) {
        return Err(format!(
            "Refusing to open path outside vault: {}",
            candidate.display()
        ));
    }
    if !candidate.exists() {
        return Err(format!("{}", candidate.display()));
    }
    Ok(candidate)
}

/// open_path: xdg-open (Linux) / open (macOS); Windows no soportado acá.
pub fn open_path(path: &Path) {
    let target = path.to_string_lossy().to_string();
    #[cfg(target_os = "macos")]
    let _ = Command::new("open").arg(target).status();
    #[cfg(not(target_os = "macos"))]
    let _ = Command::new("xdg-open").arg(target).status();
}
