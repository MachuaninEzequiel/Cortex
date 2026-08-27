#!/usr/bin/env python3
"""Captura rankings dorados de VaultReader para paridad P2 (Obra 07).

Uso:
  python search_golden.py --bm25 --limit 30 --out golden_search_bm25.json
  python search_golden.py --limit 30   # híbrido con embeddings (P2b)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATASET = REPO_ROOT / "bench" / "datasets" / "vault-synth-1k"
QUERIES = REPO_ROOT / "bench" / "datasets" / "queries-es-en.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--bm25", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    ns = ap.parse_args()

    from cortex.semantic.vault_reader import VaultReader

    items = [
        json.loads(line)
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: ns.limit]

    reader = VaultReader(
        vault_path=str(DATASET),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        vector_cache=None,
    )
    reader.sync()

    out = {"modo": "bm25" if ns.bm25 else "hibrido", "queries": []}
    for item in items:
        hits = reader.search(
            item["query"], top_k=ns.top_k, use_embeddings=not ns.bm25
        )
        rels = []
        for h in hits:
            p = Path(h.path)
            try:
                rels.append(str(p.relative_to(DATASET)))
            except ValueError:
                rels.append(h.path)
        out["queries"].append({"query": item["query"], "paths": rels})

    ns.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(out['queries'])} queries → {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
