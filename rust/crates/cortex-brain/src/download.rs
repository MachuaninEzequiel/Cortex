//! Descarga del GGUF de Liquid (Obra 19, G-L1, C-L1.2).
//!
//! C-L1.2 introduce el trait [`ModelSource`] con dos implementaciones:
//! - [`HttpSource`]: descarga desde HuggingFace vía `ureq` (la lógica
//!   completa de fetch llega en C-L1.3; por ahora la estructura está
//!   armada y `fetch` está `todo!()`).
//! - [`LocalSource`]: copia desde una ruta local. Útil para tests, para
//!   el subcomando `cortex brain install --path` y para smoke manual.
//!
//! Spec: docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md §2.

use std::path::{Path, PathBuf};

use crate::paths;

/// Tamaño de chunk para la lectura/escritura durante el download (64 KB).
const CHUNK_BYTES: usize = 64 * 1024;

/// Resultado de una descarga: ruta final del archivo + bytes transferidos.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DownloadResult {
    /// Ruta final del archivo (normalmente `paths::default_model_path()`).
    pub path: PathBuf,
    /// Bytes efectivamente escritos.
    pub bytes: u64,
}

/// Estado de progreso observable desde un callback.
///
/// En C-L1.2 esto es solo el esqueleto. En C-L1.3 se llena de verdad
/// durante la descarga.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DownloadProgress {
    /// Bytes transferidos hasta el momento.
    pub bytes_done: u64,
    /// Total esperado (si el servidor lo reportó vía `Content-Length`).
    pub bytes_total: Option<u64>,
}

impl DownloadProgress {
    #[must_use]
    pub fn new(bytes_done: u64, bytes_total: Option<u64>) -> Self {
        Self {
            bytes_done,
            bytes_total,
        }
    }
}

/// Errores posibles durante la descarga. Se mantiene chico a propósito;
/// la versión "ruidosa" (con `.to_string()` legible) la arma cada caller
/// con `i18n::*` en C-L1.5.
#[derive(Debug)]
pub enum DownloadError {
    /// El source devolvió bytes vacíos.
    Empty,
    /// I/O local (escribir el tmp, renombrar, abrir el source, etc).
    Io(std::io::Error),
    /// HTTP: el servidor devolvió un status no-2xx o falló la conexión.
    /// `String` con el detalle (vendrá de `ureq::Error::to_string()`).
    Http(String),
    /// La lógica de fetch todavía no está implementada (gate C-L1.3).
    NotImplemented,
}

impl std::fmt::Display for DownloadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DownloadError::Empty => f.write_str("source devolvió 0 bytes"),
            DownloadError::Io(e) => write!(f, "io: {e}"),
            DownloadError::Http(s) => write!(f, "http: {s}"),
            DownloadError::NotImplemented => f.write_str("fetch: lógica pendiente (C-L1.3)"),
        }
    }
}

impl std::error::Error for DownloadError {}

impl From<std::io::Error> for DownloadError {
    fn from(e: std::io::Error) -> Self {
        DownloadError::Io(e)
    }
}

/// Trait abstracto para las fuentes de GGUF. Permite testear toda la
/// lógica de `install` sin tocar red: en tests se usa [`LocalSource`];
/// en producción, [`HttpSource`].
///
/// **C-L1.2:** firma definida. La implementación real de `HttpSource::fetch`
/// queda para C-L1.3 (lógica de descarga + sha256 + progreso). `LocalSource::fetch`
/// sí está completa porque es la que ejercita los tests del trait.
pub trait ModelSource: Send + Sync {
    /// Trae el archivo a `dest`. Devuelve el resultado con la ruta final
    /// y los bytes transferidos. El callback `on_progress` se invoca
    /// periódicamente (mínimo una vez al inicio, una al final); en esta
    /// etapa es opcional y se deja en `None` cuando no se quiere.
    fn fetch(
        &self,
        dest: &Path,
        on_progress: Option<&mut dyn FnMut(DownloadProgress)>,
    ) -> Result<DownloadResult, DownloadError>;
}

// ── LocalSource (completa, para tests y `cortex brain install --path`) ───

/// Copia un archivo local al destino. Útil para:
/// - Tests del módulo `download::*` (sin red).
/// - `cortex brain install --path /ruta/local.gguf` (importación manual).
#[derive(Debug, Clone)]
pub struct LocalSource {
    /// Ruta del archivo .gguf local a copiar.
    pub path: PathBuf,
}

impl LocalSource {
    #[must_use]
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }
}

impl ModelSource for LocalSource {
    fn fetch(
        &self,
        dest: &Path,
        mut on_progress: Option<&mut dyn FnMut(DownloadProgress)>,
    ) -> Result<DownloadResult, DownloadError> {
        let bytes_total = std::fs::metadata(&self.path).map(|m| m.len()).ok();

        if let Some(p) = on_progress.as_deref_mut() {
            p(DownloadProgress::new(0, bytes_total));
        }

        let input = std::fs::File::open(&self.path)?;
        let mut reader = std::io::BufReader::new(input);

        // Asegurar el directorio padre del destino.
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent)?;
        }

        // El .partial va SIEMPRE al lado del destino, en el mismo FS, para
        // que el rename(2) final sea atómico (rename cross-device devuelve
        // EXDEV y deja el árbol inconsistente). `paths::partial_dir()` queda
        // como referencia para v1.3 (cleanup global de huérfanos).
        let dest_name = dest
            .file_name()
            .unwrap_or_else(|| std::ffi::OsStr::new("model.gguf"));
        let partial = dest
            .parent()
            .unwrap_or_else(|| std::path::Path::new("."))
            .join(format!(".partial.{}", dest_name.to_string_lossy()));
        let tmp = std::fs::File::create(&partial)?;
        let mut writer = std::io::BufWriter::new(tmp);

        let mut buf = vec![0u8; CHUNK_BYTES];
        let mut total: u64 = 0;
        use std::io::Read as _;
        use std::io::Write as _;
        loop {
            let n = reader.read(&mut buf)?;
            if n == 0 {
                break;
            }
            writer.write_all(&buf[..n])?;
            total += n as u64;
            if let Some(p) = on_progress.as_deref_mut() {
                p(DownloadProgress::new(total, bytes_total));
            }
        }
        writer.flush()?;
        drop(writer);

        if total == 0 {
            // Limpio el .partial y devuelvo error explícito.
            let _ = std::fs::remove_file(&partial);
            return Err(DownloadError::Empty);
        }

        // Rename atómico al destino final.
        std::fs::rename(&partial, dest)?;

        Ok(DownloadResult {
            path: dest.to_path_buf(),
            bytes: total,
        })
    }
}

// ── HttpSource (estructura + URL; fetch en C-L1.3) ───────────────────────

/// URL default del GGUF en HuggingFace. Documentada en doc 19 §2.1.
pub const DEFAULT_REPO: &str = "LiquidAI/LFM2.5-1.2B-Instruct-GGUF";

/// URL default del archivo Q4_K_M (resolución HF: `resolve/main/...`).
pub fn default_url() -> String {
    format!(
        "https://huggingface.co/{DEFAULT_REPO}/resolve/main/{}",
        paths::DEFAULT_MODEL_FILENAME
    )
}

/// URL del sidecar `.sha256` que HuggingFace publica junto a cada binario.
pub fn default_sha256_url() -> String {
    format!(
        "https://huggingface.co/{DEFAULT_REPO}/resolve/main/{}.sha256",
        paths::DEFAULT_MODEL_FILENAME
    )
}

/// Source HTTP para el GGUF (HuggingFace o URL custom).
///
/// **C-L1.2:** la estructura y la URL están armadas. La lógica de
/// `fetch` (request, lectura chunked, sha256, progreso) se implementa
/// en C-L1.3.
#[derive(Debug, Clone)]
pub struct HttpSource {
    pub url: String,
    pub sha256_url: String,
}

impl Default for HttpSource {
    fn default() -> Self {
        Self {
            url: default_url(),
            sha256_url: default_sha256_url(),
        }
    }
}

impl HttpSource {
    /// Construye contra el repo default (`LiquidAI/LFM2.5-1.2B-Instruct-GGUF`,
    /// archivo `LFM2.5-1.2B-Instruct-Q4_K_M.gguf`).
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Construye contra una URL custom (defensa en profundidad: si HF
    /// cambia el path, el caller puede pasar otra URL).
    #[must_use]
    pub fn with_url(url: String, sha256_url: String) -> Self {
        Self { url, sha256_url }
    }
}

impl ModelSource for HttpSource {
    fn fetch(
        &self,
        _dest: &Path,
        _on_progress: Option<&mut dyn FnMut(DownloadProgress)>,
    ) -> Result<DownloadResult, DownloadError> {
        // Implementación real llega en C-L1.3: ureq::get → response →
        // Content-Length → loop de read_exact → write → sha256 → rename.
        Err(DownloadError::NotImplemented)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write as _;
    use std::sync::Mutex;

    // Serializa tests que tocan filesystem compartido.
    static FS_LOCK: Mutex<()> = Mutex::new(());

    fn tmpdir(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("cortex-download-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn local_source_copia_archivo_y_reporta_bytes() {
        let _g = FS_LOCK.lock().unwrap();
        let dir = tmpdir("local-ok");
        let src = dir.join("src.gguf");
        let mut f = std::fs::File::create(&src).unwrap();
        f.write_all(&vec![0u8; 1024]).unwrap();
        f.write_all(b"hello").unwrap();
        drop(f);

        let dest = dir.join("dest.gguf");
        let src_meta = std::fs::metadata(&src).unwrap().len();
        let source = LocalSource::new(src.clone());
        let res = source.fetch(&dest, None).expect("fetch ok");

        assert_eq!(res.bytes, src_meta);
        assert_eq!(res.path, dest);
        assert!(dest.exists());

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn local_source_reporte_de_progreso_se_invoca_al_menos_dos_veces() {
        let _g = FS_LOCK.lock().unwrap();
        let dir = tmpdir("local-progress");
        let src = dir.join("src.gguf");
        std::fs::write(&src, vec![0u8; 1024]).unwrap();

        let dest = dir.join("dest.gguf");
        let source = LocalSource::new(src.clone());
        let mut calls = 0u32;
        let mut last: Option<DownloadProgress> = None;
        let res = source
            .fetch(
                &dest,
                Some(&mut |p: DownloadProgress| {
                    calls += 1;
                    last = Some(p);
                }),
            )
            .expect("fetch ok");
        assert!(res.bytes >= 1024);
        assert!(calls >= 2, "se invoca al menos 2 veces: {calls}");
        let last = last.expect("last progress");
        assert_eq!(last.bytes_done, res.bytes);
        assert_eq!(last.bytes_total, Some(1024));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn local_source_archivo_vacio_devuelve_empty() {
        let _g = FS_LOCK.lock().unwrap();
        let dir = tmpdir("local-empty");
        let src = dir.join("empty.gguf");
        std::fs::write(&src, b"").unwrap();

        let dest = dir.join("dest.gguf");
        let source = LocalSource::new(src.clone());
        let res = source.fetch(&dest, None);
        assert!(matches!(res, Err(DownloadError::Empty)));
        assert!(!dest.exists(), "no debe quedar un destino vacío");

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn local_source_no_abre_si_source_no_existe() {
        let _g = FS_LOCK.lock().unwrap();
        let dir = tmpdir("local-missing");
        let src = dir.join("missing.gguf");
        let dest = dir.join("dest.gguf");
        let source = LocalSource::new(src);
        let res = source.fetch(&dest, None);
        assert!(matches!(res, Err(DownloadError::Io(_))));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn local_source_escribe_en_partial_y_luego_renombra_atomico() {
        let _g = FS_LOCK.lock().unwrap();
        let dir = tmpdir("local-rename");
        let src = dir.join("src.gguf");
        std::fs::write(&src, vec![1u8; 4096]).unwrap();

        let dest = dir.join("dest.gguf");
        let source = LocalSource::new(src);
        let res = source.fetch(&dest, None).expect("fetch ok");
        assert!(res.path.exists());

        // Después del rename, el .partial.<nombre> local no debe quedar.
        let partial = dir.join(".partial.dest.gguf");
        assert!(!partial.exists(), "el .partial se debe haber renombrado");

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn http_source_tiene_url_default_a_huggingface() {
        let s = HttpSource::new();
        assert_eq!(s.url, default_url());
        assert!(s.url.contains("huggingface.co"));
        assert!(s.url.contains("LiquidAI/LFM2.5-1.2B-Instruct-GGUF"));
        assert!(s.url.contains(paths::DEFAULT_MODEL_FILENAME));
        assert!(s.sha256_url.ends_with(".sha256"));
    }

    #[test]
    fn http_source_con_url_custom() {
        let s = HttpSource::with_url(
            "https://example.com/mi.gguf".into(),
            "https://example.com/mi.gguf.sha256".into(),
        );
        assert_eq!(s.url, "https://example.com/mi.gguf");
        assert_eq!(s.sha256_url, "https://example.com/mi.gguf.sha256");
    }

    #[test]
    fn http_source_fetch_devuelve_not_implemented_en_esta_etapa() {
        let s = HttpSource::new();
        let dest = std::env::temp_dir().join("cortex-http-todo.gguf");
        let res = s.fetch(&dest, None);
        assert!(matches!(res, Err(DownloadError::NotImplemented)));
    }
}
