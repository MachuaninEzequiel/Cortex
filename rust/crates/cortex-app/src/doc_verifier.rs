//! Puerto de `cortex.doc_verifier` (P12A-4): detecta si un PR trae docs de
//! agente dentro del vault. Modo local (git diff) y modo CI (lista de files).
//!
//! Contrato de clasificación (Ola 4 fix): `vault_files` es la UNIÓN; las tres
//! particiones new/modified/deleted son mutuamente excluyentes y cubren todo
//! `vault_files`; los paths fuera del vault se descartan.
//!
//! Divergencias documentadas:
//! - El mensaje de error git replica a Python byte-a-byte:
//!   `check_output` sin stderr capturado ⇒ `CalledProcessError.stderr is None`
//!   ⇒ el mensaje ES literalmente "git status failed: None".

use std::path::PathBuf;
use std::process::Command;

use serde_json::json;

#[derive(Debug, Clone, Default, PartialEq)]
pub struct DocVerificationResult {
    pub has_agent_docs: bool,
    pub vault_files: Vec<String>,
    pub new_files: Vec<String>,
    pub modified_files: Vec<String>,
    pub deleted_files: Vec<String>,
    pub valid_files: Vec<String>,
    pub invalid_files: Vec<String>,
    pub errors: Vec<String>,
}

impl DocVerificationResult {
    pub fn total_vault_files(&self) -> usize {
        self.vault_files.len()
    }

    pub fn total_changes(&self) -> usize {
        self.new_files.len() + self.modified_files.len() + self.deleted_files.len()
    }

    /// `to_dict` con el orden de claves de Python.
    pub fn to_dict(&self) -> serde_json::Value {
        json!({
            "has_agent_docs": self.has_agent_docs,
            "vault_files": self.vault_files,
            "new_files": self.new_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "valid_files": self.valid_files,
            "invalid_files": self.invalid_files,
            "errors": self.errors,
            "total_vault_files": self.total_vault_files(),
            "total_changes": self.total_changes(),
        })
    }

    /// `to_json` (json.dumps(to_dict(), indent=2)): emisión MANUAL para
    /// preservar el ORDEN DE INSERCIÓN de las claves (serde_json ordena
    /// alfabético por defecto y eso rompería la paridad byte-a-byte).
    pub fn to_json(&self) -> String {
        enum V {
            B(bool),
            N(usize),
            L(Vec<String>),
        }
        let campos: Vec<(&str, V)> = vec![
            ("has_agent_docs", V::B(self.has_agent_docs)),
            ("vault_files", V::L(self.vault_files.clone())),
            ("new_files", V::L(self.new_files.clone())),
            ("modified_files", V::L(self.modified_files.clone())),
            ("deleted_files", V::L(self.deleted_files.clone())),
            ("valid_files", V::L(self.valid_files.clone())),
            ("invalid_files", V::L(self.invalid_files.clone())),
            ("errors", V::L(self.errors.clone())),
            ("total_vault_files", V::N(self.total_vault_files())),
            ("total_changes", V::N(self.total_changes())),
        ];
        let esc = |s: &str| json_str(s);
        let mut out = String::from("{\n");
        for (i, (k, v)) in campos.iter().enumerate() {
            if i > 0 {
                out.push_str(",\n");
            }
            out.push_str("  ");
            out.push_str(&esc(k));
            out.push_str(": ");
            match v {
                V::B(b) => out.push_str(if *b { "true" } else { "false" }),
                V::N(n) => out.push_str(&n.to_string()),
                V::L(items) => {
                    if items.is_empty() {
                        out.push_str("[]");
                    } else {
                        out.push('[');
                        for (j, item) in items.iter().enumerate() {
                            if j > 0 {
                                out.push(',');
                            }
                            out.push('\n');
                            out.push_str("    ");
                            out.push_str(&esc(item));
                        }
                        out.push('\n');
                        out.push_str("  ]");
                    }
                }
            }
        }
        out.push_str("\n}");
        out
    }
}

fn json_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub struct DocVerifier {
    pub vault_path: PathBuf,
    pub root: PathBuf,
}

/// Partición (new, modified, deleted) del diff.
type DiffStatus = (Vec<String>, Vec<String>, Vec<String>);

impl DocVerifier {
    pub fn new(vault_path: impl Into<PathBuf>) -> Self {
        Self::with_root(vault_path, None)
    }

    pub fn with_root(vault_path: impl Into<PathBuf>, root: Option<PathBuf>) -> Self {
        let vault_path = vault_path.into();
        let root = root.unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
        // Si vault es absoluto, root pasa a ser su padre.
        let root = if vault_path.is_absolute() {
            vault_path.parent().unwrap_or(&root).to_path_buf()
        } else {
            root
        };
        Self { vault_path, root }
    }

    pub fn verify_from_diff(
        &self,
        base_branch: &str,
        changed_files: Option<&[String]>,
    ) -> DocVerificationResult {
        let mut result = DocVerificationResult::default();

        let Some(vault_rel) = self.vault_relative() else {
            result.errors.push(format!(
                "Vault directory not found: {}",
                self.vault_path.display()
            ));
            return result;
        };

        let (new, modified, deleted) = match changed_files {
            None => match self.git_diff_status(base_branch) {
                Ok(t) => t,
                Err(()) => {
                    // Python: check_output no captura stderr ⇒ exc.stderr=None.
                    result.errors.push("git status failed: None".to_string());
                    return result;
                }
            },
            Some(files) => (Vec::new(), files.to_vec(), Vec::new()),
        };

        // Prefijo estilo str: "vault/" — Python concatena str paths.
        let prefix = format!("{vault_rel}/");
        for (fpath, bucket_new, bucket_mod, bucket_del) in [
            (&new, true, false, false),
            (&modified, false, true, false),
            (&deleted, false, false, true),
        ] {
            for f in fpath {
                let Some(rel) = vault_relative_md(f, &prefix) else {
                    continue;
                };
                if bucket_new {
                    result.new_files.push(rel.clone());
                } else if bucket_mod {
                    result.modified_files.push(rel.clone());
                } else if bucket_del {
                    result.deleted_files.push(rel.clone());
                }
                result.vault_files.push(rel);
            }
        }

        result.has_agent_docs = !result.new_files.is_empty() || !result.modified_files.is_empty();
        result
    }

    pub fn verify_from_list(&self, changed_files: &[String]) -> DocVerificationResult {
        self.verify_from_diff("main", Some(changed_files))
    }

    fn vault_relative(&self) -> Option<String> {
        self.vault_path
            .strip_prefix(&self.root)
            .ok()
            .map(|p| p.to_string_lossy().replace('\\', "/"))
    }

    /// `_git_diff_status`: check_output(["git","diff","--name-status",base,"--"]).
    /// Error (rc != 0 o git ausente) ⇒ Err(()).
    fn git_diff_status(&self, base_branch: &str) -> Result<DiffStatus, ()> {
        let out = Command::new("git")
            .args(["diff", "--name-status", base_branch, "--"])
            .current_dir(&self.root)
            .output()
            .map_err(|_| ())?;
        if !out.status.success() {
            return Err(());
        }
        let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
        let mut new = Vec::new();
        let mut modified = Vec::new();
        let mut deleted = Vec::new();
        for line in text.split('\n') {
            if line.is_empty() {
                continue;
            }
            let Some((status, filepath)) = line.split_once('\t') else {
                continue;
            };
            match status {
                "A" => new.push(filepath.to_string()),
                "M" | "R" | "C" => modified.push(filepath.to_string()),
                "D" => deleted.push(filepath.to_string()),
                _ => {}
            }
        }
        Ok((new, modified, deleted))
    }
}

/// `_vault_relative_md`: vault-relative sólo para .md bajo el prefijo.
fn vault_relative_md(fpath: &str, prefix: &str) -> Option<String> {
    let rel = fpath.strip_prefix(prefix)?;
    if !rel.ends_with(".md") {
        return None;
    }
    Some(rel.to_string())
}
