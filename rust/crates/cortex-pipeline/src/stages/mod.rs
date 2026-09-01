//! Stages nativos. Test/Lint/Security ejecutan comandos locales (subprocess
//! con timeout por polling, como runtime_context); Documentation queda en
//! stub contractual hasta motor de memory nativo.

pub mod documentation;
pub mod lint;
pub mod security;
pub mod test;

/// Ejecuta `cmd` (split por espacios, como cmd.split() de Python).
/// Divergencia documentada: el timeout de subprocess.run se aplica
/// best-effort en el caller; aquí el spawn es bloqueante.
pub fn run_command(cmd: &str, _timeout_s: u64) -> (i32, String) {
    let mut parts = cmd.split_whitespace();
    let Some(program) = parts.next() else {
        return (-1, String::new());
    };
    match std::process::Command::new(program)
        .args(parts.collect::<Vec<_>>())
        .output()
    {
        Ok(out) => (
            out.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&out.stdout).into_owned(),
        ),
        Err(_) => (-1, String::new()),
    }
}
