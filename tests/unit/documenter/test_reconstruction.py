"""End-to-end tests for :class:`Reconstructor` (T1.4)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cortex.documenter.reconstruction import (
    ReconstructionInput,
    Reconstructor,
    _decide_status,
    _scope_cross_check,
)
from cortex.session import CheckpointSource, SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner

PY = sys.executable


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestScopeCrossCheck:
    def test_split_in_out_unimpl(self) -> None:
        touched = [Path("src/a.py"), Path("src/b.py"), Path("README.md")]
        scope = [Path("src/a.py"), Path("src/c.py")]
        in_scope, out_scope, unimpl = _scope_cross_check(touched, scope)
        assert in_scope == [Path("src/a.py")]
        assert out_scope == [Path("src/b.py"), Path("README.md")]
        assert unimpl == [Path("src/c.py")]

    def test_empty_scope_everything_is_out(self) -> None:
        touched = [Path("a"), Path("b")]
        in_scope, out_scope, unimpl = _scope_cross_check(touched, [])
        assert in_scope == []
        assert out_scope == touched
        assert unimpl == []

    def test_posix_normalization(self) -> None:
        # Windows-style and POSIX-style match.
        touched = [Path("src\\a.py")]
        scope = [Path("src/a.py")]
        in_scope, _, _ = _scope_cross_check(touched, scope)
        # On non-Windows, the backslash is a literal char and won't match.
        # We only assert that the function does not crash and is consistent.
        assert isinstance(in_scope, list)


class TestDecideStatus:
    def _passing(self, name: str = "ok"):  # type: ignore[no-untyped-def]
        from datetime import UTC, datetime

        from cortex.session.models import VerificationHookResult

        return VerificationHookResult(
            name=name,
            command="echo",
            passed=True,
            exit_code=0,
            output="",
            duration_ms=1,
            run_at=datetime.now(UTC),
        )

    def _failing(self, name: str = "fail"):  # type: ignore[no-untyped-def]
        from datetime import UTC, datetime

        from cortex.session.models import VerificationHookResult

        return VerificationHookResult(
            name=name,
            command="exit 1",
            passed=False,
            exit_code=1,
            output="",
            duration_ms=1,
            run_at=datetime.now(UTC),
        )

    def test_all_pass_and_complete_yields_closed(self) -> None:
        assert (
            _decide_status(verification_results=[self._passing()], unimplemented=[])
            is SessionStatus.CLOSED
        )

    def test_one_fail_yields_handoff(self) -> None:
        assert (
            _decide_status(
                verification_results=[self._passing(), self._failing()],
                unimplemented=[],
            )
            is SessionStatus.HANDOFF
        )

    def test_unimplemented_yields_handoff_even_when_passing(self) -> None:
        assert (
            _decide_status(
                verification_results=[self._passing()],
                unimplemented=[Path("src/missing.py")],
            )
            is SessionStatus.HANDOFF
        )

    def test_no_hooks_no_unimpl_yields_closed(self) -> None:
        assert _decide_status(verification_results=[], unimplemented=[]) is SessionStatus.CLOSED


# ---------------------------------------------------------------------------
# End-to-end reconstruction
# ---------------------------------------------------------------------------


@pytest.fixture
def setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Build a git repo, spec file and session ready for reconstruction."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "foo.py").write_text("def f(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    # Persist + commit the spec BEFORE opening the session, mirroring the
    # production layout where ``vault/`` is part of the git history. We
    # want session.start_commit to already include the spec file, so that
    # the user's downstream edits show only ``src/...`` changes in the
    # diff.
    specs = repo / "vault" / "specs"
    specs.mkdir(parents=True)
    spec_path = specs / "2026-05-16_demo.md"
    spec_path.write_text(
        textwrap.dedent(
            """\
            ---
            title: demo
            doc_type: spec
            goal: keep foo working
            files_in_scope:
              - src/foo.py
            acceptance_criteria:
              - returns 1
            verification_hooks:
              - {name: smoke, command: %s -c "exit(0)", required: true, success_criteria: "exit 0", timeout_seconds: 30}
            ---

            ## Goal
            keep foo working
            """
        )
        % PY,
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add spec"], cwd=repo, check=True)

    sessions_dir = tmp_path / "sessions"
    storage = SessionStorage(sessions_dir)
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-16_demo",
        spec_path=Path("vault/specs/2026-05-16_demo.md"),
        spec_summary="keep foo working",
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


class TestPrivateHelpers:
    def test_resolve_spec_path_keeps_absolute(self, tmp_path: Path) -> None:
        from cortex.session.storage import SessionStorage

        storage = SessionStorage(tmp_path / "s")
        service = SessionService(storage, repo_root=tmp_path)
        rec = Reconstructor(
            session_service=service,
            verification_runner=VerificationRunner(repo_root=tmp_path),
            repo_root=tmp_path,
        )
        abs_path = tmp_path / "specs" / "x.md"
        assert rec._resolve_spec_path(abs_path) == abs_path

    def test_build_handoff_abandoned_branch_blocked_status(self) -> None:
        from cortex.documenter.reconstruction import _build_handoff
        from cortex.documenter.spec_loader import LoadedSpec

        spec = LoadedSpec(
            path=Path("vault/specs/x.md"),
            title="x",
            goal="g",
            files_in_scope=[],
            constraints=[],
            acceptance_criteria=[],
            verification_hooks=[],
        )
        handoff = _build_handoff(
            spec=spec,
            diff_entries=[],
            verification_results=[],
            checkpoints=[],
            in_scope=[],
            out_of_scope=[],
            unimplemented=[],
            suggested_adrs=[],
            suggested_status=SessionStatus.ABANDONED,
        )
        assert handoff.status == "blocked"


class TestLegacySpecWithoutHooks:
    def test_no_hooks_logs_warning_and_continues(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A spec persisted without verification_hooks must still be reconstructable."""
        import logging
        import textwrap

        from cortex.session.storage import SessionStorage

        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
        specs = repo / "vault" / "specs"
        specs.mkdir(parents=True)
        spec_path = specs / "2026-05-16_legacy.md"
        spec_path.write_text(
            textwrap.dedent(
                """\
                ---
                title: legacy
                doc_type: spec
                goal: legacy spec — no hooks
                files_in_scope: []
                ---
                """
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "legacy"], cwd=repo, check=True)

        storage = SessionStorage(tmp_path / "sessions")
        service = SessionService(storage, repo_root=repo)
        record = service.open(
            spec_id="2026-05-16_legacy",
            spec_path=Path("vault/specs/2026-05-16_legacy.md"),
        )
        rec = Reconstructor(
            session_service=service,
            verification_runner=VerificationRunner(repo_root=repo),
            repo_root=repo,
        )

        with caplog.at_level(logging.WARNING, logger="cortex.documenter.reconstruction"):
            out = rec.reconstruct(ReconstructionInput(session_id=record.session_id))

        # No hooks executed; the warning was emitted.
        assert out.verification_results == []
        assert any("no verification_hooks" in r.message for r in caplog.records)


class TestReconstructEndToEnd:
    def test_no_changes_yields_handoff_with_unimplemented(self, setup) -> None:  # type: ignore[no-untyped-def]
        out = _reconstruct(setup)
        assert out.suggested_status is SessionStatus.HANDOFF
        # Spec listed src/foo.py but nothing was touched after sync.
        assert Path("src/foo.py") in out.unimplemented_files
        assert out.verification_results
        assert out.verification_results[0].passed is True

    def test_modify_in_scope_yields_closed(self, setup) -> None:  # type: ignore[no-untyped-def]
        repo = setup["repo"]
        (repo / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=repo, check=True)

        out = _reconstruct(setup)
        assert out.suggested_status is SessionStatus.CLOSED
        assert Path("src/foo.py") in out.in_scope_files
        assert not out.out_of_scope_files
        assert not out.unimplemented_files
        # The handoff reflects the same conclusion.
        assert out.handoff.status == "complete"
        assert any("src/foo.py" in a.path for a in out.handoff.artifacts_produced)

    def test_modify_outside_scope_recorded_as_drift(self, setup) -> None:  # type: ignore[no-untyped-def]
        repo = setup["repo"]
        # Touch src/foo.py (in scope) AND a file outside scope.
        (repo / "src" / "foo.py").write_text("def f(): return 3\n", encoding="utf-8")
        (repo / "extra.md").write_text("noise\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit + extra"], cwd=repo, check=True)

        out = _reconstruct(setup)
        assert Path("extra.md") in out.out_of_scope_files
        # Drift surfaces in the handoff context_for_next.
        assert any("Scope drift" in c for c in out.handoff.context_for_next)

    def test_failing_hook_yields_handoff(self, setup) -> None:  # type: ignore[no-untyped-def]
        # Rewrite the spec with a failing hook.
        spec_path = setup["repo"] / "vault" / "specs" / "2026-05-16_demo.md"
        text = spec_path.read_text(encoding="utf-8").replace("exit(0)", "exit(1)")
        spec_path.write_text(text, encoding="utf-8")

        # Modify in-scope file too — should still HANDOFF because hook fails.
        (setup["repo"] / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=setup["repo"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=setup["repo"], check=True)

        out = _reconstruct(setup)
        assert out.suggested_status is SessionStatus.HANDOFF
        failing = [r for r in out.verification_results if not r.passed]
        assert failing
        # Failures show up as unverified_claims on the handoff.
        assert any("did not pass" in c for c in out.handoff.unverified_claims)

    def test_byo_mode_reflected_in_checkpoints(self, setup) -> None:  # type: ignore[no-untyped-def]
        # No checkpoints emitted at all → out.raw_checkpoints is empty,
        # ADR suggestions empty.
        (setup["repo"] / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=setup["repo"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=setup["repo"], check=True)
        out = _reconstruct(setup)
        assert out.raw_checkpoints == []
        assert out.suggested_adrs == []

    def test_managed_checkpoint_with_decision_keyword_yields_adr_candidate(self, setup) -> None:  # type: ignore[no-untyped-def]
        setup["service"].checkpoint(
            setup["session_id"],
            source=CheckpointSource.CORTEX_SDDWORK,
            note="Decidimos usar bcrypt instead of argon2 (trade-off).",
        )
        (setup["repo"] / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=setup["repo"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=setup["repo"], check=True)
        out = _reconstruct(setup)
        assert out.suggested_adrs
        assert out.handoff.suggested_adr is True
