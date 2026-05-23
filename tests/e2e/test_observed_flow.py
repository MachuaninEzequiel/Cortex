"""End-to-end tests for the Observed mode (Phase 03 / T3.11).

Verifies the full loop: install an IDE hook → trigger an IDE event
(git commit) → checkpoint is registered in the active Session.

These tests shell out to real ``git`` and rely on the ``cortex`` console
script being importable from the active interpreter. They run on
Windows (git-for-windows bundles sh.exe) and POSIX equivalently.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cortex.session import CheckpointSource
from cortex.session.hooks import default_installer
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

# ── Helpers ──────────────────────────────────────────────────────────


def _git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=False, capture_output=True
    )


def _git_or_skip(*args: str, cwd: Path) -> None:
    res = _git(*args, cwd=cwd)
    if res.returncode != 0:
        pytest.skip(f"git error: {res.stderr.decode(errors='replace')}")


@pytest.fixture
def observed_repo(tmp_path: Path) -> dict:
    """Build a minimal Cortex-aware git repo with one OPEN session."""
    repo = tmp_path / "observed"
    repo.mkdir()
    (repo / ".cortex" / "sessions").mkdir(parents=True)
    (repo / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8"
    )

    _git_or_skip("init", "-q", "-b", "main", cwd=repo)
    _git_or_skip("config", "user.email", "e@e", cwd=repo)
    _git_or_skip("config", "user.name", "e", cwd=repo)
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git_or_skip("add", ".", cwd=repo)
    _git_or_skip("commit", "-q", "-m", "initial", cwd=repo)

    spec_dir = repo / "vault" / "specs"
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "2026-05-16_observed.md"
    spec_path.write_text("# observed\n", encoding="utf-8")

    storage = SessionStorage(repo / ".cortex" / "sessions")
    svc = SessionService(storage, repo)
    record = svc.open(
        spec_id="2026-05-16_observed",
        spec_path=spec_path,
        spec_summary="observed mode E2E",
    )
    return {
        "repo": repo,
        "session_id": record.session_id,
        "service": svc,
    }


def _cortex_on_path() -> bool:
    return shutil.which("cortex") is not None


# ── Test cases ───────────────────────────────────────────────────────


@pytest.mark.skipif(not _cortex_on_path(), reason="`cortex` binary not on PATH")
class TestObservedFlowGitHook:
    def test_install_then_commit_creates_checkpoint(self, observed_repo: dict) -> None:
        """A single commit after install must register exactly one IDE_HOOK checkpoint."""
        repo: Path = observed_repo["repo"]
        svc: SessionService = observed_repo["service"]
        default_installer().install("cursor", repo)

        (repo / "feature.txt").write_text("hello\n", encoding="utf-8")
        _git_or_skip("add", "feature.txt", cwd=repo)
        _git_or_skip("commit", "-q", "-m", "add feature", cwd=repo)

        updated = svc.get(observed_repo["session_id"])
        ide_hook_cps = [
            cp for cp in updated.checkpoints if cp.source is CheckpointSource.IDE_HOOK
        ]
        assert len(ide_hook_cps) == 1, (
            f"expected 1 IDE_HOOK checkpoint, got {len(ide_hook_cps)}; "
            f"all checkpoints: {[cp.source.value for cp in updated.checkpoints]}"
        )
        assert "git commit" in ide_hook_cps[0].note

    def test_multiple_commits_register_one_checkpoint_each(
        self, observed_repo: dict
    ) -> None:
        repo: Path = observed_repo["repo"]
        svc: SessionService = observed_repo["service"]
        default_installer().install("cursor", repo)

        for i in range(3):
            (repo / f"f{i}.txt").write_text(f"{i}\n", encoding="utf-8")
            _git_or_skip("add", f"f{i}.txt", cwd=repo)
            _git_or_skip("commit", "-q", "-m", f"commit-{i}", cwd=repo)

        updated = svc.get(observed_repo["session_id"])
        ide_hook_cps = [
            cp for cp in updated.checkpoints if cp.source is CheckpointSource.IDE_HOOK
        ]
        assert len(ide_hook_cps) == 3

    def test_session_mode_inferred_as_observed(self, observed_repo: dict) -> None:
        """After the documenter sees ide-hook checkpoints, the mode is OBSERVED."""
        repo: Path = observed_repo["repo"]
        svc: SessionService = observed_repo["service"]
        default_installer().install("cursor", repo)

        (repo / "x.txt").write_text("x\n", encoding="utf-8")
        _git_or_skip("add", "x.txt", cwd=repo)
        _git_or_skip("commit", "-q", "-m", "x", cwd=repo)

        updated = svc.get(observed_repo["session_id"])
        from cortex.session.models import SessionMode

        inferred = SessionService.infer_mode(updated.checkpoints)
        assert inferred is SessionMode.OBSERVED


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-shell sabotage harness")
class TestObservedHookFailureNeverBlocksCommit:
    """Even when `cortex` exits non-zero the post-commit hook must succeed."""

    def test_commit_succeeds_when_cortex_fails(self, tmp_path: Path) -> None:
        repo = tmp_path / "no-cortex"
        repo.mkdir()
        _git_or_skip("init", "-q", "-b", "main", cwd=repo)
        _git_or_skip("config", "user.email", "e@e", cwd=repo)
        _git_or_skip("config", "user.name", "e", cwd=repo)

        default_installer().install("cursor", repo)

        # Sabotage: a fake `cortex` binary that always exits 99.
        fake_bin = tmp_path / "fake-bin"
        fake_bin.mkdir()
        fake_cortex = fake_bin / "cortex"
        fake_cortex.write_text(
            "#!/bin/sh\nexit 99\n", encoding="utf-8", newline="\n"
        )
        fake_cortex.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

        (repo / "README.md").write_text("x\n", encoding="utf-8")
        _git_or_skip("add", ".", cwd=repo)
        res = _git("commit", "-q", "-m", "init", cwd=repo, env=env)
        assert res.returncode == 0, (
            f"git commit returned {res.returncode}; "
            f"stderr: {res.stderr.decode(errors='replace')}"
        )
