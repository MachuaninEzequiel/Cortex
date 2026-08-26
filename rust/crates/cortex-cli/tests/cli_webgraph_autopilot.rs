//! Tests de webgraph export + autopilot preflight (P12B-8 Task 7).

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

fn make_l7() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::create_dir_all(root.join("vault/sessions")).unwrap();
    for i in 0..3 {
        std::fs::write(
            root.join(format!("vault/specs/s{i}.md")),
            format!("# s{i}\n"),
        )
        .unwrap();
    }
    for i in 0..2 {
        std::fs::write(
            root.join(format!("vault/sessions/x{i}.md")),
            format!("# x{i}\n"),
        )
        .unwrap();
    }
    std::fs::create_dir_all(root.join(".github/workflows")).unwrap();
    std::fs::write(root.join(".mcp.json"), "{}\n").unwrap();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(
        root.join(".cortex/org.yaml"),
        "schema_version: 1\norganization:\n  name: Acme Org\nmemory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n",
    )
    .unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
    tmp
}

#[test]
fn pf_security_request_json_byte_parity() {
    let tmp = tempfile::tempdir().unwrap();
    let req = "implementar autenticación completa con JWT y refresh tokens";
    let py_out = Command::new("/bin/sh")
        .arg("-c")
        .arg(format!(
            "cd {} && CORTEX_PY=1 cortex-cli autopilot preflight --request \"{}\" --json",
            tmp.path().display(),
            req
        ))
        .output();
    // El oráculo real se valida en el gate; acá fijamos los bytes nativos.
    let out = bin()
        .current_dir(tmp.path())
        .args(["autopilot", "preflight", "--request", req, "--json"])
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "{\n  \"task_type\": \"security\",\n  \"confidence\": 0.7,\n  \"reason\": \"Security keywords in request\",\n  \"suggested_complexity\": \"deep\"\n}\n"
    );
    let _ = py_out;
}

#[test]
fn pf_noop_tie_breaks_like_python_first_max() {
    // "qué hora es": sin candidatos >0.3 ⇒ primer máximo (ambiguous noop,
    // razón "Request appears sufficiently specific"). Regresión del tie-break
    // max_by (último) vs Python max (primero).
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .current_dir(tmp.path())
        .args([
            "autopilot",
            "preflight",
            "--request",
            "qué hora es",
            "--json",
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("\"task_type\": \"noop\""));
    assert!(stdout.contains("\"confidence\": 0.0"));
    assert!(stdout.contains("\"reason\": \"Request appears sufficiently specific\""));
}

#[test]
fn pf_text_mode_float_repr_has_trailing_zero() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .current_dir(tmp.path())
        .args(["autopilot", "preflight", "--request", "qué hora es"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.starts_with("task_type: noop\nconfidence: 0.0\n"),
        "{stdout}"
    );
}

#[test]
fn wg_export_without_config_matches_python_error() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .current_dir(tmp.path())
        .args(["webgraph", "export"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&out.stderr),
        format!(
            "Config not found at {}. Run `cortex setup agent` first or pass a valid --project-root.\n",
            tmp.path().join(".cortex/config.yaml").display()
        )
    );
}

#[test]
fn wg_export_empty_fixture_writes_snapshot_and_echoes_path() {
    let tmp = make_l7();
    // Vaciar el vault para que el embedder nunca se invoque (determinismo).
    std::fs::remove_dir_all(tmp.path().join("vault/specs")).unwrap();
    std::fs::remove_dir_all(tmp.path().join("vault/sessions")).unwrap();

    let out = bin()
        .current_dir(tmp.path())
        .args(["webgraph", "export", "--no-cache"])
        .env("USER", "tester")
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    let expected_suffix = "/.cortex/webgraph/cache/snapshot-hybrid.json\n";
    assert!(stdout.ends_with(expected_suffix), "stdout: {stdout}");

    let snap_path = tmp
        .path()
        .join(".cortex/webgraph/cache/snapshot-hybrid.json");
    let body = std::fs::read_to_string(&snap_path).unwrap();
    // Orden pydantic + legend al final; contenido determinista salvo
    // fingerprint/generated_at.
    assert!(body.starts_with("{\n  \"version\": \"2.0\",\n  \"fingerprint\": \""));
    assert!(body.contains("\"nodes\": [],\n  \"edges\": [],\n  \"legend\": {"));
    assert!(body.trim_end().ends_with('}'));
}

#[test]
fn wg_serve_subcommand_delegates_to_python() {
    // serve no está wireado: external_subcommand ⇒ passthrough.
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/echo")
        .args(["webgraph", "serve", "--port", "9"])
        .output()
        .unwrap();
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "webgraph serve --port 9\n"
    );
}
