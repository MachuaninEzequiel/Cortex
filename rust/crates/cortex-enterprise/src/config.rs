//! Puerto de `cortex.enterprise.config`: discovery/carga/escritura de
//! `.cortex/org.yaml`, presets por perfil y resumen de topología.
//!
//! Paridad de emisión: `yaml.safe_dump(payload, sort_keys=False,
//! allow_unicode=False)` vía `cortex_setup::yaml::dump_with(node, false)`.
//! La carga normaliza el slug como el validator Pydantic (`slug or name`,
//! fallback "organization") y ejecuta las validaciones cruzadas.

use std::path::{Path, PathBuf};

use cortex_setup::yaml::{self as pyyaml, Yaml};
use serde_json::Value as Json;

use crate::error::EnterpriseError;
use crate::models::{
    CiProfile, EnterpriseOrgConfig, GitPolicy, MemoryConfig, OrgProfile, OrganizationConfig,
    PromotionConfig,
};
use cortex_workspace::runtime_context::slugify;

/// Ruta legacy canónica de la config enterprise.
pub const DEFAULT_ENTERPRISE_CONFIG_PATH: &str = ".cortex/org.yaml";

const HEADER: &str = "# Cortex enterprise memory topology\n\
                      # This file governs organization-level memory, promotion and governance behavior.\n\
                      # Local runtime mechanics still live in config.yaml.\n\n";

/// Perfiles soportados, en orden de declaración Python.
pub fn list_enterprise_presets() -> Vec<&'static str> {
    vec![
        "small-company",
        "multi-project-team",
        "regulated-organization",
        "custom",
    ]
}

/// Ruta legacy: `<project_root>/.cortex/org.yaml` (sin resolver symlinks;
/// Python hace resolve() pero la igualdad de tests usa el join directo).
pub fn root_enterprise_config_path(project_root: &Path) -> PathBuf {
    project_root.join(DEFAULT_ENTERPRISE_CONFIG_PATH)
}

/// Descubre org.yaml: layout-aware gana sobre el path legacy. None si no existe.
pub fn discover_enterprise_config_path(
    project_root: &Path,
    workspace_layout: Option<&cortex_workspace::WorkspaceLayout>,
) -> Option<PathBuf> {
    let path = match workspace_layout {
        Some(layout) => layout.org_config_path(),
        None => root_enterprise_config_path(project_root),
    };
    path.exists().then_some(path)
}

/// Normaliza `organization.slug` = slugify(slug or name, fallback="organization")
/// (validator Pydantic `_normalize_slug`).
fn normalize_slug(config: &mut EnterpriseOrgConfig) {
    let source = if config.organization.slug.is_empty() {
        config.organization.name.clone()
    } else {
        config.organization.slug.clone()
    };
    config.organization.slug = slugify(&source, "organization");
}

fn parse_org_config(
    payload: Json,
    config_path: &Path,
) -> Result<EnterpriseOrgConfig, EnterpriseError> {
    let Json::Object(_) = payload else {
        return Err(EnterpriseError::Validation(format!(
            "Enterprise config must be a mapping: {}",
            config_path.display()
        )));
    };
    let mut config: EnterpriseOrgConfig =
        serde_json::from_value(payload).map_err(|e| EnterpriseError::Validation(e.to_string()))?;
    normalize_slug(&mut config);
    config.validate()?;
    Ok(config)
}

/// Carga la config enterprise.
///
/// Precedencia Python: layout > `path` explícito > legacy bajo project_root.
/// Sin archivo ⇒ `Ok(None)` salvo `required`
/// (`Enterprise config not found: {path}`). YAML vacío ⇒ defaults.
pub fn load_enterprise_config(
    project_root: &Path,
    required: bool,
    path: Option<&Path>,
    workspace_layout: Option<&cortex_workspace::WorkspaceLayout>,
) -> Result<Option<EnterpriseOrgConfig>, EnterpriseError> {
    let config_path: PathBuf = if let Some(layout) = workspace_layout {
        layout.org_config_path()
    } else if let Some(explicit) = path {
        // Path.resolve() no estricto de Python: canonicaliza lo existente.
        path_resolve_lenient(explicit)
    } else {
        root_enterprise_config_path(project_root)
    };

    if !config_path.exists() {
        if required {
            return Err(EnterpriseError::NotFound(format!(
                "Enterprise config not found: {}",
                config_path.display()
            )));
        }
        return Ok(None);
    }

    let raw = std::fs::read_to_string(&config_path)?;
    let yaml_value: serde_yaml::Value = serde_yaml::from_str(&raw)?;
    // yaml.safe_load(...) or {} ⇒ null/empty → objeto vacío (defaults).
    let payload = match &yaml_value {
        serde_yaml::Value::Null => Json::Object(Default::default()),
        other => yaml_to_json(other),
    };
    parse_org_config(payload, &config_path).map(Some)
}

/// Resolve() no estricto mínimo de Python (canonicaliza ancestro existente).
fn path_resolve_lenient(path: &Path) -> PathBuf {
    if path.is_absolute() {
        std::fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf())
    } else {
        let cwd = std::env::current_dir().unwrap_or_default();
        let joined = cwd.join(path);
        std::fs::canonicalize(&joined).unwrap_or(joined)
    }
}

/// Conversión serde_yaml → serde_json para reusar los structs serde.
fn yaml_to_json(value: &serde_yaml::Value) -> Json {
    match value {
        serde_yaml::Value::Null => Json::Null,
        serde_yaml::Value::Bool(b) => Json::Bool(*b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Json::Number(i.into())
            } else if let Some(u) = n.as_u64() {
                Json::Number(u.into())
            } else {
                serde_json::Number::from_f64(n.as_f64().unwrap_or(0.0))
                    .map(Json::Number)
                    .unwrap_or(Json::Null)
            }
        }
        serde_yaml::Value::String(s) => Json::String(s.clone()),
        serde_yaml::Value::Sequence(items) => Json::Array(items.iter().map(yaml_to_json).collect()),
        serde_yaml::Value::Mapping(map) => {
            let mut out = serde_json::Map::new();
            for (k, v) in map {
                let key = match k {
                    serde_yaml::Value::String(s) => s.clone(),
                    other => serde_yaml::to_string(other)
                        .unwrap_or_default()
                        .trim()
                        .into(),
                };
                out.insert(key, yaml_to_json(v));
            }
            Json::Object(out)
        }
        serde_yaml::Value::Tagged(t) => yaml_to_json(&t.value),
    }
}

/// Conversión serde_json → Yaml del emisor PyYAML (orden preservado).
fn json_to_yaml(value: &Json) -> Yaml {
    match value {
        Json::Null => Yaml::Null,
        Json::Bool(b) => Yaml::Bool(*b),
        Json::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Int(i)
            } else if let Some(u) = n.as_u64() {
                Yaml::Int(i64::try_from(u).unwrap_or(i64::MAX))
            } else {
                Yaml::Float(n.as_f64().unwrap_or(0.0))
            }
        }
        Json::String(s) => Yaml::Str(s.clone()),
        Json::Array(items) => Yaml::Seq(items.iter().map(json_to_yaml).collect()),
        Json::Object(map) => Yaml::Map(
            map.iter()
                .map(|(k, v)| (k.clone(), json_to_yaml(v)))
                .collect(),
        ),
    }
}

/// Construye una config por preset (tabla 1:1 de Python; regulated fija
/// branch_isolation_enabled=true ignorando el argumento).
pub fn build_enterprise_org_config(
    project_name: &str,
    profile: OrgProfile,
    github_actions_enabled: bool,
    branch_isolation_enabled: bool,
) -> Result<EnterpriseOrgConfig, EnterpriseError> {
    let organization = OrganizationConfig {
        name: project_name.to_string(),
        slug: slugify(project_name, "project"),
        profile,
    };
    let integration = crate::models::IntegrationConfig {
        github_actions_enabled,
        webgraph_workspace_enabled: true,
        ide_profiles: vec![],
    };

    let (memory, promotion, governance) = match profile {
        OrgProfile::SmallCompany
        | OrgProfile::Custom
        | OrgProfile::MultiProjectTeam
        | OrgProfile::RegulatedOrganization => {
            let branch = if profile == OrgProfile::RegulatedOrganization {
                true
            } else {
                branch_isolation_enabled
            };
            let scope = match profile {
                OrgProfile::MultiProjectTeam | OrgProfile::RegulatedOrganization => {
                    crate::models::RetrievalScope::All
                }
                _ => crate::models::RetrievalScope::Local,
            };
            let weight = match profile {
                OrgProfile::MultiProjectTeam => 1.2,
                OrgProfile::RegulatedOrganization => 1.3,
                _ => 1.0,
            };
            let governance_cfg = match profile {
                OrgProfile::RegulatedOrganization => crate::models::GovernanceConfig {
                    git_policy: GitPolicy::Strict,
                    ci_profile: CiProfile::Enforced,
                    version_sessions_in_git: true,
                },
                OrgProfile::Custom => crate::models::GovernanceConfig {
                    git_policy: GitPolicy::Custom,
                    ..crate::models::GovernanceConfig::default()
                },
                _ => crate::models::GovernanceConfig::default(),
            };
            (
                MemoryConfig {
                    branch_isolation_enabled: branch,
                    retrieval_default_scope: scope,
                    retrieval_enterprise_weight: weight,
                    ..MemoryConfig::default()
                },
                PromotionConfig::default(),
                governance_cfg,
            )
        }
    };

    let config = EnterpriseOrgConfig {
        schema_version: 1,
        organization,
        memory,
        promotion,
        governance,
        integration,
        teams: vec![],
        classifications: EnterpriseOrgConfig::default().classifications,
        policies: Default::default(),
        retention_defaults: Default::default(),
    };
    config.validate()?;
    Ok(config)
}

/// Escribe org.yaml (layout-aware o legacy) con mkdir -p del padre.
pub fn write_enterprise_config(
    project_root: &Path,
    config: &EnterpriseOrgConfig,
    workspace_layout: Option<&cortex_workspace::WorkspaceLayout>,
) -> Result<PathBuf, EnterpriseError> {
    let path = match workspace_layout {
        Some(layout) => layout.org_config_path(),
        None => root_enterprise_config_path(project_root),
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(&path, render_enterprise_config_yaml(config))?;
    Ok(path)
}

/// `render_enterprise_config_yaml`: header exacto + safe_dump
/// (sort_keys=False, allow_unicode=False).
pub fn render_enterprise_config_yaml(config: &EnterpriseOrgConfig) -> String {
    format!("{HEADER}{}", dump_enterprise_config_yaml(config))
}

/// safe_dump del payload SIN header (para el CLI `org-config`, que imprime
/// `yaml.safe_dump(config.model_dump(mode='json'), sort_keys=False,
/// allow_unicode=False)` tras el bloque de líneas descriptivas).
pub fn dump_enterprise_config_yaml(config: &EnterpriseOrgConfig) -> String {
    let payload =
        serde_json::to_value(config).expect("config serializable a JSON (model_dump mode=json)");
    pyyaml::dump_with(&json_to_yaml(&payload), false)
}

/// Resumen de topología (orden exacto de líneas Python, unidas por ", ").
pub fn describe_enterprise_topology(
    config: Option<&EnterpriseOrgConfig>,
    project_root: Option<&Path>,
    workspace_layout: Option<&cortex_workspace::WorkspaceLayout>,
) -> String {
    let Some(config) = config else {
        return "project-only (no .cortex/org.yaml)".to_string();
    };

    let mut summary = vec![
        format!("profile={}", config.organization.profile),
        format!("mode={}", config.memory.mode),
        format!("project_memory={}", config.memory.project_memory_mode),
        format!(
            "branch_isolation={}",
            if config.memory.branch_isolation_enabled {
                "on"
            } else {
                "off"
            }
        ),
        format!(
            "retrieval_default={}",
            config.memory.retrieval_default_scope
        ),
        format!(
            "promotion={}",
            if config.promotion.enabled {
                "on"
            } else {
                "off"
            }
        ),
        format!("ci={}", config.governance.ci_profile),
    ];

    // Quirk Python: base se pasa como project_root posicional, no como
    // workspace_root kwarg.
    let base = workspace_layout
        .map(|l| l.workspace_root.clone())
        .or_else(|| project_root.map(Path::to_path_buf));
    if config.memory.enterprise_semantic_enabled {
        if let Some(base) = &base {
            summary.push(format!(
                "enterprise_vault={}",
                config
                    .resolve_enterprise_vault_path(base, None)
                    .map(|p| p.display().to_string())
                    .unwrap_or_default()
            ));
        } else {
            summary.push(format!(
                "enterprise_vault={}",
                config.memory.enterprise_vault_path
            ));
        }
    } else {
        summary.push("enterprise_vault=disabled".to_string());
    }
    summary.join(", ")
}
