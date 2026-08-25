> **HANDOFF ACTIVO (2026-08-24, cierre dual-stream + verificación integral).**
> Obra 07: P0–P11 ✅ COMPLETADAS · P12 ABIERTA. Si algo acá contradice
> historia vieja de este archivo, MANDA ESTA SECCIÓN.

## 0. Contexto en 30 segundos

Cortex (`cortex-memory` v0.7.0): memoria cognitiva híbrida + gobernanza.
Programa: migración TOTAL Python→Rust (Obra 07, plan maestro
`docs/transformacion/08-MIGRACION-TOTAL-RUST.md`). Suite Python = ORÁCULO
(2455 passed, 18 skipped). Paridad-como-contrato en todo.

## 1. Estado por fases

P0–P11 ✅ (detalle y gates: `ESTADO-ACTUAL.md`). P11 quedó PARCIAL:
plugin CI ✅ (`ci_golden_p11.py`, commit `0707f08`); restan pr_context,
hu/workitems, tutor, review_knowledge.

## 2. LÉEME ANTES DE TOCAR NADA — deuda real

**NO es "todo Rust" todavía.** El comando `cortex` del usuario sigue siendo
Python detrás de la fachada passthrough `cortex-cli` (decisión G6). El MCP
nativo tiene catálogo/ruteo congelados pero handlers "no nativo" salvo ping.
Quedan ~22k líneas Python en dominios secundarios. EL MAPA COMPLETO,
con LOC, dependencias y orden de ataque sugerido, está en:

    docs/transformacion/09-DEUDA-MIGRACION-PYTHON.md

Léelo antes de planear cualquier tarea de migración. Orden resumido §4:
episodic.append/reindex → hu+pr_context → mcp handlers → workspace/layout →
doctor → enterprise → webgraph axum → CLI clap nativo → pipeline/autopilot →
baja definitiva de Python.

## 3. Cómo verificar (SIEMPRE)

```bash
cd rust
cargo fmt --all --check && cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace            # 219 passed al cierre; igualmente
                                  # preferí -p <crate> si tocas uno solo
```

Paridad: cada fase tiene su oráculo en `bench/parity/*_golden*.py`
(modos build/verify). Suite Python:
`.venv/bin/python -m pytest tests/unit tests/integration --no-cov`.

## 4. Decisiones cerradas (no re-discutir)

1. Paridad bit-exacta; f32/SIMD prohibido sin ADR que re-valide.
2. BM25 casero (substring semantics); tantivy descartado.
3. Embeddings por ort sobre artefactos chroma/fastembed cacheados.
4. ChromaDB sale → store nativo JSONL/export neutro.
5. minijinja/ratatui/rmcp/tokio/git2 aprobados como deps del porteo.
6. Brain: propone-nunca-muta; LFM2.5 GGUF vía llama.cpp.
7. Fachada passthrough cortex-cli (G6): subcomandos nativos se agregan ahí
   cuando existan, sin romper el passthrough mientras dure la transición.
8. MCP wire-format exacto (nulls explícitos vs omisión rmcp): decisión
   PENDIENTE DEL DUEÑO antes de portear handlers (registrado por stream B).
9. Los motores no-nativos devuelven fallo EXPLÍCITO documentado (patrón
   P6/P9): nunca se finge paridad conductual.

## 5. Reglas de trabajo heredadas

Suite verde antes de cada commit · planes mandan · verificación contra código
real, no checkboxes · un gate por commit · commits atómicos prefijados ·
reglas de memoria: un modelo residente por vez, batches ≤64, caché jamás en
/tmp.

## 6. Deudas/decisiones pendientes del dueño

GPU para ≥5× e2e · release 0.7.0 (CHANGELOG normalizado) · ventana pct_motor
(≥2 semanas uso real) · wire-format MCP (ver §4.8) · tutor: ¿migrar o
reemplazar por ratatui/no-migrar? · limpieza de untracked (progress.md scratch,
uv.lock, runtime jsonl/json) cuando corresponda.

---


