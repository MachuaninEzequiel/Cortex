//! Ciclo de vida de terminal (spec §15): raw mode + alternate screen +
//! cursor oculto, con restauración RAII garantizada (Drop) y hook de panic.
//!
//! Extraído de `cortex-cli session watch` (T6-b): el CLI ya no contiene el
//! lifecycle; acá vive y se reutiliza por cualquier pantalla.

use std::io::stdout;

use ratatui::crossterm::cursor::{Hide, Show};
use ratatui::crossterm::event::{DisableMouseCapture, EnableMouseCapture};
use ratatui::crossterm::execute;
use ratatui::crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};

/// Hook de panic instalado por `Tui::enter`; restaura el terminal aunque un
/// `panic!` corte el flujo antes del `Drop` (spec §15: "Nunca dejar el
/// terminal en raw mode tras un error").
fn install_panic_hook() {
    use std::sync::atomic::{AtomicBool, Ordering};
    static INSTALLED: AtomicBool = AtomicBool::new(false);
    if INSTALLED.swap(true, Ordering::SeqCst) {
        return;
    }
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        // Última defensa: restaurar sin unwrap (spec §15: evitar unwrap en
        // cleanup). Los errores se ignoran a propósito.
        let _ = execute!(stdout(), LeaveAlternateScreen, DisableMouseCapture, Show);
        let _ = disable_raw_mode();
        eprintln!("cortex-tui: error fatal — {info}");
        previous(info);
    }));
}

/// Guard de terminal: mientras viva, raw mode + alternate screen activos.
/// `Drop` restaura pase lo que pase (salida normal, error o panic).
pub struct Tui {
    restored: bool,
}

impl Tui {
    /// Entra al modo TUI: raw mode + pantalla alterna + cursor oculto.
    /// En cualquier fallo intermedio restaura lo ya abierto y devuelve `Err`.
    pub fn enter() -> Result<Self, String> {
        install_panic_hook();
        if enable_raw_mode().is_err() {
            return Err("no se pudo habilitar el modo raw.".into());
        }
        let mut tui = Self { restored: false };
        if execute!(stdout(), EnterAlternateScreen, EnableMouseCapture, Hide).is_err() {
            tui.restore();
            return Err("no se pudo entrar a la pantalla alterna.".into());
        }
        Ok(tui)
    }

    /// Restaura el terminal de forma idempotente.
    pub fn restore(&mut self) {
        if self.restored {
            return;
        }
        let _ = execute!(stdout(), LeaveAlternateScreen, DisableMouseCapture, Show);
        let _ = disable_raw_mode();
        self.restored = true;
    }
}

impl Drop for Tui {
    fn drop(&mut self) {
        self.restore();
    }
}

/// Dimensiones actuales de la terminal (fallback 80×24 si no se puede leer).
pub fn terminal_size() -> (u16, u16) {
    ratatui::crossterm::terminal::size().unwrap_or((80, 24))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn restore_es_idempotente() {
        // Sin terminal real: el guard debe poder construirse y restaurarse
        // sin panic (los comandos fallan silenciosamente en no-tty).
        let mut tui = Tui { restored: false };
        tui.restore();
        tui.restore();
        assert!(tui.restored);
    }

    #[test]
    fn drop_restaura_si_falta_restore_explicito() {
        let tui = Tui { restored: false };
        drop(tui); // no debe panic ni colgar
    }
}
