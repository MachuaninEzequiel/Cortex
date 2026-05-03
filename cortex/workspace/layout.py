"""
cortex.workspace.layout
-----------------------
Central workspace path resolver for Cortex.

``WorkspaceLayout`` is the single source of truth for every filesystem
path that the Cortex runtime depends on.  It supports two layout
modes (new and legacy) and provides a ``discover()`` class-method that
walks up from any directory to find the project root.

Layout modes
~~~~~~~~~~~~

**New layout** (layout_version >= 2)::

    <repo-root>/
      .cortex/                    ← workspace_root
        config.yaml
        vault/
        vault-enterprise/
        memory/
        enterprise-memory/
        org.yaml
        workspace.yaml
        AGENT.md
        system-prompt.md
        skills/
        subagents/
        webgraph/
        logs/
        scripts/
      .github/
        workflows/

**Legacy layout** (layout_version 1 or absent)::

    <repo-root>/
      config.yaml
      vault/
      vault-enterprise/
      .memory/
      .cortex/
        org.yaml
        skills/
        subagents/
        AGENT.md
        system-prompt.md
        webgraph/
        logs/
      scripts/
      .github/
        workflows/

All relative paths in ``config.yaml`` and ``org.yaml`` resolve against
``workspace_root`` — which equals ``repo_root`` in legacy mode and
``repo_root / ".cortex"`` in new mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class WorkspaceLayout:
    """Central workspace path resolver for Cortex.

    Provides a single, well-defined location for every path the
    runtime needs.  No other module should hardcode layout paths.

    Use :meth:`discover` to auto-detect the project layout, or
    :meth:`from_repo_root` when the repo root is already known.
    """

    # ── Roots ──────────────────────────────────────────────────────
    repo_root: Path
    workspace_root: Path

    # ── Layout mode ────────────────────────────────────────────────
    is_legacy_layout: bool = False
    is_new_layout: bool = True

    # ────────────────────────────────────────────────────────────────
    # Class-methods: discovery
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def discover(cls, start: Path) -> "WorkspaceLayout":
        """Walk up from *start* to find a Cortex project root.

        Precedence (first match wins):
        1. ``repo_root /.cortex / workspace.yaml`` with layout_version >= 2
        2. ``repo_root /.cortex / config.yaml``
        3. ``repo_root / config.yaml`` or ``repo_root /.cortex/`` (legacy)
        4. Bootstrap: assume *start* (or nearest git root) is the repo root.

        Parameters
        ----------
        start:
            Directory to begin the search from.  Typically
            ``Path.cwd()`` or a project root passed by the user.

        Returns
        -------
        WorkspaceLayout
            A fully-resolved layout with absolute paths.
        """
        current = start.resolve()

        # Strategy: scan upward from *start*. At each direct
        #  parent, check whether THAT parent looks like a repo root
        #  (i.e. has .cortex/ or config.yaml as a child).  We skip
        #  directories named ".cortex" themselves — they are part of
        #  the project, not a root.
        for parent in [current] + list(current.parents):
            # Skip directories whose name is ".cortex" — they are
            # the workspace, not the repo root.
            if parent.name == ".cortex":
                continue

            # ── Case 1: workspace.yaml with layout_version >= 2 ──
            ws_yaml = parent / ".cortex" / "workspace.yaml"
            if ws_yaml.is_file():
                try:
                    data = yaml.safe_load(ws_yaml.read_text(encoding="utf-8")) or {}
                    if isinstance(data, dict) and data.get("layout_version", 1) >= 2:
                        return cls.from_repo_root(parent, _force_new=True)
                except Exception:
                    pass

            # ── Case 2: .cortex/config.yaml (new layout) ──
            cortex_dir = parent / ".cortex"
            cortex_config = cortex_dir / "config.yaml"
            if cortex_config.is_file():
                root_config = parent / "config.yaml"
                if not root_config.is_file():
                    # config.yaml only inside .cortex/ → new layout
                    return cls.from_repo_root(parent, _force_new=True)
                # Both .cortex/config.yaml AND root config.yaml exist.
                # This is legacy — fall through to Case 3.

            # ── Case 3: legacy layout ──
            root_config = parent / "config.yaml"
            git_dir = parent / ".git"
            cortex_dir_exists = cortex_dir.is_dir()
            if root_config.is_file() or (cortex_dir_exists and git_dir.is_dir()):
                return cls._from_legacy_root(parent)

        # ── Case 4: bootstrap — no project found ──
        repo_root = _find_git_root(start) or start.resolve()
        return cls.from_repo_root(repo_root, _force_new=True)

    @classmethod
    def from_repo_root(
        cls,
        repo_root: Path,
        *,
        _force_new: bool = False,
    ) -> "WorkspaceLayout":
        """Build a *new-layout* workspace rooted at ``repo_root``.

        Parameters
        ----------
        repo_root:
            Absolute path to the repository root.
        _force_new:
            Internal flag — always returns new layout (used by
            ``discover`` when it has already determined the layout).
        """
        repo = repo_root.resolve()
        ws = repo / ".cortex"
        layout = cls(
            repo_root=repo,
            workspace_root=ws,
            is_legacy_layout=False,
            is_new_layout=True,
        )
        return layout

    # ────────────────────────────────────────────────────────────────
    # Private: legacy constructor
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def _from_legacy_root(cls, repo_root: Path) -> "WorkspaceLayout":
        """Build a *legacy-layout* workspace rooted at ``repo_root``.

        In legacy mode the workspace root *is* the repo root —
        ``config.yaml``, ``vault/``, ``.memory/`` all live at the top.
        """
        repo = repo_root.resolve()
        layout = cls(
            repo_root=repo,
            workspace_root=repo,
            is_legacy_layout=True,
            is_new_layout=False,
        )
        return layout

    # ────────────────────────────────────────────────────────────────
    # Config paths
    # ────────────────────────────────────────────────────────────────

    @property
    def config_path(self) -> Path:
        """Path to the main Cortex config file.

        New layout: ``repo_root / ".cortex" / "config.yaml"``
        Legacy:     ``repo_root / "config.yaml"``
        """
        if self.is_legacy_layout:
            return self.repo_root / "config.yaml"
        return self.workspace_root / "config.yaml"

    @property
    def org_config_path(self) -> Path:
        """Path to the enterprise org config.

        Both layouts: ``repo_root / ".cortex" / "org.yaml"``

        In new layout this lives inside workspace_root.
        In legacy layout .cortex/ is a separate directory.
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "org.yaml"
        return self.workspace_root / "org.yaml"

    # ────────────────────────────────────────────────────────────────
    # Vault paths
    # ────────────────────────────────────────────────────────────────

    @property
    def vault_path(self) -> Path:
        """Path to the local knowledge vault.

        New layout: ``repo_root / ".cortex" / "vault"``
        Legacy:     ``repo_root / "vault"``
        """
        if self.is_legacy_layout:
            return self.repo_root / "vault"
        return self.workspace_root / "vault"

    @property
    def enterprise_vault_path(self) -> Path:
        """Path to the enterprise knowledge vault.

        New layout: ``repo_root / ".cortex" / "vault-enterprise"``
        Legacy:     ``repo_root / "vault-enterprise"``
        """
        if self.is_legacy_layout:
            return self.repo_root / "vault-enterprise"
        return self.workspace_root / "vault-enterprise"

    # ────────────────────────────────────────────────────────────────
    # Memory paths
    # ────────────────────────────────────────────────────────────────

    @property
    def episodic_memory_path(self) -> Path:
        """Path to the episodic memory root directory.

        New layout: ``repo_root / ".cortex" / "memory"``
        Legacy:     ``repo_root / ".memory"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".memory"
        return self.workspace_root / "memory"

    @property
    def enterprise_memory_path(self) -> Path:
        """Path to the enterprise episodic memory root directory.

        New layout: ``repo_root / ".cortex" / "enterprise-memory"``
        Legacy:     ``repo_root / ".memory" / "enterprise"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".memory" / "enterprise"
        return self.workspace_root / "enterprise-memory"

    # ────────────────────────────────────────────────────────────────
    # Workspace assets
    # ────────────────────────────────────────────────────────────────

    @property
    def skills_dir(self) -> Path:
        """Path to the skills directory.

        Both layouts: ``repo_root / ".cortex" / "skills"``

        (In legacy layout .cortex/ exists as a sibling to vault/;
        in new layout it lives inside workspace_root.)
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "skills"
        return self.workspace_root / "skills"

    @property
    def subagents_dir(self) -> Path:
        """Path to the subagents directory.

        Both layouts: ``repo_root / ".cortex" / "subagents"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "subagents"
        return self.workspace_root / "subagents"

    @property
    def agent_guidelines_path(self) -> Path:
        """Path to the AGENT.md file.

        Both layouts: ``repo_root / ".cortex" / "AGENT.md"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "AGENT.md"
        return self.workspace_root / "AGENT.md"

    @property
    def system_prompt_path(self) -> Path:
        """Path to the system-prompt.md file.

        Both layouts: ``repo_root / ".cortex" / "system-prompt.md"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "system-prompt.md"
        return self.workspace_root / "system-prompt.md"

    @property
    def workspace_yaml_path(self) -> Path:
        """Path to the workspace.yaml file.

        New layout: ``repo_root / ".cortex" / "workspace.yaml"``
        Legacy:     ``repo_root / ".cortex" / "workspace.yaml"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "workspace.yaml"
        return self.workspace_root / "workspace.yaml"

    # ────────────────────────────────────────────────────────────────
    # WebGraph paths
    # ────────────────────────────────────────────────────────────────

    @property
    def webgraph_dir(self) -> Path:
        """Path to the WebGraph directory.

        Both layouts: ``repo_root / ".cortex" / "webgraph"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "webgraph"
        return self.workspace_root / "webgraph"

    @property
    def webgraph_config_path(self) -> Path:
        """Path to the WebGraph config file.

        Both layouts: ``repo_root / ".cortex" / "webgraph" / "config.yaml"``
        """
        return self.webgraph_dir / "config.yaml"

    @property
    def webgraph_workspace_path(self) -> Path:
        """Path to the WebGraph workspace file.

        Both layouts: ``repo_root / ".cortex" / "webgraph" / "workspace.yaml"``
        """
        return self.webgraph_dir / "workspace.yaml"

    @property
    def webgraph_cache_dir(self) -> Path:
        """Path to the WebGraph cache directory.

        Both layouts: ``repo_root / ".cortex" / "webgraph" / "cache"``
        """
        return self.webgraph_dir / "cache"

    # ────────────────────────────────────────────────────────────────
    # Runtime paths
    # ────────────────────────────────────────────────────────────────

    @property
    def logs_dir(self) -> Path:
        """Path to the MCP logs directory.

        Both layouts: ``repo_root / ".cortex" / "logs"``
        """
        if self.is_legacy_layout:
            return self.repo_root / ".cortex" / "logs"
        return self.workspace_root / "logs"

    @property
    def scripts_dir(self) -> Path:
        """Path to the scripts directory.

        New layout: ``repo_root / ".cortex" / "scripts"``
        Legacy:     ``repo_root / "scripts"``
        """
        if self.is_legacy_layout:
            return self.repo_root / "scripts"
        return self.workspace_root / "scripts"

    # ────────────────────────────────────────────────────────────────
    # CI/CD (outside .cortex)
    # ────────────────────────────────────────────────────────────────

    @property
    def workflows_dir(self) -> Path:
        """Path to the GitHub Actions workflows directory.

        Always: ``repo_root / ".github" / "workflows"``
        (GitHub requires this location.)
        """
        return self.repo_root / ".github" / "workflows"

    # ────────────────────────────────────────────────────────────────
    # Enterprise promotion
    # ────────────────────────────────────────────────────────────────

    @property
    def promotion_records_path(self) -> Path:
        """Path to the promotion records file.

        New layout: ``repo_root / ".cortex" / "vault-enterprise" / "promotion" / "records.jsonl"``
        Legacy:     ``repo_root / "vault-enterprise" / ".cortex" / "promotion" / "records.jsonl"``
        """
        if self.is_legacy_layout:
            return (
                self.repo_root / "vault-enterprise" / ".cortex" / "promotion" / "records.jsonl"
            )
        return self.enterprise_vault_path / "promotion" / "records.jsonl"

    @property
    def promotion_dir(self) -> Path:
        """Directory containing promotion records.

        New layout: ``repo_root / ".cortex" / "vault-enterprise" / "promotion"``
        Legacy:     ``repo_root / "vault-enterprise" / ".cortex" / "promotion"``
        """
        return self.promotion_records_path.parent

    # ────────────────────────────────────────────────────────────────
    # Vault index
    # ────────────────────────────────────────────────────────────────

    @property
    def vault_index_path(self) -> Path:
        """Path to the vault's search index file.

        New layout: ``repo_root / ".cortex" / "vault" / ".cortex_index.json"``
        Legacy:     ``repo_root / "vault" / ".cortex_index.json"``
        """
        return self.vault_path / ".cortex_index.json"

    # ────────────────────────────────────────────────────────────────
    # Git
    # ────────────────────────────────────────────────────────────────

    @property
    def gitignore_path(self) -> Path:
        """Path to the ``.gitignore`` file.

        Always: ``repo_root / ".gitignore"``
        """
        return self.repo_root / ".gitignore"

    # ────────────────────────────────────────────────────────────────
    # Resolution helpers
    # ────────────────────────────────────────────────────────────────

    def resolve_workspace_relative(self, value: str | Path) -> Path:
        """Resolve a relative path against ``workspace_root``.

        In new layout, ``"vault"`` resolves to ``repo_root / ".cortex" / "vault"``.
        In legacy layout, ``"vault"`` resolves to ``repo_root / "vault"``.

        Absolute paths are returned unchanged.
        """
        p = Path(value)
        if p.is_absolute():
            return p.resolve()
        return (self.workspace_root / p).resolve()

    # ────────────────────────────────────────────────────────────────
    # Legacy compatibility helpers
    # ────────────────────────────────────────────────────────────────

    @property
    def legacy_config_path(self) -> Path:
        """Config path in the legacy layout (always repo_root / config.yaml)."""
        return self.repo_root / "config.yaml"

    @property
    def legacy_vault_path(self) -> Path:
        """Vault path in the legacy layout (always repo_root / vault)."""
        return self.repo_root / "vault"

    @property
    def legacy_memory_path(self) -> Path:
        """Memory path in the legacy layout (always repo_root / .memory)."""
        return self.repo_root / ".memory"

    @property
    def legacy_org_config_path(self) -> Path:
        """Org config in the legacy layout (always repo_root / .cortex / org.yaml)."""
        return self.repo_root / ".cortex" / "org.yaml"

    # ────────────────────────────────────────────────────────────────
    # Dunder helpers
    # ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        mode = "legacy" if self.is_legacy_layout else "new"
        return (
            f"WorkspaceLayout("
            f"repo_root={self.repo_root!r}, "
            f"workspace_root={self.workspace_root!r}, "
            f"mode={mode})"
        )


# ────────────────────────────────────────────────────────────────────
# Module-level helpers
# ────────────────────────────────────────────────────────────────────


def _find_git_root(start: Path) -> Path | None:
    """Walk upwards to find the closest ``.git`` directory."""
    current = start.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").is_dir():
            return parent
    return None