from __future__ import annotations

import shutil
from pathlib import Path

from cortex.ide.base import IDEAdapter

# The 3 subagents that exist canonically in `.cortex/subagents/` AND in
# the Pi bundle. ``sync_canonical_subagents`` keeps the bundle in sync
# with the canonical directory so that ``inject_profiles`` propagates
# the latest contracts (Plan 01 Tripartita Refinada changes) to Pi.
_SHARED_AGENTS = (
    "cortex-code-explorer.md",
    "cortex-code-implementer.md",
    "cortex-documenter.md",
)


def _default_pi_bundle_dir() -> Path:
    """Path to the in-tree ``cortex-pi/`` bundle.

    Path(__file__) is cortex/ide/adapters/pi.py, so 4 parents up lands at
    the repo root that contains both ``cortex/`` and ``cortex-pi/``.
    """
    return Path(__file__).resolve().parent.parent.parent.parent / "cortex-pi"


class PiAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "pi"

    @property
    def display_name(self) -> str:
        return "Pi Coding Agent"

    def sync_canonical_subagents(
        self,
        project_root: Path,
        *,
        bundle_dir: Path | None = None,
    ) -> list[Path]:
        """Mirror ``.cortex/subagents/`` into ``cortex-pi/.pi/agents/``.

        Pi is the only target IDE that copies its agents from a frozen
        bundle (``cortex-pi/``) instead of reading the canonical workspace
        directly. Before ``inject_profiles`` copies that bundle into the
        project, this method overwrites the 3 shared agents in the bundle
        with the latest canonical content from the project's
        ``.cortex/subagents/`` directory.

        Idempotent. If the canonical directory does not exist (e.g. Pi
        is being injected before any Cortex setup ran), the bundle stays
        untouched and an empty list is returned.

        Args:
            project_root: Project where the canonical subagents live.
            bundle_dir:   Override for the Pi bundle root. Tests pass a
                          temporary directory so they do not mutate the
                          repository's real ``cortex-pi/`` bundle.

        Returns:
            Paths under ``<bundle_dir>/.pi/agents/`` that were overwritten.
        """
        from cortex.workspace.layout import WorkspaceLayout

        layout = WorkspaceLayout.discover(project_root)
        canonical_dir = layout.subagents_dir
        if not canonical_dir.is_dir():
            return []

        bundle = bundle_dir if bundle_dir is not None else _default_pi_bundle_dir()
        pi_bundle_agents = bundle / ".pi" / "agents"
        pi_bundle_agents.mkdir(parents=True, exist_ok=True)

        overwritten: list[Path] = []
        for name in _SHARED_AGENTS:
            src = canonical_dir / name
            if not src.exists():
                continue
            dst = pi_bundle_agents / name
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            overwritten.append(dst)
        return overwritten

    def inject_profiles(
        self,
        project_root: Path,
        prompts: dict[str, str] | None = None,
        *,
        sync_canonical: bool = True,
    ) -> list[str]:
        """Inject Cortex Pi configuration.

        Copies the entire cortex-pi folder contents into the project root.
        When ``sync_canonical`` is True (the default), the 3 shared
        subagents in the bundle are first re-synced from
        ``.cortex/subagents/`` so the project receives the latest
        Tripartita Refinada contracts even when the bundle is stale.

        Args:
            project_root:   Destination project.
            prompts:        Unused by Pi (the bundle ships its own prompts).
            sync_canonical: When True, refresh the bundle's shared
                            subagents from the canonical workspace before
                            copying. Set to False to copy the bundle as-is
                            (useful for reproducing a bundle snapshot).
        """
        if sync_canonical:
            self.sync_canonical_subagents(project_root)

        cortex_pi_dir = _default_pi_bundle_dir()

        files_written = []
        if cortex_pi_dir.exists() and cortex_pi_dir.is_dir():
            for item in cortex_pi_dir.iterdir():
                dest = project_root / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                    files_written.append(f"{item.name}/")
                else:
                    shutil.copy2(item, dest)
                    files_written.append(item.name)
        else:
            raise FileNotFoundError(f"cortex-pi template directory not found at {cortex_pi_dir}")

        return files_written

    def get_config_paths(self) -> dict[str, Path]:
        """Pi configuration is project-local, no global config paths."""
        return {}
        
    def detect_installation(self) -> bool:
        """Detect if the Pi Coding Agent CLI is on PATH.

        Pi is distributed as the npm package ``@mariozechner/pi-coding-agent``.
        Once installed globally, it exposes a ``pi`` executable. We probe
        for that binary instead of returning a hardcoded ``True``, so
        ``cortex doctor`` and ``cortex inject --ide pi`` can surface a
        clear error when Pi is missing.
        """
        return shutil.which("pi") is not None

    def inject_mcp(self, project_root: Path) -> list[str]:
        """Pi Coding Agent uses bash tools, MCP injection not required."""
        return []

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Uninstall Pi configuration."""
        if project_root is None:
            return []
            
        files_removed = []
        pi_dir = project_root / ".pi"
        if pi_dir.exists():
            shutil.rmtree(pi_dir)
            files_removed.append(".pi/")
            
        for f in ["AGENTS.md", "justfile", "README.md", "extensions"]:
            path = project_root / f
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    files_removed.append(f"{f}/")
                else:
                    path.unlink()
                    files_removed.append(f)
                    
        return files_removed
