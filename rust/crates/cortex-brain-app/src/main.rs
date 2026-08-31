//! Entrypoint del binario `cortex-brain` (G-A1).
//!
//! Decide el rol según argv:
//! - `--query ...`        ⇒ cliente IPC (G-A9).
//! - `--projects-list`    ⇒ lista proyectos y sale (G-A3).
//! - sin flag reconocido ⇒ GUI Tauri (default).
//!
//! G-A1 sólo implementa el camino GUI. Los otros dos retornan error
//! explícito y exit 2 — los flags se cablean en los gates siguientes.

use std::process::ExitCode;

use cortex_brain_app::{run as run_app, Role};

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().collect();
    let role = Role::from_argv(&argv);

    match role {
        Role::App => {
            run_app();
            ExitCode::SUCCESS
        }
        Role::QueryClient => {
            eprintln!(
                "cortex-brain: --query todavía no implementado (llega en G-A9). \
                 Mientras tanto, abrí la GUI con `cortex-brain` (sin flags)."
            );
            ExitCode::from(2)
        }
        Role::ProjectsList => {
            eprintln!("cortex-brain: --projects-list todavía no implementado (llega en G-A3).");
            ExitCode::from(2)
        }
    }
}
