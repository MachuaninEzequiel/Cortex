"""Defensive-path tests for canonical writers (Fase 13 backlog cleanup).

Covers branches that the higher-level writer tests skip because they
exercise the writer pipeline via the legacy shim or the happy path. These
tests address the 9 defensive lines flagged in Fase 03/04 REALIZACION.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cortex.documentation.data import HUData, SessionData, SpecData
from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import SchemaValidationError
from cortex.documentation.writers import (
    _coerce_status,
    _next_number,
    write_hu_note,
    write_session_note_canonical,
    write_spec_note_canonical,
)


class _FakeVault:
    def __init__(self, root: Path) -> None:
        self._root = root
        self.indexed: list[str] = []

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        self.indexed.append(relative_path)
        return True


# ---------------------------------------------------------------------------
# _coerce_status
# ---------------------------------------------------------------------------


def test_coerce_status_returns_requested_when_valid() -> None:
    assert _coerce_status(DocType.ADR, "accepted") == "accepted"


def test_coerce_status_falls_back_when_empty() -> None:
    assert _coerce_status(DocType.ADR, "") == "accepted"  # first alpha-sorted


def test_coerce_status_falls_back_when_unknown() -> None:
    assert _coerce_status(DocType.ADR, "ratified") == "accepted"


# ---------------------------------------------------------------------------
# _next_number
# ---------------------------------------------------------------------------


def test_next_number_missing_folder(tmp_path: Path) -> None:
    import re
    pattern = re.compile(r"^ADR-(\d+)")
    assert _next_number(tmp_path / "missing", pattern) == 1


def test_next_number_skips_subdirectories(tmp_path: Path) -> None:
    import re
    folder = tmp_path / "decisions"
    folder.mkdir()
    (folder / "subdir").mkdir()  # entry that is not a file
    (folder / "ADR-001-foo.md").write_text("x", encoding="utf-8")
    pattern = re.compile(r"^ADR-(\d+)")
    assert _next_number(folder, pattern) == 2


def test_next_number_handles_malformed_match(tmp_path: Path) -> None:
    """A file whose regex group is non-numeric must not crash the helper."""
    import re
    folder = tmp_path / "decisions"
    folder.mkdir()
    # Crafted regex group=non-digit so ``int()`` raises ValueError -> branch.
    (folder / "ADR-bad-foo.md").write_text("x", encoding="utf-8")
    pattern = re.compile(r"^ADR-([A-Za-z0-9]+)")
    assert _next_number(folder, pattern) == 1


# ---------------------------------------------------------------------------
# write_session_note_canonical
# ---------------------------------------------------------------------------


def test_session_canonical_requires_session_id(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = SessionData(title="t", session_id="")
    with pytest.raises(SchemaValidationError, match="session_id"):
        write_session_note_canonical(data, vault=vault)


def test_session_canonical_writes_and_indexes(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = SessionData(title="Feat A", session_id="abc123", spec_summary="x")
    path = write_session_note_canonical(data, vault=vault)
    assert path.exists()
    assert vault.indexed
    assert path.parent.name == "sessions"


# ---------------------------------------------------------------------------
# write_spec_note_canonical
# ---------------------------------------------------------------------------


def test_spec_canonical_writes(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = SpecData(title="Refactor X", goal="g")
    path = write_spec_note_canonical(data, vault=vault)
    assert path.exists()
    assert path.parent.name == "specs"


# ---------------------------------------------------------------------------
# write_hu_note canonical
# ---------------------------------------------------------------------------


def test_hu_canonical_requires_external_id(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = HUData(title="t", external_id="", source="linear", kind="story")
    with pytest.raises(SchemaValidationError, match="external_id"):
        write_hu_note(data, vault=vault)


def test_hu_canonical_requires_source(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = HUData(title="t", external_id="PROJ-1", source="", kind="story")
    with pytest.raises(SchemaValidationError, match="source"):
        write_hu_note(data, vault=vault)


def test_hu_canonical_writes(tmp_path: Path) -> None:
    vault = _FakeVault(tmp_path)
    data = HUData(
        title="Import PROJ-1",
        external_id="PROJ-1",
        source="linear",
        kind="story",
        description="d",
    )
    path = write_hu_note(data, vault=vault)
    assert path.exists()
    assert path.parent.name == "hu"


# ---------------------------------------------------------------------------
# _write_note: relative_to fallback for paths outside vault.path
# ---------------------------------------------------------------------------


def test_write_note_falls_back_when_path_outside_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the resolved target lives outside ``vault.path``, the rel_path
    fallback in ``_write_note`` must not crash and still trigger indexing."""

    # Build a vault whose ``path`` is a sibling of the actual write target.
    class _SiblingVault:
        def __init__(self, vault_root: Path) -> None:
            self._root = vault_root
            self.indexed: list[str] = []

        @property
        def path(self) -> Path:
            return self._root

        def index_file(self, rel_path: str) -> bool:
            self.indexed.append(rel_path)
            return True

    vault_root = tmp_path / "real_vault"
    vault_root.mkdir()
    vault = _SiblingVault(vault_root)

    # Force the writer to resolve to an unrelated location by monkeypatching
    # the routing target resolver.
    from cortex.documentation import writers as writers_mod
    real_resolve = writers_mod.resolve_target_path

    def stub_resolve(spec, ctx, root, vault_scope="local", project_id=None):
        # Return a path that is not relative to ``vault.path``.
        return tmp_path / "elsewhere" / "specs" / "x.md"

    monkeypatch.setattr(writers_mod, "resolve_target_path", stub_resolve)

    data = SpecData(title="Off path", goal="g")
    path = write_spec_note_canonical(data, vault=vault)

    assert path.exists()
    assert vault.indexed, "indexer must still be invoked"
    assert "elsewhere" in vault.indexed[0] or vault.indexed[0].startswith("\\") or ":" in vault.indexed[0]
