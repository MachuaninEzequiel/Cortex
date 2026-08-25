//! Puerto de `cortex.enterprise.governance`: permisos multi-tenant y
//! visibilidad por clasificación. Módulo puro — no toca filesystem.
//!
//! Paridad: primer match de equipo gana; `admin` es pseudo-equipo con acceso
//! total; sin teams configurados ⇒ permisivo (back-compat); mensajes de
//! denegación replican el repr de Python (`'alice'`, `None`).

use crate::error::EnterpriseError;
use crate::models::{Classification, EnterpriseOrgConfig};

/// Pseudo-equipo integrado con acceso a todo.
pub const ADMIN_TEAM: &str = "admin";

/// Espejo del repr de Python para Option<&str>: `'x'` o `None`.
fn py_repr(value: Option<&str>) -> String {
    match value {
        Some(s) => format!("'{s}'"),
        None => "None".to_string(),
    }
}

/// Resuelve el equipo de `actor`: primer match en `org.teams`; falsey ⇒ None;
/// desconocido ⇒ None.
pub fn user_team(actor: Option<&str>, org: &EnterpriseOrgConfig) -> Option<String> {
    let actor = actor?;
    if actor.is_empty() {
        return None;
    }
    for team in &org.teams {
        if team.members.iter().any(|m| m == actor) {
            return Some(team.id.clone());
        }
    }
    None
}

/// ``true`` si el equipo puede promover conocimiento.
pub fn team_can_promote(team_id: Option<&str>, org: &EnterpriseOrgConfig) -> bool {
    if team_id == Some(ADMIN_TEAM) {
        return true;
    }
    let Some(team_id) = team_id else {
        // Sin equipos configurados ⇒ permisivo (back-compat).
        return org.teams.is_empty();
    };
    org.teams
        .iter()
        .find(|t| t.id == team_id)
        .map(|t| t.can_promote)
        .unwrap_or(false)
}

/// ``true`` si el equipo puede aprobar/rechazar promociones pendientes.
pub fn team_can_review(team_id: Option<&str>, org: &EnterpriseOrgConfig) -> bool {
    if team_id == Some(ADMIN_TEAM) {
        return true;
    }
    let Some(team_id) = team_id else {
        return org.teams.is_empty();
    };
    org.teams
        .iter()
        .find(|t| t.id == team_id)
        .map(|t| t.can_review)
        .unwrap_or(false)
}

/// Visibilidad de una clasificación para un equipo.
///
/// Reglas Python: `public`/`internal` siempre visibles; `confidential`
/// (y cualquier clasificación desconocida, que se comporta igual) solo para
/// `ADMIN_TEAM` o equipos listados en `policies.confidential_visible_to`.
pub fn classification_visible_to(
    classification: &str,
    team_id: Option<&str>,
    org: &EnterpriseOrgConfig,
) -> bool {
    if classification == "public" || classification == "internal" {
        return true;
    }
    if team_id == Some(ADMIN_TEAM) {
        return true;
    }
    let Some(team_id) = team_id else { return false };
    if team_id.is_empty() {
        return false;
    }
    org.policies
        .confidential_visible_to
        .iter()
        .any(|allowed| allowed == team_id)
}

/// Clasificaciones que un equipo puede ver (orden/duplicados preservados).
pub fn allowed_classifications_for(
    team_id: Option<&str>,
    org: &EnterpriseOrgConfig,
) -> Vec<Classification> {
    org.classifications
        .iter()
        .copied()
        .filter(|c| classification_visible_to(c.as_str(), team_id, org))
        .collect()
}

/// Valida que `actor` pueda promover; devuelve el team id resuelto (`""` si
/// no hay equipo). Error exacto: `actor 'x' (team=None) cannot promote`.
pub fn assert_can_promote(
    actor: &str,
    org: &EnterpriseOrgConfig,
) -> Result<String, EnterpriseError> {
    let team_id = user_team(Some(actor), org);
    if !team_can_promote(team_id.as_deref(), org) {
        return Err(EnterpriseError::Permission(format!(
            "actor {} (team={}) cannot promote",
            py_repr(Some(actor)),
            py_repr(team_id.as_deref()),
        )));
    }
    Ok(team_id.unwrap_or_default())
}

/// Valida que `actor` pueda revisar; devuelve el team id resuelto.
pub fn assert_can_review(
    actor: &str,
    org: &EnterpriseOrgConfig,
) -> Result<String, EnterpriseError> {
    let team_id = user_team(Some(actor), org);
    if !team_can_review(team_id.as_deref(), org) {
        return Err(EnterpriseError::Permission(format!(
            "actor {} (team={}) cannot review",
            py_repr(Some(actor)),
            py_repr(team_id.as_deref()),
        )));
    }
    Ok(team_id.unwrap_or_default())
}
