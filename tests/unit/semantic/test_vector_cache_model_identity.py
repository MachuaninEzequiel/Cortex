"""Regression tests: A1 (parametric dim) + A3 (model identity in cache).

Spec: docs/transformacion/04-VECTORIZACION-E-IDIOMA.md Fase A.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest

from cortex.documentation.common import compute_fingerprint
from cortex.semantic import vector_cache as vc_module
from cortex.semantic.vector_cache import VectorCache, cache_fingerprint


def _vec(dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(dim).astype(np.float32)


# ---------------------------------------------------------------------------
# A1 — VECTOR_DIM constant is gone; dim is parametric
# ---------------------------------------------------------------------------


def test_vector_dim_constant_removed() -> None:
    """The hardcoded 384-dim constant must not exist anymore."""
    assert not hasattr(vc_module, "VECTOR_DIM")


def test_explicit_dim_768_roundtrip(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "v768", model_name="e5-base", dim=768)
    v = _vec(768, 1)
    cache.put("fp-1", "chunk-1", v)
    out = cache.get("fp-1")
    assert out is not None
    np.testing.assert_array_equal(out, v)


def test_wrong_dim_rejected(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "v", model_name="m", dim=384)
    with pytest.raises(ValueError, match="shape"):
        cache.put("fp-x", "chunk-x", _vec(768))


def test_dim_derived_from_first_vector(tmp_path: Path) -> None:
    """dim=None → derived from the first vector, then enforced."""
    cache = VectorCache(tmp_path / "v", model_name="m")
    cache.put("fp-a", "c-a", _vec(1024, 2))
    with pytest.raises(ValueError, match="shape"):
        cache.put("fp-b", "c-b", _vec(384, 3))
    # The good entry survives the rejected one.
    out = cache.get("fp-a")
    assert out is not None and out.shape == (1024,)


def test_dim_persisted_across_reload(tmp_path: Path) -> None:
    d = tmp_path / "v"
    VectorCache(d, model_name="m").put("fp", "c", _vec(768, 4))
    reloaded = VectorCache(d, model_name="m")
    out = reloaded.get("fp")
    assert out is not None and out.shape == (768,)


def test_default_still_384_compatible(tmp_path: Path) -> None:
    """Retrocompat: default constructor accepts 384-dim MiniLM vectors."""
    cache = VectorCache(tmp_path / "v")
    v = _vec(384, 5)
    cache.put("fp", "c", v)
    np.testing.assert_array_equal(cache.get("fp"), v)


# ---------------------------------------------------------------------------
# A3 — model identity invalidates the cache
# ---------------------------------------------------------------------------


def test_fingerprint_salted_by_model_name() -> None:
    text = "same body text"
    fa = cache_fingerprint("model-a", text)
    fb = cache_fingerprint("model-b", text)
    assert fa != fb
    assert fa != compute_fingerprint(text)  # not the bare content hash
    assert cache_fingerprint("model-a", text) == fa  # deterministic


def test_same_text_other_model_is_miss(tmp_path: Path) -> None:
    """Same embedding_text under model B must be a forced miss."""
    d = tmp_path / "v"
    ca = VectorCache(d, model_name="model-a")
    fa = cache_fingerprint("model-a", "hola mundo")
    ca.put(fa, "chunk", _vec(384, 6))
    assert ca.get(fa) is not None

    fb = cache_fingerprint("model-b", "hola mundo")
    cb = VectorCache(d, model_name="model-b")
    assert cb.get(fb) is None


def test_header_model_mismatch_resets(tmp_path: Path, caplog) -> None:
    """Opening a cache dir built by another model resets it with a WARNING."""
    d = tmp_path / "v"
    VectorCache(d, model_name="model-a").put("fp", "c", _vec(384, 7))

    with caplog.at_level(logging.WARNING, logger="cortex.semantic.vector_cache"):
        cb = VectorCache(d, model_name="model-b")
    assert len(cb) == 0
    assert any("model-a" in r.message and "model-b" in r.message for r in caplog.records)

    # ...and it must be usable for the new model without stale reads.
    cb.put("fp2", "c2", _vec(384, 8))
    assert cb.get("fp") is None
    assert cb.get("fp2") is not None
