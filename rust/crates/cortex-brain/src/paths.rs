//! Rutas y convenciones del modelo GGUF local.
//!
//! Vive en su propio módulo (no dentro de `llama`) para que tanto el
//! binario standalone como `cortex brain install` puedan consultarla SIN
//! el feature `llama` (que requiere cmake y compilación pesada).
//!
//! Spec: docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md §2.

use std::path::PathBuf;

#[cfg(test)]
use std::path::Path;

/// Nombre del archivo GGUF (constante; verificado contra
/// LiquidAI/LFM2.5-1.2B-Instruct-GGUF en HuggingFace).
pub const DEFAULT_MODEL_FILENAME: &str = "LFM2.5-1.2B-Instruct-Q4_K_M.gguf";

/// Directorio default: `$HOME/.cache/cortex/models/`.
/// Sin soporte de `XDG_CACHE_HOME` ni `~/Library/Caches` (macOS) en v1
/// (ver §6.1 fuera de alcance del doc 19).
#[must_use]
pub fn default_model_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_default();
    PathBuf::from(home)
        .join(".cache")
        .join("cortex")
        .join("models")
}

/// Ruta default completa al GGUF.
#[must_use]
pub fn default_model_path() -> PathBuf {
    default_model_dir().join(DEFAULT_MODEL_FILENAME)
}

/// Devuelve la ruta default **solo si existe**; `None` si el archivo no
/// está. Usado por el binario y el Companion para detectar "¿hay modelo?".
#[must_use]
pub fn default_model_path_if_exists() -> Option<PathBuf> {
    let p = default_model_path();
    p.exists().then_some(p)
}

/// Sidecar con el sha256 esperado del GGUF (escrito por
/// `download::install` después de validar).
#[must_use]
pub fn sha_sidecar_path() -> PathBuf {
    default_model_dir().join(".sha256")
}

/// Lockfile de instalación concurrente.
#[must_use]
pub fn lockfile_path() -> PathBuf {
    default_model_dir().join(".lock")
}

/// Directorio de descargas parciales (tmp antes del rename atómico).
#[must_use]
pub fn partial_dir() -> PathBuf {
    default_model_dir().join(".partial")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // Serializa los tests que tocan $HOME.
    static HOME_LOCK: Mutex<()> = Mutex::new(());

    /// Helper: aísla el HOME bajo un directorio temporal.
    fn with_tmp_home<F: FnOnce(&Path)>(f: F) {
        let dir = std::env::temp_dir().join(format!("cortex-paths-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        // SAFETY: tests serializados por `HOME_LOCK`.
        unsafe {
            std::env::set_var("HOME", &dir);
        }
        f(&dir);
        // SAFETY: idem.
        unsafe {
            std::env::remove_var("HOME");
        }
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn default_model_dir_termina_en_models() {
        let _g = HOME_LOCK.lock().unwrap();
        with_tmp_home(|home| {
            let d = default_model_dir();
            assert_eq!(d, home.join(".cache").join("cortex").join("models"));
        });
    }

    #[test]
    fn default_model_path_incluye_nombre_oficial() {
        let _g = HOME_LOCK.lock().unwrap();
        with_tmp_home(|home| {
            let p = default_model_path();
            assert_eq!(
                p,
                home.join(".cache")
                    .join("cortex")
                    .join("models")
                    .join(DEFAULT_MODEL_FILENAME)
            );
            assert_eq!(DEFAULT_MODEL_FILENAME, "LFM2.5-1.2B-Instruct-Q4_K_M.gguf");
        });
    }

    #[test]
    fn default_model_path_if_exists_none_sin_archivo() {
        let _g = HOME_LOCK.lock().unwrap();
        with_tmp_home(|_| {
            assert!(default_model_path_if_exists().is_none());
        });
    }

    #[test]
    fn default_model_path_if_exists_some_con_archivo() {
        let _g = HOME_LOCK.lock().unwrap();
        with_tmp_home(|home| {
            let dir = home.join(".cache").join("cortex").join("models");
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join(DEFAULT_MODEL_FILENAME), b"fake-gguf").unwrap();
            let p = default_model_path_if_exists().expect("debe existir");
            assert!(p.ends_with(DEFAULT_MODEL_FILENAME));
        });
    }

    #[test]
    fn sidecar_paths_viven_en_el_mismo_dir() {
        let _g = HOME_LOCK.lock().unwrap();
        with_tmp_home(|_| {
            let d = default_model_dir();
            assert_eq!(sha_sidecar_path().parent(), Some(d.as_path()));
            assert_eq!(lockfile_path().parent(), Some(d.as_path()));
            assert_eq!(partial_dir().parent(), Some(d.as_path()));
        });
    }
}
