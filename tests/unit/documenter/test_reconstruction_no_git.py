"""Reconstruction tests for sessions opened without a git repository.

When :attr:`SessionRecord.is_gitless` is true the Reconstructor must:

* Not call any git subprocess (no ``git diff``, no ``git rev-parse``).
* Treat ``diff_text`` and ``diff_entries`` as empty.
* Derive ``files_touched`` from ``Checkpoint.artifacts_touched`` instead.
* Set ``ReconstructionOutput.gitless = True`` so the persister can emit
  the visible no-git notice in the session note.
"""

from __future__ import annotations

import textwrap
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.documenter.reconstruction import (
    ReconstructionInput,
    Reconstructor,
    _files_touched_from_checkpoints,
)
from cortex.session import (
    CheckpointSource,
)
from cortex.session.models import Checkpoint
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner

# ---------------------------------------------------------------------------
# Pure helper
# ---------------------------------------------------------------------------


def _cp(*paths: str, source: CheckpointSource = CheckpointSource.MANUAL) -> Checkpoint:
    return Checkpoint(
        timestamp=datetime.now(UTC),
        source=source,
        artifacts_touched=list(paths),
    )


class TestFilesTouchedFromCheckpoints:
    def test_empty_checkpoints_returns_empty_list(self) -> None:
        assert _files_touched_from_checkpoints([]) == []

    def test_aggregates_artifacts_in_order(self) -> None:
        result = _files_touched_from_checkpoints(
            [_cp("a.py", "b.py"), _cp("c.py")]
        )
        assert result == [Path("a.py"), Path("b.py"), Path("c.py")]

    def test_deduplicates_by_posix_path(self) -> None:
        """Same file mentioned in two checkpoints only appears once."""
        result = _files_touched_from_checkpoints(
            [_cp("a.py"), _cp("a.py", "b.py"), _cp("a.py")]
        )
        # POSIX-normalised comparison: 'a.py' seen once.
        assert [p.as_posix() for p in result] == ["a.py", "b.py"]


# ---------------------------------------------------------------------------
# End-to-end reconstruction without git
# ---------------------------------------------------------------------------


@pytest.fixture
def no_git_setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    """A workspace with no git, a spec file, and an open gitless session."""
    repo = tmp_path / "workspace_no_git"
    repo.mkdir()

    specs = repo / "vault" / "specs"
    specs.mkdir(parents=True)
    spec_path = specs / "2026-05-18_no-git-demo.md"
    spec_path.write_text(
        textwrap.dedent(
            """\
            ---
            title: no-git demo
            doc_type: spec
            goal: validate gitless reconstruction
            files_in_scope:
              - src/foo.py
            acceptance_criteria:
              - foo returns 1
            ---

            ## Goal
            validate gitless reconstruction
            """
        ),
        encoding="utf-8",
    )

    sessions_dir = tmp_path / "sessions"
    storage = SessionStorage(sessions_dir)
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-18_no-git-demo",
        spec_path=Path("vault/specs/2026-05-18_no-git-demo.md"),
        spec_summary="validate gitless reconstruction",
    )
    assert record.is_gitless

    # Inject a synthetic checkpoint claiming work on ``src/foo.py`` so the
    # reconstructor has something to surface as ``files_touched``.
    service.checkpoint(
        record.session_id,
        source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
        verified_claims=["wrote stub for foo()"],
        artifacts_touched=["src/foo.py"],
        note="initial implementation",
    )

    return {
        "repo": repo,
        "service": service,
        "session_id": record.session_id,
        "runner": VerificationRunner(repo_root=repo),
    }


def _reconstruct(setup):  # type: ignore[no-untyped-def]
    reconstructor = Reconstructor(
        session_service=setup["service"],
        verification_runner=setup["runner"],
        repo_root=setup["repo"],
    )
    return reconstructor.reconstruct(
        ReconstructionInput(session_id=setup["session_id"])
    )


class TestReconstructionGitless:
    def test_diff_text_is_empty(self, no_git_setup) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(no_git_setup)
        assert output.diff_text == ""
        assert output.diff_entries == []

    def test_files_touched_from_checkpoints(self, no_git_setup) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(no_git_setup)
        # The implementer's checkpoint declared src/foo.py.
        assert [p.as_posix() for p in output.files_touched] == ["src/foo.py"]

    def test_gitless_flag_propagated(self, no_git_setup) -> None:  # type: ignore[no-untyped-def]
        output = _reconstruct(no_git_setup)
        assert output.gitless is True

    def test_does_not_invoke_git_subprocess(self, no_git_setup) -> None:  # type: ignore[no-untyped-def]
        """No call into the git module short-circuits the slow path."""
        # Patch every entry-point in cortex.session.git to fail loudly if
        # the reconstructor reaches them. The whole point of gitless mode
        # is to never shell out to git.
        with (
            patch(
                "cortex.documenter.reconstruction.git_module.diff",
                side_effect=AssertionError("git.diff must not be called in gitless"),
            ),
            patch(
                "cortex.documenter.reconstruction.git_module.diff_name_status",
                side_effect=AssertionError(
                    "git.diff_name_status must not be called in gitless"
                ),
            ),
            patch(
                "cortex.documenter.reconstruction.git_module.get_head_commit",
                side_effect=AssertionError(
                    "git.get_head_commit must not be called in gitless"
                ),
            ),
        ):
            output = _reconstruct(no_git_setup)
        assert output.gitless is True
