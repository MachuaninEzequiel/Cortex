from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from cortex.webgraph.config import WebGraphConfig


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


def install_webgraph(project_root: Path, interactive: bool = True) -> bool:
    del interactive
    ok, _missing = install_missing_webgraph_dependencies()
    if not ok:
        return False
    webgraph_root = project_root / ".cortex" / "webgraph"
    webgraph_root.mkdir(parents=True, exist_ok=True)
    (webgraph_root / "cache").mkdir(exist_ok=True)
    config = WebGraphConfig.load(project_root)
    config.save(project_root)
    return True
