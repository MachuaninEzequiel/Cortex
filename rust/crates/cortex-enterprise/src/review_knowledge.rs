//! Puerto de `cortex.cli.review_knowledge`: operaciones de la cola de
//! revisión y renderización comprobable. El registro clap llega en P12B-8
//! (CLI nativo último); acá sólo viven dominio + strings de salida exactos.

use std::path::{Path, PathBuf};

use cortex_workspace::WorkspaceLayout;

use crate::clock::{isoformat_full, Clock};
use crate::error::EnterpriseError;
use crate::promotion_doctype::{mark_as_accepted, mark_as_rejected};

#[derive(Debug, Clone, PartialEq)]
pub struct PendingDraft {
    pub path: String,
    pub doc_type: Option<String>,
    pub title: Option<String>,
    pub owner: Option<String>,
    pub team: Option<String>,
    pub created_at: Option<String>,
}

/// Valida que `full_path` quede dentro del vault resuelto y traduce el error
/// al mensaje del CLI Python.
///
/// Ruling (enmienda en ledger): `security::validate_under_root` de cortex-app
/// compara lexicográficamente y NO normaliza `..` en tramos inexistentes;
/// `Path.resolve()` de Python sí lo hace. Se normaliza localmente aquí (capa
/// CLI) sin duplicar `resolve_safe` ni tocar territorio de A.
fn validate_inside_vault(
    vault_root: &Path,
    input_path: &str,
) -> Result<std::path::PathBuf, EnterpriseError> {
    let full = vault_root.join(input_path);
    let resolved_vault = python_resolve(vault_root);
    let resolved = python_resolve(&full);
    if !resolved.starts_with(&resolved_vault) {
        return Err(EnterpriseError::Validation(format!(
            "Path escapes enterprise vault: {input_path}"
        )));
    }
    Ok(resolved)
}

/// Espejo local de `Path.resolve(strict=False)` para la capa CLI:
/// canonicaliza el ancestro existente más profundo y normaliza `.`/`..`
/// del resto contra ese buffer.
pub(crate) fn python_resolve(path: &Path) -> std::path::PathBuf {
    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    // Componentes absolutos; se busca el ancestro existente más profundo y
    // el resto se normaliza léxicamente ("." se descarta, ".." popea contra
    // el buffer ya resuelto — semántica de Path.resolve(strict=False)).
    let comps: Vec<std::path::Component> = abs.components().collect();
    let mut idx = comps.len();
    while idx > 0 {
        let candidate: PathBuf = comps[..idx].iter().collect();
        if candidate.exists() {
            break;
        }
        idx -= 1;
    }
    let base: PathBuf = comps[..idx].iter().collect();
    let mut out = std::fs::canonicalize(&base).unwrap_or(base);
    for comp in &comps[idx..] {
        match comp {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

/// Salida exacta de `cortex review-knowledge approve`.
pub fn approve_output(
    layout: &WorkspaceLayout,
    path: &str,
    reviewer: &str,
    reason: &str,
    clock: &dyn Clock,
) -> Result<String, EnterpriseError> {
    let vault_root = layout.enterprise_vault_path();
    let full_path = validate_inside_vault(&vault_root, path)?;
    mark_as_accepted(&full_path, reviewer, reason, clock)?;
    Ok(format!(
        "[OK] {path} -> status: accepted (reviewer={reviewer})"
    ))
}

/// Salida exacta de `cortex review-knowledge reject` (move o delete).
pub fn reject_output(
    layout: &WorkspaceLayout,
    path: &str,
    reviewer: &str,
    reason: &str,
    delete: bool,
    clock: &dyn Clock,
) -> Result<String, EnterpriseError> {
    let vault_root = layout.enterprise_vault_path();
    let full_path = validate_inside_vault(&vault_root, path)?;
    let new_path = mark_as_rejected(&full_path, reviewer, reason, delete, clock)?;
    if delete {
        return Ok(format!("[OK] {path} -> deleted (reviewer={reviewer})"));
    }
    let shown = match new_path {
        Some(target) => target
            .strip_prefix(&vault_root)
            .map(|p| p.display().to_string())
            .unwrap_or_else(|_| path.to_string()),
        None => path.to_string(),
    };
    Ok(format!("[OK] {path} -> {shown} (reviewer={reviewer})"))
}

/// Timestamp completo estilo Python para eventos de auditoría.
pub fn audit_timestamp(clock: &dyn Clock) -> String {
    isoformat_full(clock.now())
}
