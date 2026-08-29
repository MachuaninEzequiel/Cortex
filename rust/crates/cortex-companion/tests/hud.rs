//! HUD v1 (doc 17): layout, hit-test, Copiar, Esc sale, sin inyectar.

use std::path::PathBuf;

use crossterm::event::KeyCode;
use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::{Frame, Terminal};

use cortex_companion::app::{hit_test, update, AppAction, AppState, Effect};
use cortex_companion::engine::ActionProposal;
use cortex_companion::screens::home::HomeData;
use cortex_companion::screens::hud_screen::{hud_areas, hud_prompt, is_hygiene, render_hud};
use cortex_companion::{CompanionMode, Screen, UiRequest};

fn req_float() -> UiRequest {
    UiRequest {
        screen: Screen::Home,
        project_root: PathBuf::from("/tmp/fixture"),
        mode: CompanionMode::Float,
    }
}

fn hygiene() -> ActionProposal {
    ActionProposal {
        id: "vault.validate_docs".into(),
        title: "Validar documentos del vault".into(),
        score: 8.0,
        cost: "instant".into(),
        reversible: true,
        effect: "corre DocValidator".into(),
    }
}

#[test]
fn hygiene_filter_rejects_session_lifecycle() {
    assert!(is_hygiene("vault.validate_docs"));
    assert!(is_hygiene("vault.reindex"));
    assert!(!is_hygiene("session.close_stale"));
    assert!(!is_hygiene("session.checkpoint_now"));
    assert!(!is_hygiene("setup.finish_bootstrap"));
}

#[test]
fn hud_render_has_copy_not_dashboard() {
    let data = HomeData {
        project: "/home/chucho/cortex-demo".into(),
        branch: Some("feature/obra17".into()),
        hygiene: Some(hygiene()),
        prompt: "descomponé el plan en tickets según la spec de auth.".into(),
        ..Default::default()
    };
    let mut term = Terminal::new(TestBackend::new(100, 12)).expect("term");
    term.draw(|f: &mut Frame<'_>| {
        let mut areas = hud_areas(f.area());
        let _ = render_hud(f, f.area(), &data, &mut areas);
    })
    .expect("draw");
    let buf = term.backend().buffer();
    let mut text = String::new();
    for cell in buf.content.iter() {
        text.push_str(cell.symbol());
    }
    assert!(text.contains("COMPANION"), "eyebrow");
    assert!(text.contains("Copiar"), "CTA copiar");
    assert!(text.contains("Aprobar"), "higiene");
    assert!(text.contains("preguntale a Cortex"), "ask");
    assert!(!text.contains("Doctor: OK"), "no doctor mentiroso");
    assert!(!text.contains("Sesiones"), "sin botonera de nav");
    assert!(hud_prompt(&data).contains("descomponé el plan"), "prompt");
    assert!(
        text.contains('▀') || text.contains('▄') || text.contains('█'),
        "isotipo en half-blocks, no placa"
    );
}

#[test]
fn hud_brand_column_matches_grid() {
    let wide = hud_areas(Rect::new(0, 0, 100, 12));
    assert_eq!(wide.brand.width, 28);
    assert_eq!(wide.mark.x, 1);
    assert_eq!(wide.word.height, 3);
    let narrow = hud_areas(Rect::new(0, 0, 80, 12));
    assert_eq!(narrow.brand.width, 22);
}

#[test]
fn hud_copy_click_emits_copy_prompt() {
    let mut st = AppState::new(req_float());
    st.hud_prompt = "pegame esto".into();
    let mut term = Terminal::new(TestBackend::new(100, 12)).expect("term");
    term.draw(|f: &mut Frame<'_>| {
        let mut areas = hud_areas(f.area());
        st.areas.hud_copy = Some(areas.copy_btn);
        st.areas.hud_approve = areas.approve_btn;
        st.areas.hud_skip = areas.skip_btn;
        let data = HomeData::default();
        let _ = render_hud(f, f.area(), &data, &mut areas);
    })
    .expect("draw");
    let btn = st.areas.hud_copy.expect("copy rect");
    let action = hit_test(&st, btn.x + 1, btn.y).expect("hit");
    assert_eq!(action, AppAction::CopyPrompt);
    let fx = update(&mut st, action).expect("effect");
    assert_eq!(
        fx,
        Effect::CopyPrompt {
            text: "pegame esto".into()
        }
    );
}

#[test]
fn hud_esc_quits() {
    let mut st = AppState::new(req_float());
    assert!(update(&mut st, AppAction::Back).is_none());
    assert!(st.quit, "Esc en HUD vacío debe salir, no no-op");
}

#[test]
fn hud_approve_opens_modal_for_hygiene() {
    let mut st = AppState::new(req_float());
    st.actions.proposals = vec![hygiene()];
    let mut term = Terminal::new(TestBackend::new(100, 12)).expect("term");
    term.draw(|f: &mut Frame<'_>| {
        let areas = hud_areas(f.area());
        st.areas.hud_approve = areas.approve_btn;
    })
    .expect("draw");
    let btn = st.areas.hud_approve.expect("approve");
    let action = hit_test(&st, btn.x + 1, btn.y).expect("hit");
    assert!(matches!(action, AppAction::ApproveProposal { .. }));
    assert!(update(&mut st, action).is_none());
    assert!(st.pending.is_some(), "debe abrir modal, no ejecutar");
}

#[test]
fn hud_skip_remembers_hygiene_id() {
    let mut st = AppState::new(req_float());
    st.actions.proposals = vec![hygiene()];
    let fx = update(&mut st, AppAction::HudSkip);
    assert_eq!(
        fx,
        Some(Effect::HudSkip {
            id: "vault.validate_docs".into()
        })
    );
    assert_eq!(st.hud_skipped.as_deref(), Some("vault.validate_docs"));
}

#[test]
fn hud_skip_escribe_actions_yaml() {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let root = std::env::temp_dir().join(format!("cortex-hud-skip-{}-{nanos}", std::process::id()));
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    let be = cortex_companion::engine::InProcessBackend::open(&root).unwrap();
    let log = cortex_companion::approval::ActionLog::new(&root.join(".cortex"));
    let mut st = AppState::new(req_float());
    st.actions.proposals = vec![hygiene()];

    let fx = update(&mut st, AppAction::HudSkip).expect("fx");
    cortex_companion::effects::apply(&be, &log, &mut st, fx);

    let actions_yaml = std::fs::read_to_string(root.join(".cortex/actions.yaml"))
        .expect("actions.yaml debe existir");
    assert!(actions_yaml.contains("vault.validate_docs"));
    assert!(actions_yaml.contains("skips: 1"));

    let learner = cortex_actions::learning::Learner::new(&root.join(".cortex"));
    assert!(learner.multiplicador("vault.validate_docs") < 1.0);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn enter_without_ask_copies_not_injects() {
    let mut st = AppState::new(req_float());
    st.hud_prompt = "prompt x".into();
    let fx = update(&mut st, AppAction::Key(KeyCode::Enter)).expect("fx");
    assert_eq!(
        fx,
        Effect::CopyPrompt {
            text: "prompt x".into()
        }
    );
}

#[test]
fn prompt_plan_pide_implement_al_agente() {
    let s = cortex_companion::engine::SessionSummary {
        id: "SES-1".into(),
        status: "open".into(),
        mode: "composed".into(),
        opened_at: "".into(),
        phase: Some("plan".into()),
    };
    let p = cortex_companion::screens::hud_screen::compose_agent_prompt(Some(&s));
    assert!(p.contains("files_in_scope") || p.contains("ticket"), "{p}");
    assert!(!p.contains("cortex session"), "nunca CLI al humano: {p}");
}

#[test]
fn prompt_sin_fase_pide_checkpoint_al_agente() {
    let s = cortex_companion::engine::SessionSummary {
        id: "SES-1".into(),
        status: "open".into(),
        mode: "composed".into(),
        opened_at: "".into(),
        phase: None,
    };
    let p = cortex_companion::screens::hud_screen::compose_agent_prompt(Some(&s));
    assert!(p.contains("checkpoint"), "{p}");
    assert!(!p.contains("cortex session"), "{p}");
}

#[test]
fn prompt_sin_sesion_pide_skills_no_cli() {
    let p = cortex_companion::screens::hud_screen::compose_agent_prompt(None);
    assert!(!p.contains("cortex session"), "{p}");
    assert!(p.contains("skills"), "{p}");
}

#[test]
fn prompt_nunca_menciona_cortex_session() {
    for ph in ["grill", "spec", "plan", "implement", "review", "close"] {
        let s = cortex_companion::engine::SessionSummary {
            id: "SES-1".into(),
            status: "open".into(),
            mode: "composed".into(),
            opened_at: "".into(),
            phase: Some(ph.into()),
        };
        let p = cortex_companion::screens::hud_screen::compose_agent_prompt(Some(&s));
        assert!(
            !p.contains("corré `cortex"),
            "fase {ph} no debe pedir corré cortex: {p}"
        );
        assert!(
            !p.contains("pedile al humano que"),
            "fase {ph} no debe pedir al humano comandos: {p}"
        );
    }
}

#[test]
fn liquid_ram_transition_idle_weak_awake() {
    use cortex_companion::app::{LiquidRam, MarkRam};
    let mut lr = LiquidRam::default();
    assert_eq!(lr.ram(), MarkRam::WeakAwake);
    lr.mark_active();
    assert_eq!(lr.ram(), MarkRam::Awake);
    lr.mark_idle();
    assert_eq!(lr.ram(), MarkRam::WeakAwake);
    lr.last_activity = std::time::Instant::now() - std::time::Duration::from_secs(91);
    assert_eq!(lr.ram(), MarkRam::Idle);
}

#[test]
fn hud_sidecar_40x24_renders_vertical_layout() {
    let data = HomeData {
        project: "/home/chucho/cortex".into(),
        branch: Some("main".into()),
        prompt: "implementá el ticket 1".into(),
        ..Default::default()
    };
    let mut term = Terminal::new(TestBackend::new(40, 24)).expect("term");
    term.draw(|f: &mut Frame<'_>| {
        let mut areas = hud_areas(f.area());
        assert_eq!(areas.brand.width, 40);
        assert_eq!(areas.dialogs.width, 40);
        let _ = render_hud(f, f.area(), &data, &mut areas);
    })
    .expect("draw");
    let buf = term.backend().buffer();
    let mut text = String::new();
    for cell in buf.content.iter() {
        text.push_str(cell.symbol());
    }
    assert!(text.contains("COMPANION"));
    assert!(text.contains("Copiar"));
    assert!(text.contains("implementá el ticket 1"));
}
