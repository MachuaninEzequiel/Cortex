"""Tests for :class:`DocumenterPersister` (T1.5)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cortex.documenter.persistence import (
    DocumenterPersister,
    FinishOverrides,
)
from cortex.documenter.reconstruction import (
    ReconstructionInput,
    Reconstructor,
)
from cortex.services.note_service import NoteService
from cortex.session import CheckpointSource, SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner

PY = sys.executable


# ---------------------------------------------------------------------------
# Dummies for the persistence dependencies that need a vault.
# ---------------------------------------------------------------------------


class _DummySemantic:
    def __init__(self) -> None:
        self.indexed: list[str] = []

    def index_file(self, rel_path: str) -> bool:
        self.indexed.append(rel_path)
        return True

    def sync(self) -> int:
        return 0


class _DummyEpisodic:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    def add(self, **kwargs: object) -> object:  # type: ignore[no-untyped-def]
        self.entries.append(dict(kwargs))
        return object()


# ---------------------------------------------------------------------------
# Fixture: a full reconstruction ready to feed the persister.
# ---------------------------------------------------------------------------


@pytest.fixture
def setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Build repo + spec + session + reconstruction → return everything."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "foo.py").write_text("def f(): return 1\n", encoding="utf-8")

    vault = repo / "vault"
    vault.mkdir()
    (vault / "specs").mkdir()
    (vault / "sessions").mkdir()
    (vault / "decisions").mkdir()

    spec_path = vault / "specs" / "2026-05-16_demo.md"
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
            """
        )
        % PY,
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    storage = SessionStorage(tmp_path / "sessions")
    session_service = SessionService(storage, repo_root=repo)
    record = session_service.open(
        spec_id="2026-05-16_demo",
        spec_path=Path("vault/specs/2026-05-16_demo.md"),
        spec_summary="keep foo working",
    )

    notes = NoteService(
        vault_path=vault,
        semantic=_DummySemantic(),  # type: ignore[arg-type]
        episodic=_DummyEpisodic(),  # type: ignore[arg-type]
    )
    persister = DocumenterPersister(
        note_service=notes,
        session_service=session_service,
        vault_path=vault,
    )
    runner = VerificationRunner(repo_root=repo)
    reconstructor = Reconstructor(
        session_service=session_service,
        verification_runner=runner,
        repo_root=repo,
    )

    return {
        "repo": repo,
        "vault": vault,
        "session_id": record.session_id,
        "session_service": session_service,
        "persister": persister,
        "reconstructor": reconstructor,
    }


def _commit_change(setup, content: str) -> None:  # type: ignore[no-untyped-def]
    (setup["repo"] / "src" / "foo.py").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=setup["repo"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=setup["repo"], check=True)


def _reconstruct(setup):  # type: ignore[no-untyped-def]
    return setup["reconstructor"].reconstruct(ReconstructionInput(session_id=setup["session_id"]))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFinalizeHappyPath:
    def test_persists_session_note_and_closes(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)

        assert result.final_status is SessionStatus.CLOSED
        assert result.session_note_path is not None
        assert result.session_note_path.is_file()
        # Session record is closed and active pointer cleared.
        record = setup["session_service"].get(setup["session_id"])
        assert record.status is SessionStatus.CLOSED
        assert setup["session_service"].get_active() is None

    def test_summary_carries_diagnostic_info(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)
        assert "status: closed" in result.summary
        assert "hooks: 1/1 passed" in result.summary


class TestHandoffPath:
    def test_failing_hook_persists_as_handoff(self, setup) -> None:  # type: ignore[no-untyped-def]
        # Modify spec so the hook fails.
        spec_path = setup["vault"] / "specs" / "2026-05-16_demo.md"
        text = spec_path.read_text(encoding="utf-8").replace("exit(0)", "exit(1)")
        spec_path.write_text(text, encoding="utf-8")
        # Commit the spec change so it shows in diff cleanly.
        subprocess.run(["git", "add", "."], cwd=setup["repo"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "spec edit"], cwd=setup["repo"], check=True)
        _commit_change(setup, "def f(): return 2\n")

        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)
        assert result.final_status is SessionStatus.HANDOFF
        record = setup["session_service"].get(setup["session_id"])
        assert record.status is SessionStatus.HANDOFF
        # Note: status=handoff propagates into the session note body.
        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        assert "handoff" in body.lower()


class TestADRCreation:
    def test_adr_candidate_persists(self, setup) -> None:  # type: ignore[no-untyped-def]
        setup["session_service"].checkpoint(
            setup["session_id"],
            source=CheckpointSource.CORTEX_SDDWORK,
            note="Decidimos usar bcrypt instead of argon2 (trade-off de portabilidad).",
        )
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)
        assert result.adrs_created
        # File is at vault/decisions/.
        adr_path = result.adrs_created[0]
        assert adr_path.is_file()
        assert adr_path.parent.name == "decisions"

    def test_overrides_can_reject_all_adrs(self, setup) -> None:  # type: ignore[no-untyped-def]
        setup["session_service"].checkpoint(
            setup["session_id"],
            source=CheckpointSource.CORTEX_SDDWORK,
            note="Decidimos usar bcrypt instead of argon2 (trade-off).",
        )
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        # Explicitly approve an empty subset.
        result = setup["persister"].finalize(
            out, overrides=FinishOverrides(approved_adr_indices=[])
        )
        assert result.adrs_created == []


class TestUnimplementedSurfacedAsNextSteps:
    def test_unimplemented_files_appear_in_next_steps(self, setup) -> None:  # type: ignore[no-untyped-def]
        """A HANDOFF caused by unimplemented files writes them as next-steps."""
        # Don't touch ``src/foo.py`` → reconstruction marks it unimplemented.
        out = _reconstruct(setup)
        assert Path("src/foo.py") in out.unimplemented_files
        result = setup["persister"].finalize(out)
        assert result.final_status is SessionStatus.HANDOFF
        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        # The session template renders next_steps as a bullet list under a
        # "Next Steps" heading; the file path must be there.
        assert "src/foo.py" in body


class TestIdempotence:
    def test_already_closed_returns_existing_paths(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        first = setup["persister"].finalize(out)
        # Second call sees a CLOSED session and short-circuits.
        second = setup["persister"].finalize(out)
        assert second.already_closed is True
        assert second.session_note_path == first.session_note_path
        assert second.final_status == first.final_status


class TestOverrides:
    def test_forced_status_overrides_suggested(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        # Reconstruction suggests CLOSED; we force HANDOFF.
        result = setup["persister"].finalize(
            out, overrides=FinishOverrides(forced_status=SessionStatus.HANDOFF)
        )
        assert result.final_status is SessionStatus.HANDOFF
        record = setup["session_service"].get(setup["session_id"])
        assert record.status is SessionStatus.HANDOFF

    def test_edited_title_used(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(
            out, overrides=FinishOverrides(edited_note_title="Custom Title")
        )
        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        assert "Custom Title" in body


# ---------------------------------------------------------------------------
# Phase 08 / T8.3 — self-review of the about-to-persist draft.
# ---------------------------------------------------------------------------


class _MockReconstruction:
    """Minimal stand-in for ReconstructionOutput; only the two fields
    that ``_self_review_draft`` reads."""

    def __init__(
        self,
        files_touched: list[Path] | None = None,
        verification_results: list[object] | None = None,
    ) -> None:
        self.files_touched = files_touched or []
        self.verification_results = verification_results or []


class _MockHookResult:
    def __init__(self, passed: bool) -> None:
        self.passed = passed


class TestSelfReviewDraft:
    """Pure scan over the draft body. No persistence required."""

    def test_self_review_clean_returns_empty_list(self) -> None:
        from cortex.documenter.persistence import DocumenterPersister

        rec = _MockReconstruction(
            files_touched=[Path("src/foo.py")],
            verification_results=[_MockHookResult(True)],
        )
        body = "src/foo.py was modified to add the new handler. tests pass."
        warnings = DocumenterPersister._self_review_draft(rec, body)  # type: ignore[arg-type]
        assert warnings == []

    def test_self_review_detects_placeholders(self) -> None:
        from cortex.documenter.persistence import DocumenterPersister

        rec = _MockReconstruction()
        body = "implemented handler. TODO: error path. src/foo.py touched."
        warnings = DocumenterPersister._self_review_draft(rec, body)  # type: ignore[arg-type]
        assert any("placeholder" in w.lower() for w in warnings)

    def test_self_review_detects_unreferenced_files(self) -> None:
        from cortex.documenter.persistence import DocumenterPersister

        rec = _MockReconstruction(files_touched=[Path("src/foo.py"), Path("src/bar.py")])
        # Body mentions foo.py but not bar.py.
        body = "src/foo.py was extended."
        warnings = DocumenterPersister._self_review_draft(rec, body)  # type: ignore[arg-type]
        assert any("src/bar.py" in w for w in warnings)

    def test_self_review_detects_unverified_claims(self) -> None:
        from cortex.documenter.persistence import DocumenterPersister

        rec = _MockReconstruction(
            files_touched=[Path("src/foo.py")],
            verification_results=[_MockHookResult(False)],  # nothing passed
        )
        body = "src/foo.py was extended and tests pass cleanly."
        warnings = DocumenterPersister._self_review_draft(rec, body)  # type: ignore[arg-type]
        assert any("verified hook" in w.lower() for w in warnings)


class TestSelfReviewWarningsPropagateToNote:
    """End-to-end: warnings reach the persisted note as tag + next_steps."""

    def test_warnings_propagate_to_note_tags(self, setup) -> None:  # type: ignore[no-untyped-def]
        # Force a TBD placeholder into the checkpoint note so the
        # self-review fires on the draft body.
        setup["session_service"].checkpoint(
            setup["session_id"],
            source=CheckpointSource.CORTEX_SDDWORK,
            note="implemented handler. TBD: error path",
        )
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)

        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        # Tag is in the frontmatter.
        assert "auto-draft" in body
        # Warning text was appended to next_steps.
        assert "self-review" in body.lower()


# ---------------------------------------------------------------------------
# Phase 09.C / T9.C — granular tasks reach the session note + summary.
# ---------------------------------------------------------------------------


class TestDocumenterReportsTaskCompletion:
    def test_task_completion_appears_in_summary(self, setup) -> None:  # type: ignore[no-untyped-def]
        from cortex.session import Task, TaskStatus

        # Decorate the session with three tasks: 1 done, 1 skipped, 1 pending.
        sid = setup["session_id"]
        svc = setup["session_service"]
        svc.add_task(sid, Task(id="T1", description="prep"))
        svc.add_task(sid, Task(id="T2", description="impl"))
        svc.add_task(sid, Task(id="T3", description="docs"))
        svc.update_task_status(sid, "T1", TaskStatus.DONE)
        svc.update_task_status(sid, "T2", TaskStatus.SKIPPED, note="not needed")

        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)

        # Summary line carries the aggregate.
        assert "tasks: 1/3 done" in result.summary
        assert "1 skipped" in result.summary
        # Body has the dedicated section.
        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        assert "## Tasks" in body
        assert "T1 — prep" in body
        assert "T2 — impl" in body
        assert "[done]" in body
        assert "[skipped]" in body

    def test_session_without_tasks_omits_section(self, setup) -> None:  # type: ignore[no-untyped-def]
        _commit_change(setup, "def f(): return 2\n")
        out = _reconstruct(setup)
        result = setup["persister"].finalize(out)
        body = result.session_note_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        # No tasks section when tasks list is empty.
        assert "## Tasks" not in body
        # Summary does not mention tasks.
        assert "tasks:" not in result.summary
