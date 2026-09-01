# PROMPT STREAM A — P13 "plano-de-datos" (pegar en terminal dedicada)

Sos el agente del **Stream A** ("plano-de-datos") de la fase **P13
(Companion Engine)** de Cortex. Ponete en contexto leyendo EN ESTE ORDEN,
sin saltarte ninguno:

1. `docs/transformacion/PROMPT-P13-A.md` (este archivo — son reglas vinculantes)
2. `docs/transformacion/11-COMPANION-ENGINE-P13.md` (LA SPEC COMPLETA — leela ENTERA, incluidos los anexos A-I)
3. `docs/transformacion/HANDOFF.md` (sección "HANDOFF ACTIVO"; §4.8 ya está RESUELTO)
4. `docs/transformacion/progreso-p13a.md` (tu único registro de progreso — si no existe, crealo)

## PRECONDICIÓN DE ARRANQUE (verificar antes de escribir código)

P12 debe estar CERRADA: `P12A-9` (mcp handlers) y `P12B-8` (CLI clap nativo)
commiteados. Verificalo con `git log --oneline -20` y leyendo el final de
`progreso-p12a.md` / `progreso-p12b.md`. Si NO está cerrada: STOP, avisá y
no avances (los territorios de P13 pisan crates de P12).

## TERRITORIO (solo tuyo)

- `rust/crates/cortex-mcp/` COMPLETO (agregás transporte HTTP; el catálogo/
  ruteo quedan intocables — están congelados por golden P9)
- Extensiones PUNTUALES en `rust/crates/cortex-app/src/`: SOLO
  `append_row_external` en episodic y `render_yaml` en session (§6.3 del doc 11)
- Dentro de `rust/crates/cortex-companion/`: SOLO `src/sync.rs`,
  `src/daemon.rs`, `src/agent.rs` y sus tests (lib.rs/auth.rs/client.rs/bin/*
  son del stream B — consumí los tipos de lib.rs, NUNCA los redefinas ni edites)
- Edits quirúrgicos en `rust/Cargo.toml` SOLO para la feature de rmcp
  (`transport-streamable-http-server`), append-only, validar
  `cargo metadata -q` tras cada edit
- Gates `bench/parity/*p13a*` y ÚNICAMENTE `docs/transformacion/progreso-p13a.md`

PROHIBIDO tocar: `cortex-config`, `cortex-cli`, `cortex-doctor`,
`cortex-brain`, lib.rs/auth.rs/client.rs/bins del crate companion,
ADR-COMPANION-*.md, README.md, HANDOFF.md, ESTADO-ACTUAL.md, docs 09/12,
ni nada de `bench/parity/*p13b*`.

## SECUENCIA ANTI-COLISIÓN (vinculante)

El stream B hace PRIMERO el scaffolding del crate (gate R0-B). Hasta que
veas ese commit en trunk (`git log --oneline | grep -i p13`), trabajá SOLO
en tus otros territorios. Orden recomendado mientras tanto:

1. **R5-prep**: extensiones cortex-app (`append_row_external`,
   `render_yaml`) + tests unitarios propios (~50 LOC según §6.3).
2. **R1**: transporte HTTP de cortex-mcp.

Cuando R0-B esté commiteado: pasá al daemon/sync (R2-R4) sobre el crate.

## TU COLA DE GATES (un commit por gate, estilo Obra 07)

| Gate | Contenido | Criterio de pase (doc 11 §13) |
|---|---|---|
| R1 | `serve_http_blocking` + feature rmcp | **equivalencia estructural** vs golden list_tools.json (null≡ausente, descriptions/schemas profundos idénticos — decisión FIRMADA, Anexo A) + payload `cortex_ping` byte-a-byte VÍA HTTP loopback |
| R2 | `daemon.rs` read-only: hello/health/manifest + deletes | goldens hello/health · handshake mismatch rechaza · path-traversal rechazado (≥6 casos: `../x`, `/abs`, `vault/../../etc`, …) |
| R3 | `sync.rs`+`agent.rs`: push manifest+blobs+deletes+reindex | round-trip fixture 200 archivos · alta/baja/modificación convergen · index_lag converge a ~0 |
| R4 | reads remotas paridad | G-R1: search/context/next `--json` byte-a-byte local vs remote sobre fixture común loopback |
| R5 | op-log Node→PC + integrador idempotente | merge concurrente determinista: 2 productores × 500 ops ⇒ JSONL final == esperado byte-a-byte, 0 pérdidas, crash mid-batch re-pull sin duplicar |
| R6 | write-through sesiones/notas | YAML generado en Node == YAML integrado en PC (bytes) |

Prefijo de commits: `feat(obra13 R1/R2/… A)`.

## ⚠️ GUARDARRAILES DE RECURSOS (VINCULANTES — sesiones anteriores murieron por RAM)

Máquina: 11 GiB RAM / 20 cores, DOS streams en paralelo. Obligatorio:

- **R0.** Al arrancar: `pgrep -af "pytest|cargo|python"` — matá zombis heredados.
- **R1.** Exportá al inicio:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6
  ```
- **R2. Verificación POR NIVELES:** Nivel 1 (iteración libre):
  `cargo fmt --all --check && cargo clippy -p <tu-crate> --all-targets -- -D warnings && cargo test -p <tu-crate>`.
  Nivel 2 (pre-commit): tu golden build/verify. Nivel 3 (oráculo Python
  `.venv/bin/python -m pytest tests/unit tests/integration --no-cov`): UNA vez
  por tarea, justo antes del commit, SIEMPRE bajo lock R3. PROHIBIDO durante iteración.
- **R3. LOCK de operaciones pesadas** (goldens con modelos ONNX, suite completa):
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Antes de entrar: `free -m` → available < 4000 MB ⇒ esperá 60 s y reintentá.
- **R4.** Todo comando potencialmente pesado envuelto en `timeout 1200 <cmd>`.
- **R5.** Un solo proceso pesado a la vez (nada de pytest en background mientras compilás).
- **R6. COMMIT TEMPRANO:** gate verde ⇒ commit atómico INMEDIATO + actualizar
  `progreso-p13a.md` justo después. Lo no commiteado se pierde si morís.
- **R7.** `git add` SOLO tus archivos. Fuera de todo commit: `uv.lock`,
  `progress.md`, artefactos runtime.

## Reglas heredadas vigentes

Paridad bit-exacta como contrato · fallo explícito ante cualquier condición
no soportada (patrón P6/P9) · un gate por commit · sin dependencias nuevas
sin ADR (las tuyas ya están aprobadas en ADR-COMPANION-0/2 del doc 11 §14:
rmcp-http y axum interno del SDK; notify es del stream B) · suite Python =
ORÁCULO compartido (por eso el lock R3) · wire-format MCP: omisión rmcp
canónica, payloads byte-a-byte (RESUELTO, Anexo A del doc 11).

## Definición de hecho de tu stream

R1–R6 commiteados con sus gates verdes + suite Python oráculo verde en cada
commit + `progreso-p13a.md` actualizado con evidencia por gate (comandos y
salidas, no checkboxes). Al terminar: anunciá "STREAM A P13 COMPLETO" y
dejá registrado qué falta del lado B para el cierre integral.
