from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from cortex.enterprise.config import build_enterprise_org_config, list_enterprise_presets


@dataclass(frozen=True)
class EnterpriseSetupInput:
    profile: str
    overrides: dict[str, Any]


def validate_enterprise_preset(profile: str) -> str:
    preset = profile.strip().lower()
    allowed = set(list_enterprise_presets())
    if preset not in allowed:
        raise ValueError(
            f"Invalid preset '{profile}'. Supported values: {', '.join(sorted(allowed))}"
        )
    return preset


def load_org_config_overrides(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Organization config must be a mapping: {path}")
    return payload


def resolve_enterprise_setup(
    *,
    project_name: str,
    profile: str = "small-company",
    overrides: dict[str, Any] | None = None,
    github_actions_enabled: bool = True,
) -> EnterpriseSetupInput:
    normalized_profile = validate_enterprise_preset(profile)
    base_config = build_enterprise_org_config(
        project_name=project_name,
        profile=normalized_profile,  # type: ignore[arg-type]
        github_actions_enabled=github_actions_enabled,
        branch_isolation_enabled=normalized_profile == "regulated-organization",
    )
    merged: dict[str, Any] = base_config.model_dump(mode="json")
    if overrides:
        merged = _deep_merge(merged, overrides)
    return EnterpriseSetupInput(profile=normalized_profile, overrides=merged)


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged
