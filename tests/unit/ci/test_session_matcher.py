"""Tests for :func:`cortex.ci.session_matcher.find_session_for_pr`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.ci.session_matcher import find_session_for_pr
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "x.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def storage(tmp_path: Path) -> SessionStorage:
    return SessionStorage(tmp_path / "sessions")


@pytest.fixture
def service(repo: Path, storage: SessionStorage) -> SessionService:
    return SessionService(storage, repo_root=repo)


def test_explicit_match_wins(service: SessionService, storage: SessionStorage) -> None:
    rec = service.open(spec_id="2026-05-17_a", spec_path=Path("vault/specs/a.md"))
    record, kind = find_session_for_pr(storage, explicit_session_id=rec.session_id)
    assert kind == "explicit"
    assert record is not None
    assert record.session_id == rec.session_id


def test_explicit_unknown_returns_none(storage: SessionStorage) -> None:
    record, kind = find_session_for_pr(storage, explicit_session_id="missing")
    assert kind == "none"
    assert record is None


def test_match_by_base_commit(
    service: SessionService, storage: SessionStorage
) -> None:
    rec = service.open(spec_id="2026-05-17_b", spec_path=Path("vault/specs/b.md"))
    record, kind = find_session_for_pr(storage, base_commit=rec.start_commit)
    assert kind == "by_commit"
    assert record is not None
    assert record.session_id == rec.session_id


def test_match_by_head_branch(
    service: SessionService, storage: SessionStorage
) -> None:
    rec = service.open(spec_id="2026-05-17_c", spec_path=Path("vault/specs/c.md"))
    # The fixture uses "main" as the active branch; we pass it as
    # head_branch to verify the match.
    record, kind = find_session_for_pr(storage, head_branch=rec.start_branch)
    assert kind == "by_branch"
    assert record is not None
    assert record.session_id == rec.session_id


def test_no_match_returns_none(storage: SessionStorage) -> None:
    record, kind = find_session_for_pr(
        storage, base_commit="0" * 40, head_branch="never-existed"
    )
    assert kind == "none"
    assert record is None
