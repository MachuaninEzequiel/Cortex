//! Helpers de formato numérico estilo CPython compartidos por los handlers
//! (lección P12B-8: `format!("{}", 0.0_f64)` da `"0"` ≠ repr Python `"0.0"`).

/// `repr(f)` de Python 3.12: shortest round-trip con `.0` en enteros y
/// notación científica para extremos.
pub fn py_float_repr(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() {
            "-0.0".into()
        } else {
            "0.0".into()
        };
    }
    let abs = f.abs();
    // CPython usa repr shortest con cortes a 1e16/1e-5.
    if !(1e-4..1e16).contains(&abs) {
        let s = format!("{f:e}");
        // Rust: "1e20" → Python: "1e+20" (dos dígitos de exponente mínimo).
        let (mantissa, exp) = s.split_once('e').unwrap_or((s.as_str(), ""));
        let exp_val: i32 = exp.parse().unwrap_or(0);
        return format!(
            "{mantissa}e{}{:02}",
            if exp_val < 0 { "-" } else { "+" },
            exp_val.abs()
        );
    }
    if f.fract() == 0.0 {
        format!("{f:.1}")
    } else {
        format!("{f}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn floats_estilo_python() {
        assert_eq!(py_float_repr(0.0), "0.0");
        assert_eq!(py_float_repr(-3.0), "-3.0");
        assert_eq!(py_float_repr(2.5), "2.5");
        assert_eq!(py_float_repr(1e20), "1e+20");
    }
}
