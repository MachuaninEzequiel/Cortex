#!/usr/bin/env python3
"""Deterministic retrieval evaluation over the synthetic ES/EN dataset.

Measures the REAL semantic pipeline (VaultReader: BM25 + vector cosine)
against human-ordered relevant docs. This is the gate that decides whether
a new embedding model is actually better (Obra 04, Fase D).

Usage:
    # baseline (all-MiniLM-L6-v2), both languages:
    .venv/bin/python eval/retrieval/run_eval.py

    # candidate model comparison:
    .venv/bin/python eval/retrieval/run_eval.py --model multilingual-e5-base --backend onnx

Results are written to eval/retrieval/results/<slug>.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent.parent))  # repo root -> import cortex

from cortex.semantic.vault_reader import VaultReader  # noqa: E402


def load_queries(lang: str) -> list[dict]:
    import yaml

    data = yaml.safe_load((EVAL_DIR / "dataset" / f"queries.{lang}.yaml").read_text(encoding="utf-8"))
    return data["queries"]


def mrr_at_k(ranked: list[str], relevant: list[str], k: int = 10) -> float:
    rel_set = set(relevant)
    for i, doc in enumerate(ranked[:k], start=1):
        if doc in rel_set:
            return 1.0 / i
    return 0.0


def recall_at_k(ranked: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for doc in ranked[:k] if doc in set(relevant))
    return hits / len(relevant)


def evaluate_lang(lang: str, model: str, backend: str, top_k: int, limit: int | None) -> dict:
    queries = load_queries(lang)
    if limit:
        queries = queries[:limit]
    vault = EVAL_DIR / "dataset" / lang
    with tempfile.TemporaryDirectory(prefix=f"cortex-eval-{lang}-") as tmp:
        reader = VaultReader(
            vault_path=str(vault),
            embedding_model=model,
            embedding_backend=backend,
            vector_cache=None,  # deterministic: no cache across runs
        )
        reader.sync()
        per_query = []
        for item in queries:
            hits = reader.search(item["query"], top_k=top_k)
            # Normalize hit paths to vault-relative POSIX paths.
            ranked = []
            for h in hits:
                p = Path(h.path)
                if p.is_absolute():
                    with_suppress = p.relative_to(vault.resolve())
                else:
                    with_suppress = Path(str(p).replace(str(vault) + "/", "") or p.name)
                ranked.append(with_suppress.as_posix())
            relevant = [r for r in item["relevant"]]
            per_query.append({
                "query": item["query"],
                "ranked": ranked,
                "relevant": relevant,
                "mrr10": mrr_at_k(ranked, relevant),
                "recall5": recall_at_k(ranked, relevant, 5),
                "recall1": recall_at_k(ranked, relevant, 1),
            })
    n = len(per_query)
    summary = {
        "language": lang,
        "model": model,
        "backend": backend,
        "num_queries": n,
        "mrr10": round(sum(q["mrr10"] for q in per_query) / n, 4),
        "recall5": round(sum(q["recall5"] for q in per_query) / n, 4),
        "recall1": round(sum(q["recall1"] for q in per_query) / n, 4),
        "per_query": per_query,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--backend", default="onnx")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--lang", choices=["es", "en"], default=None,
                        help="Evaluate a single language (default: both).")
    parser.add_argument("--limit", type=int, default=None, help="Smoke mode: first N queries only.")
    parser.add_argument("--out", default=None, help="Override results filename.")
    args = parser.parse_args()

    langs = [args.lang] if args.lang else ["es", "en"]
    report: dict = {
        "model": args.model,
        "backend": args.backend,
        "top_k": args.top_k,
        "languages": {},
    }
    for lang in langs:
        print(f"== evaluating {lang} ({args.model}) ==")
        summary = evaluate_lang(lang, args.model, args.backend, args.top_k, args.limit)
        print(f"   MRR@10={summary['mrr10']}  R@5={summary['recall5']}  R@1={summary['recall1']}")
        report["languages"][lang] = {k: summary[k] for k in ("mrr10", "recall5", "recall1", "num_queries")}
        (EVAL_DIR / "results").mkdir(exist_ok=True)
        slug = args.model.replace("/", "_")
        out_name = args.out or f"{slug}-{lang}.json"
        out_path = EVAL_DIR / "results" / out_name
        out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"   details -> {out_path}")

    results_file = EVAL_DIR / "results" / (args.out or f"{args.model.replace('/', '_')}-summary.json")
    results_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["languages"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
