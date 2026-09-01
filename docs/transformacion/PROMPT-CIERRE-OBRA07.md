# PROMPT CIERRE OBRA 07 — Residual post-P12 (pegar en terminal dedicada)

Sos el agente de **CIERRE RESIDUAL de la Obra 07** (migración Python→Rust de
Cortex). P0–P12 están completadas y gateadas; tu trabajo es liquidar la
brecha restante documentada en `docs/transformacion/12-AUDITORIA-PYTHON-
RESIDUAL.md` §9.2 hasta dejar la Obra 07 en condiciones de iniciar la **baja
definitiva de Python**.

Ponete en contexto leyendo EN ESTE ORDEN, sin saltarte ninguno:

1. `docs/transformacion/PROMPT-CIERRE-OBRA07.md` (este archivo — reglas vinculantes)
2. `docs/transformacion/HANDOFF.md` (sección "HANDOFF ACTIVO"; §4.8 RESUELTO: omisión rmcp canónica, payloads byte-a-byte — ver Anexo A de doc 11)
3. `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` COMPLETO (§9 es TU mapa de trabajo)
4. `docs/transformacion/progreso-p12b.md` tabla P12B-8 (el patrón de wireado CLI que replicás) y `progreso-p12a.md` sección P12A-9 (el patrón de handlers in-process que replicás)
5. Creá `docs/transformacion/progreso-cierre.md` — tu ÚNICO registro de progreso

## PRECONDICIONES DE ARRANQUE (verificar antes de escribir código)

1. Trunk limpio: `git status` — si hay cambios sin commitear de la sesión de
   depreciación post-P12 (`cortex/brain/*`, `cortex/embedders/openai.py`,
   `cortex/hooks/agent_hooks.py`, `HANDOFF.md`, `docs/transformacion/12-*`),
   comitealos PRIMERO como `chore(obra07): depreciación post-P12 según doc 12`
   (son revisados y verificados: tests/unit/embedders 24 passed).
2. Corré la suite baseline y REGISTRÁ en progreso-cierre.md el set EXACTO de
   fallos e2e preexistentes:
   `.venv/bin/python -m pytest tests/unit tests/integration --no-cov` bajo
   lock R3 (abajo). Ese set es tu línea de base para demostrar "0 regresiones".

## TERRITORIO (solo tuyo)

- `rust/crates/cortex-mcp/src/`: handlers no-sesión (nuevos módulos handlers_*)
- `rust/crates/cortex-cli/src/`: commands/* nuevos + main.rs (wireado)
- `rust/crates/cortex-autopilot/`, `rust/crates/cortex-pipeline/` (extensión)
- `rust/crates/cortex-tui/` (SOLO la pantalla de sesiones ratatui de T6)
- Tests e2e Python rotos: `tests/e2e/**` SOLO los del baseline roto (T5)
- Gates `bench/parity/*cierre*` · `docs/transformacion/progreso-cierre.md`
- Refresco documental AL CIERRE: `ESTADO-ACTUAL.md` + `HANDOFF.md` (flujo
  normal vigente: el dual-stream está cerrado)

PROHIBIDO: `rust/crates/cortex-companion/` (P13, otro plan), borrar código
Python vivo del oráculo, cambiar goldens existentes sin motivo documentado,
`uv.lock`/`progress.md` en commits.

## TU COLA DE TAREAS (orden de valor; un commit atómico por tarea)

### T1 — Handlers MCP no-sesión in-process (desbloqueados por §4.8)

Familias en fallo explícito hoy: search, context, sync_ticket, proposal,
documenter-briefing, finish_session, write_doc, self_review_note,
autopilot-tools, import/get_hu. Patrón EXACTO de P12A-9: backend inyectable
por familia + emisor wire-format propio (separadores ", "/": ", orden de
claves = declaración pydantic, mensajes ❌ byte-a-byte).
Los backends nativos existen: search/context (cortex-app::semantic+episodic+
context), documenter (cortex-app::documenter), write_doc/spec/note
(cortex-services), hu (cortex-app::workitems).
**Gate**: `bench/parity/cierre_mcp_golden.py` build/verify + checker Rust —
payload byte-a-byte contra `cortex/mcp/server.py` Python REAL por familia,
fixtures commiteados. Suite oráculo verde.

### T2 — Wirear subcomandos CLI restantes (mata el passthrough)

Sobre el esqueleto clap de P12B-8 (STUB_TABLE a nivel de datos), wireá:
search/search-vector/context/next/session{open,start,checkpoint,close,status,
list}/vault{stats,reindex --dry-run}/docs{search,migrate}/ci/hu/pr-context/
setup/mcp-serve. Cada uno delega in-process en su crate (NUNCA subprocess a
Python salvo rollback CORTEX_PY=1). Salidas texto/--json idénticas.
**Gate**: EXTENDER `bench/parity/cli_golden_p12b.py` (o crear cierre_cli_golden)
con ≥2 casos por subcomando (texto + --json) contra el CLI Python real;
byte-a-byte; cold start medido N=20 por subcomando (<100 ms).

### T3 — autopilot service + cli (~800 LOC)

La capa de decisión ya es nativa (P12B-5); portá `service.py` (444) y la
subapp cli (354) orquestando sobre SessionService + ActionEngine NATIVOS.
Los autopilot-tools MCP entran acá si no cerraron en T1.
**Gate**: ampliar doctor_golden (autopilot REAL end-to-end) + golden propio
de service (policies/detectors/lifecycle sobre sesiones fixture).

### T4 — pipeline stage Documentation (stub → real)

Conectar la stage al documenter/services nativos (P12B-6 dejó el stub).
**Gate**: ampliar `pipeline_golden_p12b.py` con flow Documentation pass/fail.

### T5 — Oráculo 100 % verde (limpieza de los 32F+3E e2e rotos)

Los fallos preexistentes vienen del commit de recatorización (imports de
módulos borrados). Para cada test roto: SI el escenario sigue teniendo
sentido, actualizalo a la estructura actual; SI NO, retiralo con justificación
una-por-una en progreso-cierre.md. PROHIBIDO debilitar asserts de tests vivos.
**Gate**: suite Python completa **0 failed 0 error** — primera vez desde la
recatorización. Esto es REQUISITO duro para autorizar la baja definitiva.

### T6 — (OPCIONAL, si el resto está verde) Pantalla sesiones ratatui

Reemplazo de session_tui rich (decisión doc 09 §3.8): pantalla ratatui sobre
SessionService nativo, misma información que el --json expone.
**Gate**: snapshot render <50 ms + paridad de DATOS (no de estética) contra
`session list --json`. Si no llegás, dejala documentada como única deuda UX.

### T7 — Refresco documental de cierre (obligatorio)

Al completar T1–T5 (+T6 si fue): actualizá `ESTADO-ACTUAL.md` (tabla de
fases + sección "lo que todavía depende de Python" reducida a lo REAL),
`HANDOFF.md` (nueva sección HANDOFF ACTIVO post-cierre), doc 12 §9.2
(marcando ítems resueltos), y anunciá **"OBRA 07 — CIERRE COMPLETO"**.
La baja definitiva de Python (wheels solo-Rust, README binarios, archivado
de goldens) es el PASO SIGUIENTE separado: no lo ejecutes en esta sesión.

## ⚠️ GUARDARRAILES DE RECURSOS (VINCULANTES — sesiones anteriores murieron por RAM)

Máquina: 11 GiB RAM / 20 cores. Obligatorio:

- **R0.** Al arrancar: `pgrep -af "pytest|cargo|python"` — matá zombis heredados.
- **R1.** Exportá al inicio:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6
  ```
- **R2. Verificación POR NIVELES:** Nivel 1 (iteración libre):
  `cargo fmt --all --check && cargo clippy -p <tu-crate> --all-targets -- -D warnings && cargo test -p <tu-crate>`.
  Nivel 2 (pre-commit): tus goldens build/verify. Nivel 3 (suite Python
  completa `--no-cov`): UNA vez por tarea, justo antes del commit, bajo lock R3.
  PROHIBIDO durante iteración (usá subconjuntos: `tests/unit/mcp …`).
- **R3. LOCK de operaciones pesadas** (goldens con ONNX/chroma, suite completa):
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Antes de entrar: `free -m` → available < 4000 MB ⇒ esperá 60 s y reintentá.
- **R4.** Todo comando potencialmente pesado envuelto en `timeout 1200 <cmd>`.
- **R5.** Un solo proceso pesado a la vez.
- **R6. COMMIT TEMPRANO:** tarea con gate verde ⇒ commit atómico INMEDIATO
  prefijado `feat(obra07 cierre T<n>)` + actualizar `progreso-cierre.md`
  justo después con evidencia (comandos y salidas, no checkboxes).
  Lo no commiteado se pierde si la sesión muere.
- **R7.** `git add` SOLO tus archivos.

## Reglas heredadas vigentes

Paridad bit-exacta como contrato · drift visible ⇒ revert · fallo explícito
para lo no portado (patrón P6/P9) · un gate por commit · sin dependencias
nuevas sin ADR chico · wire-format MCP resuelto (omisión rmcp canónica +
equivalencia estructural, Anexo A doc 11) · suite Python = ORÁCULO hasta la
baja final · verificación SIEMPRE contra código real, no checkboxes.

## Definición de hecho

T1–T5 y T7 completas con gates verdes + suite Python **100 % verde** +
passthrough CLI reducido a SOLO rollback CORTEX_PY=1 + progreso-cierre.md con
evidencia completa. T6 documentada como hecha o como única deuda abierta.
Al terminar anunciá **"OBRA 07 — CIERRE COMPLETO"** con el resumen de
métricas (subcomandos wireados, familias MCP in-process, cold start medido,
estado del oráculo).
