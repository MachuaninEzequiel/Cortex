//! Tests MITAD B — RUTA 2 (baja definitiva): `hu import` éxito (provider
//! jira configurado vía file:// en tmp), error provider desconocido,
//! `--no-remember` — glue CLI sobre WorkItemService::import_item (P12A-2)
//! con providers construidos desde config (integrations.jira), espejo de
//! `_get_workitem_service` del oráculo.
//!
//! TDD estricto: RED contra el estado previo (providers vacíos ⇒ import
//! siempre falla con "Unknown work item provider: jira") y GREEN tras
//! wirear providers. Servicios reales + fixtures tmp, sin mocks.

use std::process::Command;
use std::process::Output;

fn cli(root: &std::path::Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(args)
        .current_dir(root)
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .env("JIRA_EMAIL", "a@b.c")
        .env("JIRA_API_TOKEN", "tok")
        .output()
        .expect("run cortex-cli")
}

fn stdout(o: &Output) -> String {
    String::from_utf8_lossy(&o.stdout).into_owned()
}

fn stderr(o: &Output) -> String {
    String::from_utf8_lossy(&o.stderr).into_owned()
}

/// Configura un workspace nuevo con jira ENABLED vía `file://` en tmp.
/// `conn_error` = en vez de archivos, dejamos el file:// sin resolver
/// (caso "connection failed" del oráculo con URLError de file scheme no
/// portable ⇒ NO se gatea byte-a-byte; sólo se verifica rc=1 + origen).
fn fixture(root: &std::path::Path, jira_enabled: bool, fake_body: Option<&str>) {
    let cortex = root.join(".cortex");
    cortex.mkdir_all().unwrap();
    std::fs::write(cortex.join("workspace.yaml"), "layout_version: 2\n").unwrap();
    let jira_line = if jira_enabled {
        format!(
            "integrations:\n  jira:\n    enabled: true\n    base_url: \"file://{}/jira/\"\n",
            root.display()
        )
    } else {
        "integrations:\n  jira:\n    enabled: false\n".to_string()
    };
    std::fs::write(
        cortex.join("config.yaml"),
        format!("semantic:\n  vault_path: vault\n{jira_line}"),
    )
    .unwrap();
    if let Some(body) = fake_body {
        let issue = root
            .join("jira")
            .join("rest")
            .join("api")
            .join("3")
            .join("issue");
        std::fs::create_dir_all(&issue).unwrap();
        std::fs::write(issue.join("PROJ-1"), body).unwrap();
    }
}

// Método auxiliar local (para no depender de create_dir api versiones):
trait MkDirAll {
    fn mkdir_all(&self) -> std::io::Result<()>;
}
impl MkDirAll for std::path::Path {
    fn mkdir_all(&self) -> std::io::Result<()> {
        std::fs::create_dir_all(self)
    }
}

const ISSUE_BODY: &str = r#"{"key":"PROJ-1","fields":{"summary":"Hacer login","issuetype":{"name":"Story"},"description":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Bueno"}]}],"version":1},"labels":["auth"],"assignee":{"displayName":"Ana"},"status":{"name":"In Progress"},"priority":{"name":"High"}}}"#;
const ISSUE_BODY_MD: &str = r#"{"key":"PROJ-1","fields":{"summary":"Hacer login","issuetype":{"name":"Story"},"description":"* aceptar 1\n- aceptar 2\n[ ] aceptar 3","labels":["auth"],"status":{"name":"Todo"}}}"#;

#[test]
fn import_exito_provider_jira_file() {
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, Some(ISSUE_BODY));
    let out = cli(tmp.path(), &["hu", "import", "PROJ-1"]);
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(0), "{err}");
    let v = tmp
        .path()
        .join(".cortex")
        .join("vault")
        .join("hu")
        .join("HU-PROJ-1.md");
    assert!(v.exists(), "nota canónica debe existir: {}", v.display());
    let expected = format!("Tracked item imported -> {}\n", v.display());
    assert_eq!(stdout(&out), expected);
    // Contenido canónico del writer P8b (fuente jira + kind story).
    let note = std::fs::read_to_string(&v).unwrap();
    assert!(note.contains("source: jira"), "{note}");
    assert!(note.contains("kind: story"), "{note}");
    assert!(note.contains("external_id: PROJ-1"), "{note}");
}

#[test]
fn import_description_markdown_flatten() {
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, Some(ISSUE_BODY_MD));
    let out = cli(
        tmp.path(),
        &["hu", "import", "PROJ-1", "--provider", "jira"],
    );
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(0), "{err}");
    let v = tmp
        .path()
        .join(".cortex")
        .join("vault")
        .join("hu")
        .join("HU-PROJ-1.md");
    let note = std::fs::read_to_string(&v).unwrap();
    // La descripción markdown cruda viaja directo (str description).
    assert!(note.contains("aceptar 1"), "{note}");
    assert!(note.contains("- aceptar 2"), "{note}");
}

#[test]
fn import_no_remember_ok() {
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, Some(ISSUE_BODY));
    let out = cli(tmp.path(), &["hu", "import", "PROJ-1", "--no-remember"]);
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(0), "{err}");
    assert!(
        stdout(&out).contains("Tracked item imported ->"),
        "{}",
        stdout(&out)
    );
}

#[test]
fn import_provider_desconocido_error_exacto() {
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, Some(ISSUE_BODY));
    let out = cli(
        tmp.path(),
        &["hu", "import", "PROJ-1", "--provider", "nope"],
    );
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(1), "{}", stdout(&out));
    assert_eq!(err, "Unknown work item provider: nope\n");
}

#[test]
fn import_sin_integration_configurada_error_canonico() {
    // jira disabled en config ⇒ providers vacíos ⇒ "Unknown work item
    // provider: jira" (mismo origen que el KeyError del oráculo sin
    // integraciones; mensaje limpio = mejora deliberada documentada S19).
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), false, None);
    let out = cli(
        tmp.path(),
        &["hu", "import", "PROJ-1", "--provider", "jira"],
    );
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(1), "{}", stdout(&out));
    assert_eq!(err, "Unknown work item provider: jira\n");
}

#[test]
fn import_jira_enabled_sin_env_no_configurado() {
    // jira enabled pero sin env JIRA_EMAIL/JIRA_API_TOKEN ⇒ provider
    // registrado pero no configurado ⇒ mensaje canónico del oráculo
    // (RuntimeError "Provider 'jira' is not configured." → nativo limpio).
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, Some(ISSUE_BODY));
    let out = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(["hu", "import", "PROJ-1"])
        .current_dir(tmp.path())
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .env_remove("JIRA_EMAIL")
        .env_remove("JIRA_API_TOKEN")
        .output()
        .expect("run cortex-cli");
    let err = stderr(&out);
    assert_eq!(out.status.code(), Some(1), "{}", stdout(&out));
    assert_eq!(err, "Provider 'jira' is not configured.\n");
}

#[test]
fn import_jira_file_missing_conexion_falla() {
    // base_url file:// válida pero archivo inexistente ⇒ el oráculo tira
    // URLError (no portable) ⇒ el nativo informa `Jira connection
    // failed` con rc 1 (equiv al oráculo; sin paridad byte-a-byte).
    let tmp = tempfile::tempdir().unwrap();
    fixture(tmp.path(), true, None); // sin archivo
    let out = cli(
        tmp.path(),
        &["hu", "import", "PROJ-1", "--provider", "jira"],
    );
    assert_eq!(out.status.code(), Some(1));
    let err = stderr(&out);
    assert!(err.starts_with("Jira connection failed"), "{err}");
}
