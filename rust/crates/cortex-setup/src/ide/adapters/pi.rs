//! Porteo de cortex/ide/adapters/pi.py (P8d).
//!
//! Pi es su propia SSoT: ``inject_profiles`` copia el bundle in-tree
//! ``cortex-pi/`` VERBATIM al project root (nunca se rehidrata desde
//! `.cortex/`; el sync canónico está DESACTIVADO desde mayo 2026 y no se
//! portea — es código muerto). ``inject_mcp`` no aplica (Pi usa bash tools).
//!
//! ``uninstall`` es conservador con archivos del adopter: solo extrae bloques
//! marcados, borra archivos 100% Cortex (idénticos al bundle) y de
//! ``extensions/`` solo quita los archivos que trae el bundle.

use std::io;
use std::path::{Path, PathBuf};

use crate::ide::{IdeAdapter, IdeCtx};

/// Marcadores para localizar bloques Cortex dentro de archivos del project
/// root (AGENTS.md / README.md / justfile). Mismo patrón que codex.py:
/// uninstall solo extrae lo que está entre los marcadores.
const CORTEX_PI_MARKER_OPEN: &str = "<!-- BEGIN CORTEX SECTION (auto-generated, do not edit) -->";
const CORTEX_PI_MARKER_CLOSE: &str = "<!-- END CORTEX SECTION -->";

/// Archivos del project root que el bundle cortex-pi copia verbatim.
/// Uninstall NUNCA debe borrarlos completos salvo que su contenido sea
/// exactamente el del bundle (o sea un bloque Cortex marcado).
const PI_ROOT_FILES: [&str; 3] = ["AGENTS.md", "README.md", "justfile"];

pub struct PiAdapter;

impl PiAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        PiAdapter
    }
}

impl Default for PiAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Path al bundle in-tree `cortex-pi/` (espejo de `_default_pi_bundle_dir`):
/// 4 padres arriba del módulo Python = repo root; acá, 3 arriba del manifest.
fn default_pi_bundle_dir() -> PathBuf {
    PathBuf::from(concat!(env!("CARGO_MANIFEST_DIR"), "/../../../cortex-pi"))
}

/// `shutil.copytree(item, dest, dirs_exist_ok=True)`: copia recursiva que
/// fusiona sobre destino existente. Sin deps nuevas.
fn copy_dir_all(src: &Path, dst: &Path) -> io::Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let dest = dst.join(entry.file_name());
        if ty.is_dir() {
            copy_dir_all(&entry.path(), &dest)?;
        } else {
            std::fs::copy(entry.path(), &dest)?;
        }
    }
    Ok(())
}

/// Emulación EXACTA de la regex de Python:
/// ``OPEN .*? CLOSE \n?`` con DOTALL (sub global, no-codicioso): elimina cada
/// bloque completo más UN `\n` inmediatamente posterior si existe; el resto
/// del contenido queda byte-a-byte intacto (a diferencia de
/// `base::strip_marker_blocks`, que además recorta el final).
///
/// Devuelve `(cleaned, hubo_cambios)` — equivalente a comparar
/// `marker_pattern.sub("", existing)` contra `existing`.
fn sub_marker_blocks(content: &str) -> (String, bool) {
    let bytes = content.as_bytes();
    let open_b = CORTEX_PI_MARKER_OPEN.as_bytes();
    let close_b = CORTEX_PI_MARKER_CLOSE.as_bytes();
    let mut out = String::with_capacity(content.len());
    let mut changed = false;
    let mut i = 0usize;
    while i < bytes.len() {
        // Buscar próximo OPEN.
        if i + open_b.len() <= bytes.len() && &bytes[i..i + open_b.len()] == open_b {
            // Buscar el CLOSE más cercano después del OPEN (no-codicioso).
            let mut j = i + open_b.len();
            let mut close_at = None;
            while j + close_b.len() <= bytes.len() {
                if &bytes[j..j + close_b.len()] == close_b {
                    close_at = Some(j + close_b.len());
                    break;
                }
                j += 1;
            }
            if let Some(end) = close_at {
                // Consumir UN '\n' inmediatamente posterior (`\n?`).
                let mut end2 = end;
                if end2 < bytes.len() && bytes[end2] == b'\n' {
                    end2 += 1;
                }
                changed = true;
                i = end2;
                continue;
            }
        }
        // Copiar el byte-runa actual (seguro: límites UTF-8 preservados).
        let ch_len = content[i..]
            .chars()
            .next()
            .map(|c| c.len_utf8())
            .unwrap_or(1);
        out.push_str(&content[i..i + ch_len]);
        i += ch_len;
    }
    (out, changed)
}

impl IdeAdapter for PiAdapter {
    fn name(&self) -> &'static str {
        "pi"
    }

    fn display_name(&self) -> &'static str {
        "Pi Coding Agent"
    }

    /// Pi configuration is project-local, no global config paths.
    fn config_paths(&self, _ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        Vec::new()
    }

    /// Copies the entire cortex-pi folder contents into the project root,
    /// **as-is**. El bundle `cortex-pi/` es la única fuente de verdad de Pi
    /// y nunca se refresca desde `.cortex/`. El flag ``sync_canonical`` de
    /// Python está neutralizado (acepta el kwarg pero lo ignora).
    fn inject_profiles(
        &self,
        ctx: &IdeCtx,
        _prompts: &crate::ide::Prompts,
    ) -> Result<Vec<String>, String> {
        let cortex_pi_dir = default_pi_bundle_dir();

        let mut files_written = Vec::new();
        if cortex_pi_dir.is_dir() {
            for item in std::fs::read_dir(&cortex_pi_dir)
                .map_err(|e| format!("read {}: {e}", cortex_pi_dir.display()))?
            {
                let item = item.map_err(|e| e.to_string())?;
                let dest = ctx.project_root.join(item.file_name());
                if item.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    copy_dir_all(&item.path(), &dest)
                        .map_err(|e| format!("copytree {}: {e}", item.path().display()))?;
                    files_written.push(format!("{}/", item.file_name().to_string_lossy()));
                } else {
                    std::fs::copy(item.path(), &dest)
                        .map_err(|e| format!("copy {}: {e}", item.path().display()))?;
                    files_written.push(item.file_name().to_string_lossy().into_owned());
                }
            }
        } else {
            return Err(format!(
                "cortex-pi template directory not found at {}",
                cortex_pi_dir.display()
            ));
        }

        Ok(files_written)
    }

    /// Pi Coding Agent uses bash tools, MCP injection not required.
    fn inject_mcp(&self, _ctx: &IdeCtx) -> Result<Vec<String>, String> {
        Ok(Vec::new())
    }

    /// Uninstall conservador con archivos del adopter (ver doc de Python).
    /// En Rust `ctx.project_root` siempre está presente: la rama `None`
    /// de Python (warning + no-op) no es alcanzable.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let project_root = ctx.project_root;
        let mut files_removed: Vec<String> = Vec::new();

        let pi_dir = project_root.join(".pi");
        if pi_dir.exists() {
            let _ = std::fs::remove_dir_all(&pi_dir);
            files_removed.push(".pi/".to_string());
        }

        let bundle = default_pi_bundle_dir();

        for name in PI_ROOT_FILES {
            let path = project_root.join(name);
            if !path.is_file() {
                continue;
            }
            let existing = std::fs::read_to_string(&path).unwrap_or_default();
            let (cleaned, had_blocks) = sub_marker_blocks(&existing);
            if had_blocks {
                // Había bloque(s) Cortex marcados: extraerlos solamente.
                if !cleaned.trim().is_empty() {
                    let _ = std::fs::write(&path, &cleaned);
                    files_removed.push(format!("{name} (Cortex section removed)"));
                } else {
                    let _ = std::fs::remove_file(&path);
                    files_removed.push(name.to_string());
                }
                continue;
            }
            let bundle_src = bundle.join(name);
            let bundle_content = std::fs::read_to_string(&bundle_src).unwrap_or_default();
            if bundle_src.exists() && existing == bundle_content {
                // Archivo creado íntegramente por Cortex (copia verbatim del
                // bundle, sin contenido previo del adopter): seguro borrar.
                let _ = std::fs::remove_file(&path);
                files_removed.push(name.to_string());
                continue;
            }
            // Contenido mixto/desconocido: dejar intacto y reportarlo.
            files_removed.push(format!(
                "{name} (skipped: unknown/mixed content, left intact)"
            ));
        }

        // extensions/: solo borrar los archivos que trae el bundle; nunca el
        // directorio completo (el adopter puede tener las suyas).
        let ext_dir = project_root.join("extensions");
        let bundle_ext = bundle.join("extensions");
        if ext_dir.is_dir() && bundle_ext.is_dir() {
            let mut items: Vec<PathBuf> = std::fs::read_dir(&bundle_ext)
                .into_iter()
                .flatten()
                .flatten()
                .map(|e| e.path())
                .collect();
            // `sorted(bundle_ext.iterdir())` de Python: orden lexicográfico.
            items.sort_by_key(|p| p.to_string_lossy().into_owned());
            for item in items {
                let target = ext_dir.join(item.file_name().unwrap_or_default());
                if target.is_file() {
                    let _ = std::fs::remove_file(&target);
                    if let Ok(rel) = target.strip_prefix(project_root) {
                        files_removed.push(rel.to_string_lossy().into_owned());
                    }
                }
            }
        }

        files_removed
    }
}
