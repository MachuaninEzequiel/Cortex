//! B6 — Aplicación de efectos compartida entre el binario y los tests.
//!
//! El reducer (`app::update`) es puro: declara `Effect`. Este módulo es el
//! runtime que los aplica contra el `Backend` inyectado, y es el ÚNICO lugar
//! donde una mutación puede ejecutarse: siempre a través de `run_guarded`
//! (B2) con la decisión que el usuario tomó en el modal de la máquina de
//! estados. Así el flujo auditado es idéntico en producción y en tests
//! (nada de loops bloqueantes ni lógica duplicada en el binario).

use crate::app::{AppState, ApprovalTarget, Effect, OutcomeLine, PendingApproval};
use crate::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi};
use crate::engine::Backend;
use crate::menu::MenuOutput;

/// `ApprovalUi` que reporta una decisión YA tomada en la máquina de estados
/// (el modal clickeado o Esc). No bloquea: la decisión es input, no I/O.
pub struct AnsweredUi {
    answer: bool,
}

impl AnsweredUi {
    pub fn new(answer: bool) -> Self {
        Self { answer }
    }
}

impl ApprovalUi for AnsweredUi {
    fn ask(&mut self, _req: &ApprovalRequest) -> bool {
        self.answer
    }
}

/// Aplica un efecto declarado por el reducer. Los mutantes pasan SIEMPRE por
/// `run_guarded` con auditoría en `action_log` (patrón P6/P9: nada en
/// silencio, fallos propagados a la UI).
pub fn apply<B: Backend + ?Sized>(be: &B, log: &ActionLog, st: &mut AppState, fx: Effect) {
    match fx {
        Effect::RunCommand { family, args } => {
            // Defensivo: las guarded se enrutan al modal en el reducer; si una
            // llegara acá igual, se ejecuta como lectura (nunca muta sin decisión).
            st.menu_output = Some(match be.menu_run(family, &args) {
                Ok(s) => MenuOutput::ok(s),
                Err(e) => MenuOutput::err(e),
            });
        }
        Effect::ResolveApproval => resolve(be, log, st),
    }
}

/// Consume `pending` (decisión incluida) y ejecuta el objetivo.
fn resolve<B: Backend + ?Sized>(be: &B, log: &ActionLog, st: &mut AppState) {
    let Some(PendingApproval {
        req,
        target,
        decision,
    }) = st.pending.take()
    else {
        return;
    };
    // Sin decisión explícita no hay ejecución (defensivo; el reducer siempre
    // setea decision antes de emitir ResolveApproval).
    let answer = decision.unwrap_or(false);
    let mut ui = AnsweredUi::new(answer);

    match target {
        ApprovalTarget::RunMenu { family, args } => {
            let mut out: Option<String> = None;
            let r = run_guarded(&mut ui, log, &req, || {
                be.menu_run(family, &args).map(|s| out = Some(s))
            });
            st.menu_output = Some(match (answer, r, out) {
                (true, Ok(()), Some(s)) => MenuOutput::ok(s),
                (true, Ok(()), None) => MenuOutput::ok("ejecutado (sin salida)".to_string()),
                (true, Err(e), _) => MenuOutput::err(e),
                (false, _, _) => MenuOutput::ok("denegado — sin cambios".to_string()),
            });
        }
        ApprovalTarget::CloseSession { session_id } => {
            let r = run_guarded(&mut ui, log, &req, || be.close_session(&session_id));
            st.sessions.outcome = Some(outcome_line(answer, r));
        }
        ApprovalTarget::ApproveAction { id } => {
            let r = run_guarded(&mut ui, log, &req, || be.approve_action(&id));
            st.actions.outcome = Some(outcome_line(answer, r));
        }
        ApprovalTarget::ApproveBatch { ids } => {
            if answer {
                // Una aprobación única del lote; CADA ítem audita por
                // separado con su propio audit_key (brief B6).
                let mut okc = 0usize;
                let mut failed: Vec<String> = Vec::new();
                for id in &ids {
                    let req = proposal_req(st, id);
                    match run_guarded(&mut ui, log, &req, || be.approve_action(id)) {
                        Ok(()) => okc += 1,
                        Err(_) => failed.push(id.clone()),
                    }
                }
                st.actions.outcome = Some(if failed.is_empty() {
                    (format!("lote auto-ok: {okc} ejecutadas"), false)
                } else {
                    (
                        format!(
                            "lote auto-ok: {okc} ejecutadas, fallaron: {}",
                            failed.join(", ")
                        ),
                        true,
                    )
                });
            } else {
                // Lote denegado: ninguna ejecución, una sola auditoría con la
                // clave del modal.
                let _ = run_guarded(&mut ui, log, &req, || Ok(()));
                st.actions.outcome = Some(("lote denegado — sin cambios".to_string(), false));
            }
        }
    }
}

/// Resultado legible para el panel de salida: denegar NO es un error del
/// sistema (decisión del usuario); ejecutar bien tampoco; fallar sí.
fn outcome_line(answer: bool, r: Result<(), String>) -> OutcomeLine {
    if !answer {
        return ("denegado — sin cambios".to_string(), false);
    }
    match r {
        Ok(()) => ("ejecutado".to_string(), false),
        Err(e) => (e, true),
    }
}

/// Pedido de aprobación reconstruido para un ítem del lote (mismo efecto y
/// título que vería si la aprobara individualmente).
fn proposal_req(st: &AppState, id: &str) -> ApprovalRequest {
    let p = st.actions.proposals.iter().find(|p| p.id == id);
    ApprovalRequest {
        title: format!("Aprobar «{}»", p.map(|p| p.title.as_str()).unwrap_or(id)),
        effect: p
            .map(|p| p.effect.clone())
            .unwrap_or_else(|| format!("acción {id}")),
        audit_key: id.to_string(),
    }
}
