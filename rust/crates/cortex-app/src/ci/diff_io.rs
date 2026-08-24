//! Puerto de `cortex/ci/diff_io.py` — resolver el texto del diff.
//!
//! Tres modos de entrada, en orden de prioridad:
//! 1. `--diff <file>`: leer el archivo crudo.
//! 2. `--base-commit` (+ `--head-commit` opcional): `git diff base..head|HEAD`.
//! 3. Auto: `git diff <trunk>..HEAD` con trunk = main | master (el que exista).

use std::path::Path;
use std::process::Command;

use crate::git;

#[derive(Debug, Clone)]
pub struct DiffResolutionError(pub String);

impl std::fmt::Display for DiffResolutionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for DiffResolutionError {}

pub fn read_diff_from_args(
    diff_file: Option<&Path>,
    base_commit: Option<&str>,
    head_commit: Option<&str>,
    repo_root: &Path,
) -> Result<String, DiffResolutionError> {
    if let Some(diff_file) = diff_file {
        if !diff_file.is_file() {
            return Err(DiffResolutionError(format!(
                "--diff file not found: {}",
                diff_file.display()
            )));
        }
        return std::fs::read_to_string(diff_file).map_err(|e| DiffResolutionError(e.to_string()));
    }

    let short = |s: &str| s.get(..8).unwrap_or(s).to_string();

    match (
        base_commit.filter(|s| !s.is_empty()),
        head_commit.filter(|s| !s.is_empty()),
    ) {
        (Some(base), Some(head)) => git::diff(base, head, repo_root).map_err(|e| {
            DiffResolutionError(format!(
                "git diff {}..{} failed: {e}",
                short(base),
                short(head)
            ))
        }),
        (Some(base), None) => git::diff(base, "HEAD", repo_root).map_err(|e| {
            DiffResolutionError(format!("git diff {}..HEAD failed: {e}", short(base)))
        }),
        (None, _) => {
            let trunk = detect_trunk(repo_root).ok_or_else(|| {
                DiffResolutionError(
                    "could not auto-detect trunk branch (neither 'main' nor 'master' exists); \
                         pass --diff / --base-commit / --head-commit explicitly"
                        .into(),
                )
            })?;
            git::diff(&trunk, "HEAD", repo_root)
                .map_err(|e| DiffResolutionError(format!("git diff {trunk}..HEAD failed: {e}")))
        }
    }
}

/// `main` o `master` (el que exista), o `None`.
fn detect_trunk(repo_root: &Path) -> Option<String> {
    for candidate in ["main", "master"] {
        let ok = Command::new("git")
            .args(["rev-parse", "--verify", &format!("refs/heads/{candidate}")])
            .current_dir(repo_root)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false);
        if ok {
            return Some(candidate.to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn git(repo: &Path, args: &[&str]) {
        let out = Command::new("git")
            .args(args)
            .current_dir(repo)
            .env("GIT_AUTHOR_NAME", "T")
            .env("GIT_AUTHOR_EMAIL", "t@x.com")
            .env("GIT_COMMITTER_NAME", "T")
            .env("GIT_COMMITTER_EMAIL", "t@x.com")
            .output()
            .expect("git");
        assert!(
            out.status.success(),
            "git {args:?} falló: {}",
            String::from_utf8_lossy(&out.stderr)
        );
    }

    use crate::ci::TempGuard;

    fn seed_repo() -> TempGuard {
        let tmp = TempGuard::new("diffio");
        let repo = tmp.path();
        git(repo, &["init", "-q", "-b", "main"]);
        std::fs::write(repo.join("x.txt"), "v1\n").unwrap();
        git(repo, &["add", "."]);
        git(repo, &["commit", "-q", "-m", "seed"]);
        tmp
    }

    #[test]
    fn desde_archivo_y_errores() {
        let tmp = TempGuard::new("diffio-file");
        let repo = seed_repo();
        let diff_path = tmp.path().join("in.diff");
        std::fs::write(&diff_path, "--- a/x\n+++ b/x\n+new\n").unwrap();
        let out = read_diff_from_args(Some(&diff_path), None, None, repo.path()).unwrap();
        assert!(out.contains("+new"));

        // Archivo inexistente ⇒ error "not found".
        let err = read_diff_from_args(
            Some(&tmp.path().join("missing.diff")),
            None,
            None,
            repo.path(),
        )
        .unwrap_err();
        assert!(err.0.contains("not found"));
    }

    #[test]
    fn auto_trunk_y_sin_trunk() {
        // Con trunk main existente y sin commits nuevos: diff vacío pero Ok.
        let repo = seed_repo();
        let out = read_diff_from_args(None, None, None, repo.path()).unwrap();
        assert_eq!(out, "");

        // Sin main ni master ⇒ error de auto-detección.
        let bare = TempGuard::new("diffio-plain");
        let plain = bare.path().join("plain");
        std::fs::create_dir_all(&plain).unwrap();
        let err = read_diff_from_args(None, None, None, &plain).unwrap_err();
        assert!(err.0.contains("auto-detect"));
    }

    #[test]
    fn base_commit_contra_head() {
        let repo = seed_repo();
        let head = crate::git::get_head_commit(repo.path()).unwrap();
        std::fs::write(repo.path().join("x.txt"), "v1\nv2\n").unwrap();
        git(repo.path(), &["add", "."]);
        git(repo.path(), &["commit", "-q", "-m", "v2"]);
        let out = read_diff_from_args(None, Some(&head), None, repo.path()).unwrap();
        assert!(out.contains("+++ b/x.txt"));
    }
}
