"""Tests de caracterización para :mod:`cortex.context_enricher.co_occurrence`.

Fijan el comportamiento de la superficie VIVA de
``TypedCooccurrenceGraph`` antes de la poda P2 (Obra 01):
``build_from_memories``, ``get_strongest_relationship`` y
``calculate_relationship_score`` (lo único que consume el enricher).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cortex.context_enricher.co_occurrence import (
    RelationshipType,
    TypedCooccurrenceGraph,
)


@dataclass
class _Memory:
    """Stub mínimo con la interfaz que lee build_from_memories."""

    files: list[str] = field(default_factory=list)


class TestBuildFromMemories:
    def test_coocurrencia_crea_nodos_y_relaciones(self) -> None:
        graph = TypedCooccurrenceGraph()
        memories = [
            _Memory(files=["src/auth.py", "src/models.py", "tests/test_auth.py"]),
            _Memory(files=["src/auth.py", "src/models.py"]),
        ]
        graph.build_from_memories(memories)

        assert set(graph.nodes) == {"src/auth.py", "src/models.py", "tests/test_auth.py"}
        # auth-models co-ocurre 2 veces; test_auth-models y test_auth-auth no
        # (pares únicos por memoria, self-pares excluidos)
        assert len(graph.relationships) >= 2

    def test_memoria_con_menos_de_dos_archivos_se_ignora(self) -> None:
        graph = TypedCooccurrenceGraph()
        graph.build_from_memories([_Memory(files=["solo.py"])])
        assert len(graph.nodes) == 0

    def test_test_file_infiere_tested_by(self) -> None:
        graph = TypedCooccurrenceGraph()
        graph.build_from_memories([_Memory(files=["test_auth.py", "auth.py"])])
        tipos = {rel.relation_type for rel in graph.relationships}
        assert RelationshipType.TESTED_BY in tipos

    def test_clear_vacia_el_grafo(self) -> None:
        graph = TypedCooccurrenceGraph()
        graph.build_from_memories([_Memory(files=["a.py", "b.py"])])
        graph.clear()
        assert len(graph.nodes) == 0
        assert len(graph.relationships) == 0


class TestScoring:
    def setup_method(self) -> None:
        self.graph = TypedCooccurrenceGraph()
        self.graph.build_from_memories(
            [_Memory(files=["src/auth.py", "src/models.py"])]
        )

    def test_get_strongest_relationship_encuentra_par(self) -> None:
        rel = self.graph.get_strongest_relationship("src/auth.py", "src/models.py")
        assert rel is not None
        assert rel.strength > 0

    def test_get_strongest_relationship_sin_par_devuelve_none(self) -> None:
        assert self.graph.get_strongest_relationship("src/x.py", "src/y.py") is None

    def test_score_positivo_con_solapamiento(self) -> None:
        score = self.graph.calculate_relationship_score(
            ["src/auth.py"], ["src/models.py"]
        )
        assert 0.0 < score <= 1.0

    def test_score_cero_sin_solapamiento(self) -> None:
        score = self.graph.calculate_relationship_score(
            ["src/other.py"], ["src/unrelated.py"]
        )
        assert score == 0.0

    def test_score_cero_con_listas_vacias(self) -> None:
        assert self.graph.calculate_relationship_score([], ["a.py"]) == 0.0
