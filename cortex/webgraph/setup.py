from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from cortex.runtime_context import slugify
from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.federation import WorkspaceProject, default_workspace_file, write_workspace_file
from cortex.workspace.layout import WorkspaceLayout


def get_missing_webgraph_dependencies() -> list[str]:
    """Return optional runtime dependencies that are not currently installed."""
    required = {
        "flask": "flask",
        "flask_compress": "flask-compress",
    }
    missing: list[str] = []
    for module_name, package_name in required.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


def install_missing_webgraph_dependencies() -> tuple[bool, list[str]]:
    """
    Ensure optional runtime dependencies are available.

    Returns:
        A tuple ``(ok, missing_after_install)``.
    """
    missing = get_missing_webgraph_dependencies()
    if not missing:
        return True, []

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    except (OSError, subprocess.CalledProcessError):
        return False, get_missing_webgraph_dependencies()

    remaining = get_missing_webgraph_dependencies()
    return not remaining, remaining


def install_webgraph(project_root: Path, interactive: bool = True, *, workspace_layout: WorkspaceLayout | None = None) -> bool:
    del interactive
    ok, _missing = install_missing_webgraph_dependencies()
    if not ok:
        return False
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    webgraph_root = layout.webgraph_dir
    webgraph_root.mkdir(parents=True, exist_ok=True)
    (webgraph_root / "cache").mkdir(exist_ok=True)
    config = WebGraphConfig.load(project_root, workspace_layout=layout)
    config.save(project_root, workspace_layout=layout)
    return True


def attach_project_root(workspace_root: Path, project_root: Path, *, project_id: str | None = None) -> Path:
    resolved_project_root = project_root.expanduser().resolve()
    resolved_workspace_root = workspace_root.resolve()
    workspace_file = default_workspace_file(resolved_workspace_root)
    project = WorkspaceProject(
        project_id=project_id or slugify(resolved_project_root.name, fallback="project"),
        root=resolved_project_root,
    )
    return write_workspace_file(workspace_file, [project])
