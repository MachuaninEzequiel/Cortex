//! Porteo de cortex/session/hooks/adapters/cursor.py (P8e).
//!
//! A pesar del nombre NO es Cursor-específico: instala un bloque marcado en
//! `.git/hooks/post-commit`, así que funciona para cualquier IDE que corra
//! `git commit`. El bloque emite un checkpoint con SHA y subject del commit;
//! `|| true` garantiza que un fallo de Cortex nunca falle el commit.
//!
//! Si el usuario tiene su propio `post-commit`, se agrega un bloque
//! separado; uninstall remueve SOLO ese bloque.

use std::path::{Path, PathBuf};

use super::{
    read_or_empty, strip_block, write_lf, HookAdapter, HookStatus, InstallResult, UninstallResult,
};

pub const POST_COMMIT_RELATIVE: &str = ".git/hooks/post-commit";
pub const START_MARKER: &str = "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>";
pub const END_MARKER: &str = "# <<< cortex-session-hook <<<";
pub const SHEBANG: &str = "#!/bin/sh";

/// Bloque HOOK_BLOCK de Python (`"\n".join([...])` con "" final → termina
/// en `\n\n`... exactamente: cada item va separado por `\n` y el último
/// item es "" ⇒ el bloque completo termina en `\n`).
pub const HOOK_BLOCK: &str = concat!(
    "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>\n",
    "# Emits a checkpoint to the active Cortex session after each commit.\n",
    "# The `|| true` guard prevents a Cortex failure from blocking commits.\n",
    "SHA=$(git rev-parse --short HEAD 2>/dev/null) || SHA=unknown\n",
    "SUBJ=$(git log -1 --pretty=%s 2>/dev/null) || SUBJ='(no subject)'\n",
    "cortex session checkpoint --source ide-hook --note \"git commit ${SHA}: ${SUBJ}\" >/dev/null 2>&1 || true\n",
    "# <<< cortex-session-hook <<<\n",
);

pub struct CursorGitHookAdapter;

impl CursorGitHookAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        CursorGitHookAdapter
    }

    fn hook_path(&self, target_dir: &Path) -> PathBuf {
        target_dir.join(POST_COMMIT_RELATIVE)
    }

    /// `_require_git_repo`: ValueError si no hay `.git/`.
    fn require_git_repo(&self, target_dir: &Path) -> Result<(), String> {
        let git_dir = target_dir.join(".git");
        if !git_dir.exists() {
            return Err(format!(
                "not a git repository: {} does not exist (run `git init` first)",
                git_dir.display()
            ));
        }
        Ok(())
    }

    /// `_render`: preserva contenido del usuario; agrega shebang si falta.
    fn render(&self, existing: &str) -> String {
        let existing = existing.trim_end();
        if existing.is_empty() {
            return format!("{SHEBANG}\n\n{HOOK_BLOCK}");
        }
        let trimmed_start = existing.trim_start();
        if !trimmed_start.starts_with("#!") {
            // Sin shebang en el archivo del usuario; agregarlo por seguridad.
            return format!("{SHEBANG}\n{existing}\n\n{HOOK_BLOCK}");
        }
        format!("{existing}\n\n{HOOK_BLOCK}")
    }

    /// `_ensure_executable`: chmod |0o111; OSError ignorado (Windows/RO).
    fn ensure_executable(&self, path: &Path) {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = path.metadata() {
            let mut perms = meta.permissions();
            let mode = perms.mode();
            perms.set_mode(mode | 0o111);
            let _ = std::fs::set_permissions(path, perms);
        }
    }
}

impl Default for CursorGitHookAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl HookAdapter for CursorGitHookAdapter {
    fn name(&self) -> &'static str {
        "cursor"
    }

    fn install(&self, target_dir: &Path) -> Result<InstallResult, String> {
        let target = self.hook_path(target_dir);
        self.require_git_repo(target_dir)?;
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
        self.ensure_executable(&target);
        Ok(InstallResult {
            ide: self.name(),
            installed: true,
            modified_paths: vec![target.clone()],
            message: format!("installed git post-commit hook in {}", target.display()),
        })
    }

    fn uninstall(&self, target_dir: &Path) -> Result<UninstallResult, String> {
        let target = self.hook_path(target_dir);
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
        let stripped = cleaned.trim();
        if stripped.is_empty() || stripped == SHEBANG {
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
        let target = self.hook_path(target_dir);
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
