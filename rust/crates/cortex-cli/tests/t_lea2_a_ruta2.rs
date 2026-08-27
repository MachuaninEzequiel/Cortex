//! Tests MITAD A — RUTA 2 (baja definitiva): `autopilot doctor` nativo
//! (6 checks, payload EXACTO del oráculo `cortex.autopilot.doctor`) +
//! verificación Fase 04 de `autopilot install/uninstall` (rechazo nativo,
//! NUNCA passthrough a Python).
//!
//! TDD estricto: estos tests corrieron RED contra el estado previo
//! (`doctor`/`install`/`uninstall` caían en `AutopilotCmd::Other` ⇒
//! passthrough con `CORTEX_BIN` inexistente ⇒ exit 127) y quedaron GREEN
//! tras wirear. Servicios reales + fixtures tmp, sin mocks ni grep de
//! fuente. Los bytes esperados fueron capturados del oráculo real
//! (`python -m cortex.cli.main autopilot doctor` , Fase 04).

use std::path::Path;
use std::process::{Command, Output};

fn cli(root: &Path, args: &[&str]) -> Output {
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

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SESSION_YAML: &str = r#"session_id: 2026-08-25_demo
spec_path: vault/specs/demo.md
spec_summary: demo
start_commit: '0000000000000000000000000000000000000000'
start_branch: ''
opened_at: '2026-08-26T22:24:52.720137Z'
status: open
mode: unknown
checkpoints: []
verification_results: []
tasks: []
closed_at: null
end_commit: null
documenter_decision: null
session_note_path: null
adrs_created: []
"#;

const CLAUDE_SETTINGS: &str = r#"{"hooks": {"PostToolUse": [{"type": "command", "command": "cortex session checkpoint --source ide-hook", "_cortex_managed": true}]}}"#;

/// Fixture completo: workspace nuevo + sesión abierta en disco + hook
/// claude-code instalado ⇒ los 6 checks del doctor en OK.
fn full_fixture() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex/sessions")).unwrap();
    std::fs::create_dir_all(root.join(".claude")).unwrap();
    std::fs::write(root.join(".cortex/workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        root.join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
    std::fs::write(
        root.join(".cortex/sessions/2026-08-25_demo.yaml"),
        SESSION_YAML,
    )
    .unwrap();
    std::fs::write(root.join(".claude/settings.json"), CLAUDE_SETTINGS).unwrap();
    tmp
}

/// Fixture degradado: workspace nuevo pero SIN sesiones y SIN hooks ⇒ el
/// check `hooks` falla (`ok=false`); `sessions_dir` se auto-repara con
/// mkdir como el oráculo (rc sigue siendo 0).
fn degraded_fixture() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(root.join(".cortex/workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        root.join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
    tmp
}

// ---------------------------------------------------------------------------
// doctor — texto (payload EXACTO del oráculo)
// ---------------------------------------------------------------------------

#[test]
fn doctor_full_text_matches_oracle_parity() {
    let tmp = full_fixture();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    assert_eq!(out.status.code(), Some(0), "stderr: {}", stderr(&out));
    let r = root.display().to_string();
    let expected = format!(
        "project_root: {r}\n\
         ok: True\n\
         checks: [{{'name': 'config', 'ok': True, 'detail': 'mode=assist, profile=fast_code', 'action': ''}}, {{'name': 'sessions_dir', 'ok': True, 'detail': '{r}/.cortex/sessions', 'action': ''}}, {{'name': 'adapters', 'ok': True, 'detail': \"Known IDE adapters (cortex.session.hooks): ['claude-code', 'cursor', 'opencode', 'pi']\", 'action': ''}}, {{'name': 'hooks', 'ok': True, 'detail': \"Installed adapters: ['claude-code']\", 'action': ''}}, {{'name': 'last_finish', 'ok': True, 'detail': 'Session 2026-08-25_demo still OPEN — finish or abandon when ready', 'action': ''}}, {{'name': 'service', 'ok': True, 'detail': 'AutopilotService.from_project_root wired OK', 'action': ''}}]\n\
         warnings: []\n"
    );
    assert_eq!(stdout(&out), expected);
}

#[test]
fn doctor_degraded_hooks_fail_ok_false_rc0_like_oracle() {
    let tmp = degraded_fixture();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    // El oráculo NO sale con rc 1 ante checks fallidos (Fase 04): rc=0.
    assert_eq!(out.status.code(), Some(0), "stderr: {}", stderr(&out));
    let r = root.display().to_string();
    let expected = format!(
        "project_root: {r}\n\
         ok: False\n\
         checks: [{{'name': 'config', 'ok': True, 'detail': 'mode=assist, profile=fast_code', 'action': ''}}, {{'name': 'sessions_dir', 'ok': True, 'detail': '{r}/.cortex/sessions', 'action': ''}}, {{'name': 'adapters', 'ok': True, 'detail': \"Known IDE adapters (cortex.session.hooks): ['claude-code', 'cursor', 'opencode', 'pi']\", 'action': ''}}, {{'name': 'hooks', 'ok': False, 'detail': 'No Cortex session hooks detected', 'action': 'Run `cortex session hooks install --ide <name>`.'}}, {{'name': 'last_finish', 'ok': True, 'detail': 'No sessions on disk yet', 'action': ''}}, {{'name': 'service', 'ok': True, 'detail': 'AutopilotService.from_project_root wired OK', 'action': ''}}]\n\
         warnings: ['No Cortex session hooks detected']\n"
    );
    assert_eq!(stdout(&out), expected);
}

#[test]
fn doctor_sessions_dir_self_heals_like_oracle() {
    // El oráculo hace `sessions.mkdir(parents=True, exist_ok=True)` en el
    // check sessions_dir: paridad también de efecto lateral.
    let tmp = degraded_fixture();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    assert_eq!(out.status.code(), Some(0));
    assert!(root.join(".cortex/sessions").is_dir());
}

#[test]
fn doctor_explicit_project_root_from_other_cwd() {
    let tmp = full_fixture();
    let root = tmp.path();
    let elsewhere = tempfile::tempdir().unwrap();
    let out = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args([
            "autopilot",
            "doctor",
            "--project-root",
            &root.display().to_string(),
        ])
        .current_dir(elsewhere.path())
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    let s = stdout(&out);
    assert!(s.starts_with(&format!("project_root: {}\n", root.display())));
    assert!(s.contains("ok: True\n"));
}

#[test]
fn doctor_last_finish_tie_keeps_first_like_python_max() {
    // Paridad de empate del check `last_finish`: el oráculo hace
    // `latest = max(records, key=lambda r: r.opened_at)` (doctor.py) y
    // Python devuelve el PRIMER máximo ante opened_at idénticos; el nativo
    // replica eso con un fold `>=` (no `>`, que ganaría el último). El
    // orden de lista es determinista en ambos lados (archivos ordenados
    // por nombre) ⇒ con `2026-08-25_aa-first.yaml` <
    // `2026-08-25_bb-second.yaml` (slug sin guión bajo: patrón
    // `YYYY-MM-DD_<slug>`) y el mismo opened_at, el vencedor debe ser la
    // sesión del archivo `aa-first` (id "2026-08-25_aa-first"), no la del
    // `bb-second` ("2026-08-25_bb-second"). Con `>` el test fallaría.
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex/sessions")).unwrap();
    std::fs::write(root.join(".cortex/workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        root.join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
    for (file, sid) in [
        ("2026-08-25_aa-first.yaml", "2026-08-25_aa-first"),
        ("2026-08-25_bb-second.yaml", "2026-08-25_bb-second"),
    ] {
        let yaml = SESSION_YAML.replace("2026-08-25_demo", sid);
        std::fs::write(root.join(".cortex/sessions").join(file), yaml).unwrap();
    }
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    assert_eq!(out.status.code(), Some(0), "stderr: {}", stderr(&out));
    let s = stdout(&out);
    assert!(
        s.contains("Session 2026-08-25_aa-first still OPEN — finish or abandon when ready"),
        "stdout: {s}"
    );
    assert!(
        !s.contains("Session 2026-08-25_bb-second still OPEN"),
        "empate debe ganar el primer máximo (aa-first), stdout: {s}"
    );
}

// ---------------------------------------------------------------------------
// doctor — --json (payload EXACTO del oráculo)
// ---------------------------------------------------------------------------

#[test]
fn doctor_full_json_matches_oracle_parity() {
    let tmp = full_fixture();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--json",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    assert_eq!(out.status.code(), Some(0), "stderr: {}", stderr(&out));
    let r = root.display().to_string();
    let expected = format!(
        "{{\n  \"project_root\": \"{r}\",\n  \"ok\": true,\n  \"checks\": [\n    {{\n      \"name\": \"config\",\n      \"ok\": true,\n      \"detail\": \"mode=assist, profile=fast_code\",\n      \"action\": \"\"\n    }},\n    {{\n      \"name\": \"sessions_dir\",\n      \"ok\": true,\n      \"detail\": \"{r}/.cortex/sessions\",\n      \"action\": \"\"\n    }},\n    {{\n      \"name\": \"adapters\",\n      \"ok\": true,\n      \"detail\": \"Known IDE adapters (cortex.session.hooks): ['claude-code', 'cursor', 'opencode', 'pi']\",\n      \"action\": \"\"\n    }},\n    {{\n      \"name\": \"hooks\",\n      \"ok\": true,\n      \"detail\": \"Installed adapters: ['claude-code']\",\n      \"action\": \"\"\n    }},\n    {{\n      \"name\": \"last_finish\",\n      \"ok\": true,\n      \"detail\": \"Session 2026-08-25_demo still OPEN \\u2014 finish or abandon when ready\",\n      \"action\": \"\"\n    }},\n    {{\n      \"name\": \"service\",\n      \"ok\": true,\n      \"detail\": \"AutopilotService.from_project_root wired OK\",\n      \"action\": \"\"\n    }}\n  ],\n  \"warnings\": []\n}}\n"
    );
    assert_eq!(stdout(&out), expected);
}

#[test]
fn doctor_degraded_json_ok_false_with_warnings() {
    let tmp = degraded_fixture();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "autopilot",
            "doctor",
            "--json",
            "--project-root",
            &root.display().to_string(),
        ],
    );
    assert_eq!(out.status.code(), Some(0), "stderr: {}", stderr(&out));
    let s = stdout(&out);
    assert!(s.contains("\"ok\": false"));
    assert!(s.contains("\"name\": \"hooks\",\n      \"ok\": false,\n      \"detail\": \"No Cortex session hooks detected\",\n      \"action\": \"Run `cortex session hooks install --ide <name>`.\""));
    assert!(s.contains("\"warnings\": [\n    \"No Cortex session hooks detected\"\n  ]"));
}

// ---------------------------------------------------------------------------
// install / uninstall — rechazo nativo equivalente al oráculo (Fase 04)
// ---------------------------------------------------------------------------

#[test]
fn install_rejected_natively_like_oracle() {
    let tmp = tempfile::tempdir().unwrap();
    // CORTEX_BIN inexistente ⇒ si cayera al passthrough saldría 127; el
    // rechazo nativo debe dar rc=2 sin ejecutar Python.
    let out = cli(tmp.path(), &["autopilot", "install", "--ide", "pi"]);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(
        stderr(&out),
        "No such command 'install'.\n",
        "stdout: {}",
        stdout(&out)
    );
}

#[test]
fn uninstall_rejected_natively_like_oracle() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["autopilot", "uninstall", "--ide", "pi"]);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(
        stderr(&out),
        "No such command 'uninstall'.\n",
        "stdout: {}",
        stdout(&out)
    );
}

#[test]
fn unknown_autopilot_subcommand_still_passthrough() {
    // Solo install/uninstall se rechazan nativamente; el resto de
    // subcomandos desconocidos sigue el flujo de passthrough intacto.
    let tmp = tempfile::tempdir().unwrap();
    let out = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(["autopilot", "bogus"])
        .current_dir(tmp.path())
        .env("CORTEX_BIN", "/bin/echo")
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(stdout(&out), "autopilot bogus\n");
}
