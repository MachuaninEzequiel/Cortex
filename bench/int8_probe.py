#!/usr/bin/env python3
"""Spike H-9 — MiniLM int8 vs fp32: paridad, latencia y calidad de retrieval.

Gate acordado con el dueño (2026-08-24b):
  - paridad cos(int8, fp32) ≥0.99 promedio sobre queries del eval
  - sin caída de calidad: hit@5/MRR@10 int8 ≥ fp32 - 5% relativo
  - latencia batch menor o igual

Si no pasa el gate, se descarta el modelo cuantizado (no se integra nada).

MEMORIA (lección de los OOM del 23/08 21:15 y 24/08 09:08):
  La v1 cargaba fp32 + int8 SIMULTÁNEAMENTE y embebía el corpus entero en un
  solo batch de 1000×128. Las activaciones transitorias del transformer
  (atención B×H×L×L + FFN intermedio) picaron varios GB y el arena de
  onnxruntime retuvo ese pico por sesión → ~10GB anónimos → OOM global del
  kernel en una notebook de 11GB+swap-zram (2 kills: el proceso python murió
  con la sesión de pi adentro).
  Reglas desde ahora:
    1. NUNCA dos sesiones ONNX vivas a la vez: fase fp32 completa → liberar →
       recién entonces fase int8.
    2. Corpus en lotes chicos (BATCH), jamás un batch gigante.
    3. enable_cpu_mem_arena=False para que ORT devuelva memoria al SO.
"""

from __future__ import annotations

import gc
import json
import resource
import statistics
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import tokenizers

REPO = Path(__file__).resolve().parent.parent
ONNX_DIR = Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx"
QUERIES = REPO / "bench/datasets/queries-es-en.jsonl"
VAULT = REPO / "bench/datasets/vault-synth-1k"
SEQ = 128
BATCH = 64  # textos por pasada de inferencia; el corpus NUNCA va en un solo batch


def peak_rss_mb() -> float:
    """Pico histórico de RSS del proceso (VmHWM), en MB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def sesion(ruta: Path):
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.enable_cpu_mem_arena = False  # sin arena que retenga el pico tras cada run
    return ort.InferenceSession(str(ruta), sess_options=so)


def _forward(sess, textos: list[str], tok) -> np.ndarray:
    encs = tok.encode_batch(textos, add_special_tokens=True)
    ids = np.zeros((len(encs), SEQ), dtype=np.int64)
    mask = np.zeros((len(encs), SEQ), dtype=np.int64)
    for i, e in enumerate(encs):
        n = min(len(e.ids), SEQ)
        ids[i, :n] = e.ids[:n]
        mask[i, :n] = e.attention_mask[:n]
    out = sess.run(
        None,
        {
            "input_ids": ids,
            "attention_mask": mask,
            "token_type_ids": np.zeros((len(encs), SEQ), dtype=np.int64),
        },
    )[0]
    # Mean-pooling correcto: promedio solo sobre tokens reales de CADA texto.
    # (La v1 dividía por m.sum(axis=1) de la máscara YA broadcast (b,seq,hid),
    #  que da (b,1,hid) y por broadcasting inflaba el resultado a (b,b,hid).)
    out = out * np.expand_dims(mask, -1)
    emb = out.sum(axis=1) / np.clip(mask.sum(axis=1, keepdims=True), 1e-9, None)
    return emb / np.linalg.norm(emb, axis=1, keepdims=True)


def embed(sess, textos: list[str]) -> np.ndarray:
    """Replica el pipeline chroma (pad fijo SEQ como tokenizer.json default),
    procesando en lotes de BATCH para no inflar las activaciones."""
    tok = tokenizers.Tokenizer.from_file(str(ONNX_DIR / "tokenizer.json"))
    return np.concatenate(
        [_forward(sess, textos[i : i + BATCH], tok) for i in range(0, len(textos), BATCH)],
        axis=0,
    )


def fase(nombre: str, ruta_onnx: Path, queries: list[str], corpus: list[str]):
    """Corre TODA la medición de UN modelo y devuelve sus embeddings.
    La sesión se libera acá dentro: nunca conviven dos modelos."""
    print(f"── Fase {nombre}: {ruta_onnx.name} (pico RSS hasta ahora: {peak_rss_mb():.0f}MB)")
    sess = sesion(ruta_onnx)

    q = embed(sess, queries)
    lat_runs = []
    for _ in range(3):
        t0 = time.perf_counter()
        embed(sess, queries)
        lat_runs.append((time.perf_counter() - t0) * 1000)
    lat_ms = statistics.median(lat_runs)

    c = embed(sess, corpus)
    del sess  # liberar ANTES de abrir el próximo modelo
    gc.collect()
    print(f"   embed queries={len(queries)} lat={lat_ms:.1f}ms · corpus={len(c)} · pico RSS: {peak_rss_mb():.0f}MB")
    return q, c, lat_ms


def main() -> int:
    items = [
        json.loads(line)
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    queries = [it["query"] for it in items]
    docs = sorted(VAULT.rglob("*.md"))
    corpus = [(d.stem + " " + d.read_text(encoding="utf-8")).lower()[:2000] for d in docs]

    # Secuencial estricto: fp32 termina y se libera antes de tocar int8.
    q_fp32, c_fp32, lat_f = fase("fp32", ONNX_DIR / "model.onnx", queries, corpus)
    q_int8, c_int8, lat_8 = fase("int8", ONNX_DIR / "model.int8.onnx", queries, corpus)

    # ── Paridad (con los embeddings ya cacheados; ambos modelos ya cerrados) ──
    coses = np.sum(q_fp32 * q_int8, axis=1)  # normalizados ⇒ coseno directo
    print(f"paridad cos(query): mean={coses.mean():.6f} min={coses.min():.6f}")
    print(f"latencia embed({len(queries)}): fp32={lat_f:.1f}ms · int8={lat_8:.1f}ms ({lat_f / lat_8:.2f}x)")

    def hit_mrr(corpus_emb: np.ndarray, matriz_queries: np.ndarray) -> tuple[float, float]:
        hits5 = 0
        rr_total = 0.0
        for i, item in enumerate(items):
            gold = {Path(g).name for g in item["gold_rel_paths"]}
            scores = corpus_emb @ matriz_queries[i]
            order = np.argsort(scores)[::-1][:10]
            rr = 0.0
            for rank, idx in enumerate(order, 1):
                if docs[idx].name in gold:
                    rr = 1.0 / rank
                    break
            rr_total += rr
            top5 = {docs[j].name for j in order[:5]}
            if gold & top5:
                hits5 += 1
        n = len(items)
        return hits5 / n, rr_total / n

    h_f, mrr_f = hit_mrr(c_fp32, q_fp32)
    h_8, mrr_8 = hit_mrr(c_int8, q_int8)

    resultado = {
        "cos_parity_mean": round(float(coses.mean()), 6),
        "cos_parity_min": round(float(coses.min()), 6),
        "latency_ms_fp32": round(lat_f, 1),
        "latency_ms_int8": round(lat_8, 1),
        "speedup": round(lat_f / lat_8, 2),
        "fp32": {"hit_at_5": round(h_f, 4), "mrr_at_10": round(mrr_f, 4)},
        "int8": {"hit_at_5": round(h_8, 4), "mrr_at_10": round(mrr_8, 4)},
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "batch_size": BATCH,
    }
    print(json.dumps(resultado, indent=2))

    out = REPO / "bench/results/int8-spike.json"
    out.write_text(json.dumps(resultado, indent=2) + "\n")
    print(f"→ {out}")

    pasa = (
        float(coses.mean()) >= 0.99
        and h_8 >= h_f * 0.95
        and mrr_8 >= mrr_f * 0.95
    )
    print(f"GATE int8: {'PASA ✅' if pasa else 'NO PASA ❌'}")
    return 0 if pasa else 1


if __name__ == "__main__":
    raise SystemExit(main())
