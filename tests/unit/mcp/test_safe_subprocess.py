"""Tests para cortex.mcp._subprocess (Capa 3 del MCP defensive)."""
from __future__ import annotations

import sys
from pathlib import Path

from cortex.mcp._subprocess import Result, git_branch_exists, safe_run

# ----------------------------------------------------------------------
# safe_run
# ----------------------------------------------------------------------


def test_safe_run_success(tmp_path: Path):
    """Comando exitoso devuelve ok=True con stdout."""
    if sys.platform == "win32":
        cmd = ["cmd", "/c", "echo hello"]
    else:
        cmd = ["echo", "hello"]

    result = safe_run(cmd, cwd=tmp_path, timeout=5.0)
    assert result.ok is True
    assert "hello" in result.stdout
    assert result.error is None
    assert result.returncode == 0


def test_safe_run_command_not_found(tmp_path: Path):
    """Comando inexistente devuelve ok=False sin propagar exception."""
    result = safe_run(["this-command-definitely-does-not-exist-xyz"], cwd=tmp_path, timeout=5.0)
    assert result.ok is False
    assert result.error is not None
    assert "not found" in result.error.lower()
    # Nunca debe propagar al caller
    assert isinstance(result, Result)


def test_safe_run_timeout(tmp_path: Path):
    """Comando que excede el timeout devuelve ok=False con mensaje de timeout."""
    # Usar Python para garantizar comportamiento cross-platform
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    result = safe_run(cmd, cwd=tmp_path, timeout=0.5)
    assert result.ok is False
    assert result.error is not None
    assert "timeout" in result.error.lower()
    assert result.returncode is None


def test_safe_run_nonzero_exit(tmp_path: Path):
    """Comando que sale con codigo no-cero devuelve ok=False con stdout/stderr capturados."""
    cmd = [sys.executable, "-c", "import sys; sys.stderr.write('oops'); sys.exit(2)"]
    result = safe_run(cmd, cwd=tmp_path, timeout=5.0)
    assert result.ok is False
    assert result.returncode == 2
    assert "oops" in result.stderr
    assert result.error is not None


def test_safe_run_empty_command():
    """Lista de comando vacia devuelve ok=False sin invocar nada."""
    result = safe_run([], timeout=1.0)
    assert result.ok is False
    assert "empty" in result.error.lower()


# ----------------------------------------------------------------------
# git_branch_exists
# ----------------------------------------------------------------------


def _init_git_repo_with_commit(repo_dir: Path) -> None:
    """Helper: init a local git repo with at least one commit."""
    safe_run(["git", "init", "-b", "main"], cwd=repo_dir, timeout=5.0)
    safe_run(["git", "config", "user.email", "test@test"], cwd=repo_dir, timeout=5.0)
    safe_run(["git", "config", "user.name", "Test"], cwd=repo_dir, timeout=5.0)
    (repo_dir / "f.txt").write_text("hi")
    safe_run(["git", "add", "."], cwd=repo_dir, timeout=5.0)
    safe_run(["git", "commit", "-m", "init"], cwd=repo_dir, timeout=5.0)


def test_git_branch_exists_true(tmp_path: Path):
    """Rama que existe -> True."""
    _init_git_repo_with_commit(tmp_path)
    assert git_branch_exists("main", cwd=tmp_path, timeout=3.0) is True


def test_git_branch_exists_false(tmp_path: Path):
    """Rama inexistente -> False rapidamente (sin esperar timeout completo)."""
    _init_git_repo_with_commit(tmp_path)
    assert git_branch_exists("never-existed-branch", cwd=tmp_path, timeout=3.0) is False


def test_git_branch_exists_not_a_repo(tmp_path: Path):
    """Directorio que no es repo -> False (no crashea)."""
    assert git_branch_exists("main", cwd=tmp_path, timeout=3.0) is False
