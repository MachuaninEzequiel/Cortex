//! Backends NATIVOS de producción para el server MCP (Cierre T1/P12):
//! Sesiones, Search/Context, Spec y Finish, cableados a los servicios
//! nativos (cortex-app, cortex-services…). Los handlers ya formatean las
//! salidas con el formato del oráculo; estos tipos solo proveen datos.
//!
//! Antes (server.rs `new()`): todos los backends en `None` ⇒ "ruteada pero
//! su backend aún no es nativo". El binario inyecta estos impls.

pub mod autopilot;
pub mod docs;
pub mod finish;
pub mod search;
pub mod sessions;
pub mod spec;

/// Raíz del repositorio resuelta (cwd) — el MCP corre con cwd del proyecto
/// (`cwd: "${cwd}"` en mcp.json). Mismo descubrimiento que el CLI.
pub fn repo_root() -> std::path::PathBuf {
    let cwd = std::env::current_dir().unwrap_or_default();
    cortex_workspace::WorkspaceLayout::discover(&cwd).repo_root
}

/// Config YAML del proyecto (defaults del oráculo si falta la clave).
pub fn read_config_yaml(root: &std::path::Path) -> serde_yaml::Value {
    let path = root.join(".cortex").join("config.yaml");
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|t| serde_yaml::from_str(&t).ok())
        .unwrap_or(serde_yaml::Value::Null)
}

/// Path del vault según config (espejo del CLI: `semantic.vault_path`,
/// default vault) resuelto con el layout del workspace.
pub fn vault_path(root: &std::path::Path, cfg: &serde_yaml::Value) -> std::path::PathBuf {
    let rel = cfg
        .get("semantic")
        .and_then(|m| m.get("vault_path"))
        .and_then(|v| v.as_str())
        .unwrap_or("vault");
    let layout = cortex_workspace::WorkspaceLayout::discover(root);
    layout.resolve_workspace_relative(std::path::Path::new(rel))
}
