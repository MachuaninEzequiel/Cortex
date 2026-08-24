"""Tests de cortex.embedders.fastembedder — caché persistente (Obra 04 cierre)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.embedders.fastembedder import cortex_fastembed_cache


def test_cache_default_en_homedir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    esperado = Path.home() / ".cache" / "cortex" / "fastembed"
    assert cortex_fastembed_cache() == esperado


def test_cache_respeta_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", "/tmp/mi-cache-custom")
    assert cortex_fastembed_cache() == Path("/tmp/mi-cache-custom")


def test_cache_nunca_apunta_a_tmpfs_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guardia contra regresión al default upstream /tmp/fastembed_cache (tmpfs)."""
    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    ruta = str(cortex_fastembed_cache())
    assert not ruta.startswith("/tmp"), "el cache no debe vivir en tmpfs (RAM)"
