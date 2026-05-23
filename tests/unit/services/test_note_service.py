"""Transactional rollback contract for :class:`NoteService`.

When indexing into the semantic vector store or the episodic memory store
fails *after* the session note has been persisted on disk, the persisted
file must be unlinked and the exception must propagate. This preserves
the framework invariant *"file on disk ⇒ file indexed in memory"*.

The contract was originally enforced by the deleted
``cortex.autopilot.session_writer.IndexingSessionWriter`` (see
``docs/pluggable-middle/fases/_internal/autopilot-audit.md``). Phase 08
T8.1 ports it to :class:`NoteService`, which is the new owner of the
persistence + indexing pipeline after Phase 03.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.services.note_service import NoteService


class _StubSemantic:
    """Test double for :class:`cortex.semantic.vault_reader.VaultReader`."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.indexed: list[str] = []
        self.synced = 0

    def index_file(self, rel_path: str) -> bool:
        if self.fail:
            raise RuntimeError("semantic indexing failed")
        self.indexed.append(rel_path)
        return True

    def sync(self) -> int:
        self.synced += 1
        return 0


class _StubEpisodic:
    """Test double for :class:`cortex.episodic.memory_store.EpisodicMemoryStore`."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.added: list[dict[str, object]] = []

    def add(
        self,
        *,
        content: str,
        memory_type: str,
        tags: list[str] | None = None,
        files: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> object:
        if self.fail:
            raise RuntimeError("episodic add failed")
        self.added.append(
            {
                "content": content,
                "memory_type": memory_type,
                "tags": list(tags or []),
                "files": list(files or []),
                "extra_metadata": dict(extra_metadata or {}),
            }
        )
        return self.added[-1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "sessions").mkdir(parents=True)
    return v


def _make_service(
    vault: Path,
    *,
    semantic: _StubSemantic | None = None,
    episodic: _StubEpisodic | None = None,
) -> NoteService:
    return NoteService(
        vault_path=vault,
        semantic=semantic or _StubSemantic(),  # type: ignore[arg-type]
        episodic=episodic or _StubEpisodic(),  # type: ignore[arg-type]
    )


class TestRollbackContract:
    """Indexing failure must roll back the on-disk file (T8.1)."""

    def test_indexing_success_preserves_file(self, vault: Path) -> None:
        semantic = _StubSemantic()
        episodic = _StubEpisodic()
        svc = _make_service(vault, semantic=semantic, episodic=episodic)

        path = svc.create(
            title="happy path",
            spec_summary="should survive",
            files_touched=["src/foo.py"],
        )

        assert path.is_file()
        assert len(semantic.indexed) == 1
        assert len(episodic.added) == 1

    def test_indexing_failure_unlinks_persisted_file(self, vault: Path) -> None:
        svc = _make_service(vault, semantic=_StubSemantic(fail=True))

        with pytest.raises(RuntimeError, match="semantic indexing"):
            svc.create(
                title="rollback semantic",
                spec_summary="ensure rollback works",
                files_touched=["src/foo.py"],
            )

        # No orphan note allowed.
        assert list((vault / "sessions").glob("*.md")) == []

    def test_indexing_failure_propagates_exception(self, vault: Path) -> None:
        """Caller must observe the failure — no silent success."""
        svc = _make_service(vault, semantic=_StubSemantic(fail=True))

        with pytest.raises(RuntimeError) as exc_info:
            svc.create(
                title="propagate",
                spec_summary="caller must see the exception",
                files_touched=["src/foo.py"],
            )

        # Bubbles up unchanged from the inner store.
        assert "semantic indexing" in str(exc_info.value)

    def test_episodic_failure_also_rolls_back(self, vault: Path) -> None:
        svc = _make_service(vault, episodic=_StubEpisodic(fail=True))

        with pytest.raises(RuntimeError, match="episodic add"):
            svc.create(
                title="rollback episodic",
                spec_summary="ensure rollback works",
                files_touched=["src/foo.py"],
            )

        assert list((vault / "sessions").glob("*.md")) == []

    def test_remember_false_skips_episodic_path(self, vault: Path) -> None:
        """``remember=False`` must not trigger an episodic write nor roll back."""
        episodic = _StubEpisodic(fail=True)
        svc = _make_service(vault, episodic=episodic)

        path = svc.create(
            title="no remember",
            spec_summary="should still persist",
            files_touched=["src/foo.py"],
            remember=False,
        )

        assert path.is_file()
        assert episodic.added == []
