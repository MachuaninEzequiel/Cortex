//! Porteo de `cortex/runtime_context.py` — slugify, detección git vía
//! subprocess (`git` binario, timeout 5s) y resolución del directorio
//! episódico por namespace (project/branch/custom).

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::layout::resolve_lexical;

/// `slugify`: normaliza a minúsculas, cada corrida de caracteres fuera de
/// `[a-zA-Z0-9._-]` se vuelve UN `-`, se recortan `-` extremos y un
/// resultado vacío cae al fallback.
pub fn slugify(value: &str, fallback: &str) -> String {
    let lower = value.trim().to_lowercase();
    let mut out = String::new();
    let mut in_run = false;
    for ch in lower.chars() {
        if ch.is_ascii_alphanumeric() || ch == '.' || ch == '_' || ch == '-' {
            out.push(ch);
            in_run = false;
        } else if !in_run {
            out.push('-');
            in_run = true;
        }
    }
    let trimmed = out.trim_matches('-');
    if trimmed.is_empty() {
        fallback.to_string()
    } else {
        trimmed.to_string()
    }
}

/// Corre `git <args>` en `project_root` con captura y timeout de 5s.
/// Devuelve None ante error/timeout/rc≠0/stdout vacío (contrato Python).
fn run_git_command(project_root: &Path, args: &[&str]) -> Option<String> {
    let mut child = Command::new("git")
        .args(args)
        .current_dir(project_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .stdin(Stdio::null())
        .spawn()
        .ok()?;

    let started = Instant::now();
    let timeout = Duration::from_secs(5);
    let status = loop {
        match child.try_wait() {
            Ok(Some(st)) => break Some(st),
            Ok(None) => {
                if started.elapsed() > timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return None; // TimeoutExpired ⇒ None
                }
                std::thread::sleep(Duration::from_millis(10));
            }
            Err(_) => return None, // OSError ⇒ None
        }
    };

    use std::io::Read;
    let mut stdout = String::new();
    if let Some(mut pipe) = child.stdout.take() {
        let _ = pipe.read_to_string(&mut stdout);
    }
    let output = stdout.trim().to_string();
    let st = status?;
    if !st.success() || output.is_empty() {
        return None;
    }
    Some(output)
}

/// Rama actual o `"no-git-branch"`.
pub fn detect_git_branch(project_root: &Path) -> String {
    run_git_command(project_root, &["rev-parse", "--abbrev-ref", "HEAD"])
        .unwrap_or_else(|| "no-git-branch".into())
}

/// Toplevel del repo resuelto, o el propio project_root.
pub fn detect_git_repo_path(project_root: &Path) -> PathBuf {
    match run_git_command(project_root, &["rev-parse", "--show-toplevel"]) {
        Some(repo_root) => resolve_lexical(Path::new(&repo_root)),
        None => resolve_lexical(project_root),
    }
}

/// Referencia a la config episódica relevante para namespacing
/// (`episodic_cfg.get(...)` con defaults Python).
#[derive(Debug, Clone, Copy)]
pub struct EpisodicNamespaceCfg<'a> {
    pub persist_dir: &'a str,
    pub namespace_mode: &'a str,
    pub namespace_value: &'a str,
}

impl<'a> EpisodicNamespaceCfg<'a> {
    pub fn new(persist_dir: &'a str, namespace_mode: &'a str, namespace_value: &'a str) -> Self {
        Self {
            persist_dir,
            namespace_mode,
            namespace_value,
        }
    }

    fn mode(&self) -> String {
        self.namespace_mode.trim().to_lowercase()
    }

    fn namespace(&self) -> String {
        self.namespace_value.trim().to_string()
    }
}

impl<'a> Default for EpisodicNamespaceCfg<'a> {
    fn default() -> Self {
        Self {
            persist_dir: "memory",
            namespace_mode: "project",
            namespace_value: "",
        }
    }
}

/// Resuelve el directorio de persistencia episódica según namespace_mode:
/// - `branch` → `<base>/branches/<slugify(branch, "detached")>`
/// - `custom` → `<base>/custom/<slugify(ns o "default")>`
/// - resto (project) → `<base>`
pub fn resolve_episodic_persist_dir(
    project_root: &Path,
    cfg: &EpisodicNamespaceCfg<'_>,
) -> PathBuf {
    // Defaults de dict.get los aplica quien arma la cfg (ver Default).
    let base_dir = cfg.persist_dir;
    let mode = cfg.mode();

    let resolved = resolve_lexical(&project_root.join(base_dir));
    match mode.as_str() {
        "branch" => {
            let branch = slugify(&detect_git_branch(project_root), "detached");
            resolved.join("branches").join(branch)
        }
        "custom" => {
            let mut ns = cfg.namespace();
            if ns.is_empty() {
                ns = "default".into();
            }
            resolved.join("custom").join(slugify(&ns, "default"))
        }
        _ => resolved,
    }
}
