//! Puerto de `cortex.doc_validator` (P12A-4): validación de docs generadas.
//!
//! Checks: frontmatter YAML (`---`), title, date/created, wikilinks
//! `[[nota]]`, embeds rotos `![[nota]]`.
//!
//! Divergencia documentada: el mensaje de YAML inválido incluye el texto del
//! parser (PyYAML vs serde_yaml) ⇒ NO es contrato; los gates lo normalizan.

use std::path::{Path, PathBuf};

use regex::RegexBuilder;
use serde_json::json;

#[derive(Debug, Clone, PartialEq)]
pub struct DocValidationIssue {
    pub file: String,
    pub field: String,
    pub message: String,
    pub severity: Severity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

impl Severity {
    pub fn value(self) -> &'static str {
        match self {
            Self::Error => "error",
            Self::Warning => "warning",
            Self::Info => "info",
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct DocValidationResult {
    pub is_valid: bool,
    pub issues: Vec<DocValidationIssue>,
    /// Propiedades del frontmatter (yaml crudo).
    pub properties: std::collections::BTreeMap<String, serde_yaml::Value>,
    pub wikilinks: Vec<String>,
    pub embeds: Vec<String>,
}

impl DocValidationResult {
    pub fn errors(&self) -> Vec<&DocValidationIssue> {
        self.issues
            .iter()
            .filter(|i| i.severity == Severity::Error)
            .collect()
    }

    pub fn warnings(&self) -> Vec<&DocValidationIssue> {
        self.issues
            .iter()
            .filter(|i| i.severity == Severity::Warning)
            .collect()
    }

    /// `to_dict` (orden de claves = Python) como serde_json::Value.
    pub fn to_dict(&self) -> serde_json::Value {
        let props: serde_json::Map<String, serde_json::Value> = self
            .properties
            .iter()
            .map(|(k, v)| (k.clone(), yaml_a_json(v)))
            .collect();
        json!({
            "is_valid": self.is_valid,
            "error_count": self.errors().len(),
            "warning_count": self.warnings().len(),
            "properties": props,
            "wikilinks": self.wikilinks,
            "embeds": self.embeds,
            "issues": self.issues.iter().map(|i| json!({
                "file": i.file,
                "field": i.field,
                "message": i.message,
                "severity": i.severity.value(),
            })).collect::<Vec<_>>(),
        })
    }
}

/// Conversión mínima yaml→JSON para to_dict (escalares y listas).
fn yaml_a_json(v: &serde_yaml::Value) -> serde_json::Value {
    match v {
        serde_yaml::Value::Null => serde_json::Value::Null,
        serde_yaml::Value::Bool(b) => serde_json::Value::Bool(*b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                json!(i)
            } else {
                json!(n.as_f64().unwrap_or(0.0))
            }
        }
        serde_yaml::Value::String(s) => json!(s),
        serde_yaml::Value::Sequence(items) => {
            json!(items.iter().map(yaml_a_json).collect::<Vec<_>>())
        }
        serde_yaml::Value::Mapping(m) => {
            let mut out = serde_json::Map::new();
            for (k, val) in m {
                let key = match k {
                    serde_yaml::Value::String(s) => s.clone(),
                    other => serde_yaml::to_string(other)
                        .unwrap_or_default()
                        .trim()
                        .into(),
                };
                out.insert(key, yaml_a_json(val));
            }
            serde_json::Value::Object(out)
        }
        serde_yaml::Value::Tagged(t) => yaml_a_json(&t.value),
    }
}

pub struct DocValidator {
    pub vault_path: PathBuf,
}

fn wiki_re(pattern: &str) -> regex::Regex {
    RegexBuilder::new(pattern).build().expect("regex válida")
}

/// Limpieza de link/embed: parte display | #ancla ^bloque y trim.
fn limpiar_target(raw: &str) -> String {
    raw.split('|')
        .next()
        .unwrap_or("")
        .split('#')
        .next()
        .unwrap_or("")
        .split('^')
        .next()
        .unwrap_or("")
        .trim()
        .to_string()
}

impl DocValidator {
    pub fn new(vault_path: impl Into<PathBuf>) -> Self {
        Self {
            vault_path: vault_path.into(),
        }
    }

    pub fn validate_file(&self, filepath: &Path) -> DocValidationResult {
        let path = filepath;
        let mut result = DocValidationResult::default();

        if !path.exists() {
            result.is_valid = false;
            result.issues.push(DocValidationIssue {
                file: path.display().to_string(),
                field: "file".into(),
                message: "File does not exist".into(),
                severity: Severity::Error,
            });
            return result;
        }
        if !path.display().to_string().ends_with(".md") {
            result.issues.push(DocValidationIssue {
                file: path.display().to_string(),
                field: "file".into(),
                message: "Not a markdown file".into(),
                severity: Severity::Warning,
            });
            return result;
        }

        let content = match std::fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                result.is_valid = false;
                result.issues.push(DocValidationIssue {
                    file: path.display().to_string(),
                    field: "file".into(),
                    message: format!("read error: {e}"),
                    severity: Severity::Error,
                });
                return result;
            }
        };
        // rel = relativo al vault SI el string del path empieza con el string
        // del vault (léxico, igual que Python); si no, el path completo.
        let ps = path.display().to_string();
        let vs = self.vault_path.display().to_string();
        let rel = if ps.starts_with(&vs) {
            let rest = &ps[vs.len()..];
            rest.strip_prefix('/').unwrap_or(rest).to_string()
        } else {
            ps
        };

        self.parse_frontmatter(&content, &rel, &mut result);
        result.wikilinks = self.extract_wikilinks(&content);
        result.embeds = self.extract_embeds(&content);
        self.check_embeds(&mut result, &rel);
        result.is_valid = result.errors().is_empty();
        result
    }

    pub fn validate_batch(&self, filepaths: &[PathBuf]) -> Vec<DocValidationResult> {
        filepaths.iter().map(|fp| self.validate_file(fp)).collect()
    }

    fn parse_frontmatter(&self, content: &str, rel: &str, result: &mut DocValidationResult) {
        let re = wiki_re(r"(?s)^---\s*\n(.*?)\n---");
        let Some(caps) = re.captures(content) else {
            result.issues.push(DocValidationIssue {
                file: rel.into(),
                field: "frontmatter".into(),
                message: "No YAML frontmatter found (expected --- delimiters)".into(),
                severity: Severity::Warning,
            });
            return;
        };
        let raw = caps.get(1).map(|m| m.as_str()).unwrap_or("");
        let parsed: Result<serde_yaml::Value, _> = serde_yaml::from_str(raw);
        let fm = match parsed {
            Ok(v) => v,
            Err(e) => {
                result.issues.push(DocValidationIssue {
                    file: rel.into(),
                    field: "frontmatter".into(),
                    message: format!("Invalid YAML: {e}"),
                    severity: Severity::Error,
                });
                return;
            }
        };
        if let serde_yaml::Value::Mapping(map) = fm {
            for (k, v) in map {
                let key = match k {
                    serde_yaml::Value::String(s) => s,
                    other => serde_yaml::to_string(&other)
                        .unwrap_or_default()
                        .trim()
                        .into(),
                };
                result.properties.insert(key, v);
            }
        }
        let get_str = |k: &str| -> Option<String> {
            result.properties.get(k).and_then(|v| match v {
                serde_yaml::Value::String(s) => Some(s.clone()),
                serde_yaml::Value::Number(n) => Some(n.to_string()),
                serde_yaml::Value::Bool(b) => Some(b.to_string()),
                _ => None,
            })
        };
        if get_str("title").map(|t| t.is_empty()).unwrap_or(true) {
            result.issues.push(DocValidationIssue {
                file: rel.into(),
                field: "title".into(),
                message: "Missing 'title' property in frontmatter".into(),
                severity: Severity::Warning,
            });
        }
        let tiene_fecha =
            result.properties.contains_key("date") || result.properties.contains_key("created");
        if !tiene_fecha {
            result.issues.push(DocValidationIssue {
                file: rel.into(),
                field: "date".into(),
                message: "Missing 'date' or 'created' property in frontmatter".into(),
                severity: Severity::Info,
            });
        }
    }

    /// `_extract_wikilinks`: quita embeds primero para evitar falsos positivos.
    pub fn extract_wikilinks(&self, content: &str) -> Vec<String> {
        let embed_re = wiki_re(r"!\[\[([^\]]+)\]\]");
        let clean = embed_re.replace_all(content, "");
        let link_re = wiki_re(r"\[\[([^\]]+)\]\]");
        link_re
            .captures_iter(&clean)
            .filter_map(|c| c.get(1).map(|m| limpiar_target(m.as_str())))
            .collect()
    }

    pub fn extract_embeds(&self, content: &str) -> Vec<String> {
        let embed_re = wiki_re(r"!\[\[([^\]]+)\]\]");
        embed_re
            .captures_iter(content)
            .filter_map(|c| c.get(1).map(|m| limpiar_target(m.as_str())))
            .collect()
    }

    fn check_embeds(&self, result: &mut DocValidationResult, current_file: &str) {
        for embed in &result.embeds {
            let target = self.vault_path.join(embed);
            let con_md = target.with_extension("md");
            if !target.exists() && !con_md.exists() {
                result.issues.push(DocValidationIssue {
                    file: current_file.into(),
                    field: "embed".into(),
                    message: format!("Embed target not found: {embed}"),
                    severity: Severity::Warning,
                });
            }
        }
    }
}
