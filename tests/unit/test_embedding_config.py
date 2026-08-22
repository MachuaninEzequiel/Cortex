"""Tests Obra 04 Fase C — per-language embedding configuration."""

from __future__ import annotations

import pytest

from cortex.core import (
    CortexConfig,
    EmbeddingConfig,
    EmbeddingLanguageConfig,
    embedding_block_active,
    resolve_embedder,
    resolve_language_for_text,
)
from cortex.embedders.language import detect_language


# ---------------------------------------------------------------------------
# Retrocompatibilidad estricta
# ---------------------------------------------------------------------------


def test_default_config_resolves_legacy_minilm() -> None:
    config = CortexConfig()
    assert not embedding_block_active(config)
    assert resolve_embedder(config) == ("all-MiniLM-L6-v2", "onnx")


def test_legacy_custom_fields_still_rule_without_new_block() -> None:
    config = CortexConfig()
    config.episodic.embedding_model = "intfloat/multilingual-e5-large"
    assert resolve_embedder(config) == ("intfloat/multilingual-e5-large", "onnx")
    assert resolve_embedder(config, "es") == ("intfloat/multilingual-e5-large", "onnx")


def test_no_migration_warning_when_only_legacy_customized() -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning fails the test
        config = CortexConfig()
        config.episodic.embedding_model = "something-else"
        resolve_embedder(config)


# ---------------------------------------------------------------------------
# Bloque nuevo
# ---------------------------------------------------------------------------


def _config_with_block() -> CortexConfig:
    return CortexConfig(
        embedding=EmbeddingConfig(
            model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            backend="fastembed",
            language_detection="heuristic",
            per_language={
                "es": EmbeddingLanguageConfig(
                    model="intfloat/multilingual-e5-large", backend="fastembed"
                ),
            },
        )
    )


def test_new_block_wins_over_defaults() -> None:
    config = _config_with_block()
    assert embedding_block_active(config)
    assert resolve_embedder(config) == (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "fastembed",
    )


def test_per_language_es_uses_e5_large() -> None:
    config = _config_with_block()
    assert resolve_embedder(config, "es") == ("intfloat/multilingual-e5-large", "fastembed")
    assert resolve_embedder(config, "ES") == ("intfloat/multilingual-e5-large", "fastembed")


def test_per_language_unknown_falls_back_to_block_default() -> None:
    config = _config_with_block()
    assert resolve_embedder(config, "fr") == (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "fastembed",
    )


def test_entry_backend_inherits_effective_default_when_omitted() -> None:
    config = CortexConfig(
        episodic={"embedding_backend": "local"},
        embedding=EmbeddingConfig(
            backend="fastembed",
            per_language={"en": EmbeddingLanguageConfig(model="all-MiniLM-L6-v2")},
        ),
    )
    # entry.backend=None → hereda el efectivo del bloque (fastembed), no legacy.
    assert resolve_embedder(config, "en") == ("all-MiniLM-L6-v2", "fastembed")


def test_migration_warning_when_both_customized() -> None:
    with pytest.warns(UserWarning, match="embedding"):
        CortexConfig(
            episodic={"embedding_model": "legacy-model"},
            embedding=EmbeddingConfig(backend="fastembed"),
        )


def test_is_configured_semantics() -> None:
    assert not EmbeddingConfig().is_configured()
    assert EmbeddingConfig(backend="fastembed").is_configured()
    assert EmbeddingConfig(
        language_detection="heuristic"
    ).is_configured() is False  # solo detección NO activa modelos


# ---------------------------------------------------------------------------
# Detección heurística de idioma
# ---------------------------------------------------------------------------


ES_TEXT = (
    "La decisión sobre la pasarela de pagos fue tomada porque las comisiones "
    "de Mercado Pago son menores en Latinoamérica y los webhooks requieren "
    "idempotencia para evitar cobros duplicados en el checkout."
)
EN_TEXT = (
    "The decision about the payment gateway was made because Stripe fees are "
    "lower for international customers and their webhooks require idempotency "
    "keys to avoid duplicated charges during checkout retries."
)


def test_detect_language_spanish() -> None:
    assert detect_language(ES_TEXT) == "es"


def test_detect_language_english() -> None:
    assert detect_language(EN_TEXT) == "en"


def test_detect_language_short_text_returns_none() -> None:
    assert detect_language("hola mundo") is None


def test_detect_language_neutral_text_returns_none() -> None:
    # Sin señales de ningún idioma (sin stopwords ni diacríticos) → no adivinar.
    neutral = (
        "server config value port default cache index node service endpoint "
        "retry timeout header schema payload handler registry"
    )
    assert detect_language(neutral) is None


# ---------------------------------------------------------------------------
# Resolución de idioma efectiva (frontmatter > heurística > None)
# ---------------------------------------------------------------------------


def test_resolve_language_frontmatter_wins_over_heuristic() -> None:
    config = _config_with_block()
    assert (
        resolve_language_for_text(config, EN_TEXT, frontmatter_lang="es") == "es"
    )


def test_resolve_language_detection_off_returns_none() -> None:
    config = CortexConfig()
    assert resolve_language_for_text(config, ES_TEXT) is None


def test_resolve_language_heuristic_active() -> None:
    config = _config_with_block()
    assert resolve_language_for_text(config, ES_TEXT) == "es"


def test_resolve_language_explicit_lang_without_detection() -> None:
    config = CortexConfig()  # detection off
    assert resolve_language_for_text(config, ES_TEXT, frontmatter_lang="en") == "en"
