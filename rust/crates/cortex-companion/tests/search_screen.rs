//! B7 — Panel Search + feedback (G-B2d).
//!
//! Cubre: `/` navega a Search; input teclado (Typed/Backspace); Enter con
//! query no vacía dispara `Effect::Search` y vacío NO llama al backend;
//! click [Útil] en fila episódica dispara `Effect::MarkUseful`; `effects::apply`
//! persiste feedback en `.cortex/feedback.jsonl` con el MISMO formato del
//! escritor del oráculo (`cortex/feedback_loop.py::add_feedback` +
//! `FeedbackStore.append`: claves en orden type, memory_id, feedback_type,
//! source, y ts completado al final; separadores `, `/`: `; feedback_type
//! "positive" como la TUI) y es idempotente por hit; filas semánticas no
//! tienen botón (sin memory_id, como core.py:274).

use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::{Frame, Terminal};

use cortex_companion::app::{
    hit_test, update, AppAction, AppState, Effect, SEARCH_LIST_TOP, SEARCH_USEFUL_X,
};
use cortex_companion::approval::ActionLog;
use cortex_companion::effects;
use cortex_companion::engine::{Backend, DoctorSummary, SearchHit, SessionSummary, StatsSummary};
use cortex_companion::feedback::{self, AppendOutcome};
use cortex_companion::screens::search_screen::{render_search, search_areas, SearchData};
use cortex_companion::{Screen, UiRequest};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn tmp_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dst = std::env::temp_dir().join(format!("cortex-companion-{tag}-{nanos}"));
    std::fs::create_dir_all(&dst).unwrap();
    dst
}

/// Backend de test: registra queries de búsqueda y escribe feedback real en
/// `feedback_dir` (mismo escritor `feedback.rs` que producción).
#[derive(Default)]
struct FakeBackend {
    hits: Vec<SearchHit>,
    search_calls: Mutex<Vec<String>>,
    feedback_dir: PathBuf,
    search_err: bool,
}

impl FakeBackend {
    fn calls(&self) -> Vec<String> {
        self.search_calls.lock().unwrap().clone()
    }
}

impl Backend for FakeBackend {
    fn session_current(&self) -> Result<Option<SessionSummary>, String> {
        Ok(None)
    }
    fn session_list(&self) -> Result<Vec<SessionSummary>, String> {
        Ok(vec![])
    }
    fn next_actions(&self) -> Result<Vec<cortex_companion::engine::ActionProposal>, String> {
        Ok(vec![])
    }
    fn search(&self, query: &str, _top_k: usize) -> Result<Vec<SearchHit>, String> {
        self.search_calls.lock().unwrap().push(query.to_string());
        if self.search_err {
            return Err("boom".into());
        }
        Ok(self.hits.clone())
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
    fn session_detail(&self, _session_id: &str) -> Result<Vec<String>, String> {
        Ok(vec![])
    }
    fn close_session(&self, _session_id: &str) -> Result<(), String> {
        Err("n/a".into())
    }
    fn checkpoint_session(&self, _note: &str) -> Result<(), String> {
        Err("n/a".into())
    }
    fn approve_action(&self, _action_id: &str) -> Result<(), String> {
        Err("n/a".into())
    }
    fn mark_useful(&self, memory_id: &str) -> Result<AppendOutcome, String> {
        feedback::append_useful(&self.feedback_dir, "companion", memory_id, 5 * 1024 * 1024)
    }
}

fn episodic_hit(id: &str, title: &str) -> SearchHit {
    SearchHit {
        source: "episodic".into(),
        title: title.into(),
        path: "memory/memories.jsonl".into(),
        score: 0.9,
        snippet: format!("contenido de {title}"),
        id: Some(id.into()),
    }
}

fn semantic_hit(path: &str) -> SearchHit {
    SearchHit {
        source: "semantic".into(),
        title: path.into(),
        path: path.into(),
        score: 0.4,
        snippet: "seccion del vault".into(),
        id: None,
    }
}

fn search_state(be: &FakeBackend) -> AppState {
    let _ = be;
    AppState::new(UiRequest {
        screen: Screen::Search,
        project_root: PathBuf::from("/tmp"),
    })
}

/// Simula tipear la consulta completa (carácter a carácter, como teclado real).
fn type_query(st: &mut AppState, q: &str) {
    for c in q.chars() {
        let fx = update(st, AppAction::Typed(c));
        assert!(fx.is_none(), "teclear no produce efectos");
    }
}

fn feedback_lines(dir: &Path) -> Vec<String> {
    let path = dir.join("feedback.jsonl");
    match std::fs::read_to_string(&path) {
        Ok(s) => s.lines().map(str::to_string).collect(),
        Err(_) => vec![],
    }
}

// ---------------------------------------------------------------------------
// Reducer: input de teclado y navegación
// ---------------------------------------------------------------------------

#[test]
fn slash_navigates_to_search_from_other_screens() {
    let mut st = AppState::new(UiRequest {
        screen: Screen::Home,
        project_root: PathBuf::from("/tmp"),
    });
    let fx = update(&mut st, AppAction::Typed('/'));
    assert!(fx.is_none());
    assert_eq!(st.screen, Screen::Search);
    assert_eq!(st.stack.last(), Some(&Screen::Home));
    // Back con Esc vuelve (mapeo dual teclado, accesibilidad).
    update(&mut st, AppAction::Back);
    assert_eq!(st.screen, Screen::Home);
}

#[test]
fn slash_in_search_is_query_text_not_navigation() {
    let be = FakeBackend::default();
    let mut st = search_state(&be);
    type_query(&mut st, "a/b");
    assert_eq!(st.search.query, "a/b");
    assert_eq!(st.screen, Screen::Search);
}

#[test]
fn backspace_edits_query() {
    let be = FakeBackend::default();
    let mut st = search_state(&be);
    type_query(&mut st, "auth");
    update(
        &mut st,
        AppAction::Key(crossterm::event::KeyCode::Backspace),
    );
    assert_eq!(st.search.query, "aut");
}

// ---------------------------------------------------------------------------
// Brief Step 1: empty query no llama al backend
// ---------------------------------------------------------------------------

#[test]
fn empty_query_does_not_search() {
    let be = FakeBackend::default();
    let mut st = search_state(&be);
    // query vacía ⇒ ningún efecto, ninguna llamada.
    let fx = update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter));
    assert!(fx.is_none(), "Enter con query vacía no debe buscar");
    // sólo espacios tampoco.
    type_query(&mut st, "   ");
    let fx = update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter));
    assert!(fx.is_none(), "Enter con query en blanco no debe buscar");
    assert!(be.calls().is_empty(), "el backend no fue invocado");
}

// ---------------------------------------------------------------------------
// Brief Step 1: search corre híbrida (vía Backend::search) + [Útil] persiste
// ---------------------------------------------------------------------------

#[test]
fn search_runs_hybrid_and_marks_useful() {
    let dir = tmp_dir("b7-search");
    let be = FakeBackend {
        hits: vec![
            episodic_hit("mem_a1b2c3d4", "auth refactor"),
            semantic_hit("vault/x.md"),
        ],
        feedback_dir: dir.clone(),
        ..Default::default()
    };
    let log = ActionLog::new(&dir);
    let mut st = search_state(&be);

    // tipear + Enter ⇒ efecto Search con la query exacta
    type_query(&mut st, "auth");
    let fx = update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter))
        .expect("Enter con query dispara efecto");
    assert_eq!(
        fx,
        Effect::Search {
            query: "auth".into()
        }
    );
    effects::apply(&be, &log, &mut st, fx);
    assert_eq!(be.calls(), vec!["auth".to_string()]);
    assert_eq!(st.search.hits.len(), 2);
    assert!(st.search.error.is_none());

    // click [Útil] del hit 0 (episódico): fila SEARCH_LIST_TOP, columna
    // USEFUL ⇒ hit_test produce MarkUseful con el memory_id del hit.
    let act = hit_test(&st, SEARCH_USEFUL_X + 1, SEARCH_LIST_TOP)
        .expect("la fila episódica tiene botón [Útil]");
    assert_eq!(
        act,
        AppAction::MarkUseful {
            memory_id: "mem_a1b2c3d4".into()
        }
    );
    let fx = update(&mut st, act).expect("MarkUseful dispara efecto");
    assert_eq!(
        fx,
        Effect::MarkUseful {
            memory_id: "mem_a1b2c3d4".into()
        }
    );
    effects::apply(&be, &log, &mut st, fx);

    // feedback.jsonl: UNA línea con el formato exacto del escritor oráculo
    // (orden type, memory_id, feedback_type, source, ts-apendado-al-final;
    // separadores ", " / ": "; feedback_type "positive" como la TUI).
    let lines = feedback_lines(&dir);
    assert_eq!(lines.len(), 1, "una sola línea persistida: {lines:?}");
    let l = &lines[0];
    assert!(
        l.starts_with(
            "{\"type\": \"explicit\", \"memory_id\": \"mem_a1b2c3d4\", \"feedback_type\": \"positive\", \"source\": \"companion\", \"ts\": \""
        ),
        "formato oráculo violado: {l}"
    );
    assert!(l.ends_with("+00:00\"}"), "ts ISO con offset al final: {l}");
    // legible por el lector del motor (signals.rs cuenta positivos).
    let v: serde_json::Value = serde_json::from_str(l).unwrap();
    assert_eq!(v["feedback_type"], "positive");
    assert_eq!(v["type"], "explicit");
    assert_eq!(
        v["ts"].as_str().unwrap().chars().count(),
        "2026-01-01T00:00:00.000+00:00".chars().count(),
        "ts con milisegundos (timespec=milliseconds del oráculo)"
    );

    // outcome visible y marcado en el estado (✓ en la fila).
    let (msg, is_err) = st.search.outcome.clone().expect("outcome tras marcar");
    assert!(!is_err);
    assert!(msg.contains("mem_a1b2c3d4"), "{msg}");
    assert_eq!(st.search.marked, vec!["mem_a1b2c3d4".to_string()]);

    // IDEMPOTENCIA por hit: segundo clic no duplica la línea.
    let act = hit_test(&st, SEARCH_USEFUL_X + 1, SEARCH_LIST_TOP).unwrap();
    let fx = update(&mut st, act).unwrap();
    effects::apply(&be, &log, &mut st, fx);
    assert_eq!(feedback_lines(&dir).len(), 1, "idempotente por hit");
    let (msg2, _) = st.search.outcome.clone().unwrap();
    assert!(
        msg2.contains("ya"),
        "segundo clic informa sin duplicar: {msg2}"
    );
    assert_eq!(st.search.marked.len(), 1);
}

#[test]
fn semantic_rows_have_no_useful_button() {
    let dir = tmp_dir("b7-sem");
    let be = FakeBackend {
        hits: vec![semantic_hit("vault/x.md")],
        feedback_dir: dir.clone(),
        ..Default::default()
    };
    let mut st = search_state(&be);
    st.search = SearchData {
        query: "x".into(),
        hits: be.hits.clone(),
        ..Default::default()
    };
    // click en la columna [Útil] de una fila SEMÁNTICA ⇒ sin acción (core.py
    // exige getattr(hit.entry,'id'); None ⇒ nada que puntuar).
    assert!(hit_test(&st, SEARCH_USEFUL_X + 1, SEARCH_LIST_TOP).is_none());
    // click en el cuerpo de la fila ⇒ seleccionar (abrir detalle).
    match hit_test(&st, 5, SEARCH_LIST_TOP) {
        Some(AppAction::SelectHit { index: 0 }) => {}
        other => panic!("click en fila semántica debe seleccionar, vino {other:?}"),
    }
}

#[test]
fn search_error_is_visible_never_silent() {
    let dir = tmp_dir("b7-err");
    let be = FakeBackend {
        feedback_dir: dir.clone(),
        search_err: true,
        ..Default::default()
    };
    let log = ActionLog::new(&dir);
    let mut st = search_state(&be);
    type_query(&mut st, "z");
    let fx = update(&mut st, AppAction::Key(crossterm::event::KeyCode::Enter)).unwrap();
    effects::apply(&be, &log, &mut st, fx);
    assert_eq!(st.search.error.as_deref(), Some("boom"), "P6/P9 visible");
    assert!(st.search.hits.is_empty());
}

// ---------------------------------------------------------------------------
// feedback.rs — escritor formato oráculo (unidades puras de fs)
// ---------------------------------------------------------------------------

#[test]
fn feedback_dedupe_recognizes_both_positive_aliases() {
    let dir = tmp_dir("b7-dedupe");
    std::fs::create_dir_all(&dir).unwrap();
    // una línea preexistente escrita con "useful" (variante que signals.rs
    // también cuenta como positiva) ⇒ no debe duplicarse con "positive".
    std::fs::write(
        dir.join("feedback.jsonl"),
        "{\"type\": \"explicit\", \"memory_id\": \"mem_deadbeef\", \"feedback_type\": \"useful\", \"source\": \"tui\", \"ts\": \"2026-08-01T00:00:00.000+00:00\"}\n",
    )
    .unwrap();
    let out = feedback::append_useful(&dir, "companion", "mem_deadbeef", 5 * 1024 * 1024).unwrap();
    assert_eq!(out, AppendOutcome::AlreadyMarked);
    assert_eq!(feedback_lines(&dir).len(), 1);
    // otra memoria sí se apenda.
    let out = feedback::append_useful(&dir, "companion", "mem_cafe0001", 5 * 1024 * 1024).unwrap();
    assert_eq!(out, AppendOutcome::Appended);
    assert_eq!(feedback_lines(&dir).len(), 2);
}

#[test]
fn feedback_rotates_at_max_bytes_preserving_generation() {
    let dir = tmp_dir("b7-rot");
    // cap mínimo 1 byte para provocar rotación inmediata (campo max_bytes).
    std::fs::create_dir_all(&dir).unwrap();
    feedback::append_useful(&dir, "companion", "mem_00000001", 10).unwrap();
    assert!(dir.join("feedback.jsonl").exists());
    feedback::append_useful(&dir, "companion", "mem_00000002", 10).unwrap();
    // primer archivo superó el cap ⇒ se rotó a .1.jsonl y el nuevo quedó solo.
    assert!(dir.join("feedback.1.jsonl").exists(), "rotación aplicada");
    let cur = feedback_lines(&dir);
    assert_eq!(cur.len(), 1, "el archivo vigente quedó fresco: {cur:?}");
    assert!(cur[0].contains("mem_00000002"));
    // tercera escritura reemplaza la generación anterior (v1 del oráculo).
    feedback::append_useful(&dir, "companion", "mem_00000003", 10).unwrap();
    let rot = std::fs::read_to_string(dir.join("feedback.1.jsonl")).unwrap();
    assert!(
        !rot.contains("mem_00000001"),
        "una sola generación histórica"
    );
}

#[test]
fn feedback_line_serialization_matches_python_dumps() {
    // golden byte-a-byte del formato (json.dumps default separators +
    // ensure_ascii=False; los campos escritos son ASCII ⇒ coincide con el
    // escaper ensure_ascii=True de pyjson para estos valores).
    let line = feedback::dumps_event(
        "explicit",
        "mem_a1b2c3d4",
        "positive",
        "companion",
        "2026-08-28T12:34:56.123+00:00",
    );
    assert_eq!(
        line,
        "{\"type\": \"explicit\", \"memory_id\": \"mem_a1b2c3d4\", \"feedback_type\": \"positive\", \"source\": \"companion\", \"ts\": \"2026-08-28T12:34:56.123+00:00\"}"
    );
}

// ---------------------------------------------------------------------------
// Render (snapshot + presupuesto, patrón screens_snapshot.rs)
// ---------------------------------------------------------------------------

#[test]
fn search_screen_renders_input_hits_and_budget() {
    let data = SearchData {
        query: "auth".into(),
        hits: vec![
            episodic_hit("mem_a1b2c3d4", "refactor auth"),
            episodic_hit("mem_0dd1beef", "oauth flow"),
            semantic_hit("vault/x.md"),
        ],
        selected: Some(0),
        marked: vec!["mem_a1b2c3d4".into()],
        outcome: Some(("marcado útil: mem_a1b2c3d4".into(), false)),
        error: None,
    };
    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    let mut spent = 0f32;
    term.draw(|f: &mut Frame<'_>| {
        let area: Rect = f.area();
        let mut areas = search_areas(area);
        let info = render_search(f, area, &data, 0, &mut areas);
        spent = info.spent_ms;
    })
    .expect("draw ok");
    let buf = term.backend().buffer().clone();
    // Mismo extractor que screens_snapshot.rs: símbolos no vacíos concatenados
    // (una fila = cadena continua).
    let mut text = String::new();
    for cell in buf.content() {
        let sym = cell.symbol();
        if !sym.is_empty() {
            text.push(sym.chars().next().unwrap());
        }
    }
    assert!(text.contains("consulta: auth"), "input visible: {text}");
    assert!(
        text.contains("[ Útil ]"),
        "botón en fila episódica no marcada"
    );
    assert!(text.contains("✓"), "marca de ya-útil en la fila marcada");
    assert!(text.contains("refactor auth"), "título del hit");
    assert!(text.contains("SEM"), "badge semántico");
    assert!(spent < 50.0, "presupuesto de render: {spent}ms");
}

#[test]
fn search_screen_prompts_empty_input() {
    let data = SearchData::default();
    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    term.draw(|f: &mut Frame<'_>| {
        let area: Rect = f.area();
        let mut areas = search_areas(area);
        let _info = render_search(f, area, &data, 0, &mut areas);
    })
    .expect("draw ok");
    let buf = term.backend().buffer().clone();
    let mut text = String::new();
    for cell in buf.content() {
        let sym = cell.symbol();
        if !sym.is_empty() {
            text.push(sym.chars().next().unwrap());
        }
    }
    // sin query: el panel explica el atajo; nunca una lista vacía muda.
    assert!(
        text.contains("escribí una consulta"),
        "hint de navegación: {text}"
    );
}
