//! Runner común para cortex-companion y sus modos Herdr (Sidecar, Float, Co-Pilot).

use std::io::IsTerminal;
use std::path::PathBuf;

use crossterm::event::{self, DisableMouseCapture, EnableMouseCapture};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

use crate::app::{self, AppAction, AppState};
use crate::approval::ActionLog;
use crate::effects;
use crate::engine::{Backend, InProcessBackend};
use crate::herdr;
use crate::screens::home::{home_areas, render_home, BrandAssets, HomeData};
use crate::screens::menu_screen::{menu_areas, render_menu};
use crate::screens::sessions_screen::{render_sessions, sessions_areas};
use crate::screens::{
    actions_areas, brain_areas, render_actions, render_brain, render_modal, render_search,
    search_areas,
};
use crate::{CompanionMode, Screen, UiRequest};

pub fn run_app(mode: CompanionMode, root: PathBuf, model: Option<String>) {
    let be = match InProcessBackend::open(&root) {
        Ok(be) => be,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    };
    let log = ActionLog::new(&be.action_log_dir());

    // Reportar metadata inicial en el sidebar de Herdr si corresponde
    if mode == CompanionMode::Float
        || mode == CompanionMode::Sidecar
        || mode == CompanionMode::Copilot
    {
        let _ = herdr::report_metadata(None, "cortex activo");
    }

    let mut llm: Option<Box<dyn cortex_brain::chat::LlmBackend>> = None;
    if let Some(path) = &model {
        #[cfg(feature = "llama")]
        {
            match cortex_brain::llama::LlamaChatBackend::open(std::path::Path::new(path), None) {
                Ok(b) => llm = Some(Box::new(b)),
                Err(e) => eprintln!("⚠ {e} — sigo en modo determinista"),
            }
        }
        #[cfg(not(feature = "llama"))]
        {
            let _ = path;
            eprintln!(
                "{}",
                cortex_brain::i18n::warn_sin_llama(cortex_brain::i18n::Lang::Es)
            );
        }
    }

    let agent_info = if mode == CompanionMode::Copilot || mode == CompanionMode::Float {
        herdr::detect_target_agent(&be.root)
    } else {
        None
    };
    let agent_label = agent_info
        .as_ref()
        .map(|a| {
            format!(
                "{} {}",
                a.agent.as_deref().unwrap_or("agente"),
                a.agent_status.as_deref().unwrap_or("")
            )
            .trim()
            .to_string()
        })
        .unwrap_or_default();

    let mut st = AppState::new(UiRequest {
        screen: Screen::Home,
        project_root: root,
        mode,
    });

    if !std::io::stdin().is_terminal() {
        println!(
            "Pantalla: {} (project: {}, mode: {:?})",
            app::screen_label(st.screen),
            be.root.display(),
            mode,
        );
        return;
    }

    if terminal::enable_raw_mode().is_err() {
        eprintln!("no se pudo entrar en raw mode");
        return;
    }
    let _ = execute!(std::io::stdout(), EnableMouseCapture);

    let mut terminal = match Terminal::new(CrosstermBackend::new(std::io::stdout())) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("no se pudo inicializar el terminal: {e}");
            let _ = execute!(std::io::stdout(), DisableMouseCapture);
            let _ = terminal::disable_raw_mode();
            return;
        }
    };
    let _ = terminal.hide_cursor();
    let _ = terminal.clear();

    loop {
        match st.screen {
            Screen::Sessions => {
                let sel = st.sessions.selected;
                let outcome = st.sessions.outcome.take();
                st.sessions = sessions_data(&be, sel, outcome);
            }
            Screen::Actions => {
                let outcome = st.actions.outcome.take();
                st.actions = actions_data(&be, outcome);
            }
            _ => {}
        }

        let _ = terminal.draw(|f| {
            match st.screen {
                Screen::Home => {
                    let mut data = home_data(&be, st.hud_skipped.as_deref(), &st.hud_ask);
                    data.agent_label = agent_label.clone();
                    if mode == CompanionMode::Float {
                        let mut areas = crate::screens::hud_screen::hud_areas(f.area());
                        areas.hovered_mouse = st.mouse;
                        st.areas.hud_copy = Some(areas.copy_btn);
                        st.areas.hud_approve = areas.approve_btn;
                        st.areas.hud_skip = areas.skip_btn;
                        st.hud_prompt = crate::screens::hud_screen::hud_prompt(&data);
                        if let Some(h) = data.hygiene.clone() {
                            st.actions.proposals = vec![h];
                        } else {
                            st.actions.proposals.clear();
                        }
                        let _info =
                            crate::screens::hud_screen::render_hud(f, f.area(), &data, &mut areas);
                    } else if mode == CompanionMode::Copilot {
                        let mut areas = crate::screens::copilot_screen::copilot_areas(f.area());
                        areas.hovered_mouse = st.mouse;
                        // D4: Copiar, nunca inyectar. El rect del CTA alimenta hud_copy.
                        st.areas.hud_copy = Some(areas.inject_btn);
                        st.hud_prompt = crate::screens::hud_screen::hud_prompt(&data);
                        let _info = crate::screens::copilot_screen::render_copilot(
                            f,
                            f.area(),
                            &data,
                            &agent_info,
                            &mut areas,
                        );
                    } else {
                        let mut areas = home_areas(f.area());
                        areas.hovered_mouse = st.mouse;
                        st.areas.home_sessions_btn = Some(areas.sessions_btn);
                        st.areas.home_actions_btn = Some(areas.actions_btn);
                        st.areas.home_open_session_btn = areas.open_session_btn;
                        st.areas.home_menu_btn = Some(areas.menu_btn);
                        st.areas.home_brain_btn = Some(areas.brain_btn);
                        let _info =
                            render_home(f, f.area(), &data, &BrandAssets::load(), &mut areas);
                    }
                }
                Screen::Menu => {
                    let mut areas = menu_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info = render_menu(
                        f,
                        f.area(),
                        st.menu_output.as_ref(),
                        st.scroll_offset,
                        &mut areas,
                    );
                }
                Screen::Sessions => {
                    let mut areas = sessions_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info =
                        render_sessions(f, f.area(), &st.sessions, st.scroll_offset, &mut areas);
                }
                Screen::Actions => {
                    let mut areas = actions_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info =
                        render_actions(f, f.area(), &st.actions, st.scroll_offset, &mut areas);
                }
                Screen::Search => {
                    let mut areas = search_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info =
                        render_search(f, f.area(), &st.search, st.scroll_offset, &mut areas);
                }
                Screen::Brain => {
                    let mut areas = brain_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info = render_brain(f, f.area(), &st.brain, st.scroll_offset, &mut areas);
                }
            }
            if let Some(p) = st.pending.as_ref() {
                render_modal(f, &p.req);
            }
        });

        match event::read() {
            Ok(ev) => {
                if let Some(action) = app::translate_event(&ev) {
                    let action = match action {
                        AppAction::Click { x, y } => {
                            app::hit_test(&st, x, y).unwrap_or(AppAction::Click { x, y })
                        }
                        other => other,
                    };
                    if let Some(fx) = app::update(&mut st, action) {
                        let llm_ref = llm
                            .as_mut()
                            .map(|b| b.as_mut() as &mut dyn cortex_brain::chat::LlmBackend);
                        effects::apply_opt(&be, &log, &mut st, fx, llm_ref);
                    }
                }
            }
            Err(_) => break,
        }
        if st.quit {
            break;
        }
    }

    let _ = terminal.clear();
    let _ = terminal.show_cursor();
    let _ = execute!(std::io::stdout(), DisableMouseCapture);
    let _ = terminal::disable_raw_mode();
}

fn sessions_data(
    be: &InProcessBackend,
    selected: Option<usize>,
    outcome: Option<crate::app::OutcomeLine>,
) -> crate::app::SessionsData {
    let mut data = crate::app::SessionsData {
        outcome,
        ..Default::default()
    };
    match be.session_list() {
        Ok(v) => data.sessions = v,
        Err(e) => data.error = Some(e),
    }
    data.selected = selected.filter(|i| *i < data.sessions.len());
    if let Some(i) = data.selected {
        let id = data.sessions[i].id.clone();
        data.detail = be.session_detail(&id).ok().map(|l| (id, l));
    }
    data
}

fn actions_data(
    be: &InProcessBackend,
    outcome: Option<crate::app::OutcomeLine>,
) -> crate::app::ActionsData {
    match be.next_actions() {
        Ok(proposals) => crate::app::ActionsData {
            proposals,
            outcome,
            error: None,
        },
        Err(e) => crate::app::ActionsData {
            proposals: Vec::new(),
            outcome,
            error: Some(e),
        },
    }
}

fn home_data(be: &InProcessBackend, skipped: Option<&str>, ask: &str) -> HomeData {
    let project = be.root.display().to_string();
    let branch = be.current_branch().ok().flatten();
    let session = be.session_current().ok().flatten();
    let next = be.next_actions();
    let (actions, error) = match next {
        Ok(a) => (a, None),
        Err(e) => (Vec::new(), Some(e)),
    };
    let top_action = actions.first().cloned();
    let hygiene = crate::screens::hud_screen::pick_hygiene(&actions, skipped).cloned();
    let doctor = be.doctor().ok();
    let stats = be.stats().ok();
    HomeData {
        project,
        branch,
        session,
        top_action,
        doctor,
        stats,
        error,
        prompt: String::new(),
        hygiene,
        agent_label: String::new(),
        ask: ask.to_string(),
    }
}
