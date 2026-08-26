//! Stub ruta 1 — lo rellena la MITAD A (paquete baja definitiva).
//! Devuelve `false` ⇒ passthrough al CLI Python (comportamiento idéntico
//! al actual hasta que la mitad A implemente `cortex remember`/`forget`).

pub fn run_remember(_argv: &[String]) -> bool {
    false
}

pub fn run_forget(_argv: &[String]) -> bool {
    false
}