# PROMPT AGENTE PARALELO — Cierre Obra 07: T3 + T6 (terminal dedicada distinta)

Sos el agente PARALELO de la sesión de **CIERRE RESIDUAL de la Obra 07**.
Hay OTRO agente ejecutando T2 (wireado CLI) y luego T4 (pipeline stage) en
este mismo working tree. Tu trabajo es adelantar las tareas **T3 y T6** SIN
pisarlo — tu carga fue dimensionada pareja a la suya.

Ponete en contexto leyendo EN ESTE ORDEN:

1. `docs/transformacion/PROMPT-PARALELO-CIERRE.md` (este archivo — reglas vinculantes)
2. `docs/transformacion/HANDOFF.md` ("HANDOFF ACTIVO"; §4.8 RESUELTO — Anexo A doc 11)
3. `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9 (mapa general)
4. `docs/transformacion/progreso-cierre.md` (leelo COMPLETO: estado real de T1/T5/T2 y los patrones de gate usados — replicalos)
5. Creá `docs/transformacion/progreso-cierre-paralelo.md` — tu ÚNICO registro de progreso. **NUNCA edites `progreso-cierre.md`** (es del otro agente)

## PRECONDICIONES

- `git log --oneline -8`: verificá que T1 (`21536f5`) y T5 (`f6fb828`)
  estén commiteadas y que T2 esté EN CURSO (WIP de cortex-cli o
  cierre_cli_golden). Si el principal ya anunció T3/T6 hechas, STOP y avisá.
- Baseline oráculo registrado en progreso-cierre.md (2552 passed): tu meta es
  mantenerlo verde en cada commit.

## DIVISIÓN DE CARGA ACORDADA (vinculante)

| Tarea | Dueño | Motivo |
|---|---|---|
| T2 wireado CLI | Principal (en curso) | ya tiene el WIP y el golden |
| T4 pipeline stage | Principal (después de T2) | chica, cambio de contexto barato |
| **T3 autopilot completo** | **VOS** | service+cli+tools MCP ×5 diferidas por T1 |
| **T6 ratatui sesiones** | **VOS** | autónoma en cortex-tui |
| T7 refresco documental | el que termine ÚLTIMO | integra ambos registros |

## REGLAS ANTI-COLISIÓN CON EL AGENTE DE T2/T4 (vinculantes)

PROHIBIDO tocar:
- `rust/crates/cortex-cli/` EXCEPTO `src/commands/autopilot.rs`
  (y solo tras verificar en `git status` que ese archivo está limpio;
  si está sucio, esperá y reintentá)
- `rust/crates/cortex-pipeline/**` y `bench/parity/*pipeline*` (del principal, T4)
- `bench/parity/cierre_cli_golden*` · `docs/transformacion/progreso-cierre.md`
- Cualquier archivo que aparezca MODIFICADO por el otro agente en git status

Tu registro de claims: al INICIO de cada tarea escribí en
`progreso-cierre-paralelo.md`: `[CLAIM] <T-n> iniciada <fecha>` y al terminar
`[DONE]`. Si encontrás que la tarea ya fue commiteada por el otro
(`git log | grep`), saltala y pasá a la siguiente.

Commits: prefijo `feat(obra07 cierre T<n>-par)` · `git add` SOLO tus archivos
· `Cargo.lock` incluílo solo si tu diff lo requiere.

## TU COLA (en este orden)

### PRIMERA — T3: autopilot service + cli + autopilot-tools MCP (~800 LOC) [LA GORDA, ARRANCÁ ACÁ]

1. Porte de `cortex/autopilot/service.py` (444) a
   `rust/crates/cortex-autopilot/` orquestando sobre SessionService +
   ActionEngine NATIVOS (la capa de decisión policies/detectors/lifecycle ya
   existe desde P12B-5 — extendlá, no la reimplementes).
2. Subapp cli: completá `rust/crates/cortex-cli/src/commands/autopilot.rs`
   (único archivo permitido de cortex-cli — verificá que esté limpio antes).
3. **Autopilot-tools MCP ×5** (diferidas por T1): nuevo módulo
   `rust/crates/cortex-mcp/src/handlers_autopilot.rs` (archivo NUEVO — no
   toques handlers_* existentes ni server.rs más allá del routing mínimo,
   siguiendo el patrón SESSION_TOOLS de P12A-9). Wire-format: emisor propio
   con orden pydantic, byte-a-byte (patrón T1).
- **Gate**: (a) golden autopilot service — policies/detectors/lifecycle
  end-to-end sobre sesiones fixture REALES vía SessionService nativa vs
  `cortex/autopilot/service.py` Python real; (b) los 5 tools MCP byte-a-byte
  vs `_dispatch_tool_sync`; (c) ampliar doctor_golden con escenario
  autopilot end-to-end. Suite oráculo verde.
- Commits separados por pieza si ayudan: `feat(obra07 cierre T3-par …)`.

### SEGUNDA — T6: pantalla sesiones ratatui

Reemplazo ratatui de la TUI rich vieja (decisión doc 09 §3.8) sobre
SessionService nativo, dentro de `rust/crates/cortex-tui/`.
Misma INFORMACIÓN que `session list --json` expone (paridad de datos, no de
estética rich). Integración con el CLI: SOLO si requiere tocar
`commands/` un archivo nuevo `sessions_tui.rs` limpio en git status; si
necesitarías editar main.rs, dejalo documentado como paso de integración
pendiente para el otro agente y no lo hagas.
- **Gate**: snapshot render <50 ms + test de datos mostrados == --json.
- Commit `feat(obra07 cierre T6-par)`.

## NO TE CORRESPONDE (otro agente / cierre posterior)

T2 (en curso) y T4 pipeline stage (ambas del principal) · T7 refresco
documental de ESTADO-ACTUAL/HANDOFF/doc 12 (lo hace quien termine ÚLTIMO,
integrando ambos registros) · baja definitiva de Python · cortex-companion (P13).

## ⚠️ GUARDARRAILES DE RECURSOS (VINCULANTES — DOS agentes pesados comparten 11 GiB RAM)

- **R0.** Al arrancar: `pgrep -af "pytest|cargo|python"` — matá SOLO zombis
  heredados (procesos muertos sin terminal). NUNCA mates procesos del otro agente.
- **R1.** Exportá al inicio:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=4
  ```
- **R2. Por niveles:** Nivel 1 (libre): fmt + clippy -p <tu-crate> + cargo
  test -p <tu-crate>. Nivel 2 (pre-commit): tus goldens. Nivel 3 (suite
  Python completa --no-cov): UNA vez por tarea, pre-commit, bajo lock R3.
- **R3. LOCK de operaciones pesadas:**
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Antes de entrar: `free -m` → available < 4000 MB ⇒ esperá 60 s.
- **R4.** `timeout 1200 <cmd>` en todo comando potencialmente pesado.
- **R5.** Un solo proceso pesado tuyo a la vez (y respetá el lock: el otro
  agente puede estar dentro).
- **R6. COMMIT TEMPRANO:** gate verde ⇒ commit atómico inmediato + actualizar
  `progreso-cierre-paralelo.md` con evidencia (comandos y salidas).
- **R7.** Antes de cada commit re-chequeá `git status`: si el otro agente
  tocó un archivo que vos necesitás, esperá a que lo commitee.

## Reglas heredadas vigentes

Paridad bit-exacta como contrato · drift visible ⇒ revert · fallo explícito
para lo no portado · un gate por commit · sin dependencias nuevas sin ADR
chico · wire-format MCP: omisión rmcp canónica + payloads byte-a-byte
(Anexo A doc 11) · suite Python = ORÁCULO.

## Definición de hecho de tu stream

T3 (+T6 si llegaste) commiteadas con gates byte-a-byte verdes, suite
Python 2552+ passed 0F 0E intacta, `progreso-cierre-paralelo.md` con
evidencia completa por tarea. Al terminar anunciá **"AGENTE PARALELO
COMPLETO — T3/T6 listas"** listando qué quedó pendiente para el T7 final.
