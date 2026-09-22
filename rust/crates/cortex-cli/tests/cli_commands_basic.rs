//! Tests de los comandos triviales wireados: agent-guidelines,
//! install-skills y doctor (P12B-8 Task 2).
//!
//! Paridad byte-a-byte completa se valida en el gate
//! (`bench/parity/cli_golden_p12b.py` con normalización STUB_TABLE);
//! acá se fijan bytes exactos donde el oráculo es determinista sin
//! normalización y estructura/rc para doctor.

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

#[test]
fn agent_guidelines_matches_python_resource_plus_newline() {
    // Oráculo: typer.echo(content) = contenido crudo del recurso + "\n".
    let source = include_str!("../../../../cortex/agent_guidelines.md");
    let out = bin().arg("agent-guidelines").output().unwrap();
    assert!(out.status.success());
    assert_eq!(
        out.stdout,
        source
            .as_bytes()
            .iter()
            .copied()
            .chain(std::iter::once(b'\n'))
            .collect::<Vec<u8>>()
    );
}

#[test]
fn install_skills_lists_five_and_marks_already_exists_on_replay() {
    let tmp = tempfile::tempdir().unwrap();
    let dest = tmp.path().join("skills");
    let dest_str = dest.to_str().unwrap();

    let first = bin()
        .args(["install-skills", "--dest", dest_str])
        .output()
        .unwrap();
    assert!(first.status.success());
    let stdout = String::from_utf8_lossy(&first.stdout);
    let expected_first = format!(
        "✅ Installed 5 skills into {dest_str}/\n\
         \x20  • obsidian-markdown\n\
         \x20  • json-canvas\n\
         \x20  • obsidian-bases\n\
         \x20  • obsidian-cli\n\
         \x20  • defuddle\n"
    );
    assert_eq!(stdout, expected_first);

    let second = bin()
        .args(["install-skills", "--dest", dest_str])
        .output()
        .unwrap();
    assert!(second.status.success());
    let again = String::from_utf8_lossy(&second.stdout);
    assert!(again.contains("obsidian-markdown (already exists)"));
    assert!(again.starts_with(&format!("✅ Installed 5 skills into {dest_str}/")));
}

#[test]
fn doctor_empty_fixture_rc1_with_fail_lines_on_stderr() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_str().unwrap();

    let out = bin()
        .args(["doctor", "--project-root", root])
        .output()
        .unwrap();

    assert_eq!(out.status.code(), Some(1), "fixture vacío debe fallar");
    let stdout = String::from_utf8_lossy(&out.stdout);
    let stderr = String::from_utf8_lossy(&out.stderr);

    // Presentación contractual main.py: ok→stdout [OK], warn/info→stdout,
    // fail→stderr.
    assert!(stdout.contains("[OK] project_root: "), "stdout: {stdout}");
    assert!(
        stdout.contains("[WARN] cortex_workspace: "),
        "stub contractual visible como WARN: {stdout}"
    );
    assert!(stderr.contains("[FAIL] config_yaml: "), "stderr: {stderr}");
    assert!(stderr.contains("[FAIL] vault_dir: "));
    // Sin ANSI cuando la salida no es tty.
    assert!(!stdout.contains('\x1b'));
}

#[test]
fn doctor_unknown_flag_is_clap_error_exit2() {
    // Self-golden: los errores de args de subárboles wireados los produce
    // clap (no Typer); rc de usage error = 2 en ambos mundos.
    let out = bin().arg("doctor").arg("--no-existo").output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(err.contains("unexpected argument"), "stderr: {err}");
}

#[test]
fn mcp_stdio_server_discover_probe_handled_transparently() {
    use std::io::{BufRead, BufReader, Write};
    use std::process::Stdio;

    let mut child = bin()
        .args(["mcp-server", "--stdio"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn cortex-cli");

    let mut stdin = child.stdin.take().expect("child stdin");
    let stdout = child.stdout.take().expect("child stdout");
    let mut reader = BufReader::new(stdout);

    // 1. Enviar sonda server/discover de agy
    stdin
        .write_all(b"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{}}\n")
        .unwrap();
    stdin.flush().unwrap();

    let mut line1 = String::new();
    reader.read_line(&mut line1).unwrap();
    let val1: serde_json::Value = serde_json::from_str(&line1).unwrap();
    assert_eq!(val1["id"], 1);
    assert_eq!(val1["error"]["code"], -32601);

    // 2. Enviar initialize estándar
    stdin
        .write_all(b"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}\n")
        .unwrap();
    stdin.flush().unwrap();

    let mut line2 = String::new();
    reader.read_line(&mut line2).unwrap();
    let val2: serde_json::Value = serde_json::from_str(&line2).unwrap();
    assert_eq!(val2["id"], 2);
    assert_eq!(val2["result"]["serverInfo"]["name"], "cortex");

    // 3. Enviar notifications/initialized + tools/list
    stdin
        .write_all(b"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\",\"params\":{}}\n")
        .unwrap();
    stdin
        .write_all(b"{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\",\"params\":{}}\n")
        .unwrap();
    stdin.flush().unwrap();

    let mut line3 = String::new();
    reader.read_line(&mut line3).unwrap();
    let val3: serde_json::Value = serde_json::from_str(&line3).unwrap();
    assert_eq!(val3["id"], 3);
    let tools = val3["result"]["tools"].as_array().expect("tools array");
    assert_eq!(tools.len(), 32);

    drop(stdin);
    let status = child.wait().unwrap();
    assert!(status.success());
}

