#!/usr/bin/env python3
"""
Cortex BlackBox Probe - Git Hook Installer
==========================================
Instala de forma no invasiva un hook 'post-commit' para registrar automáticamente
la actividad de git en segundo plano.

Uso:
  python .cortex-probe/install_hook.py            # Instalar
  python .cortex-probe/install_hook.py --uninstall # Desinstalar
"""

import os
import stat
import sys
from pathlib import Path

PROBE_DIR = Path(__file__).resolve().parent

def find_git_dir() -> Path:
    curr = PROBE_DIR
    while curr != curr.parent:
        if (curr / ".git").exists():
            return curr / ".git"
        curr = curr.parent
    return Path.cwd() / ".git"

def install():
    git_dir = find_git_dir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    post_commit = hooks_dir / "post-commit"

    probe_observer = PROBE_DIR / "git_observer.py"
    hook_line = f'python3 "{probe_observer.resolve()}" >/dev/null 2>&1 || python "{probe_observer.resolve()}" >/dev/null 2>&1 &\n'

    existing = ""
    if post_commit.exists():
        existing = post_commit.read_text(encoding="utf-8", errors="ignore")
        if str(probe_observer.name) in existing:
            print("ℹ️ El hook de Cortex Probe ya estaba instalado.")
            return

    new_content = existing
    if not new_content.startswith("#!"):
        new_content = "#!/bin/sh\n" + new_content
    new_content += "\n# Cortex BlackBox Probe Telemetry\n" + hook_line

    post_commit.write_text(new_content, encoding="utf-8")
    st = post_commit.stat()
    post_commit.chmod(st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"✅ Hook post-commit instalado exitosamente en: {post_commit}")

def uninstall():
    git_dir = find_git_dir()
    post_commit = git_dir / "hooks" / "post-commit"
    if not post_commit.exists():
        print("ℹ️ No había hook instalado.")
        return

    lines = post_commit.read_text(encoding="utf-8", errors="ignore").splitlines()
    clean_lines = [l for l in lines if "Cortex BlackBox Probe" not in l and "git_observer.py" not in l]

    if not any(l.strip() and not l.startswith("#!") for l in clean_lines):
        post_commit.unlink()
        print("✅ Hook post-commit eliminado por completo.")
    else:
        post_commit.write_text("\n".join(clean_lines) + "\n", encoding="utf-8")
        print("✅ Línea de Cortex Probe retirada del hook post-commit.")

if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
