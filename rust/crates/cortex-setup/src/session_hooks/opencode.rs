//! Porteo de cortex/session/hooks/adapters/opencode.py (P8e).
//!
//! Administra el bloque Cortex dentro de `.opencode/hooks.md`. Solo toca un
//! archivo markdown: el binario opencode NO necesita estar instalado.

use std::path::{Path, PathBuf};

use super::{
    read_or_empty, strip_block, write_lf, HookAdapter, HookStatus, InstallResult, UninstallResult,
};

pub const HOOKS_RELATIVE: &str = ".opencode/hooks.md";
pub const START_MARKER: &str =
    "<!-- >>> cortex-session-hook (managed by 'cortex session hooks') >>> -->";
pub const END_MARKER: &str = "<!-- <<< cortex-session-hook <<< -->";

// `_HOOK_COMMAND` de Python va embebido literal dentro del bloque
// (`concat!` no interpola consts).
pub const HOOK_BLOCK: &str = concat!(
    "<!-- >>> cortex-session-hook (managed by 'cortex session hooks') >>> -->\n",
    "## Cortex session checkpoint\n",
    "\n",
    "Emits a checkpoint to the active Cortex session after each\n",
    "significant edit. The ``|| true`` guard prevents Cortex failures\n",
    "from interrupting opencode.\n",
    "\n",
    "```sh\n",
    "cortex session checkpoint --source ide-hook --note \"edit via opencode\" >/dev/null 2>&1 || true\n",
    "```\n",
    "<!-- <<< cortex-session-hook <<< -->\n",
);

pub struct OpencodeHookAdapter;

impl OpencodeHookAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        OpencodeHookAdapter
    }

    fn hooks_path(&self, target_dir: &Path) -> PathBuf {
        target_dir.join(HOOKS_RELATIVE)
    }

    /// `_render`: preserva secciones del usuario.
    fn render(&self, existing: &str) -> String {
        let existing = existing.trim_end();
        if existing.is_empty() {
            return HOOK_BLOCK.to_string();
        }
        format!("{existing}\n\n{HOOK_BLOCK}")
    }
}

impl Default for OpencodeHookAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl HookAdapter for OpencodeHookAdapter {
    fn name(&self) -> &'static str {
        "opencode"
    }

    fn install(&self, target_dir: &Path) -> Result<InstallResult, String> {
        let target = self.hooks_path(target_dir);
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("mkdir: {e}"))?;
        }

        let existing = read_or_empty(&target);
        if existing.contains(START_MARKER) {
            return Ok(InstallResult {
                ide: self.name(),
                installed: true,
                modified_paths: vec![],
                message: format!("already installed in {}", target.display()),
            });
        }

        let new_content = self.render(&existing);
        write_lf(&target, &new_content)?;
        Ok(InstallResult {
            ide: self.name(),
            installed: true,
            modified_paths: vec![target.clone()],
            message: format!("installed opencode hooks entry in {}", target.display()),
        })
    }

    fn uninstall(&self, target_dir: &Path) -> Result<UninstallResult, String> {
        let target = self.hooks_path(target_dir);
        if !target.exists() {
            return Ok(UninstallResult {
                ide: self.name(),
                uninstalled: false,
                removed_paths: vec![],
                message: format!("{} does not exist", target.display()),
            });
        }
        let content = read_or_empty(&target);
        if !content.contains(START_MARKER) {
            return Ok(UninstallResult {
                ide: self.name(),
                uninstalled: false,
                removed_paths: vec![],
                message: format!("no cortex-managed block in {}", target.display()),
            });
        }
        let cleaned = format!(
            "{}\n",
            strip_block(&content, START_MARKER, END_MARKER).trim_end()
        );
        if cleaned.trim().is_empty() {
            std::fs::remove_file(&target).map_err(|e| format!("unlink: {e}"))?;
            return Ok(UninstallResult {
                ide: self.name(),
                uninstalled: true,
                removed_paths: vec![target.clone()],
                message: format!("removed (file had no other content) {}", target.display()),
            });
        }
        write_lf(&target, &cleaned)?;
        Ok(UninstallResult {
            ide: self.name(),
            uninstalled: true,
            removed_paths: vec![target.clone()],
            message: format!("removed cortex block from {}", target.display()),
        })
    }

    fn status(&self, target_dir: &Path) -> HookStatus {
        let target = self.hooks_path(target_dir);
        if !target.exists() {
            return HookStatus {
                ide: self.name(),
                installed: false,
                detail: format!("{} does not exist", target.display()),
            };
        }
        let installed = read_or_empty(&target).contains(START_MARKER);
        if installed {
            HookStatus {
                ide: self.name(),
                installed: true,
                detail: format!("cortex block present in {}", target.display()),
            }
        } else {
            HookStatus {
                ide: self.name(),
                installed: false,
                detail: format!("{} exists but no cortex block", target.display()),
            }
        }
    }
}
