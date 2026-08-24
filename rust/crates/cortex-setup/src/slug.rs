//! Réplica de `cortex.documentation.common.slugify`.
//!
//! ```python
//! normalized = unicodedata.normalize("NFKD", value)
//! ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
//! cleaned = _SLUG_STRIP.sub("", ascii_value.strip().lower())
//! slug = _SLUG_SEP.sub("-", cleaned)          # [\s_]+ -> "-"
//! slug = _SLUG_COLLAPSE.sub("-", slug).strip("-")   # -+ -> "-", trim
//! ```
//!
//! `_SLUG_STRIP = [^\w\s-]` con flags UNICODE **sobre el string ya
//! ascii-ficado**, donde `\w` = [a-zA-Z0-9_].

use unicode_normalization::UnicodeNormalization;

pub fn slugify(value: &str) -> String {
    if value.is_empty() {
        return String::new();
    }
    // NFKD y descarte de lo no-ASCII (equivalente a encode("ascii","ignore")).
    let nfkd: String = value.nfkd().collect();
    let ascii: String = nfkd.chars().filter(|c| c.is_ascii()).collect();
    // strip().lower()
    let cleaned_input = ascii.trim().to_lowercase();
    // _SLUG_STRIP: quitar todo lo que no sea \w, \s o '-'
    let mut cleaned = String::with_capacity(cleaned_input.len());
    for ch in cleaned_input.chars() {
        let keep = ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' || is_python_space(ch);
        if keep {
            cleaned.push(ch);
        }
    }
    // _SLUG_SEP: [\s_]+ -> "-"
    let mut sep_out = String::with_capacity(cleaned.len());
    let mut in_sep = false;
    for ch in cleaned.chars() {
        if ch == '_' || is_python_space(ch) {
            if !in_sep {
                sep_out.push('-');
                in_sep = true;
            }
        } else {
            sep_out.push(ch);
            in_sep = false;
        }
    }
    // _SLUG_COLLAPSE: -+ -> "-" y trim de bordes.
    let mut out = String::with_capacity(sep_out.len());
    let mut prev_dash = false;
    for ch in sep_out.chars() {
        if ch == '-' {
            if !prev_dash {
                out.push('-');
            }
            prev_dash = true;
        } else {
            out.push(ch);
            prev_dash = false;
        }
    }
    out.trim_matches('-').to_string()
}

/// `\s` de Python (modo UNICODE sobre ASCII): espacio, \t, \n, \r, \x0b, \x0c.
fn is_python_space(c: char) -> bool {
    matches!(c, ' ' | '\t' | '\n' | '\r' | '\u{B}' | '\u{C}')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_python_examples() {
        // Docstring del original:
        assert_eq!(slugify("Hello World"), "hello-world");
        assert_eq!(slugify("Cafe & Sueño"), "cafe-sueno");
        assert_eq!(slugify(""), "");
    }

    #[test]
    fn accents_and_symbols() {
        assert_eq!(slugify("Decisión: usar tokens"), "decision-usar-tokens");
        assert_eq!(slugify("  ADR_001 -- base  "), "adr-001-base");
        assert_eq!(slugify("🧠 memoria"), "memoria");
        assert_eq!(slugify("a___b"), "a-b");
        assert_eq!(slugify("---"), "");
    }
}
