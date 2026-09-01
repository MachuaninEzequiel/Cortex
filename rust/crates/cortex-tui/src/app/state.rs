//! Estado de la aplicación (spec §5): enums exhaustivos, sin combinaciones
//! imposibles de booleanos; el render es función pura del estado.

use crate::layout::LayoutMode;

/// Pantalla activa. F3/F4 del rediseño: Home (raíz), Sesiones, Acciones,
/// Detalle de sesión y Búsqueda.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Screen {
    Home,
    Sessions,
    Actions,
    SessionDetail,
    Search,
}

/// Fase de la pantalla de búsqueda: edición del input o navegación de
/// resultados (spec §12: Enter confirma, Esc limpia y restaura).
#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum SearchMode {
    #[default]
    Input,
    List,
}

/// Overlay modal sobre la pantalla (spec §5): focus trap, Esc cierra.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Overlay {
    None,
    Help,
    /// Revisión previa de una acción (spec §11.5). `armed` = el usuario ya
    /// confirmó una vez (las irreversibles exigen doble Enter).
    Confirm {
        index: usize,
        armed: bool,
    },
    /// Revisión previa del lote auto-ok (doc 05 §3.5: `a` = aceptar todas
    /// las auto-ok con confirmación única; son reversibles e instantáneas
    /// por contrato del motor).
    ConfirmBatch {
        count: usize,
        armed: bool,
    },
}

/// Estado de carga de datos por pantalla (spec §11.7). `Empty` se deriva
/// de los datos (`SessionsScreenData::rows` vacías): el estado vacío
/// explica qué falta y ofrece acción.
#[derive(Clone, Debug)]
pub enum LoadState<T> {
    Idle,
    Loading,
    Ready(T),
    Failed(String),
}

/// Notificación efímera (spec §13 Feedback): expira por ticks.
#[derive(Clone, Debug)]
pub struct Notification {
    pub text: String,
    pub kind: crate::theme::StatusKind,
    pub expires_at_tick: u64,
}

/// Estado raíz de la TUI.
#[derive(Clone, Debug)]
pub struct AppState {
    pub screen: Screen,
    pub overlay: Overlay,
    pub size: (u16, u16),
    /// Derivado del área en cada `Resize`/construcción (spec §9: el modo
    /// no es estado mutable independiente, pero se cachea por render).
    pub mode: LayoutMode,
    pub lang: &'static str,
    /// Snapshot real del Home (proyecto/rama/sesión/vault/salud).
    pub home: LoadState<crate::home::HomeState>,
    pub sessions: LoadState<crate::sessions::SessionsScreenData>,
    /// Propuestas del ActionEngine (pantalla ACCIONES).
    pub actions: LoadState<crate::actions::ActionsData>,
    /// Detalle de la sesión seleccionada (pantalla DETALLE).
    pub detail: LoadState<crate::session_detail::SessionDetailData>,
    /// Resultados de la pantalla de búsqueda.
    pub search: LoadState<crate::app::search::SearchData>,
    /// Texto actual del input de búsqueda.
    pub search_query: String,
    /// Fase de la búsqueda (input vs lista de resultados).
    pub search_mode: SearchMode,
    /// Índices de acciones en ejecución/en cola (cola FIFO: el batch `a` y
    /// las confirmaciones individuales comparten el canal; el front es la
    /// acción corriendo — spinner).
    pub actions_queue: std::collections::VecDeque<usize>,
    /// Historial de navegación para Esc/B (spec §5: back stack).
    pub history: Vec<Screen>,
    /// Scroll de la pantalla de detalle (reducer no conoce el máximo;
    /// el render clampea al rango real).
    pub detail_scroll: usize,
    /// Índice seleccionado en la lista actual y offset de scroll.
    pub selection: usize,
    pub offset: usize,
    /// Altura visible de la lista (el reducer la mantiene para que el
    /// offset siempre deje la selección a la vista — spec §16.4).
    pub list_viewport: usize,
    /// Cola de notificaciones (una visible, el resto encoladas).
    pub notifications: Vec<Notification>,
    /// Tick actual (avanza con `Action::Tick`).
    pub tick: u64,
    /// Posición del cursor del mouse (resaltado de hover en botones; `hit`).
    pub hover: Option<(u16, u16)>,
    pub should_quit: bool,
}

impl AppState {
    pub fn new(lang: &'static str, size: (u16, u16)) -> Self {
        Self::with_screen(Screen::Sessions, lang, size)
    }

    /// Estado raíz para la pantalla de ACCIONES (`cortex next --tui`).
    pub fn for_actions(lang: &'static str, size: (u16, u16)) -> Self {
        Self::with_screen(Screen::Actions, lang, size)
    }

    pub fn with_screen(screen: Screen, lang: &'static str, size: (u16, u16)) -> Self {
        let mode = crate::layout::layout_mode(ratatui::prelude::Rect::new(0, 0, size.0, size.1));
        Self {
            screen,
            overlay: Overlay::None,
            size,
            mode,
            lang,
            home: LoadState::Idle,
            sessions: LoadState::Loading,
            actions: LoadState::Idle,
            detail: LoadState::Idle,
            search: LoadState::Idle,
            search_query: String::new(),
            search_mode: SearchMode::Input,
            actions_queue: std::collections::VecDeque::new(),
            history: Vec::new(),
            detail_scroll: 0,
            selection: 0,
            offset: 0,
            list_viewport: size.1.saturating_sub(4).max(1) as usize,
            notifications: Vec::new(),
            tick: 0,
            hover: None,
            should_quit: false,
        }
    }

    /// Longitud de la lista actual (0 si no hay datos listos).
    pub fn list_len(&self) -> usize {
        match self.screen {
            Screen::Sessions => match &self.sessions {
                LoadState::Ready(d) => d.rows.len(),
                _ => 0,
            },
            Screen::Actions => match &self.actions {
                LoadState::Ready(d) => d.proposals.len(),
                _ => 0,
            },
            Screen::Search => match &self.search {
                LoadState::Ready(d) => d.hits.len(),
                _ => 0,
            },
            Screen::Home | Screen::SessionDetail => 0,
        }
    }

    /// Navega a otra pantalla preservando el back stack (spec §5).
    pub fn navigate(&mut self, target: Screen) {
        if self.screen == target {
            return;
        }
        self.history.push(self.screen);
        self.screen = target;
        self.selection = 0;
        self.offset = 0;
        self.detail_scroll = 0;
    }

    pub fn push_notification(&mut self, text: impl Into<String>, kind: crate::theme::StatusKind) {
        self.notifications.push(Notification {
            text: text.into(),
            kind,
            expires_at_tick: self.tick + 20,
        });
        if self.notifications.len() > 3 {
            self.notifications.remove(0);
        }
    }

    /// Índice de la acción actualmente ejecutándose (frente de la cola).
    pub fn actions_front(&self) -> Option<usize> {
        self.actions_queue.front().copied()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn estado_nuevo_empieza_cargando() {
        let s = AppState::new("es", (100, 30));
        assert!(matches!(s.sessions, LoadState::Loading));
        assert_eq!(s.mode, LayoutMode::Standard);
        assert_eq!(s.selection, 0);
        assert!(!s.should_quit);
    }

    #[test]
    fn list_len_solo_con_datos() {
        let mut s = AppState::new("es", (100, 30));
        assert_eq!(s.list_len(), 0);
        s.sessions = LoadState::Ready(crate::sessions::SessionsScreenData::default());
        assert_eq!(s.list_len(), 0);
    }
}
