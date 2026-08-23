#!/usr/bin/env python3
"""Harness de benchmarks de Cortex (Obra 03, T-BENCH-1).

Runner único. SIN BASELINE NO HAY MIGRACIÓN: este módulo captura el
rendimiento del stack Python actual como referencia inmutable contra la
que se juzgan los gates G0-G6 del porteo a Rust.

Uso:
    # baseline completo:
    .venv/bin/python -m bench.bench_harness --suite all --out bench/results/baseline-<fecha>.json

    # una suite:
    .venv/bin/python -m bench.bench_harness --suite retrieve --out bench/results/x.json

    # comparar dos corridas (>10% empeoramiento = regresión):
    .venv/bin/python -m bench.bench_harness compare bench/results/a.json bench/results/b.json

Reglas de validez (plan 03 §5.3): dataset determinista commiteado,
machine-info anotada en cada JSON, outliers >p99.9 descartados,
n/media/p50/p95/p99 por métrica.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATASET_DIR = REPO_ROOT / "bench" / "datasets" / "vault-synth-1k"
QUERIES_PATH = REPO_ROOT / "bench" / "datasets" / "queries-synth.json"

MODEL = __import__("os").environ.get("CORTEX_BENCH_MODEL", "all-MiniLM-L6-v2")
BACKEND = __import__("os").environ.get("CORTEX_BENCH_BACKEND", "onnx")

SUITES = ("cold_start", "retrieve", "index", "webgraph", "bm25", "vector_store")


# ── estadística ────────────────────────────────────────────────────────────


def _percentil(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, round(q * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def stats(muestras_ms: list[float]) -> dict:
    """Descarta outliers >p99.9 y reporta n/media/p50/p95/p99."""
    vals = sorted(muestras_ms)
    if len(vals) > 100:
        corte = _percentil(vals, 0.999)
        vals = [v for v in vals if v <= corte]
    return {
        "n": len(vals),
        "mean_ms": round(statistics.fmean(vals), 3),
        "p50_ms": round(_percentil(vals, 0.50), 3),
        "p95_ms": round(_percentil(vals, 0.95), 3),
        "p99_ms": round(_percentil(vals, 0.99), 3),
    }


def _cpu_seconds() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return ru.ru_utime + ru.ru_stime


# ── entorno ────────────────────────────────────────────────────────────────


def machine_info() -> dict:
    info = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": sys.version.split()[0],
        "cpu_count": __import__("os").cpu_count(),
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal"):
                info["ram"] = line.split(":")[1].strip()
                break
    governor = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if governor.exists():
        info["governor"] = governor.read_text().strip()
    return info


def git_info() -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() != ""
        return {"commit": commit[:12], "dirty": dirty}
    except Exception:
        return {"commit": "?", "dirty": True}


# ── fixtures compartidos ───────────────────────────────────────────────────


def _cargar_queries() -> list[str]:
    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return [q["query"] for q in data["queries"]]


def _reader(vault_path: Path):
    from cortex.semantic.vault_reader import VaultReader

    return VaultReader(
        vault_path=str(vault_path),
        embedding_model=MODEL,
        embedding_backend=BACKEND,
        vector_cache=None,
    )


# ── suites ─────────────────────────────────────────────────────────────────

COLD_SNIPPET = """
import json, sys, time
t0 = time.perf_counter()
from cortex.semantic.vector_cache import VectorCache
from cortex.semantic.vault_reader import VaultReader
t_import = time.perf_counter() - t0

cache_dir, vault, model, backend, query = sys.argv[1:6]

t0 = time.perf_counter()
vc = VectorCache(cache_dir=cache_dir, model_name=model)
reader = VaultReader(vault_path=vault, embedding_model=model,
                     embedding_backend=backend, vector_cache=vc)
reader.sync()
t_sync = time.perf_counter() - t0

t0 = time.perf_counter()
reader.search(query, top_k=5)
t_query = time.perf_counter() - t0

print(json.dumps({"import_s": t_import, "sync_s": t_sync, "first_query_s": t_query}))
"""


def suite_cold_start(queries: list[str]) -> dict:
    """Tiempo hasta primera query servible en proceso NUEVO.

    Dos mediciones (plan §5.2): con cache válido pre-construido y con
    cache vacío (sync completo con embeddings).
    """
    from cortex.semantic.vector_cache import VectorCache as _VC
    from cortex.semantic.vault_reader import VaultReader as _VR

    metrics: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="bench-cold-") as tmp:
        tmp_p = Path(tmp)
        # preconstruir el cache "cálido" una vez en este proceso
        vc_warm_dir = tmp_p / "cache-warm"
        _VR(vault_path=str(DATASET_DIR), embedding_model=MODEL,
            embedding_backend=BACKEND,
            vector_cache=_VC(cache_dir=str(vc_warm_dir), model_name=MODEL)).sync()

        def correr(cache_dir: Path) -> list[dict]:
            out = []
            for _ in range(3):
                proc = subprocess.run(
                    [sys.executable, "-c", COLD_SNIPPET, str(cache_dir),
                     str(DATASET_DIR), MODEL, BACKEND, queries[0]],
                    capture_output=True, text=True, timeout=900,
                )
                if proc.returncode != 0:
                    raise RuntimeError(f"cold_start falló: {proc.stderr[-500:]}")
                out.append(json.loads(proc.stdout.strip().splitlines()[-1]))
            return out

        calido = correr(vc_warm_dir)
        frio = correr(tmp_p / "cache-empty")

    metrics["import"] = stats([r["import_s"] * 1000 for r in calido])
    metrics["sync_warm_cache"] = stats([r["sync_s"] * 1000 for r in calido])
    metrics["sync_empty_cache"] = stats([r["sync_s"] * 1000 for r in frio])
    metrics["first_query_warm"] = stats([r["first_query_s"] * 1000 for r in calido])
    metrics["first_query_cold"] = stats([r["first_query_s"] * 1000 for r in frio])
    return {"metrics": metrics}


def suite_retrieve(queries: list[str]) -> dict:
    """p50/p99 de 200 search() con índice tibio (plan §5.2)."""
    muestras: list[float] = []
    with tempfile.TemporaryDirectory(prefix="bench-ret-") as tmp:
        reader = _reader(DATASET_DIR)
        reader.sync()
        # primera query tras sync (cold index) se registra aparte, 3 corridas
        cold_first: list[float] = []
        for i in range(3):
            r2 = _reader(DATASET_DIR)
            r2.sync()
            t0 = time.perf_counter()
            r2.search(queries[i % len(queries)], top_k=5)
            cold_first.append((time.perf_counter() - t0) * 1000)

        for i, q in enumerate(queries):
            t0 = time.perf_counter()
            reader.search(q, top_k=5)
            muestras.append((time.perf_counter() - t0) * 1000)

    return {
        "metrics": {
            "search_warm": stats(muestras),
            "first_query_after_sync": stats(cold_first),
        }
    }


def suite_index(_: list[str]) -> dict:
    """Sync completo (parse+chunk+embed+idf): mediana de 3 (plan §5.2)."""
    totales: list[float] = []
    with tempfile.TemporaryDirectory(prefix="bench-idx-") as tmp:
        del tmp
        for i in range(3):
            reader = _reader(DATASET_DIR)
            t0 = time.perf_counter()
            n = reader.sync()
            totales.append((time.perf_counter() - t0) * 1000)
            assert n > 0, "sync no indexó nada"
    return {"metrics": {"full_sync_1k": stats(totales)}, "docs_indexados": n}


def suite_bm25(queries: list[str]) -> dict:
    """BM25 puro sin embeddings: 200 queries (plan §5.2)."""
    muestras: list[float] = []
    with tempfile.TemporaryDirectory(prefix="bench-bm25-") as tmp:
        del tmp
        reader = _reader(DATASET_DIR)
        reader.sync()
        for q in queries:
            t0 = time.perf_counter()
            reader.search(q, top_k=5, use_embeddings=False)
            muestras.append((time.perf_counter() - t0) * 1000)
    return {"metrics": {"bm25_search": stats(muestras)}}


def suite_vector_store(_: list[str]) -> dict:
    """Gate G2 (Obra 03): store binario Rust schema v3 vs VectorCache Python v2.

    Dataset sintético determinista (seed 42): 5000 chunks × dim 384 f32.
    Mide ingesta completa y cold load + lectura de TODOS los vectores en ambas
    implementaciones y EXIGE mismos hits bit-idénticos (regla dura R5.2).

    Cold load = mediana de 5 reaperturas completas (plan §5.3: n=1 en escala
    ms es ruido). Ingesta = corrida única (dominada por trabajo O(N²) vs O(N),
    estable). Sin CORTEX_NATIVE=1 o sin módulo registra ``disponible: false``.
    """
    import hashlib
    import os
    import tempfile
    from pathlib import Path as _Path

    import numpy as np

    N, DIM = 5000, 384
    rng = np.random.default_rng(42)
    fps = [hashlib.sha256(f"chunk-text-{i}".encode()).hexdigest() for i in range(N)]
    cids = [f"docs/doc-{i // 5}.md#{i % 5}" for i in range(N)]
    vectores = rng.standard_normal((N, DIM)).astype(np.float32)

    from cortex.semantic.vector_cache import VectorCache

    # ── Ruta Python (schema v2): ingesta O(N²) + cold load lazy ──
    with tempfile.TemporaryDirectory(prefix="store-py-") as d:
        t0 = time.perf_counter()
        cache = VectorCache(_Path(d), model_name="bench-g2", dim=DIM)
        cache.batch_put(list(zip(fps, cids, vectores)))
        py_ingest_ms = (time.perf_counter() - t0) * 1000
        del cache

        def carga_python():
            """Reabre índice y lee los N vectores; devuelve (ms, hits dict)."""
            t = time.perf_counter()
            c = VectorCache(_Path(d), model_name="bench-g2", dim=DIM)
            hits = {fp: c.get(fp) for fp in fps}
            return (time.perf_counter() - t) * 1000, hits

        corridas_py = [carga_python()[0] for _ in range(5)]
        _, hits_py = carga_python()  # referencia de paridad (dir vivo)
    py_load_ms = statistics.median(corridas_py)

    metrics: dict = {
        "python_ingest_5k": stats([py_ingest_ms]),
        "python_cold_load_5k": {
            "n": len(corridas_py),
            "mean_ms": round(statistics.fmean(corridas_py), 3),
            "p50_ms": round(py_load_ms, 3),
        },
    }

    nativo_disponible = False
    if os.environ.get("CORTEX_NATIVE") == "1":
        try:
            from cortex_core import _native  # noqa: F401
            from cortex.semantic.native_vector_cache import NativeVectorCache

            nativo_disponible = True
        except ImportError:
            pass

    if not nativo_disponible:
        return {
            "metrics": metrics,
            "disponible": False,
            "nota": "lado nativo requiere CORTEX_NATIVE=1 + cortex_core._native",
        }

    from cortex.semantic.native_vector_cache import NativeVectorCache

    # ── Ruta nativa (schema v3): log append-only, carga de una pasada ──
    with tempfile.TemporaryDirectory(prefix="store-nat-") as d:
        t0 = time.perf_counter()
        native = NativeVectorCache(_Path(d), model_name="bench-g2")
        native.batch_put(list(zip(fps, cids, vectores)))
        n_ingest_ms = (time.perf_counter() - t0) * 1000
        del native

        def carga_nativa():
            t = time.perf_counter()
            c = NativeVectorCache(_Path(d), model_name="bench-g2")
            res = c._store.get_many(fps)
            return (time.perf_counter() - t) * 1000, res

        corridas_nat = [carga_nativa()[0] for _ in range(5)]
        _, (matrix, present) = carga_nativa()  # referencia de paridad
    n_load_ms = statistics.median(corridas_nat)

    metrics["native_ingest_5k"] = stats([n_ingest_ms])
    metrics["native_cold_load_5k"] = {
        "n": len(corridas_nat),
        "mean_ms": round(statistics.fmean(corridas_nat), 3),
        "p50_ms": round(n_load_ms, 3),
    }

    # ── Paridad de hits (regla dura R5.2) ────────────────────────────────
    divergencias = []
    for i, fp in enumerate(fps):
        vec_py = hits_py.get(fp)
        if not present[i]:
            divergencias.append((fp[:12], "falta en nativo"))
        elif vec_py is None or not np.array_equal(vec_py, matrix[i]):
            divergencias.append((fp[:12], "bits distintos o miss python"))
        if len(divergencias) >= 5:
            break
    if divergencias:
        raise SystemExit(
            f"[bench] ❌ PARIDAD ROTA en vector_store: {divergencias}"
        )

    return {
        "metrics": metrics,
        "disponible": True,
        "paridad_hits": "bit-idéntica",
        "chunks": N,
        "dim": DIM,
    }


_WEBGRAPH_NS = (250, 500, 1000)


def _records_sinteticos(n_sem: int, n_epi: int):
    import random

    from cortex.webgraph.contracts import EpisodicRecord, SemanticRecord

    rng = random.Random(42)
    sem = []
    for i in range(n_sem):
        links = [f"doc-{rng.randint(1, n_sem)}.md" for _ in range(rng.randint(0, 3))]
        sem.append(SemanticRecord(
            node_id=f"sem-{i}", node_type="doc",
            title=f"Documento {i}", summary=f"Resumen {i} " + "x" * 50,
            rel_path=f"docs/doc-{i}.md", abs_path=f"/tmp/docs/doc-{i}.md",
            tags=[f"tag{rng.randint(1, 10)}"], links=links, content="y" * 200,
        ))
    epi = []
    for i in range(n_epi):
        epi.append(EpisodicRecord(
            node_id=f"epi-{i}", node_type="memory", label=f"Memoria {i}",
            summary=f"Trabajo {i}", memory_id=f"mem-{i}",
            tags=[f"tag{rng.randint(1, 10)}"],
            files=[f"src/modulo{rng.randint(1, 40)}.py" for _ in range(rng.randint(1, 3))],
        ))
    return sem, epi


def suite_webgraph(_: list[str]) -> dict:
    """RelationBuilder.build_edges con n∈{250,500,1000}: mediana de 3."""
    from cortex.webgraph.config import WebGraphConfig
    from cortex.webgraph.relation_builder import RelationBuilder

    builder = RelationBuilder(WebGraphConfig())
    metrics: dict[str, dict] = {}
    for n in _WEBGRAPH_NS:
        sem, epi = _records_sinteticos(n, n // 2)
        corridas = []
        for _ in range(3):
            t0 = time.perf_counter()
            edges = builder.build_edges(sem, epi)
            corridas.append((time.perf_counter() - t0) * 1000)
        st = stats(corridas)
        st["edges_generados"] = len(edges)
        metrics[f"build_edges_n{n}"] = st
    return {"metrics": metrics}


SUITE_FNS = {
    "cold_start": suite_cold_start,
    "retrieve": suite_retrieve,
    "index": suite_index,
    "webgraph": suite_webgraph,
    "bm25": suite_bm25,
    "vector_store": suite_vector_store,
}


# ── runner ─────────────────────────────────────────────────────────────────


def correr_suite(nombre: str, queries: list[str]) -> dict:
    cpu0 = _cpu_seconds()
    resultado = SUITE_FNS[nombre](queries)
    resultado["cpu_seconds"] = round(_cpu_seconds() - cpu0, 3)
    return resultado


def run(suites: list[str], out: Path | None, tag: str | None) -> None:
    if not DATASET_DIR.exists():
        raise SystemExit(f"Falta el dataset: {DATASET_DIR}. Generálo y commitéalo.")
    queries = _cargar_queries()

    resultado = {
        "tag": tag or "",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": {"model": MODEL, "backend": BACKEND, "dataset": DATASET_DIR.name},
        "machine": machine_info(),
        "git": git_info(),
        "suites": {},
    }
    for nombre in suites:
        print(f"[bench] corriendo suite: {nombre} …", flush=True)
        t0 = time.perf_counter()
        resultado["suites"][nombre] = correr_suite(nombre, queries)
        print(f"[bench] {nombre}: {time.perf_counter() - t0:.1f}s", flush=True)

    # suite cpu_energy = resumen transversal (proxy batería, plan §5.2)
    resultado["suites"]["cpu_energy"] = {
        "metrics": {
            f"cpu_{s}": {"mean_s": v.get("cpu_seconds", 0.0)}
            for s, v in resultado["suites"].items() if s != "cpu_energy"
        },
        "nota": "CPU-time como proxy de energía: menos CPU-despierto = menos Wh.",
    }

    texto = json.dumps(resultado, indent=2, ensure_ascii=False) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(texto, encoding="utf-8")
        print(f"[bench] OK → {out}")
    else:
        print(texto)


def _extraer_metricas(doc: dict) -> dict[str, tuple[float, str]]:
    """Aplana {suite: {metrics: {m: {...}}}} → {(suite, metrica): p99_o_mean, unidad}."""
    plano: dict[str, tuple[float, str]] = {}
    for suite, contenido in doc.get("suites", {}).items():
        for metrica, valores in contenido.get("metrics", {}).items():
            clave = f"{suite}.{metrica}"
            if "p99_ms" in valores:
                plano[clave] = (valores["p99_ms"], "ms")
            elif "mean_s" in valores:
                plano[clave] = (valores["mean_s"], "s")
    return plano


def compare(path_a: Path, path_b: Path, umbral_pct: float = 10.0) -> int:
    """Tabla de deltas a→b. Return code 1 si hay regresión > umbral."""
    a = json.loads(path_a.read_text(encoding="utf-8"))
    b = json.loads(path_b.read_text(encoding="utf-8"))
    ma, mb = _extraer_metricas(a), _extraer_metricas(b)

    lineas = [
        f"{'métrica':<44} {'base':>12} {'nuevo':>12} {'Δ%':>8}  estado",
        "-" * 88,
    ]
    regresiones = 0
    for clave in sorted(set(ma) & set(mb)):
        va, ua = ma[clave]
        vb, ub = mb[clave]
        if va <= 0:
            continue
        delta = (vb - va) / va * 100
        estado = "REGRESIÓN" if delta > umbral_pct else ("mejora" if delta < -umbral_pct else "ok")
        regresiones += estado == "REGRESIÓN"
        lineas.append(f"{clave:<44} {va:>9.2f}{ua:>2} {vb:>9.2f}{ub:>2} {delta:>+7.1f}%  {estado}")

    print("\n".join(lineas))
    print(f"\nbase: {path_a.name} ({a['git']['commit']}) · nuevo: {path_b.name} ({b['git']['commit']})")
    if regresiones:
        print(f"\n❌ {regresiones} regresión(es) >{umbral_pct:.0f}%")
        return 1
    print("\n✅ sin regresiones")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench.bench_harness")
    sub = parser.add_subparsers(dest="comando")

    p_run = sub.add_parser("run", help="correr suites y capturar JSON")
    p_run.add_argument("--suite", default="all", choices=[*SUITES, "all"])
    p_run.add_argument("--out", type=Path, default=None)
    p_run.add_argument("--tag", default=None)

    p_cmp = sub.add_parser("compare", help="comparar dos resultados")
    p_cmp.add_argument("base", type=Path)
    p_cmp.add_argument("nuevo", type=Path)
    p_cmp.add_argument("--umbral-pct", type=float, default=10.0)

    args = parser.parse_args()
    if args.comando == "compare":
        raise SystemExit(compare(args.base, args.nuevo, args.umbral_pct))

    elegidas = list(SUITES) if getattr(args, "suite", "all") == "all" else [args.suite]
    run(elegidas, getattr(args, "out", None), getattr(args, "tag", None))


if __name__ == "__main__":
    main()
