"""Tests for the SessionService integration in :class:`SpecService`.

Phase 00 — T0.6: ``cortex create-spec`` opens a Session automatically.
This integration must:
    1. Open a Session whose ``session_id`` is the stem of the spec file.
    2. Never abort spec creation if Session opening fails (defensive).
    3. Behave like the pre-Pluggable-Middle SpecService when no
       ``session_service`` is injected (backward compatibility).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.services.spec_service import SpecService
from cortex.session import SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _DummySemantic:
    """Minimal stand-in for VaultReader (only ``index_file`` is invoked)."""

    def __init__(self) -> None:
        self.indexed: list[str] = []

    def index_file(self, rel_path: str) -> bool:
        self.indexed.append(rel_path)
        return True

    def sync(self) -> int:
        return 0


class _DummyEpisodic:
    """Minimal stand-in for EpisodicMemoryStore."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add(self, **kwargs: object) -> object:
        self.entries.append(kwargs)
        return object()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def session_service(tmp_path: Path, git_repo: Path) -> SessionService:
    storage = SessionStorage(tmp_path / "sessions")
    return SessionService(storage, repo_root=git_repo)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    v.mkdir()
    return v


def _make_spec_service(
    vault: Path,
    *,
    session_service: SessionService | None,
) -> SpecService:
    return SpecService(
        vault_path=vault,
        semantic=_DummySemantic(),  # type: ignore[arg-type]
        episodic=_DummyEpisodic(),  # type: ignore[arg-type]
        session_service=session_service,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_spec_opens_session(
    vault: Path,
    session_service: SessionService,
) -> None:
    service = _make_spec_service(vault, session_service=session_service)
    result = service.create(
        title="Auth JWT Refresh",
        goal="Implement refresh tokens",
        requirements=["rotate every 7 days"],
    )
    # The spec file exists.
    assert result.path.is_file()
    # A Session was opened with the spec stem as session_id.
    active = session_service.get_active()
    assert active is not None
    assert active.session_id == result.path.stem
    assert active.status is SessionStatus.OPEN
    assert active.spec_summary == "Implement refresh tokens"
    # The result also carries the opened session for direct inspection.
    assert result.session is not None
    assert result.session.session_id == active.session_id


def test_create_spec_without_session_service_works_unchanged(vault: Path) -> None:
    service = _make_spec_service(vault, session_service=None)
    result = service.create(title="No Session", goal="just a spec")
    assert result.path.is_file()
    assert result.session is None  # nobody opened anything


def test_create_spec_succeeds_when_session_open_fails(
    vault: Path,
    session_service: SessionService,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sabotage SessionService.open to always raise.
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(session_service, "open", _boom)

    service = _make_spec_service(vault, session_service=session_service)
    import logging

    with caplog.at_level(logging.WARNING, logger="cortex.services.spec_service"):
        result = service.create(title="Resilient", goal="never block spec")
    # Spec was persisted despite the SessionService failure.
    assert result.path.is_file()
    # The session field is None because open() blew up.
    assert result.session is None
    # A warning was logged with actionable context.
    assert any("Session" in rec.message for rec in caplog.records)


def test_session_summary_falls_back_to_title_when_goal_is_empty(
    vault: Path,
    session_service: SessionService,
) -> None:
    service = _make_spec_service(vault, session_service=session_service)
    service.create(title="Only Title", goal="")
    active = session_service.get_active()
    assert active is not None
    assert active.spec_summary == "Only Title"
