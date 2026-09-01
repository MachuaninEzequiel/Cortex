//! Puerto de `cortex/documenter/spec_loader.py` + `adr_evaluator.py`.

use std::path::{Path, PathBuf};

use super::super::session::VerificationHook;

#[derive(Debug, Clone)]
pub struct LoadedSpec {
    pub path: PathBuf,
    pub title: String,
    pub goal: String,
    /// Rutas POSIX (Python guarda `Path`; acá la forma canónica).
    pub files_in_scope: Vec<String>,
    pub constraints: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub verification_hooks: Vec<VerificationHook>,
    /// COMPOSED (spec 13 §1.3): exige checkpoint phase=close para Closed.
    /// Leniente: ausente/roto ⇒ false, nunca falla.
    pub require_close_phase: bool,
}

/// Frontmatter leniente: sin bloque o YAML roto ⇒ vacío (nunca falla).
fn frontmatter_lenient(text: &str) -> serde_yaml::Mapping {
    if !text.starts_with("---") {
        return serde_yaml::Mapping::new();
    }
    let b = text.as_bytes();
    let mut i = 3;
    while i < b.len() && (b[i] as char).is_whitespace() && b[i] != b'\n' {
        i += 1;
    }
    if i >= b.len() || b[i] != b'\n' {
        return serde_yaml::Mapping::new();
    }
    let cs = i + 1;
    let mut j = cs;
    while j < b.len() {
        if b[j] == b'\n' && text[j + 1..].starts_with("---") {
            return serde_yaml::from_str(&text[cs..j]).unwrap_or_default();
        }
        j += 1;
    }
    serde_yaml::Mapping::new()
}

fn body_after_frontmatter(text: &str) -> &str {
    let b = text.as_bytes();
    if !text.starts_with("---") {
        return text;
    }
    let mut i = 3;
    while i < b.len() && (b[i] as char).is_whitespace() && b[i] != b'\n' {
        i += 1;
    }
    if i >= b.len() || b[i] != b'\n' {
        return text;
    }
    let mut j = i + 1;
    while j < b.len() {
        if b[j] == b'\n' && text[j + 1..].starts_with("---") {
            let mut k = j + 4;
            while k < b.len() && (b[k] as char).is_whitespace() && b[k] != b'\n' {
                k += 1;
            }
            if k < b.len() && b[k] == b'\n' {
                return &text[k + 1..];
            }
        }
        j += 1;
    }
    text
}

/// `_extract_section`: texto bajo un heading `## <título>` hasta el próximo
/// `## ` o fin. Sin match ⇒ "".
pub fn extract_section(body: &str, heading: &str) -> String {
    let needle = format!("## {heading}");
    let mut out_lines: Vec<&str> = Vec::new();
    let mut dentro = false;
    for line in body.lines() {
        if line.trim_end() == needle.trim_end() {
            dentro = true;
            continue;
        }
        if dentro && line.starts_with("## ") {
            break;
        }
        if dentro {
            out_lines.push(line);
        }
    }
    out_lines.join("\n").trim().to_string()
}

fn load_hooks(raw: &[serde_yaml::Value]) -> Vec<VerificationHook> {
    let mut hooks = Vec::new();
    for item in raw {
        // Entradas inválidas se loggean y saltan — la spec queda usable.
        let name = item.get("name").and_then(|v| v.as_str()).unwrap_or("");
        let command = item.get("command").and_then(|v| v.as_str()).unwrap_or("");
        if name.is_empty() || command.is_empty() {
            continue;
        }
        let required = item
            .get("required")
            .and_then(|v| v.as_bool())
            .unwrap_or(true);
        let success_criteria = item
            .get("success_criteria")
            .and_then(|v| v.as_str())
            .unwrap_or("exit code 0")
            .to_string();
        let timeout_seconds = item
            .get("timeout_seconds")
            .and_then(|v| v.as_u64())
            .unwrap_or(300)
            .clamp(1, 1800);
        hooks.push(VerificationHook {
            name: name.into(),
            command: command.into(),
            required,
            success_criteria,
            timeout_seconds,
        });
    }
    hooks
}

fn str_list(v: Option<&serde_yaml::Value>) -> Vec<String> {
    match v {
        Some(serde_yaml::Value::Sequence(seq)) => seq
            .iter()
            .map(|x| match x {
                serde_yaml::Value::String(s) => s.clone(),
                other => serde_yaml::to_string(other)
                    .map(|s| s.trim().to_string())
                    .unwrap_or_default(),
            })
            .collect(),
        _ => Vec::new(),
    }
}

/// `require_close_phase` del frontmatter (bool; ausente/roto ⇒ false).
fn require_close_phase(fm: &serde_yaml::Mapping) -> bool {
    fm.get(serde_yaml::Value::String("require_close_phase".into()))
        .and_then(serde_yaml::Value::as_bool)
        .unwrap_or(false)
}

/// Puerto de `load_spec` — missing/malformed ⇒ spec vacía usable.
pub fn load_spec(path: &Path) -> LoadedSpec {
    let empty_path = path.to_path_buf();
    let Ok(text) = std::fs::read_to_string(path) else {
        return LoadedSpec {
            path: empty_path,
            title: String::new(),
            goal: String::new(),
            files_in_scope: vec![],
            constraints: vec![],
            acceptance_criteria: vec![],
            verification_hooks: vec![],
            require_close_phase: false,
        };
    };
    let fm = frontmatter_lenient(&text);

    let get_str = |k: &str| -> String {
        match fm.get(serde_yaml::Value::String(k.into())) {
            Some(serde_yaml::Value::String(s)) => s.clone(),
            Some(serde_yaml::Value::Null) | None => String::new(),
            Some(other) => serde_yaml::to_string(other)
                .map(|s| s.trim().to_string())
                .unwrap_or_default(),
        }
    };

    let body = body_after_frontmatter(&text);
    let goal = {
        let g = get_str("goal");
        if g.is_empty() {
            extract_section(body, "Goal")
        } else {
            g
        }
    };

    LoadedSpec {
        path: empty_path,
        title: get_str("title"),
        goal,
        files_in_scope: str_list(fm.get(serde_yaml::Value::String("files_in_scope".into()))),
        constraints: str_list(fm.get(serde_yaml::Value::String("constraints".into()))),
        acceptance_criteria: str_list(
            fm.get(serde_yaml::Value::String("acceptance_criteria".into())),
        ),
        verification_hooks: load_hooks(
            fm.get(serde_yaml::Value::String("verification_hooks".into()))
                .and_then(|v| serde_yaml::Value::as_sequence(v))
                .map(|s| s.to_vec())
                .unwrap_or_default()
                .as_slice(),
        ),
        require_close_phase: require_close_phase(&fm),
    }
}

// ── adr_evaluator ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct AdrSuggestion {
    pub title: String,
    pub rationale: String,
    pub source_checkpoint_index: usize,
    pub evidence: String,
    /// high | low
    pub confidence: String,
}

const DECISION_PATTERNS: [&str; 10] = [
    r"\bdecid(?:ed|imos|í)\b",
    r"\bchose\b",
    r"\binstead of\b",
    r"\brather than\b",
    r"\btrade-?off\b",
    r"\bvs\.?\b",
    r"\brejected\b",
    r"\balternativa(?:s)?\b",
    r"\bsupersedes\b",
    r"\bADR\b",
];

fn title_from_note(note: &str) -> String {
    let cleaned = note.split_whitespace().collect::<Vec<_>>().join(" ");
    if cleaned.chars().count() <= 80 {
        cleaned
    } else {
        let cut: String = cleaned.chars().take(77).collect();
        format!("{}...", cut.trim_end())
    }
}

/// Puerto de `suggest_adrs` — sólo inspecciona checkpoint.notes.
pub fn suggest_adrs(checkpoints: &[super::super::session::Checkpoint]) -> Vec<AdrSuggestion> {
    let mut suggestions = Vec::new();
    for (idx, cp) in checkpoints.iter().enumerate() {
        if cp.note.trim().is_empty() {
            continue;
        }
        let matches: Vec<String> = DECISION_PATTERNS
            .iter()
            .filter(|p| {
                regex::Regex::new(&format!("(?i){p}"))
                    .map(|re| re.is_match(&cp.note))
                    .unwrap_or(false)
            })
            .map(|p| p.to_string())
            .collect();
        if matches.is_empty() {
            continue;
        }
        let mut sorted_uniq = matches.clone();
        sorted_uniq.sort();
        sorted_uniq.dedup();
        suggestions.push(AdrSuggestion {
            title: title_from_note(&cp.note),
            rationale: format!(
                "Checkpoint #{idx} note mentions decision signal(s): {}",
                sorted_uniq.join(", ")
            ),
            source_checkpoint_index: idx,
            evidence: cp.note.clone(),
            confidence: if matches.len() >= 2 { "high" } else { "low" }.into(),
        });
    }
    suggestions
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn require_close_phase_parses_bool_from_frontmatter() {
        let m = frontmatter_lenient("---\nrequire_close_phase: true\n---\nbody\n");
        assert!(require_close_phase(&m));
        let m = frontmatter_lenient("---\nrequire_close_phase: false\n---\nbody\n");
        assert!(!require_close_phase(&m));
    }

    #[test]
    fn require_close_phase_missing_or_broken_defaults_false() {
        let m = frontmatter_lenient("---\ngoal: x\n---\nbody\n");
        assert!(!require_close_phase(&m));
        let broken = frontmatter_lenient("---\n: : not yaml\n---\nbody\n");
        assert!(!require_close_phase(&broken));
        assert!(frontmatter_lenient("no frontmatter at all\n").is_empty());
    }

    #[test]
    fn load_spec_carries_require_close_phase() {
        let dir = std::env::temp_dir().join(format!("cortex-a6-{}-t", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let with_flag = dir.join("spec-flag.md");
        std::fs::write(
            &with_flag,
            "---\ntitle: T\nrequire_close_phase: true\n---\n## Goal\nG\n",
        )
        .unwrap();
        assert!(load_spec(&with_flag).require_close_phase);

        let legacy = dir.join("spec-legacy.md");
        std::fs::write(&legacy, "---\ntitle: T\n---\n## Goal\nG\n").unwrap();
        assert!(!load_spec(&legacy).require_close_phase);

        let _ = std::fs::remove_file(&with_flag);
        let _ = std::fs::remove_file(&legacy);
        let _ = std::fs::remove_dir(&dir);
    }
}
