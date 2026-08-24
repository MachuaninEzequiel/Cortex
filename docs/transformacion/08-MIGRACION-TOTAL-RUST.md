# 08 — MIGRACIÓN TOTAL A RUST ("Cortex nativo")

> Estado: PLAN APROBADO POR EL DUEÑO (2026-08-24). Prioridad máxima.
> Objetivo declarado: **migrar literalmente cada parte que existe en Python**.
> Este documento define inventario, fases, gates y orden. Un gate por commit,
> mismas reglas duras de §R5 del HANDOFF (paridad antes que velocidad).

## 0. Por qué y para qué

La capa nativa ya probó la diferencia (scoring 27.6×, ingesta 3684×, BM25 p99
1.85ms, cold query 20.8×). Pero el usuario final todavía paga el impuesto de
Python en cada comando: **~0.9s de imports**, ~100MB de RSS base, dos runtimes
en disco, y el brain delegando por subprocess. La migración total entrega:

| Métrica | Hoy (Python) | Objetivo (Rust total) |
|---|---|---|
| Cold start de un comando | ~900 ms | **<100 ms** |
| RSS de la CLI | ~100 MB | **<25 MB** |
| Distribución | pipx/pip + Python runtime | **un binario + GGUF opcional** |
| Brain ↔ servicios | subprocess | llamadas in-process |
| Instalación usuario | pipx + extras | `cargo install` / binario de release |

Consecuencia documental: cuando esto termine, **pipx deja de ser necesario**
(el README se actualiza a binarios); mientras tanto pipx sigue siendo el camino
primario vigente.

## 1. Inventario completo de lo que migra (fuente: código actual)

| # | Componente Python | Líneas aprox | Destino Rust | Notas |
|---|---|---|---|---|
| 1 | Config pydantic (`cortex/core.py`) | ~700 | crate `cortex-config` (serde) | semántica de warnings legacy idéntica |
| 2 | VaultReader + chunking | ~600 | `cortex-retrieval` | reglas de chunk/frontmatter 1:1 |
| 3 | Embeddings ONNX (MiniLM vía chromadb, e5 vía fastembed) | ~400 | `cortex-embed` (ya existe ort) | e5 YA tiene paridad 1.0; falta MiniLM-vía-ort |
| 4 | Retrieval híbrido (RRF, filtros, budget) | ~800 | `cortex-retrieval` | scoring/BM25/store ya nativos |
| 5 | Memoria episódica (ChromaDB) | ~1200 | extensión de store v3 | ver §3 decisión EPISÓDICA-NATIVA |
| 6 | Session primitive + hooks + quality gates | ~2500 | `cortex-session` | tests/unit/session/* son LA spec |
| 7 | Documenter/reconstructor 8 pasos | ~1500 | `cortex-documenter` | ídem spec en tests |
| 8 | ActionEngine completo + feedback | ~2000 | `cortex-actions` | FeedbackStore JSONL formato-compatible |
| 9 | ContextEnricher + presupuesto | ~900 | `cortex-retrieval` | telemetría JSONL compatible |
| 10 | CLI Typer (main + 12 subapps) | ~4500 | `cortex` binario clap | parity --json como G6 |
| 11 | MCP server + schemas + mixins | ~2500 | `rmcp` (SDK oficial Rust) | golden contract JSON ya fija la superficie |
| 12 | TUI Home + pantallas (rich) | ~700 | `ratatui` | acá vive el cerebro ASCII con degradado (pendiente estético) |
| 13 | Setup/templates + IDE adapters ×11 | ~3000 | `cortex-setup` + minijinja | renders canónicos byte-parity |
| 14 | Webgraph server (Flask) | ~500 | axum mínimo | sirve el grafo que ya calcula cortex-core |
| 15 | Cola larga: ci plugin, tutor, hu, pr_context, documenting, review_knowledge… | ~3500 | crates temáticos | al final, uno por commit |

Total estimado: **~25k LOC Python** → migración por fases con paridad.

## 2. Arquitectura destino

```text
                    ┌─────────────────────────────┐
                    │   cortex  (binario único)    │
                    │  clap nivel-0/1 · TUI ratatui │
                    └──────┬──────────┬───────────┘
                           │          │ rmcp (MCP server stdio)
        ┌──────────────────▼───┐  ┌───▼─────────────┐
        │ cortex-app           │  │ mismo cortex-app │
        │ sessions·actions·doc·│  │ (modo servidor)  │
        │ retrieval·setup      │  └──────────────────┘
        └──┬───────┬───────┬───┘
           │       │       │
   cortex-core  cortex-embed  cortex-config      (crates ya existentes + nuevos)
   (scoring·BM25·store·webgraph) (ort e5+MiniLM)
```

El brain (`cortex-brain`) absorbe el resto: deja de delegar por subprocess y
consume `cortex-app` in-process.

## 3. Decisiones de diseño a firmar (ADRs chicos, uno por fase)

1. **EPISÓDICA-NATIVA**: ChromaDB sale. Store v3 extiende con metadata
   filtrable (colecciones, timestamps, entidades JSON). Conversor one-shot
   `chroma→nativo`. El ADR-EPISODIC vigente decía "chroma queda hasta >50k":
   la decisión del dueño de migrar todo lo reemplaza — el crossover ya no
   aplica porque desaparece el runtime Python completo.
2. **PARIDAD-COMO-CONTRATO**: cada fase toma sus tests Python como
   especificación (patrón brain: 13 tests espejados). Outputs `--json`
   comparados byte-a-byte sobre fixtures commiteados.
3. **FLAG DE DOBLE VÍA**: durante la transición, `CORTEX_PY=1` fuerza el CLI
   viejo (default: Rust). Inverso al patrón anterior porque ahora el nuevo es
   el objetivo default; Python queda como rollback hasta cierre.
4. **MINIJINJA** para templates (compatibilidad jinja2 subset usado).
5. **git2/libgit2** para diff/status del documenter (sin shell-out).

## 4. Fases y gates (orden estricto, una por commit/PR)

| Fase | Contenido | Gate |
|---|---|---|
| **P0 ✅** | Scaffolding: crates `cortex-config`, `cortex-app`; harness de parity (--json golden) | workspace verde + fixtures commiteados |
| **P1** | Config completa (bloque embedding incl.) | parse parity sobre config.yaml real + fixtures de error |
| **P2** | Vault + embeddings MiniLM-vía-ort + hybrid search | ranking idéntico queries-synth + eval ES/EN hit@5≥95% rel |
| **P3** | Episódica nativa + conversor chroma→nativo | recall parity en fixtures; round-trip de datos reales |
| **P4** | Sessions + hooks + quality gates | tests espejo de tests/unit/session/* |
| **P5** | Documenter/reconstructor + verification runner | notas generadas idénticas sobre sesiones fixture |
| **P6** | ActionEngine + next/stats + feedback JSONL | catálogo/scheduler parity + pct_motor igual |
| **P7** | ContextEnricher + budget | bundles --json idénticos |
| **P8** | Setup/templates + 11 IDE adapters (minijinja) | renders byte-parity sobre proyectos fixture |
| **P9** | MCP server rmcp | golden contract list_tools.json byte-a-byte |
| **P10** | TUI ratatui (Home <50ms) + cerebro ASCII degradado (definición estética pendiente del dueño) | snapshot render + latencia |
| **P11** | Cola larga (ci, tutor, hu, pr_context…) uno por commit | parity por comando |
| **P12** | Cierre: brain in-process, default Rust, Python app layer eliminada, wheels solo-Rust | suite completa Rust + bench final vs baseline |

## 5. Reglas (extienden §R5)

1. Paridad antes que velocidad; cualquier drift visible = revert.
2. Los tests Python de cada componente son LA especificación hasta su cierre.
3. Mientras un componente exista en ambos lados, la suite Python completa debe
   seguir verde (es el oráculo).
4. Un gate por commit; JSON de medición + fila en COMPARE.md cuando aplique.
5. Sin dependencias pesadas nuevas sin ADR (tokio, ratatui, rmcp, minijinja,
   git2 quedan aprobados por este documento).
6. Reglas de memoria vigentes (un modelo residente por vez, batches ≤64).

## 6. Estimación honesta

P0–P3 son el corazón de rendimiento (retrieval completo nativo). P4–P8 son
volumen de porteo mecánico con specs claras. P9–P12 son integración y cierre.
Es trabajo de varias sesiones; el orden está pensado para que **cada fase
deje valor independiente** (ej: P2 solo ya acelera `search` real).
