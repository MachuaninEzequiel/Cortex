"""Tests de persistencia de feedback (Obra 05 Fase A, tarea 1).

FeedbackStore: JSONL append-only con rotación. FeedbackCollector: hook
opcional que anota cada feedback explícito. Comportamiento por defecto
sin store: idéntico al histórico (gate de Fase A).
"""

from __future__ import annotations

from pathlib import Path

from cortex.feedback_loop import ExplicitFeedback, FeedbackCollector
from cortex.feedback_store import FeedbackStore


class TestFeedbackStore:
    def test_roundtrip_eventos(self, tmp_path: Path) -> None:
        st = FeedbackStore(tmp_path)
        st.append({"type": "explicit", "memory_id": "m1", "feedback_type": "useful"})
        st.append({"type": "explicit", "memory_id": "m2", "feedback_type": "not_useful"})

        eventos = st.load()
        assert [e["memory_id"] for e in eventos] == ["m1", "m2"]
        assert all("ts" in e for e in eventos)  # timestamp autocompletado

    def test_rotacion_al_superar_max_bytes(self, tmp_path: Path) -> None:
        # 800B ≈ una sola rotación con estos eventos (~110B c/u); el diseño v1
        # descarta la generación previa al volver a rotar.
        st = FeedbackStore(tmp_path, max_bytes=800)
        for i in range(10):
            st.append({"type": "explicit", "memory_id": f"m{i}", "blob": "x" * 50})

        # el archivo vivo quedó por debajo del total escrito → rotó
        assert st.path.stat().st_size < 10 * 110
        rotado = tmp_path / "feedback.1.jsonl"
        assert rotado.exists(), "debe existir la generación histórica"
        assert len(st.load()) == 10  # load lee vivo + rotado

    def test_linea_corrupta_no_revienta_load(self, tmp_path: Path) -> None:
        st = FeedbackStore(tmp_path)
        st.append({"type": "explicit", "memory_id": "bueno"})
        with st.path.open("a", encoding="utf-8") as fh:
            fh.write("{corrupta\n")

        eventos = st.load()
        assert len(eventos) == 1
        assert eventos[0]["memory_id"] == "bueno"


class TestCollectorConStore:
    def test_add_feedback_persiste_evento(self, tmp_path: Path) -> None:
        st = FeedbackStore(tmp_path)
        collector = FeedbackCollector(store=st)
        fb = ExplicitFeedback(source="user", feedback_type="positive")
        collector.add_feedback("mem_9", fb)

        eventos = st.load()
        assert len(eventos) == 1
        assert eventos[0]["memory_id"] == "mem_9"
        assert eventos[0]["type"] == "explicit"

    def test_sin_store_comportamiento_historico(self, tmp_path: Path) -> None:
        """Gate Fase A: sin store, NADA cambia (no se escribe ningún archivo)."""
        collector = FeedbackCollector()
        fb = ExplicitFeedback(source="user", feedback_type="positive")
        collector.add_feedback("mem_1", fb)

        assert collector.get_usefulness("mem_1") > 0
        assert not (tmp_path / "feedback.jsonl").exists()
