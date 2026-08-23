#!/usr/bin/env python3
"""Verificación de paridad Python-vs-Rust nativa para los gates del porteo.

Regla dura (HANDOFF §TAREA-RUST R5.2): un resultado distinto invalida el gate
aunque sea 10× más rápido. Este script corre las MISMAS queries por ambas
rutas y exige igualdad EXACTA de top-k (ids + scores bit a bit).

Uso:
    .venv/bin/python -m bench.parity_check            # retrieve (search completo)
    .venv/bin/python -m bench.parity_check --bm25     # ruta BM25

Exit 0 = paridad total · Exit 1 = divergencia (gate inválido).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATASET_DIR = REPO_ROOT / "bench" / "datasets" / "vault-synth-1k"
QUERIES_PATH = REPO_ROOT / "bench" / "datasets" / "queries-synth.json"


def _cargar_queries() -> list[str]:
    import json

    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return [q["query"] for q in data["queries"]]


def _topk_fingerprint(hits) -> list[tuple[str, float]]:
    """Firma comparable: (id estable, score) por hit. Igualdad exigida == ."""
    return [(h.matched_chunk_id or h.path, h.score) for h in hits]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm25", action="store_true", help="paridad de _bm25_search")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    from cortex.semantic.vault_reader import VaultReader

    queries = _cargar_queries()
    print(f"dataset={DATASET_DIR.name} · queries={len(queries)} · top_k={args.top_k}")

    with tempfile.TemporaryDirectory(prefix="parity-") as tmp:
        os.environ.pop("CORTEX_NATIVE", None)
        reader_py = VaultReader(
            vault_path=str(DATASET_DIR),
            embedding_model="all-MiniLM-L6-v2",
            embedding_backend="onnx",
            vector_cache=None,
        )
        n = reader_py.sync()
        print(f"índice sincronizado: {n} docs")

        # Ruta Python pura (flag ausente).
        base: list[list[tuple[str, float]]] = []
        for q in queries:
            hits = reader_py.search(q, top_k=args.top_k, use_embeddings=not args.bm25)
            base.append(_topk_fingerprint(hits))

    # Ruta nativa (flag activo) sobre una instancia fresca.
    os.environ["CORTEX_NATIVE"] = "1"
    try:
        with tempfile.TemporaryDirectory(prefix="parity-native-") as tmp:
            reader_nat = VaultReader(
                vault_path=str(DATASET_DIR),
                embedding_model="all-MiniLM-L6-v2",
                embedding_backend="onnx",
                vector_cache=None,
            )
            reader_nat.sync()
            nativa: list[list[tuple[str, float]]] = []
            for q in queries:
                hits = reader_nat.search(q, top_k=args.top_k, use_embeddings=not args.bm25)
                nativa.append(_topk_fingerprint(hits))
    finally:
        os.environ.pop("CORTEX_NATIVE", None)

    divergencias: list[int] = []
    score_diffs = 0
    for i, (b, n_) in enumerate(zip(base, nativa)):
        if b != n_:
            divergencias.append(i)
            for (id_b, s_b), (id_n, s_n) in zip(b, n_):
                if id_b != id_n:
                    score_diffs += 1
                    break

    if divergencias:
        print(f"❌ PARIDAD ROTA: {len(divergencias)}/{len(queries)} queries divergen")
        for i in divergencias[:5]:
            print(f"   query[{i}] {queries[i]!r}")
            print(f"     python : {base[i][:3]}")
            print(f"     nativo : {nativa[i][:3]}")
        return 1

    modo = "BM25" if args.bm25 else "retrieve"
    print(f"✅ PARIDAD {modo}: top-k y scores BIT-IDÉNTICOS en {len(queries)} queries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
