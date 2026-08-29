//! Copia al clipboard del terminal (OSC 52). Cero deps nuevas.
//!
//! El HUD nunca inyecta texto al pane del agente: el usuario pega.

use std::io::{self, Write};

pub fn copy(text: &str) -> io::Result<()> {
    let b64 = encode(text.as_bytes());
    let mut out = io::stdout();
    write!(out, "\x1b]52;c;{b64}\x07")?;
    out.flush()
}

fn encode(data: &[u8]) -> String {
    const T: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut s = String::with_capacity(data.len().div_ceil(3) * 4);
    let mut i = 0;
    while i + 3 <= data.len() {
        let n = ((data[i] as u32) << 16) | ((data[i + 1] as u32) << 8) | (data[i + 2] as u32);
        s.push(T[(n >> 18) as usize] as char);
        s.push(T[((n >> 12) & 63) as usize] as char);
        s.push(T[((n >> 6) & 63) as usize] as char);
        s.push(T[(n & 63) as usize] as char);
        i += 3;
    }
    match data.len() - i {
        1 => {
            let n = (data[i] as u32) << 16;
            s.push(T[(n >> 18) as usize] as char);
            s.push(T[((n >> 12) & 63) as usize] as char);
            s.push('=');
            s.push('=');
        }
        2 => {
            let n = ((data[i] as u32) << 16) | ((data[i + 1] as u32) << 8);
            s.push(T[(n >> 18) as usize] as char);
            s.push(T[((n >> 12) & 63) as usize] as char);
            s.push(T[((n >> 6) & 63) as usize] as char);
            s.push('=');
        }
        _ => {}
    }
    s
}

#[cfg(test)]
mod tests {
    use super::encode;

    #[test]
    fn base64_hello() {
        assert_eq!(encode(b"hello"), "aGVsbG8=");
    }
}
