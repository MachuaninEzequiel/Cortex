//! Tests MITAD A — RUTA 1 (baja definitiva): `session task` ×5, `session
//! hooks` ×4, `remember`, `forget` — wire nativo contra stubs/passthrough.
//!
//! TDD estricto: estos tests corrieron RED contra los stubs del paso 0
//! (los comandos derivaban a `fallback::passthrough` con `CORTEX_BIN`
//! apuntando a un binario inexistente ⇒ exit 127) y quedaron GREEN tras
//! wirear. Servicios reales + fixtures en tmp, sin mocks ni grep de fuente.

use std::process::{Command, Output};
use std::time::SystemTime;

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
tasks:
- id: T1
  description: Primera tarea con una descripcion razonable
  files_in_scope:
  - a.py
  - b.py
  - c.py
  - d.py
  depends_on: []
  status: pending
  completed_at: null
  checkpoint_index: null
  note: ''
- id: T1.2
  description: Sub tarea
  files_in_scope:
  - x.py
  depends_on: []
  status: done
  completed_at: '2026-08-26T22:25:00.000000Z'
  checkpoint_index: null
  note: ''
closed_at: null
end_commit: null
documenter_decision: null
session_note_path: null
adrs_created: []
"#;

fn session_fixture() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(tmp.path().join(".cortex/sessions")).unwrap();
    std::fs::write(
        tmp.path().join(".cortex/workspace.yaml"),
        "layout_version: 2\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\nllm:\n  provider: openai\n  model: gpt-4o\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/sessions/2026-08-25_demo.yaml"),
        SESSION_YAML,
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/sessions/active.txt"),
        "2026-08-25_demo\n",
    )
    .unwrap();
    tmp
}

fn memory_fixture() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(tmp.path().join(".cortex/memory")).unwrap();
    std::fs::create_dir_all(tmp.path().join(".cortex/vault/specs")).unwrap();
    std::fs::write(
        tmp.path().join(".cortex/workspace.yaml"),
        "layout_version: 2\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\nllm:\n  provider: openai\n  model: gpt-4o\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/vault/specs/auth.md"),
        "---\ntitle: Auth\ndoc_type: spec\nstatus: draft\n---\nJWT authentication\n",
    )
    .unwrap();
    let fila = |id: &str, doc: &str, mtype: &str, ts: &str| {
        format!(
            "{{\"id\": \"{id}\", \"document\": \"{doc}\", \"meta\": {{\"id\": \"{id}\", \"memory_type\": \"{mtype}\", \"tags\": \"[]\", \"files\": \"[]\", \"timestamp\": \"{ts}\", \"metadata_json\": \"{{}}\"}}, \"embedding\": [0.1, 0.2, 0.3]}}\n"
        )
    };
    std::fs::write(
        tmp.path().join(".cortex/memory/episodic_export.jsonl"),
        format!(
            "{}  {}",
            fila(
                "mem_aaaa1111",
                "Implementamos login con JWT",
                "session",
                "2026-05-10T12:00:00+00:00",
            ),
            fila(
                "mem_bbbb2222",
                "Refactor del modulo de pagos en Rust",
                "session",
                "2026-05-11T12:00:00+00:00",
            ),
        ),
    )
    .unwrap();
    tmp
}

fn assert_native(o: &Output, what: &str) {
    assert!(
        o.status.success(),
        "{what}: rc={:?} stderr={}",
        o.status.code(),
        stderr(o),
    );
}

// ---------------------------------------------------------------------------
// session task ×5
// ---------------------------------------------------------------------------

#[test]
fn session_task_list_native_texto_y_json() {
    let tmp = session_fixture();
    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "list",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_native(&o, "task list texto");
    let out = stdout(&o);
    assert!(out.contains("T1"), "debe listar T1: {out}");
    assert!(out.contains("pending"), "debe listar estado: {out}");
    assert!(out.contains("a.py, b.py, c.py (+1)"), "files join: {out}");

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "list",
            "--status",
            "done",
            "--json",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_native(&o, "task list --json");
    let out = stdout(&o);
    assert!(out.contains("\"id\": \"T1.2\""), "done json: {out}");
    assert!(out.contains("\"status\": \"done\""), "done json: {out}");
    assert!(!out.contains("\"id\": \"T1\","), "T1 es pending: {out}");
}

#[test]
fn session_task_updates_native() {
    let tmp = session_fixture();
    let root = tmp.path().to_str().unwrap();

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "done",
            "T1",
            "--note",
            "primer fix",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "task done");
    assert_eq!(stdout(&o), "T1 → done\n");

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "in-progress",
            "T1",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "task in-progress");
    assert_eq!(stdout(&o), "T1 → in-progress\n");

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "skip",
            "T1",
            "--reason",
            "sin contexto",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "task skip");
    assert_eq!(stdout(&o), "T1 → skipped\n");

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "block",
            "T1",
            "--reason",
            "depende de T2",
            "--json",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "task block --json");
    assert_eq!(
        stdout(&o),
        "{\"session_id\": \"2026-08-25_demo\", \"task_id\": \"T1\", \"status\": \"blocked\"}\n"
    );
}

#[test]
fn session_task_errores_native() {
    let tmp = session_fixture();
    let root = tmp.path().to_str().unwrap();

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "list",
            "--session-id",
            "2099-01-01_nope",
            "--project-root",
            root,
        ],
    );
    assert_eq!(o.status.code(), Some(1));
    assert_eq!(stderr(&o).trim(), "Session not found: 2099-01-01_nope");

    let o = cli(
        tmp.path(),
        &["session", "task", "done", "T99", "--project-root", root],
    );
    assert_eq!(o.status.code(), Some(1));
    assert_eq!(
        stderr(&o).trim(),
        "Task id 'T99' not found in session '2026-08-25_demo'"
    );

    let o = cli(
        tmp.path(),
        &[
            "session",
            "task",
            "list",
            "--status",
            "bogus",
            "--project-root",
            root,
        ],
    );
    assert_eq!(o.status.code(), Some(1));
    assert_eq!(
        stderr(&o).trim(),
        "Invalid --status 'bogus'. Must be one of: pending, in-progress, done, skipped, blocked"
    );
}

// ---------------------------------------------------------------------------
// session hooks ×4
// ---------------------------------------------------------------------------

#[test]
fn session_hooks_list_native() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_str().unwrap();

    let o = cli(
        tmp.path(),
        &["session", "hooks", "list", "--project-root", root],
    );
    assert_native(&o, "hooks list");
    let out = stdout(&o);
    for ide in ["claude-code", "cursor", "opencode", "pi"] {
        assert!(out.contains(ide), "hooks list debe incluir {ide}: {out}");
    }
    assert!(out.contains("✓"), "supported ✓: {out}");

    let o = cli(
        tmp.path(),
        &["session", "hooks", "list", "--json", "--project-root", root],
    );
    assert_native(&o, "hooks list --json");
    let out = stdout(&o);
    assert!(out.contains("\"ide\": \"pi\""), "hooks json: {out}");
    assert!(out.contains("\"supported\": true"), "hooks json: {out}");
}

#[test]
fn session_hooks_install_status_uninstall_native() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_str().unwrap();

    let o = cli(
        tmp.path(),
        &[
            "session",
            "hooks",
            "install",
            "--ide",
            "pi",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "hooks install");
    assert!(stdout(&o).starts_with("✓ pi:"), "{}", stdout(&o));
    let justfile = tmp.path().join("justfile");
    assert!(justfile.exists(), "justfile creado");
    assert!(
        std::fs::read_to_string(&justfile)
            .unwrap()
            .contains("cortex-checkpoint"),
        "recetas instaladas"
    );

    let o = cli(
        tmp.path(),
        &[
            "session",
            "hooks",
            "status",
            "--ide",
            "pi",
            "--json",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "hooks status --json");
    let out = stdout(&o);
    assert!(out.contains("\"installed\": true"), "status json: {out}");

    let o = cli(
        tmp.path(),
        &["session", "hooks", "status", "--project-root", root],
    );
    assert_native(&o, "hooks status todos");
    assert!(stdout(&o).contains("✓ pi:"), "status texto: {}", stdout(&o));
    assert!(
        stdout(&o).contains("— claude-code:"),
        "status texto: {}",
        stdout(&o)
    );

    let o = cli(
        tmp.path(),
        &[
            "session",
            "hooks",
            "uninstall",
            "--ide",
            "pi",
            "--project-root",
            root,
        ],
    );
    assert_native(&o, "hooks uninstall");
    assert!(stdout(&o).contains("removed"), "{}", stdout(&o));
    let restante = std::fs::read_to_string(&justfile).unwrap_or_default();
    assert!(
        !restante.contains("cortex-checkpoint"),
        "recetas removidas: {restante:?}"
    );
}

#[test]
fn session_hooks_errores_native() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_str().unwrap();

    let o = cli(
        tmp.path(),
        &[
            "session",
            "hooks",
            "install",
            "--ide",
            "bogus",
            "--project-root",
            root,
        ],
    );
    assert_eq!(o.status.code(), Some(1));
    assert!(
        stderr(&o).contains("unknown IDE adapter 'bogus'"),
        "{}",
        stderr(&o)
    );

    let o = cli(
        tmp.path(),
        &[
            "session",
            "hooks",
            "status",
            "--ide",
            "bogus",
            "--project-root",
            root,
        ],
    );
    assert_eq!(o.status.code(), Some(1));
    assert!(stderr(&o).contains("unknown IDE adapter 'bogus'"));
}

// ---------------------------------------------------------------------------
// remember / forget
// ---------------------------------------------------------------------------

#[test]
fn remember_native_almacena_y_anuncia() {
    let tmp = memory_fixture();
    let o = cli(
        tmp.path(),
        &[
            "remember",
            "Implementamos login con JWT en auth.py",
            "--type",
            "session",
            "--tag",
            "auth",
            "--file",
            "src/auth.py",
        ],
    );
    assert_native(&o, "remember");
    let out = stdout(&o);
    assert!(
        out.starts_with("Memory stored -> mem_"),
        "salida remember: {out}"
    );
    assert!(out.contains("   type: session"), "salida remember: {out}");
    assert!(
        out.contains("   summary: Implementamos login con JWT en auth.py"),
        "salida remember: {out}"
    );
    // La fila quedó persistida en el JSONL episódico.
    let jsonl = tmp.path().join(".cortex/memory/episodic_export.jsonl");
    let text = std::fs::read_to_string(&jsonl).unwrap();
    assert_eq!(text.lines().count(), 3, "2 semillas + 1 nueva");
    assert!(text.contains("Implementamos login con JWT en auth.py"));
}

#[test]
fn forget_native_borra_y_reporta() {
    let tmp = memory_fixture();

    let o = cli(tmp.path(), &["forget", "mem_aaaa1111"]);
    assert_native(&o, "forget ok");
    assert_eq!(stdout(&o), "Memory mem_aaaa1111 deleted.\n");

    let jsonl = tmp.path().join(".cortex/memory/episodic_export.jsonl");
    let text = std::fs::read_to_string(&jsonl).unwrap();
    assert!(!text.contains("mem_aaaa1111"), "id borrado del JSONL");
    assert!(text.contains("mem_bbbb2222"), "resto preservado");

    let o = cli(tmp.path(), &["forget", "mem_zzzz9999"]);
    assert_eq!(o.status.code(), Some(1));
    assert!(stderr(&o).contains("not found"), "{}", stderr(&o));
}

// ---------------------------------------------------------------------------
// Cold start (medición honesta N=20 por subcomando liviano)
// ---------------------------------------------------------------------------

fn elapsed_ms(f: impl Fn()) -> u128 {
    let t0 = SystemTime::now();
    f();
    t0.elapsed().unwrap().as_millis()
}

#[test]
fn cold_start_session_task_list() {
    let tmp = session_fixture();
    let root = tmp.path().to_str().unwrap().to_string();
    let times: Vec<u128> = (0..20)
        .map(|_| {
            elapsed_ms(|| {
                let o = cli(
                    tmp.path(),
                    &["session", "task", "list", "--project-root", &root],
                );
                assert!(o.status.success());
            })
        })
        .collect();
    let avg = times.iter().sum::<u128>() / times.len() as u128;
    let max = times.iter().max().copied().unwrap_or(0);
    assert!(avg < 5000, "avg {avg}ms supera el límite de cordura");
    eprintln!("[cold] session task list N=20 avg={avg}ms max={max}ms");
}

#[test]
fn cold_start_session_hooks_list() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_str().unwrap().to_string();
    let times: Vec<u128> = (0..20)
        .map(|_| {
            elapsed_ms(|| {
                let o = cli(
                    tmp.path(),
                    &["session", "hooks", "list", "--project-root", &root],
                );
                assert!(o.status.success());
            })
        })
        .collect();
    let avg = times.iter().sum::<u128>() / times.len() as u128;
    let max = times.iter().max().copied().unwrap_or(0);
    assert!(avg < 5000, "avg {avg}ms supera el límite de cordura");
    eprintln!("[cold] session hooks list N=20 avg={avg}ms max={max}ms");
}
