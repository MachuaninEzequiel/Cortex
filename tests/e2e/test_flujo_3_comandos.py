"""E2E del flujo nuevo usuario ≤3 comandos (plan §2.2 — requisito duro).

    1. `cortex init --non-interactive`   bootstrap completo
    2. `cortex start --title ... --non-interactive`  crea spec y abre sesión
    3. `cortex finish`                   cierra la sesión activa

Corre sobre un repo temporal real (git incluido) vía subprocess.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _cortex(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cortex.cli.main", *args],
        cwd=repo, capture_output=True, text=True, timeout=300,
    )


@pytest.fixture
def repo_git(tmp_path: Path) -> Path:
    repo = tmp_path / "proyecto"
    repo.mkdir()
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    def git(*a: str) -> None:
        subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    git("init")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@test.com")
    git("add", "-A")
    git("commit", "--allow-empty", "-m", "init")
    return repo


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
class TestFlujoNuevoUsuario:
    def test_tres_comandos_init_start_finish(self, repo_git: Path) -> None:
        # 1. init
        r1 = _cortex(repo_git, "init", "--non-interactive")
        assert r1.returncode == 0, r1.stderr[-800:]
        assert (repo_git / ".cortex").exists()

        # 2. start: crea spec + abre sesión
        r2 = _cortex(
            repo_git, "start",
            "--title", "Mi primera feature",
            "--goal", "Implementar algo genial",
            "--file", "README.md",
        )
        assert r2.returncode == 0, r2.stderr[-800:]

        # 3. finish: cierra la sesión activa
        r3 = _cortex(repo_git, "finish")
        assert r3.returncode == 0, r3.stderr[-800:]

        # resultado: existe nota de sesión en el vault
        notas = list((repo_git / ".cortex" / "vault" / "sessions").glob("*.md"))
        assert notas, "no hay nota de sesión en .cortex/vault/sessions/ tras el flujo"

