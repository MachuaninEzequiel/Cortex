//! Puerto de `cortex/action_engine/runner.py` (Obra 05 Fase B).
//!
//! Ejecuta acciones aplicando las reglas duras del contrato:
//! - dry-run nativo (pasa `dry_run=true` al run de la acción);
//! - irreversible ⇒ exige `approved=true` explícito;
//! - toda ejecución (incluidos dry-runs y fallos) queda en action_log.jsonl;
//! - deshacer: `undo_last()` sobre la última ejecución reversible con éxito.

use std::sync::Arc;

use crate::models::{ahora_iso, Action, ActionResult, Trigger};
use crate::store::{ActionLog, OrderedEntry};

#[derive(Debug, Clone)]
pub struct ExecutionRecord {
    pub action: Arc<Action>,
    pub result: ActionResult,
    pub duration_ms: u64,
}

pub struct Runner {
    pub log: ActionLog,
    pub trigger: Trigger,
    historial: Vec<ExecutionRecord>,
}

impl Runner {
    pub fn new(directory: &std::path::Path) -> Self {
        Self {
            log: ActionLog::new(directory),
            trigger: Trigger::OnOpen,
            historial: Vec::new(),
        }
    }

    pub fn with_trigger(mut self, trigger: Trigger) -> Self {
        self.trigger = trigger;
        self
    }

    /// Ejecuta (o simula) una acción y la registra.
    ///
    /// Reglas:
    /// - irreversible exige `approved=true` salvo en dry-run;
    /// - el resultado SIEMPRE se registra en action_log.
    pub fn execute(
        &mut self,
        action: &Arc<Action>,
        dry_run: bool,
        approved: bool,
        via: &str,
    ) -> ActionResult {
        if !dry_run && !action.reversible && !approved {
            return self.registrar(
                action,
                ActionResult::fail(format!(
                    "{} es irreversible — requiere aprobación explícita",
                    action.id
                )),
                0,
                true,
                "user",
            );
        }

        let t0 = std::time::Instant::now();
        // Espejo del try/except: el runner nunca revienta.
        let result = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            (action.run)(dry_run)
        })) {
            Ok(r) => r,
            Err(payload) => {
                let msg = panic_message(&payload);
                eprintln!("ERROR: Acción {} falló: {msg}", action.id);
                ActionResult::fail(format!("{}: {msg}", action.id))
            }
        };
        let duration = t0.elapsed().as_millis() as u64; // int((t)*1000): truncado
        self.registrar(action, result, duration, dry_run, via)
    }

    /// Deshace la última ejecución real y reversible. None si no hay.
    pub fn undo_last(&mut self) -> Option<ActionResult> {
        for idx in (0..self.historial.len()).rev() {
            let record = &self.historial[idx];
            if !record.action.reversible || !record.result.ok {
                continue;
            }
            let Some(undo_fn) = record.action.undo.clone() else {
                continue;
            };
            let resultado = undo_fn();
            let mut entry = OrderedEntry::new();
            entry.set("id", serde_json::Value::String(record.action.id.clone()));
            entry.set("ts", serde_json::Value::String(ahora_iso()));
            entry.set(
                "trigger",
                serde_json::Value::String(self.trigger.as_str().into()),
            );
            entry.set("dry_run", serde_json::Value::Bool(false));
            entry.set("ok", serde_json::Value::Bool(resultado.ok));
            entry.set(
                "message",
                serde_json::Value::String(format!("UNDO: {}", resultado.message)),
            );
            entry.set("duration_ms", serde_json::Value::from(0u64));
            self.log.append(entry).ok()?;
            self.historial.remove(idx);
            return Some(resultado);
        }
        None
    }

    fn registrar(
        &mut self,
        action: &Arc<Action>,
        result: ActionResult,
        duration_ms: u64,
        dry_run: bool,
        via: &str,
    ) -> ActionResult {
        let mut entry = OrderedEntry::new();
        entry.set("id", serde_json::Value::String(action.id.clone()));
        entry.set("ts", serde_json::Value::String(ahora_iso()));
        entry.set(
            "trigger",
            serde_json::Value::String(self.trigger.as_str().into()),
        );
        entry.set("dry_run", serde_json::Value::Bool(dry_run));
        entry.set("ok", serde_json::Value::Bool(result.ok));
        entry.set("message", serde_json::Value::String(result.message.clone()));
        entry.set("duration_ms", serde_json::Value::from(duration_ms));
        entry.set("via", serde_json::Value::String(via.to_string()));
        self.log.append(entry).expect("action_log append");
        if !dry_run {
            self.historial.push(ExecutionRecord {
                action: action.clone(),
                result: result.clone(),
                duration_ms,
            });
        }
        result
    }
}

fn panic_message(payload: &Box<dyn std::any::Any + Send>) -> String {
    if let Some(s) = payload.downcast_ref::<&str>() {
        (*s).to_string()
    } else if let Some(s) = payload.downcast_ref::<String>() {
        s.clone()
    } else {
        "pánico desconocido".to_string()
    }
}

impl Runner {
    pub fn historial_len(&self) -> usize {
        self.historial.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Categoria, Costo};
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Mutex;

    struct Tmp(PathBuf);
    impl Drop for Tmp {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    use std::path::PathBuf;

    fn tmpdir(tag: &str) -> Tmp {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-run-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&d).unwrap();
        Tmp(d)
    }

    fn accion_ok(id: &str) -> Arc<Action> {
        Arc::new(
            Action::new(
                id,
                "Acción de prueba",
                Categoria::Maintenance,
                "no cambia nada real",
            )
            .unwrap()
            .reversible(true)
            .undo(Arc::new(|| ActionResult::new(true, "deshecho")))
            .cost(Costo::Instant)
            .auto_ok(true)
            .run_fn(|dry_run| {
                if dry_run {
                    ActionResult::new(true, "[dry-run] simulado")
                } else {
                    ActionResult::new(true, "hecho")
                }
            }),
        )
    }

    /// Espejo de TestActionLog.test_toda_ejecucion_se_registra.
    #[test]
    fn toda_ejecucion_se_registra() {
        let g = tmpdir("reg");
        let mut runner = Runner::new(&g.0);
        let accion = accion_ok("test.accion");
        runner.execute(&accion, false, false, "user");
        runner.execute(&accion, true, false, "user");

        let entradas = runner.log.load();
        assert_eq!(entradas.len(), 2);
        assert!(entradas.iter().all(|e| e["id"] == "test.accion"));
        assert_eq!(entradas[0]["dry_run"], serde_json::Value::Bool(false));
        assert_eq!(entradas[1]["dry_run"], serde_json::Value::Bool(true));
        assert_eq!(entradas[0]["trigger"], serde_json::json!("on-open"));
        assert!(entradas[0].get("duration_ms").is_some());
    }

    /// Espejo de TestActionLog.test_irreversible_sin_aprobacion_no_ejecuta.
    #[test]
    fn irreversible_sin_aprobacion_no_ejecuta() {
        let g = tmpdir("irr");
        let corrio = Arc::new(AtomicUsize::new(0));
        let c2 = corrio.clone();
        let accion = Arc::new(
            Action::new("danger.drop", "t", Categoria::Maintenance, "e")
                .unwrap()
                .reversible(false)
                .run_fn(move |_dry| {
                    c2.fetch_add(1, Ordering::SeqCst);
                    ActionResult::new(true, "cambio destructivo")
                }),
        );
        let mut runner = Runner::new(&g.0);

        let resultado = runner.execute(&accion, false, false, "user");
        assert!(!resultado.ok);
        assert_eq!(corrio.load(Ordering::SeqCst), 0); // NUNCA corrió

        let resultado2 = runner.execute(&accion, false, true, "user");
        assert!(resultado2.ok);
        assert_eq!(corrio.load(Ordering::SeqCst), 1);
    }

    /// Espejo de TestActionLog.test_undo_last_deshace_solo_reales_y_reversibles.
    #[test]
    fn undo_last_deshace_solo_reales_y_reversibles() {
        let g = tmpdir("undo");
        let deshechos: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
        let d2 = deshechos.clone();
        let accion = Arc::new(
            Action::new("test.accion", "t", Categoria::Maintenance, "e")
                .unwrap()
                .reversible(true)
                .undo(Arc::new(move || {
                    d2.lock().unwrap().push("back".into());
                    ActionResult::new(true, "back")
                }))
                .auto_ok(true)
                .cost(Costo::Instant)
                .run_fn(|dry_run| {
                    if dry_run {
                        ActionResult::new(true, "[dry-run] simulado")
                    } else {
                        ActionResult::new(true, "hecho")
                    }
                }),
        );
        let irreversible = Arc::new(
            Action::new("danger.x", "t", Categoria::Maintenance, "e")
                .unwrap()
                .run_fn(|_dr| ActionResult::new(true, "boom")),
        );
        let mut runner = Runner::new(&g.0);
        runner.execute(&accion, true, false, "user");
        runner.execute(&accion, false, false, "user");
        runner.execute(&irreversible, false, true, "user");

        let resultado = runner.undo_last();
        // la última real es la irreversible (sin undo) → deshace la anterior
        assert_eq!(deshechos.lock().unwrap().clone(), vec!["back".to_string()]);
        assert_eq!(resultado.map(|r| r.message).unwrap_or_default(), "back");
        assert_eq!(runner.historial_len(), 1);
    }

    /// Espejo del run que revienta: el runner captura y registra fail.
    #[test]
    fn run_que_paniquea_registra_fail() {
        let g = tmpdir("panic");
        let accion = Arc::new(
            Action::new("x.y", "t", Categoria::Quality, "e")
                .unwrap()
                .run_fn(|_dr| panic!("boom interno")),
        );
        let mut runner = Runner::new(&g.0);
        let r = runner.execute(&accion, false, true, "user");
        assert!(!r.ok);
        assert!(r.message.contains("boom interno"));
        let entradas = runner.log.load();
        assert_eq!(entradas.len(), 1);
        assert_eq!(entradas[0]["ok"], serde_json::Value::Bool(false));
    }
}
