//! Puerto de `cortex/documenter/diff_parser.py` — parseo de
//! `git diff --name-status`.

use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiffAction {
    Added,
    Deleted,
    Modified,
    Renamed,
    Copied,
}

impl DiffAction {
    fn from_code(code: &str) -> Self {
        match code {
            "A" => Self::Added,
            "D" => Self::Deleted,
            "R" => Self::Renamed,
            "C" => Self::Copied,
            _ => Self::Modified, // unknown statuses fall back a modified
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct DiffEntry {
    pub action: DiffAction,
    /// Ubicación *actual* (post-cambio).
    pub path: PathBuf,
    /// Sólo para renames/copies.
    pub old_path: Option<PathBuf>,
}

/// Cada línea no-vacía: `<status>\t<path>` o `<status>\t<old>\t<new>`.
/// Líneas vacías y whitespace inicial se ignoran. Unknown → modified.
pub fn parse_name_status(output: &str) -> Vec<DiffEntry> {
    let mut entries = Vec::new();
    for raw in output.lines() {
        let line = raw.trim();
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('\t').collect();
        match parts.len() {
            2 => entries.push(DiffEntry {
                action: DiffAction::from_code(parts[0]),
                path: PathBuf::from(parts[1]),
                old_path: None,
            }),
            3 => entries.push(DiffEntry {
                action: DiffAction::from_code(parts[0]),
                path: PathBuf::from(parts[2]),
                old_path: Some(PathBuf::from(parts[1])),
            }),
            n => {
                eprintln!("diff_parser: línea con {n} columnas ignorada: {line:?}");
            }
        }
    }
    entries
}
