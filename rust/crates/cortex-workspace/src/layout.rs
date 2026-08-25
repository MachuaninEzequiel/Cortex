//! Porteo de `cortex/workspace/layout.py` — resolución central de rutas.
//!
//! `WorkspaceLayout` es la fuente única de verdad de cada ruta del runtime.
//! Soporta dos modos (nuevo ≥ layout_version 2 y legacy) y descubre la raíz
//! caminando hacia arriba desde cualquier directorio (`discover`).
//!
//! Precedencia de `discover` (primera coincidencia gana, por cada padre
//! ascendente, saltando directorios llamados `.cortex`):
//! 1. `<padre>/.cortex/workspace.yaml` con `layout_version >= 2` → nuevo.
//!    (YAML inválido ⇒ cae al caso siguiente, igual que Python.)
//! 2. `<padre>/.cortex/config.yaml` SIN `config.yaml` en la raíz → nuevo.
//! 3. `config.yaml` en la raíz, o (`.cortex/` Y `.git/` presentes) → legacy.
//! 4. Bootstrap: raíz git más cercana o `start` → nuevo forzado.
//!
//! Paridad: tests/unit/workspace/test_layout.py es LA especificación; el
//! oráculo P12B-1 congela todas las rutas resueltas sobre fixtures.

#![forbid(unsafe_code)]

use std::path::{Component, Path, PathBuf};

/// Resolución no estricta equivalente a `Path.resolve()` de Python para
/// fixtures sin symlinks: canonicaliza si puede; si no, absolutiza y
/// normaliza `.`/`..` léxicamente.
pub fn resolve_lexical(p: &Path) -> PathBuf {
    if let Ok(c) = std::fs::canonicalize(p) {
        return c;
    }
    let abs = if p.is_absolute() {
        p.to_path_buf()
    } else {
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("/"))
            .join(p)
    };
    normalize_lexical(&abs)
}

fn normalize_lexical(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for comp in p.components() {
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            c => out.push(c.as_os_str()),
        }
    }
    out
}

/// Camina hacia arriba buscando el `.git` más cercano (`_find_git_root`).
pub fn find_git_root(start: &Path) -> Option<PathBuf> {
    let current = resolve_lexical(start);
    for parent in current.ancestors() {
        if parent.join(".git").is_dir() {
            return Some(parent.to_path_buf());
        }
    }
    None
}

/// Resolvedor central de rutas del workspace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkspaceLayout {
    pub repo_root: PathBuf,
    pub workspace_root: PathBuf,
    pub is_legacy_layout: bool,
    pub is_new_layout: bool,
}

impl WorkspaceLayout {
    /// Walk-up discovery (ver docs del módulo para la precedencia).
    pub fn discover(start: &Path) -> WorkspaceLayout {
        let current = resolve_lexical(start);

        for parent in current.ancestors() {
            // Los directorios ".cortex" son parte del proyecto, no raíces.
            if parent.file_name() == Some(std::ffi::OsStr::new(".cortex")) {
                continue;
            }

            // Caso 1: workspace.yaml con layout_version >= 2.
            let ws_yaml = parent.join(".cortex").join("workspace.yaml");
            if ws_yaml.is_file() {
                let forced = std::fs::read_to_string(&ws_yaml)
                    .ok()
                    .and_then(|text| serde_yaml::from_str::<serde_yaml::Value>(&text).ok())
                    .and_then(|data| data.get("layout_version").and_then(|v| v.as_i64()))
                    .map(|version| version >= 2)
                    .unwrap_or(false);
                if forced {
                    return Self::from_repo_root(parent);
                }
                // YAML inválido o versión < 2 ⇒ cae a los casos siguientes.
            }

            // Caso 2: .cortex/config.yaml sin config.yaml en la raíz → nuevo.
            let cortex_config = parent.join(".cortex").join("config.yaml");
            if cortex_config.is_file() && !parent.join("config.yaml").is_file() {
                return Self::from_repo_root(parent);
            }
            // Ambos config.yaml existen ⇒ legacy: sigue al caso 3.

            // Caso 3: layout legacy.
            let root_config = parent.join("config.yaml");
            let git_dir = parent.join(".git");
            let cortex_dir_exists = parent.join(".cortex").is_dir();
            if root_config.is_file() || (cortex_dir_exists && git_dir.is_dir()) {
                return Self::from_legacy_root(parent);
            }
        }

        // Caso 4: bootstrap — sin proyecto.
        let repo_root = find_git_root(start).unwrap_or_else(|| resolve_lexical(start));
        Self::from_repo_root(&repo_root)
    }

    /// Nuevo layout enraizado en `repo_root`.
    pub fn from_repo_root(repo_root: &Path) -> WorkspaceLayout {
        let repo = resolve_lexical(repo_root);
        let ws = repo.join(".cortex");
        WorkspaceLayout {
            repo_root: repo,
            workspace_root: ws,
            is_legacy_layout: false,
            is_new_layout: true,
        }
    }

    /// Layout legacy enraizado en `repo_root`: workspace_root == repo_root.
    fn from_legacy_root(repo_root: &Path) -> WorkspaceLayout {
        let repo = resolve_lexical(repo_root);
        WorkspaceLayout {
            workspace_root: repo.clone(),
            repo_root: repo,
            is_legacy_layout: true,
            is_new_layout: false,
        }
    }

    // ── Config ──────────────────────────────────────────────────────────

    pub fn config_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join("config.yaml")
        } else {
            self.workspace_root.join("config.yaml")
        }
    }

    pub fn org_config_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("org.yaml")
        } else {
            self.workspace_root.join("org.yaml")
        }
    }

    // ── Vaults ──────────────────────────────────────────────────────────

    pub fn vault_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join("vault")
        } else {
            self.workspace_root.join("vault")
        }
    }

    pub fn enterprise_vault_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join("vault-enterprise")
        } else {
            self.workspace_root.join("vault-enterprise")
        }
    }

    // ── Memoria ─────────────────────────────────────────────────────────

    pub fn episodic_memory_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".memory")
        } else {
            self.workspace_root.join("memory")
        }
    }

    pub fn enterprise_memory_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".memory").join("enterprise")
        } else {
            self.workspace_root.join("enterprise-memory")
        }
    }

    // ── Assets del workspace (ambos layouts bajo .cortex/) ──────────────

    pub fn skills_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("skills")
        } else {
            self.workspace_root.join("skills")
        }
    }

    pub fn sessions_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("sessions")
        } else {
            self.workspace_root.join("sessions")
        }
    }

    pub fn subagents_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("subagents")
        } else {
            self.workspace_root.join("subagents")
        }
    }

    pub fn agent_guidelines_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("AGENT.md")
        } else {
            self.workspace_root.join("AGENT.md")
        }
    }

    pub fn system_prompt_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("system-prompt.md")
        } else {
            self.workspace_root.join("system-prompt.md")
        }
    }

    pub fn workspace_yaml_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("workspace.yaml")
        } else {
            self.workspace_root.join("workspace.yaml")
        }
    }

    // ── WebGraph (ambos layouts bajo .cortex/webgraph/) ─────────────────

    pub fn webgraph_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("webgraph")
        } else {
            self.workspace_root.join("webgraph")
        }
    }

    pub fn webgraph_config_path(&self) -> PathBuf {
        self.webgraph_dir().join("config.yaml")
    }

    pub fn webgraph_workspace_path(&self) -> PathBuf {
        self.webgraph_dir().join("workspace.yaml")
    }

    pub fn webgraph_cache_dir(&self) -> PathBuf {
        self.webgraph_dir().join("cache")
    }

    // ── Runtime ─────────────────────────────────────────────────────────

    pub fn logs_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join(".cortex").join("logs")
        } else {
            self.workspace_root.join("logs")
        }
    }

    pub fn scripts_dir(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join("scripts")
        } else {
            self.workspace_root.join("scripts")
        }
    }

    // ── CI/CD (fuera de .cortex) ────────────────────────────────────────

    pub fn workflows_dir(&self) -> PathBuf {
        self.repo_root.join(".github").join("workflows")
    }

    // ── Promoción enterprise ────────────────────────────────────────────

    pub fn promotion_records_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root
                .join("vault-enterprise")
                .join(".cortex")
                .join("promotion")
                .join("records.jsonl")
        } else {
            self.enterprise_vault_path()
                .join("promotion")
                .join("records.jsonl")
        }
    }

    pub fn promotion_dir(&self) -> PathBuf {
        self.promotion_records_path()
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_default()
    }

    // ── Índice / contexto ───────────────────────────────────────────────

    pub fn context_md_path(&self) -> PathBuf {
        if self.is_legacy_layout {
            self.repo_root.join("CONTEXT.md")
        } else {
            self.workspace_root.join("CONTEXT.md")
        }
    }

    pub fn vault_index_path(&self) -> PathBuf {
        self.vault_path().join(".cortex_index.json")
    }

    // ── Git ─────────────────────────────────────────────────────────────

    pub fn gitignore_path(&self) -> PathBuf {
        self.repo_root.join(".gitignore")
    }

    // ── Helpers ─────────────────────────────────────────────────────────

    /// Resuelve un path relativo contra `workspace_root`; los absolutos
    /// pasan intactos (normalizados).
    pub fn resolve_workspace_relative(&self, value: &Path) -> PathBuf {
        if value.is_absolute() {
            resolve_lexical(value)
        } else {
            resolve_lexical(&self.workspace_root.join(value))
        }
    }

    // ── Compatibilidad legacy (siempre apuntan a la raíz del repo) ──────

    pub fn legacy_config_path(&self) -> PathBuf {
        self.repo_root.join("config.yaml")
    }

    pub fn legacy_vault_path(&self) -> PathBuf {
        self.repo_root.join("vault")
    }

    pub fn legacy_memory_path(&self) -> PathBuf {
        self.repo_root.join(".memory")
    }

    pub fn legacy_org_config_path(&self) -> PathBuf {
        self.repo_root.join(".cortex").join("org.yaml")
    }

    /// Espejo exacto de `WorkspaceLayout.__repr__` de Python.
    pub fn repr(&self) -> String {
        let mode = if self.is_legacy_layout {
            "legacy"
        } else {
            "new"
        };
        format!(
            "WorkspaceLayout(repo_root=PosixPath('{}'), \
             workspace_root=PosixPath('{}'), mode={mode})",
            self.repo_root.display(),
            self.workspace_root.display()
        )
    }
}
