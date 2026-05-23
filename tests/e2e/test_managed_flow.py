"""E2E tests for Managed mode (Phase 02 / T2.6).

Validates the full flow where ``cortex-SDDwork`` (and optionally the
explorer / implementer subagents) emit checkpoints — instead of the old
YAML AgentHandoff — and the documenter consumes them via the same
``cortex finish-session`` path used by BYO mode.

The four scenarios cover the contract described in
``docs/pluggable-middle/fases/02-SDDWORK-MIGRATION.md``:

- Fast Track + single SDDwork checkpoint → CLOSED + mode=managed
- Deep Track (explorer + implementer + SDDwork checkpoints) → CLOSED
  with 3 checkpoints recorded, all surfaced into the session note
- Verification hook failing → HANDOFF
- ``cortex session checkpoint`` without active session → friendly error

The tests drive the CLI surface end-to-end, mimicking what an IDE-driven
subagent would do (emit a checkpoint via MCP / CLI, then let the user
run ``cortex finish-session``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.session import SessionMode, SessionStatus

runner = CliRunner()
PY = sys.executable


# ---------------------------------------------------------------------------
# Fixture: Cortex-shaped project (same as BYO test fixture but reused here).
# ---------------------------------------------------------------------------


@pytest.fixture
def managed_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    (repo / "src").mkdir()
    (repo / "src" / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "vault" / "sessions").mkdir()
    (cortex_dir / "vault" / "decisions").mkdir()
    (cortex_dir / "sessions").mkdir()
    (cortex_dir / "memory").mkdir()

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    monkeypatch.chdir(repo)
    return {"repo": repo, "cortex": cortex_dir}


def _create_spec(
    title: str,
    files: list[str],
    hook_command: str = f'{PY} -c "exit(0)"',
    hook_name: str = "smoke",
) -> None:
    args = [
        "create-spec",
        "--title",
        title,
        "--goal",
        f"Goal of {title}",
        "--verification-hook",
        f"name={hook_name};command={hook_command}",
    ]
    for f in files:
        args.extend(["--file", f])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"create-spec failed: {result.stdout}\n{result.stderr}"


def _commit(repo: Path, message: str = "edit") -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


def _checkpoint_via_python(
    cortex_dir: Path,
    repo: Path,
    *,
    source: str,
    verified: list[str] | None = None,
    note: str = "",
    artifacts: list[str] | None = None,
) -> None:
    """Emit a checkpoint using SessionService directly.

    The MCP tool is exercised in unit tests; here we use the Python API
    so the test does not depend on a running MCP server.
    """
    from cortex.session import CheckpointSource
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage

    storage = SessionStorage(cortex_dir / "sessions")
    service = SessionService(storage, repo_root=repo)
    active = service.get_active()
    assert active is not None, "expected active session before checkpoint"
    service.checkpoint(
        active.session_id,
        source=CheckpointSource(source),
        verified_claims=verified or [],
        artifacts_touched=artifacts or [],
        note=note,
    )


def _finish(*extra_args: str) -> dict[str, object]:
    result = runner.invoke(app, ["finish-session", "--json", *extra_args])
    assert result.exit_code == 0, f"finish-session failed: {result.stdout}\n{result.stderr}"
    return json.loads(result.stdout)


def _session_record(cortex_dir: Path, session_id: str):  # type: ignore[no-untyped-def]
    from cortex.session.storage import SessionStorage

    storage = SessionStorage(cortex_dir / "sessions")
    return storage.load(session_id)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestManagedFlow:
    def test_fast_track_single_sddwork_checkpoint(
        self, managed_project: dict[str, Path]
    ) -> None:
        """Fast Track: SDDwork emite UN checkpoint y el user corre finish."""
        repo = managed_project["repo"]
        cortex_dir = managed_project["cortex"]

        _create_spec("Fast track demo", files=["src/calculator.py"])
        _commit(repo, "add spec")

        # Simulate SDDwork doing the edit + emitting a checkpoint.
        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b\ndef mul(a, b): return a * b\n",
            encoding="utf-8",
        )
        _commit(repo, "add mul")
        _checkpoint_via_python(
            cortex_dir,
            repo,
            source="cortex-SDDwork",
            verified=["mul added; tests pass"],
            artifacts=["src/calculator.py"],
            note="Fast Track: cosmetic add, no ADR needed.",
        )

        payload = _finish()
        assert payload["final_status"] == SessionStatus.CLOSED.value

        # The session record must reflect mode=MANAGED.
        record = _session_record(cortex_dir, str(payload["session_id"]))
        assert record.mode is SessionMode.MANAGED
        assert any(cp.source.value == "cortex-SDDwork" for cp in record.checkpoints)

        # The checkpoint note surfaces into the session note body.
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")  # type: ignore[arg-type]
        assert "Fast Track" in body or "cosmetic add" in body

    def test_deep_track_three_subagents(
        self, managed_project: dict[str, Path]
    ) -> None:
        """Deep Track: explorer + implementer + SDDwork emiten checkpoint cada uno."""
        repo = managed_project["repo"]
        cortex_dir = managed_project["cortex"]

        _create_spec(
            "Deep track demo",
            files=["src/calculator.py"],
        )
        _commit(repo, "add spec")

        # Explorer checkpoint (read-only).
        _checkpoint_via_python(
            cortex_dir,
            repo,
            source="cortex-code-explorer",
            verified=["calculator.py has only `add`"],
            note="implementer: introduce `sub` next to `add`.",
        )

        # Implementer does the edit + commits + checkpoint.
        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b\ndef sub(a, b): return a - b\n",
            encoding="utf-8",
        )
        _commit(repo, "implement sub")
        _checkpoint_via_python(
            cortex_dir,
            repo,
            source="cortex-code-implementer",
            verified=["calculator.py: sub added"],
            artifacts=["src/calculator.py"],
            note="documenter: candidato a ADR? No — decision trivial.",
        )

        # SDDwork wraps up.
        _checkpoint_via_python(
            cortex_dir,
            repo,
            source="cortex-SDDwork",
            verified=["Deep Track complete: explorer + implementer ran"],
            note="documenter: 3 checkpoints; nothing surprising.",
        )

        payload = _finish()
        assert payload["final_status"] == SessionStatus.CLOSED.value

        record = _session_record(cortex_dir, str(payload["session_id"]))
        assert record.mode is SessionMode.MANAGED
        sources = {cp.source.value for cp in record.checkpoints}
        assert sources == {
            "cortex-code-explorer",
            "cortex-code-implementer",
            "cortex-SDDwork",
        }

        # Notes from all three flow into the session note body.
        # Each `note` field of the checkpoints ends up under "Key Decisions"
        # (built by the persister from ``raw_checkpoints[*].note``).
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")  # type: ignore[arg-type]
        for needle in (
            "introduce `sub`",  # explorer note
            "candidato a ADR",  # implementer note
            "nothing surprising",  # SDDwork note
        ):
            assert needle in body, f"missing {needle!r} in session note"

    def test_failing_verification_yields_handoff(
        self, managed_project: dict[str, Path]
    ) -> None:
        """Hook que falla → status=HANDOFF aun con checkpoint."""
        repo = managed_project["repo"]
        cortex_dir = managed_project["cortex"]

        _create_spec(
            "Managed failing hook",
            files=["src/calculator.py"],
            hook_command=f'{PY} -c "exit(1)"',
            hook_name="must-fail",
        )
        _commit(repo, "add spec")

        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b + 0\n", encoding="utf-8"
        )
        _commit(repo, "edit")
        _checkpoint_via_python(
            cortex_dir,
            repo,
            source="cortex-SDDwork",
            verified=["edit applied"],
            artifacts=["src/calculator.py"],
            note="hook may fail; documenter decides.",
        )

        payload = _finish()
        assert payload["final_status"] == SessionStatus.HANDOFF.value
        record = _session_record(cortex_dir, str(payload["session_id"]))
        assert record.status is SessionStatus.HANDOFF
        assert record.mode is SessionMode.MANAGED

    def test_checkpoint_without_active_session_errors(
        self, managed_project: dict[str, Path]
    ) -> None:
        """If a subagent tries to checkpoint with no active session → error."""
        # Don't open any session.
        from cortex.session.errors import SessionNotFound
        from cortex.session.service import SessionService
        from cortex.session.storage import SessionStorage

        storage = SessionStorage(managed_project["cortex"] / "sessions")
        service = SessionService(storage, repo_root=managed_project["repo"])
        assert service.get_active() is None

        # Attempting to checkpoint a non-existent session id raises.
        with pytest.raises(SessionNotFound):
            from cortex.session import CheckpointSource

            service.checkpoint(
                "2026-05-16_does-not-exist",
                source=CheckpointSource.CORTEX_SDDWORK,
                note="should fail",
            )
