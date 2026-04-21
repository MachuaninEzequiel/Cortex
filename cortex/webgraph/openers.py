from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def resolve_safe_vault_path(vault_root: Path, relative_path: str) -> Path:
    candidate = (vault_root / relative_path).resolve()
    root = vault_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Refusing to open path outside vault: {candidate}")
    if not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


def open_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)

