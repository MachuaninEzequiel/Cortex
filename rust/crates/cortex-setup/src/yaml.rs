//! Dumper YAML byte-compatible con PyYAML.
//!
//! Réplica del pipeline `yaml.safe_dump(data, default_flow_style=False,
//! allow_unicode=True, sort_keys=False)` usado por
//! `cortex.documentation.common.yaml_dump_safe` para serializar el
//! frontmatter canónico.
//!
//! Se porteó 1:1 la lógica relevante de PyYAML 6.0.x (licencia MIT):
//! - `resolver.py`: resolución de tags implícitos de escalares planos.
//! - `representer.py`: representación segura (`None/bool/int/str/list/dict`)
//!   con `default_flow_style=False`.
//! - `serializer.py`: cálculo de `implicit`.
//! - `emitter.py`: `analyze_scalar`, `choose_scalar_style`,
//!   `check_simple_key`, `write_indent/write_indicator/
//!   write_{plain,single_quoted,double_quoted}`, incluido el plegado a
//!   `best_width = 80`.
//!
//! Divergencias documentadas (alcanzan sólo a entradas imposibles en el
//! frontmatter canónico):
//! - Claves no-string no son producidas por `model_dump(mode="json")`.
//! - Anclas/alias para nodos recursivos: el frontmatter canónico jamás es
//!   recursivo.
//! - Claves complejas (`? key`) se rechazan con panic: las claves canónicas
//!   son identificadores ASCII cortos; el chequeo es fiel y sólo dispararía
//!   ante una entrada fuera del dominio.

/// Valor YAML equivalente al AST que produce `model_dump(mode="json")`.
#[derive(Debug, Clone, PartialEq)]
pub enum Yaml {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Seq(Vec<Yaml>),
    /// Mapa con orden de inserción (sort_keys=False en Python).
    Map(Vec<(String, Yaml)>),
}

/// Réplica de `SafeRepresenter.represent_float`: `repr(data).lower()` de
/// CPython con el fix del '.0' antes de 'e'. CPython usa la representación
/// decimal corta (round-trip) con notación fija cuando -4 <= exp < 16 y
/// científica con exponente de al menos 2 dígitos fuera de ese rango.
pub fn python_repr_float(v: f64) -> String {
    if v.is_nan() {
        return ".nan".to_string();
    }
    if v.is_infinite() {
        return if v > 0.0 {
            ".inf".to_string()
        } else {
            "-.inf".to_string()
        };
    }
    // Dígitos significativos más cortos que hacen round-trip.
    let mut digits = String::new();
    let mut exp10: i32 = 0;
    for prec in 0usize..=16 {
        let candidate = format!("{:.*e}", prec, v);
        let parsed: f64 = candidate.parse().unwrap_or(f64::NAN);
        if parsed == v {
            // separar "d.ddddde±X"
            let (mant, e) = candidate.split_once('e').expect("format {:e}");
            digits = mant
                .replace(['-', '.'], "")
                .trim_start_matches('0')
                .to_string();
            if digits.is_empty() {
                digits = "0".to_string();
            }
            exp10 = e.parse().unwrap_or(0);
            break;
        }
    }
    if digits == "0" {
        return "0.0".to_string();
    }
    let neg = v.is_sign_negative();
    let sign = if neg { "-" } else { "" };
    let sci = |digits: &str, exp10: i32| -> String {
        let (head, tail) = digits.split_at(1);
        // CPython: mantisa siempre con parte fraccionaria ("1.0e-05").
        let mantissa = if tail.is_empty() {
            format!("{head}.0")
        } else {
            format!("{head}.{tail}")
        };
        format!(
            "{sign}{mantissa}e{}{:02}",
            if exp10 < 0 { '-' } else { '+' },
            exp10.abs()
        )
    };
    if (-4..16).contains(&exp10) {
        // Notación fija estilo CPython.
        let nd = digits.len() as i32;
        let mut out = String::new();
        if exp10 >= 0 {
            if (exp10 as usize) + 1 >= nd as usize {
                out.push_str(&digits);
                let zeros = exp10 + 1 - nd;
                for _ in 0..zeros {
                    out.push('0');
                }
                out.push_str(".0");
            } else {
                let point = (exp10 + 1) as usize;
                out.push_str(&digits[..point]);
                out.push('.');
                out.push_str(&digits[point..]);
            }
        } else {
            out.push_str("0.");
            for _ in 0..(-exp10 - 1) {
                out.push('0');
            }
            out.push_str(&digits);
        }
        format!("{sign}{out}")
    } else {
        sci(&digits, exp10)
    }
}

impl Yaml {
    pub fn str(s: impl Into<String>) -> Yaml {
        Yaml::Str(s.into())
    }
}

const BEST_INDENT: usize = 2;
const BEST_WIDTH: usize = 80;

// ---------------------------------------------------------------------------
// Resolver (resolver.py)
// ---------------------------------------------------------------------------

fn resolve_bool(v: &str) -> bool {
    matches!(
        v,
        "yes"
            | "Yes"
            | "YES"
            | "no"
            | "No"
            | "NO"
            | "true"
            | "True"
            | "TRUE"
            | "false"
            | "False"
            | "FALSE"
            | "on"
            | "On"
            | "ON"
            | "off"
            | "Off"
            | "OFF"
    )
}

fn resolve_null(v: &str) -> bool {
    // Patrón X-mode `^(?:~|null|Null|NULL| )$`: el espacio literal fuera de
    // la clase desaparece en modo verbose y deja una alternativa vacía que
    // también matchea "".
    matches!(v, "~" | "null" | "Null" | "NULL" | "")
}

fn resolve_merge(v: &str) -> bool {
    v == "<<"
}

fn resolve_value(v: &str) -> bool {
    v == "="
}

fn resolve_yaml_tag(v: &str) -> bool {
    // ^(?:!|&|\*)$
    v.len() == 1 && matches!(v, "!" | "&" | "*")
}

fn scan_while(bytes: &[u8], start: usize, pred: impl Fn(u8) -> bool) -> usize {
    let mut i = start;
    while i < bytes.len() && pred(bytes[i]) {
        i += 1;
    }
    i
}

/// `[-+]?0b[0-1_]+`
fn scan_int_bin(b: &[u8]) -> bool {
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    b.get(i) == Some(&b'0')
        && b.get(i + 1) == Some(&b'b')
        && b.len() > i + 2
        && scan_while(b, i + 2, |c| c == b'0' || c == b'1' || c == b'_') == b.len()
}

/// `[-+]?0[0-7_]+`
fn scan_int_oct(b: &[u8]) -> bool {
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    b.get(i) == Some(&b'0')
        && b.len() > i + 1
        && scan_while(b, i + 1, |c| (b'0'..=b'7').contains(&c) || c == b'_') == b.len()
}

/// `[-+]?(?:0|[1-9][0-9_]*)`
fn scan_int_dec(b: &[u8]) -> bool {
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    let rest = &b[i..];
    match rest.first() {
        None => false,
        Some(b'0') if rest.len() == 1 => true,
        Some(c) => {
            (b'1'..=b'9').contains(c)
                && scan_while(rest, 1, |c| c.is_ascii_digit() || c == b'_') == rest.len()
        }
    }
}

/// `[-+]?0x[0-9a-fA-F_]+`
fn scan_int_hex(b: &[u8]) -> bool {
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    b.get(i) == Some(&b'0')
        && b.get(i + 1) == Some(&b'x')
        && b.len() > i + 2
        && scan_while(b, i + 2, |c| c.is_ascii_hexdigit() || c == b'_') == b.len()
}

/// `[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+`
fn scan_int_sexagesimal(b: &[u8]) -> bool {
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    let rest = &b[i..];
    if rest.first().is_none_or(|c| !(b'1'..=b'9').contains(c)) {
        return false;
    }
    let mut j = scan_while(rest, 1, |c| c.is_ascii_digit() || c == b'_');
    let mut groups = 0;
    while j < rest.len() && rest[j] == b':' {
        let start = j + 1;
        let end = scan_while(rest, start, |c| c.is_ascii_digit());
        let span = &rest[start..end];
        // [0-5]?[0-9]
        let ok = match span.len() {
            1 => span[0].is_ascii_digit(),
            2 => (b'0'..=b'5').contains(&span[0]) && span[1].is_ascii_digit(),
            _ => false,
        };
        if !ok {
            return false;
        }
        groups += 1;
        j = end;
    }
    groups >= 1 && j == rest.len()
}

fn resolve_int(v: &str) -> bool {
    let b = v.as_bytes();
    scan_int_bin(b)
        || scan_int_oct(b)
        || scan_int_dec(b)
        || scan_int_hex(b)
        || scan_int_sexagesimal(b)
}

/// `[eE][-+][0-9]+` — devuelve el índice posterior o None si no matchea.
fn scan_exp(b: &[u8], i: usize) -> Option<usize> {
    if i < b.len() && (b[i] == b'e' || b[i] == b'E') {
        let j = i + 1;
        if j < b.len() && (b[j] == b'-' || b[j] == b'+') {
            let end = scan_while(b, j + 1, |c| c.is_ascii_digit());
            if end > j + 1 {
                return Some(end);
            }
        }
        return None;
    }
    Some(i)
}

fn resolve_float(v: &str) -> bool {
    let b = v.as_bytes();
    let mut i = 0;
    if matches!(b.first(), Some(b'-') | Some(b'+')) {
        i = 1;
    }
    let rest = &b[i..];

    // [-+]?\.(?:inf|Inf|INF)
    if rest == b".inf" || rest == b".Inf" || rest == b".INF" {
        return true;
    }
    // \.(?:nan|NaN|NAN) — sin prefijo de signo en la regex
    if i == 0 && (rest == b".nan" || rest == b".NaN" || rest == b".NAN") {
        return true;
    }

    // [-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?
    if rest.first().is_some_and(|c| c.is_ascii_digit()) {
        let int_end = scan_while(rest, 1, |c| c.is_ascii_digit() || c == b'_');
        if rest.get(int_end) == Some(&b'.') {
            let frac_end = scan_while(rest, int_end + 1, |c| c.is_ascii_digit() || c == b'_');
            if let Some(e) = scan_exp(rest, frac_end) {
                if e == rest.len() {
                    return true;
                }
            }
        }
    }

    // \.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
    if rest.first() == Some(&b'.') {
        let d = scan_while(rest, 1, |c| c.is_ascii_digit());
        if d > 1 {
            let mantissa_end = scan_while(rest, d, |c| c.is_ascii_digit() || c == b'_');
            if let Some(e) = scan_exp(rest, mantissa_end) {
                if e == rest.len() {
                    return true;
                }
            }
        }
    }

    // [-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9]*
    if rest.first().is_some_and(|c| c.is_ascii_digit()) {
        let mut j = scan_while(rest, 1, |c| c.is_ascii_digit() || c == b'_');
        let mut groups = 0;
        while j < rest.len() && rest[j] == b':' {
            let start = j + 1;
            let end = scan_while(rest, start, |c| c.is_ascii_digit());
            let span = &rest[start..end];
            let ok = match span.len() {
                1 => span[0].is_ascii_digit(),
                2 => (b'0'..=b'5').contains(&span[0]) && span[1].is_ascii_digit(),
                _ => false,
            };
            if !ok {
                break;
            }
            groups += 1;
            j = end;
        }
        if groups >= 1 && rest.get(j) == Some(&b'.') {
            let k = scan_while(rest, j + 1, |c| c.is_ascii_digit() || c == b'_');
            if k == rest.len() {
                return true;
            }
        }
    }

    false
}

/// Consume 1 o 2 dígitos desde `i`; devuelve índice posterior o 0.
fn one_two_digits(b: &[u8], i: usize) -> usize {
    if i < b.len() && b[i].is_ascii_digit() {
        if i + 1 < b.len() && b[i + 1].is_ascii_digit() {
            return i + 2;
        }
        return i + 1;
    }
    0
}

/// Resolver timestamp de PyYAML (modo verbose: los espacios literales fuera
/// de clases de caracteres no participan).
fn resolve_timestamp(v: &str) -> bool {
    let b = v.as_bytes();
    // Alternativa 1: [0-9]{4}-[0-9]{2}-[0-9]{2} $
    if b.len() == 10
        && b[0..4].iter().all(|c| c.is_ascii_digit())
        && b[4] == b'-'
        && b[5..7].iter().all(|c| c.is_ascii_digit())
        && b[7] == b'-'
        && b[8..10].iter().all(|c| c.is_ascii_digit())
    {
        return true;
    }
    // Alternativa 2: [0-9]{4}-[0-9]{1,2}-[0-9]{1,2} ([Tt]|[ \t]+)
    //                [0-9]{1,2}:[0-9]{2}:[0-9]{2} (\.[0-9]*)?
    //                ([ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?
    if b.len() < 10 || !b[0..4].iter().all(|c| c.is_ascii_digit()) || b[4] != b'-' {
        return false;
    }
    let m_end = one_two_digits(b, 5);
    if m_end == 0 || b.get(m_end) != Some(&b'-') {
        return false;
    }
    let d_end = one_two_digits(b, m_end + 1);
    if d_end == 0 {
        return false;
    }
    let sep = b[d_end];
    let mut i = if sep == b'T' || sep == b't' {
        d_end + 1
    } else if sep == b' ' || sep == b'\t' {
        scan_while(b, d_end, |c| c == b' ' || c == b'\t')
    } else {
        return false;
    };
    i = one_two_digits(b, i);
    if i == 0 || b.get(i) != Some(&b':') {
        return false;
    }
    let mm = one_two_digits(b, i + 1);
    if mm != i + 3 || b.get(mm) != Some(&b':') {
        return false;
    }
    let ss = one_two_digits(b, mm + 1);
    if ss != mm + 3 {
        return false;
    }
    let mut i = ss;
    if b.get(i) == Some(&b'.') {
        i = scan_while(b, i + 1, |c| c.is_ascii_digit());
    }
    if i < b.len() {
        let mut j = scan_while(b, i, |c| c == b' ' || c == b'\t');
        if j >= b.len() {
            return false;
        }
        if b[j] == b'Z' {
            j += 1;
        } else if b[j] == b'-' || b[j] == b'+' {
            j = one_two_digits(b, j + 1);
            if j == 0 {
                return false;
            }
            if b.get(j) == Some(&b':') {
                let m2 = one_two_digits(b, j + 1);
                if m2 != j + 3 {
                    return false;
                }
                j = m2;
            }
        } else {
            return false;
        }
        i = j;
    }
    i == b.len()
}

/// Tag detectado para un escalar plano (equivalente a
/// `resolve(ScalarNode, value, (True, False))`). Orden de registro en
/// PyYAML: bool, float, int, merge, null, timestamp, value, yaml. Los
/// patrones son disjuntos entre tags, así que probar en ese orden equivale
/// a la búsqueda por primer carácter.
pub fn detected_tag(value: &str) -> &'static str {
    const STR: &str = "tag:yaml.org,2002:str";
    if resolve_bool(value) {
        return "tag:yaml.org,2002:bool";
    }
    if resolve_float(value) {
        return "tag:yaml.org,2002:float";
    }
    if resolve_int(value) {
        return "tag:yaml.org,2002:int";
    }
    if resolve_merge(value) {
        return "tag:yaml.org,2002:merge";
    }
    if resolve_null(value) {
        return "tag:yaml.org,2002:null";
    }
    if resolve_timestamp(value) {
        return "tag:yaml.org,2002:timestamp";
    }
    if resolve_value(value) {
        return "tag:yaml.org,2002:value";
    }
    if resolve_yaml_tag(value) {
        return "tag:yaml.org,2002:yaml";
    }
    STR
}

// ---------------------------------------------------------------------------
// analyze_scalar (emitter.py)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
struct ScalarAnalysis {
    #[allow(dead_code)]
    scalar: String,
    empty: bool,
    multiline: bool,
    allow_flow_plain: bool,
    allow_block_plain: bool,
    allow_single_quoted: bool,
    #[allow(dead_code)]
    allow_double_quoted: bool,
    #[allow(dead_code)]
    allow_block: bool,
}

fn is_break(ch: char) -> bool {
    matches!(ch, '\n' | '\u{85}' | '\u{2028}' | '\u{2029}')
}

/// El conjunto `\0 \t\r\n\x85\u2028\u2029` para vecinos precedentes/siguientes.
fn neighbor_space(ch: char) -> bool {
    matches!(
        ch,
        '\0' | ' ' | '\t' | '\r' | '\n' | '\u{85}' | '\u{2028}' | '\u{2029}'
    )
}

fn analyze_scalar(scalar: &str, allow_unicode: bool) -> ScalarAnalysis {
    if scalar.is_empty() {
        return ScalarAnalysis {
            scalar: String::new(),
            empty: true,
            multiline: false,
            allow_flow_plain: false,
            allow_block_plain: true,
            allow_single_quoted: true,
            allow_double_quoted: true,
            allow_block: false,
        };
    }

    let mut block_indicators = false;
    let mut flow_indicators = false;
    let mut line_breaks = false;
    let mut special_characters = false;

    let mut leading_space = false;
    let mut leading_break = false;
    let mut trailing_space = false;
    let mut trailing_break = false;
    let mut break_space = false;
    let mut space_break = false;

    if scalar.starts_with("---") || scalar.starts_with("...") {
        block_indicators = true;
        flow_indicators = true;
    }

    let chars: Vec<char> = scalar.chars().collect();
    let len = chars.len();

    let mut preceded_by_whitespace = true;
    let mut followed_by_whitespace = len == 1 || neighbor_space(chars[1]);
    let mut previous_space = false;
    let mut previous_break = false;

    for (index, &ch) in chars.iter().enumerate() {
        if index == 0 {
            if "#,[]{}&*!|>'\"%@`".contains(ch) {
                flow_indicators = true;
                block_indicators = true;
            }
            if ch == '?' || ch == ':' {
                flow_indicators = true;
                if followed_by_whitespace {
                    block_indicators = true;
                }
            }
            if ch == '-' && followed_by_whitespace {
                flow_indicators = true;
                block_indicators = true;
            }
        } else {
            if ",?[]{}".contains(ch) {
                flow_indicators = true;
            }
            if ch == ':' {
                flow_indicators = true;
                if followed_by_whitespace {
                    block_indicators = true;
                }
            }
            if ch == '#' && preceded_by_whitespace {
                flow_indicators = true;
                block_indicators = true;
            }
        }

        if is_break(ch) {
            line_breaks = true;
        }
        if !(ch == '\n' || ('\u{20}'..='\u{7E}').contains(&ch)) {
            let unicode_ok = (ch == '\u{85}'
                || ('\u{A0}'..='\u{D7FF}').contains(&ch)
                || ('\u{E000}'..='\u{FFFD}').contains(&ch)
                || ('\u{10000}'..='\u{10FFFF}').contains(&ch))
                && ch != '\u{FEFF}';
            if !unicode_ok || !allow_unicode {
                special_characters = true;
            }
        }

        if ch == ' ' {
            if index == 0 {
                leading_space = true;
            }
            if index == len - 1 {
                trailing_space = true;
            }
            if previous_break {
                break_space = true;
            }
            previous_space = true;
            previous_break = false;
        } else if is_break(ch) {
            if index == 0 {
                leading_break = true;
            }
            if index == len - 1 {
                trailing_break = true;
            }
            if previous_space {
                space_break = true;
            }
            previous_space = false;
            previous_break = true;
        } else {
            previous_space = false;
            previous_break = false;
        }

        // Actualización de vecinos tal cual PyYAML (con index ya incrementado).
        preceded_by_whitespace = neighbor_space(ch);
        followed_by_whitespace = index + 2 >= len || neighbor_space(chars[index + 2]);
    }

    let mut allow_flow_plain = true;
    let mut allow_block_plain = true;
    let mut allow_single_quoted = true;
    let allow_double_quoted = true;
    let mut allow_block = true;

    if leading_space || leading_break || trailing_space || trailing_break {
        allow_flow_plain = false;
        allow_block_plain = false;
    }

    if trailing_space {
        allow_block = false;
    }

    if break_space {
        allow_flow_plain = false;
        allow_block_plain = false;
        allow_single_quoted = false;
    }

    if space_break || special_characters {
        allow_flow_plain = false;
        allow_block_plain = false;
        allow_single_quoted = false;
        allow_block = false;
    }

    if line_breaks {
        allow_flow_plain = false;
        allow_block_plain = false;
    }

    if flow_indicators {
        allow_flow_plain = false;
    }

    if block_indicators {
        allow_block_plain = false;
    }

    ScalarAnalysis {
        scalar: scalar.to_string(),
        empty: false,
        multiline: line_breaks,
        allow_flow_plain,
        allow_block_plain,
        allow_single_quoted,
        allow_double_quoted,
        allow_block,
    }
}

// ---------------------------------------------------------------------------
// Emisor (emitter.py — subset de estados que usa safe_dump)
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct Emitter {
    pub(crate) out: String,
    /// allow_unicode=True en el pipeline canónico (yaml_dump_safe); org.yaml
    /// usa safe_dump con allow_unicode=False.
    allow_unicode: bool,
    column: usize,
    whitespace: bool,
    indention: bool,
    indent: Option<usize>,
    indents: Vec<Option<usize>>,
    flow_level: usize,

    root_context: bool,
    sequence_context: bool,
    mapping_context: bool,
    simple_key_context: bool,
}

impl Default for Emitter {
    fn default() -> Self {
        Self::new()
    }
}

impl Emitter {
    pub fn new() -> Self {
        Emitter {
            out: String::new(),
            allow_unicode: true,
            column: 0,
            whitespace: true,
            indention: true,
            indent: None,
            indents: Vec::new(),
            flow_level: 0,
            root_context: false,
            sequence_context: false,
            mapping_context: false,
            simple_key_context: false,
        }
    }

    fn write_indicator(
        &mut self,
        indicator: &str,
        need_whitespace: bool,
        whitespace: bool,
        indention: bool,
    ) {
        let data = if self.whitespace || !need_whitespace {
            indicator.to_string()
        } else {
            format!(" {indicator}")
        };
        self.whitespace = whitespace;
        self.indention = self.indention && indention;
        self.column += data.chars().count();
        self.out.push_str(&data);
    }

    fn write_line_break(&mut self) {
        self.whitespace = true;
        self.indention = true;
        self.column = 0;
        self.out.push('\n');
    }

    fn write_indent(&mut self) {
        let indent = self.indent.unwrap_or(0);
        if !self.indention || self.column > indent || (self.column == indent && !self.whitespace) {
            self.write_line_break();
        }
        if self.column < indent {
            self.whitespace = true;
            let pad = " ".repeat(indent - self.column);
            self.column = indent;
            self.out.push_str(&pad);
        }
    }

    fn write_raw(&mut self, data: &str) {
        self.column += data.chars().count();
        self.out.push_str(data);
    }

    fn write_plain(&mut self, text: &str, split: bool) {
        if text.is_empty() {
            return;
        }
        if !self.whitespace {
            self.out.push(' ');
            self.column += 1;
        }
        self.whitespace = false;
        self.indention = false;
        let chars: Vec<char> = text.chars().collect();
        let len = chars.len();
        let mut spaces = false;
        let mut breaks = false;
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= len {
            let ch = chars.get(end).copied();
            if spaces {
                if ch != Some(' ') {
                    if start + 1 == end && self.column > BEST_WIDTH && split {
                        self.write_indent();
                        self.whitespace = false;
                        self.indention = false;
                    } else {
                        let data: String = chars[start..end].iter().collect();
                        self.write_raw(&data);
                    }
                    start = end;
                }
            } else if breaks {
                if !ch.map(is_break).unwrap_or(false) {
                    if chars[start] == '\n' {
                        self.write_line_break();
                    }
                    for &br in &chars[start..end] {
                        if br == '\n' {
                            self.write_line_break();
                        } else {
                            // best_line_break es siempre '\n'; un salto
                            // distinto (\x85, U+2028...) se emite crudo.
                            self.out.push(br);
                            self.column += 1;
                        }
                    }
                    self.write_indent();
                    self.whitespace = false;
                    self.indention = false;
                    start = end;
                }
            } else if ch.map(|c| c == ' ' || is_break(c)).unwrap_or(true) {
                let data: String = chars[start..end].iter().collect();
                self.write_raw(&data);
                start = end;
            }
            if let Some(c) = ch {
                spaces = c == ' ';
                breaks = is_break(c);
            }
            end += 1;
        }
    }

    fn write_single_quoted(&mut self, text: &str, split: bool) {
        self.write_indicator("'", true, false, false);
        let chars: Vec<char> = text.chars().collect();
        let len = chars.len();
        let mut spaces = false;
        let mut breaks = false;
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= len {
            let ch = chars.get(end).copied();
            if spaces {
                if ch != Some(' ') {
                    if start + 1 == end
                        && self.column > BEST_WIDTH
                        && split
                        && start != 0
                        && end != len
                    {
                        self.write_indent();
                    } else {
                        let data: String = chars[start..end].iter().collect();
                        self.write_raw(&data);
                    }
                    start = end;
                }
            } else if breaks {
                if !ch.map(is_break).unwrap_or(false) {
                    if chars[start] == '\n' {
                        self.write_line_break();
                    }
                    for &br in &chars[start..end] {
                        if br == '\n' {
                            self.write_line_break();
                        } else {
                            self.out.push(br);
                            self.column += 1;
                        }
                    }
                    self.write_indent();
                    start = end;
                }
            } else if ch
                .map(|c| c == ' ' || is_break(c) || c == '\'')
                .unwrap_or(true)
                && start < end
            {
                let data: String = chars[start..end].iter().collect();
                self.write_raw(&data);
                start = end;
            }
            if ch == Some('\'') {
                self.out.push_str("''");
                self.column += 2;
                start = end + 1;
            }
            if let Some(c) = ch {
                spaces = c == ' ';
                breaks = is_break(c);
            }
            end += 1;
        }
        self.write_indicator("'", false, false, false);
    }

    fn escape_replacement(ch: char) -> Option<&'static str> {
        Some(match ch {
            '\0' => "0",
            '\u{7}' => "a",
            '\u{8}' => "b",
            '\t' => "t",
            '\n' => "n",
            '\u{B}' => "v",
            '\u{C}' => "f",
            '\r' => "r",
            '\u{1B}' => "e",
            '"' => "\"",
            '\\' => "\\",
            '\u{85}' => "N",
            '\u{A0}' => "_",
            '\u{2028}' => "L",
            '\u{2029}' => "P",
            _ => return None,
        })
    }

    fn write_double_quoted(&mut self, text: &str, split: bool) {
        self.write_indicator("\"", true, false, false);
        let chars: Vec<char> = text.chars().collect();
        let len = chars.len();
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= len {
            let ch = chars.get(end).copied();
            // Printable según write_double_quoted con allow_unicode=True:
            //   \x20..\x7E  ó  (\xA0..\uD7FF ó \uE000..\uFFFD).
            // Fuera de eso (y los escapes explícitos) se escapa.
            let needs_escape = ch
                .map(|c| {
                    c == '"'
                        || c == '\\'
                        || is_break(c)
                        || c == '\u{FEFF}'
                        || !(('\u{20}'..='\u{7E}').contains(&c)
                            || (self.allow_unicode
                                && (('\u{A0}'..='\u{D7FF}').contains(&c)
                                    || ('\u{E000}'..='\u{FFFD}').contains(&c))))
                })
                .unwrap_or(true);
            if needs_escape {
                if start < end {
                    let data: String = chars[start..end].iter().collect();
                    self.write_raw(&data);
                    start = end;
                }
                if let Some(c) = ch {
                    let data = if let Some(rep) = Self::escape_replacement(c) {
                        format!("\\{rep}")
                    } else if (c as u32) <= 0xFF {
                        format!("\\x{:02X}", c as u32)
                    } else if (c as u32) <= 0xFFFF {
                        format!("\\u{:04X}", c as u32)
                    } else {
                        format!("\\U{:08X}", c as u32)
                    };
                    self.write_raw(&data);
                    start = end + 1;
                }
            }
            // Condición de plegado de PyYAML: 0 < end < len(text)-1. El
            // término (end-start) puede ser negativo tras un escape
            // (start = end+1); en Python eso mata el fold salvo columna
            // enorme, y el slice text[start:end] daría vacío.
            let span_diff = end as isize - start as isize;
            if end > 0
                && end + 1 < len
                && (ch == Some(' ') || start >= end)
                && self.column as isize + span_diff > BEST_WIDTH as isize
                && split
            {
                let mut data: String = if start < end {
                    chars[start..end].iter().collect()
                } else {
                    String::new()
                };
                data.push('\\');
                if start < end {
                    start = end;
                }
                self.write_raw(&data);
                self.write_indent();
                self.whitespace = false;
                self.indention = false;
                if chars[start] == ' ' {
                    self.out.push('\\');
                    self.column += 1;
                }
            }
            end += 1;
        }
        self.write_indicator("\"", false, false, false);
    }

    /// Longitud del tag preparado (`!!str`, `!!int`, ...) para
    /// `check_simple_key`, vía DEFAULT_TAG_PREFIXES {'tag:yaml.org,2002:' ->
    /// '!!'}.
    fn prepared_tag_len(tag: &str) -> usize {
        tag.strip_prefix("tag:yaml.org,2002:")
            .map(|suffix| 2 + suffix.len())
            .unwrap_or(tag.len())
    }

    fn scalar_repr(node_scalar: &Yaml) -> (String, &'static str) {
        match node_scalar {
            Yaml::Null => ("null".into(), "tag:yaml.org,2002:null"),
            Yaml::Bool(b) => (
                if *b { "true".into() } else { "false".into() },
                "tag:yaml.org,2002:bool",
            ),
            Yaml::Int(i) => (i.to_string(), "tag:yaml.org,2002:int"),
            Yaml::Float(f) => (python_repr_float(*f), "tag:yaml.org,2002:float"),
            Yaml::Str(s) => (s.clone(), "tag:yaml.org,2002:str"),
            _ => unreachable!("scalar_repr llamado con colección"),
        }
    }

    fn check_simple_key(&self, node: &Yaml) -> bool {
        match node {
            s @ (Yaml::Str(_) | Yaml::Int(_) | Yaml::Float(_) | Yaml::Bool(_) | Yaml::Null) => {
                let (repr, tag) = Self::scalar_repr(s);
                let analysis = analyze_scalar(&repr, self.allow_unicode);
                let length = Self::prepared_tag_len(tag) + repr.chars().count();
                length < 128 && !analysis.empty && !analysis.multiline
            }
            Yaml::Seq(items) => items.is_empty(),
            Yaml::Map(entries) => entries.is_empty(),
        }
    }

    fn increase_indent(&mut self, flow: bool, indentless: bool) {
        self.indents.push(self.indent);
        match self.indent {
            None => self.indent = Some(if flow { BEST_INDENT } else { 0 }),
            Some(cur) if !indentless => self.indent = Some(cur + BEST_INDENT),
            _ => {}
        }
    }

    fn pop_indent(&mut self) {
        self.indent = self.indents.pop().flatten();
    }

    /// Equivalente a `expect_node(...)`: fija los contextos (que el
    /// CALLER determina según posición, igual que en PyYAML) y despacha.
    fn expect_node(
        &mut self,
        node: &Yaml,
        root: bool,
        sequence: bool,
        mapping: bool,
        simple_key: bool,
    ) {
        let saved = (
            self.root_context,
            self.sequence_context,
            self.mapping_context,
            self.simple_key_context,
        );
        self.root_context = root;
        self.sequence_context = sequence;
        self.mapping_context = mapping;
        self.simple_key_context = simple_key;

        match node {
            Yaml::Seq(items) => {
                if self.flow_level > 0 || items.is_empty() {
                    self.emit_flow_sequence(items);
                } else {
                    // expect_block_sequence
                    let indentless = self.mapping_context && !self.indention;
                    self.increase_indent(false, indentless);
                    for item in items {
                        self.write_indent();
                        self.write_indicator("-", true, false, true);
                        self.expect_node(item, false, true, false, false);
                    }
                    self.pop_indent();
                }
            }
            Yaml::Map(entries) => {
                if self.flow_level > 0 || entries.is_empty() {
                    self.emit_flow_mapping(entries);
                } else {
                    // expect_block_mapping
                    self.increase_indent(false, false);
                    for (k, v) in entries {
                        self.write_indent();
                        let key_node = Yaml::Str(k.clone());
                        if self.check_simple_key(&key_node) {
                            // expect_node(mapping=True, simple_key=True)
                            self.expect_node(&key_node, false, false, true, true);
                            self.write_indicator(":", false, false, false);
                            // expect_block_mapping_value vía expect_node(mapping=True)
                            self.expect_node(v, false, false, true, false);
                        } else {
                            // expect_block_mapping_value (clave compleja):
                            // '? key' + indent + ': valor'.
                            self.write_indicator("?", true, false, true);
                            self.expect_node(&key_node, false, false, true, false);
                            self.write_indent();
                            self.write_indicator(":", true, false, true);
                            self.expect_node(v, false, false, true, false);
                        }
                    }
                    self.pop_indent();
                }
            }
            scalar => {
                // expect_scalar
                let (repr, tag) = Self::scalar_repr(scalar);
                self.increase_indent(true, false);
                self.process_scalar(&repr, tag);
                self.pop_indent();
            }
        }

        (
            self.root_context,
            self.sequence_context,
            self.mapping_context,
            self.simple_key_context,
        ) = saved;
    }

    fn process_scalar(&mut self, repr: &str, tag: &'static str) {
        let analysis = analyze_scalar(repr, self.allow_unicode);
        // implicit[0] = (node.tag == detected_tag): un Int cuyo repr es "1"
        // es plain; un Str "1" (detectado como !!int) debe citarse.
        let implicit0 = tag == detected_tag(repr);

        // choose_scalar_style con event.style=None:
        //   '' si implicit[0] y análisis lo permite; si no '\''; si no '"'.
        let plain_ok = implicit0
            && !(self.simple_key_context && (analysis.empty || analysis.multiline))
            && ((self.flow_level > 0 && analysis.allow_flow_plain)
                || (self.flow_level == 0 && analysis.allow_block_plain));

        let split = !self.simple_key_context;
        if plain_ok {
            self.write_plain(repr, split);
        } else if analysis.allow_single_quoted && !(self.simple_key_context && analysis.multiline) {
            self.write_single_quoted(repr, split);
        } else {
            self.write_double_quoted(repr, split);
        }
    }

    fn emit_flow_sequence(&mut self, items: &[Yaml]) {
        self.write_indicator("[", true, true, false);
        self.flow_level += 1;
        self.increase_indent(true, false);
        for (i, item) in items.iter().enumerate() {
            if i > 0 {
                self.write_indicator(",", false, false, false);
            }
            if self.column > BEST_WIDTH {
                self.write_indent();
            }
            self.expect_node(item, false, true, false, false);
        }
        self.pop_indent();
        self.flow_level -= 1;
        self.write_indicator("]", false, false, false);
    }

    fn emit_flow_mapping(&mut self, entries: &[(String, Yaml)]) {
        self.write_indicator("{", true, true, false);
        self.flow_level += 1;
        self.increase_indent(true, false);
        for (i, (k, v)) in entries.iter().enumerate() {
            if i > 0 {
                self.write_indicator(",", false, false, false);
            }
            if self.column > BEST_WIDTH {
                self.write_indent();
            }
            let key_node = Yaml::Str(k.clone());
            if self.check_simple_key(&key_node) {
                self.expect_node(&key_node, false, false, true, true);
                self.write_indicator(":", false, false, false);
                self.expect_node(v, false, false, true, false);
            } else {
                self.write_indicator("?", true, false, false);
                self.expect_node(&key_node, false, false, true, false);
                self.write_indicator(":", true, false, false);
                self.expect_node(v, false, false, true, false);
            }
        }
        self.pop_indent();
        self.flow_level -= 1;
        self.write_indicator("}", false, false, false);
    }
}

/// Serializa `value` exactamente como
/// `yaml.safe_dump(value, default_flow_style=False, allow_unicode=True,
/// sort_keys=False)` (incluye el `\n` final del documento).
pub fn dump(value: &Yaml) -> String {
    dump_with(value, true)
}

/// Variante con `allow_unicode` explícito (org.yaml usa False).
pub fn dump_with(value: &Yaml, allow_unicode: bool) -> String {
    let mut em = Emitter::new();
    em.allow_unicode = allow_unicode;
    // expect_document_root → expect_node(root=True)
    em.expect_node(value, true, false, false, false);
    // expect_document_end → write_indent() con indent None.
    em.indent = None;
    em.write_indent();
    em.out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(v: &str) -> Yaml {
        Yaml::Str(v.into())
    }

    #[test]
    fn basic_frontmatter_shape() {
        let doc = Yaml::Map(vec![
            ("schema_version".into(), Yaml::Int(1)),
            ("doc_type".into(), s("adr")),
            ("title".into(), s("Usar tokens vs sesiones")),
            ("created_at".into(), s("2026-08-24T12:34:56.789012Z")),
            ("tags".into(), Yaml::Seq(vec![s("auth"), s("latencia")])),
            ("status".into(), s("accepted")),
            ("links".into(), Yaml::Seq(vec![])),
            ("vault_scope".into(), s("local")),
            ("fingerprint".into(), s(&"a".repeat(64))),
        ]);
        let out = dump(&doc);
        let expected = "schema_version: 1\ndoc_type: adr\ntitle: Usar tokens vs sesiones\ncreated_at: '2026-08-24T12:34:56.789012Z'\ntags:\n- auth\n- latencia\nstatus: accepted\nlinks: []\nvault_scope: local\nfingerprint: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n";
        assert_eq!(out, expected);
    }

    #[test]
    fn tricky_strings() {
        let doc = Yaml::Map(vec![
            ("unicode".into(), s("Café & Sueño: decisión ✓")),
            ("colon".into(), s("key: valor")),
            (
                "long".into(),
                s("una frase muy larga que supera los ochenta caracteres de ancho para probar el plegado de líneas del emisor"),
            ),
            ("hash".into(), s("valor con # hash")),
            ("num_like".into(), s("42")),
            ("bool_like".into(), s("true")),
            ("empty".into(), s("")),
            ("multiline".into(), s("linea1\nlinea2\n")),
            ("tab".into(), s("col\ttab")),
        ]);
        let out = dump(&doc);
        assert!(out.contains("'Café & Sueño: decisión ✓'"));
        assert!(out.contains("'key: valor'"));
        assert!(out.contains(
            "long: una frase muy larga que supera los ochenta caracteres de ancho para probar el\n  plegado"
        ));
        assert!(out.contains("'valor con # hash'"));
        assert!(out.contains("'42'"));
        assert!(out.contains("'true'"));
        assert!(out.contains("empty: ''"));
        assert!(out.contains("\"col\\ttab\""));
        let doc2 = Yaml::Map(vec![("yes".into(), s("yes"))]);
        assert_eq!(dump(&doc2), "'yes': 'yes'\n");
    }

    #[test]
    fn nested_collections() {
        let doc = Yaml::Map(vec![
            (
                "hooks".into(),
                Yaml::Seq(vec![Yaml::Map(vec![
                    ("name".into(), s("build")),
                    ("required".into(), Yaml::Bool(true)),
                    ("timeout_seconds".into(), Yaml::Int(90)),
                ])]),
            ),
            ("empty_map".into(), Yaml::Map(vec![])),
            ("nested_list".into(), Yaml::Seq(vec![Yaml::Seq(vec![])])),
            ("none_v".into(), Yaml::Null),
        ]);
        let out = dump(&doc);
        let expected = "hooks:\n- name: build\n  required: true\n  timeout_seconds: 90\nempty_map: {}\nnested_list:\n- []\nnone_v: null\n";
        assert_eq!(out, expected);
    }

    #[test]
    fn resolver_edge_cases() {
        assert_eq!(detected_tag(""), "tag:yaml.org,2002:null");
        assert_eq!(detected_tag("42"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("true"), "tag:yaml.org,2002:bool");
        assert_eq!(detected_tag("~"), "tag:yaml.org,2002:null");
        assert_eq!(
            detected_tag("2026-08-24T12:34:56.789012Z"),
            "tag:yaml.org,2002:timestamp"
        );
        assert_eq!(detected_tag("2026-08-24"), "tag:yaml.org,2002:timestamp");
        assert_eq!(detected_tag("hello world"), "tag:yaml.org,2002:str");
        assert_eq!(detected_tag("it's ok"), "tag:yaml.org,2002:str");
        assert_eq!(detected_tag("https://x.y/z?a=1"), "tag:yaml.org,2002:str");
        assert_eq!(detected_tag("="), "tag:yaml.org,2002:value");
        assert_eq!(detected_tag("<<"), "tag:yaml.org,2002:merge");
        assert_eq!(detected_tag("!"), "tag:yaml.org,2002:yaml");
        assert_eq!(detected_tag("3.14"), "tag:yaml.org,2002:float");
        assert_eq!(detected_tag(".inf"), "tag:yaml.org,2002:float");
        assert_eq!(detected_tag("1:30"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("0x1A"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("0b101"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("010"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("1_000"), "tag:yaml.org,2002:int");
        assert_eq!(detected_tag("v1.2"), "tag:yaml.org,2002:str");
        assert_eq!(detected_tag("- parece lista"), "tag:yaml.org,2002:str");
        assert_eq!(detected_tag("?que"), "tag:yaml.org,2002:str");
    }

    #[test]
    fn multiline_in_seq_item_matches_pyyaml() {
        // Caso capturado del oráculo Python con yaml_dump_safe
        // (sort_keys=False ⇒ se conserva el orden de inserción):
        //   [{"name": "n\nm", "cmd": "x"}] =>
        //   "hooks:\n- name: 'n\n\n    m'\n  cmd: x\n"
        let doc = Yaml::Map(vec![(
            "hooks".into(),
            Yaml::Seq(vec![Yaml::Map(vec![
                ("name".into(), s("n\nm")),
                ("cmd".into(), s("x")),
            ])]),
        )]);
        assert_eq!(dump(&doc), "hooks:\n- name: 'n\n\n    m'\n  cmd: x\n");
    }
}
