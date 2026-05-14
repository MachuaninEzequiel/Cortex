"""Tests for SemanticSource metadata enrichment (Fase 09)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cortex.semantic.vault_reader import VaultReader
from cortex.webgraph.semantic_source import (
    SemanticSource,
    _doc_type_from_rel_path,
)


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "decisions").mkdir(parents=True)
    (vault / "runbooks").mkdir()
    (vault / "sessions").mkdir()
    (vault / "decisions" / "ADR-007-foo.md").write_text(
        "---\ntitle: ADR-007\n---\nbody", encoding="utf-8",
    )
    (vault / "decisions" / "DEC-2026-05-14-foo.md").write_text(
        "---\ntitle: DEC foo\n---\nbody", encoding="utf-8",
    )
    (vault / "runbooks" / "RB-deploy.md").write_text(
        "---\ntitle: Deploy\n---\nbody", encoding="utf-8",
    )
    (vault / "sessions" / "2026-05-14_x.md").write_text(
        "---\ntitle: Session X\n---\nbody", encoding="utf-8",
    )
    return vault


@pytest.fixture
def fake_embedder() -> MagicMock:
    fake = MagicMock()
    fake.embed = MagicMock(return_value=[0.0] * 384)
    return fake


# ---------------------------------------------------------------------------
# _doc_type_from_rel_path
# ---------------------------------------------------------------------------


def test_path_to_doc_type_adr() -> None:
    assert _doc_type_from_rel_path("decisions/ADR-007-foo.md") == "adr"


def test_path_to_doc_type_decision_non_adr() -> None:
    assert _doc_type_from_rel_path("decisions/DEC-2026-05-14-foo.md") == "decision"


def test_path_to_doc_type_runbook() -> None:
    assert _doc_type_from_rel_path("runbooks/RB-deploy.md") == "runbook"


def test_path_to_doc_type_session() -> None:
    assert _doc_type_from_rel_path("sessions/2026-05-14_x.md") == "session"


def test_path_to_doc_type_unknown_returns_none() -> None:
    assert _doc_type_from_rel_path("random/x.md") is None


def test_path_to_doc_type_handles_backslashes() -> None:
    assert _doc_type_from_rel_path("decisions\\ADR-001.md") == "adr"


# ---------------------------------------------------------------------------
# SemanticSource.load_records metadata enrichment
# ---------------------------------------------------------------------------


def test_semantic_source_metadata_includes_doc_type(tmp_path: Path, fake_embedder: MagicMock) -> None:
    vault = _make_vault(tmp_path)
    reader = VaultReader(str(vault))
    source = SemanticSource(
        project_root=tmp_path, vault_path=vault, reader=reader, embedder=fake_embedder,
    )
    records = source.load_records(include_embeddings=False)
    by_path = {r.rel_path: r for r in records}

    adr_rec = by_path["decisions/ADR-007-foo.md"]
    assert adr_rec.metadata["doc_type"] == "adr"
    # Color/shape come from the canonical routing table.
    assert adr_rec.metadata["color"].startswith("#")
    assert adr_rec.metadata["shape"] != ""

    dec_rec = by_path["decisions/DEC-2026-05-14-foo.md"]
    assert dec_rec.metadata["doc_type"] == "decision"

    rb_rec = by_path["runbooks/RB-deploy.md"]
    assert rb_rec.metadata["doc_type"] == "runbook"


def test_semantic_source_metadata_vault_scope_default(tmp_path: Path, fake_embedder: MagicMock) -> None:
    vault = _make_vault(tmp_path)
    reader = VaultReader(str(vault))
    source = SemanticSource(
        project_root=tmp_path, vault_path=vault, reader=reader, embedder=fake_embedder,
    )
    records = source.load_records(include_embeddings=False)
    assert all(r.metadata["vault_scope"] == "local" for r in records)
