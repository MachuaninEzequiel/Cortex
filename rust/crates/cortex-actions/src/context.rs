//! Puerto de `cortex/action_engine/context.py` (Obra 05 Fase B).
//!
//! Regla dura #1 del contrato: toda acción delega en su servicio. El
//! `ActionContext` agrupa las dependencias del catálogo. La carga perezosa
//! de servicios pesados (ChromaDB/ONNX) no existe acá: las ejecuciones que
//! los requieren devuelven fallo explícito hasta su fase nativa (P11/P12);
//! precondiciones y dry-runs —que es lo que gatea la paridad de `next`—
//! son 100% nativos y deterministas.

use std::path::{Path, PathBuf};

/// Descubrimiento de layout mínimo (espejo de WorkspaceLayout.discover,
/// casos 1–3 + bootstrap) para resolver workspace_root desde un directorio.
/// Descubrimiento de layout mínimo (espejo de WorkspaceLayout.discover,
/// casos 1–3 + bootstrap). Devuelve (repo_root, es_layout_nuevo).
fn discover_workspace_root(start: &Path) -> (PathBuf, bool) {
    let mut current = Some(start);
    while let Some(dir) = current {
        if dir.file_name().map(|n| n == ".cortex").unwrap_or(false) {
            current = dir.parent();
            continue;
        }
        // Caso 1: .cortex/workspace.yaml con layout_version >= 2
        let ws_yaml = dir.join(".cortex").join("workspace.yaml");
        if ws_yaml.is_file() {
            if let Ok(text) = std::fs::read_to_string(&ws_yaml) {
                let parsed: Result<serde_yaml::Value, _> = serde_yaml::from_str(&text);
                if let Ok(v) = parsed {
                    let version = v
                        .get("layout_version")
                        .and_then(|x| x.as_i64())
                        .unwrap_or(1);
                    if version >= 2 {
                        return (dir.to_path_buf(), true);
                    }
                }
            }
        }
        // Caso 2: .cortex/config.yaml (solo si NO hay config.yaml raíz)
        let cortex_config = dir.join(".cortex").join("config.yaml");
        let root_config = dir.join("config.yaml");
        if cortex_config.is_file() && !root_config.is_file() {
            return (dir.to_path_buf(), true);
        }
        // Caso 3: legacy — config.yaml en raíz (o .cortex/ + .git/)
        if root_config.is_file() || (dir.join(".cortex").is_dir() && dir.join(".git").is_dir()) {
            return (dir.to_path_buf(), false);
        }
        current = dir.parent();
    }
    // Caso 4: bootstrap — force_new como en Python.
    (start.to_path_buf(), true)
}

/// Contexto de servicios para las acciones del catálogo.
#[derive(Clone, Debug)]
pub struct ActionContext {
    /// Raíz del repositorio/proyecto descubierta.
    pub repo_root: PathBuf,
    /// `layout.workspace_root`: raíz en legacy; `repo/.cortex` en nuevo.
    pub workspace_root: PathBuf,
}

impl ActionContext {
    /// `ActionContext.from_project_root`.
    pub fn from_project_root(project_root: Option<&Path>) -> Self {
        let start = match project_root {
            Some(p) => p.to_path_buf(),
            None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
        };
        let (repo_root, new_layout) = discover_workspace_root(&start);
        let workspace_root = if new_layout {
            repo_root.join(".cortex")
        } else {
            repo_root.clone()
        };
        Self {
            repo_root,
            workspace_root,
        }
    }

    /// Directorio ``.cortex`` real (workspace_root ya lo es en layout nuevo;
    /// en legacy workspace_root == repo_root, ahí sí se agrega el nivel).
    pub fn dot_cortex(&self) -> PathBuf {
        if self
            .workspace_root
            .file_name()
            .map(|n| n == ".cortex")
            .unwrap_or(false)
        {
            self.workspace_root.clone()
        } else {
            self.workspace_root.join(".cortex")
        }
    }

    pub fn config_path(&self) -> PathBuf {
        self.workspace_root.join("config.yaml")
    }

    pub fn config_existe(&self) -> bool {
        self.config_path().is_file()
    }

    pub fn vault_path(&self) -> PathBuf {
        self.workspace_root.join("vault")
    }

    /// `_sesiones_abiertas`: sesiones con status=open (errores ⇒ vacío).
    pub fn sesiones_abiertas(&self) -> Vec<cortex_app::session::SessionRecord> {
        let storage = cortex_app::session::SessionStorage::new(self.dot_cortex().join("sessions"));
        match storage.list_all() {
            Ok(records) => records
                .into_iter()
                .filter(|r| r.status.as_str() == "open")
                .collect(),
            Err(_) => Vec::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_fixture_layout() {
        // config.yaml en raíz (fixture canónico) ⇒ legacy: ws = raíz.
        let base = std::env::temp_dir().join(format!(
            "ctx-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(base.join("vault")).unwrap();
        std::fs::write(base.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();

        let ctx = ActionContext::from_project_root(Some(&base));
        assert_eq!(ctx.workspace_root, base);
        assert_eq!(ctx.dot_cortex(), base.join(".cortex"));
        assert_eq!(ctx.vault_path(), base.join("vault"));
        assert!(ctx.config_existe());
        std::fs::remove_dir_all(base).ok();
    }

    #[test]
    fn new_layout_ws_es_dot_cortex() {
        let base = std::env::temp_dir().join(format!(
            "ctx-new-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(base.join(".cortex")).unwrap();
        std::fs::write(base.join(".cortex").join("config.yaml"), "x: 1\n").unwrap();

        let ctx = ActionContext::from_project_root(Some(&base));
        assert_eq!(ctx.dot_cortex(), base.join(".cortex"));
        assert!(ctx.config_existe());
        std::fs::remove_dir_all(base).ok();
    }
}
