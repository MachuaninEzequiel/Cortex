# ADR-002 — Embeddings en Rust: ort elegido (Gate G5, T-EMB-1)

> Estado: SPIKE COMPLETO — decisión cerrada; integración a VaultReader pendiente
> Fecha: 2026-08-24 · Gate: G5 / T-EMB-1
> Contexto: docs/transformacion/03-MIGRACION-RUST.md §7-R2 planteaba
> "empezar copiando exactamente el modelo ONNX que usa chromadb hoy; comparar
> salidas antes de cambiar de modelo".

## Decisión

**`ort` (bindings Rust de onnxruntime) + `tokenizers` (HF oficial) sobre los
MISMOS artefactos que chromadb ya cachea (`model.onnx` + `tokenizer.json` de
all-MiniLM-L6-v2). Candle descartado.**

## Evidencia del spike (código: `rust/crates/cortex-embed/examples/g5_spike.rs`)

Pipeline replicado idéntico al de `chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2`:

| Paso | chroma (Python) | spike Rust | Paridad |
|---|---|---|---|
| Tokenización | `tokenizers.Tokenizer.from_file(tokenizer.json)` | `tokenizers::Tokenizer::from_file` (misma crate, HF) | ✅ mismos IDs |
| Entradas ONNX | input_ids/attention_mask/token_type_ids int64 | ídem | ✅ |
| Inferencia | onnxruntime (C++) | ort → MISMA librería C++ | ✅ hidden states iguales a f32 |
| Pooling | mean-pooling con attention mask + L2 (norm guard 1e-12/1e-9) | ídem | ✅ |

Resultados medidos (5 textos ES+EN, batch):

- **Paridad**: coseno(python, rust) = **1.00000000** en 5/5 textos — no solo
  ≥0.999: idéntico a precisión float32.
- **Latencia batch 100 textos** (máquina del dueño, powersave):
  - Python onnxruntime: **2871 ms**
  - Rust ort release: **1305 ms** (**2.2×**) — dominado por la inferencia C++
    compartida; la ganancia viene de eliminar conversiones numpy↔list y overhead
    de chroma. Margen adicional: batching paralelo con rayon (futuro).

## Por qué NO candle

Re-implementaría tokenizador + grafo/pooling + pesos en Rust puro: sin garantía
de outputs bit-exactos contra onnxruntime (kernel selection distinto), mayor
superficie de bugs de paridad, y ningún beneficio medible para el objetivo del
programa (el costo dominante es la inferencia del transformer, igual en ambos).
Se re-evaluaría sólo si algún día se necesita inferencia sin depender de
onnxruntime binaries (p.ej. WASM/embedded).

## Consecuencias y estado honesto

1. **Hecho**: decisión cerrada con evidencia; ejemplo ejecutable versionado;
   dependencias declaradas como feature `onnx` NO default (evita descarga de
   binaries onnxruntime en builds que no lo necesitan).
2. **Pendiente (integración G5)**: envolver en `cortex-embed` un embedder
   productivo (API `embed/embed_batch`) y conectarlo al factory de embedders /
   VaultReader detrás de `CORTEX_NATIVE=1`, con bench harness comparando el
   retrieve completo end-to-end. Estimación [M-L].
3. Riesgo conocido (R2): distribución de binaries onnxruntime por plataforma en
   CI de wheels — mitigable con download-binaries de ort o load-dynamic contra
   el runtime que ya trae chromadb.
