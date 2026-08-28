//! B6 — Aplicación de efectos compartida entre el binario y los tests.
//!
//! El reducer (`app::update`) es puro: declara `Effect`. Este módulo es el
//! runtime que los aplica contra el `Backend` inyectado, y es el ÚNICO lugar
//! donde una mutación puede ejecutarse: siempre a través de `run_guarded`
//! (B2) con la decisión que el usuario tomó en el modal de la máquina de
//! estados. Así el flujo auditado es idéntico en producción y en tests
//! (nada de loops bloqueantes ni lógica duplicada en el binario).
//!
//! B8 añade el brain híbrido: `apply_opt` acepta el `LlmBackend` opcional
//! (None = router determinista, cero tokens; Some = protocolo TOOL del
//! brain con las tools enrutadas por el engine in-process — `brain_panel`).

use crate::app::{AppState, ApprovalTarget, Effect, OutcomeLine, PendingApproval};
use crate::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi};
use crate::brain_panel::{self, BrainMsg};
use crate::engine::Backend;
use crate::feedback;
use crate::menu::{self, MenuOutput};

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

/// Aplica un efecto declarado por el reducer (sin LLM: modo determinista,
/// cero tokens — default del brain y del Companion).
pub fn apply<B: Backend>(be: &B, log: &ActionLog, st: &mut AppState, fx: Effect) {
    apply_opt(be, log, st, fx, None);
}

/// Versión con backend LLM opcional (B8): `Some` habilita el protocolo TOOL
/// del brain sobre el engine; `None` usa el router determinista 1:1.
pub fn apply_opt<B: Backend>(
    be: &B,
    log: &ActionLog,
    st: &mut AppState,
    fx: Effect,
    llm: Option<&mut dyn cortex_brain::chat::LlmBackend>,
) {
    match fx {
        Effect::RunCommand { family, args } => {
            // M-1 (fix wave final review): defensivo. El reducer ya enruta
            // guarded al modal; si una llegara acá igual, NO se ejecuta: se
            // abre el modal con el mismo flujo del camino normal (nunca muta
            // sin decisión del usuario).
            if menu::command_is_guarded(family, &args) {
                let title = menu::entry_for(family, &args)
                    .map(|e| e.title.to_string())
                    .unwrap_or_else(|| family.to_string());
                st.pending = Some(PendingApproval {
                    req: ApprovalRequest {
                        title: format!("Ejecutar «{title}»"),
                        effect: format!("cortex {family} {}", args.join(" "))
                            .trim_end()
                            .to_string(),
                        audit_key: format!("menu.{family}"),
                    },
                    target: ApprovalTarget::RunMenu { family, args },
                    decision: None,
                });
                return;
            }
            st.menu_output = Some(match be.menu_run(family, &args) {
                Ok(s) => MenuOutput::ok(s),
                Err(e) => MenuOutput::err(e),
            });
        }
        Effect::Search { query } => {
            // Misma pipeline híbrida del CLI (Backend::search), top-k default
            // 5 (brief). El error se muestra, nunca se traga (P6/P9).
            st.search.outcome = None;
            match be.search(&query, 5) {
                Ok(hits) => {
                    st.search.hits = hits;
                    st.search.selected = None;
                    st.search.error = None;
                }
                Err(e) => {
                    st.search.hits = Vec::new();
                    st.search.selected = None;
                    st.search.error = Some(e);
                }
            }
        }
        Effect::MarkUseful { memory_id } => {
            // Feedback explícito positivo (escritor formato-oráculo, B7).
            // Idempotencia por hit: AlreadyMarked informa sin duplicar.
            match be.mark_useful(&memory_id) {
                Ok(feedback::AppendOutcome::Appended) => {
                    if !st.search.marked.contains(&memory_id) {
                        st.search.marked.push(memory_id.clone());
                    }
                    st.search.outcome = Some((format!("marcado útil: {memory_id}"), false));
                }
                Ok(feedback::AppendOutcome::AlreadyMarked) => {
                    if !st.search.marked.contains(&memory_id) {
                        st.search.marked.push(memory_id.clone());
                    }
                    st.search.outcome = Some((format!("ya marcada útil: {memory_id}"), false));
                }
                Err(e) => st.search.outcome = Some((e, true)),
            }
        }
        Effect::BrainTurn { text } => {
            // Un turno de chat: reads directas, propuestas mutantes como
            // mensajes Proposal (la aprobación llega al clickear
            // [Ejecutar] — el reducer abre el modal, resolve audita).
            brain_panel::run_turn(be, &mut st.brain, &text, llm);
        }
        Effect::BrainExec { family, args } => {
            // Defensivo (las propuestas solo se crean para mutantes): una
            // lectura sugerida se ejecuta directa por el engine, como toda
            // read del brain — sin modal y sin auditoría.
            match be.menu_run(&family, &args) {
                Ok(s) => st.brain.messages.push(BrainMsg::Brain(s)),
                Err(e) => st.brain.messages.push(BrainMsg::Brain(format!("⚠ {e}"))),
            }
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
        ApprovalTarget::BrainCommand { family, args } => {
            // Propuesta del brain aprobada ⇒ ejecución por el engine
            // (`menu_run`, paridad con el CLI) + auditoría bajo la
            // audit_key del mensaje. Denegada ⇒ cero ejecución, denied
            // auditado (run_guarded lo registra). El resultado es visible
            // en el chat (nunca silencio — P6/P9).
            let mut out: Option<String> = None;
            let r = run_guarded(&mut ui, log, &req, || {
                be.menu_run(&family, &args).map(|s| out = Some(s))
            });
            match (answer, r, out) {
                (true, Ok(()), Some(s)) => {
                    st.brain.messages.push(BrainMsg::Brain(s));
                    st.brain.outcome = Some(("ejecutado".to_string(), false));
                }
                (true, Ok(()), None) => {
                    st.brain.outcome = Some(("ejecutado (sin salida)".to_string(), false))
                }
                (true, Err(e), _) => st.brain.outcome = Some((e, true)),
                (false, _, _) => {
                    st.brain.outcome = Some(("denegado — sin cambios".to_string(), false))
                }
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
