//! Observer del trabajo en curso — réplica de
//! `cortex/context_enricher/observer.py` (P12A-7).
//!
//! Fuentes: git diff, PR metadata o input manual. Extrae keywords, imports,
//! funciones/clases y detecta el dominio; genera las 4 search queries para
//! el enriquecimiento multi-estrategia.

use std::process::Command;

use regex::Regex;

use super::domain_detector::DomainDetector;
use super::models::WorkContext;

pub struct ContextObserver {
    detector: DomainDetector,
}

impl ContextObserver {
    pub fn new(model_dir: Option<&std::path::Path>) -> Self {
        Self {
            detector: DomainDetector::new(0.5, model_dir),
        }
    }

    /// Observa desde `git diff` contra la rama base.
    pub fn observe_from_git(&mut self, base_branch: &str) -> WorkContext {
        let changed_files = get_changed_files(base_branch);
        let new_files = get_new_files();
        let deleted_files = get_deleted_files(base_branch);

        let diff_content = get_diff_content(base_branch);
        let keywords = extract_keywords(&diff_content);
        let imports = extract_imports(&diff_content);
        let functions = extract_functions(&diff_content);
        let classes = extract_classes(&diff_content);

        self.build_context(
            "git_diff",
            changed_files,
            new_files,
            deleted_files,
            keywords,
            imports,
            functions,
            classes,
            None,
            None,
            vec![],
        )
    }

    /// Observa desde un PR context (campos files_changed/title/body/labels).
    pub fn observe_from_pr(
        &mut self,
        files_changed: &[String],
        title: &str,
        body: &str,
        labels: &[String],
    ) -> WorkContext {
        let text = format!("{title} {body}");
        let mut keywords = extract_text_keywords(&text);
        if !title.is_empty() {
            // dict.fromkeys preserva primer aparecimiento.
            let mut seen: Vec<String> = vec![title.to_lowercase()];
            for k in keywords {
                if !seen.contains(&k) {
                    seen.push(k);
                }
            }
            keywords = seen;
        }
        self.build_context(
            "pr",
            files_changed.to_vec(),
            vec![],
            vec![],
            keywords,
            vec![],
            vec![],
            vec![],
            Some(title.to_string()),
            Some(body.to_string()),
            labels.to_vec(),
        )
    }

    /// Observa desde una lista explícita de archivos.
    #[allow(clippy::too_many_arguments)]
    pub fn observe_from_files(
        &mut self,
        files: &[String],
        keywords: Option<Vec<String>>,
        imports: Option<Vec<String>>,
        function_names: Option<Vec<String>>,
        class_names: Option<Vec<String>>,
        pr_title: Option<String>,
        pr_body: Option<String>,
        pr_labels: Vec<String>,
    ) -> WorkContext {
        self.build_context(
            "manual",
            files.to_vec(),
            vec![],
            vec![],
            keywords.unwrap_or_default(),
            imports.unwrap_or_default(),
            function_names.unwrap_or_default(),
            class_names.unwrap_or_default(),
            pr_title,
            pr_body,
            pr_labels,
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn build_context(
        &mut self,
        source: &str,
        changed_files: Vec<String>,
        new_files: Vec<String>,
        deleted_files: Vec<String>,
        keywords: Vec<String>,
        imports: Vec<String>,
        function_names: Vec<String>,
        class_names: Vec<String>,
        pr_title: Option<String>,
        pr_body: Option<String>,
        pr_labels: Vec<String>,
    ) -> WorkContext {
        let kw_refs: Vec<&str> = keywords.iter().map(String::as_str).collect();
        let file_refs: Vec<&str> = changed_files.iter().map(String::as_str).collect();
        let domain_match = self.detector.detect(&file_refs, &kw_refs);
        let queries = build_queries(
            domain_match.domain.as_deref(),
            &changed_files,
            &keywords,
            pr_title.as_deref(),
        );
        WorkContext {
            source: source.into(),
            changed_files,
            new_files,
            deleted_files,
            keywords,
            imports,
            function_names,
            class_names,
            detected_domain: domain_match.domain,
            domain_confidence: domain_match.confidence,
            pr_title,
            pr_body,
            pr_labels,
            search_queries: queries,
        }
    }
}

/// 4 queries: topic (dominio+5 kws), archivos (8 basenames), keywords (8),
/// PR title.
fn build_queries(
    domain: Option<&str>,
    files: &[String],
    keywords: &[String],
    pr_title: Option<&str>,
) -> Vec<String> {
    let mut queries: Vec<String> = vec![];
    match domain {
        Some(d) => {
            queries.push(format!(
                "{} {}",
                d,
                keywords
                    .iter()
                    .take(5)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(" ")
            ));
        }
        None => {
            if !keywords.is_empty() {
                queries.push(
                    keywords
                        .iter()
                        .take(5)
                        .cloned()
                        .collect::<Vec<_>>()
                        .join(" "),
                );
            }
        }
    }
    if !files.is_empty() {
        let file_terms: Vec<String> = files
            .iter()
            .take(8)
            .map(|f| {
                f.rsplit('/')
                    .next()
                    .unwrap_or(f)
                    .split('.')
                    .next()
                    .unwrap_or("")
                    .to_string()
            })
            .collect();
        queries.push(file_terms.join(" "));
    }
    if !keywords.is_empty() {
        queries.push(
            keywords
                .iter()
                .take(8)
                .cloned()
                .collect::<Vec<_>>()
                .join(" "),
        );
    }
    if let Some(t) = pr_title {
        queries.push(t.to_string());
    }
    queries
}

// ---------------------------------------------------------------------------
// Git helpers
// ---------------------------------------------------------------------------

fn run_git(args: &[&str]) -> String {
    let out = Command::new("git").args(args).output();
    match out {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(_) => String::new(),
    }
}

fn lines_of(output: &str) -> Vec<String> {
    output
        .trim()
        .split('\n')
        .filter(|l| !l.is_empty())
        .map(str::to_string)
        .collect()
}

fn get_changed_files(base_branch: &str) -> Vec<String> {
    let out = run_git(&["diff", "--name-only", base_branch]);
    if out.is_empty() {
        vec![]
    } else {
        lines_of(&out)
    }
}

fn get_new_files() -> Vec<String> {
    let untracked = lines_of(&run_git(&["ls-files", "--others", "--exclude-standard"]));
    let staged = lines_of(&run_git(&[
        "diff",
        "--name-only",
        "--diff-filter=A",
        "--cached",
    ]));
    let mut out: Vec<String> = vec![];
    for f in untracked.into_iter().chain(staged) {
        if !out.contains(&f) {
            out.push(f);
        }
    }
    out
}

fn get_deleted_files(base_branch: &str) -> Vec<String> {
    let out = run_git(&["diff", "--name-only", "--diff-filter=D", base_branch]);
    if out.is_empty() {
        vec![]
    } else {
        lines_of(&out)
    }
}

fn get_diff_content(base_branch: &str) -> String {
    run_git(&["diff", base_branch])
}

// ---------------------------------------------------------------------------
// Extracción de código
// ---------------------------------------------------------------------------

fn first_group(re: &Regex, content: &str) -> Vec<String> {
    re.captures_iter(content)
        .filter_map(|c| c.get(1).map(|m| m.as_str().to_string()))
        .collect()
}

/// Imports: sólo módulo top-level, sorted dedup.
pub fn extract_imports(content: &str) -> Vec<String> {
    let mut imports: Vec<String> = vec![];
    for pattern in [
        r"(?m)^import\s+([\w.]+)",
        r"(?m)^from\s+([\w.]+)\s+import",
        r#"(?m)^(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([\w./-]+)['\"]\)"#,
    ] {
        let re = Regex::new(pattern).unwrap();
        for m in first_group(&re, content) {
            let module = m.split('.').next().unwrap_or("").to_string();
            if !module.is_empty() && !imports.contains(&module) {
                imports.push(module);
            }
        }
    }
    imports.sort();
    imports
}

/// Funciones/métodos; excluye nombres que contienen if/else/for/while.
pub fn extract_functions(content: &str) -> Vec<String> {
    let mut funcs: Vec<String> = vec![];
    for pattern in [
        r"(?m)def\s+(\w+)\s*\(",
        r"(?m)(?:async\s+)?function\s+(\w+)\s*\(",
        r"(?m)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\*?\s*\(",
    ] {
        let re = Regex::new(pattern).unwrap();
        for m in first_group(&re, content) {
            let lower = m.to_lowercase();
            if ["if", "else", "for", "while"]
                .iter()
                .any(|kw| lower.contains(kw))
            {
                continue;
            }
            if !funcs.contains(&m) {
                funcs.push(m);
            }
        }
    }
    funcs.sort();
    funcs
}

/// Nombres de clase, sorted dedup.
pub fn extract_classes(content: &str) -> Vec<String> {
    let mut classes: Vec<String> = vec![];
    for pattern in [
        r"(?m)class\s+(\w+)",
        r"(?m)(?:export\s+)?class\s+(\w+)",
        r"(?m)(?:const|let|var)\s+(\w+)\s*=\s*class\s*\{",
    ] {
        let re = Regex::new(pattern).unwrap();
        for m in first_group(&re, content) {
            if !classes.contains(&m) {
                classes.push(m);
            }
        }
    }
    classes.sort();
    classes
}

/// Keywords por frecuencia de identificadores (top 15).
pub fn extract_keywords(content: &str) -> Vec<String> {
    let re = Regex::new(r"\b([a-zA-Z_]\w{3,})\b").unwrap();
    const NOISE: &[&str] = &[
        "const",
        "let",
        "var",
        "function",
        "return",
        "import",
        "export",
        "from",
        "class",
        "def",
        "self",
        "args",
        "kwargs",
        "true",
        "false",
        "null",
        "none",
        "undefined",
        "typeof",
        "async",
        "await",
        "try",
        "catch",
        "throw",
        "new",
        "this",
        "if",
        "else",
        "for",
        "while",
        "switch",
        "case",
        "break",
        "type",
        "interface",
        "extends",
        "implements",
        "public",
        "private",
        "protected",
        "static",
        "readonly",
        "override",
    ];
    let mut freq: Vec<(String, usize)> = vec![];
    for cap in re.captures_iter(content) {
        let ident = cap[1].to_string();
        if NOISE.contains(&ident.to_lowercase().as_str()) {
            continue;
        }
        match freq.iter_mut().find(|(k, _)| *k == ident) {
            Some((_, c)) => *c += 1,
            None => freq.push((ident, 1)),
        }
    }
    freq.sort_by_key(|(_, c)| std::cmp::Reverse(*c));
    freq.into_iter().take(15).map(|(k, _)| k).collect()
}

/// Keywords de texto natural (únicos, max 10).
pub fn extract_text_keywords(text: &str) -> Vec<String> {
    let re = Regex::new(r"\b([a-zA-Z][a-zA-Z-]{2,})\b").unwrap();
    const NOISE: &[&str] = &[
        "the", "and", "for", "with", "this", "that", "from", "have", "been", "are", "was", "not",
        "but", "what", "all", "when", "there", "can", "your", "more", "will",
    ];
    let mut out: Vec<String> = vec![];
    for cap in re.captures_iter(text) {
        let w = cap[1].to_lowercase();
        if NOISE.contains(&w.as_str()) || out.contains(&w) {
            continue;
        }
        out.push(w);
    }
    out.truncate(10);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const CODE: &str = "import os\nfrom pathlib import Path\ndef refresh(user):\n    return validate(user)\nclass AuthService:\n    pass\n";

    #[test]
    fn imports_top_level_sorted() {
        assert_eq!(extract_imports(CODE), vec!["os", "pathlib"]);
    }

    #[test]
    fn funciones_filtran_keywords_de_control() {
        let code = "def if_helper(x):\n    pass\n";
        // "if_helper" CONTIENE "if" ⇒ filtrado como Python (`kw in match`).
        assert!(extract_functions(code).is_empty());
        assert_eq!(extract_functions(CODE), vec!["refresh"]);
    }

    #[test]
    fn clases_multilinea() {
        assert_eq!(extract_classes("class A:\n\nclass B {}"), vec!["A", "B"]);
    }

    #[test]
    fn keywords_texto_unicos_max10() {
        let kws = extract_text_keywords("The auth flow and the auth token");
        assert_eq!(kws, vec!["auth", "flow", "token"]);
    }

    #[test]
    fn queries_cuatro_estrategias() {
        let q = build_queries(
            Some("auth"),
            &["src/auth.py".into()],
            &["token".into(), "jwt".into()],
            Some("Fix login"),
        );
        assert_eq!(
            q,
            vec![
                "auth token jwt".to_string(),
                "auth".to_string(),
                "token jwt".to_string(),
                "Fix login".to_string(),
            ]
        );
    }
}
