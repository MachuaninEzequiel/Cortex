"""cortex.autopilot.config — Optional configuration for Autopilot.

Reads ``.cortex/autopilot.yaml`` if present; otherwise returns sensible
defaults so the module works out-of-the-box.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from cortex.workspace.layout import WorkspaceLayout
from .errors import ConfigError


class AutopilotConfig(BaseModel):
    """Runtime configuration for the Autopilot module.

    All fields have safe defaults so that Autopilot is usable even when
    the user has not created ``autopilot.yaml``.
    """
    mode: str = "assist"
    default_budget_profile: str = "fast_code"
    auto_checkpoint_files: int = 5
    auto_checkpoint_minutes: int = 10
    max_event_jsonl_mb: int = 5
    event_rotation_days: int = 30
    enable_hooks: bool = False
    ide_adapter: str | None = None

    @classmethod
    def defaults(cls) -> "AutopilotConfig":
        return cls()


def load_autopilot_config(layout: WorkspaceLayout) -> AutopilotConfig:
    """Load configuration from ``{workspace_root}/autopilot.yaml``.

    Parameters
    ----------
    layout:
        Resolved workspace layout.

    Returns
    -------
    AutopilotConfig
        Merged configuration (file values override defaults).

    Raises
    ------
    ConfigError
        If the file exists but cannot be parsed.
    """
    config_path = layout.workspace_root / "autopilot.yaml"
    if not config_path.exists():
        return AutopilotConfig.defaults()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ConfigError(f"Failed to parse autopilot config: {exc}") from exc

    if not isinstance(raw, dict):
        raw = {}

    return AutopilotConfig(**raw)
