//! Puerto de `cortex/semantic/markdown_parser.py` — paridad conductual.
//!
//! Piezas replicadas:
//! - `_FRONTMATTER_RE = ^---\s*\n(.*?)\n---\s*\n` (DOTALL, anclado al inicio)
//! - título: frontmatter `title` o `stem.replace("_"," ").title()` de Python
//! - tags: frontmatter (lista|str) + hashtags inline `\w#…` dedup ordenado
//! - wiki-links `\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]`
//! - contenido: bloque de frontmatter removido + `.strip()`

use std::path::Path;

pub struct ParsedDoc {
    pub title: String,
    pub content: String,
    pub tags: Vec<String>,
    pub links: Vec<String>,
}

fn is_ws(c: char) -> bool {
    c.is_whitespace()
}

/// Devuelve `(inicio_contenido, fin_contenido, inicio_cuerpo)` si hay bloque
/// de frontmatter, replicando `^---\s*\n(.*?)\n---\s*\n` no-greedy y DOTALL.
fn frontmatter_span(raw: &str) -> Option<(usize, usize, usize)> {
    if !raw.starts_with("---") {
        return None;
    }
    let b = raw.as_bytes();
    // \s* + \n tras "---" (el \s* retrocede hasta dejar un único \n).
    let mut i = 3;
    while i < b.len() && is_ws(b[i] as char) && b[i] != b'\n' {
        i += 1;
    }
    if i >= b.len() || b[i] != b'\n' {
        return None;
    }
    let content_start = i + 1;

    // Buscar el cierre: "\n---\s*\n" (primera aparición ⇒ no-greedy).
    let mut j = content_start;
    while j < b.len() {
        if b[j] == b'\n' && raw[j + 1..].starts_with("---") {
            let mut k = j + 4;
            while k < b.len() && is_ws(b[k] as char) && b[k] != b'\n' {
                k += 1;
            }
            if k < b.len() && b[k] == b'\n' {
                return Some((content_start, j, k + 1));
            }
        }
        j += 1;
    }
    None
}

fn split_frontmatter(raw: &str) -> (serde_yaml::Mapping, String) {
    match frontmatter_span(raw) {
        Some((cs, ce, body_start)) => {
            let fm_text = &raw[cs..ce];
            let data: serde_yaml::Mapping = serde_yaml::from_str(fm_text).unwrap_or_default();
            (data, raw[body_start..].to_string())
        }
        None => (serde_yaml::Mapping::new(), raw.to_string()),
    }
}

/// Replica `_FRONTMATTER_RE.sub("", raw).strip()`.
fn strip_frontmatter_block(raw: &str) -> String {
    match frontmatter_span(raw) {
        Some((_, _, body_start)) => raw[body_start..].trim().to_string(),
        None => raw.trim().to_string(),
    }
}

/// Replica `str.title()` de Python: mayúscula tras cualquier carácter no cased.
fn py_title(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut prev_cased = false;
    for c in s.chars() {
        if c.is_alphabetic() {
            if prev_cased {
                out.extend(c.to_lowercase());
            } else {
                out.extend(c.to_uppercase());
            }
            prev_cased = true;
        } else {
            out.push(c);
            prev_cased = false;
        }
    }
    out
}

fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// `(?<!\w)#([A-Za-z][A-Za-z0-9_-]*)` sin look-behind: escaneo manual que
/// replica el avance no-solapado de `re.findall`.
fn inline_hashtags(body: &str) -> Vec<String> {
    let chars: Vec<char> = body.chars().collect();
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        if chars[i] == '#' {
            let prev_ok = i == 0 || !is_word_char(chars[i - 1]);
            if prev_ok {
                if let Some(tag_len) = match_hashtag(&chars[i + 1..]) {
                    out.push(chars[i + 1..i + 1 + tag_len].iter().collect());
                    i += 1 + tag_len;
                    continue;
                }
            }
        }
        i += 1;
    }
    out
}

/// Longitud del match `[A-Za-z][A-Za-z0-9_-]*`, o None.
fn match_hashtag(chars: &[char]) -> Option<usize> {
    let first = *chars.first()?;
    if !first.is_ascii_alphabetic() {
        return None;
    }
    let mut n = 1usize;
    while n < chars.len()
        && (chars[n].is_ascii_alphanumeric() || chars[n] == '_' || chars[n] == '-')
    {
        n += 1;
    }
    Some(n)
}

fn wiki_links(body: &str) -> Vec<String> {
    let re = regex::Regex::new(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]").expect("regex válida");
    re.captures_iter(body).map(|c| c[1].to_string()).collect()
}

fn yaml_to_plain(v: &serde_yaml::Value) -> Option<String> {
    match v {
        serde_yaml::Value::Null => None,
        serde_yaml::Value::String(s) => Some(s.clone()),
        serde_yaml::Value::Number(n) => Some(n.to_string()),
        serde_yaml::Value::Bool(b) => Some(b.to_string()),
        _ => Some(String::new()),
    }
}

/// Puerto de `MarkdownParser.parse`.
pub fn parse(raw: &str, path: &Path) -> ParsedDoc {
    let (fm, body) = split_frontmatter(raw);

    let stem = path
        .file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_default();
    let fallback_title = py_title(&stem.replace('_', " "));

    let title = fm
        .get("title")
        .and_then(yaml_to_plain)
        .filter(|s| !s.trim().is_empty())
        .unwrap_or(fallback_title);

    let mut fm_tags: Vec<String> = Vec::new();
    match fm.get("tags") {
        Some(serde_yaml::Value::Sequence(seq)) => {
            for t in seq {
                if let Some(s) = yaml_to_plain(t) {
                    fm_tags.push(s);
                }
            }
        }
        Some(v) => {
            if let Some(s) = yaml_to_plain(v) {
                fm_tags.push(s);
            }
        }
        None => {}
    }

    let inline = inline_hashtags(&body);
    let mut tags: Vec<String> = Vec::new();
    for t in fm_tags.into_iter().chain(inline) {
        if !tags.contains(&t) {
            tags.push(t);
        }
    }

    ParsedDoc {
        title,
        content: strip_frontmatter_block(raw),
        tags,
        links: wiki_links(&body),
    }
}
