//! B2 — Flujo de aprobación (G-B3).
//!
//! Las MUTACIONES del Companion nunca se ejecutan directo: pasan por
//! `run_guarded`, que pide aprobación explícita a la UI y audita la decisión
//! (aprobado/denegado/fallo) en `.cortex/action_log.jsonl` con el MISMO
//! formato y archivo que usa el runner nativo de `cortex-actions`.
//!
//! `#![forbid(unsafe_code)]` lo aplica el crate (ver lib.rs).

use cortex_actions::store::{ActionLog as NativeLog, OrderedEntry};
use std::io;
use std::path::Path;

/// Qué está por ejecutarse, para mostrarlo en el modal de aprobación.
#[derive(Debug, Clone)]
pub struct ApprovalRequest {
    pub title: String,
    pub effect: String,
    pub audit_key: String,
}

/// Quién decide. `ask` devuelve `true` = aprobado (clic en [Ejecutar]).
pub trait ApprovalUi: Send {
    fn ask(&mut self, req: &ApprovalRequest) -> bool;
}

/// Wrapper delgado sobre el `ActionLog` nativo de `cortex-actions`: mismo
/// archivo (`action_log.jsonl`), mismo serializador `json.dumps`-compatible,
/// misma rotación y `ts` automático, más el acceso `last_line()` que los
/// tests e inspección necesitan.
pub struct ActionLog {
    inner: NativeLog,
}

impl ActionLog {
    pub fn new(directory: &Path) -> Self {
        ActionLog {
            inner: NativeLog::new(directory),
        }
    }

    /// Ruta del archivo de auditoría (`<directory>/action_log.jsonl`).
    pub fn path(&self) -> &Path {
        self.inner.path()
    }

    /// Apienda una línea de auditoría de aprobación:
    /// `{id, approved, outcome, message, ts(automático)}`.
    fn append_audit(
        &self,
        id: &str,
        approved: bool,
        outcome: &str,
        message: &str,
    ) -> io::Result<()> {
        let mut entry = OrderedEntry::new();
        entry.set("id", serde_json::Value::String(id.to_string()));
        entry.set("approved", serde_json::Value::Bool(approved));
        entry.set("outcome", serde_json::Value::String(outcome.to_string()));
        entry.set("message", serde_json::Value::String(message.to_string()));
        self.inner.append(entry)
    }

    /// Última línea no vacía del archivo (para tests e inspección).
    pub fn last_line(&self) -> Option<String> {
        let text = std::fs::read_to_string(self.inner.path()).ok()?;
        text.lines()
            .rev()
            .find(|l| !l.trim().is_empty())
            .map(|s| s.to_string())
    }
}

/// Ejecuta `f` SOLO si la UI aprueba; audita siempre en el `action_log`.
///
/// - **Aprobado** → ejecuta `f`; audita `outcome="executed"` o (si falla)
///   `"failed"` y **propaga el error** de `f` (patrón P6/P9: nunca silencioso).
/// - **Denegado** → NO ejecuta; audita `outcome="denied"`; devuelve `Ok`.
///   Denegar es la decisión del usuario, no un error del sistema.
pub fn run_guarded<F>(
    ui: &mut dyn ApprovalUi,
    log: &ActionLog,
    req: &ApprovalRequest,
    f: F,
) -> Result<(), String>
where
    F: FnOnce() -> Result<(), String>,
{
    let approved = ui.ask(req);
    if !approved {
        // Denegar no es un error de flujo (el usuario decidió), pero la
        // auditoría es obligatoria: si no se puede registrar, falla fuerte
        // (mismo `.expect` que el runner nativo de cortex-actions: nunca
        // una ejecución gobernada sin registro).
        log.append_audit(&req.audit_key, false, "denied", "denegado por el usuario")
            .expect("action_log audit append");
        return Ok(());
    }
    match f() {
        Ok(()) => {
            log.append_audit(&req.audit_key, true, "executed", "ejecutado")
                .expect("action_log audit append");
            Ok(())
        }
        Err(e) => {
            log.append_audit(&req.audit_key, true, "failed", &e)
                .expect("action_log audit append");
            Err(e)
        }
    }
}
