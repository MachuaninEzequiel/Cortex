//! Puerto de `cortex/semantic/chunker.py` — chunking por H2/H3 con fallback
//! single-chunk, colisiones de slug sufijadas y embedding_text compuesto.
//!
//! Desviación documentada: `_split_paragraphs` no se porta en P2b porque
//! ninguna ruta de la tabla canónica usa boundary="paragraph" (inalcanzable).

use super::routing::{DocType, Route};
use unicode_normalization::UnicodeNormalization;

#[derive(Debug, Clone)]
pub struct Chunk {
    pub parent_path: String,
    pub chunk_id: String,
    pub section_title: String,
    pub position: usize,
    pub text: String,
    pub doc_type: DocType,
    pub tags: Vec<String>,
}

impl Chunk {
    /// `Chunk.embedding_text`: " ".join(partes no vacías de
    /// (doc_type.value, tags, section_title, body)).strip()
    pub fn embedding_text(&self) -> String {
        let tags_part = self.tags.join(" ");
        [
            self.doc_type.value().to_string(),
            tags_part,
            self.section_title.clone(),
            self.text.clone(),
        ]
        .iter()
        .filter(|p| !p.is_empty())
        .cloned()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string()
    }
}

fn word_count(text: &str) -> usize {
    text.split_whitespace().count()
}

fn single_chunk(
    content: &str,
    section_title: &str,
    doc_type: DocType,
    tags: &[String],
    parent: &str,
) -> Chunk {
    Chunk {
        parent_path: parent.into(),
        chunk_id: parent.into(),
        section_title: section_title.into(),
        position: 0,
        text: content.trim().to_string(),
        doc_type,
        tags: tags.to_vec(),
    }
}

/// slugify de `cortex/documentation/common.py`:
/// NFKD→ascii, lower, strip `[^\w\s-]`, `[\s_]+`→"-", collapse `-+`, trim `-`.
pub fn slugify(value: &str) -> String {
    if value.is_empty() {
        return String::new();
    }
    let folded: String = value.nfkd().filter(char::is_ascii).collect();
    let cleaned: String = folded
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || c.is_whitespace() || *c == '-')
        .collect();
    // [\s_]+ → "-" y collapse "-+" en una sola pasada estable.
    let mut collapsed = String::with_capacity(cleaned.len());
    let mut prev_sep = false;
    for c in cleaned.chars() {
        if c.is_whitespace() || c == '_' || c == '-' {
            if !prev_sep {
                collapsed.push('-');
                prev_sep = true;
            }
        } else {
            collapsed.push(c);
            prev_sep = false;
        }
    }
    collapsed.trim_matches('-').to_string()
}

struct LineRef<'a> {
    /// Contenido de la línea sin el '\n'.
    text: &'a str,
    /// Byte offset del inicio de la línea.
    start: usize,
    /// Byte offset del fin del contenido (antes del '\n') = match.end() Python.
    end: usize,
}

fn mem_lines(s: &str) -> Vec<LineRef<'_>> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    for line in s.split('\n') {
        out.push(LineRef {
            text: line,
            start: offset,
            end: offset + line.len(),
        });
        offset += line.len() + 1;
    }
    // El split genera un string vacío final si hay '\n' terminal; una línea
    // vacía nunca matchea un header ⇒ se descarta por el filtro de título.
    out.retain(|l| l.text.starts_with('#'));
    out
}

/// Extrae `(título, start, end)` de headers H2 (y H3 si `h3_too`),
/// replicando `^(?:##|###)\s+(.+?)\s*$` MULTILINE con ancla real.
fn find_headers(content: &str, h3_too: bool) -> Vec<(String, usize, usize)> {
    let mut out = Vec::new();
    for line in mem_lines(content) {
        let hashes_len = if line.text.starts_with("##") {
            2
        } else {
            continue;
        };
        let after_hashes = &line.text[hashes_len..];
        let is_h3_line = after_hashes.starts_with('#');
        if is_h3_line && !h3_too {
            continue; // "### x" NO matchea ^##\s+
        }
        let hashes_len = if is_h3_line { 3 } else { 2 };
        let Some(after) = line.text.get(hashes_len..) else {
            continue;
        };
        // \s+ : al menos UN whitespace tras los numerales.
        let mut ws = 0usize;
        let b = after.as_bytes();
        while ws < b.len() && (b[ws] as char).is_whitespace() {
            ws += 1;
        }
        if ws == 0 {
            continue;
        }
        let title = after[ws..].trim_end();
        if title.is_empty() {
            continue;
        }
        out.push((title.to_string(), line.start, line.end));
    }
    out
}

/// Puerto de `chunk_document` (boundary h2/h3; paragraph inalcanzable vía tabla).
pub fn chunk_document(
    title: &str,
    content: &str,
    doc_type: DocType,
    tags: &[String],
    parent_path: &str,
    route: Route,
) -> Vec<Chunk> {
    let safe_title = if title.is_empty() {
        "(untitled)"
    } else {
        title
    };

    if content.trim().is_empty() || word_count(content) < route.min_words {
        return vec![single_chunk(
            content,
            safe_title,
            doc_type,
            tags,
            parent_path,
        )];
    }

    let headers = find_headers(content, route.boundary_h3);
    if headers.is_empty() {
        return vec![single_chunk(
            content,
            safe_title,
            doc_type,
            tags,
            parent_path,
        )];
    }

    let mut chunks: Vec<Chunk> = Vec::new();
    let mut slug_counts: std::collections::HashMap<String, usize> =
        std::collections::HashMap::new();

    let mut make = |text: &str, section_title: &str, position: usize| -> Chunk {
        let s = slugify(section_title);
        let slug = if s.is_empty() {
            "section".to_string()
        } else {
            s
        };
        let key = format!("h2-{slug}");
        let seen = slug_counts.get(&key).copied().unwrap_or(0);
        let chunk_id = if seen == 0 {
            format!("{parent_path}#{key}")
        } else {
            format!("{parent_path}#{key}-{}", seen + 1)
        };
        slug_counts.insert(key, seen + 1);
        Chunk {
            parent_path: parent_path.into(),
            chunk_id,
            section_title: section_title.into(),
            position,
            text: text.trim().to_string(),
            doc_type,
            tags: tags.to_vec(),
        }
    };

    // Prefix antes del primer header ("(prefix)", posición 0).
    let prefix = content[..headers[0].1].trim();
    if !prefix.is_empty() {
        chunks.push(make(prefix, "(prefix)", 0));
    }

    for (i, (sec_title, sec_start_of_header, header_end)) in headers.iter().enumerate() {
        let _ = sec_start_of_header;
        let sec_start = *header_end; // match.end() Python: fin del título, SIN '\n'
        let sec_end = headers.get(i + 1).map(|n| n.1).unwrap_or(content.len());
        let section_text = content[sec_start..sec_end.min(content.len())].trim();
        chunks.push(make(section_text, sec_title, i + 1));
    }

    chunks
}

/// Wrapper público de `single_chunk` para el índice (fallback no-chunked).
pub fn single_chunk_public(
    content: &str,
    section_title: &str,
    doc_type: DocType,
    tags: &[String],
    parent: &str,
) -> Chunk {
    single_chunk(content, section_title, doc_type, tags, parent)
}
