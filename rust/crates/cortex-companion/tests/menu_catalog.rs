//! Tests de integración del Menu (G-B2c): catálogo de 27 familias, render a
//! buffer sin terminal real, hit-test de entradas/scroll y ejecución
//! in-process del engine (paridad + honestidad P6/P9).

use std::collections::HashSet;
use std::path::PathBuf;

use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::{Frame, Terminal};

use cortex_companion::app::{
    hit_test, update, AppAction, AppState, Effect, HOME_MENU_BTN, MENU_LIST_HEIGHT, MENU_LIST_TOP,
    MENU_OUTPUT_HEIGHT, MENU_OUTPUT_TOP,
};
use cortex_companion::engine::{Backend, InProcessBackend};
use cortex_companion::menu::{
    command_effect, flat_rows, row_at, CatalogEntry, CommandEffect, Domain, FlatRow, MenuOutput,
};
use cortex_companion::screens::menu_screen::{menu_areas, render_menu};
use cortex_companion::{Screen, UiRequest};

const FIXTURE_REL: &str = "../../../bench/parity/archive/.p12b-doctor/.work/ap_e2e/acme-api";

fn committed_fixture() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(FIXTURE_REL)
}

fn menu_state(scroll: u16) -> AppState {
    let mut st = AppState::new(UiRequest {
        screen: Screen::Menu,
        project_root: committed_fixture(),
        mode: Default::default(),
    });
    st.scroll_offset = scroll;
    st
}

/// Renderiza el Menu 80x24 a (texto, botones registrados, ms).
fn render(output: Option<&MenuOutput>, scroll: u16) -> (String, usize, f32) {
    let mut term = Terminal::new(TestBackend::new(80, 24)).expect("test terminal");
    let mut info: Option<cortex_companion::screens::menu_screen::AppRenderInfo> = None;
    term.draw(|f: &mut Frame<'_>| {
        let mut areas = menu_areas(f.area());
        let i = render_menu(f, f.area(), output, scroll, &mut areas);
        info = Some(i);
    })
    .expect("draw ok");
    let buf = term.backend().buffer().clone();
    let mut content = String::with_capacity(80 * 24);
    for cell in buf.content.iter() {
        let sym = cell.symbol();
        if !sym.is_empty() {
            content.push(sym.chars().next().unwrap());
        }
    }
    let spent = info.as_ref().expect("render info").spent_ms;
    (content, info.expect("render info").buttons.len(), spent)
}

// --- Catálogo (G-B2c) ---

#[test]
fn catalog_has_all_27_families_grouped() {
    let cat = cortex_companion::menu::catalog();
    let mut families: HashSet<&'static str> = HashSet::new();
    for e in &cat {
        assert!(families.insert(e.family), "familia duplicada: {}", e.family);
    }
    assert_eq!(families.len(), 27, "catálogo debe tener 27 familias");
    assert!(families.contains("session"));
    assert!(families.contains("next"));
    assert!(families.contains("webgraph"));
    assert!(
        families.contains("init"),
        "init es el 27º subárbol real del CLI"
    );
    for d in [
        Domain::Sessions,
        Domain::Memory,
        Domain::Search,
        Domain::Docs,
        Domain::Ci,
        Domain::Setup,
        Domain::Enterprise,
    ] {
        assert!(cat.iter().any(|e| e.domain == d), "dominio {d:?} vacío");
    }
    // flat_rows: 7 headers + 27 entradas.
    let rows = flat_rows();
    assert_eq!(rows.len(), 34);
    assert_eq!(
        rows.iter()
            .filter(|r| matches!(r, cortex_companion::menu::FlatRow::Entry(_)))
            .count(),
        27
    );
}

#[test]
fn menu_entry_mutation_requires_approval_flow() {
    let e = CatalogEntry {
        family: "session",
        args: &["finish"],
        title: "x",
        domain: Domain::Sessions,
    };
    assert_eq!(command_effect(&e), CommandEffect::Guarded);
    let e = CatalogEntry {
        family: "stats",
        args: &[],
        title: "x",
        domain: Domain::Memory,
    };
    assert_eq!(command_effect(&e), CommandEffect::Direct);
}

// --- Render ---

#[test]
fn menu_render_shows_domains_entries_and_budget() {
    let (text, buttons, spent) = render(None, 0);
    assert!(text.contains("capacidades"), "título no renderizado");
    assert!(
        text.contains("▸ Sesiones"),
        "header de dominio no renderizado"
    );
    assert!(
        text.contains("Siguiente acción"),
        "entrada next no renderizada"
    );
    assert!(
        text.contains("cortex next"),
        "invocación visible (anti-olvido)"
    );
    assert!(
        !text.contains("Doctor"),
        "entradas bajas fuera de scroll no asoman"
    );
    // Botón volver registrado.
    assert!(buttons >= 1);
    assert!(spent < 50.0, "render {spent} ms superó presupuesto <50 ms");

    // Con scroll, los dominios bajos quedan visibles (y los altos salen).
    let (text2, _, spent2) = render(None, 15);
    assert!(
        text2.contains("▸ Enterprise"),
        "último dominio no renderizado con scroll"
    );
    assert!(
        text2.contains("Doctor"),
        "entrada baja no visible con scroll"
    );
    assert!(
        spent2 < 50.0,
        "render con scroll {spent2} ms superó presupuesto"
    );
}

#[test]
fn menu_output_panel_shows_result_and_error() {
    let ok = MenuOutput::ok("episódica 12 · semántica 34 · vault/");
    let (text, _, _) = render(Some(&ok), 0);
    assert!(text.contains("episódica 12"), "salida OK no visible");
    assert!(!text.contains('⚠'), "no debe marcar error una salida OK");

    let err = MenuOutput::err("«remember» no integrada al Companion — corré `cortex remember`");
    let (text, _, _) = render(Some(&err), 0);
    assert!(text.contains('⚠'), "error P6/P9 debe marcarse");
    assert!(
        text.contains("salida (error)"),
        "título de error no visible"
    );
}

// --- Hit-test (geometría compartida con render) ---

#[test]
fn menu_click_entry_runs_command() {
    let mut st = menu_state(0);
    // "next" está en flat 2 ⇒ y = MENU_LIST_TOP + 2 = 6.
    let action = hit_test(&st, 10, MENU_LIST_TOP + 2).expect("click en next");
    match &action {
        AppAction::RunCommand { family, args } => {
            assert_eq!(*family, "next");
            assert!(args.is_empty());
        }
        other => panic!("esperaba RunCommand, recibí {other:?}"),
    }
    let fx = update(&mut st, action).expect("efecto emitido");
    assert!(matches!(fx, Effect::RunCommand { family: "next", .. }));
}

#[test]
fn menu_click_header_row_is_noop() {
    let st = menu_state(0);
    // flat 0 = header "Sesiones" ⇒ y = 4.
    assert!(
        hit_test(&st, 10, MENU_LIST_TOP).is_none(),
        "header no es clickeable"
    );
}

#[test]
fn menu_click_output_panel_is_noop() {
    // Regresión: hit-test(Menu) no tenía cota superior de filas — un click en
    // el panel de salida (x dentro del ancho de la lista, y >= lista) disparaba
    // filas OCULTAS del catálogo, incluidas Guarded (modal inesperado).
    let st = menu_state(0);
    assert_eq!(
        MENU_OUTPUT_TOP,
        MENU_LIST_TOP + MENU_LIST_HEIGHT,
        "precondición de geometría: la salida empieza donde termina la lista"
    );
    for y in MENU_LIST_TOP + MENU_LIST_HEIGHT..MENU_OUTPUT_TOP + MENU_OUTPUT_HEIGHT {
        assert!(
            hit_test(&st, 10, y).is_none(),
            "click en el panel de salida (y={y}) no debe disparar filas ocultas"
        );
    }
}

#[test]
fn menu_click_last_visible_row_runs_command() {
    let st = menu_state(0);
    let last_y = MENU_LIST_TOP + MENU_LIST_HEIGHT - 1;
    let flat = usize::from(last_y - MENU_LIST_TOP) + usize::from(st.scroll_offset);
    // Invariante del fixture: la última fila visible es una entrada del catálogo.
    assert!(
        matches!(row_at(flat), Some(FlatRow::Entry(_))),
        "última fila visible (flat {flat}) debe ser una entrada"
    );
    let action = hit_test(&st, 10, last_y).expect("click en la última fila visible");
    assert!(
        matches!(action, AppAction::RunCommand { .. }),
        "la última fila visible debe disparar RunCommand (recibí {action:?})"
    );
}

#[test]
fn menu_back_button_goes_back() {
    let mut st = menu_state(0);
    let b = Rect::new(58, 1, 20, 3);
    let action = hit_test(&st, b.x + 10, b.y + 1).expect("click en volver");
    assert!(matches!(action, AppAction::Back));
    assert!(update(&mut st, action).is_none());
    assert_eq!(
        st.screen,
        Screen::Menu,
        "sin pila previa Back no cambia pantalla"
    );
    // con pila: Home previo
    st.stack.push(Screen::Home);
    assert!(update(&mut st, AppAction::Back).is_none());
    assert_eq!(st.screen, Screen::Home);
}

#[test]
fn menu_scroll_reveals_lower_entries() {
    // "hu" está en flat 33 (última entrada); con scroll=20 cae en y=17 (visible).
    let st = menu_state(20);
    let action = hit_test(&st, 10, MENU_LIST_TOP + 13).expect("click en hu scrolleado");
    match action {
        AppAction::RunCommand { family, args } => {
            assert_eq!(family, "hu");
            assert_eq!(args, vec!["list"]);
        }
        other => panic!("esperaba RunCommand hu, recibí {other:?}"),
    }
}

#[test]
fn home_menu_button_navigates_to_menu() {
    let mut st = AppState::new(UiRequest {
        screen: Screen::Home,
        project_root: committed_fixture(),
        mode: Default::default(),
    });
    let action =
        hit_test(&st, HOME_MENU_BTN.x + 5, HOME_MENU_BTN.y + 1).expect("botón Menú en Home");
    assert!(matches!(action, AppAction::Navigate(Screen::Menu)));
    assert!(update(&mut st, action).is_none());
    assert_eq!(st.screen, Screen::Menu);
}

// --- Ejecución in-process del engine (G-B2c) ---

#[test]
fn menu_run_integrated_families_produce_output() {
    let be = InProcessBackend::open(&committed_fixture()).expect("abrir backend");
    let stats = be.menu_run("stats", &[]).expect("stats integrada");
    assert!(stats.contains("episódica"), "stats sin conteo: {stats}");
    let doctor = be.menu_run("doctor", &[]).expect("doctor integrada");
    assert!(doctor.contains("[OK]"), "doctor sin checks: {doctor}");
    // session default → list JSON byte-parity (mismo pyjson del CLI).
    let sess = be.menu_run("session", &[]).expect("session integrada");
    assert!(sess.contains("session_id"), "session list sin JSON: {sess}");
    // search sin query ⇒ error honesto con hint.
    let err = be.menu_run("search", &[]).unwrap_err();
    assert!(
        err.contains("panel Search"),
        "hint de search ausente: {err}"
    );
}

#[test]
fn menu_run_unintegrated_fails_explicit_p6p9() {
    let be = InProcessBackend::open(&committed_fixture()).expect("abrir backend");
    let err = be.menu_run("remember", &[]).unwrap_err();
    assert!(err.contains("no integrada"), "mensaje P6/P9 ausente");
    assert!(err.contains("cortex remember"), "comando exacto ausente");
    let err = be.menu_run("inexistente", &["x".to_string()]).unwrap_err();
    assert!(
        err.contains("inexistente"),
        "familia desconocida sin nombre"
    );
}
