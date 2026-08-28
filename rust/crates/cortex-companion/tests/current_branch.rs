//! current_branch (G-B2b, engine): lectura pura de fs con `.git` directorio
//! (repo normal) y `.git` archivo (worktree) — sin subprocess.

use std::fs;
use std::path::PathBuf;

use cortex_companion::engine::InProcessBackend;

fn tmp_project(name: &str) -> PathBuf {
    let dir =
        std::env::temp_dir().join(format!("cortex-companion-b4-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("mkdir temp project");
    dir
}

#[test]
fn branch_from_git_dir_ref() {
    let dir = tmp_project("dir");
    fs::create_dir_all(dir.join(".git")).unwrap();
    fs::write(
        dir.join(".git/HEAD"),
        "ref: refs/heads/feature/obra08-streamB\n",
    )
    .unwrap();

    let be = InProcessBackend::open(&dir).expect("backend abre con .git dir");
    assert_eq!(
        be.current_branch().unwrap(),
        Some("feature/obra08-streamB".into())
    );

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn branch_from_git_file_worktree() {
    let dir = tmp_project("wt");
    let inner = dir.join("gitdir-custom");
    fs::create_dir_all(&inner).unwrap();
    fs::write(inner.join("HEAD"), "ref: refs/heads/wt-branch\n").unwrap();
    // '.git' como ARCHIVO con 'gitdir:' (layout de worktree).
    fs::write(dir.join(".git"), format!("gitdir: {}\n", inner.display())).unwrap();

    let be = InProcessBackend::open(&dir).expect("backend abre con .git file");
    assert_eq!(be.current_branch().unwrap(), Some("wt-branch".into()));

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn detached_head_yields_none() {
    let dir = tmp_project("detached");
    fs::create_dir_all(dir.join(".git")).unwrap();
    fs::write(
        dir.join(".git/HEAD"),
        "9f2a1c4dd0a0a1b2c3d4e5f6a7b8c9d0e1f2a3b4\n",
    )
    .unwrap();

    let be = InProcessBackend::open(&dir).expect("backend abre detached");
    assert_eq!(be.current_branch().unwrap(), None);

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn no_git_yields_none() {
    let dir = tmp_project("nogit");

    let be = InProcessBackend::open(&dir).expect("backend abre sin git");
    assert_eq!(be.current_branch().unwrap(), None);

    let _ = fs::remove_dir_all(&dir);
}
