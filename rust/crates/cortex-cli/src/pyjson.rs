//! Serializador compatible con `json.dumps(obj, indent=2)` de CPython
//! (ensure_ascii=True con pares sustitutos >0xFFFF, separadores de indent,
//! `{}`/`[]` compactos, orden de inserción preservado vía árbol `PyVal`).
//!
//! ¿Por qué un árbol propio y no `serde_json::Value`? `Value::Object` es
//! `BTreeMap` (ordena claves) y activar `preserve_order` a nivel workspace
//! cambiaría el build unificado de crates ya gated. Patrón house: writer
//! PyVal manual (precedentes P12B-3/P12B-6).

#![forbid(unsafe_code)]

/// Número Python-safe: enteros y floats formateados como CPython repr.
#[derive(Debug, Clone)]
pub enum Num {
    Int(i64),
    Float(f64),
}

#[derive(Debug, Clone)]
pub enum PyVal {
    Null,
    Bool(bool),
    Num(Num),
    Str(String),
    Arr(Vec<PyVal>),
    Obj(Vec<(String, PyVal)>),
}

impl PyVal {
    pub fn s(v: impl Into<String>) -> Self {
        PyVal::Str(v.into())
    }
    pub fn obj(items: Vec<(&str, PyVal)>) -> Self {
        PyVal::Obj(items.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
    }
}

/// `json.dumps(value, indent=2)` (separadores `","`/`": "` con newline).
pub fn stdlib_dumps_indent2(v: &PyVal) -> String {
    let mut out = String::new();
    write(v, 0, &mut out);
    out
}

/// `json.dumps(value)` una-línea (separadores default ", " / ": ",
/// ensure_ascii=True) sobre un array PyVal.
pub fn stdlib_dumps_compact_array(items: &[PyVal]) -> String {
    let v = PyVal::Arr(items.to_vec());
    let mut out = String::new();
    write_compact(&v, &mut out);
    out
}

fn write_compact(v: &PyVal, out: &mut String) {
    match v {
        PyVal::Arr(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_compact(item, out);
            }
            out.push(']');
        }
        PyVal::Obj(items) => {
            out.push('{');
            for (i, (k, val)) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_escaped(k, out);
                out.push_str(": ");
                write_compact(val, out);
            }
            out.push('}');
        }
        other => write(other, 0, out),
    }
}

/// `model_dump_json(indent=2)` de pydantic v2: idéntico al stdlib writer
/// pero con UTF-8 crudo (sin ensure_ascii).
pub fn pydantic_dumps_indent2(v: &PyVal) -> String {
    let mut out = String::new();
    write_utf8(v, 0, &mut out);
    out
}

fn indent(n: usize) -> String {
    " ".repeat(n * 2)
}

fn write(v: &PyVal, level: usize, out: &mut String) {
    match v {
        PyVal::Null => out.push_str("null"),
        PyVal::Bool(true) => out.push_str("true"),
        PyVal::Bool(false) => out.push_str("false"),
        PyVal::Num(Num::Int(i)) => out.push_str(&i.to_string()),
        PyVal::Num(Num::Float(f)) => out.push_str(&format_float(*f)),
        PyVal::Str(s) => write_escaped(s, out),
        PyVal::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (i, item) in items.iter().enumerate() {
                out.push_str(&indent(level + 1));
                write(item, level + 1, out);
                if i + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&indent(level));
            out.push(']');
        }
        PyVal::Obj(items) => {
            if items.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (i, (k, val)) in items.iter().enumerate() {
                out.push_str(&indent(level + 1));
                write_escaped(k, out);
                out.push_str(": ");
                write(val, level + 1, out);
                if i + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&indent(level));
            out.push('}');
        }
    }
}

fn write_utf8(v: &PyVal, level: usize, out: &mut String) {
    match v {
        PyVal::Str(s) => {
            out.push('"');
            for c in s.chars() {
                match c {
                    '"' => out.push_str("\\\""),
                    '\\' => out.push_str("\\\\"),
                    '\n' => out.push_str("\\n"),
                    '\r' => out.push_str("\\r"),
                    '\t' => out.push_str("\\t"),
                    c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
                    c => out.push(c),
                }
            }
            out.push('"');
        }
        PyVal::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (i, item) in items.iter().enumerate() {
                out.push_str(&indent(level + 1));
                write_utf8(item, level + 1, out);
                if i + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&indent(level));
            out.push(']');
        }
        PyVal::Obj(items) => {
            if items.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (i, (k, val)) in items.iter().enumerate() {
                out.push_str(&indent(level + 1));
                write_escaped(k, out);
                out.push_str(": ");
                write_utf8(val, level + 1, out);
                if i + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&indent(level));
            out.push('}');
        }
        other => write(other, level, out),
    }
}

/// repr de float CPython para el rango de valores del dominio
/// (enteros conservan ".0"; sin exponentes extremos).
pub fn format_float(f: f64) -> String {
    if f.fract() == 0.0 && f.abs() < 1e16 {
        format!("{f:.1}")
    } else {
        format!("{f}")
    }
}

/// ensure_ascii=True de CPython: controles <0x20 como `\uXXXX`, todo
/// `>=0x7F` escapado (pares sustitutos para >0xFFFF), hex lowercase.
pub fn write_escaped(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0C}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c if (c as u32) <= 0x7E => out.push(c),
            c => {
                let code = c as u32;
                if code > 0xFFFF {
                    let v = code - 0x1_0000;
                    let hi = 0xD800 + (v >> 10);
                    let lo = 0xDC00 + (v & 0x3FF);
                    out.push_str(&format!("\\u{hi:04x}\\u{lo:04x}"));
                } else {
                    out.push_str(&format!("\\u{code:04x}"));
                }
            }
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escapes_ascii_and_surrogate_pairs() {
        let mut out = String::new();
        write_escaped("á😀", &mut out);
        assert_eq!(out, "\"\\u00e1\\ud83d\\ude00\"");
    }

    #[test]
    fn preserves_insertion_order_and_indent() {
        let v = PyVal::obj(vec![
            ("b", PyVal::s("1")),
            ("a", PyVal::Arr(vec![PyVal::Num(Num::Int(1))])),
            ("empty", PyVal::Obj(vec![])),
            ("f", PyVal::Num(Num::Float(1.0))),
        ]);
        assert_eq!(
            stdlib_dumps_indent2(&v),
            "{\n  \"b\": \"1\",\n  \"a\": [\n    1\n  ],\n  \"empty\": {},\n  \"f\": 1.0\n}"
        );
    }
}
