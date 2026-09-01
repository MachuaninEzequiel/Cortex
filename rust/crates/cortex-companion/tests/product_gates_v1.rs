//! Gates v1 del Producto 17 §14.
//!
//! Verifica el paquete completo de aceptación: HUD default, Copiar con OSC 52,
//! higiene filtrada, idle ≠ awake, layout adaptativo, y cero bypass.

use std::path::PathBuf;

use crossterm::event::KeyCode;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::{Frame, Terminal};

use cortex_companion::app::{update, AppAction, AppState, Effect, MarkRam};
use cortex_companion::engine::ActionProposal;
use cortex_companion::herdr::{conclude_spawn, SpawnKind};
use cortex_companion::hud_brand::{blit_mark, tone, TOP};
use cortex_companion::screens::home::HomeData;
use cortex_companion::screens::hud_screen::{
    compose_agent_prompt, hud_areas, is_hygiene, pick_hygiene, render_hud,
};
use cortex_companion::{CompanionMode, Screen, UiRequest};

fn req_float() -> UiRequest {
    UiRequest {
        screen: Screen::Home,
        project_root: PathBuf::from("/tmp/fixture"),
        mode: CompanionMode::Float,
    }
}

// Gate 1: HUD default / toml open es float split
#[test]
fn gate_1_manifest_open_es_float_no_sidecar() {
    let manifest_path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../integrations/herdr/herdr-plugin.toml"
    );
    let src = std::fs::read_to_string(manifest_path).expect("herdr-plugin.toml");
    let open_block = src
        .split("[[actions]]")
        .find(|b| b.contains("id = \"open\""))
        .expect("bloque de accion open");
    assert!(
        open_block.contains("\"float\""),
        "open debe abrir float: {open_block}"
    );
    assert!(
        open_block.contains("\"split\""),
        "open debe ser split: {open_block}"
    );
}

// Gate 2: Copiar, cero send-text en runtime de Companion
#[test]
fn gate_2_send_text_no_se_llama_desde_companion_productivo() {
    let src_runner = include_str!("../src/runner.rs");
    let src_app = include_str!("../src/app.rs");
    let src_hud = include_str!("../src/screens/hud_screen.rs");
    let src_effects = include_str!("../src/effects.rs");

    assert!(!src_runner.contains("send_text_to_pane"));
    assert!(!src_app.contains("send_text_to_pane"));
    assert!(!src_hud.contains("send_text_to_pane"));
    assert!(!src_effects.contains("send_text_to_pane"));
}

#[test]
fn gate_2_enter_vacio_copia_prompt() {
    let mut st = AppState::new(req_float());
    st.hud_prompt = "copiame a OSC 52".into();
    let fx = update(&mut st, AppAction::Key(KeyCode::Enter)).expect("effect");
    assert_eq!(
        fx,
        Effect::CopyPrompt {
            text: "copiame a OSC 52".into()
        }
    );
}

// Gate 3: Aprobar higiene nativa, no finish en HUD
#[test]
fn gate_3_pick_hygiene_ignora_close_y_checkpoint() {
    let props = vec![
        ActionProposal {
            id: "session.close_stale".into(),
            title: "Cerrar sesión stale".into(),
            score: 9.0,
            cost: "instant".into(),
            reversible: false,
            effect: "cierra".into(),
        },
        ActionProposal {
            id: "session.checkpoint_now".into(),
            title: "Checkpoint ahora".into(),
            score: 8.5,
            cost: "instant".into(),
            reversible: true,
            effect: "checkpoint".into(),
        },
        ActionProposal {
            id: "vault.validate_docs".into(),
            title: "Validar documentos del vault".into(),
            score: 8.0,
            cost: "instant".into(),
            reversible: true,
            effect: "corre DocValidator".into(),
        },
    ];
    let h = pick_hygiene(&props, None).expect("debe encontrar higiene");
    assert_eq!(h.id, "vault.validate_docs");
    assert!(!is_hygiene("session.close_stale"));
    assert!(!is_hygiene("session.checkpoint_now"));
}

// Gate 4: idle != awake en blit y en tonos
#[test]
fn gate_4_mark_idle_distinto_de_awake() {
    let t_awake = tone(TOP, MarkRam::Awake);
    let t_weak = tone(TOP, MarkRam::WeakAwake);
    let t_idle = tone(TOP, MarkRam::Idle);

    assert_eq!(t_awake, TOP);
    assert!(t_weak < t_awake);
    assert!(t_idle < t_weak);

    let area = Rect::new(0, 0, 26, 9);
    let mut buf_idle = Buffer::empty(area);
    let mut buf_awake = Buffer::empty(area);

    blit_mark(&mut buf_idle, area, MarkRam::Idle);
    blit_mark(&mut buf_awake, area, MarkRam::Awake);

    let cells_idle: Vec<_> = buf_idle.content.iter().map(|c| c.fg).collect();
    let cells_awake: Vec<_> = buf_awake.content.iter().map(|c| c.fg).collect();

    assert_ne!(cells_idle, cells_awake, "idle debe diferir de awake");
}

// Gate 5: snapshot 100x12 prompt+Copiar, no Menú/Sesiones/Doctor OK
#[test]
fn gate_5_snapshot_hud_sin_dashboard() {
    let data = HomeData {
        project: "/home/chucho/cortex-demo".into(),
        branch: Some("feature/obra17".into()),
        prompt: "trabajo en curso".into(),
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

    assert!(text.contains("COMPANION"));
    assert!(text.contains("Copiar"));
    assert!(text.contains("preguntale a Cortex"));
    assert!(!text.contains("Doctor: OK"));
    assert!(!text.contains("Sesiones"));
    assert!(!text.contains("Menú"));
}

// Gate 6: prompt nunca pide al humano correr CLI
#[test]
fn gate_6_prompt_nunca_pide_al_humano_correr_cli() {
    for ph in ["grill", "spec", "plan", "implement", "review", "close"] {
        let s = cortex_companion::engine::SessionSummary {
            id: "SES-1".into(),
            status: "open".into(),
            mode: "composed".into(),
            opened_at: "".into(),
            phase: Some(ph.into()),
        };
        let p = compose_agent_prompt(Some(&s));
        assert!(
            !p.contains("corré `cortex"),
            "fase {ph} no debe pedir corré cortex: {p}"
        );
        assert!(
            !p.contains("pedile al humano"),
            "fase {ph} no debe pedir al humano comandos: {p}"
        );
    }
}

// Gate 7: Runner no abre llama antes del loop
#[test]
fn gate_7_runner_no_abre_llama_antes_del_loop() {
    let src = include_str!("../src/runner.rs");
    let (pre, _) = src.split_once("loop {").expect("loop del event loop");
    assert!(
        !pre.contains("LlamaChatBackend::open"),
        "open al start es el bug: el GGUF vive en RAM idle"
    );
}

// Gate 8: conclude_spawn valida json y resize
#[test]
fn gate_8_conclude_spawn_honestidad() {
    let json_float = br#"{"result":{"plugin_pane":{"pane":{"pane_id":"p-hud","focused":false}}}}"#;
    let s_float = conclude_spawn(SpawnKind::Float, json_float, None, true).unwrap();
    assert_eq!(s_float, "Bottom HUD");

    let json_sidecar =
        br#"{"result":{"plugin_pane":{"pane":{"pane_id":"p-side","focused":false}}}}"#;
    let s_side = conclude_spawn(SpawnKind::Sidecar, json_sidecar, Some(true), true).unwrap();
    assert!(s_side.contains("30"));

    assert!(conclude_spawn(SpawnKind::Sidecar, json_sidecar, Some(true), false).is_err());
    assert!(conclude_spawn(SpawnKind::Float, b"{}", None, true).is_err());
}

// Gate 9: Sidecar renderiza vertical layout sin dashboard
#[test]
fn gate_9_sidecar_40x24_renders_vertical_layout() {
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
    assert!(!text.contains("Doctor: OK"));
    assert!(!text.contains("Menú"));
}
