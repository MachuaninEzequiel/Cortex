from __future__ import annotations

from pathlib import Path

import yaml

from cortex.enterprise.models import EnterpriseOrgConfig, OrgProfile
from cortex.runtime_context import slugify

DEFAULT_ENTERPRISE_CONFIG_PATH = Path(".cortex") / "org.yaml"

_PRESET_PROFILES: tuple[OrgProfile, ...] = (
    "small-company",
    "multi-project-team",
    "regulated-organization",
    "custom",
)


def list_enterprise_presets() -> list[str]:
    return list(_PRESET_PROFILES)


def discover_enterprise_config_path(project_root: Path) -> Path | None:
    root = project_root.resolve()
    path = root / DEFAULT_ENTERPRISE_CONFIG_PATH
    if path.exists():
        return path
    return None


def load_enterprise_config(
    project_root: Path,
    *,
    required: bool = False,
    path: Path | None = None,
) -> EnterpriseOrgConfig | None:
    config_path = path.resolve() if path else root_enterprise_config_path(project_root)
    if not config_path.exists():
        if required:
            raise FileNotFoundError(f"Enterprise config not found: {config_path}")
        return None

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Enterprise config must be a mapping: {config_path}")
    return EnterpriseOrgConfig.model_validate(payload)


def root_enterprise_config_path(project_root: Path) -> Path:
    return (project_root.resolve() / DEFAULT_ENTERPRISE_CONFIG_PATH).resolve()


def build_enterprise_org_config(
    *,
    project_name: str,
    profile: OrgProfile = "small-company",
    github_actions_enabled: bool = True,
    branch_isolation_enabled: bool = False,
) -> EnterpriseOrgConfig:
    project_slug = slugify(project_name, fallback="project")
    base = {
        "organization": {
            "name": project_name,
            "slug": project_slug,
            "profile": profile,
        },
        "integration": {
            "github_actions_enabled": github_actions_enabled,
            "webgraph_workspace_enabled": True,
            "ide_profiles": [],
        },
    }

    if profile == "small-company":
        base.update(
            {
                "memory": {
                    "mode": "layered",
                    "enterprise_vault_path": "vault-enterprise",
                    "enterprise_memory_path": ".memory/enterprise/chroma",
                    "enterprise_semantic_enabled": True,
                    "enterprise_episodic_enabled": False,
                    "project_memory_mode": "isolated",
                    "branch_isolation_enabled": branch_isolation_enabled,
                    "retrieval_default_scope": "local",
                },
                "promotion": {
                    "enabled": True,
                    "allowed_doc_types": ["spec", "decision", "runbook", "hu", "incident"],
                    "require_review": True,
                    "default_targets": ["enterprise_vault"],
                },
                "governance": {
                    "git_policy": "balanced",
                    "ci_profile": "advisory",
                    "version_sessions_in_git": False,
                },
            }
        )
    elif profile == "multi-project-team":
        base.update(
            {
                "memory": {
                    "mode": "layered",
                    "enterprise_vault_path": "vault-enterprise",
                    "enterprise_memory_path": ".memory/enterprise/chroma",
                    "enterprise_semantic_enabled": True,
                    "enterprise_episodic_enabled": False,
                    "project_memory_mode": "isolated",
                    "branch_isolation_enabled": branch_isolation_enabled,
                    "retrieval_default_scope": "all",
                },
                "promotion": {
                    "enabled": True,
                    "allowed_doc_types": ["spec", "decision", "runbook", "hu", "incident"],
                    "require_review": True,
                    "default_targets": ["enterprise_vault"],
                },
                "governance": {
                    "git_policy": "balanced",
                    "ci_profile": "advisory",
                    "version_sessions_in_git": False,
                },
            }
        )
    elif profile == "regulated-organization":
        base.update(
            {
                "memory": {
                    "mode": "layered",
                    "enterprise_vault_path": "vault-enterprise",
                    "enterprise_memory_path": ".memory/enterprise/chroma",
                    "enterprise_semantic_enabled": True,
                    "enterprise_episodic_enabled": False,
                    "project_memory_mode": "isolated",
                    "branch_isolation_enabled": True,
                    "retrieval_default_scope": "all",
                },
                "promotion": {
                    "enabled": True,
                    "allowed_doc_types": ["spec", "decision", "runbook", "hu", "incident"],
                    "require_review": True,
                    "default_targets": ["enterprise_vault"],
                },
                "governance": {
                    "git_policy": "strict",
                    "ci_profile": "enforced",
                    "version_sessions_in_git": True,
                },
            }
        )
    else:
        base.update(
            {
                "memory": {
                    "mode": "layered",
                    "enterprise_vault_path": "vault-enterprise",
                    "enterprise_memory_path": ".memory/enterprise/chroma",
                    "enterprise_semantic_enabled": True,
                    "enterprise_episodic_enabled": False,
                    "project_memory_mode": "isolated",
                    "branch_isolation_enabled": branch_isolation_enabled,
                    "retrieval_default_scope": "local",
                },
                "promotion": {
                    "enabled": True,
                    "allowed_doc_types": ["spec", "decision", "runbook", "hu", "incident"],
                    "require_review": True,
                    "default_targets": ["enterprise_vault"],
                },
                "governance": {
                    "git_policy": "custom",
                    "ci_profile": "advisory",
                    "version_sessions_in_git": False,
                },
            }
        )

    return EnterpriseOrgConfig.model_validate(base)


def write_enterprise_config(project_root: Path, config: EnterpriseOrgConfig) -> Path:
    path = root_enterprise_config_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_enterprise_config_yaml(config), encoding="utf-8")
    return path


def render_enterprise_config_yaml(config: EnterpriseOrgConfig) -> str:
    payload = config.model_dump(mode="json")
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    return (
        "# Cortex enterprise memory topology\n"
        "# This file governs organization-level memory, promotion and governance behavior.\n"
        "# Local runtime mechanics still live in config.yaml.\n\n"
        + body
    )


def describe_enterprise_topology(config: EnterpriseOrgConfig | None, project_root: Path | None = None) -> str:
    if config is None:
        return "project-only (no .cortex/org.yaml)"

    summary = [
        f"profile={config.organization.profile}",
        f"mode={config.memory.mode}",
        f"project_memory={config.memory.project_memory_mode}",
        f"branch_isolation={'on' if config.memory.branch_isolation_enabled else 'off'}",
        f"retrieval_default={config.memory.retrieval_default_scope}",
        f"promotion={'on' if config.promotion.enabled else 'off'}",
        f"ci={config.governance.ci_profile}",
    ]
    if project_root is not None and config.memory.enterprise_semantic_enabled:
        summary.append(f"enterprise_vault={config.resolve_enterprise_vault_path(project_root)}")
    elif config.memory.enterprise_semantic_enabled:
        summary.append(f"enterprise_vault={config.memory.enterprise_vault_path}")
    else:
        summary.append("enterprise_vault=disabled")
    return ", ".join(summary)
