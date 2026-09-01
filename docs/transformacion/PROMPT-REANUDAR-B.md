# PROMPT STREAM B — Reanudación P12B (pegar en terminal dedicada distinta)

Sos el agente del **Stream B** ("dominios-e-integración") de la fase P12 de la
Obra 07 (migración Python→Rust de Cortex). Ponete en contexto leyendo EN ESTE
ORDEN, sin saltarte ninguno:

1. `docs/transformacion/PROMPT-REANUDAR-B.md` (este archivo — reglas vinculantes)
2. `docs/transformacion/HANDOFF.md` (sección "HANDOFF ACTIVO")
3. `docs/transformacion/09-DEUDA-MIGRACION-PYTHON.md` §7 (reglas duras dual-stream)
4. `docs/transformacion/progreso-p12b.md` (tu único registro de progreso)

**TERRITORIO (solo tuyo):** NUEVOS crates `cortex-workspace`,
`cortex-webgraph-server`, `cortex-enterprise`, `cortex-doctor`,
`cortex-autopilot`, `cortex-pipeline`; reescritura de `rust/crates/cortex-cli/`;
gates `bench/parity/*p12b*`; y ÚNICAMENTE
`docs/transformacion/progreso-p12b.md`. PROHIBIDO editar `cortex-app` /
`cortex-mcp` / `cortex-actions` (stream A) — consumilos como dependencia
read-only de Cargo.

## Estado real verificado al momento de reanudar

- **P12B-1 está COMMITEADA** (`e65109b`): crate cortex-workspace completo,
  gate byte-parity, suite Python 2455 passed.
- **La sesión anterior MURIÓ a mitad de P12B-2 (webgraph-server axum)**
  dejando WIP SIN COMMITEAR en el working tree:
  - `rust/crates/cortex-webgraph-server/` completo (~3.5k líneas:
    `server.rs` 413, `federation.rs` 367, `openers.rs` 34,
    `examples/webgraph_check.rs` 463, más módulos restantes)
  - `bench/parity/webgraph_golden_p12b.py` (~556 líneas) +
    `bench/parity/golden_webgraph/`

## PRIMER PASO OBLIGATORIO — triage del WIP

Leé COMPLETO ese WIP antes de escribir nada nuevo. Determiná si compila
(`cargo check -p cortex-webgraph-server`) y qué le falta al gate.
**Continualo hasta gate verde; NO lo reinicies desde cero** salvo rotura
fundamental (si lo descartás, documentalo en progreso-p12b.md con el motivo).

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
    cargo clippy -p cortex-workspace -p cortex-webgraph-server --all-targets
    -- -D warnings && cargo test -p <crate-tocado>`
  - *Nivel 2* (pre-commit del gate): tu golden webgraph build/verify + checker
    Rust — SIEMPRE bajo lock R3.
  - *Nivel 3* (oráculo completo `.venv/bin/python -m pytest tests/unit
    tests/integration --no-cov`): UNA sola vez por tarea completada, justo
    antes del commit, SIEMPRE bajo lock R3. **PROHIBIDO durante iteración.**
  - En pytest: siempre `--no-cov`; durante iteración preferí subconjuntos
    (`tests/unit/webgraph …`) o `-m "not slow"`.
- **R3. LOCK DE OPERACIONES PESADAS:** antes de Nivel 2/3 (o cualquier carga
  de modelos ONNX/chroma — ojo: tu gate workspace_golden_p12b.py SÍ carga
  PyYAML/oráculo pesado):
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Lock ocupado = el otro stream está corriendo algo pesado ⇒ esperá.
  Antes de entrar: `free -m` → si available < 4000 MB, esperá 60 s y reintentá.
- **R4.** Todo comando potencialmente pesado envuelto en
  `timeout 1200 <cmd>` — un cuelgue no mata la terminal.
- **R5.** Un solo proceso pesado a la vez, incluso dentro de tu stream.
- **R6. COMMIT TEMPRANO:** apenas el gate esté verde, commit atómico
  prefijado `feat(obra07 P12B-…)`; INMEDIATAMENTE después actualizá
  `progreso-p12b.md`. Lo no commiteado se pierde si la sesión muere.
- **R7.** `git add` SOLO de tus archivos. `rust/Cargo.toml` raíz y
  `Cargo.lock`: edits quirúrgicos append-only de TU member/deps; si hay hunks
  ajenos de A sin commitear, no los stages (regla §7.2.2). Fuera de commits:
  `uv.lock`, `progress.md`, artefactos runtime.

## Reglas heredadas vigentes

Paridad byte-a-byte como contrato · normalizaciones pactadas
{{ROOT}}/{{MS}}/{{TS}}/{{DATE}} · fallo explícito para backends no porteados
· un gate por commit · sin deps nuevas sin ADR chico (axum aprobado;
reqwest aprobado para pipeline) · `resolve_safe` es territorio de A, NO lo
dupliques · tutor (P12B-7) NO portear ciego: decisión del dueño pendiente ·
CLI nativo (P12B-8) es EL punto de sincronización final con A — no adelantarlo.

## Tu cola tras recuperar P12B-2

P12B-3 enterprise/review_knowledge (~2441) → P12B-4 doctor (~925) →
P12B-5 autopilot (~1902) → P12B-6 pipeline SDDwork (~1708) → P12B-7 tutor
(decisión pendiente) → P12B-8 CLI clap nativo (último).

Empezá anunciando tu plan de triage/recuperación del WIP y avanzá tarea por
tarea, commiteando cada una.
