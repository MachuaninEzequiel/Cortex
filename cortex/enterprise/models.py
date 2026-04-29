from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from cortex.runtime_context import slugify

OrgProfile = Literal["small-company", "multi-project-team", "regulated-organization", "custom"]
ProjectMemoryMode = Literal["isolated", "shared"]
RetrievalScope = Literal["local", "enterprise", "all"]
PromotableDocType = Literal["spec", "decision", "runbook", "hu", "incident", "session"]
GitPolicy = Literal["balanced", "strict", "custom"]
CIProfile = Literal["observability", "advisory", "enforced"]
PromotionTarget = Literal["enterprise_vault"]


class OrganizationConfig(BaseModel):
    name: str = "Cortex Organization"
    slug: str = ""
    profile: OrgProfile = "small-company"

    @model_validator(mode="after")
    def _normalize_slug(self) -> "OrganizationConfig":
        self.slug = slugify(self.slug or self.name, fallback="organization")
        return self


class MemoryConfig(BaseModel):
    mode: str = "layered"
    enterprise_vault_path: str = "vault-enterprise"
    enterprise_memory_path: str = ".memory/enterprise/chroma"
    enterprise_semantic_enabled: bool = True
    enterprise_episodic_enabled: bool = False
    project_memory_mode: ProjectMemoryMode = "isolated"
    branch_isolation_enabled: bool = False
    retrieval_default_scope: RetrievalScope = "local"
    retrieval_local_weight: float = Field(default=1.0, gt=0)
    retrieval_enterprise_weight: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def _validate_paths(self) -> "MemoryConfig":
        if self.enterprise_semantic_enabled and not self.enterprise_vault_path.strip():
            raise ValueError("memory.enterprise_vault_path is required when enterprise_semantic_enabled=true")
        if self.enterprise_episodic_enabled and not self.enterprise_memory_path.strip():
            raise ValueError("memory.enterprise_memory_path is required when enterprise_episodic_enabled=true")
        return self


class PromotionConfig(BaseModel):
    enabled: bool = True
    allowed_doc_types: list[PromotableDocType] = Field(
        default_factory=lambda: ["spec", "decision", "runbook", "hu", "incident"]
    )
    require_review: bool = True
    default_targets: list[PromotionTarget] = Field(default_factory=lambda: ["enterprise_vault"])


class GovernanceConfig(BaseModel):
    git_policy: GitPolicy = "balanced"
    ci_profile: CIProfile = "advisory"
    version_sessions_in_git: bool = False


class IntegrationConfig(BaseModel):
    github_actions_enabled: bool = True
    webgraph_workspace_enabled: bool = True
    ide_profiles: list[str] = Field(default_factory=list)


class EnterpriseOrgConfig(BaseModel):
    schema_version: int = 1
    organization: OrganizationConfig = Field(default_factory=OrganizationConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    promotion: PromotionConfig = Field(default_factory=PromotionConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)

    @model_validator(mode="after")
    def _validate_cross_section_rules(self) -> "EnterpriseOrgConfig":
        if self.promotion.enabled and not self.memory.enterprise_semantic_enabled:
            raise ValueError(
                "promotion.enabled requires memory.enterprise_semantic_enabled=true so promoted knowledge has a target"
            )
        if self.memory.enterprise_episodic_enabled and self.memory.project_memory_mode != "isolated":
            raise ValueError(
                "memory.enterprise_episodic_enabled currently requires memory.project_memory_mode='isolated'"
            )
        return self

    def resolve_enterprise_vault_path(self, project_root: Path) -> Path | None:
        if not self.memory.enterprise_semantic_enabled:
            return None
        path = Path(self.memory.enterprise_vault_path).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()

    def resolve_enterprise_memory_path(self, project_root: Path) -> Path | None:
        if not self.memory.enterprise_episodic_enabled:
            return None
        path = Path(self.memory.enterprise_memory_path).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()
