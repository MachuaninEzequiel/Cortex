use std::fmt;
use std::path::{Component, Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::EnterpriseError;

macro_rules! string_enum {
    ($name:ident { $($variant:ident => $value:literal),+ $(,)? }) => {
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
        pub enum $name { $(#[serde(rename = $value)] $variant),+ }
        impl $name {
            pub fn as_str(self) -> &'static str { match self { $(Self::$variant => $value),+ } }
        }
        impl PartialEq<&str> for $name {
            fn eq(&self, other: &&str) -> bool { self.as_str() == *other }
        }
        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(match self { $(Self::$variant => $value),+ })
            }
        }
    };
}

string_enum!(OrgProfile { SmallCompany => "small-company", MultiProjectTeam => "multi-project-team", RegulatedOrganization => "regulated-organization", Custom => "custom" });
string_enum!(ProjectMemoryMode { Isolated => "isolated", Shared => "shared" });
string_enum!(RetrievalScope { Local => "local", Enterprise => "enterprise", All => "all" });
string_enum!(PromotableDocType { Spec => "spec", Decision => "decision", Runbook => "runbook", Hu => "hu", Incident => "incident", Session => "session" });
string_enum!(GitPolicy { Balanced => "balanced", Strict => "strict", Custom => "custom" });
string_enum!(CiProfile { Observability => "observability", Advisory => "advisory", Enforced => "enforced" });
string_enum!(PromotionTarget { EnterpriseVault => "enterprise_vault" });
string_enum!(Classification { Public => "public", Internal => "internal", Confidential => "confidential" });

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct OrganizationConfig {
    pub name: String,
    pub slug: String,
    pub profile: OrgProfile,
}
impl Default for OrganizationConfig {
    fn default() -> Self {
        Self {
            name: "Cortex Organization".into(),
            slug: "cortex-organization".into(),
            profile: OrgProfile::SmallCompany,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct MemoryConfig {
    pub mode: String,
    pub enterprise_vault_path: String,
    pub enterprise_memory_path: String,
    pub enterprise_semantic_enabled: bool,
    pub enterprise_episodic_enabled: bool,
    pub project_memory_mode: ProjectMemoryMode,
    pub branch_isolation_enabled: bool,
    pub retrieval_default_scope: RetrievalScope,
    pub retrieval_local_weight: f64,
    pub retrieval_enterprise_weight: f64,
}
impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            mode: "layered".into(),
            enterprise_vault_path: "vault-enterprise".into(),
            enterprise_memory_path: "memory/enterprise/chroma".into(),
            enterprise_semantic_enabled: true,
            enterprise_episodic_enabled: false,
            project_memory_mode: ProjectMemoryMode::Isolated,
            branch_isolation_enabled: false,
            retrieval_default_scope: RetrievalScope::Local,
            retrieval_local_weight: 1.0,
            retrieval_enterprise_weight: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct PromotionConfig {
    pub enabled: bool,
    pub allowed_doc_types: Vec<PromotableDocType>,
    pub require_review: bool,
    pub default_targets: Vec<PromotionTarget>,
}
impl Default for PromotionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            allowed_doc_types: vec![
                PromotableDocType::Spec,
                PromotableDocType::Decision,
                PromotableDocType::Runbook,
                PromotableDocType::Hu,
                PromotableDocType::Incident,
            ],
            require_review: true,
            default_targets: vec![PromotionTarget::EnterpriseVault],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct GovernanceConfig {
    pub git_policy: GitPolicy,
    pub ci_profile: CiProfile,
    pub version_sessions_in_git: bool,
}
impl Default for GovernanceConfig {
    fn default() -> Self {
        Self {
            git_policy: GitPolicy::Balanced,
            ci_profile: CiProfile::Advisory,
            version_sessions_in_git: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct IntegrationConfig {
    pub github_actions_enabled: bool,
    pub webgraph_workspace_enabled: bool,
    pub ide_profiles: Vec<String>,
}
impl Default for IntegrationConfig {
    fn default() -> Self {
        Self {
            github_actions_enabled: true,
            webgraph_workspace_enabled: true,
            ide_profiles: vec![],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct TeamConfig {
    pub id: String,
    pub members: Vec<String>,
    pub can_promote: bool,
    pub can_review: bool,
}
impl Default for TeamConfig {
    fn default() -> Self {
        Self {
            id: String::new(),
            members: vec![],
            can_promote: true,
            can_review: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct EnterprisePolicies {
    pub confidential_visible_to: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct RetentionPolicy {
    pub session: i64,
    pub handoff: i64,
    pub spec: i64,
    pub adr: i64,
    pub decision: i64,
    pub incident: i64,
    pub postmortem: i64,
    pub runbook: i64,
    pub architecture: i64,
    pub changelog: i64,
    pub hu: i64,
    pub glossary: i64,
}
impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            session: 365,
            handoff: 30,
            spec: 1095,
            adr: 2555,
            decision: 365,
            incident: 1825,
            postmortem: 2555,
            runbook: 730,
            architecture: 2555,
            changelog: 0,
            hu: 90,
            glossary: 0,
        }
    }
}
impl RetentionPolicy {
    pub fn for_doc_type(&self, slug: &str) -> i64 {
        match slug {
            "session" => self.session,
            "handoff" => self.handoff,
            "spec" => self.spec,
            "adr" => self.adr,
            "decision" => self.decision,
            "incident" => self.incident,
            "postmortem" => self.postmortem,
            "runbook" => self.runbook,
            "architecture" => self.architecture,
            "changelog" => self.changelog,
            "hu" => self.hu,
            "glossary" => self.glossary,
            _ => 0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct EnterpriseOrgConfig {
    pub schema_version: i64,
    pub organization: OrganizationConfig,
    pub memory: MemoryConfig,
    pub promotion: PromotionConfig,
    pub governance: GovernanceConfig,
    pub integration: IntegrationConfig,
    pub teams: Vec<TeamConfig>,
    pub classifications: Vec<Classification>,
    pub policies: EnterprisePolicies,
    pub retention_defaults: RetentionPolicy,
}
impl Default for EnterpriseOrgConfig {
    fn default() -> Self {
        Self {
            schema_version: 1,
            organization: OrganizationConfig::default(),
            memory: MemoryConfig::default(),
            promotion: PromotionConfig::default(),
            governance: GovernanceConfig::default(),
            integration: IntegrationConfig::default(),
            teams: vec![],
            classifications: vec![
                Classification::Public,
                Classification::Internal,
                Classification::Confidential,
            ],
            policies: EnterprisePolicies::default(),
            retention_defaults: RetentionPolicy::default(),
        }
    }
}

impl EnterpriseOrgConfig {
    pub fn validate(&self) -> Result<(), EnterpriseError> {
        if self.memory.retrieval_local_weight <= 0.0 {
            return Err(validation(
                "memory.retrieval_local_weight must be greater than 0",
            ));
        }
        if self.memory.retrieval_enterprise_weight <= 0.0 {
            return Err(validation(
                "memory.retrieval_enterprise_weight must be greater than 0",
            ));
        }
        if self.memory.enterprise_semantic_enabled
            && self.memory.enterprise_vault_path.trim().is_empty()
        {
            return Err(validation(
                "memory.enterprise_vault_path is required when enterprise_semantic_enabled=true",
            ));
        }
        if self.memory.enterprise_episodic_enabled
            && self.memory.enterprise_memory_path.trim().is_empty()
        {
            return Err(validation(
                "memory.enterprise_memory_path is required when enterprise_episodic_enabled=true",
            ));
        }
        for team in &self.teams {
            if team.id.is_empty()
                || !team
                    .id
                    .bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
            {
                return Err(validation(
                    "teams[].id must match ^[a-z0-9-]+$ and contain at least one character",
                ));
            }
        }
        let retention = &self.retention_defaults;
        for (name, value) in [
            ("session", retention.session),
            ("handoff", retention.handoff),
            ("spec", retention.spec),
            ("adr", retention.adr),
            ("decision", retention.decision),
            ("incident", retention.incident),
            ("postmortem", retention.postmortem),
            ("runbook", retention.runbook),
            ("architecture", retention.architecture),
            ("changelog", retention.changelog),
            ("hu", retention.hu),
            ("glossary", retention.glossary),
        ] {
            if value < 0 {
                return Err(validation(format!(
                    "retention_defaults.{name} must be greater than or equal to 0"
                )));
            }
        }
        if self.promotion.enabled && !self.memory.enterprise_semantic_enabled {
            return Err(validation("promotion.enabled requires memory.enterprise_semantic_enabled=true so promoted knowledge has a target"));
        }
        if self.memory.enterprise_episodic_enabled
            && self.memory.project_memory_mode != ProjectMemoryMode::Isolated
        {
            return Err(validation("memory.enterprise_episodic_enabled currently requires memory.project_memory_mode='isolated'"));
        }
        Ok(())
    }

    pub fn resolve_enterprise_vault_path(
        &self,
        project_root: &Path,
        workspace_root: Option<&Path>,
    ) -> Option<PathBuf> {
        self.memory.enterprise_semantic_enabled.then(|| {
            resolve_config_path(
                &self.memory.enterprise_vault_path,
                project_root,
                workspace_root,
            )
        })
    }
    pub fn resolve_enterprise_memory_path(
        &self,
        project_root: &Path,
        workspace_root: Option<&Path>,
    ) -> Option<PathBuf> {
        self.memory.enterprise_episodic_enabled.then(|| {
            resolve_config_path(
                &self.memory.enterprise_memory_path,
                project_root,
                workspace_root,
            )
        })
    }
}

fn validation(message: impl Into<String>) -> EnterpriseError {
    EnterpriseError::Validation(message.into())
}
fn resolve_config_path(value: &str, project_root: &Path, workspace_root: Option<&Path>) -> PathBuf {
    let expanded = if value == "~" || value.starts_with("~/") {
        std::env::var_os("HOME")
            .map(|home| PathBuf::from(home).join(value.trim_start_matches("~/")))
            .unwrap_or_else(|| PathBuf::from(value))
    } else {
        PathBuf::from(value)
    };
    let joined = if expanded.is_absolute() {
        expanded
    } else {
        workspace_root.unwrap_or(project_root).join(expanded)
    };
    let absolute = if joined.is_absolute() {
        joined
    } else {
        std::env::current_dir().unwrap_or_default().join(joined)
    };
    let mut normalized = PathBuf::new();
    for component in absolute.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            other => normalized.push(other.as_os_str()),
        }
    }
    normalized
}
