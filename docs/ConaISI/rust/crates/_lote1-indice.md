# Lote 1 — índice y síntesis

Documentación extraída **solo del código** de cinco crates. Un `.md` por archivo fuente. Convención de nombres: path relativo con `/` → `--`; se quita `.rs`/`.py`.

## Síntesis por crate

### cortex-core
Dominio puro (sin PyO3). Cuatro gates: cosine batch Neumaier (`scoring`), store append-only `vectors.v3.bin` (`store`), BM25 substring (`bm25`), vecinos y edges cross-source rayon (`webgraph`). Invariante: `dim` paramétrica. Consumidores: `cortex-py` (FFI), `cortex-app` (store/reindex), `cortex-webgraph-server`.

### cortex-embed
Wrapper ONNX (`ort` + `tokenizers`) detrás del feature `onnx`. `OnnxEmbedder` tokeniza max 256, padding dinámico, mean-pool + L2, dim del modelo. Example `g5_spike` duplica el pipeline para comparar vectores.

### cortex-py
Fachada PyO3 `cortex_core._native` (ABI3 py311, maturin). APIs batch: `cosine_scores`, `NativeVectorStore`, `NativeBm25Index`, `semantic_neighbor_pairs`, `cross_source_build`, `NativeEmbedder`. Sin lógica de dominio. Python puro sigue siendo el default salvo `CORTEX_NATIVE=1`.

### cortex-config
Porteo serde de `cortex/core.py`. `load_and_dump` produce JSON canónico (orden de campos, `per_language` sorted, warning de migración exacto, `ok:false` sin detalle). Test de paridad contra goldens en `bench/parity`.

### cortex-app
Capa de aplicación nativa: vault semántico (parser/chunker/routing/BM25/vectores), memoria episódica JSONL, ContextEnricher + RRF, sesiones YAML, documenter, CI validate-pr, PR/workitems/docs fallback, reindex con backup. Examples = checkers de paridad P2–P12. Único `tests/`: `compute_diff`.

## Inventario de markdown creados

### cortex-core (6 + estructura)
- `00-estructura.md`
- `Cargo.toml.md`
- `src--lib.md`
- `src--scoring.md`
- `src--store.md`
- `src--bm25.md`
- `src--webgraph.md`

### cortex-embed (4 + estructura)
- `00-estructura.md`
- `Cargo.toml.md`
- `src--lib.md`
- `src--onnx.md`
- `examples--g5_spike.md`

### cortex-py (4 + estructura)
- `00-estructura.md`
- `Cargo.toml.md`
- `pyproject.toml.md`
- `cortex_core--__init__.md`
- `src--lib.md`

### cortex-config (3 + estructura)
- `00-estructura.md`
- `Cargo.toml.md`
- `src--lib.md`
- `tests--parity_fixtures.md`

### cortex-app (70 + estructura)
- `00-estructura.md`
- `Cargo.toml.md`
- `src--lib.md` `src--git.md` `src--security.md` `src--reindex.md` `src--pr.md` `src--workitems.md` `src--doc_generator.md` `src--doc_validator.md` `src--doc_verifier.md`
- `src--semantic--mod.md` `src--semantic--parser.md` `src--semantic--chunker.md` `src--semantic--routing.md`
- `src--episodic--mod.md` `src--episodic--entities.md`
- `src--session--mod.md` `src--session--quality_gates.md` `src--session--service.md` `src--session--verification.md`
- `src--context--mod.md` y 14 submódulos (`budget_resolver`, `cooccurrence`, `decay`, `doc_intent`, `domain_detector`, `feedback`, `filters`, `hybrid`, `intent`, `models`, `observer`, `presenter`, `pyjson`, `telemetry`)
- `src--documenter--mod.md` y 5 submódulos (`diff_parser`, `handoff`, `interactive`, `persister`, `spec_loader`)
- `src--ci--mod.md` y 6 submódulos (`diff_io`, `markdown_formatter`, `result`, `review_session`, `session_matcher`, `validator`)
- 18 examples (`bm25_search`, `semantic_search`, `episodic_*`, `session_check`, `verification_check`, `documenter_check`, `git_check`, `persister_check`, `context_check`, `ci_check`, `p12a1`–`p12a4`, `p12a7`, `p12a8`)
- `tests--compute_diff.md`

## Dependencias entre crates del lote

```
cortex-core  <── cortex-py
     ^              ^
     │              └── cortex-embed
     │
cortex-config ──┐
cortex-embed ───┼── cortex-app
cortex-setup ───┘   (fuera de este lote; writers HU)
```
