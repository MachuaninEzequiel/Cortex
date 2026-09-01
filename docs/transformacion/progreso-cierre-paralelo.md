# Progreso CIERRE OBRA 07 — STREAM PARALELO (T3 + T6)

> Registro ÚNICO del agente PARALELO. NUNCA editar `progreso-cierre.md`
> (pertenece al agente principal T2/T4). Prompt regente:
> `docs/transformacion/PROMPT-PARALELO-CIERRE.md`.

## Precondiciones verificadas al arranque (2026-08-25)

- ✅ `git log --oneline -8`: T1 (`21536f5`) y T5 (`f6fb828`) commiteadas;
  último commit `837c341` (estado fin de sesión, plan T2-T4).
- ✅ T2 EN CURSO por el principal: WIP sin commitear en
  `cortex-cli/{Cargo.toml,lib.rs,main.rs,pyjson.rs}` + `memory.rs`,
  `memory_cmds.rs` nuevos.
- ✅ `rust/crates/cortex-cli/src/commands/autopilot.rs` LIMPIO en git status
  (3265 bytes) — editable según reglas anti-colisión.
- ✅ Ni el principal ni nadie anunció T3/T6 hechas (grep en git log: vacío).
- ✅ R0: `pgrep -af "pytest|cargo|python"` → sin zombis heredados.
- ✅ RAM disponible: 8807 MB (≥4000 requerido). R1 exportado
  (threads=2, CARGO_BUILD_JOBS=4).

## División de carga

- Principal (otro agente): T2 wireado CLI + T4 pipeline stage.
- ESTE agente: **T3 autopilot completo** + **T6 ratatui sesiones**.
- T7 refresco documental: quien termine ÚLTIMO.

[CLAIM] T3 iniciada 2026-08-25
[DONE] T3 completada 2026-08-26 (commit e089a25)
[CLAIM] T6 iniciada 2026-08-26
[DONE] T6 completada 2026-08-26

## Evidencia T6

- `rust/crates/cortex-tui/src/sessions.rs` NUEVO: pantalla sesiones ratatui
  (reemplazo de la rich vieja, decisión doc 09 §3.8). `SessionRow` =
  espejo EXACTO de `_record_summary` (los 7 campos que emite
  `session list --json`); `SessionsScreenData::from_service` con la misma
  semántica de `list_command` (filtro status opcional, sort newest-first
  por opened_at, activa resuelta). Render puro snapshot→frame, read-only.
- `rust/crates/cortex-tui/tests/sessions_screen.rs` NUEVO (gate T6):
  (a) datos mostrados == `session list --json` (cada valor del payload
  aparece en el render; filas serializadas idénticas al dict del oráculo
  — verificado con SessionService nativo y sesiones REALES en tmp);
  (b) orden newest-first + marca de activa; (c) filtro por status +
  closed_at/mode inferido al cerrar (byo); (d) estado vacío
  "(no sessions on disk)"; (e) determinismo; (f) render promedio <50ms
  (RENDER_BUDGET_MS, N=200) — **5 passed**.
- Dependencias: cortex-tui += cortex-app (nativo), serde_json, tempfile
  (dev). Cero paquetes nuevos (todo ya en Cargo.lock).
- INTEGRACIÓN CLI PENDIENTE (documentada, NO hecha): wirear
  `cortex session watch/tui` nativo requiere tocar
  `cortex-cli/src/commands/session_cmd.rs` y/o `main.rs` (WIP T2 del
  principal) ⇒ prohibido por reglas anti-colisión. El siguiente agente
  debe agregar el subcomando que construya `SessionsScreenData` vía
  `SessionService` y llame `cortex_tui::sessions::render` en el loop
  (poll + Ctrl+C, contrato v1 read-only).
- Gates: fmt ✅ · clippy -D warnings ✅ (cortex-tui) · cargo test -p
  cortex-tui 16 ✅ (5 gate + 8 snapshots + 2 lib + 1 doc) · suite oráculo
  COMPLETA pre-commit: **2552 passed, 21 skipped, 0F 0E** (177s, bajo
  lock `.cortex/heavy.lock`).

## Evidencia T3

### Implementación
- `rust/crates/cortex-autopilot/src/service.rs` NUEVO: porte de
  `cortex/autopilot/service.py` (444) — start/preflight/checkpoint/finish/
  status orquestando SessionService NATIVO (`cortex-app::session`) + capa de
  decisión P12B-5 (puente native→decision types). `finish(auto=True)` vía
  trait `DocumenterFinalize` inyectable; sin backend ⇒ fallo explícito con el
  mensaje exacto del oráculo.
- `cortex-mcp/src/handlers_autopilot.rs` NUEVO: trait `AutopilotBackend` +
  5 handlers `*_text` byte-parity con `mcp_tools.py` (formato + `_format_error`
  por tipo de excepción). Routing mínimo en `server.rs` (AUTOPILOT_TOOLS +
  `with_autopilot_backend`). Sin tocar handlers existentes.
- `cortex-cli/src/commands/autopilot.rs`: subapp completa start/preflight/
  checkpoint/finish/status nativos (doctor/install/uninstall ⇒ passthrough).
- Drift corregido: warning out-of-scope en Rust usaba `{:?}` (comillas dobles)
  vs `{sorted(drift)}` Python (simples) → `py_list_repr` en `policies.rs` +
  test actualizado. Porte real de `session_hooks_recent_events` en
  cortex-doctor (antes ausente nativo).

### Gates (todos verdes)
1. `bench/parity/cierre_autopilot_golden.py build/verify` → `[PASS]` 236 líneas;
   parte C CLI dual py-vs-rs idéntica en 10 casos.
2. `cargo run -p cortex-autopilot --example cierre_autopilot_check` →
   `[PASS] cierre_autopilot_check byte-parity` (167 líneas A+B) / `✅ PARIDAD
   CIERRE T3`. Oráculo: service.py REAL + `_dispatch_tool_sync` REAL sobre
   sesiones fixture reales (gitless placeholder, {{TS}}/{{MIN}}/{{ROOT}}).
3. `doctor_golden_p12b.py` ampliado con escenario `autopilot_e2e` (policy real
   + sesión activa real) → `cargo run -p cortex-doctor --example doctor_check`
   `[PASS] ... byte-parity` / `✅ PARIDAD P12B-4`.
4. Suite oráculo COMPLETA: **2552 passed, 21 skipped, 0F 0E** (133s,
   `-p no:randomly`, bajo lock `.cortex/heavy.lock`).
5. fmt ✅ · clippy `-D warnings` ✅ en cortex-autopilot/mcp/doctor ·
   cargo test -p {autopilot,mcp,doctor} ✅ (5+21+4+…). Nota: clippy global
   de cortex-cli tiene warnings del WIP T2 del principal (fuera de mi
   territorio); commands/autopilot.rs con cero warnings propios.

## Cola de tareas

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| T3 autopilot service+cli+mcp×5 | ✅ | gates 1-5 arriba | `e089a25` |
| T6 pantalla ratatui sesiones | ✅ | gate T6 (5 tests) + oráculo 2552 | `fa11473` |
