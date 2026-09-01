//! Serializador JSON compatible byte-a-byte con `json.dumps` de Python y
//! `flask.jsonify` (Flask 3.x).
//!
//! Modos soportados (ambos verificados contra el runtime instalado):
//! - **COMPACT** (`jsonify`): `separators=(",", ":")`, `sort_keys=True`,
//!   `ensure_ascii=True`, `\n` final agregado por Flask.
//! - **PYTHON_DEFAULT** (`json.dumps(..., sort_keys=True)` del fingerprint):
//!   separadores `(", ", ": ")`.
//!
//! Escapes ensure_ascii: `"`, `\\`, `\n`, `\r`, `\t`, `\b`, `\f`, controles
//! `<0x20` como `\uXXXX`, todo `>=0x80` como `\uXXXX` (lowercase; pares
//! sustitutos para >0xFFFF) — idéntico a CPython.

#![forbid(unsafe_code)]

use serde_json::Value;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// jsonify: `(",", ":")`.
    Compact,
    /// json.dumps default: `(", ", ": ")`.
    PythonDefault,
}

pub fn dumps(value: &Value, mode: Mode, sort_keys: bool) -> String {
    let mut out = String::new();
    write_value(value, mode, sort_keys, &mut out);
    out
}

fn write_value(v: &Value, mode: Mode, sort_keys: bool, out: &mut String) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => {
            if n.is_f64() {
                // repr-shortest de CPython: los floats enteros conservan
                // ".0" ("1.0"); jamás colapsar a int. (Exponentes estilo
                // Python para extremos no ocurren en pesos del grafo.)
                let f = n.as_f64().unwrap_or(0.0);
                if f.fract() == 0.0 && f.abs() < 1e16 {
                    out.push_str(&format!("{f:.1}"));
                } else {
                    out.push_str(&format!("{f}"));
                }
            } else if let Some(i) = n.as_i64() {
                out.push_str(&i.to_string());
            } else if let Some(u) = n.as_u64() {
                out.push_str(&u.to_string());
            } else {
                out.push_str(&n.to_string());
            }
        }
        Value::String(s) => write_escaped(s, out),
        Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(match mode {
                        Mode::Compact => ",",
                        Mode::PythonDefault => ", ",
                    });
                }
                write_value(item, mode, sort_keys, out);
            }
            out.push(']');
        }
        Value::Object(map) => {
            out.push('{');
            let entries: Vec<(&String, &Value)> = map.iter().collect();
            let mut entries = entries;
            if sort_keys {
                entries.sort_by(|a, b| a.0.as_bytes().cmp(b.0.as_bytes()));
            }
            for (i, (k, val)) in entries.iter().enumerate() {
                if i > 0 {
                    out.push_str(match mode {
                        Mode::Compact => ",",
                        Mode::PythonDefault => ", ",
                    });
                }
                write_escaped(k, out);
                out.push(':');
                if mode == Mode::PythonDefault {
                    out.push(' ');
                }
                write_value(val, mode, sort_keys, out);
            }
            out.push('}');
        }
    }
}

fn write_escaped(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c if (c as u32) >= 0x80 => {
                let cu = c as u32;
                if cu > 0xFFFF {
                    // Par sustituto UTF-16 (CPython json/encoder.py).
                    let cu = cu - 0x10000;
                    let hi = 0xD800 + (cu >> 10);
                    let lo = 0xDC00 + (cu & 0x3FF);
                    out.push_str(&format!("\\u{hi:04x}\\u{lo:04x}"));
                } else {
                    out.push_str(&format!("\\u{cu:04x}"));
                }
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn compact_sorted_ascii() {
        let v = json!({"b": 1, "a": [1.5, null, "café ☕"], "nested": {"y": true, "x": "…"}});
        assert_eq!(
            dumps(&v, Mode::Compact, true),
            "{\"a\":[1.5,null,\"caf\\u00e9 \\u2615\"],\"b\":1,\"nested\":{\"x\":\"\\u2026\",\"y\":true}}"
        );
    }

    #[test]
    fn python_default_separators() {
        let v = json!({"a": 1, "b": "x"});
        assert_eq!(
            dumps(&v, Mode::PythonDefault, true),
            "{\"a\": 1, \"b\": \"x\"}"
        );
    }

    #[test]
    fn escapes_controles_y_surrogates() {
        let v = json!({"k": "a\u{01}\u{1F600}b"});
        assert_eq!(
            dumps(&v, Mode::Compact, false),
            "{\"k\":\"a\\u0001\\ud83d\\ude00b\"}"
        );
    }
}
