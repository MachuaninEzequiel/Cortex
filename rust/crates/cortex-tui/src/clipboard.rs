//! Copia nativa al portapapeles mediante secuencia de escape OSC 52 (spec §7).

/// Copia texto al portapapeles del emulador de terminal usando OSC 52.
pub fn copy_to_clipboard(text: &str) {
    let encoded = base64::encode(text);
    print!("\x1b]52;c;{encoded}\x07");
    let _ = std::io::Write::flush(&mut std::io::stdout());
}
