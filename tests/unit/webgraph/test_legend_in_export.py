"""Test that the exported snapshot includes the DocType + edge legend."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cortex.semantic.vault_reader import VaultReader
from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.semantic_source import SemanticSource
from cortex.webgraph.service import WebGraphService


@pytest.fixture
def small_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "decisions").mkdir(parents=True)
    (vault / "decisions" / "ADR-001.md").write_text(
        "---\ntitle: ADR-001\n---\nbody", encoding="utf-8",
    )
    return vault


def test_export_snapshot_injects_legend(small_vault: Path, tmp_path: Path) -> None:
    config = WebGraphConfig()
    embedder = MagicMock()
    embedder.embed = MagicMock(return_value=[0.0] * 384)

    reader = VaultReader(str(small_vault))
    semantic = SemanticSource(
        project_root=tmp_path,
        vault_path=small_vault,
        reader=reader,
        embedder=embedder,
    )

    # Use a stub episodic source: returns no records.
    episodic = MagicMock()
    episodic.load_records = MagicMock(return_value=[])

    service = WebGraphService(
        project_root=tmp_path,
        config=config,
        semantic_source=semantic,
        episodic_source=episodic,
    )
    out_path = tmp_path / "snap.json"
    service.export_snapshot(output_path=out_path, mode="semantic", use_cache=False)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "legend" in payload
    assert "doc_types" in payload["legend"]
    assert "edge_types" in payload["legend"]
    type_slugs = {e["type"] for e in payload["legend"]["doc_types"]}
    assert "adr" in type_slugs
    assert "runbook" in type_slugs


def test_export_snapshot_can_skip_legend(small_vault: Path, tmp_path: Path) -> None:
    config = WebGraphConfig()
    embedder = MagicMock()
    embedder.embed = MagicMock(return_value=[0.0] * 384)
    reader = VaultReader(str(small_vault))
    semantic = SemanticSource(
        project_root=tmp_path,
        vault_path=small_vault,
        reader=reader,
        embedder=embedder,
    )
    episodic = MagicMock()
    episodic.load_records = MagicMock(return_value=[])
    service = WebGraphService(
        project_root=tmp_path,
        config=config,
        semantic_source=semantic,
        episodic_source=episodic,
    )
    out_path = tmp_path / "snap.json"
    service.export_snapshot(
        output_path=out_path, mode="semantic", use_cache=False, include_legend=False,
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "legend" not in payload
