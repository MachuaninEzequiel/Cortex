//! Acciones SEMÁNTICAS (spec §5): el keymap traduce teclas → `Action`; el
//! reducer decide transiciones. Ninguna pantalla hace `match KeyCode`.

/// Acción semántica producida por el keymap o el runtime.
#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    /// Tick de reloj (spinners, expiración de notificaciones).
    Tick,
    /// El terminal cambió de tamaño.
    Resize {
        width: u16,
        height: u16,
    },
    /// Datos recargados por el runtime (snapshot nuevo).
    SessionsLoaded(crate::sessions::SessionsScreenData),
    /// La recarga falló (el runtime reintenta en el próximo tick).
    SessionsFailed(String),
    /// Snapshot REAL del Home (proyecto/rama/sesión/vault/salud).
    HomeLoaded(crate::home::HomeState),
    HomeFailed(String),
    /// Detalle de la sesión seleccionada cargado por el runtime.
    SessionDetailLoaded(crate::session_detail::SessionDetailData),
    SessionDetailFailed(String),
    /// Propuestas del ActionEngine recargadas (pantalla ACCIONES).
    ActionsLoaded(crate::actions::ActionsData),
    /// El motor no pudo armar propuestas (p. ej. proyecto sin config).
    ActionsFailed(String),
    /// Resultados de la búsqueda (pantalla BUSCAR).
    SearchLoaded(crate::app::search::SearchData),
    SearchFailed(String),

    MoveUp,
    MoveDown,
    FocusNext,
    FocusPrevious,
    GoTop,
    GoBottom,
    PageUp,
    PageDown,
    /// Abrir/activar el elemento seleccionado.
    Activate,
    /// Navegación entre pantallas (back stack, spec §12).
    OpenHome,
    OpenSessions,
    OpenActions,
    /// Volver: cierra overlay/input primero, luego pantalla anterior.
    Back,
    QuitRequested,
    OpenHelp,
    CloseOverlay,
    /// Búsqueda: abrir la pantalla con el input con foco.
    OpenSearch,
    Input(char),
    Backspace,
    Submit,
    /// Descartar la notificación más reciente.
    DismissNotification,

    // ── pantalla ACCIONES: revisión previa (spec §11.5) ──────────────────
    /// Enter sobre el ítem: abre el modal de revisión previa.
    ConfirmAction {
        index: usize,
    },
    /// Enter dentro del modal: arma la confirmación (1ª vez si irreversible)
    /// o ejecuta (reversible, o 2ª vez en irreversible).
    ConfirmArm,
    /// Esc en el modal / ahora no.
    ConfirmCancel,
    /// El runtime terminó la ejecución (resultado del runner).
    ActionFinished {
        index: usize,
        ok: bool,
        message: String,
    },
    /// Batch `a`: aceptar todas las auto-ok (doc 05 §3.5) — abre el modal
    /// de revisión del lote (reversibles e instantáneas por contrato).
    ApproveAutoOk,
    /// Copiar la selección actual (spec §12: `c` en contenido copiable).
    CopySelection,
    /// Marcar útil el hit de búsqueda seleccionado (feedback persistido).
    MarkUseful,

    // ── mouse (input primario; teclado queda como accesibilidad) ─────────
    /// Clic izquierdo: el reducer hace hit-test contra la geometría de `hit`.
    /// Si no cae en una zona activa, no-op (nunca se pierde el estado).
    Click {
        x: u16,
        y: u16,
    },
    /// Mover el mouse: solo actualiza el resaltado de hover.
    Hover {
        x: u16,
        y: u16,
    },
    /// Rueda del mouse (equivalente a j/k de lista).
    Scroll {
        down: bool,
    },
    /// Click sobre una fila de lista: selecciona; si ya estaba seleccionada,
    /// activa (patrón de doble-clic semántico sin cronometrar clicks).
    RowClick {
        index: usize,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acciones_son_comparables() {
        assert_eq!(Action::MoveUp, Action::MoveUp);
        assert_ne!(Action::MoveUp, Action::MoveDown);
    }
}
