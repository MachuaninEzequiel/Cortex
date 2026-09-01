# PROMPT REANUDAR-D — Continuación CIERRE OBRA 07 (post T3 + T6)

Sos el agente de **CONTINUACIÓN del Cierre Residual de la Obra 07** (migración
Python→Rust de Cortex). Este prompt es el handoff FINAL de la fase de dos
agentes en paralelo: T3 y T6 quedaron commiteadas. Reemplaza a
PROMPT-REANUDAR-C.md (que quedó desactualizado: marcaba T6 "en curso" y
"NO TOCAR cortex-tui" — hoy T6 está HECHA y cortex-tui es territorio libre
salvo el paso de integración pendiente detallado abajo). Reglas vinculantes
y definición de hecho de la Obra: `docs/transformacion/PROMPT-CIERRE-OBRA07.md`
— LEELO PRIMERO junto con este archivo.

## Contexto en 30 segundos

Cierre residual post-P12 de la migración total Python→Rust de Cortex
(`cortex-memory` v0.7.0). Cola original T1–T7 en curso sobre la rama
`feature/transformacion-2026-08`. Se ejecutaron DOS agentes en paralelo
sobre el mismo working tree; el stream PARALELO (T3+T6) ya terminó:

- **AGENTE PRINCIPAL** — T1/T5/T2-núcleo hechas; le quedan T2-cola → T4.
- **AGENTE PARALELO** — T3 ✅ (`e089a25`) y T6 ✅ (`fa11473`), con gates
  byte-a-byte verdes y oráculo 2552 intacto en cada commit. Su registro:
  `docs/transformacion/progreso-cierre-paralelo.md` (evidencia completa).
- **T7 refresco documental**: quien termine ÚLTIMO, integrando ambos
  registros (progreso-cierre.md + progreso-cierre-paralelo.md).

## Estado por tareas (verificar con `git log --oneline -16`)

| Tarea | Estado | Evidencia / Commit |
|---|---|---|
| Precondiciones + baseline | ✅ | `538cec4` `c9229f8` |
| T1 handlers MCP no-sesión | ✅ | `21536f5` — gate `bench/parity/cierre_mcp_golden.py` (51 escenarios) |
| T5 oráculo 100% verde | ✅ | `f6fb828` — 2552 passed 0F 0E |
| T2 CLI wireado NÚCLEO | ✅ | `c210cef` `33871a7` — gate `bench/parity/cierre_cli_golden.py` (19 casos) |
| T2-cola | ⏳ | inventario en `progreso-cierre.md` (del principal) |
| T3 autopilot service+cli+mcp×5 | ✅ paralelo | `e089a25` — gate `bench/parity/cierre_autopilot_golden.py` + checker `cierre_autopilot_check` |
| T4 pipeline stage Documentation | ⏳ | del principal (post T2-cola) |
| T6 pantalla ratatui sesiones | ✅ paralelo | `fa11473` — gate `rust/crates/cortex-tui/tests/sessions_screen.rs` (5 tests) |
| T6-b integración CLI watch/tui | ⏳ | PASO PENDIENTE documentado abajo |
| T7 refresco documental | ⏳ | quien termine ÚLTIMO |

Registros únicos de progreso: `docs/transformacion/progreso-cierre.md`
(principal) y `docs/transformacion/progreso-cierre-paralelo.md` (paralelo).

## Lectura obligatoria (en orden)

1. `docs/transformacion/PROMPT-CIERRE-OBRA07.md` (reglas vinculantes, guardarrailes R0–R7, definición de hecho)
2. Este archivo
3. `docs/transformacion/progreso-cierre.md` COMPLETO (estado T2, cola restante)
4. `docs/transformacion/progreso-cierre-paralelo.md` (evidencia T3/T6)
5. `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.2 (mapa de brecha)
6. `docs/transformacion/11-COMPANION-ENGINE-P13.md` Anexo A (wire-format MCP)

## Precondiciones de arranque

1. `git status` — esperable: WIP de T2-cola del principal en
   `cortex-cli/*` (`session_cmd.rs`, `memory.rs`, `memory_cmds.rs`, `lib.rs`,
   `main.rs`, `pyjson.rs`, `Cargo.toml`) y `rust/Cargo.lock` con hunks de
   ambos streams aún no commiteados. NO commitear `Cargo.lock` sin separar
   hunks (patrón: `git diff rust/Cargo.lock` → aplicar solo el hunk propio
   con `git apply --cached`).
2. `pgrep -af "pytest|cargo|python"` → sin zombis heredados (R0).
3. `free -m` → available ≥ 4000 MB.
4. Exportar (R1):
   ```bash
   export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
          NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=4
   ```
5. RAM 11 GiB compartida: un solo proceso pesado a la vez; ops pesadas bajo
   lock R3 (`mkdir .cortex/heavy.lock` con trap rmdir; esperar si
   available < 4000 MB) y `timeout 1200` (R4).

## Cola restante (en orden de valor)

### T2-cola (del principal — ver su progreso-cierre.md)
Inventario y patrones en `progreso-cierre.md` sección "Cola restante".
Territorio: `rust/crates/cortex-cli/src/` (EXCEPTO `commands/autopilot.rs`,
que ya es 100% nativo — no pisarlo). Gate: `bench/parity/cierre_cli_golden.py`.

### T4 pipeline stage Documentation (del principal)
Conecta el stage al persister nativo (P5). Gate propio según plan.

### T6-b — INTEGRACIÓN CLI de la pantalla sesiones (PENDIENTE, paralelo la dejó documentada)
`cortex session watch` (y/o `session tui`) todavía pasa por el CLI Python
(rich). La pantalla nativa EXISTE y está gateada:
- `rust/crates/cortex-tui/src/sessions.rs`: `SessionsScreenData::from_service(&SessionService, status_filter)` + `render(f, &data)` (puro, read-only, contrato v1 sin input).
- Requiere wirear un subcomando en `cortex-cli/src/commands/session_cmd.rs` (hoy libre: el paralelo terminó) o `main.rs`: construir `SessionService` con `SessionStorage::new(repo_root/.cortex/sessions)` (patrón `cortex_app::session::service::SessionService`), armar el snapshot y correr un loop ratatui (poll + Ctrl+C). NO romper el passthrough del resto de `session`.
- Gate existente para no romper: `cargo test -p cortex-tui` (5 tests de `sessions_screen.rs`).

### T7 refresco documental (quien termine ÚLTIMO)
Actualizar `ESTADO-ACTUAL.md`, `HANDOFF.md` (sección activa) y doc 12 §9.2
con: T1–T6 completas, T2-cola/T4 según cierre real, estado de la suite
(2552), y el estado de `cortex-companion` (P13 — FUERA del cierre).
Anunciar **"OBRA 07 — CIERRE COMPLETO"** solo si T2-cola + T4 + T6-b están
hechas o explícitamente deudadas. La baja definitiva de Python sigue
condicionada a §9.2 resuelto + oráculo verde (doc 12 §7).

## NO TE CORRESPONDE
`cortex-companion` (P13) · borrar Python vivo del oráculo · cambiar goldens
existentes sin motivo · `uv.lock`/`progress.md` en commits.

## Patrones técnicos (heredados, vinculantes)

- **Paridad bit-exacta como contrato**: los gates comparan byte-a-byte
  contra el oráculo Python REAL (dispatcher `_dispatch_tool_sync`,
  `cortex.autopilot.service` real, CLIs reales). Normalizaciones
  permitidas SOLO: `{{ROOT}}`, `{{TS}}` (ISO timestamps), `{{MIN}}`
  (minutos de warnings temporales), `{{FP}}` (fingerprints).
- **Wire-format MCP**: omisión rmcp canónica del envelope + payloads de
  tools byte-a-byte (Anexo A doc 11). Familias no nativas ⇒ fallo
  EXPLÍCITO documentado (patrón P6/P9), nunca paridad fingida.
- **Un gate por commit**; commits atómicos prefijados
  `feat(obra07 cierre T<n>…)` / `docs(obra07 cierre …)`; `git add` SOLO
  tus archivos.
- **Cargo.lock**: commitear únicamente el hunk propio (los hunks ajenos
  del otro stream pueden estar aún en el working tree).

## Cómo correr los gates (todos verdes al cierre del stream paralelo)

```bash
# Golden T3 (service e2e + MCP ×5 byte-a-byte + CLI dual py-vs-rs):
.venv/bin/python bench/parity/cierre_autopilot_golden.py verify --out bench/parity/.p12-cierre-autopilot
cd rust && cargo run -p cortex-autopilot --example cierre_autopilot_check -- ../bench/parity/.p12-cierre-autopilot

# Golden doctor ampliado (escenario autopilot_e2e):
.venv/bin/python bench/parity/doctor_golden_p12b.py verify --out bench/parity/.p12b-doctor
cargo run -p cortex-doctor --example doctor_check -- ../bench/parity/.p12b-doctor

# Gate T6 (datos == session list --json, <50ms):
cargo test -p cortex-tui

# Suite oráculo COMPLETA (R3 lock + timeout):
timeout 2400 .venv/bin/python -m pytest tests/unit tests/integration tests/e2e \
  --no-cov --tb=no -p no:randomly   # → 2552 passed, 21 skipped, 0F 0E
```

## Definición de hecho de la Obra (heredada)
Suite Python = ORÁCULO (2552 passed 0F 0E) · gates byte-a-byte por pieza ·
drift visible ⇒ revert · fallo explícito para lo no portado · sin
dependencias nuevas sin ADR chico · al terminar anunciá el cierre con el
estado honesto de cada tarea y lo deudado.
