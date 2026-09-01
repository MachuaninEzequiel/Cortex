//! Gate del port `compute_diff` (oráculo session/service.py:476) +
//! `SessionService` clonable (la TUI carga el detalle en un thread).

use cortex_app::session::service::SessionService;
use cortex_app::session::{SessionStorage, GITLESS_COMMIT_PLACEHOLDER};
use std::path::Path;
use std::process::Command;

fn git(root: &Path, args: &[&str]) -> String {
    let out = Command::new("git")
        .args(args)
        .current_dir(root)
        .output()
        .expect("git disponible en el entorno de tests (lo usan los fixtures e2e)");
    assert!(
        out.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8_lossy(&out.stdout).trim().to_string()
}

/// Repo git real de 2 commits: `base` (a.md) y `cambio` (+linea nueva).
/// Devuelve (dir vivo, hash base).
fn repo_dos_commits() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("repo");
    std::fs::create_dir_all(&root).unwrap();
    git(&root, &["init", "-q"]);
    git(&root, &["config", "user.email", "t@cortex.test"]);
    git(&root, &["config", "user.name", "cortex tests"]);
    std::fs::write(root.join("a.md"), "# base\n").unwrap();
    git(&root, &["add", "-A"]);
    git(&root, &["commit", "-qm", "base"]);
    let base = git(&root, &["rev-parse", "HEAD"]);
    std::fs::write(root.join("a.md"), "# base\n+linea nueva\n").unwrap();
    git(&root, &["add", "-A"]);
    git(&root, &["commit", "-qm", "cambio"]);
    (dir, base)
}

fn service_for(root: &Path) -> SessionService {
    let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
    SessionService::new(storage, root)
}

/// Fija `start_commit` de la sesión abierta por YAML directo (determinista).
fn fijar_start_commit(root: &Path, id: &str, start_commit: &str) {
    let p = root
        .join(".cortex")
        .join("sessions")
        .join(format!("{id}.yaml"));
    let text = std::fs::read_to_string(&p).unwrap();
    let idx = text.find("start_commit:").unwrap() + "start_commit:".len();
    let end = text[idx..].find('\n').map(|e| idx + e).unwrap();
    std::fs::write(
        &p,
        format!("{} {}{}", &text[..idx], start_commit, &text[end..]),
    )
    .unwrap();
}

#[test]
fn diff_entre_start_commit_y_head_en_sesion_abierta() {
    let (_dir, base) = repo_dos_commits();
    let root = _dir.path().join("repo");
    let svc = service_for(&root);
    svc.open("2026-08-30_diff", "vault/specs/x.md", "sesión para diff")
        .unwrap();
    fijar_start_commit(&root, "2026-08-30_diff", &base);
    // Sesión abierta ⇒ diff hasta HEAD.
    let diff = svc.compute_diff("2026-08-30_diff").unwrap();
    assert!(diff.contains("+linea nueva"), "diff sin la línea: {diff}");
    assert!(diff.contains('-'), "diff debería tener contexto removido");
}

#[test]
fn diff_en_sesion_cerrada_usa_end_commit_head() {
    let (_dir, base) = repo_dos_commits();
    let root = _dir.path().join("repo");
    let svc = service_for(&root);
    let id = "2026-08-30_cerrada";
    svc.open(id, "vault/specs/x.md", "cerrada").unwrap();
    svc.close(
        id,
        cortex_app::session::SessionStatus::Closed,
        cortex_app::session::SessionStatus::Closed,
        None, // session_note_path
        vec![],
    )
    .unwrap();
    fijar_start_commit(&root, id, &base);
    // El close nativo fija end_commit = HEAD (commit 2, con la línea):
    // el diff de la cerrada llega igual que el de la abierta.
    let diff = svc.compute_diff(id).unwrap();
    assert!(diff.contains("+linea nueva"), "diff sin la línea: {diff:?}");
    // end_commit quedó persistido (comportamiento del oráculo).
    let rec = svc.get(id).unwrap();
    assert!(rec.end_commit.is_some());
}

#[test]
fn diff_gitless_devuelve_vacio() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("repo");
    std::fs::create_dir_all(&root).unwrap(); // sin git
    let svc = service_for(&root);
    let id = "2026-08-30_gitless";
    svc.open(id, "vault/specs/x.md", "gitless").unwrap();
    fijar_start_commit(&root, id, GITLESS_COMMIT_PLACEHOLDER);
    assert_eq!(svc.compute_diff(id).unwrap(), "");
}

#[test]
fn diff_sesion_inexistente_es_error() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("repo");
    std::fs::create_dir_all(&root).unwrap();
    let err = service_for(&root).compute_diff("no_existe").unwrap_err();
    assert!(err.contains("no_existe"), "{err}");
}

#[test]
fn service_es_clonable() {
    let dir = tempfile::tempdir().unwrap();
    let svc = service_for(dir.path());
    let clone = svc.clone();
    let id = "2026-08-30_c";
    svc.open(id, "vault/specs/x.md", "c").unwrap();
    let _ = id;
    assert!(clone.get("2026-08-30_c").is_ok());
}
