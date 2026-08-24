//! Porteo de cortex/session/hooks/adapters/pi.py (P8e).
//!
//! Pi expone su automatización vía un `justfile` project-local. Este adapter
//! agrega tres recetas marcadas (`cortex-checkpoint`, `cortex-finish`,
//! `cortex-status`) envueltas en sentinelas para install/uninstall precisos.
//!
//! Target: `<target_dir>/justfile` (creado si falta).

use std::path::{Path, PathBuf};

use super::{
    read_or_empty, strip_block, write_lf, HookAdapter, HookStatus, InstallResult, UninstallResult,
};

pub const JUSTFILE_RELATIVE: &str = "justfile";
pub const START_MARKER: &str = "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>";
pub const END_MARKER: &str = "# <<< cortex-session-hook <<<";

/// Bloque RECIPE_BLOCK de Python (`"\n".join([...])`, con `{{NOTE}}` literal
/// de just — en Rust se escribe tal cual dentro del const).
pub const RECIPE_BLOCK: &str = concat!(
    "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>\n",
    "# Recipes invoked by Pi Coding Agent (or any just user) to enrich the\n",
    "# active Cortex session. All recipes use `|| true` so a Cortex failure\n",
    "# never aborts the surrounding Pi pipeline.\n",
    "\n",
    "cortex-checkpoint NOTE='pi checkpoint':\n",
    "    cortex session checkpoint --source ide-hook --note \"{{NOTE}}\" >/dev/null 2>&1 || true\n",
    "\n",
    "cortex-finish:\n",
    "    cortex finish-session || true\n",
    "\n",
    "cortex-status:\n",
    "    cortex session show || true\n",
    "# <<< cortex-session-hook <<<\n",
);

pub struct PiHookAdapter;

impl PiHookAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        PiHookAdapter
    }

    fn justfile_path(&self, target_dir: &Path) -> PathBuf {
        target_dir.join(JUSTFILE_RELATIVE)
    }

    /// `_render`: preserva contenido existente.
    fn render(&self, existing: &str) -> String {
        let existing = existing.trim_end();
        if existing.is_empty() {
            return RECIPE_BLOCK.to_string();
        }
        format!("{existing}\n\n{RECIPE_BLOCK}")
    }
}

impl Default for PiHookAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl HookAdapter for PiHookAdapter {
    fn name(&self) -> &'static str {
        "pi"
    }

    fn install(&self, target_dir: &Path) -> Result<InstallResult, String> {
        let target = self.justfile_path(target_dir);
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
            message: format!("installed cortex recipes in {}", target.display()),
        })
    }

    fn uninstall(&self, target_dir: &Path) -> Result<UninstallResult, String> {
        let target = self.justfile_path(target_dir);
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
            message: format!("removed cortex recipes from {}", target.display()),
        })
    }

    fn status(&self, target_dir: &Path) -> HookStatus {
        let target = self.justfile_path(target_dir);
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
                detail: format!("cortex recipes present in {}", target.display()),
            }
        } else {
            HookStatus {
                ide: self.name(),
                installed: false,
                detail: format!("{} exists but no cortex recipes", target.display()),
            }
        }
    }
}
