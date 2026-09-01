//! Emisor JSON con orden de claves de inserción y repr de floats de
//! CPython — infraestructura de paridad para bundles `--json`.
//!
//! `json.dumps(obj, indent=2, ensure_ascii=False)` de Python:
//! - dicts/listas vacías → `{}` / `[]` inline;
//! - floats → repr shortest round-trip (".0" forzado en enteros-valuados);
//! - strings → escape JSON con unicode crudo.

pub enum Pj {
    Obj(Vec<(String, Pj)>),
    Arr(Vec<Pj>),
    Str(String),
    /// Valor crudo ya formateado (placeholders tipo `{{ROOT}}`).
    Raw(String),
    F64(f64),
    U64(u64),
    I64(i64),
    Bool(bool),
    Null,
}

impl Clone for Pj {
    fn clone(&self) -> Self {
        match self {
            Pj::Obj(f) => Pj::Obj(f.clone()),
            Pj::Arr(a) => Pj::Arr(a.clone()),
            Pj::Str(s) => Pj::Str(s.clone()),
            Pj::Raw(s) => Pj::Raw(s.clone()),
            Pj::F64(x) => Pj::F64(*x),
            Pj::U64(n) => Pj::U64(*n),
            Pj::I64(n) => Pj::I64(*n),
            Pj::Bool(b) => Pj::Bool(*b),
            Pj::Null => Pj::Null,
        }
    }
}

/// Redondeo compatible con round(x, n) de Python (half-even sobre el valor
/// binario; coincide con cualquier redondeo correcto salvo empates exactos).
pub fn redondear(x: f64, decimales: usize) -> f64 {
    let s = format!("{x:.decimales$}");
    s.parse().unwrap_or(x)
}

/// Espejo del repr de float de CPython.
pub fn py_float(x: f64) -> String {
    let s = format!("{x}");
    if s.contains('.') || s.contains('e') || s.contains('E') || x.is_nan() || x.is_infinite() {
        s
    } else {
        format!("{s}.0")
    }
}

/// Escape ASCII puro (`ensure_ascii=True`): no-ASCII ⇒ \\uXXXX con pares
/// sustitutos para astrales.
fn escape_ascii(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) <= 0x7E => out.push(c),
            c => {
                let cp = c as u32;
                if cp <= 0xFFFF {
                    out.push_str(&format!("\\u{cp:04x}"));
                } else {
                    let v = cp - 0x10000;
                    let hi = 0xD800 + (v >> 10);
                    let lo = 0xDC00 + (v & 0x3FF);
                    out.push_str(&format!("\\u{hi:04x}\\u{lo:04x}"));
                }
            }
        }
    }
    out.push('"');
    out
}

fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
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
    out
}

fn emit(v: &Pj, indent: usize, out: &mut String) {
    let pad = "  ".repeat(indent);
    let pad_inner = "  ".repeat(indent + 1);
    match v {
        Pj::Obj(fields) => {
            if fields.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (i, (k, val)) in fields.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                out.push_str(&escape(k));
                out.push_str(": ");
                emit(val, indent + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push('}');
        }
        Pj::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                emit(item, indent + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push(']');
        }
        Pj::Str(s) => out.push_str(&escape(s)),
        Pj::Raw(s) => out.push_str(s),
        Pj::F64(x) => out.push_str(&py_float(*x)),
        Pj::U64(n) => out.push_str(&n.to_string()),
        Pj::I64(n) => out.push_str(&n.to_string()),
        Pj::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Pj::Null => out.push_str("null"),
    }
}

/// Serializa como `json.dumps(…, indent=2, ensure_ascii=False)`.
pub fn dumps(v: &Pj) -> String {
    let mut s = String::new();
    emit(v, 0, &mut s);
    s
}

fn emit_leaf_compact(v: &Pj, out: &mut String) {
    match v {
        Pj::Str(s) => out.push_str(&escape(s)),
        Pj::Raw(s) => out.push_str(s),
        Pj::F64(x) => out.push_str(&py_float(*x)),
        Pj::U64(n) => out.push_str(&n.to_string()),
        Pj::I64(n) => out.push_str(&n.to_string()),
        Pj::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Pj::Null => out.push_str("null"),
        _ => unreachable!("contenedores manejados por emit_compact"),
    }
}

fn emit_compact(v: &Pj, out: &mut String) {
    match v {
        Pj::Obj(fields) => {
            if fields.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (i, (k, val)) in fields.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                out.push_str(&escape(k));
                out.push_str(": ");
                emit_compact(val, out);
            }
            out.push('}');
        }
        Pj::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                emit_compact(item, out);
            }
            out.push(']');
        }
        other => emit_leaf_compact(other, out),
    }
}

/// Serializa como `json.dumps(obj)` default (separadores ", " / ": ").
pub fn dumps_compact(v: &Pj) -> String {
    let mut s = String::new();
    emit_compact(v, &mut s);
    s
}

/// Serializa como `json.dumps(…, indent=2)` DEFAULT (ensure_ascii=True).
pub fn dumps_ascii(v: &Pj) -> String {
    // Reutiliza la estructura del emit indent-2 pero con escape_ascii.
    fn emit_a(v: &Pj, indent: usize, out: &mut String) {
        let pad = "  ".repeat(indent);
        let pad_inner = "  ".repeat(indent + 1);
        match v {
            Pj::Obj(fields) => {
                if fields.is_empty() {
                    out.push_str("{}");
                    return;
                }
                out.push('{');
                for (i, (k, val)) in fields.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    out.push('\n');
                    out.push_str(&pad_inner);
                    out.push_str(&escape_ascii(k));
                    out.push_str(": ");
                    emit_a(val, indent + 1, out);
                }
                out.push('\n');
                out.push_str(&pad);
                out.push('}');
            }
            Pj::Arr(items) => {
                if items.is_empty() {
                    out.push_str("[]");
                    return;
                }
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    out.push('\n');
                    out.push_str(&pad_inner);
                    emit_a(item, indent + 1, out);
                }
                out.push('\n');
                out.push_str(&pad);
                out.push(']');
            }
            Pj::Str(s) => out.push_str(&escape_ascii(s)),
            Pj::Raw(s) => out.push_str(s),
            Pj::F64(x) => out.push_str(&py_float(*x)),
            Pj::U64(n) => out.push_str(&n.to_string()),
            Pj::I64(n) => out.push_str(&n.to_string()),
            Pj::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
            Pj::Null => out.push_str("null"),
        }
    }
    let mut s = String::new();
    emit_a(v, 0, &mut s);
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn formato_python_indent2() {
        let v = Pj::Obj(vec![
            ("a".into(), Pj::U64(1)),
            (
                "b".into(),
                Pj::Arr(vec![Pj::Str("x".into()), Pj::Bool(true)]),
            ),
            ("c".into(), Pj::Obj(vec![])),
            ("d".into(), Pj::F64(8.0)),
            ("e".into(), Pj::Null),
        ]);
        let esperado = "{\n  \"a\": 1,\n  \"b\": [\n    \"x\",\n    true\n  ],\n  \"c\": {},\n  \"d\": 8.0,\n  \"e\": null\n}";
        assert_eq!(dumps(&v), esperado);
    }

    #[test]
    fn repr_floats_compatibles() {
        assert_eq!(py_float(8.0), "8.0");
        assert_eq!(py_float(6.25), "6.25");
        assert_eq!(py_float(66.7), "66.7");
        assert_eq!(py_float(0.1), "0.1");
    }

    #[test]
    fn escapes_json() {
        assert_eq!(escape("a\"b\\c\nd"), "\"a\\\"b\\\\c\\nd\"");
        assert_eq!(escape("español ✓"), "\"español ✓\"");
    }
}
