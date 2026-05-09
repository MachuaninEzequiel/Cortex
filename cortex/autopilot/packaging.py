"""cortex.autopilot.packaging — Plugin manifest and install/uninstall helpers.

Provides a thin layer over the adapter registry to expose ``install`` and
``uninstall`` operations with manifest validation.  Manifests follow the
Superpowers de-facto plugin format so users can adopt Cortex without
friction.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from cortex.autopilot.adapters.registry import get_adapter


class PluginManifest(BaseModel):
    """Superpowers-compatible plugin manifest."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    skills: dict[str, str] = Field(default_factory=dict)
    hooks: dict[str, str] = Field(default_factory=dict)
    requires: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "PluginManifest":
        """Load a manifest from a ``plugin.json`` file."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


def validate_manifest(manifest: PluginManifest) -> list[str]:
    """Validate a manifest and return a list of human-readable errors.

    An empty list means the manifest is valid.
    """
    errors: list[str] = []
    if not manifest.name:
        errors.append("manifest name is required")
    if not manifest.version:
        errors.append("manifest version is required")
    if "directory" not in manifest.skills:
        errors.append("skills.directory is required")
    if "directory" not in manifest.hooks:
        errors.append("hooks.directory is required")
    return errors


def install_plugin(project_root: Path, adapter_name: str) -> list[Path]:
    """Install the Autopilot hook for *adapter_name* into *project_root*.

    Returns the list of modified paths.
    """
    adapter_cls = get_adapter(adapter_name)
    adapter = adapter_cls()
    return adapter.install(project_root)


def uninstall_plugin(project_root: Path, adapter_name: str) -> list[Path]:
    """Uninstall the Autopilot hook for *adapter_name* from *project_root*.

    Returns the list of restored/removed paths.
    """
    adapter_cls = get_adapter(adapter_name)
    adapter = adapter_cls()
    return adapter.uninstall(project_root)


def list_compatible_plugins(repo_root: Path | None = None) -> list[PluginManifest]:
    """Load all ``plugin.json`` manifests found in the repository.

    Searches for directories matching ``.*-plugin`` under *repo_root*.
    """
    if repo_root is None:
        # repo_root is three levels up from cortex/autopilot/packaging.py:
        # cortex/autopilot/packaging.py -> cortex/autopilot -> cortex -> repo_root
        repo_root = Path(__file__).resolve().parents[2]
    manifests: list[PluginManifest] = []
    for plugin_dir in repo_root.glob(".*-plugin"):
        manifest_path = plugin_dir / "plugin.json"
        if manifest_path.exists():
            try:
                manifests.append(PluginManifest.from_file(manifest_path))
            except Exception:
                continue
    return manifests
