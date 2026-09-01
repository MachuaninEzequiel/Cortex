#!/usr/bin/env python3
"""Oráculo de paridad P7 — ContextEnricher (bundles --json) vs cortex-app.

Sub-comandos:
  build   — construye el store episódico determinista, exporta el JSONL
            neutro (formato P3) y captura los goldens de bundles.
  verify  — regenera TODO en temp y compara contra lo commiteado.

Uso:
  python context_golden_p7.py build --out bench/parity/golden_context \
      [--fixtures /tmp/p7fix]
  python context_golden_p7.py verify --out bench/parity/golden_context

El lado Rust se verifica con:
  cargo run -q -p cortex-app --example context_check -- \
      <fixtures_dir> <golden_dir> <model_dir>

CONTRATO de normalización (documentado; el resto es byte-parity tras
normalizar):
  1. ``{{ROOT}}`` reemplaza la ruta absoluta del fixture (source_id de
     documentos semánticos).
  2. Floats redondeados a 5 decimales en AMBOS lados: los vectores de
     inferencia ONNX difieren a nivel ulp entre onnxruntime (Python) y ort
     (Rust) y el multi-match boost (×3.375) amplifica ese ruido hasta el
     borde del 6° decimal ⇒ tolerancia 1e-5; drift real mayor falla.
  3. Listas ``matched_by`` ordenadas en ambos lados: el oráculo construye
     matched_by con list(set(...)) cuyo orden depende del hash de proceso.
  4. Un único ``\\n`` final.

DETERMINISMO DEL FIXTURE (para siempre):
  - Timestamps episódicos fijados a fechas de 2026-01 (edad >168h ante
    cualquier fecha de verificación posterior) ⇒ decay al floor exacto
    (0.10) y recencia de entidades −0.1 estables.
  - Memorias con tag permanente ⇒ factor de decay 1.0 exacto.
  - Vault con tipos SIN chunking (glossary/sessions/handoffs/hu) ⇒
    matched_chunk_id siempre null.
  - Sin empates de score entre items distintos.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

CONFIG_YAML = """\
episodic:
  persist_dir: .memory/chroma
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2
  embedding_backend: onnx
semantic:
  vault_path: vault
retrieval:
  top_k: 5
"""

# ── vault determinista (tipos sin chunking) ────────────────────────────────
VAULT_DOCS = {
    "glossary/rrf.md": (
        "---\ntitle: RRF\ntags: [retrieval, fusion]\n---\n\n"
        "# RRF\n\n"
        "Reciprocal Rank Fusion combina rankings de búsqueda episódica y\n"
        "semántica con la constante k=60 para fusionar resultados de memoria.\n"
        "La fusión de rankings pondera cada fuente antes del combine final.\n"
    ),
    "glossary/bm25.md": (
        "---\ntitle: BM25\ntags: [retrieval]\n---\n\n"
        "# BM25\n\n"
        "BM25 rankea documentos por frecuencia de término con saturación.\n"
        "El índice semántico del vault usa tf por substring sobre título y\n"
        "contenido, idf logarítmica y normalización por longitud del doc.\n"
    ),
    "sessions/2026-01-05_auth-bug.md": (
        "---\ntitle: Sesión bug de autenticación\nstatus: closed\n---\n\n"
        "# Sesión: bug de autenticación\n\n"
        "Se arregló el error ValueError en el parser de tokens del login.\n"
        "Decisión: usar RRF con pesos adaptativos para retrieval del vault.\n"
        "Quedó documentado el runbook de deploy con rollback seguro.\n"
    ),
    "handoffs/handoff-auth.md": (
        "---\ntitle: Handoff autenticación\n---\n\n"
        "# Handoff\n\n"
        "Pendiente: revisar el error intermitente de autenticación en producción\n"
        "y actualizar el runbook de deploy del servicio de login.\n"
    ),
}

# ── memorias episódicas deterministas ─────────────────────────────────────
# (content, memory_type, tags, files)
MEMORIAS = [
    (
        "Se arregló el bug de login: def authenticate_user( del módulo auth "
        "lanzaba ValueError con tokens vacíos.",
        "decision",
        ["decision"],  # permanente ⇒ decay 1.0 exacto
        ["src/auth.py", "tests/test_auth.py"],
    ),
    (
        "Runbook: si chromadb falla al abrir, borrar .memory/chroma y correr "
        "el deploy del servicio con rollback.",
        "runbook",
        ["runbook", "ops"],  # permanente ⇒ 1.0
        ["docs/runbook-deploy.md"],
    ),
    (
        "Incidente 2026-01-15: outage de autenticación durante 20 minutos por "
        "error ValueError en el parser.",
        "incident",
        [],  # NO permanente ⇒ decay al floor 0.10 (timestamp viejo)
        ["incidents/2026-01-15.md", "src/auth.py"],
    ),
    (
        "Clase FeedbackStore persiste feedback útil en feedback.jsonl con "
        "rotación de una generación.",
        "note",
        [],
        ["cortex/feedback_store.py"],
    ),
]

TIMESTAMP_VIEJO = "2026-01-10T12:00:00+00:00"

# ── casos de WorkContext (construidos directos, source=manual) ────────────
CASOS = {
    # Caso A: una sola query (topic), mezcla episódica+semántica + decay mixto.
    "caso_a_topic": {
        "work": {
            "source": "manual",
            "changed_files": [],
            "keywords": [],
            "imports": [],
            "function_names": [],
            "class_names": [],
            "search_queries": ["bug de autenticación en el login"],
        },
        "top_k": None,
    },
    # Caso B: tres queries (topic+file+keyword) + archivos que co-ocurren +
    # entidades (function/class) ⇒ multi-match boost, grafo naive+tipado,
    # entity_search y feedback implícito activos.
    "caso_b_multi": {
        "work": {
            "source": "manual",
            "changed_files": ["src/auth.py", "docs/runbook-deploy.md"],
            "keywords": ["autenticación", "login", "rollback"],
            "imports": [],
            "function_names": ["authenticate_user"],
            "class_names": ["FeedbackStore"],
            "search_queries": [
                "bug de autenticación en el login",
                "src auth py",
                "rollback del deploy",
                "error ValueError parser",
            ],
        },
        "top_k": None,
    },
    # Caso C: presupuesto vía resolve_budget_profile("deep-code") ⇒ top_k=8
    # y pr_title strategy activa (4 queries).
    "caso_c_budget_prtitle": {
        "work": {
            "source": "manual",
            "changed_files": ["cortex/feedback_store.py"],
            "keywords": ["feedback", "persistencia"],
            "imports": [],
            "function_names": [],
            "class_names": ["FeedbackStore"],
            "pr_title": "FeedbackStore persistente",
            "search_queries": [
                "persistencia del feedback",
                "feedback_store",
                "FeedbackStore rotación",
                "FeedbackStore persistente",
            ],
        },
        "top_k": 8,
        "task_type": "deep-code",
    },
}


def _store(tmp: Path):
    from cortex.episodic.memory_store import EpisodicMemoryStore

    return EpisodicMemoryStore(
        persist_dir=str(tmp / "chroma"),
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
        collection_name="cortex_episodic",
    )


def cargar_store_desde_export(export: Path, tmp: Path):
    """Reconstruye la colección EXACTA del export neutro (ids/embeddings/
    metadatas byte-idénticos) sin re-embeddear nada."""
    import warnings

    store = _store(tmp)
    rows = [json.loads(l) for l in export.read_text(encoding="utf-8").splitlines() if l.strip()]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        store._collection.add(
            ids=[r["id"] for r in rows],
            embeddings=[r["embedding"] for r in rows],
            documents=[r["document"] for r in rows],
            metadatas=[r["meta"] for r in rows],
        )
    return store


def construir_fixture(fixtures: Path) -> Path:
    import warnings

    root = fixtures / "proyecto"
    (root / ".cortex").mkdir(parents=True)
    (root / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    for rel, contenido in VAULT_DOCS.items():
        p = root / "vault" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = _store(Path(tmp))
        ids = []
        for content, mtype, tags, files in MEMORIAS:
            entry = store.add(content=content, memory_type=mtype, tags=list(tags), files=list(files))
            ids.append(entry.id)

        # Congelar timestamps en un pasado lejano (determinismo eterno).
        for mid in ids:
            meta = store._collection.get(ids=[mid], include=["metadatas"])["metadatas"][0]
            meta["timestamp"] = TIMESTAMP_VIEJO
            store._collection.update(ids=[mid], metadatas=[meta])

        # Export neutro (formato P3) junto al fixture para el checker Rust.
        got = store._collection.get(include=["documents", "metadatas", "embeddings"])
        rows = []
        for i, mid in enumerate(got["ids"]):
            rows.append(
                {
                    "id": mid,
                    "document": got["documents"][i],
                    "meta": got["metadatas"][i],
                    "embedding": list(got["embeddings"][i]),
                }
            )
        # Los ids de MemoryEntry son aleatorios por add() ⇒ se renombran
        # de forma DETERMINISTA por contenido (orden lexicográfico) para que
        # el export sea reproducible byte-a-byte entre corridas.
        rows.sort(key=lambda r: r["document"])
        for i, r in enumerate(rows):
            nuevo_id = f"mem_p7_{i:02d}"
            r["meta"]["id"] = nuevo_id
            r["id"] = nuevo_id
        export = root / "episodic_export.jsonl"
        export.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
    return root


# ── captura/oráculo ────────────────────────────────────────────────────────


def _normalizar(payload: dict, root: Path) -> str:
    """Aplica las normalizaciones pactadas y serializa como el presenter."""
    def walk(v):
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                if isinstance(val, str) and val.startswith(str(root)):
                    val = "{{ROOT}}" + val[len(str(root)):]
                out[k] = walk(val)
            return out
        if isinstance(v, list):
            items = [walk(x) for x in v]
            return items
        if isinstance(v, float):
            return round(v, 5)
        return v

    payload = walk(payload)
    # matched_by: el oráculo usa list(set(...)); el contrato P7 ordena.
    for item in payload.get("items", []):
        if "matched_by" in item and isinstance(item["matched_by"], list):
            item["matched_by"] = sorted(item["matched_by"])
    return json.dumps(payload, indent=2, ensure_ascii=False)


def capturar(root: Path) -> dict[str, str]:
    from cortex.context_enricher.budget_resolver import resolve_budget_profile
    from cortex.context_enricher.config import ContextEnricherConfig
    from cortex.context_enricher.enricher import ContextEnricher
    from cortex.models import WorkContext
    from cortex.semantic.vault_reader import VaultReader
    import warnings

    salidas = {}
    with tempfile.TemporaryDirectory() as tmp:
        store = cargar_store_desde_export(root / "episodic_export.jsonl", Path(tmp))
        reader = VaultReader(
            vault_path=str(root / "vault"),
            embedding_model="all-MiniLM-L6-v2",
            embedding_backend="onnx",
            vector_cache=None,
        )
        reader.sync()

        for nombre, caso in CASOS.items():
            work = WorkContext(**caso["work"])
            config = ContextEnricherConfig()
            enricher = ContextEnricher(
                episodic=store, semantic=reader, config=config, observer=None,
            )
            top_k = caso.get("top_k")
            if caso.get("task_type"):
                perfil = resolve_budget_profile(caso["task_type"])
                top_k = perfil["top_k"]
            ctx = enricher.enrich(work, top_k=top_k)
            data = json.loads(ContextPresenter_json(ctx))
            salidas[f"{nombre}.json"] = _normalizar(data, root)
    return salidas


def ContextPresenter_json(ctx) -> str:
    from cortex.context_enricher.presenter import ContextPresenter

    return ContextPresenter.to_json(ctx)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_context")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()
    verificar = ns.cmd == "verify"

    ns.out.mkdir(parents=True, exist_ok=True)
    fallas = 0

    with tempfile.TemporaryDirectory() as tmp:
        root = construir_fixture(Path(tmp))
        salidas = capturar(root)

        for nombre, salida in salidas.items():
            destino = ns.out / nombre
            if verificar:
                esperado = destino.read_text(encoding="utf-8")
                if salida == esperado:
                    print(f"[PASS] {nombre}")
                else:
                    print(f"[FAIL] {nombre} difiere ({destino})")
                    print("--- esperado ---")
                    print(esperado[:800])
                    print("--- obtenido ---")
                    print(salida[:800])
                    fallas += 1
            else:
                destino.write_text(salida, encoding="utf-8")
                print(f"[capturado] {nombre}")

        if not verificar or True:
            # El fixture se deja donde pida (--fixtures) o en temp para inspect.
            destino_fixtures = ns.fixtures or Path(tmp) / "fixtures"
            if ns.fixtures:
                if destino_fixtures.exists():
                    shutil.rmtree(destino_fixtures)
                real = construir_fixture(ns.fixtures)
                print(f"fixture reconstruido → {real}")

    if verificar:
        print(f"\n{'✅ ORÁCULO DETERMINISTA' if fallas == 0 else f'❌ {fallas} diferencias'}")
        return 1 if fallas else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
