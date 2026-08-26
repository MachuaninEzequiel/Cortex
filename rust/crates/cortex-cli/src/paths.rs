//! Resolución de rutas con semántica Python (`expanduser().resolve()`).
//!
//! Lección P12B-3: `Path::file_name()` devuelve None si el tramo final es
//! ".." ⇒ normalización por `Components` explícitos, canonicalizando el
//! ancestro existente más profundo (mismo algoritmo que
//! cortex-doctor::native y cortex-enterprise::review_knowledge).

use std::path::{Component, Path, PathBuf};

/// Resolve() no estricto de Python sobre un path ya expandido.
pub fn python_resolve(path: &Path) -> PathBuf {
    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    let comps: Vec<Component> = abs.components().collect();
    let mut idx = comps.len();
    while idx > 0 {
        let candidate: PathBuf = comps[..idx].iter().collect();
        if candidate.exists() {
            break;
        }
        idx -= 1;
    }
    let base: PathBuf = comps[..idx].iter().collect();
    let mut out = std::fs::canonicalize(&base).unwrap_or(base);
    for comp in &comps[idx..] {
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

/// `Path.expanduser()`: solo `~` y `~/…` (lo que usa el CLI Python).
pub fn expand_user(path: &Path) -> PathBuf {
    let s = path.to_string_lossy();
    if s == "~" || s.starts_with("~/") {
        if let Some(home) = std::env::var_os("HOME") {
            let home = PathBuf::from(home);
            return if s.len() == 1 {
                home
            } else {
                home.join(&s[2..])
            };
        }
    }
    path.to_path_buf()
}

/// `root = Path(project_root).expanduser().resolve()` o `Path.cwd().resolve()`.
pub fn resolve_project_root(project_root: Option<&str>) -> PathBuf {
    match project_root {
        Some(raw) => python_resolve(&expand_user(Path::new(raw))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}
