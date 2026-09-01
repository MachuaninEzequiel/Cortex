# PROMPT STREAM A — Reanudación P12A (pegar en terminal dedicada)

Sos el agente del **Stream A** ("contenido-y-escritura") de la fase P12 de la
Obra 07 (migración Python→Rust de Cortex). Ponete en contexto leyendo EN ESTE
ORDEN, sin saltarte ninguno:

1. `docs/transformacion/PROMPT-REANUDAR-A.md` (este archivo — son reglas vinculantes)
2. `docs/transformacion/HANDOFF.md` (sección "HANDOFF ACTIVO")
3. `docs/transformacion/09-DEUDA-MIGRACION-PYTHON.md` §7 (reglas duras dual-stream)
4. `docs/transformacion/progreso-p12a.md` (tu único registro de progreso)

**TERRITORIO (solo tuyo):** `rust/crates/cortex-app/`, handlers de
`rust/crates/cortex-mcp/src/server.rs`, NUEVO `rust/crates/cortex-services/`,
gates `bench/parity/*p12a*`, y ÚNICAMENTE
`docs/transformacion/progreso-p12a.md`. PROHIBIDO tocar crates nuevos de B,
`cortex-cli`, `bench/parity/*p12b*`, ni ESTADO-ACTUAL.md / HANDOFF.md / doc 09.

## Estado real verificado al momento de reanudar

- **P12A-1 está COMMITEADA** (`c9b62ab`): episodic.append + semantic.index_file
  + security::resolve_safe, gate verde, suite Python 2455 passed.
- **La sesión anterior MURIÓ a mitad de P12A-2 (workitems/hu)** dejando WIP
  SIN COMMITEAR en el working tree:
  - `rust/crates/cortex-app/src/workitems.rs` (~711 líneas)
  - `rust/crates/cortex-app/examples/p12a2_check.rs` (~457 líneas)
  - `bench/parity/p12a2_golden.py` (~300 líneas) + `bench/parity/golden_p12a2/`
  - edits en `rust/crates/cortex-app/Cargo.toml` y `src/lib.rs`

## PRIMER PASO OBLIGATORIO — triage del WIP

Leé COMPLETO ese WIP antes de escribir nada nuevo. Determiná si compila
(`cargo check -p cortex-app`) y qué le falta. **Continualo hasta gate verde;
NO lo reinicies desde cero** salvo rotura fundamental (si lo descartás,
documentalo en progreso-p12a.md con el motivo).

## ⚠️ GUARDARRAILES DE RECURSOS (VINCULANTES)

Las dos sesiones anteriores murieron por saturación de RAM: máquina con
**11 GiB RAM / 20 cores**, dos streams corriendo en paralelo suites pytest
con ONNX/chroma reales y builds de Cargo simultáneos. Esto NO se repite:

- **R0.** Al arrancar: `pgrep -af "pytest|cargo|python"` — si hay procesos
  zombis heredados de sesiones muertas, matálos antes de empezar.
- **R1.** Exportá al inicio de la sesión:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6
  ```
- **R2. VERIFICACIÓN POR NIVELES — nunca correr todo por defecto:**
  - *Nivel 1* (cada iteración de código, libre): `cargo fmt --all --check &&
    cargo clippy -p cortex-app --all-targets -- -D warnings && cargo test -p cortex-app`
  - *Nivel 2* (pre-commit del gate): tu golden p12a2 build/verify + checker
    Rust — SIEMPRE bajo lock R3.
  - *Nivel 3* (oráculo completo `.venv/bin/python -m pytest tests/unit
    tests/integration --no-cov`): UNA sola vez por tarea completada, justo
    antes del commit, SIEMPRE bajo lock R3. **PROHIBIDO durante iteración.**
  - En pytest: siempre `--no-cov`; durante iteración preferí subconjuntos
    (`tests/unit/workitems …`) o `-m "not slow"`.
- **R3. LOCK DE OPERACIONES PESADAS:** antes de Nivel 2/3 (o cualquier carga
  de modelos ONNX/chroma):
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Lock ocupado = el otro stream está corriendo algo pesado ⇒ esperá.
  Antes de entrar: `free -m` → si available < 4000 MB, esperá 60 s y reintentá.
- **R4.** Todo comando potencialmente pesado envuelto en
  `timeout 1200 <cmd>` — un cuelgue no mata la terminal.
- **R5.** Un solo proceso pesado a la vez, incluso dentro de tu stream
  (nada de pytest en background mientras compilás).
- **R6. COMMIT TEMPRANO:** apenas el gate esté verde, commit atómico
  prefijado `feat(obra07 P12A-…)`; INMEDIATAMENTE después actualizá
  `progreso-p12a.md`. Lo no commiteado se pierde si la sesión muere.
- **R7.** `git add` SOLO de tus archivos. Fuera de todo commit: `uv.lock`,
  `progress.md`, artefactos runtime (`.cortex/*.jsonl`, `vault/.cortex_index.json`).

## Reglas heredadas vigentes

Paridad bit-exacta como contrato · fallo explícito para backends no porteados
(patrón P6/P9) · un gate por commit · sin deps nuevas sin ADR chico · handlers
MCP de escritura siguen con fallo explícito hasta la decisión del dueño sobre
wire-format rmcp (§7.1.4) · suite Python completa = ORÁCULO compartido (por eso
el lock R3: debe seguir verde en cada commit, pero SERIALIZADA entre streams).

## Tu cola tras recuperar P12A-2

P12A-3 pr_context (~623) → P12A-4 doc_generator/validator/verifier (~590) →
P12A-5 spec/note services (~541) → P12A-6 docs-migrate (~565) → P12A-7 context
extras (~1902) → P12A-8 documenter/interactive (~342) → P12A-9 mcp handlers.

Empezá anunciando tu plan de triage/recuperación del WIP y avanzá tarea por
tarea, commiteando cada una.
