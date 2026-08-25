//! Emisor YAML compatible **byte-a-byte** con `yaml.safe_dump` de PyYAML.
//!
//! ¿Por qué no `serde_yaml::to_string`? Porque serde_yaml NO replica el
//! formato de PyYAML y el contrato del programa es paridad de bytes:
//!
//! 1. **Folding a 80 columnas**: PyYAML parte scalars largos en espacios
//!    (`best_width=80`) con continuación indentada; serde_yaml nunca parte.
//! 2. **Quoting**: PyYAML cita con `'...'` los strings que parecen
//!    bool/int/null/timestamp o contienen indicadores (`": "`, `" #"`,
//!    leading `-`…); serde_yaml aplica reglas distintas.
//! 3. **Sequences indentless**: `key:\n- item` (PyYAML default) vs
//!    `key:\n  - item` (serde_yaml).
//! 4. **Indent de escalares**: PyYAML hace `increase_indent(flow=True)`
//!    alrededor de cada escalar ⇒ las continuaciones caen en
//!    `indent_padre + 2` (verificado contra la fuente de PyYAML 6.x,
//!    `yaml/emitter.py`: `expect_scalar`, `write_plain`,
//!    `write_single_quoted`, `choose_scalar_style`, `analyze_scalar` y el
//!    resolver implícito `yaml/resolver.py`).
//!
//! Este módulo porta fielmente el subconjunto necesario del emisor de
//! PyYAML (estilos plain/single/double + folding + análisis de escalares +
//! resolución implícita de tags). El árbol de entrada es [`Node`]; la
//! salida es `String` terminada en un único `\n` (igual que `safe_dump`).

#![forbid(unsafe_code)]

// ── árbol de entrada ────────────────────────────────────────────────────────

/// Nodo YAML serializable con formato PyYAML.
#[derive(Debug, Clone, PartialEq)]
pub enum Node {
    Str(String),
    Bool(bool),
    Int(i64),
    Seq(Vec<Node>),
    Map(Vec<(String, Node)>),
}

impl Node {
    pub fn s(v: impl Into<String>) -> Node {
        Node::Str(v.into())
    }
}

/// Análisis de un escalar (espejo de `ScalarAnalysis`/`analyze_scalar`).
struct Analysis {
    empty: bool,
    multiline: bool,
    allow_block_plain: bool,
    allow_single_quoted: bool,
}

fn is_break(ch: char) -> bool {
    matches!(ch, '\n' | '\u{85}' | '\u{2028}' | '\u{2029}')
}

fn is_space_or_break(ch: char) -> bool {
    ch == ' ' || is_break(ch)
}

const WS_CHARS: &[char] = &[
    '\0', ' ', '\t', '\r', '\n', '\u{85}', '\u{2028}', '\u{2029}',
];

fn analyze_scalar(scalar: &str) -> Analysis {
    if scalar.is_empty() {
        return Analysis {
            empty: true,
            multiline: false,
            allow_block_plain: true,
            allow_single_quoted: true,
        };
    }

    let mut block_indicators = false;
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
    }

    let chars: Vec<char> = scalar.chars().collect();
    let n = chars.len();
    // First character or preceded by a whitespace.
    let mut preceded_by_whitespace = true;
    // Last character or followed by a whitespace.
    let mut followed_by_whitespace = n == 1 || WS_CHARS.contains(&chars[1]);
    let mut previous_space = false;
    let mut previous_break = false;

    for (index, &ch) in chars.iter().enumerate() {
        if index == 0 {
            if "#,[]{}&*!|>'\"%@`".contains(ch) {
                block_indicators = true;
            }
            if (ch == '?' || ch == ':') && followed_by_whitespace {
                block_indicators = true;
            }
            if ch == '-' && followed_by_whitespace {
                block_indicators = true;
            }
        } else {
            if ch == ':' && followed_by_whitespace {
                block_indicators = true;
            }
            if ch == '#' && preceded_by_whitespace {
                block_indicators = true;
            }
        }

        if is_break(ch) {
            line_breaks = true;
        }
        let cu = ch as u32;
        if !(ch == '\n' || ('\u{20}'..='\u{7E}').contains(&ch)) {
            let unicode_ok = (cu == 0x85
                || (0xA0..=0xD7FF).contains(&cu)
                || (0xE000..=0xFFFD).contains(&cu)
                || (0x10000..0x10FFFF).contains(&cu))
                && cu != 0xFEFF;
            if !unicode_ok {
                // allow_unicode=True ⇒ unicode OK; el resto es especial.
                special_characters = true;
            }
        }

        if ch == ' ' {
            if index == 0 {
                leading_space = true;
            }
            if index == n - 1 {
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
            if index == n - 1 {
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

        preceded_by_whitespace = WS_CHARS.contains(&ch);
        // Espejo EXACTO de PyYAML: al cerrar la iteración de `index`,
        // followed apunta a chars[index+2] para la siguiente vuelta.
        let next_index = index + 2;
        followed_by_whitespace = next_index >= n || WS_CHARS.contains(&chars[next_index]);
    }

    let mut a = Analysis {
        empty: false,
        multiline: line_breaks,
        allow_block_plain: true,
        allow_single_quoted: true,
    };

    if leading_space || leading_break || trailing_space || trailing_break {
        a.allow_block_plain = false;
    }
    if break_space {
        a.allow_block_plain = false;
        a.allow_single_quoted = false;
    }
    if space_break || special_characters {
        a.allow_block_plain = false;
        a.allow_single_quoted = false;
    }
    if line_breaks {
        a.allow_block_plain = false;
    }
    if block_indicators {
        a.allow_block_plain = false;
    }
    a
}

// ── resolución implícita de tags (yaml/resolver.py) ─────────────────────────

/// True si el string resolvería implícitamente a un tag NO-str (null, bool,
/// int, float, timestamp, merge, value) ⇒ PyYAML NO puede emitirlo plain.
pub fn implicitly_non_str(s: &str) -> bool {
    if s.is_empty() || s == "~" || s == "null" || s == "Null" || s == "NULL" {
        return true; // null
    }
    if s == "<<" || s == "=" {
        return true; // merge / value
    }
    if matches!(
        s,
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
    ) {
        return true; // bool
    }
    if matches_int(s) || matches_float(s) || matches_timestamp(s) {
        return true;
    }
    false
}

fn strip_sign(body: &str) -> &str {
    body.strip_prefix(['-', '+']).unwrap_or(body)
}

fn all_in(body: &str, pred: impl Fn(char) -> bool + Copy) -> bool {
    !body.is_empty() && body.chars().all(pred)
}

fn dec_or_underscore(c: char) -> bool {
    c.is_ascii_digit() || c == '_'
}

fn matches_int(s: &str) -> bool {
    let b = strip_sign(s);
    // [-+]?0b[0-1_]+
    if let Some(rest) = b.strip_prefix("0b") {
        if all_in(rest, |c| c == '0' || c == '1' || c == '_') {
            return true;
        }
    }
    // [-+]?0x[0-9a-fA-F_]+
    if let Some(rest) = b.strip_prefix("0x") {
        if all_in(rest, |c| c.is_ascii_hexdigit() || c == '_') {
            return true;
        }
    }
    // [-+]?0[0-7_]+  (al menos un dígito tras el 0 inicial)
    if b.len() >= 2
        && b.starts_with('0')
        && all_in(&b[1..], |c| ('0'..='7').contains(&c) || c == '_')
    {
        return true;
    }
    let first = match b.chars().next() {
        Some(f) => f,
        None => return false,
    };
    // [-+]?(?:0|[1-9][0-9_]*)
    if b == "0" {
        return true;
    }
    if first != '0' && first.is_ascii_digit() && all_in(b, dec_or_underscore) {
        return true;
    }
    // [-+]?[1-9][0-9_]*(:[0-5]?[0-9])+   (sexagesimal)
    if first != '0' && first.is_ascii_digit() {
        let head: String = b.chars().take_while(|c| dec_or_underscore(*c)).collect();
        let rest = &b[head.len()..];
        if !head.is_empty() && sexagesimal_tail(rest) {
            return true;
        }
    }
    false
}

fn sexagesimal_tail(rest: &str) -> bool {
    // (: [0-5]?[0-9])+ — al menos un grupo.
    if rest.is_empty() {
        return false;
    }
    let groups: Vec<&str> = rest.split(':').collect();
    if groups.first() != Some(&"") {
        return false;
    }
    groups[1..].iter().all(|g| {
        let ok_len = g.len() == 1 || g.len() == 2;
        ok_len
            && g.chars().all(|c| c.is_ascii_digit())
            && g.parse::<u32>().map(|v| v <= 59).unwrap_or(false)
    })
}

fn matches_float(s: &str) -> bool {
    let b = strip_sign(s);
    // \.(?:inf|Inf|INF)
    if matches!(b, ".inf" | ".Inf" | ".INF") {
        return true;
    }
    // \.(?:nan|NaN|NAN)
    if matches!(b, ".nan" | ".NaN" | ".NAN") {
        return true;
    }
    // [-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
    {
        let head: String = b.chars().take_while(|c| dec_or_underscore(*c)).collect();
        if !head.is_empty() && head.starts_with(|c: char| c.is_ascii_digit()) {
            let rest = &b[head.len()..];
            if sexagesimal_upto_dot(rest) {
                return true;
            }
        }
    }
    // [-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
    if let Some(dot) = b.find('.') {
        let (head, tail) = (&b[..dot], &b[dot + 1..]);
        if !head.is_empty()
            && head.chars().all(dec_or_underscore)
            && head.starts_with(|c: char| c.is_ascii_digit())
        {
            let frac_end = tail.find(['e', 'E']).unwrap_or(tail.len());
            let frac = &tail[..frac_end];
            if frac.chars().all(dec_or_underscore) {
                let exp = &tail[frac_end..];
                return valid_exp(exp);
            }
        }
    }
    // \.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
    if let Some(stripped) = b.strip_prefix('.') {
        let frac_end = stripped.find(['e', 'E']).unwrap_or(stripped.len());
        let frac = &stripped[..frac_end];
        if !frac.is_empty()
            && frac.starts_with(|c: char| c.is_ascii_digit())
            && frac.chars().all(dec_or_underscore)
        {
            return valid_exp(&stripped[frac_end..]);
        }
    }
    false
}

fn sexagesimal_upto_dot(rest: &str) -> bool {
    match rest.find('.') {
        None => false,
        Some(d) => sexagesimal_tail(&rest[..d]),
    }
}

fn valid_exp(exp: &str) -> bool {
    // [eE][-+][0-9]+ — en el regex de PyYAML instalado el signo es
    // OBLIGATORIO cuando hay exponente.
    if exp.is_empty() {
        return true;
    }
    let mut it = exp.chars();
    match it.next() {
        Some('e') | Some('E') => {}
        _ => return false,
    }
    let rest: String = it.collect();
    let digits = match rest.strip_prefix(['-', '+']) {
        Some(d) => d,
        None => return false, // sin signo ⇒ NO resuelve como float
    };
    !digits.is_empty() && digits.chars().all(|c| c.is_ascii_digit())
}

fn is_digits_exact(v: &[char]) -> bool {
    v.iter().all(|c| c.is_ascii_digit())
}

fn matches_timestamp(s: &str) -> bool {
    let chs: Vec<char> = s.chars().collect();
    // Alternativa 1: YYYY-MM-DD (día/mes de 2 dígitos fijos).
    if chs.len() == 10
        && is_digits_exact(&chs[0..4])
        && chs[4] == '-'
        && is_digits_exact(&chs[5..7])
        && chs[7] == '-'
        && is_digits_exact(&chs[8..10])
    {
        return true;
    }
    // Alternativa 2: datetime completo.
    // YYYY-M?-D? ([Tt]|sp+) H?:M:M S (.d+)? (sp* (Z|[+-]H?(:MM)?)?)?
    let mut i = 4;
    if chs.len() < i || !is_digits_exact(&chs[0..4]) {
        return false;
    }
    if chs.get(i) != Some(&'-') {
        return false;
    }
    i += 1;
    let m_start = i;
    while i < chs.len() && chs[i].is_ascii_digit() && i - m_start < 2 {
        i += 1;
    }
    let month = &chs[m_start..i];
    if month.is_empty() {
        return false;
    }
    if chs.get(i) != Some(&'-') {
        return false;
    }
    i += 1;
    let d_start = i;
    while i < chs.len() && chs[i].is_ascii_digit() && i - d_start < 2 {
        i += 1;
    }
    if d_start == i {
        return false;
    }
    // separador: T/t o 1+ espacios/tab
    match chs.get(i) {
        Some('T') | Some('t') => i += 1,
        Some(' ') | Some('\t') => {
            while matches!(chs.get(i), Some(' ') | Some('\t')) {
                i += 1;
            }
        }
        _ => return false,
    }
    // HH? : MM : SS
    let h_start = i;
    while i < chs.len() && chs[i].is_ascii_digit() && i - h_start < 2 {
        i += 1;
    }
    if h_start == i || chs.get(i) != Some(&':') {
        return false;
    }
    i += 1;
    let mi_start = i;
    while i < chs.len() && chs[i].is_ascii_digit() && i - mi_start < 2 {
        i += 1;
    }
    if mi_start == i || chs.get(i) != Some(&':') {
        return false;
    }
    i += 1;
    let se_start = i;
    while i < chs.len() && chs[i].is_ascii_digit() && i - se_start < 2 {
        i += 1;
    }
    if se_start == i {
        return false;
    }
    // (\.[0-9]*)?
    if chs.get(i) == Some(&'.') {
        i += 1;
        while i < chs.len() && chs[i].is_ascii_digit() {
            i += 1;
        }
    }
    // (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?
    let mut j = i;
    while matches!(chs.get(j), Some(' ') | Some('\t')) {
        j += 1;
    }
    if chs.get(j) == Some(&'Z') {
        j += 1;
    } else if matches!(chs.get(j), Some('-') | Some('+')) {
        j += 1;
        let zh_start = j;
        while j < chs.len() && chs[j].is_ascii_digit() && j - zh_start < 2 {
            j += 1;
        }
        if zh_start == j {
            return false;
        }
        if chs.get(j) == Some(&':') {
            j += 1;
            let zm_start = j;
            while j < chs.len() && chs[j].is_ascii_digit() && j - zm_start < 2 {
                j += 1;
            }
            if zm_start == j {
                return false;
            }
        }
    }
    j == chs.len()
}

// ── emisor ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Style {
    Plain,
    Single,
    Double,
}

/// Contexto de nodo (espejo de expect_node de PyYAML; solo los campos
/// que afectan la salida: mapping_context y simple_key_context).
#[derive(Clone, Copy)]
struct Ctx {
    mapping: bool,
    simple_key: bool,
}

struct Emitter {
    out: String,
    column: usize,
    /// `None` ≡ `self.indent = None` de PyYAML (raíz).
    indent: Option<usize>,
    indents: Vec<Option<usize>>,
    whitespace: bool,
    indention: bool,
    best_width: usize,
    best_indent: usize,
}

impl Emitter {
    fn new() -> Emitter {
        Emitter {
            out: String::new(),
            column: 0,
            indent: None,
            indents: Vec::new(),
            whitespace: true,
            indention: true,
            best_width: 80,
            best_indent: 2,
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
        self.out.push('\n');
        self.whitespace = true;
        self.indention = true;
        self.column = 0;
    }

    fn write_indent(&mut self) {
        let indent = self.indent.unwrap_or(0);
        if !self.indention || self.column > indent || (self.column == indent && !self.whitespace) {
            self.write_line_break();
        }
        if self.column < indent {
            self.whitespace = true;
            let pad = indent - self.column;
            self.out.push_str(&" ".repeat(pad));
            self.column = indent;
        }
    }

    fn increase_indent(&mut self, flow: bool, indentless: bool) {
        self.indents.push(self.indent);
        if self.indent.is_none() {
            self.indent = Some(if flow { self.best_indent } else { 0 });
        } else if !indentless {
            let v = self.indent.unwrap() + self.best_indent;
            self.indent = Some(v);
        }
    }

    fn pop_indent(&mut self) {
        self.indent = self.indents.pop().flatten();
    }

    fn emit_node(&mut self, node: &Node, ctx: Ctx) {
        match node {
            Node::Str(_) | Node::Bool(_) | Node::Int(_) => {
                self.expect_scalar(node, ctx.simple_key);
            }
            Node::Seq(items) => {
                if items.is_empty() {
                    // check_empty_sequence → flow [].
                    self.write_indicator("[", true, true, false);
                    self.write_indicator("]", false, false, false);
                } else {
                    let indentless = ctx.mapping && !self.indention;
                    self.increase_indent(false, indentless);
                    for it in items {
                        self.write_indent();
                        self.write_indicator("-", true, false, true);
                        self.emit_node(
                            it,
                            Ctx {
                                mapping: false,
                                simple_key: false,
                            },
                        );
                    }
                    self.pop_indent();
                }
            }
            Node::Map(fields) => {
                if fields.is_empty() {
                    self.write_indicator("{", true, true, false);
                    self.write_indicator("}", false, false, false);
                } else {
                    self.increase_indent(false, false);
                    for (k, v) in fields {
                        self.write_indent();
                        // Clave simple: escalar con simple_key=true.
                        self.expect_scalar(&Node::Str(k.clone()), true);
                        self.write_indicator(":", false, false, false);
                        self.emit_node(
                            v,
                            Ctx {
                                mapping: true,
                                simple_key: false,
                            },
                        );
                    }
                    self.pop_indent();
                }
            }
        }
    }

    /// expect_scalar: increase_indent(flow=True) → process_scalar → pop.
    fn expect_scalar(&mut self, node: &Node, simple_key: bool) {
        self.increase_indent(true, false);
        self.process_scalar(node, simple_key);
        self.pop_indent();
    }

    fn process_scalar(&mut self, node: &Node, simple_key: bool) {
        let split = !simple_key;
        match node {
            Node::Bool(b) => {
                // implicit[0]=True (tag bool resuelve igual) ⇒ plain.
                self.write_plain(if *b { "true" } else { "false" }, split);
            }
            Node::Int(i) => {
                self.write_plain(&i.to_string(), split);
            }
            Node::Str(text) => {
                let analysis = analyze_scalar(text);
                let style = self.choose_style(text, &analysis, simple_key);
                match style {
                    Style::Plain => self.write_plain(text, split),
                    Style::Single => self.write_single_quoted(text, split),
                    Style::Double => self.write_double_quoted(text, split),
                }
            }
            _ => unreachable!("process_scalar sobre colección"),
        }
    }

    /// choose_scalar_style para estilo None (safe_dump de str/bool/int).
    fn choose_style(&self, text: &str, a: &Analysis, simple_key: bool) -> Style {
        // Rama plain: requiere implicit[0] — para Str significa que el
        // resolver lo etiquetaría como str; Bool/Int siempre son implícitos.
        let plain_allowed = !implicitly_non_str(text);
        if plain_allowed && !(simple_key && (a.empty || a.multiline)) && a.allow_block_plain {
            return Style::Plain;
        }
        if a.allow_single_quoted && !(simple_key && a.multiline) {
            return Style::Single;
        }
        Style::Double
    }

    // ── writers (porteo literal de yaml/emitter.py) ─────────────────────────

    fn push_run(&mut self, chs: &[char], start: usize, end: usize) {
        let data: String = chs[start..end].iter().collect();
        self.column += end - start;
        self.out.push_str(&data);
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
        let chs: Vec<char> = text.chars().collect();
        let mut spaces = false;
        let mut breaks = false;
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= chs.len() {
            let ch = chs.get(end).copied();
            if spaces {
                if ch != Some(' ') {
                    if end.saturating_sub(start) == 1 && self.column > self.best_width && split {
                        self.write_indent();
                        self.whitespace = false;
                        self.indention = false;
                    } else {
                        self.push_run(&chs, start, end);
                    }
                    start = end;
                }
            } else if breaks {
                if !ch.is_some_and(is_break) {
                    if chs[start] == '\n' {
                        self.write_line_break();
                    }
                    for br in &chs[start..end] {
                        if *br == '\n' {
                            self.write_line_break();
                        } else {
                            self.write_line_break_custom(*br);
                        }
                    }
                    self.write_indent();
                    self.whitespace = false;
                    self.indention = false;
                    start = end;
                }
            } else if ch.is_none() || ch.is_some_and(is_space_or_break) {
                self.push_run(&chs, start, end);
                start = end;
            }
            if let Some(c) = ch {
                spaces = c == ' ';
                breaks = is_break(c);
            }
            end += 1;
        }
    }

    fn write_line_break_custom(&mut self, br: char) {
        self.out.push(br);
        self.whitespace = true;
        self.indention = true;
        self.column = 0;
    }

    fn write_single_quoted(&mut self, text: &str, split: bool) {
        self.write_indicator("'", true, false, false);
        let chs: Vec<char> = text.chars().collect();
        let mut spaces = false;
        let mut breaks = false;
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= chs.len() {
            let ch = chs.get(end).copied();
            if spaces {
                if ch.is_none() || ch != Some(' ') {
                    if start + 1 == end
                        && self.column > self.best_width
                        && split
                        && start != 0
                        && end != chs.len()
                    {
                        self.write_indent();
                    } else {
                        self.push_run(&chs, start, end);
                    }
                    start = end;
                }
            } else if breaks {
                if ch.is_none_or(|c| !is_break(c)) {
                    if chs[start] == '\n' {
                        self.write_line_break();
                    }
                    for br in &chs[start..end] {
                        if *br == '\n' {
                            self.write_line_break();
                        } else {
                            self.write_line_break_custom(*br);
                        }
                    }
                    self.write_indent();
                    start = end;
                }
            } else if (ch.is_none() || ch.is_some_and(is_space_or_break) || ch == Some('\''))
                && start < end
            {
                self.push_run(&chs, start, end);
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

    fn escape_replacement(ch: char) -> Option<String> {
        Some(match ch {
            '\0' => "\\0".into(),
            '\u{7}' => "\\a".into(),
            '\u{8}' => "\\b".into(),
            '\t' => "\\t".into(),
            '\n' => "\\n".into(),
            '\u{B}' => "\\v".into(),
            '\u{C}' => "\\f".into(),
            '\r' => "\\r".into(),
            '\u{1B}' => "\\e".into(),
            '"' => "\\\"".into(),
            '\\' => "\\\\".into(),
            '\u{85}' => "\\N".into(),
            '\u{A0}' => "\\_".into(),
            '\u{2028}' => "\\L".into(),
            '\u{2029}' => "\\P".into(),
            _ => {
                let cu = ch as u32;
                if cu <= 0xFF {
                    format!("\\x{cu:02X}")
                } else if cu <= 0xFFFF {
                    format!("\\u{cu:04X}")
                } else {
                    format!("\\U{cu:08X}")
                }
            }
        })
    }

    fn needs_double_escape(ch: char) -> bool {
        let cu = ch as u32;
        matches!(cu, 0x22 | 0x5C | 0x85 | 0x2028 | 0x2029 | 0xFEFF)
            || !(('\u{20}'..'\u{7E}').contains(&ch)
                || (0xA0..=0xD7FF).contains(&cu)
                || (0xE000..=0xFFFD).contains(&cu))
    }

    fn write_double_quoted(&mut self, text: &str, split: bool) {
        self.write_indicator("\"", true, false, false);
        let chs: Vec<char> = text.chars().collect();
        let mut start = 0usize;
        let mut end = 0usize;
        while end <= chs.len() {
            let ch = chs.get(end).copied();
            let must_escape = match ch {
                None => true,
                Some(c) => Self::needs_double_escape(c),
            };
            if must_escape {
                if start < end {
                    self.push_run(&chs, start, end);
                    start = end;
                }
                if let Some(c) = ch {
                    let data = Self::escape_replacement(c).unwrap();
                    self.column += data.chars().count();
                    self.out.push_str(&data);
                    start = end + 1;
                }
            }
            let cond_fold = 0 < end
                && end < chs.len().saturating_sub(1)
                && (ch == Some(' ') || start >= end)
                // end-start puede ser negativo tras un escape (start=end+1):
                // PyYAML lo permite aritméticamente ⇒ isize.
                && self.column as isize + (end as isize - start as isize)
                    > self.best_width as isize
                && split;
            if cond_fold {
                let mut data: String = if start < end {
                    chs[start..end].iter().collect()
                } else {
                    String::new()
                };
                data.push('\\');
                if start < end {
                    start = end;
                }
                self.column += data.chars().count();
                self.out.push_str(&data);
                self.write_indent();
                self.whitespace = false;
                self.indention = false;
                if chs.get(start) == Some(&' ') {
                    self.out.push('\\');
                    self.column += 1;
                }
            }
            end += 1;
        }
        self.write_indicator("\"", false, false, false);
    }
}

/// Serializa el árbol a String con formato PyYAML safe_dump
/// (sort_keys=False · allow_unicode=True · width=80 · indent=2 ·
/// explicit_start=False), terminado en `\n`.
pub fn to_pyyaml_string(node: &Node) -> String {
    let mut em = Emitter::new();
    em.emit_node(
        node,
        Ctx {
            mapping: false,
            simple_key: false,
        },
    );
    // Document end: un único salto de línea final (safe_dump).
    if !em.out.ends_with('\n') {
        em.out.push('\n');
    }
    em.out
}
