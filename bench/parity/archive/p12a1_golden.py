#!/usr/bin/env python3
"""Oráculo de paridad P12A-1 — escrituras nativas (Obra 07, stream A).

Cubre los tres prereq globales de P12A:

  1. episodic.append     — NativeEpisodicStore.append vs EpisodicMemoryStore.add:
                           mismas filas (formato export neutro id/document/meta/
                           embedding), mismo contenido de meta flattenada,
                           embeddings por tolerancia numérica y rankings EXACTOS.
  2. semantic index_file — VaultReader.index_file vs SemanticIndex::index_file:
                           rankings híbridos post-reindex incremental idénticos.
  3. security.resolve_safe — ejercitado transitivamente por ambos (index_file
                           usa resolve_safe en los dos lados).

Sub-comandos:
  build   — construye fixtures deterministas + goldens en --out.
  verify  — regenera TODO en temp y compara contra lo commiteado.

Uso:
  python p12a1_golden.py build --out bench/parity/golden_p12a1 \
      [--fixtures /tmp/p12a1fix] \
      [--model-dir ~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx]
  python p12a1_golden.py verify --out bench/parity/golden_p12a1

El lado Rust se verifica con:
  cargo run -q -p cortex-app --example p12a1_check -- <fixtures_dir> <golden_dir> <model_dir>

CONTRATO de normalización (documentado; el resto es byte-parity):
  1. Los ids `mem_{hex8}` y los timestamps `datetime.now()` son aleatorios ⇒
     las comparaciones se hacen claveadas POR DOCUMENTO (único por fila) y el
     timestamp se normaliza a ``{{TS}}``.
  2. Embeddings: chromadb persiste float32 y ort devuelve f64 (desde f32);
     se comparan con tolerancia abs ≤ 1e-4 por dimensión. El CONTRATO
     conductual son los rankings exactos post-append/reindex.
  3. Orden de claves DENTRO de meta no es contrato (chroma no garantiza orden
     al devolver metadatas); los VALORES sí, byte-a-byte.
  4. Keyword hits: se comparan como listas ordenadas por document (el orden
     de collection.get es indefinido en chroma).
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL_DEFAULT = Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx"

ARCHIVOS_GOLDEN = [
    "golden_base.jsonl",
    "golden_after.jsonl",
    "append_specs.json",
    "golden_entries_after.json",
    "golden_rankings.json",
    "golden_sem_r1.json",
    "golden_sem_r2.json",
    "spec_modificado.md",
]

# ── memorias base (las mismas 12 del golden P3) + 4 nuevas del append ──────

MEMORIAS_BASE = [
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

APPEND_SPECS = [
    {
        "content": "Workitem HU-123 importado desde Jira: naming canónico HU-123.md con fallback slug legacy.",
        "memory_type": "workitem",
        "tags": ["hu", "jira"],
        "files": ["vault/hu/HU-123.md"],
        "extra_metadata": {"origen": "jira", "workitem_id": "HU-123"},
    },
    {
        "content": "class WorkItemService delega la escritura en writers.build_note con frontmatter estable.",
        "memory_type": "decision",
        "tags": ["rust"],
        "files": [],
        "extra_metadata": None,
    },
    {
        "content": "docs-migrate migró la bóveda legacy a estructura canónica specs/ y adr/.",
        "memory_type": "ops",
        "tags": ["migracion"],
        "files": [],
        "extra_metadata": {"herramienta": "docs-migrate"},
    },
    {
        "content": "Error KeyError: workitem_id faltante al importar HU sin key externa.",
        "memory_type": "incident",
        "tags": [],
        "files": [],
        "extra_metadata": None,
    },
]

QUERIES_VEC = [
    "workitem HU importado",
    "servicio de workitems escritura",
    "migración de bóveda",
    "error importando workitem",
    "webgraph rendimiento rayon",
    "rotación de feedback",
]
QUERIES_KEYWORD = ["HU-123.md", "build_note"]

# ── fixture semántico (vault chico determinista) ────────────────────────────

VAULT_FILES = {
    "glosario-core.md": (
        "---\ntitle: Glosario core\ntags: [glosario]\n---\n\n"
        "# Glosario\n\n"
        "La memoria episódica guarda eventos con embedding vectorial.\n"
        "La búsqueda híbrida fusiona rankings BM25 y vectoriales con RRF k=60.\n"
        "El store append-only escribe filas JSONL neutras.\n"
    ),
    "specs/2026-06-01_gate.md": (
        "---\ntitle: Spec gate paridad\ndoc_type: spec\n---\n\n"
        "Objetivo: el gate de paridad valida rankings del store episódico.\n"
        "Verification hook: round-trip append load search contra el export.\n"
        "El gate corre antes de cada commit del stream A.\n"
    ),
    "adr/ADR-0009-store-nativo.md": (
        "---\ntitle: ADR 0009 store nativo\n---\n\n"
        "Decisión: ChromaDB sale; store nativo JSONL append-only.\n"
        "Embeddings por ort sobre artefactos cacheados del modelo MiniLM.\n"
        "Paridad bit-exacta antes que velocidad; drift visible implica revert.\n"
    ),
    "notas/vault-notes.md": (
        "---\ntitle: Notas del vault\n---\n\n"
        "Notas sueltas sobre chunking de documentos largos por routing.\n"
        "Los chunks respetan boundaries h3 cuando el route lo habilita.\n"
    ),
}

VAULT_SPEC_MODIFICADO = (
    "---\ntitle: Spec gate paridad v2\ndoc_type: spec\n---\n\n"
    "Objetivo v2: el gate ahora cubre además el reindex incremental semántico.\n"
    "index_file re-parsea un solo archivo y recalcula BM25 completo.\n"
    "Los chunks viejos del padre se purgan antes de regenerar.\n"
)

QUERIES_SEM = [
    "gate de paridad del store",
    "reindex incremental",
    "store append-only JSONL",
    "chunking por routing",
]


def _store(tmp: Path):
    from cortex.episodic.memory_store import EpisodicMemoryStore

    return EpisodicMemoryStore(
        persist_dir=str(tmp / "chroma"),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        collection_name="cortex_episodic",
    )


def _exportar_rows(store, out_path: Path) -> None:
    got = store._collection.get(include=["documents", "metadatas", "embeddings"])
    rows = []
    for i, mid in enumerate(got["ids"]):
        rows.append({
            "id": mid,
            "document": got["documents"][i],
            "meta": dict(got["metadatas"][i] or {}),
            "embedding": [float(x) for x in got["embeddings"][i]],
        })
    rows.sort(key=lambda r: r["id"])
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def construir_vault(base: Path) -> Path:
    vault = base / "vault"
    for rel, cuerpo in VAULT_FILES.items():
        p = vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo, encoding="utf-8")
    return vault


def correr_episodico(work: Path, out: Path) -> None:
    """Store real Python: 12 base + 4 append → goldens de la sección episódica."""
    store = _store(work)
    for content, mtype, tags, files in MEMORIAS_BASE:
        store.add(content=content, memory_type=mtype, tags=list(tags), files=list(files))
    # Export del estado BASE (para el checker Rust que carga+appendea).
    _exportar_rows(store, out / "golden_base.jsonl")

    for spec in APPEND_SPECS:
        store.add(
            content=spec["content"],
            memory_type=spec["memory_type"],
            tags=list(spec["tags"]),
            files=list(spec["files"]),
            extra_metadata=dict(spec["extra_metadata"]) if spec["extra_metadata"] else None,
        )
    (out / "append_specs.json").write_text(
        json.dumps(APPEND_SPECS, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Estado AFTER completo (base+append) exportado.
    _exportar_rows(store, out / "golden_after.jsonl")

    # Entries after (claveadas por document, timestamp normalizado).
    entries = {}
    for e in store.list_entries():
        d = e.model_dump(mode="json")
        d["timestamp"] = "{{TS}}"
        entries[d.pop("content")] = d
    (out / "golden_entries_after.json").write_text(
        json.dumps({"entries": entries}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Rankings después del append (vector exacto por ORDEN; keyword ordenado).
    rank = []
    for q in QUERIES_VEC:
        hits = store.search(q, top_k=5, use_embeddings=True)
        rank.append({"query": q, "docs": [h.entry.content for h in hits]})
    kw = []
    for q in QUERIES_KEYWORD:
        hits = store.search(q, top_k=5, use_embeddings=False)
        docs = sorted(h.entry.content for h in hits)
        kw.append({"query": q, "docs": docs})
    (out / "golden_rankings.json").write_text(
        json.dumps({"vector": rank, "keyword": kw}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _rankings(reader, queries: list[str], vault_root: str) -> list[dict]:
    res = []
    for q in queries:
        hits = reader.search(q, top_k=3, use_embeddings=True)
        rels = []
        for h in hits:
            try:
                rels.append(str(Path(h.path).relative_to(vault_root)))
            except ValueError:
                rels.append(h.path)
        res.append({"query": q, "paths": rels})
    return res


def correr_semantico(work: Path, out: Path) -> bool:
    """VaultReader: sync → R1; modify+index_file → R2. Sanity interno R2==full."""
    from cortex.semantic.vault_reader import VaultReader

    reader = VaultReader(
        vault_path=str(work),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        vector_cache=None,
    )
    reader.sync()
    r1 = _rankings(reader, QUERIES_SEM, str(work))

    spec_rel = "specs/2026-06-01_gate.md"
    # 1) escribir el contenido nuevo en disco; 2) reindexar incrementalmente.
    (work / spec_rel).write_text(VAULT_SPEC_MODIFICADO, encoding="utf-8")
    assert reader.index_file(spec_rel), "index_file debía succeed"
    r2 = _rankings(reader, QUERIES_SEM, str(work))

    # Sanity del oráculo: un sync FULL sobre el vault modificado da lo mismo.
    full = VaultReader(
        vault_path=str(work),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        vector_cache=None,
    )
    full.sync()
    estable = r2 == _rankings(full, QUERIES_SEM, str(work))

    (out / "golden_sem_r1.json").write_text(
        json.dumps({"queries": r1}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / "golden_sem_r2.json").write_text(
        json.dumps({"queries": r2}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / "spec_modificado.md").write_text(VAULT_SPEC_MODIFICADO, encoding="utf-8")
    return estable


def _normalizar_jsonl(texto: str) -> str:
    """Quita los campos aleatorios (id, meta.id, meta.timestamp) por línea."""
    lineas = []
    for line in texto.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        r.pop("id", None)
        if isinstance(r.get("meta"), dict):
            r["meta"].pop("id", None)
            r["meta"].pop("timestamp", None)
        lineas.append(json.dumps(r, sort_keys=True, ensure_ascii=False))
    return "\n".join(sorted(lineas)) + "\n"


def _normalizar_entries(texto: str) -> str:
    """Quita los ids aleatorios del dump entries (claveado por document)."""
    data = json.loads(texto)
    for e in data.get("entries", {}).values():
        e.pop("id", None)
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=1) + "\n"


def generar_todo(out: Path, fixtures: Path | None) -> bool:
    """Genera todos los goldens en `out` (temp). Devuelve estabilidad semántica."""
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        pristine_vault = construir_vault(base / "fixtures")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            correr_episodico(base / "work_epi", out)

            work_sem = base / "work_sem"
            shutil.copytree(pristine_vault, work_sem)
            estable = correr_semantico(work_sem, out)

        if fixtures:
            if fixtures.exists():
                shutil.rmtree(fixtures)
            fixtures.mkdir(parents=True)
            shutil.copytree(pristine_vault, fixtures / "vault")
            shutil.copy(out / "golden_base.jsonl", fixtures / "base.jsonl")
            print(f"fixture reconstruido → {fixtures}")
    return estable


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_p12a1")
        p.add_argument("--fixtures", type=Path, default=None)
        p.add_argument("--model-dir", type=Path, default=MODEL_DEFAULT)
    ns = ap.parse_args()

    if not ns.model_dir.exists():
        print(f"❌ model_dir inexistente: {ns.model_dir}")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        frescos = Path(tmp) / "goldens"
        estable = generar_todo(frescos, ns.fixtures)

        if ns.cmd == "build":
            ns.out.mkdir(parents=True, exist_ok=True)
            for nombre in ARCHIVOS_GOLDEN:
                shutil.copy(frescos / nombre, ns.out / nombre)
            print(f"[capturado] {len(ARCHIVOS_GOLDEN)} archivos → {ns.out}")
            print("\nVerificación Rust:")
            print(
                f"  cargo run -q -p cortex-app --example p12a1_check -- "
                f"<fixtures_dir> {ns.out} {ns.model_dir}"
            )
            return 0

        # ── verify: comparar contra lo commiteado ──
        fallas = 0
        for nombre in ARCHIVOS_GOLDEN:
            crudo_nuevo = (frescos / nombre).read_text(encoding="utf-8")
            esperado_p = ns.out / nombre
            if not esperado_p.exists():
                print(f"[FAIL] falta golden commiteado: {esperado_p}")
                fallas += 1
                continue
            crudo_esperado = esperado_p.read_text(encoding="utf-8")
            # Los export JSONL y el entries dump llevan ids aleatorios ⇒
            # comparación normalizada.
            if nombre.endswith(".jsonl"):
                nuevo = _normalizar_jsonl(crudo_nuevo)
                esperado = _normalizar_jsonl(crudo_esperado)
            elif nombre == "golden_entries_after.json":
                nuevo = _normalizar_entries(crudo_nuevo)
                esperado = _normalizar_entries(crudo_esperado)
            else:
                nuevo, esperado = crudo_nuevo, crudo_esperado
            if nuevo == esperado:
                print(f"[PASS] {nombre}")
            else:
                print(f"[FAIL] {nombre} difiere")
                for l in list(difflib.unified_diff(
                        esperado.splitlines(), nuevo.splitlines(),
                        lineterm=""))[:40]:
                    print(" ", l)
                fallas += 1

    if fallas == 0 and estable:
        print("\n✅ ORÁCULO DETERMINISTA (lado Python)")
        return 0
    if not estable:
        print("❌ ORÁCULO SEMÁNTICO INESTABLE (index_file != full-sync en Python)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
