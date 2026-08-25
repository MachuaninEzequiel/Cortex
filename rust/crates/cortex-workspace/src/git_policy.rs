//! Porteo de `cortex/git_policy.py` — patrones y snippet de `.gitignore`
//! por layout, y chequeo de contenido de `.gitignore`.

#![forbid(unsafe_code)]

use std::path::Path;

use crate::layout::WorkspaceLayout;

/// Patrones siempre recomendados, independiente del layout.
pub const RECOMMENDED_GITIGNORE_PATTERNS: &[&str] = &[".memory/", "*.chroma/", "vault/sessions/"];

/// Patrones específicos del nuevo layout (seguros en cualquiera).
pub const NEW_LAYOUT_GITIGNORE_PATTERNS: &[&str] = &[
    ".cortex/memory/",
    ".cortex/vault/sessions/",
    ".cortex/session.lock",
];

/// Patrones específicos del legacy.
pub const LEGACY_GITIGNORE_PATTERNS: &[&str] =
    &[".memory/", "vault/sessions/", ".cortex/session.lock"];

const SNIPPET_NEW_HEAD: &[&str] = &[
    "# Cortex local state (new layout)",
    ".cortex/memory/",
    "*.chroma/",
    "",
    "# Cortex vault policy",
    "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
    "# Ignore session churn by default unless your team explicitly audits sessions in Git",
];
const SNIPPET_LEGACY_HEAD: &[&str] = &[
    "# Cortex local state",
    ".memory/",
    "*.chroma/",
    "",
    "# Cortex vault policy",
    "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
    "# Ignore session churn by default unless your team explicitly audits sessions in Git",
];

/// Snippet de `.gitignore` según layout detectado. Sin layout ⇒ superset
/// conservador (legacy), igual que Python.
pub fn recommended_gitignore_snippet(layout: Option<&WorkspaceLayout>) -> String {
    match layout {
        Some(l) if l.is_new_layout => {
            let mut lines: Vec<&str> = SNIPPET_NEW_HEAD.to_vec();
            lines.push(".cortex/vault/sessions/");
            lines.join("\n")
        }
        _ => {
            let mut lines: Vec<&str> = SNIPPET_LEGACY_HEAD.to_vec();
            lines.push("vault/sessions/");
            lines.join("\n")
        }
    }
}

/// True si `.gitignore` de `root` contiene el patrón exacto (líneas vacías
/// y comentarios se ignoran; comparación post-strip).
pub fn gitignore_contains(root: &Path, pattern: &str) -> bool {
    let gitignore = root.join(".gitignore");
    if !gitignore.exists() {
        return false;
    }
    let normalized = pattern.trim();
    let Ok(content) = std::fs::read_to_string(&gitignore) else {
        return false;
    };
    for line in content.lines() {
        let candidate = line.trim();
        if candidate.is_empty() || candidate.starts_with('#') {
            continue;
        }
        if candidate == normalized {
            return true;
        }
    }
    false
}
