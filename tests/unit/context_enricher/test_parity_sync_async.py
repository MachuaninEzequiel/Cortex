"""Golden de paridad scoring: ContextEnricher sync vs AsyncContextEnricher.

Red de seguridad P5 (deuda V3): el path async duplicaba las fases 2-6 y
se había drift-eado (se saltaba Fase 08: filtros estructurales y
DocIntent boost). Estos tests comparan salida COMPLETA (items, scores,
matched_by, budget) entre ambas implementaciones sobre mocks idénticos.

Escenarios:
1. overlap multi-estrategia → multi-match boost idéntico.
2. decay temporal activo → factores idénticos.
3. filtros estructurales (Fase 08) → aplicados en AMBOS (post-fix).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock


from cortex.context_enricher.async_enricher import AsyncContextEnricher
from cortex.context_enricher.config import ContextEnricherConfig
from cortex.context_enricher.filters import EnrichmentFilters
from cortex.models import EpisodicHit, MemoryEntry, WorkContext


def _work() -> WorkContext:
    return WorkContext(
        source="manual",
        changed_files=["auth.py"],
        keywords=["token", "refresh"],
        detected_domain="auth",
        search_queries=[
            "auth token refresh",
            "auth jwt session",
            "token expiry rotation",
            "fix token bug",
        ],
    )


def _config(**overrides) -> ContextEnricherConfig:
    base = dict(
        min_score=0.01,
        max_items=8,
        max_chars=4000,
        graph_expansion=False,
        typed_graph=False,
        memory_decay=False,
        feedback_loop=False,
        entity_search=False,
    )
    base.update(overrides)
    return ContextEnricherConfig(**base)


def _hit(mem_id: str, score: float, age_days: int = 0) -> EpisodicHit:
    entry = MemoryEntry(
        id=mem_id,
        content=f"contenido determinista {mem_id} " * 3,
        memory_type="bugfix",
        files=["auth.py"],
        tags=["auth"],
        timestamp=datetime.now(UTC) - timedelta(days=age_days),
    )
    return EpisodicHit(entry=entry, score=score)


def _mocks(script: dict[str, list[EpisodicHit]]):
    """Dos sets de mocks idénticos (uno por enricher) con script por query."""

    def construir():
        epi = MagicMock()
        epi.search.side_effect = lambda query, **kw: script.get(query, [])
        epi.count.return_value = 0
        epi.search_by_entity.return_value = []
        sem = MagicMock()
        sem.search.return_value = []
        sem.count.return_value = 0
        return epi, sem

    return construir(), construir()


def _huella(ctx):
    """Huella comparable de un EnrichedContext."""
    return [
        (
            i.source_id,
            round(i.score, 9),
            round(i.enriched_score, 9),
            tuple(sorted(i.matched_by)),
        )
        for i in ctx.items
    ] + [
        ctx.total_searches,
        ctx.total_raw_hits,
        ctx.total_items,
        ctx.total_chars,
        ctx.within_budget,
    ]


def _correr_ambos(config, script, work=None, filters=None):
    (epi_s, sem_s), (epi_a, sem_a) = _mocks(script)

    def correr_sync():
        from cortex.context_enricher.enricher import ContextEnricher

        enriquecedor = ContextEnricher(epi_s, sem_s, config)
        if filters is None:
            return enriquecedor.enrich(work or _work())
        return enriquecedor.enrich(work or _work(), filters=filters)

    def correr_async():
        enriquecedor = AsyncContextEnricher(epi_a, sem_a, config)
        if filters is None:
            return enriquecedor.enrich(work or _work())
        return enriquecedor.enrich(work or _work(), filters=filters)

    sync_h = _huella(correr_sync())
    async_h = _huella(correr_async())
    return sync_h, async_h


Q1 = "auth token refresh"
Q3 = "token expiry rotation"


class TestParidadScoring:
    def test_overlap_multimatch_boost_identicos(self) -> None:
        # mem_1 aparece en DOS estrategias → boost multi-match debe ser igual.
        script = {
            Q1: [_hit("mem_0", 0.9), _hit("mem_1", 0.8)],
            Q3: [_hit("mem_1", 0.7), _hit("mem_2", 0.5)],
        }
        sync_h, async_h = _correr_ambos(_config(), script)
        assert len(sync_h) > 0
        assert sync_h == async_h
        # sanity: mem_1 realmente fue multi-match
        matched = next(h for h in sync_h if isinstance(h, tuple) and h and h[0] == "mem_1")
        assert len(matched[3]) >= 2

    def test_decay_temporal_factores_identicos(self) -> None:
        # min_score bajísimo para que NI el item decaído al floor se filtre:
        # el escenario compara los FACTORES aplicados en cada implementación.
        config = _config(memory_decay=True, min_score=0.0005)
        # age_days=5: lejos del borde min_age_hours=24 para determinismo estricto.
        script = {
            Q1: [_hit("fresco", 0.9, age_days=5), _hit("antiguo", 0.9, age_days=400)],
        }
        sync_h, async_h = _correr_ambos(config, script)
        assert sync_h == async_h
        scores = {h[0]: h[2] for h in sync_h if isinstance(h, tuple)}
        assert scores["antiguo"] < scores["fresco"]  # decay realmente aplicado

    def test_filtros_fase08_aplicados_en_ambos(self) -> None:
        """Drift V3: pre-fix el path async ignoraba los filtros estructurales."""
        script = {
            Q1: [_hit("reciente_ok", 0.9, age_days=2), _hit("viejo_fuera", 0.95, age_days=900)],
        }
        filtros = EnrichmentFilters(max_age_days=365)
        sync_h, async_h = _correr_ambos(_config(), script, filters=filtros)
        ids_sync = {h[0] for h in sync_h if isinstance(h, tuple)}
        assert "viejo_fuera" not in ids_sync  # sync ya filtraba antes del fix
        assert sync_h == async_h  # tras la unificación, async también
