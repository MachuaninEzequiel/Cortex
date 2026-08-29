//! Snapshots y presupuesto del render Home (G-B2b): render a Buffer sin
//! terminal real (TestBackend de ratatui), hit-test coherente con las consts
//! de `app.rs`, y presupuesto <50 ms (gate P10 pattern).

use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::{Frame, Terminal};

use cortex_companion::app::{HOME_ACTIONS_BTN, HOME_SESSIONS_BTN};
use cortex_companion::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary};
use cortex_companion::screens::home::{
    home_areas, render_home, AppRenderInfo, BrandAssets, HomeData,
};

fn proposal(id: &str, score: f64) -> ActionProposal {
    ActionProposal {
        id: id.into(),
        title: "suggest_next_phase".into(),
        score,
        cost: "instant".into(),
        reversible: true,
        effect: "sugiere la siguiente fase".into(),
    }
}

/// Renderiza el Home a un Buffer 80x24 y devuelve (texto, info del render).
fn render(data: &HomeData) -> (String, AppRenderInfo) {
    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    let mut info: Option<AppRenderInfo> = None;
    term.draw(|f: &mut Frame<'_>| {
        let area = f.area();
        let mut areas = home_areas(area);
        let i = render_home(f, area, data, &BrandAssets::load(), &mut areas);
        info = Some(i);
    })
    .expect("draw ok");
    let buf = term.backend().buffer().clone();
    let mut content = String::with_capacity(buf.area.width as usize * buf.area.height as usize);
    for cell in buf.content.iter() {
        let sym = cell.symbol();
        if !sym.is_empty() {
            content.push(sym.chars().next().unwrap());
        }
    }
    (content, info.expect("render info"))
}

#[test]
fn home_renders_buttons_wordmark_and_budget() {
    let data = HomeData {
        project: "fixture".into(),
        branch: Some("main".into()),
        session: None,
        top_action: Some(proposal("suggest_next_phase", 1.5)),
        doctor: Some(DoctorSummary {
            ok: true,
            checks: vec![("vault".into(), "ok".into()), ("mcp".into(), "ok".into())],
        }),
        stats: Some(StatsSummary {
            episodic: 12,
            semantic: 34,
            vault_path: "vault/".into(),
        }),
        error: None,
        prompt: String::new(),
        hygiene: None,
        agent_label: String::new(),
        ask: String::new(),
    };
    let (text, info) = render(&data);
    // Datos visibles.
    assert!(text.contains("fixture"), "proyecto no renderizado");
    assert!(text.contains("main"), "rama no renderizada");
    assert!(
        text.contains("suggest_next_phase"),
        "top action no renderizada"
    );
    assert!(text.contains("[OK]"), "doctor ok no renderizado");
    assert!(text.contains("12"), "conteo episódico no renderizado");
    // Botones registrados (hit-test del frame siguiente) y render ("Abrir
    // sesión" solo cuando NO hay sesión).
    assert!(info.buttons.iter().any(|b| b.id == "open-session"));
    assert!(info.buttons.iter().any(|b| b.id == "view-actions"));
    assert!(info.buttons.iter().any(|b| b.id == "sessions"));
    assert!(
        text.contains("Abrir sesión"),
        "botón 'Abrir sesión' no visible"
    );
    // Branding pintado (wordmark usa half-blocks ▀/▄/█).
    assert!(text.contains('▀'), "wordmark de branding no renderizado");
    // Presupuesto G-B2b.
    assert!(
        info.spent_ms < 50.0,
        "render {} ms superó presupuesto <50 ms",
        info.spent_ms
    );
}

#[test]
fn home_with_session_hides_open_button_and_shows_id() {
    let data = HomeData {
        project: "p".into(),
        branch: None,
        session: Some(SessionSummary {
            id: "SES-2026-08-28_x".into(),
            status: "OPEN".into(),
            mode: "managed".into(),
            opened_at: "".into(),
        }),
        top_action: None,
        doctor: None,
        stats: None,
        error: None,
        prompt: String::new(),
        hygiene: None,
        agent_label: String::new(),
        ask: String::new(),
    };
    let (text, info) = render(&data);
    assert!(text.contains("SES-2026-08-28_x"), "id de sesión no visible");
    assert!(text.contains("OPEN"), "status OPEN no visible");
    assert!(
        !info.buttons.iter().any(|b| b.id == "open-session"),
        "'Abrir sesión' no debe existir con sesión activa"
    );
}

#[test]
fn home_surfaces_load_error_p6p9() {
    let data = HomeData {
        project: "p".into(),
        error: Some("Cortex no está configurado en X".into()),
        ..Default::default()
    };
    let (text, _info) = render(&data);
    assert!(
        text.contains("Cortex no está configurado"),
        "error de carga debe ser visible, nunca silencioso"
    );
}

#[test]
fn home_areas_use_same_consts_as_hit_test() {
    // Coherencia render ↔ hit-test: MISMAS rects (G-B2b/B3 contract).
    let areas = home_areas(Rect::new(0, 0, 80, 24));
    assert_eq!(areas.sessions_btn, HOME_SESSIONS_BTN);
    assert_eq!(areas.actions_btn, HOME_ACTIONS_BTN);
}

#[test]
fn home_doctor_fail_visible() {
    let data = HomeData {
        project: "p".into(),
        doctor: Some(DoctorSummary {
            ok: false,
            checks: vec![("sessions_dir".into(), "fail".into())],
        }),
        ..Default::default()
    };
    let (text, _info) = render(&data);
    assert!(text.contains("[FAIL]"), "doctor fail debe pintar [FAIL]");
}
