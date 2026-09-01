"""Tests de caracterización para :mod:`cortex.memory_decay`.

Fijan el comportamiento de la superficie VIVA del módulo antes de la poda
P2 (Obra 01): ``DecayConfig``, ``MemoryDecay.should_decay`` y
``calculate_decay_factor``, que es lo único que consumen los enrichers.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from cortex.memory_decay import DecayConfig, MemoryDecay


class TestDecayConfig:
    def test_post_init_deriva_decay_rate_desde_half_life(self) -> None:
        config = DecayConfig(half_life_hours=168.0)
        esperado = math.pow(0.5, 1.0 / 168.0)
        assert config.decay_rate == pytest.approx(esperado)

    def test_decay_rate_explcito_distinto_del_default_se_respeta(self) -> None:
        """Bug #9 (deep review 2026-08): __post_init__ pisaba SIEMPRE
        decay_rate con la derivación de half_life. Un decay_rate explícito
        distinto del default es una intención del caller y se respeta."""
        assert DecayConfig(decay_rate=0.9).decay_rate == 0.9

    def test_path_del_enricher_no_cambia(self) -> None:
        """Los enrichers pasan decay_rate=default + half_life de config:
        la derivación desde half_life debe seguir gobernando (igual que
        antes del fix)."""
        config = DecayConfig(decay_rate=0.995, half_life_hours=720.0)
        esperado = math.pow(0.5, 1.0 / 720.0)
        assert config.decay_rate == pytest.approx(esperado)

    def test_defaults_sensatos(self) -> None:
        config = DecayConfig()
        assert config.floor == 0.10
        assert config.min_age_hours == 24.0
        assert config.half_life_hours == 168.0


class TestShouldDecay:
    def setup_method(self) -> None:
        self.decay = MemoryDecay()

    def test_tipos_permanentes_no_decaen(self) -> None:
        for memory_type in ("adr", "architecture", "decision", "vault_doc"):
            assert self.decay.should_decay(memory_type, []) is False

    def test_tags_permanentes_no_decaen(self) -> None:
        assert self.decay.should_decay("general", ["runbook"]) is False

    def test_temporal_si_decae(self) -> None:
        assert self.decay.should_decay("bugfix", []) is True


class TestCalculateDecayFactor:
    def setup_method(self) -> None:
        self.now = datetime.now(UTC)
        self.decay = MemoryDecay(now=self.now)

    def test_permanente_devuelve_factor_completo(self) -> None:
        viejo = self.now - timedelta(days=365)
        factor = self.decay.calculate_decay_factor("adr", [], viejo)
        assert factor == 1.0

    def test_reciente_bajo_min_age_no_decae(self) -> None:
        reciente = self.now - timedelta(hours=1)
        factor = self.decay.calculate_decay_factor("bugfix", [], reciente)
        assert factor == 1.0

    def test_viejo_temporal_decae_por_encima_del_floor(self) -> None:
        viejo = self.now - timedelta(days=30)
        factor = self.decay.calculate_decay_factor("feature", [], viejo)
        assert 0.10 <= factor < 1.0

    def test_muy_viejo_llega_al_floor(self) -> None:
        muy_viejo = self.now - timedelta(days=365 * 5)
        factor = self.decay.calculate_decay_factor("conversation", [], muy_viejo)
        assert factor == pytest.approx(0.10)

    def test_naive_timestamp_se_trata_como_utc(self) -> None:
        naive = (self.now - timedelta(days=30)).replace(tzinfo=None)
        factor = self.decay.calculate_decay_factor("bugfix", [], naive)
        assert 0.10 <= factor < 1.0
