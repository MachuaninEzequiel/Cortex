#!/usr/bin/env python3
"""T-EVAL-1: scorer de retrieval sobre queries-es-en.jsonl.

Puntúa la pila actual (VaultReader híbrido o BM25) contra las gold paths:
- hit@5: fracción de queries cuyo gold aparece en el top-5
- MRR@10: media de recíprocos del ranking del gold

Uso:
    .venv/bin/python -m bench.eval_retrieval --out bench/results/eval-retrieval.json
    .venv/bin/python -m bench.eval_retrieval --bm25
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATASET = REPO_ROOT / "bench" / "datasets" / "vault-synth-1k"
QUERIES = REPO_ROOT / "bench" / "datasets" / "queries-es-en.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "bench/results/eval-retrieval.json")
    parser.add_argument("--bm25", action="store_true")
    args = parser.parse_args()

    from cortex.semantic.vault_reader import VaultReader

    items = [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]

    with tempfile.TemporaryDirectory() as tmp:
        reader = VaultReader(
            vault_path=str(DATASET),
            embedding_model="all-MiniLM-L6-v2",
            embedding_backend="onnx",
            vector_cache=None,
        )
        reader.sync()

        hits5 = 0
        rr_total = 0.0
        for item in items:
            hits = reader.search(item["query"], top_k=10, use_embeddings=not args.bm25)
            paths = [h.path for h in hits]
            gold = {Path(g).name for g in item["gold_rel_paths"]}
            rr = 0.0
            for rank, p in enumerate(paths, 1):
                if Path(p).name in gold:
                    rr = 1.0 / rank
                    break
            rr_total += rr
            if rr > 0 and any(Path(x).name in gold for x in paths[:5]):
                hits5 += 1

    n = max(len(items), 1)
    resultado = {
        "queries": n,
        "hit_at_5": round(hits5 / n, 4),
        "mrr_at_10": round(rr_total / n, 4),
        "modo": "bm25" if args.bm25 else "hibrido",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(resultado, indent=2) + "\n")
    print(json.dumps(resultado))
    # Gate informal del plan: paridad top-k ≥95% ⇒ hit@5 ≥0.95 con gold propio.
    return 0 if resultado["hit_at_5"] >= 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
