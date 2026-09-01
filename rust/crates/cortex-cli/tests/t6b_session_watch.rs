//! Gate CIERRE T6-b — `cortex session watch` / `session tui` nativos.
//!
//! Contrato (brief T6-b): en consola no-interactiva (CI: stdout es pipe) el
//! brazo nativo emite un snapshot único del render ratatui del mismo
//! `SessionService` que alimenta `session list --json` y sale rc 0. Los ids
//! y la marca de activa del snapshot deben coincidir con el fixture real;
//! con fixture vacío (o filtro sin resultados) emite el mensaje contractual
//! "(no sessions on disk)". Integración con binario real + fixtures reales
//! en tmp: sin mocks ni grep de fuente.

use std::path::{Path, PathBuf};
use std::process::Command;

use cortex_app::session::service::SessionService;
use cortex_app::session::{SessionStatus, SessionStorage};

fn bin() -> Command {
    let mut c = Command::new(env!("CARGO_BIN_EXE_cortex-cli"));
    // Hermético: el brazo nativo decide solo; sin rollback heredado del host.
    c.env_remove("CORTEX_PY");
    c.env_remove("CORTEX_BIN");
    c
}

/// Raíz de proyecto real en tmp con marca de layout nuevo (`.cortex/config.yaml`)
/// para que `WorkspaceLayout::discover` se detenga en el fixture.
fn fixture_root(tag: &str) -> (tempfile::TempDir, PathBuf) {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join(tag);
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(root.join(".cortex").join("config.yaml"), "{}\n").unwrap();
    (tmp, root)
}

fn service_at(root: &Path) -> SessionService {
    let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
    SessionService::new(storage, root)
}

fn seed_two_open(root: &Path) {
    let svc = service_at(root);
    svc.open(
        "2026-05-16_demo",
        "vault/specs/2026-05-16_demo.md",
        "Primera demo",
    )
    .unwrap();
    svc.open(
        "2026-05-17_segunda",
        "vault/specs/2026-05-17_segunda.md",
        "Segunda demo",
    )
    .unwrap();
}

#[test]
fn watch_snapshot_no_tty_paridad_con_list_json() {
    let (_tmp, root) = fixture_root("parity");
    seed_two_open(&root);

    let watch = bin()
        .args(["session", "watch", "--project-root"])
        .arg(&root)
        .output()
        .unwrap();
    assert_eq!(
        watch.status.code(),
        Some(0),
        "rc != 0; stderr: {}",
        String::from_utf8_lossy(&watch.stderr)
    );

    // Misma fuente de datos que `session list --json` sobre el mismo fixture.
    let json = bin()
        .args(["session", "list", "--json", "--project-root"])
        .arg(&root)
        .output()
        .unwrap();
    assert!(json.status.success());
    let records: Vec<serde_json::Value> = serde_json::from_slice(&json.stdout).unwrap();

    let stdout = String::from_utf8_lossy(&watch.stdout);
    for rec in &records {
        let id = rec["session_id"].as_str().unwrap();
        assert!(stdout.contains(id), "falta id {id} en el snapshot");
    }
    // Marca de activa presente (la última abierta es la activa del servicio).
    assert!(stdout.contains('●'), "falta la marca de sesión activa");
}

#[test]
fn watch_y_tui_comparten_entrypoint_y_filtro_status() {
    let (_tmp, root) = fixture_root("filter");
    let svc = service_at(&root);
    svc.open(
        "2026-05-16_demo",
        "vault/specs/2026-05-16_demo.md",
        "Primera demo",
    )
    .unwrap();
    svc.close(
        "2026-05-16_demo",
        SessionStatus::Closed,
        SessionStatus::Closed,
        None,
        vec![],
    )
    .unwrap();

    // `tui` == `watch`: con filtro open no quedan sesiones ⇒ mensaje contractual.
    let tui = bin()
        .args(["session", "tui", "--project-root"])
        .arg(&root)
        .args(["--status", "open"])
        .output()
        .unwrap();
    assert_eq!(
        tui.status.code(),
        Some(0),
        "rc != 0; stderr: {}",
        String::from_utf8_lossy(&tui.stderr)
    );
    let stdout = String::from_utf8_lossy(&tui.stdout);
    assert!(
        stdout.contains("(no sessions on disk)"),
        "mensaje vacío ausente: {stdout}"
    );

    // Sin filtro la cerrada aparece con su status en la tabla.
    let watch = bin()
        .args(["session", "watch", "--project-root"])
        .arg(&root)
        .output()
        .unwrap();
    assert_eq!(watch.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&watch.stdout);
    assert!(stdout.contains("2026-05-16_demo"), "{stdout}");
    assert!(stdout.contains("closed"), "{stdout}");
}

#[test]
fn watch_vacio_fixture_sin_sesiones() {
    let (_tmp, root) = fixture_root("empty");
    let out = bin()
        .args(["session", "watch", "--project-root"])
        .arg(&root)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("(no sessions on disk)"),
        "mensaje vacío ausente: {stdout}"
    );
}
