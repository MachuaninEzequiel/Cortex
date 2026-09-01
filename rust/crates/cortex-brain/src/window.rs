//! Ventana dedicada del brain (BRAIN-3): abre una terminal ejecutando
//! cortex-brain. Best-effort multiplataforma; si no hay terminal conocida
//! devuelve error accionable y el usuario corre el binario directo.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

/// Intenta lanzar `cmd` (argv completo) en una ventana de terminal nueva.
pub fn launch_window(cmd: &[String]) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    return try_macos(cmd);
    #[cfg(target_os = "windows")]
    return try_windows(cmd);
    #[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
    try_linux(cmd)
}

/// Busca un binario en PATH.
fn which(bin: &str) -> Option<PathBuf> {
    std::env::var("PATH")
        .ok()?
        .split(std::path::MAIN_SEPARATOR)
        .find_map(|dir| {
            let p = Path::new(dir).join(bin);
            p.is_file().then_some(p)
        })
}

#[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
fn try_linux(cmd: &[String]) -> Result<(), String> {
    // Todas las terminals soportadas usan la forma "<term> <flag> <argv…>".
    let candidatas: &[(&str, &str)] = &[
        ("gnome-terminal", "--"),
        ("konsole", "-e"),
        ("alacritty", "-e"),
        ("kitty", "-e"),
        ("xterm", "-e"),
    ];
    let mut ultimo_error = String::from("no encontré una terminal conocida");
    for (bin, flag) in candidatas {
        if which(bin).is_none() {
            continue;
        }
        let mut argv: Vec<String> = vec![(*bin).to_string(), (*flag).to_string()];
        argv.extend(cmd.iter().cloned());
        let resultado = Command::new(&argv[0])
            .args(&argv[1..])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn();
        match resultado {
            Ok(_) => return Ok(()),
            Err(e) => ultimo_error = format!("{bin}: {e}"),
        }
    }
    Err(ultimo_error)
}

#[cfg(target_os = "macos")]
fn try_macos(cmd: &[String]) -> Result<(), String> {
    let interior = cmd.join(" ").replace('"', "\\\"");
    let script = format!("tell application \"Terminal\" to do script \"{interior}\"");
    Command::new("osascript")
        .args(["-e", &script])
        .stdout(Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("osascript: {e}"))
}

#[cfg(target_os = "windows")]
fn try_windows(cmd: &[String]) -> Result<(), String> {
    Command::new("cmd")
        .arg("/C")
        .arg("start")
        .arg("cortex-brain")
        .args(cmd)
        .stdout(Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("start: {e}"))
}
