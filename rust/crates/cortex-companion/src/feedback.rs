//! Escritor de feedback explícito para el Companion (B7, G-B2d).
//!
//! Porteo del formato canónico del oráculo:
//! `cortex/feedback_loop.py::FeedbackCollector.add_feedback` (claves en
//! orden `type`, `memory_id`, `feedback_type`, `source`; `ts` lo completa
//! `FeedbackStore.append` al final vía `setdefault` — `json.dumps` default
//! con separadores `", "` / `": "`) + `cortex/feedback_store.py` (append
//! JSONL, rotación a `feedback.1.jsonl` al superar `max_bytes`, una sola
//! generación histórica).
//!
//! El escaper es `cortex_cli::pyjson::write_escaped` (ensure_ascii=True de
//! CPython). El oráculo escribe con ensure_ascii=False, pero todos los
//! valores que se escriben acá son ASCII (tipo fijo, `mem_<hex8>`, tipo de
//! feedback fijo, source fijo, ISO-8601) ⇒ ambas salidas coinciden byte a
//! byte para estos campos.
//!
//! Diferencias declaradas vs el oráculo (b7):
//! - **Idempotencia por hit** (exigida por el plan B7): antes de apendar se
//!   escanean `feedback.jsonl` y `feedback.1.jsonl` y, si YA existe un
//!   evento `explicit` para esa `memory_id` con `feedback_type` positivo
//!   (`"positive"` o `"useful"` — las dos variantes que cuenta
//!   `cortex-actions::signals`), no se duplica. El oráculo Python no dedupe;
//!   acá el doble clic del mouse haría inflar el score, así que el
//!   Companion dedupe en el lado del escritor (el archivo sigue siendo
//!   legible por `signals.rs` sin cambios).
//! - Fallo de escritura ⇒ `Err` propagado a la UI (patrón P6/P9), nunca
//!   silencio con warning (el logger de Python no aplica en la UI).

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use chrono::{SecondsFormat, Utc};
use cortex_cli::pyjson::write_escaped;

/// Nombre canónico del store (misma constante del oráculo).
pub const FEEDBACK_FILE: &str = "feedback.jsonl";
/// Generación histórica que conserva la rotación (oráculo: una sola).
pub const FEEDBACK_ROTATED: &str = "feedback.1.jsonl";
/// `max_bytes` default del FeedbackStore del oráculo (5 MB).
pub const MAX_BYTES_DEFAULT: u64 = 5 * 1024 * 1024;

/// Resultado de un intento de apendizado.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppendOutcome {
    /// Línea nueva escrita.
    Appended,
    /// El hit ya estaba marcado (positivo previo) ⇒ sin escritura.
    AlreadyMarked,
}

/// `json.dumps(evento)` del evento explícito, una línea, claves en el orden
/// del oráculo (type, memory_id, feedback_type, source, ts último).
pub fn dumps_event(
    event_type: &str,
    memory_id: &str,
    feedback_type: &str,
    source: &str,
    ts: &str,
) -> String {
    let mut out = String::from("{");
    out.push_str("\"type\": ");
    write_escaped(event_type, &mut out);
    out.push_str(", \"memory_id\": ");
    write_escaped(memory_id, &mut out);
    out.push_str(", \"feedback_type\": ");
    write_escaped(feedback_type, &mut out);
    out.push_str(", \"source\": ");
    write_escaped(source, &mut out);
    out.push_str(", \"ts\": ");
    write_escaped(ts, &mut out);
    out.push('}');
    out
}

/// `datetime.now(UTC).isoformat(timespec="milliseconds")` — offset `+00:00`
/// explícito (no `Z`), milisegundos, igual que el completado de ts del
/// FeedbackStore.
fn now_iso_ms() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Millis, false)
}

/// ¿Ya existe un evento positivo (`"positive"` o `"useful"`) para esa
/// memoria en el store vigente o rotado? Parseo tolerante (líneas corruptas
/// se ignoran, como `load()` del oráculo).
fn already_positive(dot_cortex: &Path, memory_id: &str) -> bool {
    for name in [FEEDBACK_FILE, FEEDBACK_ROTATED] {
        let text = match fs::read_to_string(dot_cortex.join(name)) {
            Ok(t) => t,
            Err(_) => continue,
        };
        for line in text.lines() {
            if line.trim().is_empty() {
                continue;
            }
            let Ok(ev) = serde_json::from_str::<serde_json::Value>(line) else {
                continue;
            };
            if ev.get("type").and_then(|v| v.as_str()) != Some("explicit") {
                continue;
            }
            if ev.get("memory_id").and_then(|v| v.as_str()) != Some(memory_id) {
                continue;
            }
            if matches!(
                ev.get("feedback_type").and_then(|v| v.as_str()),
                Some("positive") | Some("useful")
            ) {
                return true;
            }
        }
    }
    false
}

/// Rota si el archivo vigente superó `max_bytes` (oráculo: el check corre
/// ANTES del append; descarta la generación anterior y renombra).
fn rotate_if_needed(dot_cortex: &Path, max_bytes: u64) -> Result<(), String> {
    let path = dot_cortex.join(FEEDBACK_FILE);
    let Ok(meta) = fs::metadata(&path) else {
        return Ok(());
    };
    if meta.len() < max_bytes {
        return Ok(());
    }
    let rotado = dot_cortex.join(FEEDBACK_ROTATED);
    if rotado.exists() {
        fs::remove_file(&rotado).map_err(|e| format!("feedback rotate (unlink): {e}"))?;
    }
    fs::rename(&path, &rotado).map_err(|e| format!("feedback rotate (rename): {e}"))?;
    Ok(())
}

/// Apendiza un evento explícito positivo ("marcar útil") para `memory_id`
/// con `source` dado (la TUI usa "tui"; el Companion usa "companion" — el
/// lector `signals.rs` no filtra por source). Idempotente por hit.
pub fn append_useful(
    dot_cortex: &Path,
    source: &str,
    memory_id: &str,
    max_bytes: u64,
) -> Result<AppendOutcome, String> {
    if already_positive(dot_cortex, memory_id) {
        return Ok(AppendOutcome::AlreadyMarked);
    }
    fs::create_dir_all(dot_cortex).map_err(|e| format!("feedback dir: {e}"))?;
    rotate_if_needed(dot_cortex, max_bytes)?;
    let line = dumps_event("explicit", memory_id, "positive", source, &now_iso_ms());
    let mut fh = OpenOptions::new()
        .create(true)
        .append(true)
        .open(dot_cortex.join(FEEDBACK_FILE))
        .map_err(|e| format!("feedback open: {e}"))?;
    fh.write_all(line.as_bytes())
        .and_then(|()| fh.write_all(b"\n"))
        .and_then(|()| fh.flush())
        .and_then(|()| fh.sync_all())
        .map_err(|e| format!("feedback write: {e}"))?;
    Ok(AppendOutcome::Appended)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_ts_has_offset_and_millis() {
        let ts = now_iso_ms();
        assert!(ts.ends_with("+00:00"), "{ts}");
        // "YYYY-MM-DDTHH:MM:SS.mmm+00:00" ⇒ 10+1+8+1+3+6 = 29 chars — el largo
        // EXACTO de datetime.now(UTC).isoformat(timespec="milliseconds")
        // (verificado contra Python: 29). Con alto fijo de millis, el largo
        // es constante.
        assert_eq!(ts.chars().count(), 29, "{ts}");
        // Milisegundos SIEMPRE 3 dígitos (nunca ".9" ni ".90") como Python.
        assert!(ts[20..23].chars().all(|c| c.is_ascii_digit()), "{ts}");
    }
}
