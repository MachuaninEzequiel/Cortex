"""Tests for cortex.autopilot.session_writer."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from cortex.autopilot.models import AutopilotSessionState, SessionDraft
from cortex.autopilot.session_writer import (
    IndexingSessionWriter,
    SessionWriter,
    VaultSessionWriter,
    _slugify,
    is_indexing_writer,
)
from cortex.security.paths import PathSecurityError


def _state(**overrides) -> AutopilotSessionState:
    base = {
        "project_root": "/repo",
        "workspace_root": "/repo/.cortex",
        "session_id": "test123abc",
        "mode": "assist",
        "status": "implementation_seen",
    }
    base.update(overrides)
    return AutopilotSessionState(**base)


def _draft(**overrides) -> SessionDraft:
    base = {
        "title": "Sample autopilot run",
        "body": "Implemented user profile endpoint.",
        "confidence": "medium",
        "warnings": [],
        "source_events": 3,
    }
    base.update(overrides)
    return SessionDraft(**base)


class TestSlugify:
    def test_basic(self) -> None:
        assert _slugify("Fix Login Bug") == "fix-login-bug"

    def test_punctuation_stripped(self) -> None:
        assert _slugify("Hello, world! (v2)") == "hello-world-v2"

    def test_empty_fallback(self) -> None:
        assert _slugify("") == "autopilot-session"
        assert _slugify("   ") == "autopilot-session"


class TestVaultSessionWriter:
    def test_writes_file_with_frontmatter(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(_state(), _draft())

        assert path.exists()
        assert path.parent == tmp_path / "vault" / "sessions"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert 'title: "Sample autopilot run"' in content
        assert "session_id: test123abc" in content
        assert "tags: [session, autopilot]" in content
        assert "confidence: medium" in content
        assert "Implemented user profile endpoint." in content

    def test_auto_draft_confidence_adds_tag(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(_state(), _draft(confidence="auto-draft"))
        content = path.read_text(encoding="utf-8")
        assert "tags: [session, autopilot, auto-draft]" in content
        assert "confidence: auto-draft" in content

    def test_warnings_section(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(
            _state(),
            _draft(warnings=["Placeholder found: TODO", "File missing from draft"]),
        )
        content = path.read_text(encoding="utf-8")
        assert "## Warnings" in content
        assert "- Placeholder found: TODO" in content
        assert "- File missing from draft" in content

    def test_filename_includes_session_id_and_slug(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(_state(session_id="abcdef"), _draft(title="Multi-word title"))
        # filename = <date>_<sid>_<slug>.md
        assert "_abcdef_" in path.name
        assert path.name.endswith("multi-word-title.md")

    def test_distinct_sessions_do_not_collide(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        p1 = writer.write(_state(session_id="aaa111"), _draft())
        p2 = writer.write(_state(session_id="bbb222"), _draft())
        assert p1 != p2
        assert p1.exists() and p2.exists()

    def test_yaml_double_quote_escaped(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(_state(), _draft(title='Fix "quoted" bug'))
        content = path.read_text(encoding="utf-8")
        assert 'title: "Fix \\"quoted\\" bug"' in content

    def test_creates_sessions_dir_if_missing(self, tmp_path: Path) -> None:
        vault = tmp_path / "fresh-vault"
        assert not vault.exists()
        writer = VaultSessionWriter(vault)
        path = writer.write(_state(), _draft())
        assert (vault / "sessions").is_dir()
        assert path.exists()

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        path = writer.write(_state(), _draft())
        assert path.is_absolute()


class TestProtocolConformance:
    """``VaultSessionWriter`` must satisfy the ``SessionWriter`` protocol."""

    def test_vault_writer_is_session_writer(self, tmp_path: Path) -> None:
        writer = VaultSessionWriter(tmp_path / "vault")
        assert isinstance(writer, SessionWriter)

    def test_indexing_writer_is_session_writer(self, tmp_path: Path) -> None:
        inner = VaultSessionWriter(tmp_path / "vault")
        idx = IndexingSessionWriter(
            inner=inner,
            vault_path=tmp_path / "vault",
            semantic=_StubSemantic(),
            episodic=_StubEpisodic(),
        )
        assert isinstance(idx, SessionWriter)


# ---------------------------------------------------------------------------
# IndexingSessionWriter — mandatory indexing decorator
# ---------------------------------------------------------------------------


class _StubSemantic:
    """In-memory VaultReader stub. Records every ``index_file`` call."""

    def __init__(self, fail: bool = False) -> None:
        self.indexed: list[str] = []
        self._fail = fail

    def index_file(self, rel_path: str) -> bool:
        if self._fail:
            raise RuntimeError("semantic indexing intentionally failed")
        self.indexed.append(rel_path)
        return True


class _StubEpisodic:
    """In-memory EpisodicMemoryStore stub. Records ``add`` calls."""

    def __init__(self, fail: bool = False) -> None:
        self.added: list[dict] = []
        self._fail = fail

    def add(
        self,
        *,
        content: str,
        memory_type: str = "general",
        tags: list[str] | None = None,
        files: list[str] | None = None,
        extra_metadata: dict | None = None,
    ):
        if self._fail:
            raise RuntimeError("episodic add intentionally failed")
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


class TestIndexingSessionWriter:
    def test_writes_then_indexes_semantic_and_episodic(
        self, tmp_path: Path
    ) -> None:
        vault = tmp_path / "vault"
        semantic = _StubSemantic()
        episodic = _StubEpisodic()
        writer = IndexingSessionWriter(
            inner=VaultSessionWriter(vault),
            vault_path=vault,
            semantic=semantic,
            episodic=episodic,
            context_metadata={"project_id": "demo", "branch": "main"},
        )

        path = writer.write(_state(changed_files=["src/a.py"]), _draft())

        assert path.exists()
        # Selective semantic index hit with the relative path.
        rel = str(path.relative_to(vault))
        assert semantic.indexed == [rel]
        # Episodic entry exists with session tags and runtime metadata.
        assert len(episodic.added) == 1
        entry = episodic.added[0]
        assert entry["memory_type"] == "session"
        assert "session" in entry["tags"] and "autopilot" in entry["tags"]
        assert "auto-draft" not in entry["tags"]
        assert entry["files"] == ["src/a.py"]
        assert entry["extra_metadata"]["session_id"] == "test123abc"
        assert entry["extra_metadata"]["project_id"] == "demo"
        assert entry["extra_metadata"]["session_note_path"] == str(path)

    def test_auto_draft_propagates_to_episodic_tag(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        semantic = _StubSemantic()
        episodic = _StubEpisodic()
        writer = IndexingSessionWriter(
            inner=VaultSessionWriter(vault),
            vault_path=vault,
            semantic=semantic,
            episodic=episodic,
        )
        writer.write(_state(), _draft(confidence="auto-draft"))
        assert "auto-draft" in episodic.added[0]["tags"]

    def test_indexing_failure_rolls_back_file(self, tmp_path: Path) -> None:
        """Semantic failure must unlink the persisted file (transactional)."""
        vault = tmp_path / "vault"
        writer = IndexingSessionWriter(
            inner=VaultSessionWriter(vault),
            vault_path=vault,
            semantic=_StubSemantic(fail=True),
            episodic=_StubEpisodic(),
        )
        with pytest.raises(RuntimeError, match="semantic indexing"):
            writer.write(_state(), _draft())
        # No orphan file must remain.
        sessions_dir = vault / "sessions"
        if sessions_dir.exists():
            assert list(sessions_dir.glob("*.md")) == []

    def test_episodic_failure_also_rolls_back(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        semantic = _StubSemantic()
        writer = IndexingSessionWriter(
            inner=VaultSessionWriter(vault),
            vault_path=vault,
            semantic=semantic,
            episodic=_StubEpisodic(fail=True),
        )
        with pytest.raises(RuntimeError, match="episodic add"):
            writer.write(_state(), _draft())
        sessions_dir = vault / "sessions"
        if sessions_dir.exists():
            assert list(sessions_dir.glob("*.md")) == []

    def test_is_indexing_writer_helper(self, tmp_path: Path) -> None:
        vault_only = VaultSessionWriter(tmp_path / "vault")
        idx = IndexingSessionWriter(
            inner=vault_only,
            vault_path=tmp_path / "vault",
            semantic=_StubSemantic(),
            episodic=_StubEpisodic(),
        )
        assert is_indexing_writer(idx) is True
        assert is_indexing_writer(vault_only) is False
        assert is_indexing_writer(None) is False
