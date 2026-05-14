"""Tests for ``cortex docs vectorization`` CLI subcommands (Fase 06)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
from typer.testing import CliRunner

from cortex.cli.docs_vectorization import app
from cortex.semantic.vector_cache import VECTOR_DIM, VectorCache

runner = CliRunner()


def _patch_resolve(tmp_path: Path, cache_dir_name: str = "vectors"):
    """Patch _resolve_cache so the CLI hits a tmp dir."""
    cache = VectorCache(tmp_path / ".cortex" / cache_dir_name)
    return cache, patch(
        "cortex.cli.docs_vectorization._resolve_cache",
        return_value=cache,
    )


def test_stats_empty_cache(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    with p:
        result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Total entries: 0" in result.stdout


def test_stats_json_output(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    vec = np.random.rand(VECTOR_DIM).astype(np.float32)
    cache.put("fp1", "c1", vec)
    with p:
        result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_entries"] == 1


def test_compact_runs(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    for i in range(3):
        vec = np.random.rand(VECTOR_DIM).astype(np.float32)
        cache.put(f"fp{i}", f"c{i}", vec)
    cache.invalidate("fp0")
    with p:
        result = runner.invoke(app, ["compact"])
    assert result.exit_code == 0
    assert "Compacted" in result.stdout


def test_clear_with_confirmation_yes(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    vec = np.random.rand(VECTOR_DIM).astype(np.float32)
    cache.put("fp1", "c1", vec)
    with p:
        result = runner.invoke(app, ["clear", "--yes"])
    assert result.exit_code == 0
    assert "Cache cleared" in result.stdout
    assert cache.stats().total_entries == 0


def test_clear_aborts_without_confirmation(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    vec = np.random.rand(VECTOR_DIM).astype(np.float32)
    cache.put("fp1", "c1", vec)
    with p:
        result = runner.invoke(app, ["clear"], input="n\n")
    assert result.exit_code != 0
    assert cache.stats().total_entries == 1


def test_clear_empty_cache_skips_prompt(tmp_path: Path) -> None:
    cache, p = _patch_resolve(tmp_path)
    with p:
        result = runner.invoke(app, ["clear"])
    assert result.exit_code == 0
