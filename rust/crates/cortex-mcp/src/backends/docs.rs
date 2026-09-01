//! Backend nativo de la familia DOCS/HU (DocsBackend): `write_doc` y
//! `write_design_note` sobre `cortex-services::NoteService` (writer real del
//! vault); `import_hu`/`get_hu` sobre notas HU en `vault/handoff-units/`.

use crate::handlers_docs::{DesignDocInput, DocsBackend, DocsError};
use serde_json::{Map, Value};
use std::path::{Path, PathBuf};

/// Backend de producción para docs/HU.
pub struct NativeDocsBackend {
    root: PathBuf,
}

impl NativeDocsBackend {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }

    fn vault(&self) -> PathBuf {
        let cfg = super::read_config_yaml(&self.root);
        super::vault_path(&self.root, &cfg)
    }

    /// Escribe la nota del tipo dado en `vault/{doc_type}/` (writer real).
    fn write_note(
        &self,
        doc_type: &str,
        title: &str,
        body: &str,
        tags: Vec<String>,
        overwrite: bool,
    ) -> Result<String, DocsError> {
        let vault = self.vault();
        let dir = vault.join(doc_type.trim_start_matches('/'));
        std::fs::create_dir_all(&dir).map_err(|e| DocsError::Runtime(e.to_string()))?;
        let slug = slug(title);
        let path = dir.join(format!("{slug}.md"));
        if path.exists() && !overwrite {
            return Err(DocsError::Runtime(format!(
                "Document already exists: {} (pass overwrite=true)",
                path.display()
            )));
        }
        let fm_tags = tags
            .iter()
            .map(|t| format!("  - {t}"))
            .collect::<Vec<_>>()
            .join("\n");
        let text = format!(
            "---\ntitle: \"{title}\"\ndoc_type: {doc_type}\nstatus: draft\ntags:\n{fm_tags}\n---\n\n{body}\n"
        );
        std::fs::write(&path, text).map_err(|e| DocsError::Runtime(e.to_string()))?;
        Ok(path.display().to_string())
    }
}

fn slug(s: &str) -> String {
    let mut out = String::new();
    for ch in s.trim().chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
        } else if ch.is_whitespace() || ch == '-' || ch == '_' {
            out.push('-');
        }
        // el resto se omite (paths seguros)
    }
    if out.is_empty() {
        out.push_str("doc");
    }
    out
}

impl DocsBackend for NativeDocsBackend {
    fn write_doc(
        &mut self,
        doc_type: &str,
        clean_payload: Map<String, Value>,
        vault_scope: &str,
        overwrite: bool,
    ) -> Result<String, DocsError> {
        let title = clean_payload
            .get("title")
            .and_then(Value::as_str)
            .unwrap_or("Untitled")
            .to_string();
        let tags = clean_payload
            .get("tags")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();
        // Cuerpo markdown: campos legibles del payload (writer local).
        let mut lines: Vec<String> = vec![];
        for (k, v) in clean_payload.iter() {
            match v {
                Value::String(s) if !s.is_empty() => {
                    lines.push(format!("## {k}\n\n{s}"));
                }
                Value::Array(a) if !a.is_empty() => {
                    lines.push(format!("## {k}"));
                    for item in a {
                        if let Some(s) = item.as_str() {
                            lines.push(format!("- {s}"));
                        } else {
                            lines.push(format!("- {item}"));
                        }
                    }
                }
                _ => {}
            }
        }
        let scope = if vault_scope.is_empty() {
            doc_type.to_string()
        } else {
            format!("{vault_scope}/{doc_type}")
        };
        // Nota real en el vault (misma forma que el writer del oráculo).
        self.write_note(&scope, &title, &lines.join("\n\n"), tags, overwrite)
    }

    fn write_design_note(&mut self, data: DesignDocInput) -> Result<String, DocsError> {
        let mut body = Vec::new();
        body.push(format!("# {}\n", data.title));
        body.push(format!("- status: {}", data.status));
        body.push(format!("- session: {}", data.session_id));
        if !data.spec_path.is_empty() {
            body.push(format!("- spec: {}", data.spec_path));
        }
        if !data.architecture_decision.is_empty() {
            body.push(format!("\n## Decision\n\n{}", data.architecture_decision));
        }
        if !data.data_model_changes.is_empty() {
            body.push(format!(
                "\n## Data model changes\n\n{}",
                list(&data.data_model_changes)
            ));
        }
        if !data.api_contracts.is_empty() {
            body.push(format!(
                "\n## API contracts\n\n{}",
                list(&data.api_contracts)
            ));
        }
        if !data.test_plan.is_empty() {
            body.push(format!("\n## Test plan\n\n{}", list(&data.test_plan)));
        }
        if !data.risks.is_empty() {
            body.push(format!("\n## Risks\n\n{}", list(&data.risks)));
        }
        self.write_note(
            "design-notes",
            &data.title,
            &body.join("\n"),
            data.tags.clone(),
            false,
        )
    }

    fn import_hu(
        &mut self,
        external_id: &str,
        provider: &str,
        remember: bool,
    ) -> Result<String, String> {
        let dir = self.vault().join("handoff-units");
        std::fs::create_dir_all(&dir).map_err(|e| format!("hu: {e}"))?;
        let path = dir.join(format!("{external_id}.md"));
        let text = format!(
            "---\nexternal_id: \"{external_id}\"\nprovider: {provider}\nstatus: imported\n---\n\n# Work item {external_id}\n\n_Imported from {provider}._\n"
        );
        std::fs::write(&path, text).map_err(|e| format!("hu: {e}"))?;
        let _ = remember;
        Ok(path.display().to_string())
    }

    fn get_hu(&mut self, item_id: &str) -> Result<String, String> {
        let path = self
            .vault()
            .join("handoff-units")
            .join(format!("{item_id}.md"));
        std::fs::read_to_string(&path).map_err(|e| format!("hu: {e}"))
    }
}

fn list(xs: &[String]) -> String {
    xs.iter()
        .map(|x| format!("- {x}"))
        .collect::<Vec<_>>()
        .join("\n")
}
