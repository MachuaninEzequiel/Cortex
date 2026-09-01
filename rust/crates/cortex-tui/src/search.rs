//! Pantalla BUSCAR (spec §12 adaptada): input con cursor visible, búsqueda
//! vía el motor inyectado (adapter del CLI sobre NativeMemory — la TUI no
//! duplica retrieval), resultados con fuente/score/título/path, conteo y
//! estados vacío/error explícitos.
//!
//! Dos fases (spec: "Enter confirma; Esc limpia y restaura"): INPUT
//! (escribir/editar) y LIST (navegar j/k, Enter muestra la ruta del hit).

use crate::app::search::SearchData;
use crate::app::state::{AppState, LoadState, Overlay, SearchMode};
use crate::components::empty_state::EmptyState;
use crate::components::header::AppHeader;
use crate::components::list::SelectableList;
use crate::components::status_bar::StatusBar;
use crate::components::truncate_visual;
use crate::layout::{layout_mode, render_too_small, LayoutMode};
use crate::theme::{StatusKind, Theme};
use ratatui::prelude::{Constraint, Layout, Line, Rect, Span};
use ratatui::Frame;

/// Cursor visual del input (un bloque; el cursor real del terminal queda
/// reservado para F3/async — el render es puro y determinista).
const CURSOR: &str = "▏";

/// Máximo de caracteres visibles de la query en la línea de input.
const QUERY_MAX_VISIBLE: usize = 60;

/// Render puro de la pantalla de búsqueda.
pub fn render(f: &mut Frame<'_>, state: &AppState) {
    let area = f.area();
    if layout_mode(area) == LayoutMode::TooSmall {
        render_too_small(f, state.lang);
        return;
    }
    let theme = Theme::new(crate::env_color_mode());

    let [header_area, body_area, status_area] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(4),
        Constraint::Length(1),
    ])
    .areas(area);

    let right: Vec<(StatusKind, String)> = match &state.search {
        LoadState::Ready(d) if !d.hits.is_empty() => vec![(
            StatusKind::Active,
            format!(
                "{} {}",
                d.hits.len(),
                if state.lang == "en" {
                    "hits"
                } else {
                    "resultados"
                }
            ),
        )],
        _ => vec![],
    };
    f.render_widget(
        AppHeader {
            title: if state.lang == "en" {
                "search"
            } else {
                "búsqueda"
            },
            right: &right,
            lang: state.lang,
            mode: state.mode,
        },
        header_area,
    );

    // Layout interno: input fijo arriba, resultados debajo.
    let [input_area, list_area] =
        Layout::vertical([Constraint::Length(1), Constraint::Min(3)]).areas(body_area);

    render_input(f, input_area, state, &theme);

    match (&state.search, state.search_mode) {
        (LoadState::Loading, _) => {
            let frame = spinner_frame(state.tick);
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: if state.lang == "en" {
                        "searching…"
                    } else {
                        "buscando…"
                    },
                    body: &[],
                    hint: Some(if state.lang == "en" {
                        "q quit"
                    } else {
                        "q salir"
                    }),
                    theme: &theme,
                },
                list_area,
            );
            let _ = frame;
        }
        (LoadState::Failed(err), _) => {
            let short = truncate_visual(err, 70);
            let body = vec![short.as_str()];
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Error,
                    title: if state.lang == "en" {
                        "Search failed"
                    } else {
                        "La búsqueda falló"
                    },
                    body: &body,
                    hint: Some(if state.lang == "en" {
                        "Esc to edit · q quit"
                    } else {
                        "Esc para editar · q salir"
                    }),
                    theme: &theme,
                },
                list_area,
            );
        }
        (LoadState::Ready(d), _) if d.hits.is_empty() => {
            let title = if state.lang == "en" {
                format!("no results for '{}'", truncate_visual(&d.query, 40))
            } else {
                format!("sin resultados para '{}'", truncate_visual(&d.query, 40))
            };
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: &title,
                    body: &[],
                    hint: Some(if state.lang == "en" {
                        "Esc to edit · q quit"
                    } else {
                        "Esc para editar · q salir"
                    }),
                    theme: &theme,
                },
                list_area,
            );
        }
        (LoadState::Ready(d), _) => render_hits(f, list_area, d, state, &theme),
        (LoadState::Idle, _) => {
            // Aún sin búsqueda: el input invita.
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: if state.lang == "en" {
                        "Type a query and press Enter"
                    } else {
                        "Escribí una consulta y presioná Enter"
                    },
                    body: &[],
                    hint: Some(if state.lang == "en" {
                        "q quit"
                    } else {
                        "q salir"
                    }),
                    theme: &theme,
                },
                list_area,
            );
        }
    }

    // Status bar: acciones según la fase.
    let hints: Vec<(&'static str, &'static str)> = match state.search_mode {
        SearchMode::Input => vec![
            (
                "Enter",
                if state.lang == "en" {
                    "search"
                } else {
                    "buscar"
                },
            ),
            ("/", "search"),
            ("?", "help"),
            ("q", if state.lang == "en" { "quit" } else { "salir" }),
        ],
        SearchMode::List => vec![
            (
                "j/k",
                if state.lang == "en" {
                    "navigate"
                } else {
                    "navegar"
                },
            ),
            (
                "Enter",
                if state.lang == "en" {
                    "show path"
                } else {
                    "ver ruta"
                },
            ),
            (
                "Esc",
                if state.lang == "en" {
                    "edit query"
                } else {
                    "editar consulta"
                },
            ),
            ("q", if state.lang == "en" { "quit" } else { "salir" }),
        ],
    };
    let position = match (&state.search, state.search_mode) {
        (LoadState::Ready(d), SearchMode::List) if !d.hits.is_empty() => {
            Some((state.selection + 1, d.hits.len()))
        }
        _ => None,
    };
    let message = state.notifications.first();
    f.render_widget(
        StatusBar {
            hints: &hints,
            position,
            message,
            theme: &theme,
        },
        status_area,
    );

    if state.overlay == Overlay::Help {
        crate::components::help::render_help(f, area, &theme, state.lang);
    }
}

/// Línea de input: `/ query▏` (con cursor visual y truncado seguro).
fn render_input(f: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let q = truncate_visual(&state.search_query, QUERY_MAX_VISIBLE);
    let prompt = if state.lang == "en" {
        "query"
    } else {
        "consulta"
    };
    let line = Line::from(vec![
        Span::styled(format!("{prompt}: "), theme.shortcut_key()),
        Span::styled(q.clone(), theme.body()),
        Span::styled(CURSOR, theme.accent),
    ]);
    f.render_widget(
        ratatui::widgets::Paragraph::new(line),
        Rect::new(area.x, area.y, area.width, 1),
    );
}

fn render_hits(f: &mut Frame<'_>, area: Rect, data: &SearchData, state: &AppState, theme: &Theme) {
    let items: Vec<Vec<Line<'static>>> = data
        .hits
        .iter()
        .enumerate()
        .map(|(i, h)| {
            let is_sel = i == state.selection;
            let base = if is_sel {
                theme.selected()
            } else {
                theme.body()
            };
            let source_style = if h.source == "episodic" {
                theme.shortcut_key()
            } else {
                theme.muted()
            };
            vec![Line::from(vec![
                Span::styled(
                    format!("{:<9}", truncate_visual(&h.source, 9)),
                    source_style,
                ),
                Span::styled(format!("{:.4}  ", h.score), theme.muted()),
                Span::styled(truncate_visual(&h.title, 44), base),
                Span::styled(
                    format!("  ({})", truncate_visual(&h.path, 40)),
                    theme.subtitle(),
                ),
            ])]
        })
        .collect();
    f.render_widget(
        SelectableList {
            items: &items,
            selected: state.selection,
            offset: state.offset,
            theme,
        },
        area,
    );
}

/// Frame del spinner (determinista: deriva del tick del estado).
fn spinner_frame(tick: u64) -> &'static str {
    crate::app::runtime::SPINNER[tick as usize % crate::app::runtime::SPINNER.len()]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::search::SearchHit;
    use crate::app::update as reducer;

    fn hits_state(n: usize) -> AppState {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        reducer(
            &mut s,
            crate::app::Action::SearchLoaded(SearchData {
                query: "auth".into(),
                hits: (0..n)
                    .map(|i| SearchHit {
                        source: if i % 2 == 0 { "episodic" } else { "semantic" }.into(),
                        score: 1.0 - (i as f64 / 100.0),
                        title: format!("Resultado {i}"),
                        path: format!("vault/nota-{i}.md"),
                        memory_id: (i % 2 == 0).then(|| format!("mem-{i}")),
                    })
                    .collect(),
            }),
        );
        s
    }

    fn draw(state: &AppState, w: u16, h: u16) -> String {
        let backend = ratatui::backend::TestBackend::new(w, h);
        let mut terminal = ratatui::Terminal::with_options(
            backend,
            ratatui::TerminalOptions {
                viewport: ratatui::Viewport::Fixed(Rect::new(0, 0, w, h)),
            },
        )
        .unwrap();
        terminal.draw(|f| render(f, state)).unwrap();
        let buf = terminal.backend().buffer();
        let mut s = String::new();
        for y in 0..buf.area.height {
            for x in 0..buf.area.width {
                s.push_str(buf[(x, y)].symbol());
            }
            s.push('\n');
        }
        s
    }

    #[test]
    fn input_muestra_query_y_cursor() {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        assert_eq!(s.screen, crate::app::Screen::Search);
        assert_eq!(s.search_mode, SearchMode::Input);
        for c in "auth".chars() {
            reducer(&mut s, crate::app::Action::Input(c));
        }
        let out = draw(&s, 80, 24);
        assert!(out.contains("consulta: auth▏"), "{out}");
    }

    #[test]
    fn submit_emite_efecto_de_busqueda() {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        for c in "auth".chars() {
            reducer(&mut s, crate::app::Action::Input(c));
        }
        let effect = reducer(&mut s, crate::app::Action::Submit);
        assert_eq!(
            effect,
            crate::app::Effect::Search {
                query: "auth".into()
            }
        );
        assert!(matches!(&s.search, LoadState::Loading));
        assert_eq!(s.search_mode, SearchMode::Input); // pasa a lista al cargar
    }

    #[test]
    fn submit_vacio_no_busca() {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        let effect = reducer(&mut s, crate::app::Action::Submit);
        assert_eq!(effect, crate::app::Effect::None);
    }

    #[test]
    fn backspace_edita_y_esc_vuelve_a_input() {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        for c in "auth".chars() {
            reducer(&mut s, crate::app::Action::Input(c));
        }
        reducer(&mut s, crate::app::Action::Backspace);
        assert_eq!(s.search_query, "aut");
        // En fase lista, Esc vuelve a input (restaura la query).
        reducer(&mut s, crate::app::Action::Submit);
        let _ = hits_state(2);
        reducer(
            &mut s,
            crate::app::Action::SearchLoaded(SearchData {
                query: "aut".into(),
                hits: vec![],
            }),
        );
        assert_eq!(s.search_mode, SearchMode::List);
        reducer(&mut s, crate::app::Action::Back);
        assert_eq!(s.search_mode, SearchMode::Input);
        // En fase input, Esc sale de la pantalla (vuelve al Home/origen).
        let n = s.history.len();
        reducer(&mut s, crate::app::Action::Back);
        assert!(s.history.len() < n || s.screen != crate::app::Screen::Search);
    }

    #[test]
    fn lista_muestra_hits_fuente_escore() {
        let s = hits_state(3);
        assert_eq!(s.screen, crate::app::Screen::Search);
        let out = draw(&s, 80, 24);
        assert!(out.contains("Resultado 0"), "{out}");
        assert!(out.contains("episodic"), "{out}");
        assert!(out.contains("semantic"), "{out}");
        assert!(out.contains("vault/nota-0.md"), "{out}");
        assert!(out.contains("1/3"), "posición: {out}");
    }

    #[test]
    fn sin_resultados_es_explicito_y_reversible() {
        let mut s = AppState::new("es", (100, 30));
        reducer(&mut s, crate::app::Action::OpenSearch);
        for c in "nada".chars() {
            reducer(&mut s, crate::app::Action::Input(c));
        }
        reducer(
            &mut s,
            crate::app::Action::SearchLoaded(SearchData {
                query: "nada".into(),
                hits: vec![],
            }),
        );
        let out = draw(&s, 80, 24);
        assert!(out.contains("sin resultados para 'nada'"), "{out}");
    }

    #[test]
    fn enter_en_hit_notifica_la_ruta() {
        let mut s = hits_state(1);
        reducer(&mut s, crate::app::Action::Activate);
        assert_eq!(s.notifications.len(), 1);
        assert!(s.notifications[0].text.contains("vault/nota-0.md"));
    }
}
