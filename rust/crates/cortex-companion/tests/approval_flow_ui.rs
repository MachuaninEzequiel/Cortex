//! B6 — Panels Sessions+Actions con aprobación por clic integrada a la
//! máquina de estados (G-B3 UI).
//!
//! FakeBackend con contadores + `ActionLog` en temp dir: los clicks se
//! resuelven con `hit_test`, el reducer abre el modal (`pending`), y
//! `effects::apply(ResolveApproval)` ejecuta SOLO lo aprobado, auditando en
//! el action_log (cada ítem del lote por separado, spec 14 §5).

use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use ratatui::backend::TestBackend;
use ratatui::prelude::Color;
use ratatui::Terminal;

use cortex_companion::app::{
    hit_test, update, ActionsData, AppAction, AppState, Effect, SessionsData, ACTIONS_APPROVE_W,
    ACTIONS_APPROVE_X, ACTIONS_BATCH_BTN, ACTIONS_LIST_TOP, MODAL_APROBAR_RECT, MODAL_DENEGAR_RECT,
    SESSIONS_CLOSE_BTN, SESSIONS_LIST_TOP,
};
use cortex_companion::approval::ActionLog;
use cortex_companion::effects;
use cortex_companion::engine::{
    ActionProposal, Backend, DoctorSummary, SearchHit, SessionSummary, StatsSummary,
};
use cortex_companion::screens::actions_screen::{actions_areas, render_actions};
use cortex_companion::{Screen, UiRequest};

// ---------------------------------------------------------------------------
// Helpers de test
// ---------------------------------------------------------------------------

#[derive(Default)]
struct FakeBackend {
    proposals: Vec<ActionProposal>,
    sessions: Vec<SessionSummary>,
    approved: Mutex<Vec<String>>,
    closed: Mutex<Vec<String>>,
}

impl FakeBackend {
    fn approved_ids(&self) -> Vec<String> {
        self.approved.lock().unwrap().clone()
    }
    fn closed_ids(&self) -> Vec<String> {
        self.closed.lock().unwrap().clone()
    }
}

impl Backend for FakeBackend {
    fn session_current(&self) -> Result<Option<SessionSummary>, String> {
        Ok(None)
    }
    fn session_list(&self) -> Result<Vec<SessionSummary>, String> {
        Ok(self.sessions.clone())
    }
    fn next_actions(&self) -> Result<Vec<ActionProposal>, String> {
        Ok(self.proposals.clone())
    }
    fn search(&self, _query: &str, _top_k: usize) -> Result<Vec<SearchHit>, String> {
        Ok(vec![])
    }
    fn doctor(&self) -> Result<DoctorSummary, String> {
        Ok(DoctorSummary {
            ok: true,
            checks: vec![],
        })
    }
    fn stats(&self) -> Result<StatsSummary, String> {
        Ok(StatsSummary {
            episodic: 0,
            semantic: 0,
            vault_path: "vault/".into(),
        })
    }
    fn session_detail(&self, session_id: &str) -> Result<Vec<String>, String> {
        Ok(vec![format!("sesión {session_id}")])
    }
    fn close_session(&self, session_id: &str) -> Result<(), String> {
        self.closed.lock().unwrap().push(session_id.to_string());
        Ok(())
    }
    fn checkpoint_session(&self, _note: &str) -> Result<(), String> {
        Ok(())
    }
    fn approve_action(&self, action_id: &str) -> Result<(), String> {
        self.approved.lock().unwrap().push(action_id.to_string());
        Ok(())
    }
}

fn proposal(id: &str, reversible: bool, cost: &str) -> ActionProposal {
    ActionProposal {
        id: id.into(),
        title: format!("t-{id}"),
        score: 1.0,
        cost: cost.into(),
        reversible,
        effect: format!("efecto exacto de {id}"),
    }
}

fn summary(id: &str) -> SessionSummary {
    SessionSummary {
        id: id.into(),
        status: "OPEN".into(),
        mode: "managed".into(),
        opened_at: "2026-08-28T00:00:00+00:00".into(),
    }
}

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "cortex-companion-b6-{tag}-{}-{nanos}",
        std::process::id()
    ))
}

fn cleanup(dir: &Path) {
    let _ = std::fs::remove_dir_all(dir);
}

/// Estado en la pantalla dada con los datos del backend cargados (el runtime
/// hace esto antes de cada draw; en los tests se setean directo).
fn setup(screen: Screen, fb: &FakeBackend) -> AppState {
    let mut st = AppState::new(UiRequest {
        screen,
        project_root: PathBuf::from("/tmp/fixture"),
    });
    st.actions = ActionsData {
        proposals: fb.proposals.clone(),
        ..Default::default()
    };
    st.sessions = SessionsData {
        sessions: fb.sessions.clone(),
        ..Default::default()
    };
    st
}

/// Click en la columna [Aprobar] de la fila de propuestas `row`.
fn approve_click(st: &AppState, row: usize) -> AppAction {
    hit_test(
        st,
        ACTIONS_APPROVE_X + ACTIONS_APPROVE_W / 2,
        ACTIONS_LIST_TOP + row as u16,
    )
    .expect("click en [Aprobar] de la fila")
}

/// Click en el botón [Aprobar] del modal abierto.
fn modal_approve_click(st: &AppState) -> AppAction {
    hit_test(
        st,
        MODAL_APROBAR_RECT.x + MODAL_APROBAR_RECT.width / 2,
        MODAL_APROBAR_RECT.y,
    )
    .expect("click en [Aprobar] del modal")
}

// ---------------------------------------------------------------------------
// Los 3 tests del brief + foco del modal + Sessions + hover
// ---------------------------------------------------------------------------

#[test]
fn click_approve_on_action_executes_and_audits() {
    let dir = unique_dir("approve");
    let fb = FakeBackend {
        proposals: vec![proposal("p1", true, "instant")],
        ..Default::default()
    };
    let mut st = setup(Screen::Actions, &fb);
    let log = ActionLog::new(&dir);

    // El modal muestra SIEMPRE el efecto exacto (spec 14 §5).
    let act = approve_click(&st, 0);
    assert!(update(&mut st, act).is_none());
    let pend = st.pending.clone().expect("modal abierto");
    assert_eq!(pend.req.effect, "efecto exacto de p1");
    assert_eq!(pend.req.audit_key, "p1");

    let act = modal_approve_click(&st);
    let fx = update(&mut st, act).expect("ResolveApproval");
    assert_eq!(fx, Effect::ResolveApproval);
    effects::apply(&fb, &log, &mut st, fx);

    assert_eq!(fb.approved_ids(), vec!["p1".to_string()]);
    let last = log.last_line().expect("auditoría escrita");
    assert!(last.contains("\"id\": \"p1\""), "línea: {last}");
    assert!(last.contains("\"approved\": true"), "línea: {last}");
    assert!(last.contains("\"outcome\": \"executed\""), "línea: {last}");
    assert!(st.pending.is_none(), "el modal se cierra al resolver");
    cleanup(&dir);
}

#[test]
fn click_deny_on_modal_never_executes() {
    let dir = unique_dir("deny");
    let fb = FakeBackend {
        proposals: vec![proposal("p1", true, "instant")],
        ..Default::default()
    };
    let mut st = setup(Screen::Actions, &fb);
    let log = ActionLog::new(&dir);

    let act = approve_click(&st, 0);
    assert!(update(&mut st, act).is_none());
    let act = hit_test(
        &st,
        MODAL_DENEGAR_RECT.x + MODAL_DENEGAR_RECT.width / 2,
        MODAL_DENEGAR_RECT.y,
    )
    .expect("click en [Denegar] del modal");
    assert!(matches!(act, AppAction::Deny { ref audit_key } if audit_key == "p1"));
    let fx = update(&mut st, act).expect("ResolveApproval");
    effects::apply(&fb, &log, &mut st, fx);

    assert!(fb.approved_ids().is_empty(), "denegar NUNCA ejecuta");
    let last = log.last_line().expect("auditoría de denegación");
    assert!(last.contains("\"approved\": false"), "línea: {last}");
    assert!(last.contains("\"outcome\": \"denied\""), "línea: {last}");
    assert!(
        matches!(st.actions.outcome, Some((_, false))),
        "denegar no es un error del sistema"
    );
    assert!(st.pending.is_none());
    cleanup(&dir);
}

#[test]
fn batch_auto_ok_only_batchable_items() {
    let dir = unique_dir("batch");
    let fb = FakeBackend {
        proposals: vec![
            proposal("p-ok", true, "instant"),
            proposal("p-no", false, "minutes"),
            proposal("p-slow", true, "minutes"),
        ],
        ..Default::default()
    };
    let mut st = setup(Screen::Actions, &fb);
    let log = ActionLog::new(&dir);

    // Click en [Aprobar lote auto-ok] ⇒ pending con SOLO los batchables.
    let act = hit_test(
        &st,
        ACTIONS_BATCH_BTN.x + ACTIONS_BATCH_BTN.width / 2,
        ACTIONS_BATCH_BTN.y,
    )
    .expect("click en lote auto-ok");
    assert!(matches!(act, AppAction::ApproveBatch));
    assert!(update(&mut st, act).is_none());
    let pend = st.pending.clone().expect("modal de lote abierto");
    assert_eq!(
        pend.target,
        cortex_companion::app::ApprovalTarget::ApproveBatch {
            ids: vec!["p-ok".to_string()]
        }
    );

    let act = modal_approve_click(&st);
    let fx = update(&mut st, act).expect("ResolveApproval");
    effects::apply(&fb, &log, &mut st, fx);

    // Solo la batchable se ejecuta, y su auditoría es POR ÍTEM (audit_key=p-ok).
    assert_eq!(fb.approved_ids(), vec!["p-ok".to_string()]);
    let last = log.last_line().expect("auditoría del ítem");
    assert!(last.contains("\"id\": \"p-ok\""), "línea: {last}");
    assert!(last.contains("\"approved\": true"), "línea: {last}");
    cleanup(&dir);
}

#[test]
fn batch_with_two_batchables_audits_each_item_separately() {
    // Minor 3 del review: lote con ≥2 batchables ⇒ cada aprobación audita
    // por separado (una línea por ítem en action_log).
    let dir = unique_dir("batch2");
    let fb = FakeBackend {
        proposals: vec![
            proposal("p-a", true, "instant"),
            proposal("p-b", true, "instant"),
            proposal("p-c", false, "minutes"),
        ],
        ..Default::default()
    };
    let mut st = setup(Screen::Actions, &fb);
    let log = ActionLog::new(&dir);

    let act = hit_test(
        &st,
        ACTIONS_BATCH_BTN.x + ACTIONS_BATCH_BTN.width / 2,
        ACTIONS_BATCH_BTN.y,
    )
    .expect("click en lote auto-ok");
    assert!(matches!(act, AppAction::ApproveBatch));
    assert!(update(&mut st, act).is_none());
    let pend = st.pending.clone().expect("modal de lote abierto");
    assert_eq!(
        pend.target,
        cortex_companion::app::ApprovalTarget::ApproveBatch {
            ids: vec!["p-a".to_string(), "p-b".to_string()]
        }
    );

    let act = modal_approve_click(&st);
    let fx = update(&mut st, act).expect("ResolveApproval");
    effects::apply(&fb, &log, &mut st, fx);

    assert_eq!(
        fb.approved_ids(),
        vec!["p-a".to_string(), "p-b".to_string()]
    );
    let lines: Vec<String> = std::fs::read_to_string(log.path())
        .expect("action_log escrito")
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.to_string())
        .collect();
    assert_eq!(lines.len(), 2, "una línea de auditoría por ítem: {lines:?}");
    assert!(
        lines[0].contains("\"id\": \"p-a\"") && lines[0].contains("\"approved\": true"),
        "línea 0: {}",
        lines[0]
    );
    assert!(
        lines[1].contains("\"id\": \"p-b\"") && lines[1].contains("\"approved\": true"),
        "línea 1: {}",
        lines[1]
    );
    assert!(lines
        .iter()
        .all(|l| l.contains("\"outcome\": \"executed\"")));
    cleanup(&dir);
}

#[test]
fn session_close_button_guards_and_audits() {
    let dir = unique_dir("close");
    let fb = FakeBackend {
        sessions: vec![summary("2026-08-28_demo")],
        ..Default::default()
    };
    let mut st = setup(Screen::Sessions, &fb);
    let log = ActionLog::new(&dir);

    // Click en fila ⇒ selección (detalle), sin mutación.
    let act = hit_test(&st, 10, SESSIONS_LIST_TOP).expect("click en fila de sesión");
    assert!(matches!(act, AppAction::SelectSession { index: 0 }));
    assert!(update(&mut st, act).is_none());
    assert_eq!(st.sessions.selected, Some(0));

    // [Cerrar sesión] ⇒ modal con efecto exacto; aprobar ⇒ close_session + audit.
    let act = hit_test(&st, SESSIONS_CLOSE_BTN.x + 2, SESSIONS_CLOSE_BTN.y)
        .expect("click en Cerrar sesión");
    assert!(
        matches!(act, AppAction::CloseSession { ref session_id } if session_id == "2026-08-28_demo")
    );
    assert!(update(&mut st, act).is_none());
    // Fix finding B6 (review): el efecto del modal debe ser un comando
    // EJECUTABLE del CLI nativo — `cortex finish` (alias documentado);
    // `cortex session finish` no existe (rc 2). El id de la sesión queda en
    // el título del modal.
    let pend = st.pending.as_ref().expect("modal abierto");
    assert_eq!(pend.req.effect, "cortex finish", "efecto = comando real");
    assert!(
        pend.req.title.contains("2026-08-28_demo"),
        "título identifica la sesión: {}",
        pend.req.title
    );
    assert!(pend.req.audit_key.contains("2026-08-28_demo"));

    let act = modal_approve_click(&st);
    let fx = update(&mut st, act).expect("ResolveApproval");
    effects::apply(&fb, &log, &mut st, fx);
    assert_eq!(fb.closed_ids(), vec!["2026-08-28_demo".to_string()]);
    let last = log.last_line().expect("auditoría de close");
    assert!(last.contains("\"outcome\": \"executed\""), "línea: {last}");
    cleanup(&dir);
}

#[test]
fn modal_focus_trap_only_accepts_its_buttons() {
    let fb = FakeBackend {
        proposals: vec![proposal("p1", true, "instant")],
        ..Default::default()
    };
    let mut st = setup(Screen::Actions, &fb);
    let act = approve_click(&st, 0);
    assert!(update(&mut st, act).is_none());

    // Click afuera del modal: no dispara nada (ni selección ni navegación).
    assert!(
        hit_test(&st, 10, 3).is_none(),
        "el modal captura todo el mouse"
    );
    // Acciones ajenas no cierran el modal.
    assert!(
        update(&mut st, AppAction::Back).is_some(),
        "Esc = denegar (efecto)"
    );
    // (el Back resuelve como denegación: ver test de deny arriba; acá solo se
    // verifica que el reducer NO deja pasar otras acciones)
}

#[test]
fn guarded_menu_row_opens_modal_not_direct_effect() {
    let dir = unique_dir("menu");
    let fb = FakeBackend::default();
    let mut st = setup(Screen::Menu, &fb);
    let log = ActionLog::new(&dir);

    // "remember" es Guarded: el reducer NO emite RunCommand, abre el modal.
    let fx = update(
        &mut st,
        AppAction::RunCommand {
            family: "remember",
            args: vec![],
        },
    );
    assert!(fx.is_none(), "guardada va al modal, no directo");
    let pend = st.pending.clone().expect("modal de menú abierto");
    assert!(pend.req.effect.contains("cortex remember"), "efecto exacto");
    let act = modal_approve_click(&st);
    let fx = update(&mut st, act).expect("ResolveApproval");
    effects::apply(&fb, &log, &mut st, fx);
    // FakeBackend usa el menu_run default del trait ⇒ P6/P9 explícito visible.
    assert!(
        st.menu_output.as_ref().is_some_and(|o| o.is_error),
        "fallo explícito visible"
    );
    let last = log.last_line().expect("auditoría del menú");
    assert!(last.contains("\"outcome\": \"failed\""), "línea: {last}");
    cleanup(&dir);
}

#[test]
fn batch_button_disabled_when_no_batchable() {
    let fb = FakeBackend {
        proposals: vec![proposal("p-no", false, "minutes")],
        ..Default::default()
    };
    let st = setup(Screen::Actions, &fb);
    assert!(
        hit_test(
            &st,
            ACTIONS_BATCH_BTN.x + ACTIONS_BATCH_BTN.width / 2,
            ACTIONS_BATCH_BTN.y
        )
        .is_none(),
        "sin batchables el botón lote está deshabilitado"
    );
}

// ---------------------------------------------------------------------------
// Hover (minor B4/B6): aserción de buffer del estado hover de un botón.
// ---------------------------------------------------------------------------

fn render_actions_buffer(data: &ActionsData, hover: Option<(u16, u16)>) -> ratatui::buffer::Buffer {
    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    term.draw(|f| {
        let mut areas = actions_areas(f.area());
        areas.hover_mouse = hover;
        let _ = render_actions(f, f.area(), data, 0, &mut areas);
    })
    .expect("draw ok");
    term.backend().buffer().clone()
}

#[test]
fn batch_button_hover_paints_accent() {
    let data = ActionsData {
        proposals: vec![proposal("p1", true, "instant")],
        ..Default::default()
    };
    let cell_pos = (ACTIONS_BATCH_BTN.x + 1, ACTIONS_BATCH_BTN.y);
    let cyan = cortex_branding::palette::CYAN;
    let cyan = Color::Rgb(cyan.0, cyan.1, cyan.2);

    let hover = render_actions_buffer(&data, Some(cell_pos));
    let idle = render_actions_buffer(&data, None);

    let fg =
        |buf: &ratatui::buffer::Buffer, pos: (u16, u16)| -> Option<Color> { buf[pos].style().fg };
    assert_eq!(
        fg(&hover, cell_pos),
        Some(cyan),
        "el borde del botón debe pintar el acento cyan con hover"
    );
    assert_ne!(
        fg(&idle, cell_pos),
        Some(cyan),
        "sin hover el botón no usa el acento"
    );
}
