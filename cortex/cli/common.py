"""Plomería compartida entre los submódulos de ``cortex.cli``.

Extraída de cli/main.py (deuda V2, Obra 01 fase P4) para que los
subapps importen de acá sin ciclos: main.py también importa de este
módulo, nunca al revés.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from cortex.core import AgentMemory

_DEFAULT_CONFIG = {
    "episodic": {
        "persist_dir": ".memory/chroma",
        "collection_name": "cortex_episodic",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_backend": "onnx",  # lightweight default (no PyTorch required)
    },
    "semantic": {
        "vault_path": "vault",
    },
    "retrieval": {
        "top_k": 5,
        "episodic_weight": 1.0,
        "semantic_weight": 1.0,
    },
    "llm": {
        "provider": "none",
        "model": "",
    },
}


def _load_memory(project_root: str | Path | None = None) -> AgentMemory:  # noqa: F821
    """Return an ``AgentMemory`` rooted at *project_root* (or CWD if None).

    Accepts ``--project-root`` from any CLI command so that adopters
    don't need to ``cd`` into their workspace just to run a query.
    """
    from cortex.core import AgentMemory
    from cortex.workspace import WorkspaceLayout

    start = Path(project_root).expanduser().resolve() if project_root else Path.cwd()
    layout = WorkspaceLayout.discover(start)
    config_path = layout.config_path
    if not config_path.exists():
        typer.echo(
            f"❌ Cortex no está configurado en {start}.\n"
            f"   No encuentro `{config_path}`.\n"
            "   Ejecutá `cortex setup full --non-interactive` para inicializar el workspace,\n"
            "   o pasá `--project-root <ruta>` apuntando a un repo ya configurado.",
            err=True,
        )
        sys.exit(1)
    return AgentMemory(config_path=config_path)


def _get_staged_files() -> list[str]:
    """Get list of staged (and modified) files from git."""

    files: list[str] = []
    try:
        # Staged files
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            files.extend(f for f in result.stdout.strip().split("\n") if f)

        # Modified (not staged)
        result2 = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        if result2.stdout.strip():
            files.extend(f for f in result2.stdout.strip().split("\n") if f)

        # Untracked
        result3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=10,
        )
        if result3.stdout.strip():
            files.extend(f for f in result3.stdout.strip().split("\n") if f)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return list(dict.fromkeys(files))  # Deduplicate preserving order
