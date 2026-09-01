//! Reducer puro (spec §2/§16.1): `update(&mut AppState, Action) -> Effect`.
//! Sin IO, sin render, sin terminal — testeable sin TTY. El runtime ejecuta
//! el efecto y devuelve acciones de datos.

use super::effect::Effect;
use super::state::{AppState, LoadState, Overlay, Screen, SearchMode};
use super::Action;
use crate::layout::layout_mode;
use crate::theme::StatusKind;

/// Reducer: estado + acción → (estado, efecto).
pub fn update(state: &mut AppState, action: Action) -> Effect {
    match action {
        Action::Tick => {
            state.tick = state.tick.saturating_add(1);
            expire_notifications(state);
            Effect::None
        }
        Action::Resize { width, height } => {
            state.size = (width, height);
            state.mode = layout_mode(ratatui::prelude::Rect::new(0, 0, width, height));
            // Altura visible de la lista: pantalla menos header y status bar.
            state.list_viewport = (height.saturating_sub(4)).max(1) as usize;
            keep_selection_visible(state);
            Effect::None
        }
        Action::SessionsLoaded(data) => {
            state.sessions = LoadState::Ready(data);
            state.offset = 0;
            state.selection = state.selection.min(state.list_len().saturating_sub(1));
            keep_selection_visible(state);
            Effect::None
        }
        Action::SessionsFailed(err) => {
            state.sessions = LoadState::Failed(err);
            Effect::None
        }
        Action::HomeLoaded(home) => {
            state.home = LoadState::Ready(home);
            Effect::None
        }
        Action::HomeFailed(err) => {
            state.home = LoadState::Failed(err);
            Effect::None
        }
        Action::SessionDetailLoaded(data) => {
            state.detail = LoadState::Ready(data);
            state.detail_scroll = 0;
            Effect::None
        }
        Action::SessionDetailFailed(err) => {
            state.detail = LoadState::Failed(err);
            Effect::None
        }
        Action::ActionsLoaded(data) => {
            state.actions = LoadState::Ready(data);
            state.selection = state.selection.min(state.list_len().saturating_sub(1));
            keep_selection_visible(state);
            Effect::None
        }
        Action::ActionsFailed(err) => {
            state.actions = LoadState::Failed(err);
            Effect::None
        }
        Action::SearchLoaded(data) => {
            state.search = LoadState::Ready(data);
            state.search_mode = SearchMode::List;
            state.selection = 0;
            state.offset = 0;
            keep_selection_visible(state);
            Effect::None
        }
        Action::SearchFailed(err) => {
            state.search = LoadState::Failed(err);
            state.search_mode = SearchMode::List;
            Effect::None
        }

        // ── navegación de lista ─────────────────────────────────────────
        Action::MoveUp => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = state.detail_scroll.saturating_sub(1);
            } else if state.list_len() > 0 && state.selection > 0 {
                state.selection -= 1;
                keep_selection_visible(state);
            }
            Effect::None
        }
        Action::MoveDown => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = state.detail_scroll.saturating_add(1);
            } else if state.list_len() > 0 && state.selection + 1 < state.list_len() {
                state.selection += 1;
                keep_selection_visible(state);
            }
            Effect::None
        }
        Action::GoTop => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = 0;
            } else {
                state.selection = 0;
                state.offset = 0;
            }
            Effect::None
        }
        Action::GoBottom => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = usize::MAX;
            } else if state.list_len() > 0 {
                state.selection = state.list_len() - 1;
                keep_selection_visible(state);
            }
            Effect::None
        }
        Action::PageUp => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = state
                    .detail_scroll
                    .saturating_sub(state.list_viewport.saturating_sub(1).max(1));
            } else {
                let step = state.list_viewport.saturating_sub(1).max(1);
                state.selection = state.selection.saturating_sub(step);
                keep_selection_visible(state);
            }
            Effect::None
        }
        Action::PageDown => {
            if state.screen == Screen::SessionDetail {
                state.detail_scroll = state.detail_scroll.saturating_add(state.list_viewport);
            } else {
                let step = state.list_viewport.saturating_sub(1).max(1);
                if state.list_len() > 0 {
                    state.selection = (state.selection + step).min(state.list_len() - 1);
                    keep_selection_visible(state);
                }
            }
            Effect::None
        }
        Action::FocusNext | Action::FocusPrevious => Effect::None,

        // ── mouse (input primario; teclado = accesibilidad) ─────────────────
        // El click se traduce a una acción semántica pura (hit::hit_test) y
        // se despacha por ESTE mismo reducer: clic y tecla son indivisibles.
        Action::Click { x, y } => match crate::hit::hit_test(state, x, y) {
            Some(inner) => update(state, inner),
            None => Effect::None,
        },
        Action::Hover { x, y } => {
            state.hover = Some((x, y));
            Effect::None
        }
        Action::Scroll { down } => update(state, if down { Action::MoveDown } else { Action::MoveUp }),
        Action::RowClick { index } => {
            if state.list_len() > 0 && index < state.list_len() {
                if index == state.selection {
                    // Segundo clic sobre lo ya seleccionado = activar.
                    return update(state, Action::Activate);
                }
                state.selection = index;
                keep_selection_visible(state);
            }
            Effect::None
        }

        Action::Activate => match state.screen {
            // Sesiones: Enter abre el detalle de la sesión (spec §11.4).
            Screen::Sessions => match &state.sessions {
                LoadState::Ready(d) => {
                    if let Some(row) = d.rows.get(state.selection) {
                        let id = row.session_id.clone();
                        state.navigate(Screen::SessionDetail);
                        state.detail = LoadState::Loading;
                        Effect::LoadSessionDetail { id }
                    } else {
                        Effect::None
                    }
                }
                _ => Effect::None,
            },
            // Acciones: Enter abre la revisión previa (spec §11.5).
            Screen::Actions => {
                if state.list_len() > 0 {
                    state.overlay = Overlay::Confirm {
                        index: state.selection,
                        armed: false,
                    };
                }
                Effect::None
            }
            // Búsqueda (fase lista): Enter muestra la ruta del hit (v1; el
            // feedback persistido espera el port nativo del collector).
            Screen::Search => match &state.search {
                LoadState::Ready(d) => {
                    if let Some(hit) = d.hits.get(state.selection) {
                        state.push_notification(
                            format!("{} · {}", hit.title, hit.path),
                            StatusKind::Active,
                        );
                    }
                    Effect::None
                }
                _ => Effect::None,
            },
            _ => Effect::None,
        },

        // ── navegación entre pantallas (back stack) ─────────────────────
        Action::OpenHome => {
            state.navigate(Screen::Home);
            Effect::None
        }
        Action::OpenSessions => {
            state.navigate(Screen::Sessions);
            Effect::None
        }
        Action::OpenActions => {
            state.navigate(Screen::Actions);
            Effect::None
        }

        // ── overlays y navegación ───────────────────────────────────────
        Action::Back => {
            if state.overlay != Overlay::None {
                state.overlay = Overlay::None;
            } else if state.screen == Screen::Search && state.search_mode == SearchMode::List {
                // Esc en la lista: volver a editar la query (spec §12:
                // Esc limpia/restaura — acá restaura el input).
                state.search_mode = SearchMode::Input;
            } else if let Some(prev) = state.history.pop() {
                state.screen = prev;
                state.selection = 0;
                state.offset = 0;
                state.detail_scroll = 0;
            }
            Effect::None
        }
        Action::OpenHelp => {
            state.overlay = Overlay::Help;
            Effect::None
        }
        Action::CloseOverlay => {
            state.overlay = Overlay::None;
            Effect::None
        }
        Action::OpenSearch => {
            state.navigate(Screen::Search);
            state.search_query.clear();
            state.search = LoadState::Idle;
            state.search_mode = SearchMode::Input;
            Effect::None
        }
        Action::Input(ch) => {
            if state.screen == Screen::Search && state.search_mode == SearchMode::Input {
                state.search_query.push(ch);
            }
            Effect::None
        }
        Action::Backspace => {
            if state.screen == Screen::Search && state.search_mode == SearchMode::Input {
                state.search_query.pop();
            }
            Effect::None
        }
        Action::Submit => {
            if state.screen == Screen::Search && state.search_mode == SearchMode::Input {
                let q = state.search_query.trim().to_string();
                if !q.is_empty() {
                    state.search = LoadState::Loading;
                    Effect::Search { query: q }
                } else {
                    Effect::None
                }
            } else {
                Effect::None
            }
        }

        Action::QuitRequested => {
            state.should_quit = true;
            Effect::Quit
        }

        // ── ACCIONES: revisión previa y ejecución ────────────────────────
        Action::ConfirmAction { index } => {
            if state.list_len() > 0 && index < state.list_len() {
                state.overlay = Overlay::Confirm {
                    index,
                    armed: false,
                };
            }
            Effect::None
        }
        Action::ConfirmArm => match state.overlay {
            Overlay::Confirm { index, armed } => {
                let reversible = match &state.actions {
                    LoadState::Ready(d) => {
                        d.proposals.get(index).map(|p| p.reversible).unwrap_or(true)
                    }
                    _ => true,
                };
                let execute = reversible || armed;
                if execute {
                    state.overlay = Overlay::None;
                    state.actions_queue.push_back(index);
                    state.push_notification(
                        if state.lang == "en" {
                            "executing…"
                        } else {
                            "ejecutando…"
                        },
                        StatusKind::Pending,
                    );
                    Effect::RunAction { index }
                } else {
                    // Irreversible: la primera Enter solo ARMA la confirmación
                    // (spec §11.5: la selección por defecto favorece la opción
                    // segura; doble Enter para destructivas).
                    state.overlay = Overlay::Confirm { index, armed: true };
                    state.push_notification(
                        if state.lang == "en" {
                            "Enter again to confirm"
                        } else {
                            "Enter de nuevo para confirmar"
                        },
                        StatusKind::Warning,
                    );
                    Effect::None
                }
            }
            // Lote auto-ok: contrato garantiza reversible+instant ⇒ un solo
            // Enter (el modal ya avisó el efecto).
            Overlay::ConfirmBatch { count, armed: _ } => {
                state.overlay = Overlay::None;
                let indexes: Vec<usize> = match &state.actions {
                    LoadState::Ready(d) => d
                        .proposals
                        .iter()
                        .enumerate()
                        .filter(|(_, p)| p.auto_ok)
                        .map(|(i, _)| i)
                        .collect(),
                    _ => vec![],
                };
                for i in indexes {
                    state.actions_queue.push_back(i);
                }
                let _ = count;
                state.push_notification(
                    if state.lang == "en" {
                        "executing batch…"
                    } else {
                        "ejecutando lote…"
                    },
                    StatusKind::Pending,
                );
                match state.actions_queue.front().copied() {
                    Some(f) => Effect::RunAction { index: f },
                    None => Effect::None,
                }
            }
            _ => Effect::None,
        },
        Action::ConfirmCancel => {
            state.overlay = Overlay::None;
            Effect::None
        }
        Action::ActionFinished { index, ok, message } => {
            // El índice terminado es el frente de la cola (FIFO: batch `a`
            // e individuales comparten el canal).
            if state.actions_queue.front() == Some(&index) {
                state.actions_queue.pop_front();
            }
            let next = state.actions_queue.front().copied();
            let kind = if ok {
                StatusKind::Success
            } else {
                StatusKind::Error
            };
            let label = if ok {
                if state.lang == "en" {
                    "done"
                } else {
                    "hecha"
                }
            } else {
                if state.lang == "en" {
                    "failed"
                } else {
                    "falló"
                }
            };
            let short = crate::components::truncate_visual(&message, 60);
            // Reemplaza la notificación "ejecutando…" (un solo mensaje vivo).
            if state
                .notifications
                .last()
                .is_some_and(|n| n.kind == StatusKind::Pending)
            {
                state.notifications.pop();
            }
            state.push_notification(format!("[{}]: {label} — {short}", index + 1), kind);
            // Si quedaron más del lote, el runtime encadena la siguiente.
            match next {
                Some(nx) => Effect::RunAction { index: nx },
                None => Effect::None,
            }
        }
        Action::ApproveAutoOk => {
            // Batch `a`: todas las auto-ok del catálogo visible (son
            // reversibles e instantáneas por contrato) con un solo modal.
            if state.screen == Screen::Actions {
                if let LoadState::Ready(d) = &state.actions {
                    let count = d.proposals.iter().filter(|p| p.auto_ok).count();
                    if count > 0 {
                        state.overlay = Overlay::ConfirmBatch {
                            count,
                            armed: false,
                        };
                    }
                }
            }
            Effect::None
        }
        Action::CopySelection => {
            let text = crate::app::copy_selection(state);
            match text {
                Some(t) => Effect::CopyToClipboard { text: t },
                None => {
                    state.push_notification(
                        if state.lang == "en" {
                            "nothing copyable here"
                        } else {
                            "nada copiable acá"
                        },
                        StatusKind::Pending,
                    );
                    Effect::None
                }
            }
        }
        Action::MarkUseful => {
            if let LoadState::Ready(d) = &state.search {
                if let Some(hit) = d.hits.get(state.selection) {
                    match &hit.memory_id {
                        Some(mid) => Effect::MarkUseful {
                            memory_id: mid.clone(),
                        },
                        None => {
                            state.push_notification(
                                if state.lang == "en" {
                                    "only episodic hits can be marked useful"
                                } else {
                                    "solo los hits episódicos son marcables"
                                },
                                StatusKind::Pending,
                            );
                            Effect::None
                        }
                    }
                } else {
                    Effect::None
                }
            } else {
                Effect::None
            }
        }
        Action::DismissNotification => {
            if !state.notifications.is_empty() {
                state.notifications.remove(0);
            }
            Effect::None
        }
    }
}

/// Expira notificaciones vencidas (spec §13: los éxitos pueden expirar;
/// los errores persisten hasta acción del usuario).
fn expire_notifications(state: &mut AppState) {
    state
        .notifications
        .retain(|n| n.kind == crate::theme::StatusKind::Error || n.expires_at_tick > state.tick);
}

/// Invariante (spec §16.4): mientras haya espacio, el offset mantiene la
/// selección visible; el offset se ajusta solo lo necesario.
pub fn keep_selection_visible(state: &mut AppState) {
    let len = state.list_len();
    if len == 0 {
        state.selection = 0;
        state.offset = 0;
        return;
    }
    state.selection = state.selection.min(len - 1);
    if state.selection < state.offset {
        state.offset = state.selection;
    } else if state.offset + state.list_viewport > len {
        // La lista no llena el viewport: sin scroll.
        state.offset = 0;
    } else if state.selection >= state.offset + state.list_viewport {
        state.offset = state.selection + 1 - state.list_viewport;
    }
}

/// Texto copiable de la selección actual (spec §12: `c` solo en contenido
/// copiable): id de sesión (lista/detalle) o ruta del hit (búsqueda).
pub fn copy_selection(state: &AppState) -> Option<String> {
    match state.screen {
        Screen::Sessions => match &state.sessions {
            LoadState::Ready(d) => d.rows.get(state.selection).map(|r| r.session_id.clone()),
            _ => None,
        },
        Screen::SessionDetail => match &state.detail {
            LoadState::Ready(d) => Some(d.session_id.clone()),
            _ => None,
        },
        Screen::Search => match (&state.search, state.search_mode) {
            (LoadState::Ready(d), SearchMode::List) => {
                d.hits.get(state.selection).map(|h| h.path.clone())
            }
            _ => None,
        },
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::super::state::{AppState, LoadState, Overlay};
    use super::*;
    use crate::sessions::{SessionRow, SessionsScreenData};

    fn state_con(n: usize) -> AppState {
        let mut s = AppState::new("es", (100, 30));
        s.list_viewport = 5; // viewport chico para probar scroll
        s.sessions = LoadState::Ready(SessionsScreenData {
            rows: (0..n)
                .map(|i| SessionRow {
                    session_id: format!("2026-05-{i:02}_s"),
                    status: "open".into(),
                    mode: "managed".into(),
                    opened_at: "2026-05-01T10:00:00+00:00".into(),
                    closed_at: None,
                    checkpoint_count: 0,
                    spec_summary: "demo".into(),
                })
                .collect(),
            active_id: None,
            now: chrono::DateTime::parse_from_rfc3339("2026-05-17T10:00:00+00:00")
                .unwrap()
                .with_timezone(&chrono::Utc),
            counts: Default::default(),
        });
        s
    }

    #[test]
    fn quit_pide_efecto() {
        let mut s = AppState::new("es", (100, 30));
        assert_eq!(update(&mut s, Action::QuitRequested), Effect::Quit);
        assert!(s.should_quit);
    }

    #[test]
    fn esc_cierra_overlay_primero() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::OpenHelp);
        assert_eq!(s.overlay, Overlay::Help);
        update(&mut s, Action::Back);
        assert_eq!(s.overlay, Overlay::None);
    }

    #[test]
    fn movimiento_respeta_limites() {
        let mut s = state_con(3);
        update(&mut s, Action::MoveDown);
        assert_eq!(s.selection, 1);
        update(&mut s, Action::MoveDown);
        update(&mut s, Action::MoveDown); // tope
        assert_eq!(s.selection, 2);
        update(&mut s, Action::GoBottom);
        assert_eq!(s.selection, 2);
        update(&mut s, Action::MoveUp);
        assert_eq!(s.selection, 1);
        update(&mut s, Action::GoTop);
        assert_eq!(s.selection, 0);
    }

    #[test]
    fn pagina_se_mueve_por_viewport() {
        let mut s = state_con(20);
        s.selection = 0;
        update(&mut s, Action::PageDown);
        assert_eq!(s.selection, 4);
        update(&mut s, Action::PageUp);
        assert_eq!(s.selection, 0);
    }

    #[test]
    fn offset_mantiene_seleccion_visible() {
        let mut s = state_con(20);
        // Bajar hasta el final: el offset debe desplazarse para seguir viendo.
        for _ in 0..25 {
            update(&mut s, Action::MoveDown);
        }
        assert_eq!(s.selection, 19);
        assert!(s.selection < s.offset + s.list_viewport);
        assert!(s.selection >= s.offset);
        assert!(s.offset + s.list_viewport <= 20);
    }

    #[test]
    fn resize_ajusta_viewport_y_seleccion() {
        let mut s = state_con(20);
        update(&mut s, Action::MoveDown);
        update(
            &mut s,
            Action::Resize {
                width: 60,
                height: 12,
            },
        );
        assert_eq!(s.mode, crate::layout::LayoutMode::Minimal);
        assert_eq!(s.list_viewport, 8);
        assert!(s.selection < 20);
        // Selección conservada (spec §16.1: resize preserva selección).
        assert_eq!(s.selection, 1);
    }

    #[test]
    fn sesiones_cargadas_resetean_seleccion_si_vacia() {
        let mut s = state_con(5);
        update(&mut s, Action::MoveDown);
        assert_eq!(s.selection, 1);
        update(
            &mut s,
            Action::SessionsLoaded(SessionsScreenData::default()),
        );
        assert_eq!(s.selection, 0);
    }

    #[test]
    fn error_no_revienta_y_reintenta_con_tick() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::SessionsFailed("storage roto".into()));
        assert!(matches!(s.sessions, LoadState::Failed(_)));
        // El runtime reintenta: vuelve a Loading y despacha datos.
        update(
            &mut s,
            Action::SessionsLoaded(SessionsScreenData::default()),
        );
        assert!(matches!(s.sessions, LoadState::Ready(_)));
    }

    #[test]
    fn notificaciones_experian() {
        let mut s = AppState::new("es", (100, 30));
        s.push_notification("ok", crate::theme::StatusKind::Success);
        for _ in 0..20 {
            update(&mut s, Action::Tick);
        }
        update(&mut s, Action::Tick);
        assert!(s.notifications.is_empty());
    }

    #[test]
    fn errores_no_experian() {
        let mut s = AppState::new("es", (100, 30));
        s.push_notification("grave", crate::theme::StatusKind::Error);
        for _ in 0..50 {
            update(&mut s, Action::Tick);
        }
        assert_eq!(s.notifications.len(), 1);
        update(&mut s, Action::DismissNotification);
        assert!(s.notifications.is_empty());
    }

    // ── ACCIONES: revisión previa (spec §11.5) ──────────────────────────

    fn action_state(n: usize) -> AppState {
        let mut s = AppState::for_actions("es", (100, 30));
        s.list_viewport = 10;
        use crate::actions::{ActionView, ActionsData};
        s.actions = LoadState::Ready(ActionsData {
            proposals: (0..n)
                .map(|i| ActionView {
                    id: format!("test.accion_{i}"),
                    title: format!("Acción de prueba {i}"),
                    category: "maintenance".into(),
                    effect: "efecto de la acción".into(),
                    cost: "seconds".into(),
                    reversible: i % 2 == 0, // pares reversibles
                    auto_ok: false,
                    score: 5.0,
                })
                .collect(),
        });
        s
    }

    #[test]
    fn acciones_reversibles_se_ejecutan_con_un_enter() {
        let mut s = action_state(2);
        update(&mut s, Action::Activate); // Enter sobre la lista
        assert_eq!(
            s.overlay,
            Overlay::Confirm {
                index: 0,
                armed: false
            }
        );
        let effect = update(&mut s, Action::ConfirmArm);
        assert_eq!(effect, Effect::RunAction { index: 0 });
        assert_eq!(s.overlay, Overlay::None);
        assert_eq!(s.actions_queue.front(), Some(&0));
    }

    #[test]
    fn acciones_irreversibles_requieren_doble_enter() {
        let mut s = action_state(3);
        update(&mut s, Action::MoveDown); // selección 1 (irreversible)
        update(&mut s, Action::Activate);
        assert_eq!(
            s.overlay,
            Overlay::Confirm {
                index: 1,
                armed: false
            }
        );
        // Primera Enter: solo arma la confirmación.
        let effect = update(&mut s, Action::ConfirmArm);
        assert_eq!(effect, Effect::None);
        assert_eq!(
            s.overlay,
            Overlay::Confirm {
                index: 1,
                armed: true
            }
        );
        assert_eq!(s.actions_queue.front(), None);
        // Segunda Enter: ejecuta.
        let effect = update(&mut s, Action::ConfirmArm);
        assert_eq!(effect, Effect::RunAction { index: 1 });
        assert_eq!(s.actions_queue.front(), Some(&1));
    }

    #[test]
    fn esc_cancela_la_confirmacion() {
        let mut s = action_state(2);
        update(&mut s, Action::Activate);
        update(&mut s, Action::ConfirmCancel);
        assert_eq!(s.overlay, Overlay::None);
        assert_eq!(s.actions_queue.front(), None);
    }

    #[test]
    fn action_finished_notifica_y_libera() {
        let mut s = action_state(2);
        update(&mut s, Action::Activate);
        update(&mut s, Action::ConfirmArm);
        assert_eq!(s.actions_queue.front(), Some(&0));
        update(
            &mut s,
            Action::ActionFinished {
                index: 0,
                ok: true,
                message: "[dry-run] efecto".into(),
            },
        );
        assert_eq!(s.actions_queue.front(), None);
        assert_eq!(s.notifications.len(), 1);
        assert_eq!(s.notifications[0].kind, crate::theme::StatusKind::Success);
    }

    #[test]
    fn q_no_es_bloqueado_por_confirmacion_en_reducer() {
        // El keymap bloquea q con overlay; el reducer solo procesa lo que
        // recibe (QuitRequested sigue funcionando fuera del modal).
        let mut s = action_state(2);
        update(&mut s, Action::Activate);
        assert_eq!(
            s.overlay,
            Overlay::Confirm {
                index: 0,
                armed: false
            }
        );
        update(&mut s, Action::QuitRequested);
        assert!(s.should_quit);
    }

    // ── navegación entre pantallas (back stack, spec §12) ───────────────

    #[test]
    fn navegacion_preserva_historial_y_back_vuelve() {
        let mut s = AppState::new("es", (100, 30)); // screen Sessions
        update(&mut s, Action::OpenActions);
        assert_eq!(s.screen, Screen::Actions);
        assert_eq!(s.history, vec![Screen::Sessions]);
        update(&mut s, Action::Back);
        assert_eq!(s.screen, Screen::Sessions);
        assert!(s.history.is_empty());
        // Back sin historial: no-op (no cierra la TUI por accidente).
        update(&mut s, Action::Back);
        assert_eq!(s.screen, Screen::Sessions);
    }

    #[test]
    fn no_navega_dos_veces_a_la_misma_pantalla() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::Back); // no-op
        assert_eq!(s.history.len(), 0);
        update(&mut s, Action::OpenSessions); // ya es Sessions
        assert_eq!(s.screen, Screen::Sessions);
        assert_eq!(s.history.len(), 0);
    }

    #[test]
    fn enter_en_sesiones_abre_detalle_con_efecto() {
        let mut s = state_con(3);
        let efecto = update(&mut s, Action::Activate);
        assert_eq!(s.screen, Screen::SessionDetail);
        assert_eq!(s.history, vec![Screen::Sessions]);
        assert!(matches!(&s.detail, LoadState::Loading));
        let Effect::LoadSessionDetail { id } = efecto else {
            panic!("esperaba LoadSessionDetail, got {efecto:?}");
        };
        assert_eq!(id, "2026-05-00_s");
    }

    #[test]
    fn detalle_cargado_o_fallido_se_refleja() {
        let mut s = AppState::new("es", (100, 30));
        update(
            &mut s,
            Action::SessionDetailLoaded(crate::session_detail::SessionDetailData {
                session_id: "2026-05-17_demo".into(),
                status: "open".into(),
                mode: "managed".into(),
                spec_path: "vault/specs/x.md".into(),
                spec_summary: "demo".into(),
                opened_at: "2026-05-17T10:00:00+00:00".into(),
                closed_at: None,
                now: chrono::DateTime::parse_from_rfc3339("2026-05-17T12:00:00+00:00")
                    .unwrap()
                    .with_timezone(&chrono::Utc),
                checkpoints: vec![],
                verification: vec![],
                tasks: vec![],
                diff_preview: String::new(),
                diff_error: None,
            }),
        );
        assert!(matches!(&s.detail, LoadState::Ready(_)));
        update(&mut s, Action::SessionDetailFailed("roto".into()));
        assert!(matches!(&s.detail, LoadState::Failed(_)));
    }

    // ── lote auto-ok (doc 05 §3.5: `a`) ─────────────────────────────────

    fn auto_ok_state() -> AppState {
        let mut s = action_state(3);
        // action_state: pares reversibles, todos auto_ok=false; marco 2.
        use crate::actions::{ActionView, ActionsData};
        s.actions = LoadState::Ready(ActionsData {
            proposals: (0..3)
                .map(|i| ActionView {
                    id: format!("test.accion_{i}"),
                    title: format!("Acción {i}"),
                    category: "maintenance".into(),
                    effect: "efecto".into(),
                    cost: "instant".into(),
                    reversible: true,
                    auto_ok: i < 2,
                    score: 5.0,
                })
                .collect(),
        });
        s.screen = Screen::Actions;
        s
    }

    #[test]
    fn batch_auto_ok_abre_modal_y_encola_todas() {
        let mut s = auto_ok_state();
        update(&mut s, Action::ApproveAutoOk);
        assert_eq!(
            s.overlay,
            Overlay::ConfirmBatch {
                count: 2,
                armed: false
            }
        );
        let effect = update(&mut s, Action::ConfirmArm);
        assert_eq!(effect, Effect::RunAction { index: 0 });
        assert_eq!(s.actions_queue.len(), 2, "encola las dos");
        assert_eq!(s.overlay, Overlay::None);
    }

    #[test]
    fn lote_encadena_hasta_vaciar_la_cola() {
        let mut s = auto_ok_state();
        update(&mut s, Action::ApproveAutoOk);
        update(&mut s, Action::ConfirmArm); // front = 0
                                            // Termina la 0: el reducer encadena la 1.
        let effect = update(
            &mut s,
            Action::ActionFinished {
                index: 0,
                ok: true,
                message: "hecha".into(),
            },
        );
        assert_eq!(effect, Effect::RunAction { index: 1 });
        assert_eq!(s.actions_queue.len(), 1);
        // Termina la 1: cola vacía, sin efecto.
        let effect = update(
            &mut s,
            Action::ActionFinished {
                index: 1,
                ok: true,
                message: "hecha".into(),
            },
        );
        assert_eq!(effect, Effect::None);
        assert!(s.actions_queue.is_empty());
    }

    #[test]
    fn sin_auto_ok_no_hay_modal() {
        let mut s = action_state(2); // ninguno auto_ok
        s.screen = Screen::Actions;
        update(&mut s, Action::ApproveAutoOk);
        assert_eq!(s.overlay, Overlay::None);
    }

    #[test]
    fn copy_selection_por_pantalla() {
        // Sesiones: copia el id seleccionado.
        let mut s = state_con(3);
        update(&mut s, Action::MoveDown);
        let effect = update(&mut s, Action::CopySelection);
        let Effect::CopyToClipboard { text } = effect else {
            panic!("esperaba copiar, got {effect:?}");
        };
        assert_eq!(text, "2026-05-01_s");
        // Detalle: copia el id.
        let mut s = AppState::new("es", (100, 30));
        s.screen = Screen::SessionDetail;
        update(
            &mut s,
            Action::SessionDetailLoaded(crate::session_detail::SessionDetailData {
                session_id: "2026-05-17_demo".into(),
                status: "open".into(),
                mode: "managed".into(),
                spec_path: "x".into(),
                spec_summary: "d".into(),
                opened_at: "2026-05-17T10:00:00+00:00".into(),
                closed_at: None,
                now: chrono::DateTime::parse_from_rfc3339("2026-05-17T12:00:00+00:00")
                    .unwrap()
                    .with_timezone(&chrono::Utc),
                checkpoints: vec![],
                verification: vec![],
                tasks: vec![],
                diff_preview: String::new(),
                diff_error: None,
            }),
        );
        let effect = update(&mut s, Action::CopySelection);
        let Effect::CopyToClipboard { text } = effect else {
            panic!("esperaba copiar, got {effect:?}");
        };
        assert_eq!(text, "2026-05-17_demo");
        // Sin contenido copiable: aviso muted, sin efecto.
        let mut s = AppState::new("es", (100, 30));
        let effect = update(&mut s, Action::CopySelection);
        assert_eq!(effect, Effect::None);
        assert_eq!(s.notifications.len(), 1);
    }

    #[test]
    fn mark_useful_solo_hits_episodicos() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::OpenSearch);
        update(
            &mut s,
            Action::SearchLoaded(crate::app::search::SearchData {
                query: "q".into(),
                hits: vec![crate::app::search::SearchHit {
                    source: "semantic".into(),
                    score: 0.5,
                    title: "doc".into(),
                    path: "vault/x.md".into(),
                    memory_id: None,
                }],
            }),
        );
        let effect = update(&mut s, Action::MarkUseful);
        assert_eq!(effect, Effect::None);
        assert!(s.notifications[0].text.contains("episódicos"));
        // Episódico con id: efecto de persistencia.
        update(
            &mut s,
            Action::SearchLoaded(crate::app::search::SearchData {
                query: "q".into(),
                hits: vec![crate::app::search::SearchHit {
                    source: "episodic".into(),
                    score: 0.5,
                    title: "mem".into(),
                    path: "id=mem-1".into(),
                    memory_id: Some("mem-1".into()),
                }],
            }),
        );
        let effect = update(&mut s, Action::MarkUseful);
        assert_eq!(
            effect,
            Effect::MarkUseful {
                memory_id: "mem-1".into()
            }
        );
    }

    #[test]
    fn scroll_del_detalle_es_acotado() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::MoveDown); // sin datos: no-op
        assert_eq!(s.detail_scroll, 0);
        s.screen = Screen::SessionDetail;
        for _ in 0..5 {
            update(&mut s, Action::MoveDown);
        }
        assert_eq!(s.detail_scroll, 5);
        for _ in 0..9 {
            update(&mut s, Action::MoveUp);
        }
        assert_eq!(s.detail_scroll, 0);
    }

    // ── mouse: click y rueda producen las mismas transiciones que el teclado ──

    #[test]
    fn click_en_boton_status_navega() {
        let mut s = AppState::with_screen(Screen::Home, "es", (120, 30));
        let status = crate::hit::root_chunks(ratatui::prelude::Rect::new(0, 0, 120, 30))[2];
        let (cell, _) = crate::hit::status_cells(status)
            .into_iter()
            .find(|(_, h)| h.key == "[s]")
            .unwrap();
        update(&mut s, Action::Click { x: cell.x + 1, y: status.y });
        assert_eq!(s.screen, Screen::Sessions);
    }

    #[test]
    fn click_en_fila_selecciona_y_vuelve_a_activar() {
        let mut s = state_con(3);
        s.screen = Screen::Sessions;
        update(&mut s, Action::RowClick { index: 2 });
        assert_eq!(s.selection, 2);
        assert_eq!(s.screen, Screen::Sessions); // primer clic: solo selección
        // Clic sobre la ya seleccionada = Activate (abre el detalle, como Enter).
        update(&mut s, Action::RowClick { index: 2 });
        assert_eq!(s.screen, Screen::SessionDetail);
    }

    #[test]
    fn rueda_equivale_a_j_k() {
        let mut s = state_con(3);
        s.screen = Screen::Sessions;
        update(&mut s, Action::Scroll { down: true });
        assert_eq!(s.selection, 1);
        update(&mut s, Action::Scroll { down: false });
        assert_eq!(s.selection, 0);
    }

    #[test]
    fn hover_guarda_posicion() {
        let mut s = AppState::new("es", (100, 30));
        update(&mut s, Action::Hover { x: 42, y: 7 });
        assert_eq!(s.hover, Some((42, 7)));
    }
}
