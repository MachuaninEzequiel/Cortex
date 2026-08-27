//! Tests MITAD B — RUTA 2 (baja definitiva): `webgraph doctor` ×3 y
//! `webgraph serve` smoke ×2 + error sin config — wire nativo sobre
//! WorkspaceLayout + WebGraphConfig + create_app axum (P12B-2).
//!
//! TDD estricto: estos tests corrieron RED contra el estado previo
//! (`serve`/`doctor` caían en `WebgraphCmd::Other` ⇒ passthrough con
//! `CORTEX_BIN` inexistente ⇒ exit 127) y quedaron GREEN tras wirear.
//! Servicios reales + fixtures tmp, sin mocks ni grep de fuente. Los
//! bytes esperados fueron capturados del oráculo real
//! (`.venv/bin/cortex webgraph doctor`, cli.py).

use std::io::{Read, Write};
use std::net::TcpStream;
use std::process::{Child, Command, Output};
use std::time::Duration;

fn cli(root: &std::path::Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(args)
        .current_dir(root)
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .output()
        .expect("run cortex-cli")
}

fn stdout(o: &Output) -> String {
    String::from_utf8_lossy(&o.stdout).into_owned()
}

fn stderr(o: &Output) -> String {
    String::from_utf8_lossy(&o.stderr).into_owned()
}

/// Workspace nuevo: workspace.yaml + config.yaml + vault + memory/chroma.
fn fixture_completa(root: &std::path::Path) {
    let cortex = root.join(".cortex");
    std::fs::create_dir_all(cortex.join("vault")).unwrap();
    std::fs::create_dir_all(cortex.join("memory").join("chroma")).unwrap();
    std::fs::write(cortex.join("workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        cortex.join("config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
}

/// Workspace degradado: sin vault y sin store episódico.
fn fixture_degradada(root: &std::path::Path) {
    let cortex = root.join(".cortex");
    std::fs::create_dir_all(&cortex).unwrap();
    std::fs::write(cortex.join("workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        cortex.join("config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
}

fn http_get(port: u16, path: &str) -> u16 {
    use std::io::BufRead;
    let mut stream = TcpStream::connect(("127.0.0.1", port)).expect("connect");
    stream
        .write_all(
            format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                .as_bytes(),
        )
        .expect("write");
    let mut line = String::new();
    let mut reader = std::io::BufReader::new(stream);
    reader.read_line(&mut line).expect("read status line");
    let status: u16 = line
        .split_whitespace()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);
    // Drena el body para que el server no bloquee (keep-alive off ya).
    let mut buf = Vec::new();
    let _ = reader.read_to_end(&mut buf);
    status
}

fn free_port() -> u16 {
    let l = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    l.local_addr().unwrap().port()
}

fn wait_ready(port: u16, extra: &mut Child) -> u16 {
    for _ in 0..100 {
        // el proceso debe seguir vivo (no murió al arrancar)
        if let Ok(Some(_)) = extra.try_wait() {
            return 0;
        }
        if let Ok(status) = std::panic::catch_unwind(|| http_get(port, "/")) {
            if status != 0 {
                return status;
            }
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    0
}

// ---------------------------------------------------------------------------
// webgraph doctor
// ---------------------------------------------------------------------------

#[test]
fn doctor_fixture_completa_todo_ok() {
    let tmp = tempfile::tempdir().unwrap();
    fixture_completa(tmp.path());
    let out = cli(
        tmp.path(),
        &[
            "webgraph",
            "doctor",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(0), "{}", stderr(&out));
    let root_norm = tmp.path().to_string_lossy().replace("\\", "/");
    let expected = format!(
        "[OK] project_root: {root}\n\
         [OK] config_yaml: {root}/.cortex/config.yaml\n\
         [OK] vault_dir: {root}/.cortex/vault\n\
         [OK] episodic_store: {root}/.cortex/memory/chroma\n\
         [OK] webgraph_dependencies: ok\n\
         \n\
         WebGraph doctor passed.\n",
        root = root_norm
    );
    assert_eq!(stdout(&out), expected);
    assert_eq!(stderr(&out), "");
}

#[test]
fn doctor_fixture_degradada_fail_rc1() {
    let tmp = tempfile::tempdir().unwrap();
    fixture_degradada(tmp.path());
    let out = cli(
        tmp.path(),
        &[
            "webgraph",
            "doctor",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(1), "{}", stderr(&out));
    let root_norm = tmp.path().to_string_lossy().replace("\\", "/");
    // Líneas de checks van a stdout (igual que el oráculo); el resumen a stderr.
    let expected_out = format!(
        "[OK] project_root: {root}\n\
         [OK] config_yaml: {root}/.cortex/config.yaml\n\
         [FAIL] vault_dir: {root}/.cortex/vault\n\
         [FAIL] episodic_store: {root}/.cortex/memory/chroma\n\
         [OK] webgraph_dependencies: ok\n",
        root = root_norm
    );
    assert_eq!(stdout(&out), expected_out);
    assert_eq!(
        stderr(&out),
        "\nWebGraph doctor found blocking issues. Fix the failing checks and retry.\n"
    );
}

#[test]
fn doctor_sin_config_falla_igual_que_oraculo() {
    // Fixture con .cortex/workspace.yaml de layout 2 pero SIN config.yaml ⇒
    // el oráculo reporta config_yaml FAIL (discover nuevo layout sin config
    // inexistente no es lo mismo que ausencia de proyecto; ver cli.py).
    let tmp = tempfile::tempdir().unwrap();
    let cortex = tmp.path().join(".cortex");
    std::fs::create_dir_all(&cortex).unwrap();
    std::fs::write(cortex.join("workspace.yaml"), "layout_version: 2\n").unwrap();
    let out = cli(
        tmp.path(),
        &[
            "webgraph",
            "doctor",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(1), "{}", stderr(&out));
    let root_norm = tmp.path().to_string_lossy().replace("\\", "/");
    assert!(
        stdout(&out).contains("[FAIL] config_yaml:"),
        "{}",
        stdout(&out)
    );
    assert!(
        stdout(&out).contains("[FAIL] vault_dir:"),
        "{}",
        stdout(&out)
    );
    assert!(
        stdout(&out).contains("[FAIL] episodic_store:"),
        "{}",
        stdout(&out)
    );
    assert_eq!(
        stderr(&out),
        "\nWebGraph doctor found blocking issues. Fix the failing checks and retry.\n"
    );
    let _ = root_norm;
}

// ---------------------------------------------------------------------------
// webgraph serve — smoke acotado (no-terminal, patrón P12B-2)
// ---------------------------------------------------------------------------

#[test]
fn serve_smoke_responde_200_en_index() {
    let tmp = tempfile::tempdir().unwrap();
    fixture_completa(tmp.path());
    let port = free_port();
    let port_s = port.to_string();
    let mut child = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args([
            "webgraph",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            &port_s,
            "--no-open",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .current_dir(tmp.path())
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .spawn()
        .expect("spawn serve");

    let status = wait_ready(port, &mut child);
    assert_eq!(status, 200, "GET / debe responder 200 (smoke)");
    child.kill().expect("kill serve");
    let _ = child.wait();
}

#[test]
fn serve_sin_config_error_rc1_sin_abrir_puerto() {
    let tmp = tempfile::tempdir().unwrap();
    // Sin .cortex/config.yaml: el oráculo falla con el mensaje canónico
    // (misma _require_config que export). rc 1, sin levantar server.
    let out = cli(
        tmp.path(),
        &[
            "webgraph",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--no-open",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(1), "{}", stderr(&out));
    let msg = format!(
        "Config not found at {}. Run `cortex setup agent` first or pass a valid --project-root.",
        tmp.path().join(".cortex").join("config.yaml").display()
    );
    assert_eq!(stderr(&out), format!("{msg}\n"));
    assert_eq!(stdout(&out), "");
}
