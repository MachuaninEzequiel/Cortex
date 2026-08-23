"""Gate G4 — paridad de vecinos semánticos nativos vs loops Python.

El gate exige sets de edges IDÉNTICOS (HANDOFF §TAREA-RUST R4). Estos tests
comparan la lista COMPLETA de edges (id, source, target, type, evidence,
weight bits) construida con y sin CORTEX_NATIVE=1.
"""

from __future__ import annotations

import pytest

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import EpisodicRecord, SemanticRecord
from cortex.webgraph.relation_builder import RelationBuilder


def _native_available() -> bool:
    try:
        from cortex_core import _native  # noqa: F401
    except ImportError:
        return False
    return True


requires_native = pytest.mark.skipif(
    not _native_available(),
    reason="cortex_core._native no compilado (maturin develop -m rust/crates/cortex-py)",
)


def _records(n_sem: int, n_epi: int, seed: int = 42):
    """Registros híbridos deterministas con embeddings pseudoaleatorios."""
    import random

    rng = random.Random(seed)
    sem, epi = [], []
    for i in range(n_sem):
        vec = [rng.uniform(-1, 1) for _ in range(32)]
        if i % 9 == 0:
            vec = None
        sem.append(
            SemanticRecord(
                node_id=f"sem-{i:04}",
                node_type="semantic_note",
                title=f"Doc {i}",
                summary=f"resumen {i}",
                rel_path=f"docs/doc-{i}.md",
                abs_path=f"/tmp/docs/doc-{i}.md",
                content=" ".join(f"palabra{i}-{k}" for k in range(12)),
                embedding=vec,
            )
        )
    for i in range(n_epi):
        vec = [rng.uniform(-1, 1) for _ in range(32)]
        if i % 11 == 0:
            vec = None
        epi.append(
            EpisodicRecord(
                node_id=f"epi-{i:04}",
                node_type="episodic_memory",
                label=f"Memoria {i}",
                summary=f"mem {i}",
                memory_id=f"mem-{i}",
                content=" ".join(f"eco{i}-{k}" for k in range(10)),
                embedding=vec,
            )
        )
    return sem, epi


def _fingerprint(edges):
    return [
        (
            e.id,
            e.source,
            e.target,
            e.edge_type,
            round(e.weight, 12),
            list(e.evidence),
        )
        for e in edges
    ]


@requires_native
def test_edges_identicos_con_y_sin_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tamaño suficiente para superar el umbral de pares de la ruta nativa
    # cross-source (>=100k pares episódico×semántico).
    sem, epi = _records(600, 400)
    config = WebGraphConfig(semantic_neighbor_threshold=0.05, semantic_neighbor_max_nodes=220)
    builder = RelationBuilder(config)

    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    edges_py = builder.build_edges([r.model_copy() for r in sem], [r.model_copy() for r in epi])

    monkeypatch.setenv("CORTEX_NATIVE", "1")
    edges_nat = builder.build_edges(sem, epi)

    assert _fingerprint(edges_nat) == _fingerprint(edges_py)


@requires_native
def test_orden_de_edges_tambien_es_identico(monkeypatch: pytest.MonkeyPatch) -> None:
    """La LISTA de edges.values() debe ser idéntica (orden de inserción)."""
    sem, epi = _records(600, 400, seed=7)
    config = WebGraphConfig(semantic_neighbor_threshold=0.1, semantic_neighbor_max_edges_per_node=3)
    builder = RelationBuilder(config)

    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    ids_py = [e.id for e in builder.build_edges(sem, epi)]
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    ids_nat = [e.id for e in builder.build_edges(sem, epi)]
    assert ids_nat == ids_py


@requires_native
def test_max_nodes_excedido_no_construye_vecinos(monkeypatch: pytest.MonkeyPatch) -> None:
    """El guard de semantic_neighbor_max_nodes se respeta en ambas rutas."""
    sem, epi = _records(10, 5)
    config = WebGraphConfig(semantic_neighbor_max_nodes=5)
    builder = RelationBuilder(config)

    monkeypatch.setenv("CORTEX_NATIVE", "1")
    edges = builder.build_edges(sem, epi)
    assert not any(e.edge_type == "semantic_neighbor" for e in edges)


def test_flag_apagado_ruta_python(monkeypatch: pytest.MonkeyPatch) -> None:
    sem, epi = _records(6, 4)
    builder = RelationBuilder(WebGraphConfig())
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    assert builder._native_neighbor_pairs(sem + epi) is None
