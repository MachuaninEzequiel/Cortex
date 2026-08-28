//! B2 — Flujo de aprobación: las mutaciones del Companion solo se ejecutan
//! con aprobación explícita, y esa decisión (aprobado/denegado/fallo) queda
//! auditada en el action_log con el MISMO formato de cortex-actions.
use cortex_companion::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------------------
// Helpers de test
// ---------------------------------------------------------------------------

struct RecorderUi {
    approved: bool,
    calls: usize,
}
impl ApprovalUi for RecorderUi {
    fn ask(&mut self, _: &ApprovalRequest) -> bool {
        self.calls += 1;
        self.approved
    }
}

fn req(keys: &str, effect: &str) -> ApprovalRequest {
    ApprovalRequest {
        title: keys.to_string(),
        effect: effect.to_string(),
        audit_key: keys.to_string(),
    }
}

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "cortex-companion-approval-{tag}-{}-{nanos}",
        std::process::id()
    ))
}

fn cleanup(dir: &Path) {
    let _ = std::fs::remove_dir_all(dir);
}

// ---------------------------------------------------------------------------
// Los 3 tests del brief (adaptados al patrón del crate: tests/ integration).
// ---------------------------------------------------------------------------

#[test]
fn denied_mutation_never_executes() {
    let dir = unique_dir("denied");
    let mut ui = RecorderUi {
        approved: false,
        calls: 0,
    };
    let log = ActionLog::new(&dir);
    let mut executed = false;

    let r = run_guarded(
        &mut ui,
        &log,
        &req("sess.close", "Cierra la sesión SES-x"),
        || {
            executed = true;
            Ok(())
        },
    );

    // Denegar NO es error: es la decisión del usuario.
    assert!(r.is_ok(), "denegar no debe ser un error: {r:?}");
    assert!(!executed, "la mutación denegada NO debe ejecutarse");
    assert_eq!(
        ui.calls, 1,
        "la UI debe haberse consultado exactamente una vez"
    );

    let last = log
        .last_line()
        .expect("debe existir una línea de auditoría");
    assert!(last.contains("\"approved\": false"), "línea: {last}");
    assert!(last.contains("\"outcome\": \"denied\""), "línea: {last}");
    cleanup(&dir);
}

#[test]
fn approved_mutation_executes_and_audits() {
    let dir = unique_dir("approved");
    let mut ui = RecorderUi {
        approved: true,
        calls: 0,
    };
    let log = ActionLog::new(&dir);
    let mut executed = false;

    run_guarded(
        &mut ui,
        &log,
        &req("sess.close", "Cierra la sesión SES-x"),
        || {
            executed = true;
            Ok(())
        },
    )
    .expect("aprobación debe ejecutar sin error");

    assert!(executed, "la mutación aprobada debe ejecutarse");
    let last = log
        .last_line()
        .expect("debe existir una línea de auditoría");
    assert!(last.contains("\"approved\": true"), "línea: {last}");
    assert!(last.contains("\"outcome\": \"executed\""), "línea: {last}");
    cleanup(&dir);
}

#[test]
fn failure_is_audited_not_silent() {
    let dir = unique_dir("failed");
    let mut ui = RecorderUi {
        approved: true,
        calls: 0,
    };
    let log = ActionLog::new(&dir);

    let r = run_guarded(
        &mut ui,
        &log,
        &req("remember", "Guarda una memoria"),
        || Err("backend no disponible".to_string()),
    );

    // El error de la mutación se PROPAGA (nunca se traga).
    assert!(r.is_err(), "el fallo de la mutación debe propagarse");
    assert!(r.unwrap_err().contains("backend no disponible"));

    let last = log
        .last_line()
        .expect("debe existir una línea de auditoría");
    assert!(last.contains("\"approved\": true"), "línea: {last}");
    assert!(last.contains("\"outcome\": \"failed\""), "línea: {last}");
    assert!(last.contains("backend no disponible"), "línea: {last}");
    cleanup(&dir);
}

// La auditoría reusa el formato del action_log nativo de cortex-actions.
#[test]
fn audit_reuses_native_action_log_format() {
    let dir = unique_dir("format");
    let log = ActionLog::new(&dir);
    let mut ui = RecorderUi {
        approved: true,
        calls: 0,
    };
    run_guarded(&mut ui, &log, &req("sess.close", "detalle"), || Ok(())).unwrap();

    // El archivo es exactamente action_log.jsonl (mismo que cortex-actions) y la
    // línea se serializa con json.dumps-compat: claves con " y comas ", ".
    let path = log.path();
    assert_eq!(
        path.file_name().unwrap().to_str().unwrap(),
        "action_log.jsonl",
        "debe reusar exactamente el archivo de cortex-actions"
    );
    let last = log.last_line().unwrap();
    assert!(last.starts_with('{') && last.ends_with('}'));
    assert!(last.contains("\"approved\": true"), "línea: {last}");
    cleanup(&dir);
}
