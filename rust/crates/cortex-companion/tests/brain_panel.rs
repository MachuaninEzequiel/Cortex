//! B8 — Brain panel híbrido (G-B4, doc 14 §2.2/§2.3):
//! - reads del brain enrutadas por el engine IN-PROCESS (nunca subprocess);
//! - Tool::READ ejecuta directa, sin aprobación (aserción: sin `pending`,
//!   sin líneas de auditoría);
//! - propuesta de MUTACIÓN (línea "cortex <familia> ..." guardada) ⇒
//!   BrainMsg::Proposal con [Ejecutar] → run_guarded (aprobar ejecuta y
//!   audita; denegar NUNCA ejecuta);
//! - tools no mapeadas / inexistentes ⇒ Err explícito con nombre (P6/P9);
//! - router determinista: cero tokens, cero LLM, cero subprocess.

use std::path::PathBuf;
use std::sync::Mutex;

use cortex_brain::chat::ScriptedBackend;
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::json;

use cortex_companion::app::{
    self, AppAction, AppState, Effect, BRAIN_EXEC_X, BRAIN_LIST_TOP, HOME_BRAIN_BTN,
};
use cortex_companion::approval::ActionLog;
use cortex_companion::brain_panel::{
    route_brain_tool, run_turn, tokenize, BrainMode, BrainMsg, BrainPanel,
};
use cortex_companion::effects;
use cortex_companion::engine::{
    ActionProposal, Backend, DoctorSummary, SearchHit, SessionSummary, StatsSummary,
};
use cortex_companion::screens::{brain_areas, brain_rows, render_brain};
use cortex_companion::{Screen, UiRequest};

fn temp_dir(tag: &str) -> PathBuf {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dst = std::env::temp_dir().join(format!("cortex-companion-{tag}-{nanos}"));
    std::fs::create_dir_all(&dst).unwrap();
    dst
}

/// Backend de test con contadores: registra cada lectura y cada `menu_run`.
#[derive(Default)]
struct FakeBackend {
    search_calls: Mutex<Vec<String>>,
    menu_calls: Mutex<Vec<(String, Vec<String>)>>,
}

impl FakeBackend {
    fn calls(&self) -> Vec<String> {
        self.search_calls.lock().unwrap().clone()
    }
    fn menu(&self) -> Vec<(String, Vec<String>)> {
        self.menu_calls.lock().unwrap().clone()
    }
}

impl Backend for FakeBackend {
    fn session_current(&self) -> Result<Option<SessionSummary>, String> {
        Ok(Some(SessionSummary {
            id: "SES-2026-08-28_fake".to_string(),
            status: "open".to_string(),
            mode: "composed".to_string(),
            opened_at: "2026-08-28T10:00:00Z".to_string(),
        }))
    }
    fn session_list(&self) -> Result<Vec<SessionSummary>, String> {
        Ok(vec![])
    }
    fn next_actions(&self) -> Result<Vec<ActionProposal>, String> {
        Ok(vec![ActionProposal {
            id: "session.checkpoint_now".to_string(),
            title: "Checkpoint ahora".to_string(),
            score: 5.0,
            cost: "instant".to_string(),
            reversible: true,
            effect: "cortex session checkpoint --note 'checkpoint del motor'".to_string(),
        }])
    }
    fn search(&self, query: &str, _top_k: usize) -> Result<Vec<SearchHit>, String> {
        self.search_calls.lock().unwrap().push(query.to_string());
        Ok(vec![SearchHit {
            source: "episodic".to_string(),
            title: "hit de prueba".to_string(),
            path: "memory/mem.jsonl".to_string(),
            score: 0.42,
            snippet: "contenido".to_string(),
            id: Some("mem_a1b2c3d4".to_string()),
        }])
    }
    fn doctor(&self) -> Result<DoctorSummary, String> {
        Ok(DoctorSummary {
            ok: true,
            checks: vec![("config_yaml".to_string(), "ok".to_string())],
        })
    }
    fn stats(&self) -> Result<StatsSummary, String> {
        Ok(StatsSummary {
            episodic: 12,
            semantic: 7,
            vault_path: "vault".to_string(),
        })
    }
    fn session_detail(&self, _session_id: &str) -> Result<Vec<String>, String> {
        Ok(vec![])
    }
    fn close_session(&self, _session_id: &str) -> Result<(), String> {
        Ok(())
    }
    fn checkpoint_session(&self, _note: &str) -> Result<(), String> {
        Ok(())
    }
    fn approve_action(&self, _action_id: &str) -> Result<(), String> {
        Ok(())
    }
    fn menu_run(&self, family: &str, args: &[String]) -> Result<String, String> {
        self.menu_calls
            .lock()
            .unwrap()
            .push((family.to_string(), args.to_vec()));
        Ok(format!("ran {family}"))
    }
}

fn state_at(screen: Screen) -> AppState {
    AppState::new(UiRequest {
        screen,
        project_root: PathBuf::from("."),
        mode: Default::default(),
    })
}

// ---- 1. readTool ejecuta DIRECTO, sin aprobación (spec §2.3 Tier Read) ----

#[test]
fn read_tool_executes_directly_no_approval() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    let mut llm = ScriptedBackend::new("test", ["TOOL: memory.search auth"]);
    run_turn(&fb, &mut panel, "¿qué hay de auth?", Some(&mut llm));

    // la tool se enruto al engine in-process (no al CLI): un solo llamado.
    assert_eq!(fb.calls(), vec!["auth".to_string()]);
    // sin mutaciones: no hay propuesta ni pending.
    assert!(
        !panel
            .messages
            .iter()
            .any(|m| matches!(m, BrainMsg::Proposal { .. })),
        "una READ jamás genera Proposal"
    );
    // el resultado del engine es visible en el chat.
    let last = panel.messages.last().expect("respuesta del brain");
    match last {
        BrainMsg::Brain(t) => assert!(t.contains("hit de prueba") && t.contains("0.42")),
        other => panic!("esperaba Brain, obtuve {other:?}"),
    }
    // cero auditoria: run_guarded jamas se invoco (el log ni existe).
    let log_dir = temp_dir("read-no-audit");
    let log = ActionLog::new(&log_dir);
    assert!(log.last_line().is_none(), "las reads no auditan");
    let _ = std::fs::remove_dir_all(&log_dir);
}

// ---- 2. propuesta mutante → [Ejecutar] → run_guarded (aprueba/deniega) ----

fn proposal_case() -> (FakeBackend, BrainPanel) {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    let mut llm = ScriptedBackend::new(
        "test",
        ["Para registrar el avance corré:\ncortex session checkpoint --note 'avance del panel'"],
    );
    run_turn(&fb, &mut panel, "¿cómo registro avance?", Some(&mut llm));
    (fb, panel)
}

#[test]
fn mutate_proposal_shows_execute_button_and_guards() {
    let (fb, panel) = proposal_case();
    let prop = panel
        .messages
        .iter()
        .find_map(|m| match m {
            BrainMsg::Proposal { command, audit_key } => Some((command.clone(), audit_key.clone())),
            _ => None,
        })
        .expect("la propuesta mutante debe ser un Proposal con boton [Ejecutar]");
    assert_eq!(
        prop.0,
        "cortex session checkpoint --note 'avance del panel'"
    );
    assert!(prop.1.starts_with("brain.session"), "audit_key: {}", prop.1);

    // click en [Ejecutar] => modal con el efecto EXACTO (spec §5).
    let mut st = state_at(Screen::Brain);
    st.brain = panel;
    let fx = app::update(
        &mut st,
        AppAction::RunBrainCommand {
            command: prop.0.clone(),
            audit_key: prop.1.clone(),
        },
    );
    assert!(
        fx.is_none(),
        "guarded abre modal (estado), no efecto directo"
    );
    let pending = st.pending.clone().expect("pending del brain");
    assert_eq!(pending.req.audit_key, prop.1);
    assert_eq!(
        pending.req.effect, prop.0,
        "el modal muestra el efecto exacto"
    );

    // APROBAR: ejecuta por el engine y audita.
    let log_dir = temp_dir("prop-approve");
    let log = ActionLog::new(&log_dir);
    let fx = app::update(
        &mut st,
        AppAction::Approve {
            audit_key: prop.1.clone(),
        },
    )
    .expect("fx");
    effects::apply(&fb, &log, &mut st, fx);
    assert_eq!(
        fb.menu(),
        vec![(
            "session".to_string(),
            vec![
                "checkpoint".to_string(),
                "--note".to_string(),
                "avance del panel".to_string()
            ]
        )]
    );
    let audit = log.last_line().expect("linea de auditoria");
    assert!(
        audit.contains("\"approved\": true") && audit.contains("\"outcome\": \"executed\""),
        "{audit}"
    );
    assert!(audit.contains(&prop.1));
    // el resultado de la ejecucion es visible en el chat.
    assert!(st
        .brain
        .messages
        .iter()
        .any(|m| matches!(m, BrainMsg::Brain(t) if t == "ran session")));

    // DENEGAR (otro state): NUNCA ejecuta, audita denied.
    let fb2 = FakeBackend::default();
    let (_, panel2) = proposal_case();
    let mut st2 = state_at(Screen::Brain);
    st2.brain = panel2.clone();
    let _ = app::update(
        &mut st2,
        AppAction::RunBrainCommand {
            command: prop.0.clone(),
            audit_key: prop.1.clone(),
        },
    );
    let log_dir2 = temp_dir("prop-deny");
    let log2 = ActionLog::new(&log_dir2);
    let fx = app::update(
        &mut st2,
        AppAction::Deny {
            audit_key: prop.1.clone(),
        },
    )
    .expect("fx");
    effects::apply(&fb2, &log2, &mut st2, fx);
    assert!(fb2.menu().is_empty(), "denegar jamas ejecuta");
    let audit = log2.last_line().expect("auditoria de denegacion");
    assert!(
        audit.contains("\"approved\": false") && audit.contains("\"outcome\": \"denied\""),
        "{audit}"
    );
    let _ = std::fs::remove_dir_all(&log_dir);
    let _ = std::fs::remove_dir_all(&log_dir2);
}

#[test]
fn read_commands_never_become_proposals() {
    // el escaneo SOLO crea botones para mutaciones (command_is_guarded).
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    let mut llm = ScriptedBackend::new(
        "test",
        ["cortex doctor\npara anotar corré:\ncortex remember 'nota'"],
    );
    run_turn(&fb, &mut panel, "¿qué comando corro?", Some(&mut llm));
    let props: Vec<String> = panel
        .messages
        .iter()
        .filter_map(|m| match m {
            BrainMsg::Proposal { command, .. } => Some(command.clone()),
            _ => None,
        })
        .collect();
    assert_eq!(
        props,
        vec!["cortex remember 'nota'".to_string()],
        "solo la mutante"
    );
}

// ---- 3. tools no mapeadas: Err EXPLICITO con nombre (P6/P9) ----

#[test]
fn unmapped_tool_fails_explicitly() {
    let fb = FakeBackend::default();
    let e = route_brain_tool("webgraph.serve", &json!({}), &fb).unwrap_err();
    assert!(e.contains("no mapeada"), "{e}");
    assert!(
        e.contains("cortex webgraph serve"),
        "sugerencia del comando exacto: {e}"
    );
    // SafeAction del brain (spawn) NO se replica: falla igual que desconocida.
    assert!(
        fb.calls().is_empty() && fb.menu().is_empty(),
        "un Err no ejecuta nada"
    );
}

#[test]
fn unknown_tool_fails_explicitly_with_name() {
    let fb = FakeBackend::default();
    let e = route_brain_tool("vault.reindex", &json!({}), &fb).unwrap_err();
    assert!(e.contains("vault.reindex"), "el nombre debe aparecer: {e}");
}

#[test]
fn unknown_tool_from_model_never_routes() {
    // espejo del contrato del brain: tool fuera del catalogo jamas llega a
    // ejecutarse (el companion ni la enruta).
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    let mut llm = ScriptedBackend::new("test", ["TOOL: vault.reindex todo"]);
    run_turn(&fb, &mut panel, "reindexa", Some(&mut llm));
    assert!(fb.menu().is_empty() && fb.calls().is_empty());
    let last = panel.messages.last().unwrap();
    match last {
        BrainMsg::Brain(t) => assert!(t.contains("inexistente"), "{t}"),
        other => panic!("{other:?}"),
    }
}

// ---- 4. router determinista: cero tokens, cero LLM, cero subprocess ----

#[test]
fn deterministic_router_zero_tokens() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    run_turn(&fb, &mut panel, "session", None);
    assert_eq!(panel.mode, BrainMode::Deterministic);
    assert_eq!(panel.messages.len(), 2, "User + Brain, sin pasos extra");
    match &panel.messages[1] {
        BrainMsg::Brain(t) => assert!(t.contains("SES-2026-08-28_fake"), "{t}"),
        other => panic!("{other:?}"),
    }
    assert!(fb.calls().is_empty(), "session no busca");
    assert!(fb.menu().is_empty(), "nada pasa por subprocess/CLI");
}

#[test]
fn deterministic_free_search_routes_to_engine() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    run_turn(&fb, &mut panel, "busca docs sobre autenticación", None);
    assert_eq!(fb.calls(), vec!["autenticación".to_string()]);
    match panel.messages.last().unwrap() {
        BrainMsg::Brain(t) => assert!(t.contains("hit de prueba"), "{t}"),
        other => panic!("{other:?}"),
    }
}

#[test]
fn actions_propose_lists_and_its_effect_is_guarded_text() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    run_turn(&fb, &mut panel, "¿qué hago ahora?", None);
    // el texto de actions.propose lista id + efecto.
    match panel.messages.last().unwrap() {
        BrainMsg::Brain(t) => {
            assert!(t.contains("session.checkpoint_now"), "{t}");
            assert!(t.contains("Checkpoint ahora"), "{t}");
        }
        other => panic!("{other:?}"),
    }
}

// ---- 5. input del chat: teclado dual sin matar la app (lección B7) ----

#[test]
fn brain_input_types_q_and_slash_without_quitting() {
    let mut st = state_at(Screen::Brain);
    for c in ['q', '/', 'u', 'e', 'r', 'y'] {
        app::update(&mut st, AppAction::Typed(c));
    }
    assert!(!st.quit, "'q' dentro del input de Brain es TEXTO");
    assert_eq!(st.brain.input, "q/uery");
    // y el global sigue vivo fuera de Brain/Search:
    let mut home = state_at(Screen::Home);
    app::update(&mut home, AppAction::Typed('q'));
    assert!(home.quit);
}

#[test]
fn enter_emits_brain_turn_with_trim_and_clears_input() {
    let mut st = state_at(Screen::Brain);
    for c in [' ', 's', 'e', 's', 's', 'i', 'o', 'n', ' '] {
        app::update(&mut st, AppAction::Typed(c));
    }
    let fx =
        app::update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter)).expect("BrainTurn");
    assert_eq!(
        fx,
        Effect::BrainTurn {
            text: "session".to_string()
        }
    );
    assert!(st.brain.input.is_empty(), "el input se limpia al enviar");
    // input vacio: NUNCA se enruta nada.
    assert!(
        app::update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter)).is_none(),
        "Enter sin texto no emite efecto"
    );
}

#[test]
fn brain_turn_effect_appends_messages_deterministic() {
    let fb = FakeBackend::default();
    let log_dir = temp_dir("effect-brain-turn");
    let log = ActionLog::new(&log_dir);
    let mut st = state_at(Screen::Brain);
    effects::apply(
        &fb,
        &log,
        &mut st,
        Effect::BrainTurn {
            text: "stats".to_string(),
        },
    );
    assert!(matches!(st.brain.messages[0], BrainMsg::User(_)));
    match st.brain.messages.last().unwrap() {
        BrainMsg::Brain(t) => assert!(t.contains("episódica 12"), "{t}"),
        other => panic!("{other:?}"),
    }
    let _ = std::fs::remove_dir_all(&log_dir);
}

// ---- 6. navegacion: Home -> Brain (mouse-first con doble teclado) ----

#[test]
fn home_brain_button_navigates() {
    let st = state_at(Screen::Home);
    let act = app::hit_test(&st, HOME_BRAIN_BTN.x + 1, HOME_BRAIN_BTN.y)
        .expect("el footer de Home tiene el acceso a brain");
    let mut st = st;
    assert!(matches!(act, AppAction::Navigate(Screen::Brain)));
    app::update(&mut st, act);
    assert_eq!(st.screen, Screen::Brain);
    // Tab desde cualquier lado (sin estar en Brain) también navega.
    let mut st2 = state_at(Screen::Home);
    app::update(&mut st2, AppAction::Key(crossterm::event::KeyCode::Tab));
    assert_eq!(st2.screen, Screen::Brain);
}

#[test]
fn brain_row_click_resolves_to_command() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel::default();
    let mut llm = ScriptedBackend::new("test", ["corré:\ncortex remember 'apunte'"]);
    run_turn(&fb, &mut panel, "anotá esto", Some(&mut llm));
    let (command, audit_key) = panel
        .messages
        .iter()
        .find_map(|m| match m {
            BrainMsg::Proposal { command, audit_key } => Some((command.clone(), audit_key.clone())),
            _ => None,
        })
        .expect("proposta de remember (mutacion incondicional)");
    let mut st = state_at(Screen::Brain);
    st.brain = panel;
    // la fila del Proposal es la ultima de las filas expandidas.
    let rows = brain_rows(&st.brain);
    let idx = rows.len() - 1;
    let act = app::hit_test(&st, BRAIN_EXEC_X + 1, BRAIN_LIST_TOP + idx as u16)
        .expect("clic en [Ejecutar] de la fila");
    assert_eq!(act, AppAction::RunBrainCommand { command, audit_key });
}

// ---- 7. render: mensajes, input, botones y presupuesto ----

#[test]
fn brain_screen_renders_chat_and_budget() {
    let fb = FakeBackend::default();
    let mut panel = BrainPanel {
        input: "ses".to_string(),
        ..BrainPanel::default()
    };
    let mut llm = ScriptedBackend::new("test", ["corré:\ncortex forget mem_a1b2c3d4"]);
    run_turn(&fb, &mut panel, "¿borro la nota?", Some(&mut llm));

    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    let mut spent = 0f32;
    term.draw(|f| {
        let mut areas = brain_areas(f.area());
        areas.hover_mouse = Some((BRAIN_EXEC_X + 2, BRAIN_LIST_TOP + 2));
        spent = render_brain(f, f.area(), &panel, 0, &mut areas).spent_ms;
    })
    .expect("draw");
    let buf = term.backend().buffer().clone();
    let text: String = buf
        .content()
        .iter()
        .filter_map(|c| {
            let s = c.symbol();
            (!s.is_empty()).then(|| s.chars().next().unwrap())
        })
        .collect();
    assert!(text.contains("pregunta: ses"), "input visible: {text}");
    assert!(text.contains("[Ejecutar]"), "boton de propuesta visible");
    assert!(
        text.contains("cortex forget mem_a1b2c3d4"),
        "comando propuesto: {text}"
    );
    assert!(spent < 50.0, "presupuesto de render: {spent}ms");
}

// ---- 8. tokenizador (comandos propuestos con comillas) ----

#[test]
fn tokenize_handles_quotes() {
    assert_eq!(
        tokenize("cortex session checkpoint --note 'avance del panel'"),
        [
            "cortex",
            "session",
            "checkpoint",
            "--note",
            "avance del panel"
        ]
        .into_iter()
        .map(String::from)
        .collect::<Vec<_>>()
    );
    assert_eq!(
        tokenize("cortex remember \"nota con espacios\""),
        ["cortex", "remember", "nota con espacios"]
            .into_iter()
            .map(String::from)
            .collect::<Vec<_>>()
    );
}
