//! Puerto de `cortex/session/git.py` — subprocess con timeout de 10s.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

const TIMEOUT_SECS: u64 = 10;

#[derive(Debug)]
pub struct GitError(pub String);

impl std::fmt::Display for GitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

fn run(args: &[&str], repo_root: &Path) -> Result<String, GitError> {
    let mut child = Command::new("git")
        .args(args)
        .current_dir(repo_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| {
            GitError(if e.kind() == std::io::ErrorKind::NotFound {
                "git executable not found on PATH".into()
            } else {
                format!("git spawn: {e}")
            })
        })?;

    let start = Instant::now();
    let deadline = Duration::from_secs(TIMEOUT_SECS);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let out = child
                    .wait_with_output()
                    .map_err(|e| GitError(e.to_string()))?;
                let stdout = String::from_utf8_lossy(&out.stdout).to_string();
                if !status.success() {
                    let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
                    return Err(GitError(format!(
                        "git {} failed (exit {:?}): {stderr}",
                        args.join(" "),
                        status.code()
                    )));
                }
                return Ok(stdout);
            }
            Ok(None) => {
                if start.elapsed() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(GitError(format!(
                        "git {} timed out after {TIMEOUT_SECS}s in {}",
                        args.join(" "),
                        repo_root.display()
                    )));
                }
                std::thread::sleep(Duration::from_millis(20));
            }
            Err(e) => return Err(GitError(e.to_string())),
        }
    }
}

pub fn is_git_repo(repo_root: &Path) -> bool {
    matches!(
        run(&["rev-parse", "--is-inside-work-tree"], repo_root)
            .map(|s| s.trim().to_string())
            .as_deref(),
        Ok("true")
    )
}

pub fn get_head_commit(repo_root: &Path) -> Result<String, GitError> {
    let sha = run(&["rev-parse", "HEAD"], repo_root)?.trim().to_string();
    if sha.len() != 40
        || !sha
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
    {
        return Err(GitError(format!(
            "git rev-parse HEAD returned unexpected output: {sha:?}"
        )));
    }
    Ok(sha)
}

pub fn get_current_branch(repo_root: &Path) -> Result<String, GitError> {
    Ok(run(&["rev-parse", "--abbrev-ref", "HEAD"], repo_root)?
        .trim()
        .to_string())
}

pub fn diff(start_ref: &str, end_ref: &str, repo_root: &Path) -> Result<String, GitError> {
    run(&["diff", &format!("{start_ref}..{end_ref}")], repo_root)
}

pub fn diff_name_status(
    start_ref: &str,
    end_ref: &str,
    repo_root: &Path,
) -> Result<String, GitError> {
    run(
        &["diff", "--name-status", &format!("{start_ref}..{end_ref}")],
        repo_root,
    )
}

/// Utilidad para fixtures: commit inicial determinista en un repo temporal.
pub fn init_and_commit_all(repo_root: &Path, message: &str) -> Result<(), GitError> {
    run(&["init", "-q", "-b", "main"], repo_root)?;
    for (k, v) in [
        ("user.name", "Cortex Fixture"),
        ("user.email", "fixture@cortex.local"),
        ("commit.gpgsign", "false"),
    ] {
        run(&["config", k, v], repo_root)?;
    }
    run(&["add", "-A"], repo_root)?;
    // Fecha fija ⇒ SHA reproducible entre corridas sobre el MISMO contenido.
    run(
        &[
            "-c",
            "GIT_AUTHOR_DATE=2026-08-24T12:00:00+00:00",
            "-c",
            "GIT_COMMITTER_DATE=2026-08-24T12:00:00+00:00",
            "commit",
            "-q",
            "-m",
            message,
        ],
        repo_root,
    )?;
    let _ = PathBuf::new();
    Ok(())
}
