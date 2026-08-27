#!/usr/bin/env python3
"""Oráculo de paridad P3 para memoria episódica (Obra 07).

Sub-comandos:
  build    — crea un store temporal con memorias deterministas, exporta el
             JSONL neutro (id/document/meta/embedding) y captura los goldens:
             entries.json (dump por id, timestamps normalizados),
             vector_rankings.json, keyword.json, entity_order.json,
             queries.json (las consultas usadas).
  roundtrip— verifica que el store REAL del repo (.memory/chroma) se exporta
             sin pérdida: cuenta + ids ordenados.

Uso:
  python episodic_golden.py build --out bench/parity/golden_episodic
  python episodic_golden.py roundtrip [--persist .memory/chroma] --out …
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MEMORIAS = [
    ("Se arregló el bug de login en la función authenticate_user del módulo auth.", "bugfix", ["auth", "login"], ["src/auth.py"]),
    ("Refactor de VaultReader para soportar frontmatter multilingüe.", "refactor", ["vault"], ["cortex/semantic/vault_reader.py"]),
    ("Decisión de arquitectura: usar RRF con k=60 para fusionar retrieval.", "decision", ["architecture"], []),
    ("Error ValueError: invalid literal for int en el parser de config.", "incident", [], ["parser.py"]),
    ("Se agregó endpoint POST /api/memories al servicio REST.", "feature", ["api"], ["server.py"]),
    ("Clase FeedbackStore persiste feedback en feedback.jsonl con rotación.", "feature", ["feedback"], []),
    ("Runbook: si chromadb falla al abrir, borrar .memory/chroma y reindexar.", "runbook", ["ops"], []),
    ("La clase NativeVectorCache escribe store v3 append-only.", "note", ["rust"], ["rust/cortex-core"]),
    ("config.get('embedding_model') devuelve el modelo activo por idioma.", "note", ["config"], []),
    ("Incidente 2026-05-15: subagente colgado 14 minutos + MCP desconectado.", "incident", ["mcp"], []),
    ("Memoria genérica sin entidades ni archivos adjuntos.", "general", [], []),
    ("Se optimizó el webgraph con rayon: vecinos n1000 en 345ms.", "perf", ["webgraph", "rust"], []),
]

QUERIES_VEC = [
    "bug de autenticación",
    "chunking de documentos largos",
    "fusión de rankings de búsqueda",
    "error parseando configuración",
    "API de memorias",
    "visualizador de grafo rendimiento",
]

QUERIES_KEYWORD = [
    "feedback.jsonl",
    "rayon",
]

ENTITY_CASES = [
    ("function", "authenticate_user"),
    ("class", "FeedbackStore"),
    ("endpoint", "/api/memories"),
]


def _store(tmp: Path):
    from cortex.episodic.memory_store import EpisodicMemoryStore

    return EpisodicMemoryStore(
        persist_dir=str(tmp / "chroma"),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        collection_name="cortex_episodic",
    )


def cmd_build(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    import warnings

    with tempfile.TemporaryDirectory() as tmp:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = _store(Path(tmp))
        for content, mtype, tags, files in MEMORIAS:
            store.add(content=content, memory_type=mtype, tags=list(tags), files=list(files))

        # ── Export neutro (incluye embeddings tal cual están en chroma) ──
        got = store._collection.get(include=["documents", "metadatas", "embeddings"])
        rows = []
        for i, mid in enumerate(got["ids"]):
            emb = got["embeddings"][i]
            rows.append({
                "id": mid,
                "document": got["documents"][i],
                "meta": dict(got["metadatas"][i] or {}),
                "embedding": [float(x) for x in emb],
            })
        rows.sort(key=lambda r: r["id"])
        with (out / "exported.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # ── Golden: entries (sorted por id, timestamps normalizados) ──
        entries = []
        for e in sorted(store.list_entries(), key=lambda x: x.id):
            d = e.model_dump(mode="json")
            d["timestamp"] = "{{TS}}"
            entries.append(d)
        (out / "entries.json").write_text(
            json.dumps({"ok": True, "entries": entries}, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # ── Golden: rankings vectoriales ──
        rank = []
        for q in QUERIES_VEC:
            hits = store.search(q, top_k=5, use_embeddings=True)
            rank.append({"query": q, "ids": [h.entry.id for h in hits]})
        (out / "vector_rankings.json").write_text(
            json.dumps({"queries": rank}, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (out / "queries.json").write_text(
            json.dumps({"vector": QUERIES_VEC, "keyword": QUERIES_KEYWORD}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # ── Golden: keyword ($contains) ──
        kw = []
        for q in QUERIES_KEYWORD:
            hits = store.search(q, top_k=5, use_embeddings=False)
            kw.append({"query": q, "ids": [h.entry.id for h in hits]})
        (out / "keyword.json").write_text(
            json.dumps(kw, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        # ── Golden: entity search (SOLO orden de ids: el score tiene recency) ──
        ent = []
        for etype, evalue in ENTITY_CASES:
            hits = store.search_by_entity(etype, evalue, top_k=10)
            ent.append({"type": etype, "value": evalue, "ids": [h.entry.id for h in hits]})
        (out / "entity_order.json").write_text(
            json.dumps(ent, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    print(f"goldens episódicos → {out}")
    return 0


def cmd_roundtrip(persist: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    from cortex.episodic.memory_store import EpisodicMemoryStore

    store = EpisodicMemoryStore(
        persist_dir=str(persist),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )
    got = store._collection.get(include=["documents", "metadatas", "embeddings"])
    rows = []
    for i, mid in enumerate(got["ids"]):
        emb = got["embeddings"][i]
        rows.append({
            "id": mid,
            "document": got["documents"][i],
            "meta": dict(got["metadatas"][i] or {}),
            "embedding": [float(x) for x in emb],
        })
    rows.sort(key=lambda r: r["id"])
    dst = out / "real_exported.jsonl"
    with dst.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"count": len(rows), "file": str(dst)}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "roundtrip"])
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_episodic")
    ap.add_argument("--persist", type=Path, default=REPO_ROOT / ".memory/chroma")
    ns = ap.parse_args()
    if ns.cmd == "build":
        return cmd_build(ns.out)
    return cmd_roundtrip(ns.persist, ns.out)


if __name__ == "__main__":
    raise SystemExit(main())
