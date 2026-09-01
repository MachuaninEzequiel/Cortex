//! Puerto de `cortex/security/paths.py` (P12A-1).
//!
//! Helpers centrales de seguridad de rutas: todo componente que construye
//! rutas de filesystem desde input operacional debe usarlos en vez de
//! concatenación ad-hoc.
//!
//! Semántica replicada 1:1:
//! - `Path.resolve()` de Python NO es estricto (strict=False por defecto):
//!   resuelve symlinks del tramo existente y normaliza el resto, sin fallar
//!   si el destino no existe. El espejo Rust (`resolve_lenient`) canonicaliza
//!   el ancestro existente más profundo y le pega la cola restante.
//! - Mensajes de error idénticos a los de Python (son contrato observable).

use std::ffi::OsString;
use std::path::{Path, PathBuf};

/// Espejo de `PathSecurityError(ValueError)`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathSecurityError(pub String);

impl std::fmt::Display for PathSecurityError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for PathSecurityError {}

/// `Path(p).resolve()` no estricto: canonicaliza el ancestro existente más
/// profundo (symlinks incluidos) y re-attacha los componentes restantes.
/// Las rutas relativas se anclan al cwd, como en Python.
fn resolve_lenient(path: &Path) -> PathBuf {
    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    let mut suffix: Vec<OsString> = Vec::new();
    let mut existing = abs.clone();
    while !existing.exists() {
        match (existing.parent(), existing.file_name()) {
            (Some(parent), Some(name)) if parent != existing => {
                suffix.push(name.to_os_string());
                existing = parent.to_path_buf();
            }
            _ => break,
        }
    }
    let mut out = std::fs::canonicalize(&existing).unwrap_or(existing);
    for part in suffix.iter().rev() {
        out.push(part);
    }
    out
}

/// Puerto de `resolve_safe`: resuelve *rel* bajo *root* y garantiza que el
/// resultado quede dentro de *root*. Rutas absolutas rechazadas.
///
/// Errores (mensaje idéntico al Python):
/// - `"Absolute paths are not allowed: {rel}"`
/// - `"Path escapes allowed root ({root}): {rel}"`
pub fn resolve_safe(root: &Path, rel: &Path) -> Result<PathBuf, PathSecurityError> {
    if rel.is_absolute() {
        return Err(PathSecurityError(format!(
            "Absolute paths are not allowed: {}",
            rel.display()
        )));
    }
    let root_resolved = resolve_lenient(root);
    let target = resolve_lenient(&root_resolved.join(rel));
    if !target.starts_with(&root_resolved) {
        return Err(PathSecurityError(format!(
            "Path escapes allowed root ({}): {}",
            root.display(),
            rel.display()
        )));
    }
    Ok(target)
}

/// Puerto de `validate_under_root`: valida un *path* ya construido (absoluto
/// o relativo) dentro de *root* y devuelve la versión resuelta.
pub fn validate_under_root(path: &Path, root: &Path) -> Result<PathBuf, PathSecurityError> {
    let root_resolved = resolve_lenient(root);
    let target = resolve_lenient(path);
    if !target.starts_with(&root_resolved) {
        return Err(PathSecurityError(format!(
            "Path escapes allowed root ({}): {}",
            root.display(),
            path.display()
        )));
    }
    Ok(target)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resuelve_bajo_root() {
        let tmp = std::env::temp_dir().join("cortex_sec_ok");
        std::fs::create_dir_all(&tmp).unwrap();
        let got = resolve_safe(&tmp, Path::new("a/b.md")).unwrap();
        assert_eq!(got, tmp.join("a/b.md"));
        assert!(got.starts_with(&tmp));
    }

    #[test]
    fn absoluta_rechazada() {
        let err = resolve_safe(Path::new("/tmp"), Path::new("/etc/passwd")).unwrap_err();
        assert_eq!(err.0, "Absolute paths are not allowed: /etc/passwd");
    }

    #[test]
    fn escape_con_dots_rechazado() {
        let tmp = std::env::temp_dir().join("cortex_sec_escape");
        std::fs::create_dir_all(&tmp).unwrap();
        let err = resolve_safe(&tmp, Path::new("../fuera.md")).unwrap_err();
        assert!(
            err.0.starts_with("Path escapes allowed root ("),
            "{}",
            err.0
        );
        assert!(err.0.ends_with("): ../fuera.md"));
    }

    #[test]
    fn dots_internos_permittedos() {
        // a/../b.md resuelve dentro del root ⇒ permitido (igual que Python).
        let tmp = std::env::temp_dir().join("cortex_sec_inner");
        let sub = tmp.join("a");
        std::fs::create_dir_all(&sub).unwrap();
        let got = resolve_safe(&tmp, Path::new("a/../b.md")).unwrap();
        assert_eq!(got, tmp.join("b.md"));
    }

    #[test]
    fn validate_under_root_acepta_absoluto_dentro() {
        let tmp = std::env::temp_dir().join("cortex_sec_val");
        std::fs::create_dir_all(&tmp).unwrap();
        // Python: path.resolve() de un absoluto bajo root ⇒ ok.
        assert_eq!(
            validate_under_root(&tmp.join("x.md"), &tmp).unwrap(),
            tmp.join("x.md")
        );
        // Un relativo se ancla al CWD (igual que Path.resolve() en Python):
        // salvo que el cwd esté bajo root, escapa y rechaza.
        if std::env::current_dir().unwrap().starts_with(&tmp) {
            // improbable; skip semántico
        } else {
            assert!(validate_under_root(Path::new("x.md"), &tmp).is_err());
        }
        assert!(validate_under_root(Path::new("/etc/passwd"), &tmp).is_err());
    }
}
