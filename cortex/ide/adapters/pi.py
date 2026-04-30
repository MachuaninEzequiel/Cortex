from __future__ import annotations

import shutil
from pathlib import Path

from cortex.ide.base import IDEAdapter


class PiAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "pi"

    @property
    def display_name(self) -> str:
        return "Pi Coding Agent"

    def inject_profiles(self, project_root: Path, prompts: dict[str, str] | None = None) -> list[str]:
        """Inject Cortex Pi configuration.
        
        Copies the entire cortex-pi folder contents into the project root.
        """
        # Find cortex-pi relative to this file
        # Path(__file__) is cortex/ide/adapters/pi.py
        # parent(1) is adapters
        # parent(2) is ide
        # parent(3) is cortex (the package)
        # parent(4) is cortex (the repo root)
        pkg_root = Path(__file__).resolve().parent.parent.parent.parent
        cortex_pi_dir = pkg_root / "cortex-pi"
        
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
        """Pi is a CLI tool, assume true if selected."""
        return True

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
