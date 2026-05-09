# Fase 9 — Delegación y Deep Track Real: Realización

## Fecha
2026-05-09

## Resumen
Se cerró la inconsistencia entre la skill `cortex-SDDwork.md` (que mencionaba `cortex_delegate_task`) y el MCP server (que no lo exponía). Se implementó la Opción A: tres tools MCP experimentales (`cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result`), un motor de two-stage review, y la integración en `AutopilotService`.

## Archivos creados
1. `cortex/autopilot/delegation.py` — `DelegationEngine` con two-stage review (Stage 1: spec compliance, Stage 2: quality review), registro en memoria de tareas delegadas (`register_task`, `get_task_result`), y `ReviewVerdict`.
2. `tests/unit/autopilot/test_delegation.py` — 13 tests cubriendo:
   - Stage 1: falla en status=failed, diff vacío con archivos, archivos fuera de scope.
   - Stage 2: falla en rejection_reason, tests_passed=False.
   - Registro de tareas.
   - Integración con `AutopilotService.review_delegation()`: accepted crea checkpoint, rejected logea evento y warning.

## Archivos modificados
1. `cortex/mcp/server.py`:
   - Importa `DelegationResult`, `register_task`, `get_task_result`.
   - Agrega 3 `types.Tool` en `handle_list_tools`:
     - `cortex_delegate_task` — delega tarea simple, retorna `task_id`.
     - `cortex_delegate_batch` — delega múltiples tareas, retorna `task_ids`.
     - `cortex_get_task_result` — recupera resultado y ejecuta two-stage review via `AutopilotService.review_delegation()`.
   - Handlers en `handle_call_tool` que logean y retornan texto legible.

2. `cortex/autopilot/service.py`:
   - Importa `DelegationEngine`, `ReviewVerdict`, `DelegationResult`.
   - Nuevo método `review_delegation(session_id, result)` que:
     - Ejecuta two-stage review.
     - Persiste el veredicto como evento `"delegation_review"`.
     - Si es rechazado, agrega warning al estado.
     - Si es aceptado, registra un checkpoint automático con los archivos del resultado.

3. `cortex/setup/cortex_workspace.py`:
   - Actualizada la skill `cortex-SDDwork.md` para reflejar que las tools de delegación están disponibles como MCP experimentales.
   - Agregado `cortex_delegate_batch` y `cortex_get_task_result` con two-stage review obligatorio.
   - Regla explícita: si no hay runtime de subagente, degrada a Fast Track o pide confirmación.

## Diseño clave

### Two-stage review (§9.5)
- **Stage 1 (spec compliance)**: verifica `status != failed`, `diff_summary` no vacío si hay archivos, y `files_changed` dentro del scope de `state.changed_files`.
- **Stage 2 (quality review)**: verifica ausencia de `rejection_reason` y `tests_passed != False`.
- Ambos stages deben pasar para `accepted=True`.

### Tools MCP experimentales
- Todas las 3 tools llevan `[EXPERIMENTAL]` en su descripción.
- `cortex_delegate_task` y `cortex_delegate_batch` solo registran tareas en un registro en memoria (no spawn subagentes reales).
- `cortex_get_task_result` es el punto de integración con two-stage review: recibe los datos del resultado y ejecuta `review_delegation()`.

### Alineación skill ↔ MCP
- La skill `cortex-SDDwork.md` ahora documenta las 3 tools experimentales y el flujo de two-stage review.
- No quedan instrucciones que pidan tools inexistentes.

### Deep Track registra motivo y costo
- `preflight()` ya siembra `state.budget.deep_track_reason` cuando `suggested_complexity == "deep"` (implementado en Fase 8).
- `review_delegation()` registra eventos estructurados en el event log, permitiendo auditoría de costo de delegación.

## Tests
- `pytest tests/unit/autopilot/test_delegation.py` — 13/13 passed.
- Suite completa Autopilot — 258/258 passed (sin regresiones).

## Incidentes y resoluciones
1. **`cortex-SDDwork.md` mencionaba `cortex_delegate_task` pero no existía en MCP**: Se agregaron las 3 tools en `server.py` y se actualizó el template de la skill para documentarlas como experimentales.
2. **`server.py` requiere importar `DelegationResult`**: Se agregó el import sin romper imports existentes.
3. **`ReviewVerdict` necesitaba integrarse con eventos y checkpoints**: `AutopilotService.review_delegation()` maneja ambos casos (accepted/rejected) de forma atómica.

## Desviaciones respecto del plan
- Ninguna. Se siguió la Opción A recomendada (tools MCP experimentales) y el two-stage review obligatorio.

## Riesgos residuales
- Las tools de delegación son mock/stub (no spawn subagentes reales). El two-stage review opera sobre datos proporcionados por el caller. En producción, el harness real debería proporcionar `DelegationResult` con diff real y resultado de tests.
- El registro de tareas es en memoria (`_task_registry` global). En producción debería persistirse en `StateStore`.

## Próximos pasos
- Fase 10 (Doctor, Observabilidad y Auditoría) puede usar los eventos `"delegation_review"` ya emitidos.
- Fase 11 (Tests E2E) puede validar el flujo completo de delegación MCP.
