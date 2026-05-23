"""Tests for the diff + checkpoint provenance merge in :class:`Reconstructor`.

Phase 09.A+ / May 2026: in git-aware sessions the documenter now combines
``git diff`` (verified by the index) with ``Checkpoint.artifacts_touched``
(declared by the agent). The output exposes three lists:

* ``files_verified_by_git``  — appeared in the diff (objective ground truth)
* ``files_declared_only``    — only in checkpoints (agent claim, uncommitted)
* ``files_touched``          — the union, preserving git-first order

The merge avoids the legacy false-handoff where an agent wrote a file but
forgot to commit before ``cortex finish-session``: the file is still
attributed to the session via the checkpoint, marked as declared-only so
the user can spot it and decide.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cortex.documenter.reconstruction import ReconstructionInput, Reconstructor
from cortex.session import CheckpointSource
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner

PY = sys.executable


@pytest.fixture
def git_session_with_uncommitted_file(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Open a git session, declare a file via checkpoint, never commit it.

    The classic "false handoff" reproducer: the agent's checkpoint claims
    it touched ``src/new.py``, but git diff between session.start_commit
    and HEAD shows nothing because the file was created (or modified) but
    not committed yet.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    specs = repo / "vault" / "specs"
    specs.mkdir(parents=True)
    spec_path = specs / "2026-05-18_provenance.md"
    spec_path.write_text(
        textwrap.dedent(
            """\
            ---
            title: provenance
            doc_type: spec
            goal: cover the merge
            files_in_scope:
              - src/new.py
            ---
            """
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "spec"], cwd=repo, check=True)

    sessions_dir = tmp_path / "sessions"
    storage = SessionStorage(sessions_dir)
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-18_provenance",
        spec_path=Path("vault/specs/2026-05-18_provenance.md"),
        spec_summary="cover the merge",
    )

    # Declare-only checkpoint: the agent claims to have touched src/new.py
    # but we never commit it. The diff between start_commit and HEAD will
    # show zero changes.
    service.checkpoint(
        record.session_id,
        source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
        verified_claims=["wrote stub for new()"],
        artifacts_touched=["src/new.py"],
        note="initial implementation, pending commit",
    )

    return {
        "repo": repo,
        "service": service,
        "session_id": record.session_id,
        "runner": VerificationRunner(repo_root=repo),
    }


def _reconstruct(setup):  # type: ignore[no-untyped-def]
    rec = Reconstructor(
        session_service=setup["service"],
        verification_runner=setup["runner"],
        repo_root=setup["repo"],
    )
    return rec.reconstruct(ReconstructionInput(session_id=setup["session_id"]))


class TestProvenanceMerge:
    def test_declared_only_file_appears_in_files_touched(
        self, git_session_with_uncommitted_file
    ) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(git_session_with_uncommitted_file)
        # The uncommitted file IS in files_touched (via checkpoint claim).
        assert any(p.as_posix() == "src/new.py" for p in output.files_touched)

    def test_declared_only_list_populated(
        self, git_session_with_uncommitted_file
    ) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(git_session_with_uncommitted_file)
        assert [p.as_posix() for p in output.files_declared_only] == ["src/new.py"]
        # The git-verified list is empty because nothing was committed past
        # the seed + spec commits.
        assert output.files_verified_by_git == []

    def test_unimplemented_skips_declared_files(
        self, git_session_with_uncommitted_file
    ) -> None:  # type: ignore[no-untyped-def]
        """The file declared by checkpoint counts as "touched", so the
        scope check should NOT mark it as unimplemented."""
        output = _reconstruct(git_session_with_uncommitted_file)
        assert output.unimplemented_files == []


@pytest.fixture
def git_session_with_committed_file(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Same setup but the agent actually commits the file. The diff sees it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    specs = repo / "vault" / "specs"
    specs.mkdir(parents=True)
    spec_path = specs / "2026-05-18_provenance-committed.md"
    spec_path.write_text(
        textwrap.dedent(
            """\
            ---
            title: provenance-committed
            doc_type: spec
            goal: cover the both-source case
            files_in_scope:
              - src/new.py
            ---
            """
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "spec"], cwd=repo, check=True)

    sessions_dir = tmp_path / "sessions"
    storage = SessionStorage(sessions_dir)
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-18_provenance-committed",
        spec_path=Path("vault/specs/2026-05-18_provenance-committed.md"),
        spec_summary="cover the both-source case",
    )

    # Now commit the file AFTER opening the session — git diff sees it.
    (repo / "src").mkdir()
    (repo / "src" / "new.py").write_text("def new(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add new.py"], cwd=repo, check=True)

    service.checkpoint(
        record.session_id,
        source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
        verified_claims=["wrote new() and committed"],
        artifacts_touched=["src/new.py"],
        note="committed",
    )

    return {
        "repo": repo,
        "service": service,
        "session_id": record.session_id,
        "runner": VerificationRunner(repo_root=repo),
    }


class TestProvenanceBothSources:
    def test_committed_file_appears_only_in_verified(
        self, git_session_with_committed_file
    ) -> None:  # type: ignore[no-untyped-def]
        """When a file is in BOTH git diff and a checkpoint, it counts as
        verified and is NOT duplicated in declared_only."""
        output = _reconstruct(git_session_with_committed_file)
        verified = [p.as_posix() for p in output.files_verified_by_git]
        declared = [p.as_posix() for p in output.files_declared_only]
        assert "src/new.py" in verified
        assert "src/new.py" not in declared

    def test_files_touched_is_deduplicated(
        self, git_session_with_committed_file
    ) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(git_session_with_committed_file)
        paths = [p.as_posix() for p in output.files_touched]
        # ``src/new.py`` must appear exactly once even though both sources
        # claim it.
        assert paths.count("src/new.py") == 1
