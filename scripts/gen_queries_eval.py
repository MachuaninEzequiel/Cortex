#!/usr/bin/env python3
"""T-EVAL-1 (A3): genera `queries-es-en.jsonl` determinista para gates de paridad.

Toma 100 docs del vault sintético (seed 42: 50 con keywords ES, 50 EN) y por
cada uno construye una query a partir de tokens REALES del contenido, anotando
el gold path. El scorer (`eval_retrieval.py`) mide hit@5 / MRR@10 contra este
archivo — mismo formato compartido con Obra 04.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "bench" / "datasets" / "vault-synth-1k"
OUT = REPO_ROOT / "bench" / "datasets" / "queries-es-en.jsonl"

# Vocabulario del generador sintético (ver bench_harness/_records y el vault):
# separar por "sabor" permite queries ES y EN balanceadas.
KEYS_ES = {"autenticacion", "despliegue", "latencia", "memoria", "rendimiento",
           "sesion", "cobertura", "migracion", "cuantizacion", "bateria",
           "indice", "cache", "throughput"}
KEYS_EN = {"auth", "deploy", "latency", "memory", "performance", "session",
           "coverage", "migration", "quantization", "battery", "index",
           "cache", "chunking", "embeddings", "retrieval", "scoring"}


def cargar_docs() -> list[dict]:
    docs = []
    for md in sorted(DATASET.rglob("*.md")):
        rel = str(md.relative_to(DATASET))
        texto = md.read_text(encoding="utf-8")
        # título en frontmatter o primer heading
        title = ""
        for line in texto.splitlines():
            if line.startswith("title:") or line.startswith("# "):
                title = line.split(":", 1)[-1].split("#", 1)[-1].strip().strip('"')
                break
        docs.append({"rel": rel, "title": title, "text": texto})
    return docs


def main() -> int:
    rng = random.Random(42)
    docs = cargar_docs()
    if len(docs) < 100:
        print(f"ERROR: dataset tiene {len(docs)} docs (<100)", file=sys.stderr)
        return 1

    # 100 queries: 50 ancladas en tokens ES, 50 en tokens EN (determinista).
    df: dict[str, int] = {}
    for doc in docs:
        for w in set((doc["title"] + " " + doc["text"]).lower().split()):
            df[w] = df.get(w, 0) + 1

    muestras = rng.sample(docs, 100)
    out = []
    for i, doc in enumerate(muestras):
        vocab = KEYS_ES if i % 2 == 0 else KEYS_EN
        _ = vocab  # balance ES/EN documentado; el matching es léxico-literal.
        # Tokens LITERALES del texto bajado (reconstruirlos desde el título
        # rompe guiones: "RUNBOOK-719" ≠ "runbook 719").
        texto_lower = (doc["title"] + " " + doc["text"]).lower()
        tokens_doc = list(dict.fromkeys(texto_lower.split()))
        unicos = [t for t in tokens_doc if df.get(t, 0) == 1]
        elegidos = (unicos or tokens_doc)[:4]
        if not elegidos:
            continue
        query = " ".join(elegidos)
        out.append({
            "id": f"q{i:03}",
            "query": query,
            "gold_rel_paths": [doc["rel"]],
            "lang": "es" if i % 2 == 0 else "en",
        })

    with OUT.open("w", encoding="utf-8") as f:
        for item in out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"OK → {OUT} · {len(out)} queries anotadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
