from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from cortex.enterprise.models import EnterpriseOrgConfig, OrgProfile
from cortex.runtime_context import slugify

if TYPE_CHECKING:
    from cortex.workspace.layout import WorkspaceLayout

# NOTE: The actual location of org.yaml depends on the workspace layout.
# In legacy layout: repo_root / ".cortex" / "org.yaml"
# In new layout:    workspace_root / "org.yaml"  (which is repo_root / ".cortex" / "org.yaml")
# Both resolve to the same physical path, so the default constant is still valid.
DEFAULT_ENTERPRISE_CONFIG_PATH = Path(".cortex") / "org.yaml"

_PRESET_PROFILES: tuple[OrgProfile, ...] = (
    "small-company",
    "multi-project-team",
    "regulated-organization",
    "custom",
)


def list_enterprise_presets() -> list[str]:
    return list(_PRESET_PROFILES)


def discover_enterprise_config_path(
    project_root: Path,
    *,
    workspace_layout: "WorkspaceLayout | None" = None,
) -> Path | None:
    """Discover the enterprise config file.

    If a WorkspaceLayout is provided, use it to find org.yaml.
    Otherwise, fall back to the legacy path.
    """
    if workspace_layout is not None:
        path = workspace_layout.org_config_path
        if path.exists():
            return path
        return None

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
    workspace_layout: "WorkspaceLayout | None" = None,
) -> EnterpriseOrgConfig | None:
    """Load enterprise organisational config.

    If a WorkspaceLayout is provided, use it to locate org.yaml.
    Otherwise, fall back to the legacy path under ``project_root / .cortex/``.
    """
    if workspace_layout is not None:
        config_path = workspace_layout.org_config_path
    elif path is not None:
        config_path = path.resolve()
    else:
        config_path = root_enterprise_config_path(project_root)

    if not config_path.exists():
        if required:
            raise FileNotFoundError(f"Enterprise config not found: {config_path}")
        return None

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Enterprise config must be a mapping: {config_path}")
    return EnterpriseOrgConfig.model_validate(payload)


def root_enterprise_config_path(project_root: Path) -> Path:
    """Return the legacy path for org.yaml (repo_root / .cortex / org.yaml)."""
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
                    "retrieval_local_weight": 1.0,
                    "retrieval_enterprise_weight": 1.0,
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
                    "retrieval_local_weight": 1.0,
                    "retrieval_enterprise_weight": 1.2,
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
                    "retrieval_local_weight": 1.0,
                    "retrieval_enterprise_weight": 1.3,
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
                    "retrieval_local_weight": 1.0,
                    "retrieval_enterprise_weight": 1.0,
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


def write_enterprise_config(
    project_root: Path,
    config: EnterpriseOrgConfig,
    *,
    workspace_layout: "WorkspaceLayout | None" = None,
) -> Path:
    """Write enterprise config to disk.

    If a WorkspaceLayout is provided, write to the layout-aware path.
    Otherwise, fall back to the legacy path.
    """
    if workspace_layout is not None:
        path = workspace_layout.org_config_path
    else:
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


def describe_enterprise_topology(
    config: EnterpriseOrgConfig | None,
    project_root: Path | None = None,
    *,
    workspace_layout: "WorkspaceLayout | None" = None,
) -> str:
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
    # Resolve enterprise_vault_path using workspace_layout or project_root
    base = None
    if workspace_layout is not None:
        base = workspace_layout.workspace_root
    elif project_root is not None:
        base = project_root

    if base is not None and config.memory.enterprise_semantic_enabled:
        summary.append(f"enterprise_vault={config.resolve_enterprise_vault_path(base)}")
    elif config.memory.enterprise_semantic_enabled:
        summary.append(f"enterprise_vault={config.memory.enterprise_vault_path}")
    else:
        summary.append("enterprise_vault=disabled")
    return ", ".join(summary)
